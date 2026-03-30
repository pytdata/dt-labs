from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.models.catalog import Test
from app.models.lab import LabResult
from app.schemas.appointment import (
    LabResultResponse,
    ManualTestResult,
    TestCreate,
    TestResponse,
    TestResponseForSettings,
)


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


@router.post(
    "/create",
    response_model=TestResponse,  # Ensure this schema includes id, name, price, etc.
    status_code=status.HTTP_201_CREATED,
)
async def create_new_test(
    payload: TestCreate,  # Your Pydantic model
    db: AsyncSession = Depends(get_db),
):
    # 1. Check for duplicate test name (Case-insensitive)
    stmt = select(Test).where(func.lower(Test.name) == payload.name.strip().lower())
    existing = await db.scalar(stmt)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A test with the name '{payload.name}' already exists.",
        )

    # 2. Initialize the Test Object
    new_test = Test(
        name=payload.name.strip(),
        test_category_id=payload.test_category_id,
        sample_category_id=payload.sample_category_id,
        department=payload.department,
        default_analyzer_id=payload.default_analyzer_id,
        price_ghs=payload.price_ghs,
        test_duration=payload.test_duration,
        requires_phlebotomy=payload.requires_phlebotomy,
        test_status=True,  # Default to active
    )

    try:
        db.add(new_test)
        await db.commit()
        await db.refresh(new_test)
        return new_test
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get("/tests-with-category", response_model=List[TestResponseForSettings])
async def get_all_tests_with_category(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Test)
        .options(
            joinedload(Test.test_category),
            joinedload(Test.default_analyzer),
            joinedload(Test.sample_category),
        )
        .order_by(Test.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/{test_id}/change/", response_model=TestResponseForSettings)
async def update_test(
    test_id: int, payload: TestCreate, db: AsyncSession = Depends(get_db)
):
    # 1. Fetch the existing test
    result = await db.execute(select(Test).where(Test.id == test_id))
    db_test = result.scalar_one_or_none()

    if not db_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )

    # 2. Update the fields dynamically from the payload
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_test, key, value)

    try:
        # 3. Commit the changes
        await db.commit()
        await db.refresh(db_test)

        # 4. Re-fetch with relationships to satisfy the response model
        # This ensures 'test_category', 'sample_category', etc., are loaded
        stmt = (
            select(Test)
            .options(
                joinedload(Test.test_category),
                joinedload(Test.default_analyzer),
                joinedload(Test.sample_category),
            )
            .where(Test.id == test_id)
        )
        final_result = await db.execute(stmt)
        return final_result.scalar_one()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not update test: {str(e)}",
        )


# from app.models import Test


@router.delete("/{test_id}")
async def delete_test(test_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Verify the test exists in the directory first
    result = await db.execute(select(Test).where(Test.id == test_id))
    db_test = result.scalar_one_or_none()

    if not db_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The test you are trying to delete does not exist.",
        )

    try:
        # 2. Attempt the hard delete
        await db.delete(db_test)
        await db.commit()
        return {"message": "Test removed successfully"}

    except IntegrityError:
        # 3. This block catches Database errors when Foreign Key constraints fail
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This test is already linked to patient results or billing records. "
                "It cannot be deleted to preserve medical history."
            ),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the test.",
        )


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
