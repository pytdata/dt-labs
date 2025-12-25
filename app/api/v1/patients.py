from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientOut

router = APIRouter()

DEFAULT_PREFIX = "YGK"  # can be moved to Settings table later

async def _next_patient_no(db: AsyncSession) -> str:
    max_id = (await db.execute(select(func.max(Patient.id)))).scalar() or 0
    nxt = int(max_id) + 1
    return f"{DEFAULT_PREFIX}-PT-{nxt:06d}"

@router.post("", response_model=PatientOut)
async def create_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    patient_no = await _next_patient_no(db)
    patient = Patient(patient_no=patient_no, **payload.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient

@router.get("", response_model=list[PatientOut])
async def list_patients(
    q: str | None = Query(default=None, description="Filter by surname or first_name"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Patient).order_by(Patient.id.desc())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Patient.surname.ilike(like)) | (Patient.first_name.ilike(like)))
    return (await db.execute(stmt)).scalars().all()