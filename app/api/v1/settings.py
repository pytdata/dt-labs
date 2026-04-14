from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core import deps, constants
from app.db.session import get_db
from app.models.company import OrganizationPrefix
from app.models.users import User
from app.schemas.settings import PrefixUpdate
from typing import List

from app.core.rbac import PermissionChecker
from app.models.permission import Permission, Role
from app.schemas.permissions import RoleCreate, RoleResponse


router = APIRouter()


@router.get("/prefixes")
async def get_prefixes(db: AsyncSession = Depends(get_db)):
    # Look for the singleton configuration row (ID 1)
    stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    result = await db.execute(stmt)
    prefixes = result.scalar_one_or_none()

    if not prefixes:
        # Return system defaults if the DB row hasn't been created yet
        return {
            "org_identifier": "YKG",
            "patient": "PAT",
            "test": "TST",
            "appointment": "APT",
            "invoice": "INV",
            "bill": "BIL",
            "analyzer": "ANL",
            "payment": "PAY",
            "lab": "LAB",
            "radiology": "RAD",
        }
    return prefixes


@router.post("/prefixes")
async def save_prefixes(data: PrefixUpdate, db: AsyncSession = Depends(get_db)):

    stmt = select(OrganizationPrefix).where(OrganizationPrefix.id == 1)
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if db_obj:
        # Modern SQLAlchemy allows direct attribute updates from a dict
        for key, value in data.model_dump().items():
            setattr(db_obj, key, value)
    else:
        # Create the initial record with ID 1
        db_obj = OrganizationPrefix(id=1, **data.model_dump())
        db.add(db_obj)

    try:
        await db.commit()
        await db.refresh(db_obj)
        return {"status": "success", "message": "Prefix configuration updated"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during save")


@router.post(
    "/roles",
    response_model=RoleResponse,
    dependencies=[Depends(PermissionChecker("settings", "write"))],
)
async def create_or_update_role(
    payload: RoleCreate, db: AsyncSession = Depends(get_db)
):
    # 1. Fetch Role WITH permissions loaded upfront
    stmt = (
        select(Role)
        .options(selectinload(Role.permissions))  # <--- Add this line
        .where(Role.slug == payload.slug)
    )
    result = await db.execute(stmt)
    db_role = result.scalar_one_or_none()

    if not db_role:
        db_role = Role(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            permissions=[],  # Initialize empty list
        )
        db.add(db_role)
    else:
        # Now this works because permissions were eager-loaded
        db_role.permissions = []

    # 2. Sync Permissions
    for resource, actions in payload.access_map.items():
        for action in actions:
            p_stmt = select(Permission).where(
                Permission.resource == resource, Permission.action == action
            )
            p_result = await db.execute(p_stmt)
            db_perm = p_result.scalar_one_or_none()

            if not db_perm:
                db_perm = Permission(resource=resource, action=action)
                db.add(db_perm)
                await db.flush()

            db_role.permissions.append(db_perm)

    await db.commit()
    # Eager load again during refresh to avoid the same error on return
    await db.refresh(db_role, attribute_names=["permissions"])
    return db_role


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role))
    return result.scalars().all()


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int, payload: RoleCreate, db: AsyncSession = Depends(get_db)
):
    # Reuse the logic from your POST but filter by ID
    stmt = (
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    result = await db.execute(stmt)
    db_role = result.scalar_one_or_none()

    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    db_role.name = payload.name
    db_role.slug = payload.slug
    db_role.permissions = []  # Clear and sync new permissions

    for resource, actions in payload.access_map.items():
        for action in actions:
            p_stmt = select(Permission).where(
                Permission.resource == resource, Permission.action == action
            )
            p_res = await db.execute(p_stmt)
            db_p = p_res.scalar_one_or_none()
            if not db_p:
                db_p = Permission(resource=resource, action=action)
                db.add(db_p)
                await db.flush()
            db_role.permissions.append(db_p)

    await db.commit()
    await db.refresh(db_role, attribute_names=["permissions"])
    return db_role


@router.get("/resources")
async def get_system_resources(
    current_user: User = Depends(deps.get_current_user),
):

    if not current_user.has_permission("settings", "read"):
        raise HTTPException(status_code=403, detail="Forbidden")

    return constants.SYSTEM_RESOURCES
