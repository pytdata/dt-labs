from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, func, select, update
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.company import CompanyProfile, OrganizationPrefix
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult, Patient
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


@router.get("/phlebotomy-queue/", response_model=list[LabQueueResponse2])
async def get_phlebotomy_results_queue(db: AsyncSession = Depends(get_db)):
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    lab_prefix = settings.lab if settings else "LAB"
    pat_prefix = settings.patient if settings else "PAT"
    apt_prefix = settings.appointment if settings else "APT"

    # 2. Build Query with explicit Eager Loading for the Doctor
    stmt = (
        select(LabOrderItem)
        .join(Test, LabOrderItem.test_id == Test.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .where(
            LabOrderItem.status == LabStatus.AWAITING_RESULTS,
            Test.requires_phlebotomy == True,
        )
        .options(
            selectinload(LabOrderItem.order).options(
                selectinload(LabOrder.patient),
                selectinload(LabOrder.appointment).options(
                    selectinload(Appointment.patient),
                    selectinload(Appointment.doctor),  # <--- ADD THIS LINE
                ),
            ),
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
        )
        .order_by(LabOrder.created_at.asc())
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    # 3. Transform and Inject
    queue_out = []
    for item in items:
        # Now model_validate won't trigger a lazy-load error for the doctor
        q_dto = LabQueueResponse2.model_validate(item)

        setattr(q_dto, "_org_code", org_code)
        setattr(q_dto, "_mod_prefix", lab_prefix)

        if q_dto.order:
            if q_dto.order.patient:
                setattr(q_dto.order.patient, "_org_code", org_code)
                setattr(q_dto.order.patient, "_mod_prefix", pat_prefix)

            if q_dto.order.appointment:
                appt = q_dto.order.appointment
                setattr(appt, "_org_code", org_code)
                setattr(appt, "_mod_prefix", apt_prefix)

                if appt.patient:
                    setattr(appt.patient, "_org_code", org_code)
                    setattr(appt.patient, "_mod_prefix", pat_prefix)

        queue_out.append(q_dto)

    return queue_out


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
async def get_radiology_queue(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    rad_prefix = settings.radiology if settings else "RAD"
    pat_prefix = settings.patient if settings else "PAT"
    apt_prefix = settings.appointment if settings else "APT"

    # 2. Build Query
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .outerjoin(Test.test_category)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        .outerjoin(Appointment.doctor)
    )

    filters = [
        Test.requires_phlebotomy == False,
        LabOrderItem.status.in_(
            [LabStatus.AWAITING_RESULTS, LabStatus.AWAITING_APPROVAL]
        ),
        LabOrderItem.stage.in_(
            [LabStage.BOOKING, LabStage.RUNNING, LabStage.ANALYZING]
        ),
    ]

    if start_date:
        filters.append(func.date(LabOrderItem.created_at) >= start_date)
    if end_date:
        filters.append(func.date(LabOrderItem.created_at) <= end_date)

    stmt = (
        stmt.where(*filters)
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
        .order_by(LabOrderItem.id.desc())
    )

    result = await db.execute(stmt)
    results = result.unique().scalars().all()

    # 3. Transform and Inject Prefixes
    queue_out = []
    for item in results:
        # Validate Pydantic Model
        q_dto = LabQueueResponse2.model_validate(item)

        # Inject Radiology Item Prefixes
        setattr(q_dto, "_org_code", org_code)
        setattr(q_dto, "_mod_prefix", rad_prefix)

        # Cascade to Appointment and Patient
        if q_dto.order and q_dto.order.appointment:
            appt = q_dto.order.appointment
            setattr(appt, "_org_code", org_code)
            setattr(appt, "_mod_prefix", apt_prefix)

            if appt.patient:
                setattr(appt.patient, "_org_code", org_code)
                setattr(appt.patient, "_mod_prefix", pat_prefix)

        queue_out.append(q_dto)

    return queue_out


@router.get("/active-appointments/", response_model=list[LabQueueResponse])
async def get_all_finalized_results(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
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
                joinedload(Appointment.phlebotomy),
                joinedload(Appointment.doctor),
            ),
            # 3. Load results
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.status == LabStatus.COMPLETED)
    )

    # --- DYNAMIC DATE FILTERING ---
    if start_date:
        # func.date() casts the TIMESTAMP to a DATE for accurate comparison
        stmt = stmt.where(func.date(LabOrderItem.created_at) >= start_date)

    if end_date:
        stmt = stmt.where(func.date(LabOrderItem.created_at) <= end_date)
    # ------------------------------

    # Sort by most recent first
    stmt = stmt.order_by(LabOrderItem.id.desc())

    result = await db.execute(stmt)
    results = result.unique().scalars().all()
    return results


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
    # 1. Fetch Company Profile first
    company_stmt = select(CompanyProfile)
    company_res = await db.execute(company_stmt)
    company = company_res.scalars().first()

    # 2. Fetch Lab Item with all necessary relationships
    stmt = (
        select(LabOrderItem)
        .options(
            selectinload(LabOrderItem.order)
            .selectinload(LabOrder.appointment)
            .selectinload(Appointment.patient),
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

    return templates.TemplateResponse(
        "lab/report_print.html",
        {"request": {}, "item": item, "company": company, "now": datetime.now()},
    )


@router.get("/queue/{dept}", response_model=list[LabQueueResponse])
async def get_lab_queue(
    dept: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):

    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    lab_prefix = settings.lab if settings else "LAB"
    rad_prefix = settings.radiology if settings else "RAD"
    pat_prefix = settings.patient if settings else "PAT"
    apt_prefix = settings.appointment if settings else "APT"

    # 2. Build Lab Queue Query
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .outerjoin(Test.test_category)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
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
    ).order_by(LabOrderItem.id.desc())

    if start_date:
        stmt = stmt.where(LabOrder.created_at >= start_date)
    if end_date:
        stmt = stmt.where(LabOrder.created_at <= end_date)

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

    # 3. Execute and Transform
    result = await db.execute(stmt)
    items = result.unique().scalars().all()

    queue_out = []
    for item in items:
        # Convert to Pydantic
        q_dto = LabQueueResponse.model_validate(item)

        # Determine if this item uses LAB or RAD prefix based on the test
        current_mod = rad_prefix if dept == "radiology" else lab_prefix

        # Inject Lab Item Prefixes
        q_dto._org_code = org_code
        q_dto._mod_prefix = current_mod

        # Cascade prefixes down the nesting
        if q_dto.order and q_dto.order.appointment:
            appt = q_dto.order.appointment
            # Appointment Prefix
            appt._org_code = org_code
            appt._mod_prefix = apt_prefix

            # Patient Prefix
            if appt.patient:
                appt.patient._org_code = org_code
                appt.patient._mod_prefix = pat_prefix

        queue_out.append(q_dto)

    return queue_out


@router.get(
    "/appointments/{appointment_id}/pending-items",
    response_model=list[LabOrderItemResponse],
)
async def get_pending_lab_items(
    appointment_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.order)
        .join(
            LabOrderItem.test
        )  # Explicitly join the Test table to filter on its columns
        .options(
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(
            LabOrder.appointment_id == appointment_id,
            # Handle both stages to ensure items aren't missed
            LabOrderItem.stage.in_([LabStage.SAMPLING, LabStage.BOOKING]),
            LabOrderItem.status == LabStatus.AWAITING_SAMPLE,
            # The boolean filter:
            Test.requires_phlebotomy == True,
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
