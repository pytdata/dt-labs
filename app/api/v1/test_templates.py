from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload


from app.db.session import get_db
from app.models.catalog import Test
from app.models.lab import LabOrderItem, TestTemplate
from app.schemas.test_templates import (
    TestTemplateCreate,
    TestTemplateUpdate,
    TestTemplatesResponse,
)


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


router = APIRouter()


@router.get("/", response_model=list[TestTemplatesResponse])
async def get_all_templates(
    query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TestTemplate)
        .options(selectinload(TestTemplate.test))
        .order_by(TestTemplate.created_on.asc())
        .limit(query.limit)
        .offset(query.offset)
    )

    result = await db.execute(stmt)
    all_templates = result.scalars().all()

    return all_templates


@router.get("/grouped")
async def get_grouped_templates(db: AsyncSession = Depends(get_db)):
    # This query finds unique tests and counts how many parameters they have
    stmt = (
        select(
            TestTemplate.test_id,
            Test.name.label("test_name"),
            func.count(TestTemplate.id).label("parameter_count"),
            func.max(TestTemplate.created_on).label("last_updated"),
        )
        .join(Test, TestTemplate.test_id == Test.id)
        .group_by(TestTemplate.test_id, Test.name)
        .order_by(Test.name.asc())
    )

    result = await db.execute(stmt)
    # We return a list of dictionaries manually since it's an aggregate query
    return [
        {
            "test_id": row.test_id,
            "test_name": row.test_name,
            "parameter_count": row.parameter_count,
            "created_on": row.last_updated,
        }
        for row in result.all()
    ]


@router.post("/", response_model=TestTemplatesResponse)
async def create_test_template(
    payload: TestTemplateCreate, db: AsyncSession = Depends(get_db)
):
    data = payload
    db.add(data)
    await db.commit()
    await db.refresh(data)

    return data


@router.post("/bulk")
async def create_test_templates_bulk(
    data: list[TestTemplateCreate],
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        for item in data:
            template = TestTemplate(
                test_id=item.test_id,
                test_name=item.test_name,
                unit=item.unit,
                min_reference_range=item.min_reference_range,
                max_reference_range=item.max_reference_range,
            )
            db.add(template)

    return {"message": "Templates created successfully"}


@router.patch("/by-test/{test_id}")
async def update_test_templates_bulk(
    test_id: int,
    data: list[TestTemplateCreate],  # Reusing your create schema
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        # 1. Delete all existing parameters for this test
        delete_stmt = delete(TestTemplate).where(TestTemplate.test_id == test_id)
        await db.execute(delete_stmt)

        # 2. Add the new updated list
        for item in data:
            new_param = TestTemplate(
                test_id=test_id,
                test_name=item.test_name,
                short_code=item.short_code,
                unit=item.unit,
                min_reference_range=item.min_reference_range,
                max_reference_range=item.max_reference_range,
            )
            db.add(new_param)

    return {"message": "Template updated successfully"}


@router.delete("/{id}/", status_code=204)
async def delete_test_template(id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(TestTemplate).where(TestTemplate.id == id)

    result = await db.execute(stmt)
    result = result.scalar()
    if result:
        stmt = delete(TestTemplate).where(TestTemplate.id == id)
        await db.execute(stmt)
        await db.commit()

        return None
    raise HTTPException(detail="Resource not found", status_code=404)


@router.patch("/{template_id}")
async def update_test_template(
    template_id: int,
    data: TestTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TestTemplate).where(TestTemplate.id == template_id)
    template = await db.scalar(stmt)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test template not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return {
        "message": "Test template updated successfully",
        "template_id": template.id,
    }


@router.get("/by-test/{test_id}", response_model=list[TestTemplatesResponse])
async def get_templates_by_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TestTemplate)
        .options(selectinload(TestTemplate.test))
        .where(TestTemplate.test_id == test_id)
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()

    print(templates)

    return templates


@router.get("/by-item/{order_item_id}")
async def get_template_for_order_item(
    order_item_id: int, db: AsyncSession = Depends(get_db)
):
    # 1. Find the test_id for this specific order item
    stmt = select(LabOrderItem).where(LabOrderItem.id == order_item_id)
    result = await db.execute(stmt)
    order_item = result.scalar_one_or_none()

    if not order_item:
        raise HTTPException(status_code=404, detail="Order item not found")

    # 2. Fetch all parameters associated with that test_id
    template_stmt = select(TestTemplate).where(
        TestTemplate.test_id == order_item.test_id
    )
    template_result = await db.execute(template_stmt)
    return template_result.scalars().all()
