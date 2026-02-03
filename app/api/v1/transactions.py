from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from app.models.billing import Invoice, InvoiceItem, Payment
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


from app.models.lab import LabOrder, LabOrderItem
from app.schemas.payment import (
    GenerateInvoicePayload,
    InvoiceResponse,
    PaymentFilterParams,
    PaymentResponse,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[PaymentResponse],
)
async def get_all_transactions(
    filters: Annotated[PaymentFilterParams, Depends()],
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Payment)
        .join(Payment.invoice)
        .options(
            selectinload(Payment.invoice).selectinload(Invoice.patient),
            selectinload(Payment.verified_by),
        )
        .order_by(Payment.received_at.desc())
    )

    if filters.invoice_id:
        stmt = stmt.where(Payment.invoice_id == filters.invoice_id)

    if filters.patient_id:
        stmt = stmt.where(Invoice.patient_id == filters.patient_id)

    if filters.method:
        stmt = stmt.where(Payment.method == filters.method)

    result = await db.execute(stmt)
    payments = result.scalars().all()

    return payments


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
)
async def get_all_invoices(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.patient),
            selectinload(Invoice.items).selectinload(InvoiceItem.test),
            selectinload(Invoice.payments),
        )
        .order_by(Invoice.created_at.desc())
    )

    result = await db.execute(stmt)
    invoices = result.scalars().all()

    return invoices


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
)
async def get_invoice_details(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.patient),
            selectinload(Invoice.items).selectinload(InvoiceItem.test),
            selectinload(Invoice.payments),
        )
    )

    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.post(
    "/invoices/",
    status_code=status.HTTP_201_CREATED,
    response_model=InvoiceResponse,
)
async def generate_invoice(
    payload: GenerateInvoicePayload,
    db: AsyncSession = Depends(get_db),
):
    # ---- Fetch order with items ----
    stmt = (
        select(LabOrder)
        .where(LabOrder.id == payload.order_id)
        .options(
            selectinload(LabOrder.items).selectinload(LabOrderItem.test),
            selectinload(LabOrder.patient),
        )
    )

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    if not order.items:
        raise HTTPException(status_code=400, detail="Order has no tests")

    # ---- Create invoice ----
    invoice = Invoice(
        invoice_no=f"INV-{uuid4().hex[:8].upper()}",
        patient_id=order.patient_id,
        order_id=order.id,
        payment_mode=payload.payment_mode,
        notes=payload.notes,
    )

    db.add(invoice)
    await db.flush()  # get invoice.id

    total_amount = Decimal("0.00")

    # ---- Create invoice items ----
    for item in order.items:
        price = Decimal(item.test.price_ghs or 0)

        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            test_id=item.test_id,
            description=item.test.name,
            unit_price=price,
            qty=1,
            line_total=price,
        )

        total_amount += price
        db.add(invoice_item)

    # ---- Finalize totals ----
    invoice.total_amount = total_amount
    invoice.amount_paid = Decimal("0.00")
    invoice.balance = total_amount
    invoice.status = "unpaid"

    await db.commit()

    # ---- Reload with relationships ----
    await db.refresh(invoice)

    return invoice
