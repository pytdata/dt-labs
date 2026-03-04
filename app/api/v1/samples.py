from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.catalog import Sample, SampleCategory, Test
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.sample import (
    SampleCategoryCreate,
    SampleCategoryResponse,
    SampleCreate,
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


@router.get("/", summary="Get all samples", response_model=list[SampleResponse])
async def get_all_samples(
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Sample)
        .options(
            selectinload(Sample.sample_category),
            # selectinload(Sample.collector),
        )
        .order_by(Sample.collection_date.desc())
    )

    result = await db.execute(stmt)

    samples = result.scalars().all()

    return samples


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


@router.delete("/{id}", status_code=204)
async def delete_sample(
    id: int,
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(select(Sample).where(Sample.id == id))

    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    await db.delete(sample)
    await db.commit()

    return None
