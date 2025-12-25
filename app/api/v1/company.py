from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import CompanyProfile
from app.schemas import CompanyProfileOut, CompanyProfileUpdate

router = APIRouter()

@router.get("", response_model=CompanyProfileOut)
async def get_company(db: AsyncSession = Depends(get_db)):
    cp = (await db.execute(select(CompanyProfile))).scalars().first()
    if not cp:
        cp = CompanyProfile(name="YKG LAB & DIAGNOSTIC CENTER")
        db.add(cp)
        await db.commit()
        await db.refresh(cp)
    return cp

@router.put("", response_model=CompanyProfileOut)
async def update_company(payload: CompanyProfileUpdate, db: AsyncSession = Depends(get_db)):
    cp = (await db.execute(select(CompanyProfile))).scalars().first()
    if not cp:
        cp = CompanyProfile(name=payload.name or "YKG LAB & DIAGNOSTIC CENTER")
        db.add(cp)
    else:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(cp, k, v)
    await db.commit()
    await db.refresh(cp)
    return cp
