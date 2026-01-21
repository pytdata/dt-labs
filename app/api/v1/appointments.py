from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy import or_


from app.db.session import get_db
from app.models import Patient
from app.models.catalog import Test
from app.models.lab import Appointment
from app.models.users import User
from app.schemas.appointment import (
    AppointmenCreate,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
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
    status: AppointmentStatus | None = None


@router.get("/", response_model=list[AppointmentResponse])
async def get_all_appointments(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Appointment)
        .join(Appointment.patient)
        .join(Appointment.doctor)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor),
            selectinload(Appointment.tests),
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

    # if filter_query.department:
    #     stmt = stmt.where(
    #         Appointment.department.has(
    #             Department.name.ilike(f"%{filter_query.department.strip()}%")
    #         )
    #     )

    if filter_query.status:
        stmt = stmt.where(Appointment.status.in_([filter_query.status]))

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    result = await db.execute(stmt)
    appointment = result.scalars().all()

    return appointment


@router.put(
    "/{appointment_id}/",
    status_code=status.HTTP_200_OK,
    response_model=AppointmentResponse,
)
async def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor),
            selectinload(Appointment.tests),
        )
    )

    appointment = await db.scalar(stmt)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    data = payload.model_dump(exclude_unset=True)

    # Update scalar fields
    for field, value in data.items():
        if field not in {"test_ids", "end_time"}:
            setattr(appointment, field, value)

    # Conditional end_time logic
    if "status" in data and data["status"] == AppointmentStatus.completed:
        if appointment.end_time is None:
            appointment.end_time = datetime.now(timezone.utc).time()

    # Update tests (many-to-many)
    if payload.test_ids is not None:
        tests = await db.scalars(select(Test).where(Test.id.in_(payload.test_ids)))
        appointment.tests = tests.all()

    await db.commit()

    await db.refresh(appointment)

    return appointment


@router.get("/{id}/")
async def get_appointment(
    id: int,
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .where(Appointment.id == id)
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

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    result = await db.execute(stmt)
    appointment = result.scalar()

    return appointment


@router.delete(
    "/{appointment_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = await db.scalar(stmt)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    await db.delete(appointment)
    await db.commit()

    return None


@router.post("/")
async def create_appointment(
    data: AppointmenCreate, db: AsyncSession = Depends(get_db)
):
    # fetch all selected tests
    stmt = select(Test).where(Test.id.in_(data.test_ids))
    result = await db.execute(stmt)
    tests = result.scalars().all()

    if not tests:
        raise HTTPException(status_code=400, detail="No valid tests selected")

    # convert date to utc
    # appointment_at_utc = datetime.strptime(data.appointment_at, "%Y-%m-%d").replace(
    #     tzinfo=timezone.utc
    # )

    # start_time = datetime.strptime(data.start_time, "%H:%M").time()
    # end_time = datetime.strptime(data.end_time, "%H:%M").time()

    # create appointment
    appointment = Appointment(
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        notes=data.notes,
        mode_of_payment=data.mode_of_payment,
        tests=tests,
    )

    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    return {"message": "ok"}
