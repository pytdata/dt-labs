from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models import Analyzer, Test
from app.schemas import AnalyzerOut, TestOut
from app.schemas.catalog import AnalyzerCreate, AnalyzerUpdate

router = APIRouter()


# ---------------------------------------------------------------------------
# ANALYZER ENDPOINTS
# ---------------------------------------------------------------------------

@router.get("/analyzers", response_model=list[AnalyzerOut])
async def list_analyzers(db: AsyncSession = Depends(get_db)):
    """List all analyzers ordered by name."""
    return (await db.execute(select(Analyzer).order_by(Analyzer.name))).scalars().all()


@router.get("/analyzers/{analyzer_id}", response_model=AnalyzerOut)
async def get_analyzer(analyzer_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single analyzer by ID."""
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()
    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")
    return analyzer


@router.post("/analyzers", response_model=AnalyzerOut, status_code=status.HTTP_201_CREATED)
async def create_analyzer(payload: AnalyzerCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new analyzer.

    For Mindray BC-5150 (Haematology):
      - connection_type: tcp
      - transport_type: tcp_server
      - protocol_type: hl7
      - is_automated: true
      - tcp_port: 10001  (LIS listens on this port)

    For Mindray BS-240 (Chemistry) — HL7 mode:
      - connection_type: tcp
      - transport_type: tcp_server
      - protocol_type: hl7
      - is_automated: true
      - tcp_port: 10002

    For Mindray BS-240 (Chemistry) — ASTM mode:
      - connection_type: tcp
      - transport_type: tcp_server
      - protocol_type: astm
      - is_automated: true
      - tcp_port: 10003
    """
    # Check for duplicate name
    existing = (
        await db.execute(select(Analyzer).where(Analyzer.name == payload.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"An analyzer named '{payload.name}' already exists.",
        )

    analyzer = Analyzer(**payload.model_dump())
    db.add(analyzer)
    await db.commit()
    await db.refresh(analyzer)
    return analyzer


@router.put("/analyzers/{analyzer_id}", response_model=AnalyzerOut)
async def update_analyzer(
    analyzer_id: int, payload: AnalyzerUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an existing analyzer configuration."""
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()
    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(analyzer, key, value)

    await db.commit()
    await db.refresh(analyzer)
    return analyzer


@router.delete("/analyzers/{analyzer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analyzer(analyzer_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an analyzer by ID."""
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()
    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")
    await db.delete(analyzer)
    await db.commit()
    return None


@router.patch("/analyzers/{analyzer_id}/toggle", response_model=AnalyzerOut)
async def toggle_analyzer_active(analyzer_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle is_active status of an analyzer."""
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()
    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")
    analyzer.is_active = not analyzer.is_active
    await db.commit()
    await db.refresh(analyzer)
    return analyzer


# ---------------------------------------------------------------------------
# TEST ENDPOINTS
# ---------------------------------------------------------------------------

@router.get("/tests", response_model=list[TestOut])
async def list_tests(db: AsyncSession = Depends(get_db)):
    """List all tests ordered by name."""
    return (await db.execute(select(Test).order_by(Test.name))).scalars().all()