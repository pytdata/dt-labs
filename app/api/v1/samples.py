from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Sample, SampleCategory, Test
from app.models.enums import LabStage, LabStatus, PhlebotomyStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.sample import (
    SampleCategoryCreate,
    SampleCategoryResponse,
    SampleCreate,
    SampleCreateRequest,
    SampleDetailResponse,
    SampleResponse,
)


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    department: str | None = None
    search: str | None = None
    # status: AppointmentStatus | None = None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_sample(
    payload: SampleCreate,
    db: AsyncSession = Depends(get_db),
):
    # ensure appointment exists
    appointment = await db.get(Appointment, payload.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # create a labOrder
    lab_order = LabOrder(
        patient_id=payload.patient_id, appointment_id=payload.appointment_id
    )
    db.add(lab_order)
    await db.commit()
    await db.refresh(lab_order)

    # create a laborderItem
    lab_order_items = []
    for test_id in payload.test_ids:
        test_exisit = await db.get(Test, test_id)
        if not test_exisit:
            raise HTTPException(detail="Test not found", status_code=404)

        lab_order_item = LabOrderItem(order_id=lab_order.id, test_id=test_id)
        lab_order_items.append(lab_order_item)

    db.add_all(lab_order_items)
    await db.commit()
    # await db.refresh(lab_order_items)

    sample = Sample(
        sample_type=payload.sample_type,
        appointment_id=payload.appointment_id,
        patient_id=payload.patient_id,
        test_requested=payload.test_ids,
        priority=payload.priority,
        storage_location=payload.storage_location,
        # collector_id=payload.collector_id,
        collection_site=payload.collection_site,
        # sample_condition=payload.sample_condition,
        status=payload.status,
    )

    db.add(sample)
    await db.commit()
    await db.refresh(sample)

    return {
        "message": "Sample created successfully",
        "data": sample,
    }


# @router.get("/", summary="Get all samples", response_model=list[SampleResponse])
# async def get_all_samples(
#     filter_query: Annotated[FilterParams, Query()],
#     db: AsyncSession = Depends(get_db),
# ):
#     stmt = (
#         select(Sample)
#         .options(
#             selectinload(Sample.sample_category),
#             # selectinload(Sample.collector),
#         )
#         .order_by(Sample.collection_date.desc())
#     )

#     result = await db.execute(stmt)

#     samples = result.scalars().all()

#     return samples


@router.post("/collect", response_model=SampleDetailResponse)
async def collect_sample(
    payload: SampleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. ENSURE PHLEBOTOMY EXISTS
    stmt = select(Phlebotomy).where(
        Phlebotomy.appointment_id == payload.appointment_id,
        Phlebotomy.status != PhlebotomyStatus.completed,
    )
    result = await db.execute(stmt)
    phleb = result.scalar_one_or_none()

    if not phleb:
        phleb = Phlebotomy(
            appointment_id=payload.appointment_id,
            patient_id=payload.patient_id,
            status=PhlebotomyStatus.pending,
        )
        db.add(phleb)
        await db.flush()

    # 2. FETCH THE ACTUAL LAB ORDER ITEMS
    # We fetch them as objects so we can link them directly to the Sample
    items_stmt = select(LabOrderItem).where(LabOrderItem.id.in_(payload.test_item_ids))
    items_result = await db.execute(items_stmt)
    items_to_link = items_result.scalars().all()

    if not items_to_link:
        raise HTTPException(status_code=400, detail="No valid test items provided")

    # 3. CREATE THE SAMPLE
    # Assigning 'items=items_to_link' creates the relationship in memory immediately
    new_sample = Sample(
        sample_type_id=payload.sample_category_id,
        phlebotomy_id=phleb.id,
        appointment_id=payload.appointment_id,
        patient_id=payload.patient_id,
        priority=payload.priority,
        storage_location=payload.storage_location,
        collection_site=payload.collection_site,
        status="collected",
        items=items_to_link,  # <--- CRITICAL: Direct relationship assignment
    )

    # 4. UPDATE ITEM STATUSES INDIVIDUALLY
    for item in items_to_link:
        # Change from IN_PROGRESS to AWAITING_RESULTS
        item.status = LabStatus.AWAITING_RESULTS

        # Move the stage from SAMPLING to RUNNING (or ANALYSIS)
        # so it leaves the Phlebotomy list and enters the Lab list
        item.stage = LabStage.RUNNING

    db.add(new_sample)

    try:
        await db.commit()

        # 5. RE-FETCH WITH FULL RELATIONSHIPS FOR RESPONSE
        # Using unique() is mandatory when using selectinload on collection relationships
        refresh_stmt = (
            select(Sample)
            .where(Sample.id == new_sample.id)
            .options(
                selectinload(Sample.items).selectinload(LabOrderItem.test),
                selectinload(Sample.category),
            )
        )
        final_result = await db.execute(refresh_stmt)
        return final_result.unique().scalar_one()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post(
    "/sample-categories",
    response_model=SampleCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sample_category(
    payload: SampleCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SampleCategory).where(
        func.lower(SampleCategory.category_name) == payload.category_name.lower()
    )
    existing = await db.scalar(stmt)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample category already exists",
        )

    category = SampleCategory(category_name=payload.category_name.strip().lower())

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category


@router.get(
    "/sample-categories",
    response_model=list[SampleCategoryResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_sample_category(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SampleCategory)
    existing = await db.scalars(stmt)

    return existing


@router.delete("/{sample_id}")
async def delete_sample(sample_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Fetch sample with phlebotomy relationship
    stmt = (
        select(Sample)
        .where(Sample.id == sample_id)
        .options(selectinload(Sample.phlebotomy))
    )
    result = await db.execute(stmt)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    phleb_id = sample.phlebotomy_id

    # 2. Revert the linked LabOrderItems back to 'awaiting_sample'
    update_stmt = (
        update(LabOrderItem)
        .where(LabOrderItem.sample_id == sample_id)
        .values(sample_id=None, status="awaiting_sample", stage="booking")
    )
    await db.execute(update_stmt)

    # 3. Delete the sample record
    await db.delete(sample)
    await (
        db.flush()
    )  # Flush so we can check remaining samples in the phlebotomy session

    # 4. OPTIONAL: Cleanup Phlebotomy session if empty
    if phleb_id:
        count_stmt = select(func.count(Sample.id)).where(
            Sample.phlebotomy_id == phleb_id
        )
        count_result = await db.execute(count_stmt)
        remaining_samples = count_result.scalar()

        if remaining_samples == 0:
            # If no samples left, we can either delete the phlebotomy session
            # or set it back to a 'pending' state. Let's delete it to keep data clean.
            phleb_stmt = select(Phlebotomy).where(Phlebotomy.id == phleb_id)
            phleb_res = await db.execute(phleb_stmt)
            phleb_obj = phleb_res.scalar_one_or_none()
            if phleb_obj:
                await db.delete(phleb_obj)

    try:
        await db.commit()
        return {"message": "Sample deleted, tests reverted, and session cleaned up."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/appointment/{appointment_id}", response_model=list[SampleDetailResponse])
async def get_appointment_samples(
    appointment_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Sample)
        .where(Sample.appointment_id == appointment_id)
        .options(
            # 1. Load the Category name (Serum, Whole Blood, etc.)
            selectinload(Sample.category),
            # 2. Load the LabOrderItems AND the Test definitions (CBC, Glucose, etc.)
            selectinload(Sample.items).selectinload(LabOrderItem.test),
        )
        .order_by(Sample.collection_date.desc())
    )

    result = await db.execute(stmt)
    # unique() is required when using selectinload on collection relationships
    samples = result.unique().scalars().all()

    return samples


@router.post("/phlebotomy/{phleb_id}/complete")
async def complete_phlebotomy_session(
    phleb_id: int, db: AsyncSession = Depends(get_db)
):
    # 1. Fetch the phlebotomy record to get the associated appointment_id
    stmt = select(Phlebotomy).where(Phlebotomy.id == phleb_id)
    result = await db.execute(stmt)
    phleb = result.scalar_one_or_none()

    if not phleb:
        raise HTTPException(status_code=404, detail="Phlebotomy session not found")

    # 2. CHECK FOR MISSING SAMPLES (The Safety Check)
    # We join LabOrder to reach the appointment_id
    count_stmt = (
        select(func.count(LabOrderItem.id))
        .join(LabOrderItem.order)  # Join the parent LabOrder
        .join(LabOrderItem.test)  # Join Test to check requirements
        .where(
            LabOrder.appointment_id == phleb.appointment_id,
            LabOrderItem.sample_id == None,
            Test.requires_phlebotomy == True,
        )
    )
    count_result = await db.execute(count_stmt)
    unsampled_count = count_result.scalar()

    if unsampled_count and unsampled_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete. {unsampled_count} tests are still missing samples.",
        )

    # 3. UPDATE STATUSES
    # Move the Phlebotomy session to 'completed'
    phleb.status = "completed"
    phleb.completed_at = func.now()

    # Move all items for this appointment to 'awaiting_results' / 'analysis'
    # We use a subquery to find all items belonging to this appointment's orders
    items_to_update_stmt = (
        update(LabOrderItem)
        .where(
            LabOrderItem.id.in_(
                select(LabOrderItem.id)
                .join(LabOrderItem.order)
                .where(LabOrder.appointment_id == phleb.appointment_id)
            )
        )
        .values(status="awaiting_results", stage="analysis")
    )
    await db.execute(items_to_update_stmt)

    try:
        await db.commit()
        return {"message": "Collection finalized successfully."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
