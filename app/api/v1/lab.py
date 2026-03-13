from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, func, select, update
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult
from app.schemas.appointment import TestResponse
from app.schemas.lab import LabOrderItemResponse, LabQueueResponse, LabQueueResponse2
from app.core.config import settings
from app.schemas.lab_results import LabResultStatus


templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
router = APIRouter()


class DepartmentType(str, Enum):
    radiology = "radiology"
    phlebotomy = "phlebotomy"


class PhlebotomyStatus(str, Enum):
    awaiting_sample = "awaiting_sample"
    awaiting_results = "awaiting_results"
    in_progress = "in_progress"


@router.get("/phlebotomy-queue/")
async def get_phlebotomy_results_queue(db: AsyncSession = Depends(get_db)):
    """
    Fetches only LabOrderItems that require phlebotomy and are awaiting results.
    """
    stmt = (
        select(LabOrderItem)
        .join(Test, LabOrderItem.test_id == Test.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .where(
            # Using your specific Enum or String status
            LabOrderItem.status == LabStatus.AWAITING_RESULTS,
            # LabOrderItem.status == LabStatus.IN_PROGRESS,
            # Ensure it's a lab test, not radiology
            Test.requires_phlebotomy == True,
        )
        .options(
            # Match your model relationships
            selectinload(LabOrderItem.order).selectinload(LabOrder.patient),
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
        )
        .order_by(LabOrder.created_at.asc())
    )

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/results/submit-phlebotomy")
async def submit_lab_results(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_active_user),  # To track who entered it
):
    order_item_id = payload.get("order_item_id")
    results_data = payload.get("results")  # This is our JSON object

    async with db.begin():
        # 1. Create the LabResult record
        new_result = LabResult(
            order_item_id=order_item_id,
            results=results_data,  # This goes straight into the JSON column
            source="manual",
            # entered_by_user_id=current_user.id,
            status=LabResultStatus.verified,  # Or pending if you want a second person to verify
            received_at=func.now(),
        )
        db.add(new_result)

        # 2. Update the LabOrderItem stage and status
        # This moves it from 'analysis' to 'completed'
        stmt = (
            update(LabOrderItem)
            .where(LabOrderItem.id == order_item_id)
            .values(status="COMPLETED", stage="completed")
        )
        await db.execute(stmt)

    return {"message": "Results saved and item completed successfully"}


@router.get("/queue/radiology", response_model=list[LabQueueResponse2])
async def get_radiology_queue(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .outerjoin(Test.test_category)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        .outerjoin(Appointment.doctor)
        .where(
            Test.requires_phlebotomy == False,
            # 1. Status Check: Must be past payment
            LabOrderItem.status.in_(
                [
                    LabStatus.AWAITING_RESULTS,
                    LabStatus.AWAITING_APPROVAL,
                ]
            ),
            # 2. Stage Check: Include BOOKING so it shows up immediately after payment
            LabOrderItem.stage.in_(
                [
                    LabStage.BOOKING,  # <--- Added this
                    LabStage.RUNNING,
                    LabStage.ANALYZING,
                ]
            ),
        )
        .options(
            contains_eager(LabOrderItem.test).contains_eager(Test.test_category),
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .options(
                contains_eager(Appointment.patient), contains_eager(Appointment.doctor)
            ),
            selectinload(LabOrderItem.radiology_result),
            selectinload(LabOrderItem.lab_result),
        )
    )

    result = await db.execute(stmt)
    results = result.unique().scalars().all()
    return results


@router.get("/active-appointments/", response_model=list[LabQueueResponse])
async def get_all_finalized_results(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .options(
            # 1. Load test and category
            joinedload(LabOrderItem.test).joinedload(Test.test_category),
            # 2. Load the chain: Order -> Appointment -> Patient AND Phlebotomy
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .options(
                joinedload(Appointment.patient),
                joinedload(Appointment.phlebotomy),  # <--- THIS FIXES THE ERROR
                joinedload(Appointment.doctor),  # Recommended to avoid future errors
            ),
            # 3. Load results
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.status == LabStatus.COMPLETED)
    )

    result = await db.execute(stmt)
    # unique() is vital here because we have multiple joinedloads
    results = result.unique().scalars().all()
    print(f"Found {len(results)} finalized records.")
    return results


@router.get("/item/{item_id}")
async def get_lab_item_details(item_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .options(
            joinedload(LabOrderItem.test).joinedload(Test.test_category),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .joinedload(Appointment.patient),
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Result not found")
    return item


@router.get("/report/{item_id}")
async def get_radiology_report_data(item_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches comprehensive data for a finalized radiology report including
    patient, doctor, and test details.
    """
    stmt = (
        select(LabOrderItem)
        .options(
            joinedload(LabOrderItem.test),
            joinedload(LabOrderItem.radiology_result),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .joinedload(Appointment.patient),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .joinedload(Appointment.doctor),
        )
        .where(LabOrderItem.id == item_id)
    )

    result = await db.execute(stmt)
    # .unique() is required when using joinedload on many-to-one relationships in some versions
    item = result.unique().scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Lab item not found")

    if not item.radiology_result:
        raise HTTPException(status_code=404, detail="No results found for this item")

    # Return a structured dictionary or a Pydantic model
    return {
        "id": item.id,
        "test_name": item.test.name,
        "patient": item.order.appointment.patient,
        "doctor": item.order.appointment.doctor,
        "findings": item.radiology_result.result_value,
        "conclusion": item.radiology_result.comments,
        "status": item.status,
        "finalized_at": item.radiology_result.entered_at,
    }


@router.get("/report/print/{item_id}")
async def print_lab_report(item_id: int, db: AsyncSession = Depends(get_db)):
    # Explicitly load EVERY relationship used in the HTML template
    stmt = (
        select(LabOrderItem)
        .options(
            selectinload(LabOrderItem.order)
            .selectinload(LabOrder.appointment)
            .selectinload(Appointment.patient),
            selectinload(LabOrderItem.order)
            .selectinload(LabOrder.appointment)
            .selectinload(Appointment.doctor),  # Fixed: Load the doctor!
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.id == item_id)
    )

    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Report not found")

    # Safety check for the template
    is_lab = False
    if item.test and item.test.test_category:
        is_lab = item.test.test_category.category_name != "Radiology"

    return templates.TemplateResponse(
        "lab/report_print.html",
        {"request": {}, "item": item, "is_lab": is_lab, "now": datetime.now()},
    )


@router.get("/queue/{dept}", response_model=list[LabQueueResponse])
async def get_lab_queue(dept: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .outerjoin(Test.test_category)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        # Use outerjoin here because phlebotomy/radiology records
        # aren't created until AFTER the scientist starts work
        .outerjoin(Appointment.phlebotomy)
        .options(
            contains_eager(LabOrderItem.test).contains_eager(Test.test_category),
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .options(
                contains_eager(Appointment.patient),
                contains_eager(Appointment.phlebotomy),
            ),
        )
    )

    if dept == "phlebotomy":
        stmt = stmt.where(
            Test.requires_phlebotomy == True,
            LabOrderItem.status == LabStatus.AWAITING_SAMPLE,
        )
    else:
        # Radiology / Others
        stmt = stmt.where(
            Test.requires_phlebotomy == False,
            LabOrderItem.status.in_(
                [LabStatus.AWAITING_RESULTS, LabStatus.AWAITING_APPROVAL]
            ),
        )

    result = await db.execute(stmt)
    # .unique() is necessary when using joined loads/contains_eager
    return result.unique().scalars().all()


@router.get(
    "/appointments/{appointment_id}/pending-items",
    response_model=list[LabOrderItemResponse],
)
async def get_pending_lab_items(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabOrderItem)
        .options(
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
            selectinload(LabOrderItem.radiology_result),  # Add this!
            selectinload(LabOrderItem.lab_result),  # Add this for safety too!
        )
        .where(
            LabOrderItem.order.has(appointment_id=appointment_id),
            LabOrderItem.stage == LabStage.SAMPLING,
            LabOrderItem.status == LabStatus.AWAITING_SAMPLE,
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/appointments/{appointment_id}/radiology-items",
    response_model=list[LabOrderItemResponse],
)
async def get_radiology_items(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.order)
        .join(LabOrderItem.test)
        .where(
            LabOrder.appointment_id == appointment_id,
            Test.requires_phlebotomy == False,
            LabOrderItem.status.in_(["awaiting_results", "in_progress"]),
        )
        .options(
            selectinload(LabOrderItem.test),
            # NEW: Load the specific radiology result relationship
            selectinload(LabOrderItem.radiology_result),
            # selectinload(LabOrderItem.lab_result),
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()
