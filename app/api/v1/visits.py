from typing import Annotated, Literal
from fastapi import APIRouter, Depends
from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import Patient
from app.models.lab import Visit
from app.schemas import PatientCreate, PatientOut
from sqlalchemy import or_
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.schemas.visit import VisitResponse


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] = "newest"
    doctor: str | None = None
    patient: str | None = None
    department: str | None = None
    search: str | None = None


@router.get("/", response_model=list[VisitResponse])
async def get_all_visits(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Visit)
        .options(
            selectinload(Visit.patient),
            selectinload(Visit.department),
            selectinload(Visit.doctor),
        )
        .order_by(Visit.visit_date.desc())
    )

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    if filter_query.doctor:
        stmt = stmt.where(
            or_(
                Visit.doctor.full_name.ilike(f"%{filter_query.doctor}"),
            )
        )
    if filter_query.patient:
        stmt = stmt.where(
            or_(
                Visit.patient.first_name.ilike(f"%{filter_query.patient}"),
                Visit.patient.surname.ilike(f"%{filter_query.patient}"),
                Visit.patient.other_names.ilike(f"%{filter_query.patient}"),
            )
        )
    if filter_query.department:
        stmt = stmt.where(
            or_(
                Visit.department.name.ilike(f"%{filter_query.department}"),
            )
        )

    result = await db.execute(stmt)
    visits = result.scalars().all()

    return visits
