from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload, selectinload
from app.db.session import get_db
from app.models.catalog import Phlebotomy, Sample
from app.models.enums import LabStage, LabStatus
from app.models.lab import Appointment, LabOrderItem, RadiologyLabResult


from app.schemas.lab import RadiologyResultResponse, RadiologySubmitRequest

router = APIRouter()


@router.post("/submit-result")
async def submit_radiology_result(
    data: RadiologySubmitRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),
):
    # 1. Update the Order Item Status & Stage
    # This moves it from 'AWAITING_RESULTS' to 'AWAITING_APPROVAL'
    stmt = (
        update(LabOrderItem)
        .where(LabOrderItem.id == data.order_item_id)
        .values(
            status=LabStatus.AWAITING_APPROVAL,
            stage=LabStage.ANALYZING,  # This represents the "Review" phase
            # entered_by_user_id=current_user.id,
        )
    )
    await db.execute(stmt)

    # 2. Save the Long-form Findings
    new_result = RadiologyLabResult(
        order_item_id=data.order_item_id,
        result_value=data.findings,
        comments=data.conclusion,
        # entered_by_user_id=current_user.id,
        status="pending_verification",
    )
    db.add(new_result)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"status": "success", "message": "Results submitted for review"}


@router.get("/result-by-item/{item_id}")
async def get_radiology_result(item_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches findings so a Senior can review them in the modal."""
    stmt = select(RadiologyLabResult).where(RadiologyLabResult.order_item_id == item_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report findings not found")

    return report


@router.post("/finalize-report/{item_id}")
async def finalize_radiology_report(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # Crucial for medical audit trails
):
    # 1. Fetch with selectinload (matches your relationship name)
    stmt = (
        select(LabOrderItem)
        .options(selectinload(LabOrderItem.radiology_result))
        .where(LabOrderItem.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Radiology item not found")

    # 2. Safety check: Ensure findings exist
    if not item.radiology_result:
        raise HTTPException(
            status_code=400,
            detail="No report findings found. You cannot finalize an empty report.",
        )

    try:
        # 3. Update Order Item Status
        # Using the Enum ensures consistency with your queue filter
        item.status = LabStatus.COMPLETED
        item.stage = LabStage.COMPLETE  # Or LabStage.ENDED per your Enum

        # 4. Finalize the Result Record (The Digital Signature)
        item.radiology_result.status = "verified"
        # Since your model has entered_by_user_id, we can track who finalized it here
        # Or add a 'verified_by_id' to your RadiologyLabResult model later
        item.radiology_result.entered_at = datetime.now()

        await db.commit()

        return {
            "status": "success",
            "message": "Report finalized and moved to patient history",
            "item_id": item_id,
        }

    except Exception as e:
        await db.rollback()
        # Log the error properly for debugging
        print(f"Finalization Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to finalize report")


@router.get(
    "/radiology/result-by-item/{item_id}", response_model=RadiologyResultResponse
)
async def get_radiology_result_by_item(
    item_id: int, db: AsyncSession = Depends(get_db)
):
    """
    Fetches the saved findings for a specific lab order item for review.
    """
    stmt = select(RadiologyLabResult).where(RadiologyLabResult.order_item_id == item_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=404, detail="No report findings found for this item."
        )

    return report
