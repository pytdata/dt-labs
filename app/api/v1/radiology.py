from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.db.session import get_db
from app.models.catalog import Phlebotomy, Sample
from app.models.enums import LabStage
from app.models.lab import Appointment, LabOrderItem, RadiologyLabResult


from app.schemas.lab import RadiologyResultResponse, RadiologyResultSubmit

router = APIRouter()


@router.post("/submit-result")
async def submit_radiology_result(
    payload: RadiologyResultSubmit,
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch the LabOrderItem
    # Use select(...).with_for_update() if you want to prevent
    # two scientists from submitting the same result simultaneously.
    stmt = select(LabOrderItem).where(LabOrderItem.id == payload.order_item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Radiology test item not found")

    # 2. Prevent duplicate results if one already exists
    # (Optional but recommended)
    check_stmt = select(RadiologyLabResult).where(
        RadiologyLabResult.order_item_id == item.id
    )
    existing = await db.execute(check_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Result already exists for this item"
        )

    # 3. Create the New LabResult
    new_result = RadiologyLabResult(
        order_item_id=item.id,
        result_value=payload.findings,
        comments=payload.conclusion,
        status="pending",
        # entered_by_user_id=current_user.id, # Uncomment when Auth is ready
    )

    # 4. Update the LabOrderItem Status
    item.status = "awaiting_approval"
    item.stage = LabStage.ANALYZING

    db.add(new_result)

    try:
        await db.commit()
        # We refresh to ensure new_result.id is loaded before the session ends
        await db.refresh(new_result)

        return {
            "message": "Radiology report submitted successfully",
            "id": new_result.id,
            "order_item_id": item.id,
        }
    except Exception as e:
        await db.rollback()
        # Log the error properly here
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save report to database")


@router.post("/finalize-report/{item_id}")
async def finalize_radiology_report(item_id: int, db: AsyncSession = Depends(get_db)):
    """
    Finalizes a radiology report, moves it out of the active queue,
    and marks the results as verified.
    """
    # 1. Fetch the LabOrderItem with its related result
    stmt = (
        select(LabOrderItem)
        .options(selectinload(LabOrderItem.radiology_result))
        .where(LabOrderItem.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Radiology item not found")

    # 2. Check if the result exists before finalizing
    if not item.radiology_result:
        raise HTTPException(
            status_code=400,
            detail="No report findings found. You cannot finalize an empty report.",
        )

    try:
        # 3. Update the LabOrderItem
        # This moves it out of the 'RUNNING'/'ANALYZING' filter in your queue
        item.status = "completed"
        item.stage = LabStage.ENDED

        # 4. Update the Radiology Result Record
        item.radiology_result.status = "verified"
        # item.radiology_result.verified_at = datetime.now()
        # item.radiology_result.verified_by = current_user.id

        await db.commit()

        return {
            "status": "success",
            "message": "Report finalized and moved to patient history",
            "item_id": item_id,
        }

    except Exception as e:
        await db.rollback()
        print(f"Finalization Error: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during finalization"
        )


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
