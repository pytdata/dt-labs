from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, String, cast, func, or_, select, update
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.company import CompanyProfile, OrganizationPrefix
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult, Patient
from app.models.users import User
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


@router.get("/phlebotomy-queue/", response_model=List[LabQueueResponse2])
async def get_phlebotomy_results_queue(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches the lab queue for items awaiting results or in analysis (provisional).
    Supports date range filtering and global search.
    """

    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    lab_prefix = settings.lab if settings else "LAB"
    pat_prefix = settings.patient if settings else "PAT"
    apt_prefix = settings.appointment if settings else "APT"

    # 2. Build Base Query with Joins and Status logic
    stmt = (
        select(LabOrderItem)
        .join(Test, LabOrderItem.test_id == Test.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .join(Patient, LabOrder.patient_id == Patient.id)
        .where(
            # UPDATED: We now include 'ANALYSING' so items with provisional results stay in the queue
            LabOrderItem.status.in_([LabStatus.AWAITING_RESULTS, "ANALYSING"]),
            Test.requires_phlebotomy == True,
        )
        .options(
            # ADDED: Load the lab_result so frontend can check item.lab_result.status
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.order).options(
                selectinload(LabOrder.patient),
                selectinload(LabOrder.appointment).options(
                    selectinload(Appointment.patient),
                    selectinload(Appointment.doctor),
                ),
            ),
            selectinload(LabOrderItem.test).selectinload(Test.test_category),
        )
    )

    # 3. Dynamic Date Filtering
    if start_date:
        stmt = stmt.where(func.date(LabOrderItem.created_at) >= start_date)

    if end_date:
        stmt = stmt.where(func.date(LabOrderItem.created_at) <= end_date)

    # 4. Global Search Logic
    if search:
        search_query = f"%{search}%"
        stmt = stmt.where(
            or_(
                LabOrderItem.id.cast(String).ilike(search_query),
                Patient.first_name.ilike(search_query),
                Patient.surname.ilike(search_query),
                Patient.patient_no.ilike(search_query),
                Test.name.ilike(search_query),
            )
        )

    # Sort by most recent items first
    stmt = stmt.order_by(LabOrderItem.created_at.desc())

    result = await db.execute(stmt)
    items = result.scalars().all()

    # 5. Transform and Inject Prefixes
    queue_out = []
    for item in items:
        # Validate into the response model
        q_dto = LabQueueResponse2.model_validate(item)

        # Inject dynamic prefixes for display logic
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
    current_user: User = Depends(get_current_user),
):
    order_item_id = payload.get("order_item_id")
    results_data = payload.get("results")
    is_finalized = payload.get("is_finalized", False)

    # Use a try block to handle the logic without starting a new transaction block
    try:
        result_status = "verified" if is_finalized else "pending"

        # Check if a result already exists
        stmt = select(LabResult).where(LabResult.order_item_id == order_item_id)
        existing_result = (await db.execute(stmt)).scalar_one_or_none()

        if existing_result:
            existing_result.results = results_data
            existing_result.status = result_status
            if is_finalized:
                existing_result.verified_by_user_id = current_user.id
                existing_result.verified_at = func.now()
        else:
            new_result = LabResult(
                order_item_id=order_item_id,
                results=results_data,
                source="manual",
                entered_by_user_id=current_user.id,
                status=result_status,
                received_at=func.now(),
                verified_by_user_id=current_user.id if is_finalized else None,
                verified_at=func.now() if is_finalized else None,
            )
            db.add(new_result)

        # Update LabOrderItem
        item_status = "COMPLETED" if is_finalized else "ANALYSING"
        item_stage = "completed" if is_finalized else "analysis"

        update_stmt = (
            update(LabOrderItem)
            .where(LabOrderItem.id == order_item_id)
            .values(status=item_status, stage=item_stage)
        )
        await db.execute(update_stmt)

        # Commit the changes manually if your get_db doesn't auto-commit
        await db.commit()

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Results saved successfully", "finalized": is_finalized}


@router.get("/queue/radiology", response_model=list[LabQueueResponse2])
async def get_radiology_queue(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = Query(None),
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

    # Build Query
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

    # Add Search Logic
    if search:
        s = f"%{search}%"
        filters.append(
            or_(
                LabOrderItem.id.cast(String).ilike(s),
                Patient.first_name.ilike(s),
                Patient.surname.ilike(s),
                Test.name.ilike(s),
            )
        )

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
    search: Optional[str] = None,  # 1. Added search parameter
    db: AsyncSession = Depends(get_db),
):
    # Base Query
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        # We join through order and appointment to get to the Patient
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .join(Appointment, LabOrder.appointment_id == Appointment.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .options(
            joinedload(LabOrderItem.test).joinedload(Test.test_category),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .options(
                joinedload(Appointment.patient),
                joinedload(Appointment.phlebotomy),
                joinedload(Appointment.doctor),
            ),
            selectinload(LabOrderItem.lab_result),
            selectinload(LabOrderItem.radiology_result),
        )
        .where(LabOrderItem.status == LabStatus.COMPLETED)
    )

    # Date Filtering
    if start_date:
        stmt = stmt.where(func.date(LabOrderItem.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(LabOrderItem.created_at) <= end_date)

    # 2. SEARCH LOGIC
    if search:
        search_query = f"%{search}%"
        stmt = stmt.where(
            or_(
                # LabOrderItem.display_id.ilike(search_query),
                Patient.first_name.ilike(search_query),
                Patient.surname.ilike(search_query),
                Patient.patient_no.ilike(search_query),
                Test.name.ilike(search_query),
            )
        )

    stmt = stmt.order_by(LabOrderItem.id.desc())
    result = await db.execute(stmt)
    results = result.unique().scalars().all()
    return results


@router.get("/report/{item_id}")
async def get_combined_report_data(item_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches sanitized data for both Radiology and Laboratory results.
    Excludes sensitive user data and handles potential null relationships.
    """
    stmt = (
        select(LabOrderItem)
        .options(
            joinedload(LabOrderItem.test),
            joinedload(LabOrderItem.radiology_result),
            joinedload(LabOrderItem.lab_result),
            joinedload(LabOrderItem.order)
            .joinedload(LabOrder.appointment)
            .options(joinedload(Appointment.patient), joinedload(Appointment.doctor)),
        )
        .where(LabOrderItem.id == item_id)
    )

    result = await db.execute(stmt)
    item = result.unique().scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Lab item not found")

    # --- 1. Result Processing (Resolves Pylance Optional Errors) ---
    findings = "No findings recorded."
    results_json = None
    conclusion = "N/A"
    finalized_at = None
    category = "General"

    # Explicit 'is not None' checks narrow the type for Pylance
    if item.radiology_result is not None:
        category = "Radiology"
        findings = item.radiology_result.result_value
        conclusion = item.radiology_result.comments or "N/A"
        finalized_at = item.radiology_result.entered_at

    elif item.lab_result is not None:
        category = "Laboratory"
        results_json = item.lab_result.results
        conclusion = item.lab_result.comments or "N/A"
        finalized_at = item.lab_result.verified_at or item.lab_result.received_at

    # --- 2. Data Sanitization (Security & "Undefined" Fix) ---
    patient_data = None
    doctor_data = None

    if item.order and item.order.appointment:
        appt = item.order.appointment

        # Patient: Construct full_name and blood_group safely
        if appt.patient:
            p = appt.patient
            patient_data = {
                "id": p.id,
                "full_name": f"{p.first_name} {p.surname}",
                "patient_no": p.patient_no,
                "age": p.age,
                "sex": p.sex,
                "blood_group": getattr(p, "blood_group", "N/A"),
            }

        # Doctor: Pick only non-sensitive fields
        if appt.doctor:
            d = appt.doctor
            doctor_data = {
                "id": d.id,
                "full_name": d.full_name,
                "email": d.email,
                "phone": d.phone_number,
            }

    return {
        "id": item.id,
        "test_name": item.test.name if item.test else "Unknown Test",
        "category": category,
        "patient": patient_data,
        "doctor": doctor_data,
        "findings": findings,
        "results": results_json,
        "conclusion": conclusion,
        "status": item.status,
        "finalized_at": finalized_at,
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
    search: str | None = None,  # Added search parameter
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
        stmt = stmt.where(func.date(LabOrder.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(LabOrder.created_at) <= end_date)

    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(search_filter),
                Patient.surname.ilike(search_filter),
                cast(LabOrderItem.id, String).ilike(search_filter),
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


@router.get("/results/by-item/{order_item_id}")
async def get_result_by_item(order_item_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(LabResult).where(LabResult.order_item_id == order_item_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
