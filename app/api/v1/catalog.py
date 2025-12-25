from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import Analyzer, Test
from app.schemas import AnalyzerOut, TestOut

router = APIRouter()

@router.get("/analyzers", response_model=list[AnalyzerOut])
async def list_analyzers(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Analyzer).order_by(Analyzer.name))).scalars().all()

@router.get("/tests", response_model=list[TestOut])
async def list_tests(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Test).order_by(Test.name))).scalars().all()
