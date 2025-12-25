from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_db
from app.models import Invoice, Payment, LabOrder, Patient

router = APIRouter()


@router.get("/accounting")
async def accounting_report(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Simple accounting report: totals for invoices and payments."""
    inv_conditions = []
    pay_conditions = []
    if start:
        inv_conditions.append(Invoice.created_at >= start)
        pay_conditions.append(Payment.received_at >= start)
    if end:
        inv_conditions.append(Invoice.created_at <= end)
        pay_conditions.append(Payment.received_at <= end)

    inv_q = select(
        func.coalesce(func.sum(Invoice.total_amount), 0),
        func.coalesce(func.sum(Invoice.amount_paid), 0),
        func.coalesce(func.sum(Invoice.balance), 0),
        func.count(Invoice.id),
    )
    pay_q = select(
        func.coalesce(func.sum(Payment.amount), 0),
        func.count(Payment.id),
    )
    if inv_conditions:
        inv_q = inv_q.where(and_(*inv_conditions))
    if pay_conditions:
        pay_q = pay_q.where(and_(*pay_conditions))

    inv_totals = (await db.execute(inv_q)).first()
    pay_totals = (await db.execute(pay_q)).first()

    return {
        "invoice_total": float(inv_totals[0]) if inv_totals else 0,
        "amount_paid": float(inv_totals[1]) if inv_totals else 0,
        "balance": float(inv_totals[2]) if inv_totals else 0,
        "invoice_count": int(inv_totals[3]) if inv_totals else 0,
        "payments_total": float(pay_totals[0]) if pay_totals else 0,
        "payment_count": int(pay_totals[1]) if pay_totals else 0,
    }


@router.get("/hospital-referrals")
async def hospital_referrals(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Extract orders for hospital referral use (patient + sample IDs)."""
    stmt = (
        select(
            LabOrder.id,
            LabOrder.sample_id,
            LabOrder.created_at,
            Patient.patient_no,
            Patient.first_name,
            Patient.surname,
        )
        .join(Patient, LabOrder.patient_id == Patient.id)
    )
    if start:
        stmt = stmt.where(LabOrder.created_at >= start)
    if end:
        stmt = stmt.where(LabOrder.created_at <= end)

    rows = (await db.execute(stmt.order_by(LabOrder.created_at.desc()))).all()
    return [
        {
            "order_id": r.id,
            "sample_id": r.sample_id,
            "created_at": r.created_at,
            "patient_no": r.patient_no,
            "patient_name": f"{r.first_name} {r.surname}",
        }
        for r in rows
    ]
