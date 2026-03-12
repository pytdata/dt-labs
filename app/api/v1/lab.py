from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, func, select, update
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.appointment import TestResponse
from app.schemas.lab import LabOrderItemResponse, LabQueueResponse, LabQueueResponse2
from app.core.config import settings


templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
router = APIRouter()


class DepartmentType(str, Enum):
    radiology = "radiology"
    phlebotomy = "phlebotomy"


class PhlebotomyStatus(str, Enum):
    awaiting_sample = "awaiting_sample"
    awaiting_results = "awaiting_results"
    in_progress = "in_progress"


@router.get("/queue/radiology", response_model=list[LabQueueResponse2])
async def get_radiology_queue(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .outerjoin(Test.test_category)  # JOIN CATEGORY HERE
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        .outerjoin(Appointment.doctor)
        .where(
            Test.requires_phlebotomy == False,
            # Use the Enum members directly if your model uses Enum types
            LabOrderItem.status.in_(
                [
                    LabStatus.AWAITING_RESULTS,
                    LabStatus.AWAITING_APPROVAL,
                ]
            ),
            LabOrderItem.stage.in_(
                [
                    LabStage.RUNNING,
                    LabStage.ANALYZING,
                ]
            ),
        )
        .options(
            # Eagerly load the category to satisfy Pydantic
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


@router.get("/report/print/{item_id}", response_class=HTMLResponse)
async def print_lab_report(
    request: Request, item_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(LabOrderItem)
        .options(
            joinedload(LabOrderItem.test).joinedload(Test.test_category),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .joinedload(Appointment.patient),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .joinedload(Appointment.doctor),
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Report not found")

    # Pass the data to a clean, printable HTML template
    return templates.TemplateResponse(
        "lab/report_print.html", {"request": request, "item": item}
    )


@router.get("/queue/{dept}", response_model=list[LabQueueResponse])
async def get_lab_queue(dept: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        # We need to join the category so contains_eager can see it
        .outerjoin(Test.test_category)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        .outerjoin(Appointment.phlebotomy)
        .options(
            # Use contains_eager for everything since you joined them manually
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
        stmt = stmt.where(
            Test.requires_phlebotomy == False,
            LabOrderItem.status.in_(
                [LabStatus.AWAITING_RESULTS, LabStatus.AWAITING_APPROVAL]
            ),
        )

    result = await db.execute(stmt)
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
        .join(LabOrderItem.order)
        .join(LabOrderItem.test)
        .where(
            LabOrder.appointment_id == appointment_id,
            LabOrderItem.status == "awaiting_sample",
            # LabOrderItem.ssAdd this to ensure you're in the right workflow
            Test.requires_phlebotomy == True,
        )
        .options(
            selectinload(LabOrderItem.test),
            selectinload(LabOrderItem.radiology_result),  # Keeps Pydantic from crashing
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
