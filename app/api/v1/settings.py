from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.company import OrganizationPrefix
from app.schemas.settings import PrefixUpdate


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
