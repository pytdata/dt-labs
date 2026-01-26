from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.catalog import Sample, Test
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.sample import SampleCreate, SampleResponse


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    department: str | None = None
    search: str | None = None
    # status: AppointmentStatus | None = None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_sample(
    payload: SampleCreate,
    db: AsyncSession = Depends(get_db),
):
    # ensure appointment exists
    appointment = await db.get(Appointment, payload.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # create a labOrder
    lab_order = LabOrder(
        patient_id=payload.patient_id, appointment_id=payload.appointment_id
    )
    db.add(lab_order)
    await db.commit()
    await db.refresh(lab_order)

    # create a laborderItem
    lab_order_items = []
    for test_id in payload.test_requested:
        test_exisit = await db.get(Test, test_id)
        if not test_exisit:
            raise HTTPException(detail="Test not found", status_code=404)

        lab_order_item = LabOrderItem(order_id=lab_order.id, test_id=test_id)
        lab_order_items.append(lab_order_item)

    db.add_all(lab_order_items)
    await db.commit()
    # await db.refresh(lab_order_items)

    sample = Sample(
        sample_type=payload.sample_type,
        appointment_id=payload.appointment_id,
        patient_id=payload.patient_id,
        test_requested=payload.test_requested,
        priority=payload.priority,
        storage_location=payload.storage_location,
        # collector_id=payload.collector_id,
        collection_site=payload.collection_site,
        sample_condition=payload.sample_condition,
        status=payload.status,
    )

    db.add(sample)
    await db.commit()
    await db.refresh(sample)

    return {
        "message": "Sample created successfully",
        "data": sample,
    }


@router.get("/", summary="Get all samples", response_model=list[SampleResponse])
async def get_all_samples(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Sample)
        .options(
            selectinload(Sample.sample_category),
            # selectinload(Sample.collector),
        )
        .order_by(Sample.collection_date.desc())
    )

    result = await db.execute(stmt)

    samples = result.scalars().all()

    return samples
