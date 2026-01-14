from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy import or_


from app.db.session import get_db
from app.models import Patient
from app.models.lab import Appointment
from app.models.users import Department, User


router = APIRouter()


class AppointmentStatus(str, Enum):
    upcoming = "upcoming"
    in_progress = "in_progress"
    completed = "completed"


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    department: str | None = None
    search: str | None = None
    status: AppointmentStatus | None = None


@router.get("/appointment")
async def get_all_appointment(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Appointment)
        .join(Appointment.patient)
        .join(Appointment.doctor)
        # .join(Appointment.created_by_user)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor),
            # selectinload(Appointment.created_by_user),
        )
        .order_by(Appointment.appointment_at.desc())
    )
    if filter_query.doctor:
        stmt = stmt.where(
            Appointment.doctor.has(
                User.full_name.ilike(f"%{filter_query.doctor.strip()}%")
            )
        )

    if filter_query.patient:
        q = f"%{filter_query.patient.strip()}%"
        stmt = stmt.where(
            Appointment.patient.has(
                or_(
                    Patient.first_name.ilike(q),
                    Patient.surname.ilike(q),
                    Patient.other_names.ilike(q),
                )
            )
        )

    if filter_query.department:
        stmt = stmt.where(
            Appointment.department.has(
                Department.name.ilike(f"%{filter_query.department.strip()}%")
            )
        )

    if filter_query.status:
        stmt = stmt.where(Appointment.status.in_([filter_query.status]))

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    result = await db.execute(stmt)
    appointment = result.scalars().all()

    return appointment
