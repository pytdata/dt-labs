from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import Patient
from app.models.lab import LabOrder, LabOrderItem, LabResult, Visit
from app.models.users import User
from app.schemas import PatientCreate, PatientOut
from sqlalchemy import or_
from sqlalchemy import func, select
from sqlalchemy import select
from sqlalchemy.orm import selectinload


from typing import Annotated, Literal


from pydantic import BaseModel, Field

from app.schemas.lab_results import LabResultResponse
from app.web.dependency import get_current_user

router = APIRouter()

DEFAULT_PREFIX = "YGK"  # can be moved to Settings table later


async def _next_patient_no(db: AsyncSession) -> str:
    max_id = (await db.execute(select(func.max(Patient.id)))).scalar() or 0
    nxt = int(max_id) + 1
    return f"{DEFAULT_PREFIX}-PT-{nxt:06d}"


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


@router.get("", response_model=list[PatientOut])
async def list_patients(
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
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
    result = await db.execute(stmt)

    patients = []
    for patient, last_visit_date in result.all():
        patient.last_visit_date = last_visit_date
        patients.append(patient)

    return patients

    # return (await db.execute(stmt)).scalars().all()


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
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    stmt = (
        select(LabResult)
        .join(LabOrderItem, LabResult.order_item_id == LabOrderItem.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .where(LabOrder.patient_id == patient_id)
        .order_by(LabResult.received_at.desc())
    )

    result = await db.execute(stmt)
    lab_results = result.scalars().all()

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
