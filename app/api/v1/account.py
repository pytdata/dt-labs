from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.db.session import get_db
from app.models.billing import Invoice
from app.models.catalog import Test
from app.models.lab import LabOrderItem


router = APIRouter()


@router.get("/reports/financial-summary")
async def get_financial_summary(db: AsyncSession = Depends(get_db)):
    # Query to get daily totals for the last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)

    stmt = (
        select(
            func.date(Invoice.created_at).label("date"),
            func.sum(Invoice.total_amount).label("total_expected"),
            func.sum(Invoice.amount_paid).label("total_collected"),
        )
        .where(Invoice.created_at >= seven_days_ago)
        .group_by(func.date(Invoice.created_at))
        .order_by(func.date(Invoice.created_at))
    )

    result = await db.execute(stmt)
    data = result.all()

    return {
        "labels": [row.date.strftime("%d %b") for row in data],
        "expected": [float(row.total_expected) for row in data],
        "collected": [float(row.total_collected) for row in data],
    }


@router.get("/reports/data")
async def get_report_data(type: str, db: AsyncSession = Depends(get_db)):
    if type == "revenue":
        # Financial Trend (Daily Collection)
        stmt = (
            select(
                func.date(Invoice.created_at).label("label"),
                func.sum(Invoice.amount_paid).label("collected"),
            )
            .group_by(func.date(Invoice.created_at))
            .order_by(func.date(Invoice.created_at))
            .limit(7)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return {
            "type": "line",
            "labels": [r.label.strftime("%d %b") for r in rows],
            "datasets": [
                {"label": "Revenue (GHS)", "data": [float(r.collected) for r in rows]}
            ],
        }

    elif type == "workload":
        # Department Split (Who is busiest?)
        stmt = (
            select(Test.test_category, func.count(LabOrderItem.id))
            .join(Test, LabOrderItem.test_id == Test.id)
            .group_by(Test.test_category)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return {
            "type": "doughnut",
            "labels": [r[0] for r in rows],
            "datasets": [{"label": "Total Tests", "data": [r[1] for r in rows]}],
        }

    elif type == "status":
        # Efficiency: Completion Rates
        stmt = select(LabOrderItem.status, func.count(LabOrderItem.id)).group_by(
            LabOrderItem.status
        )
        result = await db.execute(stmt)
        rows = result.all()
        # Maps the Enum values to human-readable labels
        return {
            "type": "bar",
            "labels": [str(r[0]).replace("_", " ") for r in rows],
            "datasets": [{"label": "Number of Tests", "data": [r[1] for r in rows]}],
        }
