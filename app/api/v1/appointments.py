from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, List, Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import or_


from app.core.deps import get_current_user
from app.core.rbac import PermissionChecker
from app.db.session import get_db
from app.models import Patient
from app.models.billing import Billing, BillingItem, Invoice, InvoiceItem
from app.models.catalog import Test
from app.models.company import OrganizationPrefix
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult
from app.models.users import User
from app.schemas.appointment import (
    AppointmenCreate,
    AppointmentDetailResponse,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)


router = APIRouter()


class FilterParams(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    patient_id: int | None = None
    department: str | None = None
    search: str | None = None
    status: AppointmentStatus | None = None


@router.post(
    "/",
    dependencies=[Depends(PermissionChecker("appointments", "write"))],
)
async def create_appointment(
    data: AppointmenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Use begin_nested() to create a Savepoint
        async with db.begin_nested():
            # 1. Fetch Tests to calculate totals
            stmt = select(Test).where(Test.id.in_(data.test_ids))
            result = await db.execute(stmt)
            tests = result.scalars().all()

            if not tests:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid tests selected",
                )

            total_billable_amount = sum(t.price_ghs for t in tests)

            # Create Appointment
            appointment = Appointment(
                patient_id=data.patient_id,
                doctor_id=data.doctor_id,
                notes=data.notes,
                mode_of_payment=data.mode_of_payment,
                total_price=total_billable_amount,
                tests=tests,
                created_by_user_id=current_user.id,
            )
            db.add(appointment)
            await db.flush()

            # Create Lab Order
            order = LabOrder(
                patient_id=data.patient_id,
                appointment_id=appointment.id,
                status="pending",
                created_by_id=current_user.id,
            )
            db.add(order)
            await db.flush()

            # Create Billing Record
            billing = Billing(
                bill_no=f"BIL-{appointment.id}-{datetime.now().strftime('%M%S')}",
                patient_id=data.patient_id,
                appointment_id=appointment.id,
                total_billed=total_billable_amount,
                created_by_id=current_user.id,
            )
            db.add(billing)
            await db.flush()

            #  Create Master Invoice
            invoice = Invoice(
                invoice_no=f"INV-{appointment.id}-{datetime.now().strftime('%M%S')}",
                patient_id=data.patient_id,
                appointment_id=appointment.id,
                order_id=order.id,
                total_amount=total_billable_amount,
                amount_paid=0,
                balance=total_billable_amount,
                status="unpaid",
                payment_mode=data.mode_of_payment,
                created_by_id=current_user.id,
            )
            db.add(invoice)
            await db.flush()

            # Process Tests
            for test in tests:
                order_item = LabOrderItem(
                    order_id=order.id,
                    test_id=test.id,
                    status=LabStatus.AWAITING_PAYMENT,
                    stage=LabStage.BOOKING,
                )
                db.add(order_item)
                await db.flush()

                db.add(
                    BillingItem(
                        billing_id=billing.id,
                        test_id=test.id,
                        test_name=test.name,
                        price_at_booking=test.price_ghs,
                    )
                )

                db.add(
                    InvoiceItem(
                        invoice_id=invoice.id,
                        test_id=test.id,
                        lab_order_item_id=order_item.id,
                        description=test.name,
                        unit_price=test.price_ghs,
                        qty=1,
                        line_total=test.price_ghs,
                        is_paid=False,
                    )
                )

        # Explicitly commit the main transaction after the nested block succeeds
        await db.commit()

        return {
            "status": "success",
            "message": "Appointment, Billing, and Invoice created successfully.",
            "appointment_id": appointment.id,
            "bill_id": billing.id,
            "invoice_id": invoice.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()  # Rollback on any unexpected failure
        print(f"TRANSACTION ERROR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System failed to process the appointment transaction.",
        )


@router.get(
    "/",
    response_model=List[AppointmentResponse],
    dependencies=[Depends(PermissionChecker("appointments", "read"))],
)
async def get_all_appointments(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    """
    Fetch all appointments with comprehensive filtering and prefix injection.
    Requires 'appointments:read' permission.
    """
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    # Defaults if settings haven't been configured yet
    org_code = settings.org_identifier if settings else "YKG"
    apt_prefix = settings.appointment if settings else "APT"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Build Appointment Query
    stmt = (
        select(Appointment)
        .join(Appointment.patient)
        .join(Appointment.doctor)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor),
            selectinload(Appointment.tests),
            selectinload(Appointment.invoice),
        )
    )

    # --- Apply Filters ---
    if filter_query.start_date and filter_query.end_date:
        stmt = stmt.where(
            func.date(Appointment.appointment_at).between(
                filter_query.start_date, filter_query.end_date
            )
        )
    elif filter_query.start_date:
        stmt = stmt.where(
            func.date(Appointment.appointment_at) >= filter_query.start_date
        )
    elif filter_query.end_date:
        stmt = stmt.where(
            func.date(Appointment.appointment_at) <= filter_query.end_date
        )

    if filter_query.patient_id:
        stmt = stmt.where(Appointment.patient_id == filter_query.patient_id)

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
        stmt = stmt.where(Appointment.status == filter_query.status)

    # Pagination and Ordering
    stmt = (
        stmt.order_by(Appointment.appointment_at.desc())
        .limit(filter_query.limit)
        .offset(filter_query.offset)
    )

    # 3. Execute and Transform
    result = await db.execute(stmt)
    appointments = result.scalars().all()

    appointments_out = []
    for appt in appointments:
        # Convert to Pydantic (Uses the field_validator we added to UserResponse earlier)
        a_dto = AppointmentResponse.model_validate(appt)

        # Inject Appointment Prefixes for computed display_id
        a_dto._org_code = org_code
        a_dto._mod_prefix = apt_prefix

        # Inject Patient Prefixes into the nested patient object for its display_id
        if a_dto.patient:
            a_dto.patient._org_code = org_code
            a_dto.patient._mod_prefix = pat_prefix

        appointments_out.append(a_dto)

    return appointments_out


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


@router.get(
    "/{id}/",
    response_model=AppointmentDetailResponse,
    dependencies=[Depends(PermissionChecker("appointments", "read"))],
)
async def get_appointment(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full details of a single appointment including invoice items and lab orders.
    Requires 'appointments:read' permission.
    """
    # 1. Fetch Global Prefix Settings
    prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    prefix_res = await db.execute(prefix_stmt)
    settings = prefix_res.scalar_one_or_none()

    org_code = settings.org_identifier if settings else "YKG"
    apt_prefix = settings.appointment if settings else "APT"
    pat_prefix = settings.patient if settings else "PAT"

    # 2. Build Detailed Query
    stmt = (
        select(Appointment)
        .where(Appointment.id == id)
        .options(
            selectinload(Appointment.tests),
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.created_by_user),
            # Nested eager loading for invoice items
            joinedload(Appointment.invoice).selectinload(Invoice.items),
            joinedload(Appointment.lab_order),
        )
    )

    result = await db.execute(stmt)
    # Using .unique() is required when using joinedload on collections (like invoice items)
    appointment = result.unique().scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    # 3. Transform and Inject Prefixes
    # This ensures both the Appointment and Patient display IDs are correctly formatted
    a_dto = AppointmentDetailResponse.model_validate(appointment)

    # Inject Appointment Prefix
    a_dto._org_code = org_code
    a_dto._mod_prefix = apt_prefix

    # Inject Patient Prefix into the nested patient object
    if a_dto.patient:
        a_dto.patient._org_code = org_code
        a_dto.patient._mod_prefix = pat_prefix

    return a_dto


@router.patch(
    "/{id}/",
    response_model=AppointmentDetailResponse,
    dependencies=[Depends(PermissionChecker("appointments", "write"))],
)
async def partial_update_appointment(
    id: int,
    data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        # 1. Fetch Global Prefix Settings
        prefix_stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
        prefix_res = await db.execute(prefix_stmt)
        settings = prefix_res.scalar_one_or_none()

        org_code = settings.org_identifier if settings else "YKG"
        apt_prefix = settings.appointment if settings else "APT"
        pat_prefix = settings.patient if settings else "PAT"

        # USE begin_nested() instead of begin() to avoid the "already begun" error
        async with db.begin_nested():
            # 2. Fetch appointment with Tests and Invoice
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Appointment not found",
                )

            # 3. Update basic fields
            update_data = data.model_dump(exclude_unset=True, exclude={"test_ids"})
            for key, value in update_data.items():
                setattr(appointment, key, value)

            # 4. Synchronize Tests and Invoice
            if data.test_ids is not None:
                test_stmt = select(Test).where(Test.id.in_(data.test_ids))
                test_result = await db.execute(test_stmt)
                new_tests = test_result.scalars().all()

                appointment.tests = list(new_tests)
                new_total = sum(t.price_ghs for t in new_tests)
                appointment.total_price = new_total

                if appointment.invoice:
                    inv = appointment.invoice
                    inv.total_amount = new_total
                    inv.balance = new_total - inv.amount_paid
                    inv.status = "paid" if inv.balance <= 0 else "unpaid"

                    # Sync InvoiceItems
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

            # Flush changes within the savepoint
            await db.flush()

        # 5. COMMIT AND RE-FETCH
        # Commit the session transaction after the nested block succeeds
        await db.commit()

        # Re-fetch with full eager loading for the final response
        stmt = (
            select(Appointment)
            .where(Appointment.id == id)
            .options(
                joinedload(Appointment.patient),
                joinedload(Appointment.doctor),
                joinedload(Appointment.invoice).selectinload(Invoice.items),
                joinedload(Appointment.lab_order),
                selectinload(Appointment.tests),
            )
        )
        result = await db.execute(stmt)
        appointment = result.unique().scalar_one_or_none()

        # 6. Transform and Inject Prefixes
        a_dto = AppointmentDetailResponse.model_validate(appointment)
        a_dto._org_code = org_code
        a_dto._mod_prefix = apt_prefix

        if a_dto.patient:
            a_dto.patient._org_code = org_code
            a_dto.patient._mod_prefix = pat_prefix

        return a_dto

    except HTTPException:
        # Don't wrap 404s in 500s
        raise
    except Exception as e:
        await db.rollback()
        print(f"Update Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update appointment transaction.",
        )


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
