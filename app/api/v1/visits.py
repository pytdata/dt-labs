from datetime import datetime, timezone
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import Patient
from app.models.lab import Visit
from app.models.users import Department, User
from app.schemas import PatientCreate, PatientOut
from sqlalchemy import or_
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.schemas.visit import PaymentMode, UpdateVisit, VisitResponse, VisitStatus


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    department: str | None = None
    search: str | None = None
    status: VisitStatus | None = None


@router.get("/", response_model=list[VisitResponse])
async def get_all_visits(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Visit)
        .join(Visit.patient)
        .join(Visit.department)
        .join(Visit.doctor)
        .options(
            selectinload(Visit.patient),
            selectinload(Visit.department),
            selectinload(Visit.doctor),
        )
        .order_by(Visit.visit_date.desc())
    )

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    if filter_query.doctor:
        stmt = stmt.where(
            Visit.doctor.has(User.full_name.ilike(f"%{filter_query.doctor.strip()}%"))
        )

    if filter_query.patient:
        q = f"%{filter_query.patient.strip()}%"
        stmt = stmt.where(
            Visit.patient.has(
                or_(
                    Patient.first_name.ilike(q),
                    Patient.surname.ilike(q),
                    Patient.other_names.ilike(q),
                )
            )
        )

    if filter_query.department:
        stmt = stmt.where(
            Visit.department.has(
                Department.name.ilike(f"%{filter_query.department.strip()}%")
            )
        )

    if filter_query.status:
        stmt = stmt.where(Visit.status.in_([filter_query.status]))

    result = await db.execute(stmt)
    visits = result.scalars().all()

    return visits


@router.get("/{id}/", response_model=VisitResponse)
async def get_visit(id: int, db: AsyncSession = Depends(get_db)):
    """Get a visit object that matches the given id."""

    stmt = (
        select(Visit)
        .where(Visit.id == id)
        .join(Visit.patient)
        .join(Visit.department)
        .join(Visit.doctor)
        .options(
            selectinload(Visit.patient),
            selectinload(Visit.department),
            selectinload(Visit.doctor),
        )
        .order_by(Visit.visit_date.desc())
    )
    results = await db.execute(stmt)
    visits = results.scalar()

    return visits


@router.put("/{id}/")
async def update_visit(
    id: int,
    data: UpdateVisit,
    db: AsyncSession = Depends(get_db),
):
    visit_date_obj = datetime.strptime(data.visit_date, "%d-%m-%Y").replace(
        tzinfo=timezone.utc
    )
    time_of_visit_obj = (
        datetime.strptime(data.visit_time, "%H:%M").time().replace(tzinfo=timezone.utc)
    )

    stmt = select(Visit).where(Visit.id == id)
    result = await db.execute(stmt)
    visit_obj = result.scalar()
    if not visit_obj:
        raise HTTPException(detail="Resource not found", status_code=404)

    visit_obj.patient_id = data.patient_id
    visit_obj.department_id = data.department_id
    visit_obj.doctor_id = data.doctor_id
    visit_obj.visit_date = visit_date_obj
    visit_obj.reason = data.reason
    visit_obj.status = VisitStatus.pending
    visit_obj.mode_of_payment = data.payment_mode
    visit_obj.time_of_visit = time_of_visit_obj

    db.add(visit_obj)
    await db.commit()

    return {"message": "ok"}
