from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import Patient
from app.models.company import OrganizationPrefix
from app.models.lab import LabOrder, LabOrderItem, LabResult, Visit
from app.schemas import PatientCreate, PatientOut
from sqlalchemy import or_
from sqlalchemy.orm import selectinload


from typing import Annotated, Literal


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


@router.post("/", response_model=PatientOut)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),
):
    patient_no = await _next_patient_no(db)
    patient = Patient(patient_no=patient_no, **payload.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/", response_model=list[PatientOut])
async def list_patients(
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    # Defaults if settings haven't been configured yet
    org_code = settings.org_identifier if settings else "YKG"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Build Patient Query
    last_visit_subq = (
        select(
            Visit.patient_id,
            func.max(Visit.visit_date).label("last_visit_date"),
        )
        .group_by(Visit.patient_id)
        .subquery()
    )

    stmt = select(Patient, last_visit_subq.c.last_visit_date).outerjoin(
        last_visit_subq,
        last_visit_subq.c.patient_id == Patient.id,
    )

    # --- Apply Filters ---
    if filter_query.first_name:
        like = f"%{filter_query.first_name.strip()}%"
        stmt = stmt.where(Patient.first_name.ilike(like))

    if filter_query.surname:
        like = f"%{filter_query.surname.strip()}%"
        stmt = stmt.where(Patient.surname.ilike(like))

    if filter_query.sort_by == "oldest":
        stmt = stmt.order_by(Patient.id.asc())
    else:
        stmt = stmt.order_by(Patient.id.desc())

    # Apply limit and offset
    stmt = stmt.limit(limit=filter_query.limit).offset(offset=filter_query.offset)

    if filter_query.sex:
        sexes = [s.capitalize() for s in filter_query.sex]
        stmt = stmt.where(Patient.sex.in_(sexes))

    if filter_query.search:
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(f"%{filter_query.search}%"),
                Patient.surname.ilike(f"%{filter_query.search}%"),
                Patient.other_names.ilike(f"%{filter_query.search}%"),
            )
        )

    if filter_query.start_date:
        stmt = stmt.where(
            Patient.created_at >= datetime.combine(filter_query.start_date, time.min)
        )

    if filter_query.end_date:
        stmt = stmt.where(
            Patient.created_at <= datetime.combine(filter_query.end_date, time.max)
        )

    # 3. Execute and Transform
    result = await db.execute(stmt)

    patients_out = []
    for patient, last_visit_date in result.all():
        # Convert DB model to Pydantic Schema
        p_dto = PatientOut.model_validate(patient)

        # Inject the prefixes into the private attributes
        p_dto._org_code = org_code
        p_dto._mod_prefix = pat_prefix

        # Manually attach the last_visit_date from the join
        p_dto.last_visit_date = last_visit_date

        patients_out.append(p_dto)

    return patients_out


@router.get("/search")
async def search_patients(
    q: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Patient)
        .where(
            or_(
                Patient.first_name.ilike(f"%{q}%"),
                Patient.surname.ilike(f"%{q}%"),
            )
        )
        .limit(5)
    )

    result = await db.execute(stmt)
    patients = result.scalars().all()

    return [
        {
            "id": p.id,
            "full_name": f"{p.first_name} {p.surname}",
            "phone": p.phone,
            "dob": p.date_of_birth,
        }
        for p in patients
    ]


@router.get("/{id}/", response_model=PatientOut)
async def get_patients(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Patient).where(Patient.id == id)

    result = await db.execute(stmt)

    result = result.scalar()
    if not result:
        raise HTTPException(detail="Resource not found", status_code=404)
    return result


@router.get("/{patient_id}/lab-results")
async def get_patient_lab_results(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Use a join to find results specifically belonging to this patient
    stmt = (
        select(LabResult)
        .join(LabResult.order_item)
        .join(LabOrderItem.order)
        .options(
            # Eagerly load the test name and category so the frontend can display them
            selectinload(LabResult.order_item).selectinload(LabOrderItem.test)
        )
        .where(LabOrder.patient_id == patient_id)
        .order_by(LabResult.received_at.desc())
    )

    result = await db.execute(stmt)
    lab_results = result.scalars().all()

    # Debugging: Print count to terminal to see if DB is actually returning rows
    print(f"DEBUG: Found {len(lab_results)} results for patient {patient_id}")

    return lab_results


@router.get(
    "/lab-results",
    response_model=list[LabResultResponse],
)
async def get_all_lab_results(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabResult)
        .options(
            selectinload(LabResult.sample),
            selectinload(LabResult.order_item),
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
