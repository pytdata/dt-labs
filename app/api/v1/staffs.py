from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.permission import Role
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
        # 1. Base Query (You already have lazy="selectin" in the model,
        # so selectinload here is technically redundant but fine to keep)
        stmt = select(User).options(selectinload(User.role)).order_by(User.id.desc())

        # 2. Dynamic Filtering
        if filter_query.name:
            stmt = stmt.where(User.full_name.ilike(f"%{filter_query.name.strip()}%"))

        if filter_query.role:
            # We join the 'role' relationship and filter by Role.name
            stmt = stmt.join(User.role).where(
                Role.name.ilike(f"%{filter_query.role.strip()}%")
            )

        if filter_query.gender:
            stmt = stmt.where(User.gender == filter_query.gender)

        # 3. Pagination & Execution
        stmt = stmt.limit(filter_query.limit).offset(filter_query.offset)
        result = await db.execute(stmt)
        users = result.scalars().all()

        # NO MANUAL LOOPING NEEDED HERE
        return users

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
    # 1. Check if user already exists
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # 2. Fetch the Role object based on the slug sent from the frontend
    # Replace 'Role' with your actual Role model name
    role_obj = await db.scalar(select(Role).where(Role.slug == payload.role))

    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{payload.role}' does not exist",
        )

    # 3. Create the Staff/User record
    staff = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=get_password_hash(payload.password),
        role=role_obj,  # Assign the actual DB object, not the string
        phone_number=payload.phone_number,
        gender=payload.gender,
        is_active=True,
    )

    try:
        db.add(staff)
        await db.commit()
        await db.refresh(staff)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data exist.",
        )

    return {"message": "Staff created successfully"}


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
    # 1. Fetch user with role relationship loaded
    stmt = select(User).options(selectinload(User.role)).where(User.id == staff_id)
    user = await db.scalar(stmt)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Convert payload to dict, excluding fields not provided by JS
    update_data = payload.model_dump(exclude_unset=True)

    # 2. Handle Role Lookup (The missing link)
    if "role" in update_data:
        role_identifier = update_data.pop("role")
        # Look up role by slug (from your JS select values)
        role_stmt = select(Role).where(Role.slug == role_identifier)
        db_role = await db.scalar(role_stmt)

        if not db_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_identifier}' does not exist",
            )
        user.role_id = db_role.id

    # 3. Handle email uniqueness
    if "email" in update_data:
        existing = await db.scalar(
            select(User)
            .where(User.email == update_data["email"])
            .where(User.id != staff_id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
            )

    # 4. Handle password hashing
    if "password" in update_data and update_data["password"]:
        user.password_hash = get_password_hash(update_data.pop("password"))
    elif "password" in update_data:
        update_data.pop("password")  # Remove empty password string if sent

    # 5. Update remaining fields (full_name, phone_number, etc.)
    for field, value in update_data.items():
        if hasattr(user, field):
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
