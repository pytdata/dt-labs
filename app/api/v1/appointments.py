from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import or_


from app.db.session import get_db
from app.models import Patient, association
from app.models.billing import Invoice, InvoiceItem, Payment
from app.models.catalog import Phlebotomy, Priority, Sample, SampleStatus, Test
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult, Visit
from app.models.users import User
from app.schemas.appointment import (
    AppointmenCreate,
    AppointmentDetailResponse,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
    TestResponse,
)
from app.schemas.lab_results import LabResultStatus


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    patient_id: int | None = None
    department: str | None = None
    search: str | None = None
    status: AppointmentStatus | None = None


DEFAULT_PREFIX = "YKG"


async def _next_test_no(db: AsyncSession) -> str:
    max_id = (await db.execute(select(func.max(LabResult.id)))).scalar() or 0
    nxt = int(max_id) + 1
    return f"{DEFAULT_PREFIX}-TEST-{nxt:06d}"


@router.post("/")
async def create_appointment(
    data: AppointmenCreate,
    # current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        async with db.begin():
            # 1. Fetch Tests
            stmt = select(Test).where(Test.id.in_(data.test_ids))
            result = await db.execute(stmt)
            tests = result.scalars().all()
            print(f"DEBUG: Found tests: {tests}")

            if not tests:
                raise HTTPException(status_code=400, detail="No valid tests selected")

            total_amount = sum(t.price_ghs for t in tests)
            # Check if any test in this booking needs a needle
            requires_phlebotomy = any(t.requires_phlebotomy for t in tests)

            # 2. Create Appointment
            appointment = Appointment(
                patient_id=data.patient_id,
                doctor_id=data.doctor_id,
                notes=data.notes,
                mode_of_payment=data.mode_of_payment,
                total_price=total_amount,
                # ADD THIS LINE HERE:
                tests=tests,
            )
            db.add(appointment)
            await db.flush()

            # 3. Create Lab Order (The Clinical "Folder")
            order = LabOrder(
                patient_id=data.patient_id,
                appointment_id=appointment.id,
                status="pending",
            )
            db.add(order)
            await db.flush()

            # 4. Create Invoice (The Financial "Folder")
            invoice = Invoice(
                invoice_no=f"INV-{appointment.id}",
                patient_id=data.patient_id,
                appointment_id=appointment.id,
                total_amount=total_amount,
                amount_paid=data.total_price,
                balance=total_amount - data.total_price,
                # status="paid" if (total_amount - data.total_price) <= 0 else "unpaid",
                status="unpaid",
                payment_mode=data.mode_of_payment,
            )
            db.add(invoice)

            await db.flush()

            # 5. Process Tests into Items
            for test in tests:
                # Invoice Item (For billing)
                db.add(
                    InvoiceItem(
                        invoice_id=invoice.id,
                        test_id=test.id,
                        description=test.name,
                        unit_price=test.price_ghs,
                        qty=1,
                        line_total=test.price_ghs,
                    )
                )

                # Lab Order Item (The actual "Task")
                # Logic: If it's Radiology/Direct, it skips Phlebotomy status
                item_status = (
                    "awaiting_sample"
                    if test.requires_phlebotomy
                    else "awaiting_results"
                )

                order_item = LabOrderItem(
                    order_id=order.id, test_id=test.id, status=item_status
                )
                db.add(order_item)
                await db.flush()

            # 6. Payment Confirmation (Manual Momo/Cash)
            if data.total_price > 0:
                db.add(
                    Payment(
                        invoice_id=invoice.id,
                        amount=data.total_price,
                        method=data.mode_of_payment,
                        # verified_by_user_id=current_user.id,
                        description="Initial booking payment",
                    )
                )

        return {
            "status": "success",
            "appointment_id": appointment.id,
            "order_id": order.id,
        }

    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
            # selectinload(LabOrderItem.result),
        )
        .order_by(Appointment.appointment_at.desc())
    )

    if filter_query.patient_id:
        stmt = stmt.where(
            Appointment.patient.has(Patient.id == filter_query.patient_id)
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

    if filter_query.status:
        stmt = stmt.where(Appointment.status.in_([filter_query.status]))

    stmt = (
        stmt.limit(filter_query.limit)
        .offset(filter_query.offset)
        .order_by(Appointment.appointment_at.desc())
    )

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


@router.get("/{id}/", response_model=AppointmentDetailResponse)
async def get_appointment(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    print(id)
    stmt = (
        select(Appointment)
        .where(Appointment.id == id)
        .options(
            # selectinload is best for 1-to-N (tests)
            selectinload(Appointment.tests),
            # joinedload is often faster for 1-to-1 (patient, doctor)
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.created_by_user),
            joinedload(Appointment.invoice),
            joinedload(Appointment.lab_order),
        )
    )

    result = await db.execute(stmt)
    # Use .unique() if you have many-to-many relationships (like tests)
    # to avoid duplicate parent rows in the result set
    appointment = result.unique().scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


@router.patch("/{id}/", response_model=AppointmentDetailResponse)
async def partial_update_appointment(
    id: int,
    data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        async with db.begin():
            # 1. Fetch appointment with Tests and Invoice
            stmt = (
                select(Appointment)
                .where(Appointment.id == id)
                .options(
                    selectinload(Appointment.tests), joinedload(Appointment.invoice)
                )
            )
            result = await db.execute(stmt)
            appointment = result.unique().scalar_one_or_none()

            if not appointment:
                raise HTTPException(status_code=404, detail="Appointment not found")

            # 2. Update basic fields
            update_data = data.model_dump(exclude_unset=True, exclude={"test_ids"})
            for key, value in update_data.items():
                setattr(appointment, key, value)

            # 3. Synchronize Tests and Invoice
            if data.test_ids is not None:
                # Fetch the new test objects
                test_stmt = select(Test).where(Test.id.in_(data.test_ids))
                test_result = await db.execute(test_stmt)
                new_tests = test_result.scalars().all()

                # Update Appointment relationship
                appointment.tests = list(new_tests)

                # Calculate new total
                new_total = sum(t.price_ghs for t in new_tests)
                appointment.total_price = new_total

                # 4. Update the linked Invoice
                if appointment.invoice:
                    inv = appointment.invoice
                    inv.total_amount = new_total
                    inv.balance = new_total - inv.amount_paid

                    # Update status if the new total is now covered by previous payments
                    if inv.balance <= 0:
                        inv.status = "paid"
                    else:
                        inv.status = "unpaid"

                    # 5. Refresh InvoiceItems (Delete old, add new)
                    # This ensures the itemized bill matches the new tests
                    delete_stmt = delete(InvoiceItem).where(
                        InvoiceItem.invoice_id == inv.id
                    )
                    await db.execute(delete_stmt)

                    for test in new_tests:
                        db.add(
                            InvoiceItem(
                                invoice_id=inv.id,
                                test_id=test.id,
                                description=test.name,
                                unit_price=test.price_ghs,
                                qty=1,
                                line_total=test.price_ghs,
                            )
                        )

            await db.flush()
            # Commit the transaction so data is persisted
            # await db.commit() # Only if not using 'async with db.begin()'

            # RE-FETCH WITH EAGER LOADING
            stmt = (
                select(Appointment)
                .where(Appointment.id == id)
                .options(
                    joinedload(Appointment.patient),
                    joinedload(Appointment.doctor),
                    joinedload(Appointment.invoice),
                    joinedload(Appointment.lab_order),
                    selectinload(Appointment.tests),
                )
            )
            result = await db.execute(stmt)
            appointment = result.unique().scalar_one_or_none()

            return appointment

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
