from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/", response_model=list[PaymentResponse])
async def get_all_transactions(
    filters: Annotated[PaymentFilterParams, Depends()],
    method: Annotated[Optional[List[str]], Query()] = None,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    try:
        # 1. Base query with optimized relationship loading
        stmt = (
            select(Payment)
            .join(Payment.invoice)
            .options(
                # Deep loading: Payment -> Invoice -> Patient
                selectinload(Payment.invoice).selectinload(Invoice.patient),
                selectinload(Payment.verified_by),
            )
            .order_by(Payment.received_at.desc())
        )

        # 2. Date Range & Invoice/Patient Filtering
        if filters.start_date:
            stmt = stmt.where(func.date(Payment.received_at) >= filters.start_date)
        if filters.end_date:
            stmt = stmt.where(func.date(Payment.received_at) <= filters.end_date)
        if filters.invoice_id:
            stmt = stmt.where(Payment.invoice_id == filters.invoice_id)
        if filters.patient_id:
            stmt = stmt.where(Invoice.patient_id == filters.patient_id)

        # 3. Multi-Method Filtering (Cash, Momo, etc.)
        if method:
            stmt = stmt.where(Payment.method.in_(method))
        elif filters.method:
            stmt = stmt.where(Payment.method == filters.method)

        # 4. Pagination & Execution
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        payments = result.scalars().all()

        return payments

    except Exception as e:
        print(f"Transaction Fetch Error: {e}")
        return []


@router.get("/invoices", response_model=list[InvoiceResponse])
async def get_all_invoices(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    try:
        # 1. Base query with deep loading to prevent N+1 issues
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.patient),
                selectinload(Invoice.items).selectinload(InvoiceItem.test),
                selectinload(Invoice.payments),
            )
            .order_by(Invoice.created_at.desc())
        )

        # 2. Date Range Filtering
        if start_date:
            stmt = stmt.where(func.date(Invoice.created_at) >= start_date)
        if end_date:
            stmt = stmt.where(func.date(Invoice.created_at) <= end_date)

        # 3. Status Filtering
        if status:
            stmt = stmt.where(Invoice.status.ilike(status))

        # 4. Execution
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        invoices = result.scalars().all()

        return invoices

    except Exception as e:
        print(f"Error fetching invoices: {e}")
        return []


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
