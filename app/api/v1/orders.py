from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import LabOrder, LabOrderItem, Test
from app.schemas import LabOrderCreate, LabOrderOut

router = APIRouter()

@router.post("", response_model=LabOrderOut)
async def create_order(payload: LabOrderCreate, db: AsyncSession = Depends(get_db)):
    tests = (await db.execute(select(Test).where(Test.id.in_(payload.test_ids)))).scalars().all()
    if len(tests) != len(payload.test_ids):
        raise HTTPException(status_code=400, detail="One or more tests not found")

    order = LabOrder(patient_id=payload.patient_id)
    db.add(order)
    await db.flush()

    for t in tests:
        item = LabOrderItem(order_id=order.id, test_id=t.id, analyzer_id=t.default_analyzer_id)
        db.add(item)

    await db.commit()
    await db.refresh(order)
    return order
