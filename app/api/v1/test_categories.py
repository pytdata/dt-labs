from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy import or_


from app.db.session import get_db
from app.models import Patient
from app.models.catalog import Test, TestCategory
from app.models.users import User
from app.schemas.appointment import TestCategoryResponse, TestResponse


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    test_category_type: int
    name: str | None = None


@router.get("/", response_model=list[TestResponse])
async def get_all_tests_categories(
    # test_category_id: int,
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    if not filter_query:
        # stmt = (
        #     select(TestCategory)
        #     .where(TestCategory)
        #     .order_by(TestCategory.date_added.desc())
        # )
        # stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)
        # test_result = await db.execute(stmt)
        # selected_test_result = test_result.scalar()
        # return selected_test_result
        raise HTTPException("The query 'test_category; is required")
    stmt = (
        select(TestCategory)
        .where(TestCategory.id == filter_query.test_category_type)
        .order_by(TestCategory.date_added.desc())
    )

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    test_result = await db.execute(stmt)
    selected_test_result = test_result.scalar()

    if selected_test_result:
        test_stmt = select(Test).where(Test.test_category_id == selected_test_result.id)

        if filter_query.name:
            test_stmt = test_stmt.where(Test.name.ilike(f"%{filter_query.name}%"))
        results = await db.execute(test_stmt)
        tests = results.scalars().all()
        return tests

    raise HTTPException(detail="Resource not found", status_code=404)


@router.get("/tests/", response_model=list[TestResponse])
async def get_all_tests(
    # test_category_id: int,
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Test).order_by(TestCategory.date_added.desc())
    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)
    test_result = await db.execute(stmt)
    selected_test_result = test_result.scalar()
    return selected_test_result
