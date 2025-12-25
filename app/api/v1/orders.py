from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.db.session import get_db
from app.models import LabOrder, LabOrderItem, Test, LabResult
from app.schemas import (
    LabOrderCreate,
    LabOrderOut,
    SampleCollectIn,
    SampleOut,
    LabResultIn,
    LabResultOut,
)
from app.services.sample_service import generate_sample_id

router = APIRouter()

@router.post("", response_model=LabOrderOut)
async def create_order(payload: LabOrderCreate, db: AsyncSession = Depends(get_db)):
    tests = (await db.execute(select(Test).where(Test.id.in_(payload.test_ids)))).scalars().all()
    if len(tests) != len(payload.test_ids):
        raise HTTPException(status_code=400, detail="One or more tests not found")

    order = LabOrder(patient_id=payload.patient_id, sample_id=generate_sample_id())
    db.add(order)
    await db.flush()

    for t in tests:
        item = LabOrderItem(order_id=order.id, test_id=t.id, analyzer_id=t.default_analyzer_id, sample_id=order.sample_id)
        db.add(item)

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/sample", response_model=SampleOut)
async def ensure_sample(order_id: int, db: AsyncSession = Depends(get_db)):
    """Ensure a LabOrder has a sample id and propagate to items."""
    order = (await db.execute(select(LabOrder).where(LabOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.sample_id:
        order.sample_id = generate_sample_id()
    items = (await db.execute(select(LabOrderItem).where(LabOrderItem.order_id == order.id))).scalars().all()
    for it in items:
        it.sample_id = it.sample_id or order.sample_id

    await db.commit()
    await db.refresh(order)
    return SampleOut(order_id=order.id, sample_id=order.sample_id)


@router.post("/{order_id}/sample/collect", response_model=SampleOut)
async def mark_sample_collected(order_id: int, payload: SampleCollectIn, db: AsyncSession = Depends(get_db)):
    order = (await db.execute(select(LabOrder).where(LabOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.sample_id:
        order.sample_id = generate_sample_id()

    order.sample_collected_at = payload.collected_at or datetime.utcnow()
    order.collected_by_user_id = payload.collected_by_user_id
    order.sample_notes = payload.note

    items = (await db.execute(select(LabOrderItem).where(LabOrderItem.order_id == order.id))).scalars().all()
    for it in items:
        it.sample_id = it.sample_id or order.sample_id

    await db.commit()
    await db.refresh(order)
    return SampleOut(order_id=order.id, sample_id=order.sample_id)


@router.post("/items/{item_id}/results", response_model=LabResultOut)
async def add_result(item_id: int, payload: LabResultIn, db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(LabOrderItem).where(LabOrderItem.id == item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    order = item.order
    if not order and item.order_id:
        order = (await db.execute(select(LabOrder).where(LabOrder.id == item.order_id))).scalar_one_or_none()

    sample_id = item.sample_id or (order.sample_id if order else None) or generate_sample_id()

    lr = LabResult(
        order_item_id=item.id,
        analyzer_id=item.analyzer_id,
        sample_id=sample_id,
        source="manual",
        status=payload.status,
        results=payload.results,
        comments=payload.comments,
        raw_format="manual",
    )
    if payload.status == "verified":
        lr.verified_at = datetime.utcnow()
    db.add(lr)
    await db.commit()
    await db.refresh(lr)
    return lr


@router.post("/results/{result_id}/verify", response_model=LabResultOut)
async def verify_result(result_id: int, db: AsyncSession = Depends(get_db)):
    lr = (await db.execute(select(LabResult).where(LabResult.id == result_id))).scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=404, detail="Result not found")
    lr.status = "verified"
    lr.verified_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lr)
    return lr
