from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.deps import get_current_user
from app.core.rbac import PermissionChecker
from app.db.session import get_db
from app.models import Patient
from app.models.company import OrganizationPrefix
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult, Visit
from app.models.users import User
from app.schemas import PatientCreate, PatientOut
from sqlalchemy import or_
from sqlalchemy.orm import selectinload


from typing import Annotated, List, Literal, Optional


from pydantic import BaseModel, Field

from app.schemas.lab_results import LabResultResponse

router = APIRouter()

DEFAULT_PREFIX = "YGK"  # can be moved to Settings table later


async def _next_patient_no(db: AsyncSession) -> str:
    # Get the current max ID
    max_id = (await db.execute(select(func.max(Patient.id)))).scalar() or 0

    # Logic to start from 100
    # If the database is empty (max_id is 0), start at 100.
    # Otherwise, increment the current max_id.
    if max_id == 0:
        nxt = 100
    else:
        nxt = int(max_id) + 1

    # Change :06d to :03d for 3-digit padding (e.g., 101, 102...)
    return f"{DEFAULT_PREFIX}-PT-{nxt:03d}"


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    first_name: str | None = None
    surname: str | None = None
    sex: list[str] | None = None
    search: str | None = None

    start_date: date | None = None
    end_date: date | None = None


@router.post(
    "/",
    response_model=PatientOut,
    dependencies=[Depends(PermissionChecker("patients", "write"))],
)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient_no = await _next_patient_no(db)

    # Store who created the patient for audit trails
    patient_data = payload.model_dump()
    patient = Patient(
        patient_no=patient_no, **patient_data, created_by_id=current_user.id
    )

    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get(
    "/",
    response_model=List[PatientOut],
    dependencies=[Depends(PermissionChecker("patients", "read"))],
)
async def list_patients(
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Build Scalar Subquery targeting Appointment table
    # Replace 'appointment_date' with whatever your date column is named
    last_appt_stmt = (
        select(func.max(Appointment.appointment_at))
        .where(Appointment.patient_id == Patient.id)
        .scalar_subquery()
    )

    # 3. Main Query: Select Patient AND the calculated field
    stmt = select(Patient, last_appt_stmt.label("last_visit_date"))

    # --- Apply Filters ---
    if filter_query.search:
        q = f"%{filter_query.search.strip()}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(q),
                Patient.surname.ilike(q),
                Patient.other_names.ilike(q),
                Patient.patient_no.ilike(q),
            )
        )

    if filter_query.sex:
        stmt = stmt.where(Patient.sex.in_(filter_query.sex))

    if filter_query.start_date:
        stmt = stmt.where(func.date(Patient.created_at) >= filter_query.start_date)
    if filter_query.end_date:
        stmt = stmt.where(func.date(Patient.created_at) <= filter_query.end_date)

    # Sorting
    if filter_query.sort_by == "oldest":
        stmt = stmt.order_by(Patient.id.asc())
    else:
        stmt = stmt.order_by(Patient.id.desc())

    # Pagination
    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    # 4. Execute and Map
    result = await db.execute(stmt)
    rows = result.all()  # Returns [(Patient, datetime), ...]

    patients_out = []
    for patient_obj, last_date in rows:
        p_dto = PatientOut.model_validate(patient_obj)

        # Inject prefix data for display_id
        p_dto._org_code = org_code
        p_dto._mod_prefix = pat_prefix

        # Now last_date will pull from Appointment table
        p_dto.last_visit_date = last_date

        patients_out.append(p_dto)

    return patients_out


@router.get(
    "/search",
    dependencies=[Depends(PermissionChecker("patients", "read"))],
)
async def search_patients(
    q: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Quick search for patients by name or patient number.
    Returns prefix-aware IDs and basic info for selection UI.
    """
    # 1. Fetch Global Prefix Settings for Display IDs
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Build Search Query
    # Included patient_no in the search for better UX
    search_term = f"%{q.strip()}%"
    stmt = (
        select(Patient)
        .where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.surname.ilike(search_term),
                Patient.other_names.ilike(search_term),
                Patient.patient_no.ilike(search_term),
            )
        )
        .limit(10)  # Increased slightly for better results
    )

    result = await db.execute(stmt)
    patients = result.scalars().all()

    # 3. Return Formatted Results
    return [
        {
            "id": p.id,
            # Generate the Display ID manually here to match your PatientOut logic
            "display_id": f"{org_code}-{pat_prefix}-{str(p.id).zfill(4)}",
            "full_name": f"{p.first_name} {p.surname}",
            "phone": p.phone,
            "dob": p.date_of_birth.isoformat() if p.date_of_birth else None,
        }
        for p in patients
    ]


@router.get(
    "/{id}/",
    response_model=PatientOut,
    dependencies=[Depends(PermissionChecker("patients", "read"))],
)
async def get_patients(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a single patient by ID with prefix-aware formatting.
    Access restricted to users with 'patients:read' permission.
    """
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Fetch Patient Record
    stmt = select(Patient).where(Patient.id == id)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient record not found"
        )

    # 3. Transform to Pydantic and Inject Prefixes
    # This ensures the 'display_id' computed field uses the correct DB settings
    p_dto = PatientOut.model_validate(patient)
    p_dto._org_code = org_code
    p_dto._mod_prefix = pat_prefix

    # Note: If your PatientOut requires last_visit_date, you may need a
    # separate query or a join here similar to the list_patients route.

    return p_dto


@router.get(
    "/{patient_id}/lab-results",
    response_model=List[LabResultResponse],
    dependencies=[Depends(PermissionChecker("patients", "read"))],
)
async def get_patient_lab_results(
    patient_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    # Verify Patient Exists
    patient_exists = await db.scalar(select(Patient.id).where(Patient.id == patient_id))
    if not patient_exists:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Build Query
    stmt = (
        select(LabResult)
        .join(LabResult.order_item)
        .join(LabOrderItem.order)
        .options(
            selectinload(LabResult.order_item).selectinload(LabOrderItem.test),
            selectinload(LabResult.entered_by_user),
            selectinload(LabResult.verified_by_user),
        )
        .where(LabOrder.patient_id == patient_id)
    )

    # Apply Date Filters on LabResult.received_at or updated_at
    if start_date:
        stmt = stmt.where(func.date(LabResult.received_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(LabResult.received_at) <= end_date)

    stmt = stmt.order_by(LabResult.received_at.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/lab-results",
    response_model=List[LabResultResponse],
    dependencies=[Depends(PermissionChecker("lab_results", "read"))],
)
async def get_all_lab_results(
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch all lab results.
    Access restricted to users with 'lab_results:read' permission.
    """
    stmt = (
        select(LabResult)
        .options(
            selectinload(LabResult.sample),
            # Load the test name and category via order_item
            selectinload(LabResult.order_item).selectinload(LabOrderItem.test),
            selectinload(LabResult.analyzer),
            selectinload(LabResult.analyzer_message),
            selectinload(LabResult.entered_by_user),
            selectinload(LabResult.verified_by_user),
        )
        .order_by(LabResult.received_at.desc())
    )

    result = await db.execute(stmt)
    lab_results = result.scalars().all()

    return lab_results
