from datetime import date
from typing import Annotated, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy import extract


from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from app.models.billing import Invoice, InvoiceItem, Payment
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from dateutil.relativedelta import relativedelta


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
    db: AsyncSession = Depends(get_db),
    # Use = Query(None) to handle multiple checkbox values and avoid Annotated conflicts
    method: Optional[List[str]] = Query(None),
    status: Optional[List[str]] = Query(None),
    limit: int = 100,
    offset: int = 0,
):
    try:
        # 1. Base query with optimized relationship loading
        # We join Invoice so we can filter by Invoice.status and Invoice.patient_id
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

        # 2. Date Range & ID Filtering
        if filters.start_date:
            stmt = stmt.where(func.date(Payment.received_at) >= filters.start_date)

        if filters.end_date:
            stmt = stmt.where(func.date(Payment.received_at) <= filters.end_date)

        if filters.invoice_id:
            stmt = stmt.where(Payment.invoice_id == filters.invoice_id)

        if filters.patient_id:
            stmt = stmt.where(Invoice.patient_id == filters.patient_id)

        # 3. Multi-Method Filtering (from query params: ?method=cash&method=momo)
        if method:
            stmt = stmt.where(Payment.method.in_(method))

        # 4. Status Filtering (from query params: ?status=paid&status=unpaid)
        # We filter based on the status field in the Invoice table
        if status:
            stmt = stmt.where(Invoice.status.in_(status))

        # 5. Pagination & Execution
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        payments = result.scalars().all()

        return payments

    except Exception as e:
        # It's better to log this properly in production
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


@router.get("/summary")
async def get_invoice_summary(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    this_month_start = datetime(now.year, now.month, 1)
    last_month_start = this_month_start - relativedelta(months=1)
    last_month_end = this_month_start - timedelta(seconds=1)

    # 1. Total Invoice Amount (All time)
    total_stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0))
    total_res = await db.execute(total_stmt)
    total_all_time = total_res.scalar()

    # 2. Current Month Revenue
    current_month_stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        Invoice.created_at >= this_month_start
    )
    current_month_res = await db.execute(current_month_stmt)
    current_month_total = current_month_res.scalar()

    # 3. Last Month Revenue (for % change)
    last_month_stmt = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        and_(
            Invoice.created_at >= last_month_start, Invoice.created_at <= last_month_end
        )
    )
    last_month_res = await db.execute(last_month_stmt)
    last_month_total = last_month_res.scalar()

    # 4. Calculate Percentage Change
    pct_change = 0
    if last_month_total > 0:
        pct_change = ((current_month_total - last_month_total) / last_month_total) * 100

    return {
        "total_all_time": float(total_all_time),
        "this_month": float(current_month_total),
        "percentage_change": round(pct_change, 2),
        "is_up": pct_change >= 0,
    }


@router.get("/stats")
async def get_transaction_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()

    today_start = datetime(now.year, now.month, now.day)
    this_month_start = datetime(now.year, now.month, 1)

    # helper for date ranges
    async def get_sum(start_date, end_date=None):
        query = select(func.coalesce(func.sum(Payment.amount), 0))
        if end_date:
            query = query.where(
                and_(Payment.received_at >= start_date, Payment.received_at <= end_date)
            )
        else:
            query = query.where(Payment.received_at >= start_date)

        # Await the execution
        result = await db.execute(query)
        return result.scalar()

    # Calculate all stats
    total_res = await db.execute(select(func.coalesce(func.sum(Payment.amount), 0)))

    stats = {
        "total_all_time": total_res.scalar(),
        "today": await get_sum(today_start),
        "this_week": await get_sum(today_start - timedelta(days=now.weekday())),
        "this_month": await get_sum(this_month_start),
    }

    return stats


@router.get("/stats/monthly")
async def get_monthly_transaction_stats(
    year: int = Query(default=2026), db: AsyncSession = Depends(get_db)
):
    # Group by month and sum the payment amounts
    stmt = (
        select(
            extract("month", Payment.received_at).label("month"),
            func.sum(Payment.amount).label("total"),
        )
        .where(extract("year", Payment.received_at) == year)
        .group_by(extract("month", Payment.received_at))
        .order_by("month")
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Create a list of 12 zeros and fill in the months that have data
    monthly_totals = [0.0] * 12
    for row in rows:
        month_index = int(row.month) - 1  # SQL months are 1-12
        monthly_totals[month_index] = float(row.total)

    return monthly_totals
