import strawberry
from strawberry.types import Info
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Patient, Test, Analyzer

@strawberry.type
class PatientType:
    id: int
    patient_no: str
    full_name: str

@strawberry.type
class TestType:
    id: int
    name: str
    price_ghs: Optional[float]

@strawberry.type
class AnalyzerType:
    id: int
    name: str

@strawberry.type
class Query:
    @strawberry.field
    async def patients(self, info: Info) -> List[PatientType]:
        db: AsyncSession = info.context["db"]
        rows = (await db.execute(select(Patient).order_by(Patient.id.desc()))).scalars().all()
        return [PatientType(id=p.id, patient_no=p.patient_no, full_name=p.full_name) for p in rows]

    @strawberry.field
    async def tests(self, info: Info) -> List[TestType]:
        db: AsyncSession = info.context["db"]
        rows = (await db.execute(select(Test).order_by(Test.name))).scalars().all()
        return [TestType(id=t.id, name=t.name, price_ghs=float(t.price_ghs) if t.price_ghs is not None else None) for t in rows]

    @strawberry.field
    async def analyzers(self, info: Info) -> List[AnalyzerType]:
        db: AsyncSession = info.context["db"]
        rows = (await db.execute(select(Analyzer).order_by(Analyzer.name))).scalars().all()
        return [AnalyzerType(id=a.id, name=a.name) for a in rows]

schema = strawberry.Schema(query=Query)
