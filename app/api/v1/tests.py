from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


from app.db.session import get_db
from app.models.catalog import Test
from app.models.lab import Appointment, LabOrder, LabOrderItem, LabResult
from app.schemas.appointment import LabResultResponse, ManualTestResult, TestResponse


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


@router.get("/tests/", response_model=list[TestResponse])
async def get_all_tests(
    # test_category_id: int,
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Test)
    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)
    test_result = await db.execute(stmt)
    selected_test_result = test_result.scalars()
    return selected_test_result


# @router.get("/active-appointments/", response_model=list[dict])
# async def get_tests_for_active_appointments(db: AsyncSession = Depends(get_db)):
#     """
#     Returns all tests related to active appointments.
#     Active appointments are those with status 'upcoming' or 'in_progress'.
#     """
#     # Query active appointments
#     stmt = (
#         select(Appointment)
#         .where(Appointment.status.in_(["upcoming", "in_progress"]))
#         .options(selectinload(Appointment.tests))
#         .options(selectinload(Appointment.patient))
#         .options(
#             selectinload(Appointment.lab_order)
#             .selectinload(LabOrder.items)
#             .selectinload(LabOrderItem.result)
#         )
#     )
#     result = await db.execute(stmt)
#     appointments = result.scalars().unique().all()  # unique() avoids duplicates

#     tests_data = []
#     for appointment in appointments:
#         for order in appointment.lab_order:
#             for item in order.items:
#                 tests_data.append(
#                     {
#                         "appointment_id": appointment.id,
#                         "created_at": appointment.appointment_at,
#                         "amount": appointment.total_price,
#                         "patient_no": appointment.patient.patient_no,
#                         "test_duration": item.test.test_duration,
#                         "test_id": item.test_id,
#                         "test_name": item.test.name,
#                         "test_no": item.result.test_no if item.result else None,
#                         "result_status": item.result.status if item.result else None,
#                         "lab_result_id": item.result.id if item.result else None,
#                         "order_item_status": item.status,
#                     }
#                 )

#     return tests_data


@router.get("/phlebotomy-only", response_model=list[TestResponse])
async def get_phlebotomy_tests(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Test).where(Test.requires_phlebotomy == True).order_by(Test.name.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{id}/", response_model=LabResultResponse)
async def manual_update_test_results(
    id: int, data: ManualTestResult, db: AsyncSession = Depends(get_db)
):
    stmt = select(LabResult).where(Test.id == id)
    lab_results = await db.execute(stmt)
    results = lab_results.scalar()
    if not results:
        raise HTTPException(detail="Resource not found", status_code=404)

    manual_results = data.model_dump()
    results.results = manual_results

    db.add(results)
    await db.commit()
    await db.refresh(results)

    return results


@router.get("/{id}/", response_model=LabResultResponse)
async def get_test_result(id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(LabResult).where(LabResult.id == id)
    lab_results = await db.execute(stmt)
    results = lab_results.scalar()
    if not results:
        raise HTTPException(detail="Resource not found", status_code=404)

    return results
