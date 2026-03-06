from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Enum, func, select, update
from sqlalchemy.orm import contains_eager, selectinload

from app.db.session import get_db
from app.models.catalog import Phlebotomy, Test
from app.models.enums import LabStage
from app.models.lab import Appointment, LabOrder, LabOrderItem
from app.schemas.appointment import TestResponse
from app.schemas.lab import LabOrderItemResponse, LabQueueResponse, LabQueueResponse2


router = APIRouter()


class DepartmentType(str, Enum):
    radiology = "radiology"
    phlebotomy = "phlebotomy"


class PhlebotomyStatus(str, Enum):
    awaiting_sample = "awaiting_sample"
    awaiting_results = "awaiting_results"
    in_progress = "in_progress"


@router.get("/queue/radiology", response_model=list[LabQueueResponse2])
async def get_radiology_queue(db: AsyncSession = Depends(get_db)):
    """
    Fetches all pending radiology investigations across all appointments.
    """
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.test)
        .join(LabOrderItem.order)
        .join(LabOrder.appointment)
        .join(Appointment.patient)
        .outerjoin(Appointment.doctor)  # Get the referring physician
        .where(
            Test.requires_phlebotomy == False,  # Radiology/Imaging only
            LabOrderItem.status.in_(
                ["awaiting_results", "in_progress", "awaiting_approval"]
            ),
            LabOrderItem.stage.in_([LabStage.RUNNING, LabStage.ANALYZING]),
        )
        .options(
            contains_eager(LabOrderItem.test),
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .contains_eager(Appointment.patient),
            contains_eager(LabOrderItem.order)
            .contains_eager(LabOrder.appointment)
            .contains_eager(Appointment.doctor),
            # Pre-load results to avoid lazy-loading errors in Pydantic
            selectinload(LabOrderItem.radiology_result),
            selectinload(LabOrderItem.lab_result),
        )
    )

    result = await db.execute(stmt)
    # .unique() is required when using contains_eager with joins
    return result.unique().scalars().all()


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
        .join(LabOrderItem.order)
        .join(LabOrderItem.test)
        .where(
            LabOrder.appointment_id == appointment_id,
            LabOrderItem.status == "awaiting_sample",
            # LabOrderItem.ssAdd this to ensure you're in the right workflow
            Test.requires_phlebotomy == True,
        )
        .options(
            selectinload(LabOrderItem.test),
            selectinload(LabOrderItem.radiology_result),  # Keeps Pydantic from crashing
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/appointments/{appointment_id}/radiology-items",
    response_model=list[LabOrderItemResponse],
)
async def get_radiology_items(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabOrderItem)
        .join(LabOrderItem.order)
        .join(LabOrderItem.test)
        .where(
            LabOrder.appointment_id == appointment_id,
            Test.requires_phlebotomy == False,
            LabOrderItem.status.in_(["awaiting_results", "in_progress"]),
        )
        .options(
            selectinload(LabOrderItem.test),
            # NEW: Load the specific radiology result relationship
            selectinload(LabOrderItem.radiology_result),
            # selectinload(LabOrderItem.lab_result),
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()
