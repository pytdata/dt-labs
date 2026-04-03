from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.users import User
from app.schemas.staff import Gender, StaffCreate, StaffResponse, StaffUpdate


router = APIRouter()


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort_by: Literal["newest", "oldest"] | None = None
    name: str | None = None
    role: str | None = None
    gender: Gender | None = None


@router.get("/", response_model=list[StaffResponse])
async def get_all_staffs(
    filter_query: Annotated[FilterParams, Query()], db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Base Query
        stmt = select(User).order_by(User.id.desc())

        # 2. Dynamic Filtering
        if filter_query.name:
            stmt = stmt.where(User.full_name.ilike(f"%{filter_query.name.strip()}%"))

        if filter_query.role:
            stmt = stmt.where(User.role.ilike(f"%{filter_query.role.strip()}%"))

        if filter_query.gender:
            # Ensuring it handles single or list inputs if your FilterParams varies
            stmt = stmt.where(User.gender == filter_query.gender)

        # 3. Pagination
        stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

        # 4. Execution
        result = await db.execute(stmt)
        staffs = result.scalars().all()

        return staffs

    except Exception as e:
        print(f"Staff Fetch Error: {e}")
        return []


@router.get("/{id}/", response_model=StaffResponse)
async def get_staff(
    id: int,
    filter_query: Annotated[FilterParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .where(User.id == id)
        # .join(Appointment.created_by_user)
        .order_by(User.id.desc())
    )

    stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)

    result = await db.execute(stmt)
    staff = result.scalar()

    return staff


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
async def create_staff(
    payload: StaffCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_user = await db.scalar(select(User).where(User.email == payload.email))

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    staff = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        phone_number=payload.phone_number,
        gender=payload.gender,
        is_active=True,
    )

    db.add(staff)
    await db.commit()
    await db.refresh(staff)

    return {"emssage": "ok"}


@router.put(
    "/{staff_id}/",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
)
async def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.id == staff_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Handle email uniqueness
    if "email" in update_data:
        existing = await db.scalar(
            select(User)
            .where(User.email == update_data["email"])
            .where(User.id != staff_id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    # Handle password separately
    if "password" in update_data:
        user.password_hash = get_password_hash(update_data.pop("password"))

    # Update remaining fields
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


@router.delete(
    "/{staff_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == staff_id)
    staff = await db.scalar(stmt)

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff not found",
        )

    await db.delete(staff)
    await db.commit()

    return None
