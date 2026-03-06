from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, func, select, update
from sqlalchemy.orm import contains_eager, selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.appointment import TestResponse
from app.schemas.lab import LabOrderItemResponse, LabQueueResponse


router = APIRouter()


class DepartmentType(str, Enum):
    radiology = "radiology"
    phlebotomy = "phlebotomy"


class PhlebotomyStatus(str, Enum):
    awaiting_sample = "awaiting_sample"
    awaiting_results = "awaiting_results"
    in_progress = "in_progress"


@router.get("/queue/{dept}", response_model=list[LabQueueResponse])
async def get_lab_queue(dept: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        # Use outerjoin because Phlebotomy might not exist yet
        .outerjoin(Appointment.phlebotomy)
        .options(
            contains_eager(LabOrderItem.test),
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .contains_eager(Appointment.patient),
            # Load the phlebotomy record into the appointment object
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .contains_eager(Appointment.phlebotomy),
        )
    )

    if dept == DepartmentType.phlebotomy:
        # Only tests that need a needle
        stmt = stmt.where(Test.requires_phlebotomy == True)  # noqa: E712
    else:
        # Radiology / Laboratory Investigations that don't need a sample
        stmt = stmt.where(Test.requires_phlebotomy == False)  # noqa: E712

    # Only show items that aren't finished yet
    stmt = stmt.where(
        LabOrderItem.status.in_(
            [
                PhlebotomyStatus.awaiting_sample,
                # PhlebotomyStatus.awaiting_results,
                PhlebotomyStatus.in_progress,
            ]
        )
    )

    result = await db.execute(stmt)
    return result.unique().scalars().all()


@router.get(
    "/appointments/{appointment_id}/pending-items",
    response_model=list[LabOrderItemResponse],
)
async def get_pending_lab_items(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.order)  # Join the Order table
        .join(LabOrderItem.test)  # Join the Test table
        .where(
            # Filter via the joined Order table
            LabOrder.appointment_id == appointment_id,
            LabOrderItem.status == "awaiting_sample",
            Test.requires_phlebotomy == True,
        )
        .options(selectinload(LabOrderItem.test))
    )

    result = await db.execute(stmt)
    return result.scalars().all()
