from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import Analyzer, AnalyzerMessage, LabOrder, LabOrderItem, Test, AnalyzerTestMapping, LabResult
from app.schemas import ASTMResultIn, AnalyzerIngestIn
from app.core.config import settings

router = APIRouter()

@router.post("/astm/results")
async def ingest_astm_result(payload: ASTMResultIn, db: AsyncSession = Depends(get_db)):
    """Legacy/simple ASTM ingest (kept for compatibility)."""
    analyzer = None
    if payload.analyzer_name:
        analyzer = (await db.execute(select(Analyzer).where(Analyzer.name == payload.analyzer_name))).scalars().first()

    db.add(AnalyzerMessage(analyzer_id=analyzer.id if analyzer else None, raw=payload.raw or "", meta={
        "sample_id": payload.sample_id,
        "patient_no": payload.patient_no,
        "test_name": payload.test_name,
        "parameter": payload.parameter,
        "value": payload.value,
        "unit": payload.unit,
        "format": "ASTM",
    }))
    
    await db.commit()

    # Optional: map parsed ASTM results into structured LabResult rows
    try:
        if payload.format == "ASTM" and isinstance(payload.parsed, dict) and payload.parsed.get("results"):
            # Find the most recent lab order matching sample_id. By default, sample_id strategy is patient_no.
            sample_id = payload.sample_id
            if sample_id:
                q = await db.execute(
                    select(LabOrder).where(LabOrder.sample_id == sample_id).order_by(LabOrder.created_at.desc())
                )
                order = q.scalars().first()
            else:
                order = None

            # If we didn't store sample_id on orders yet, fallback: try patient_no -> latest order for that patient
            if not order and payload.patient_no:
                pq = await db.execute(select(Patient).where(Patient.patient_no == payload.patient_no))
                patient = pq.scalars().first()
                if patient:
                    oq = await db.execute(
                        select(LabOrder).where(LabOrder.patient_id == patient.id).order_by(LabOrder.created_at.desc())
                    )
                    order = oq.scalars().first()

            if order:
                # Build mapping test_code -> order_item_id
                items_q = await db.execute(select(LabOrderItem).where(LabOrderItem.order_id == order.id))
                items = items_q.scalars().all()

                # Map by AnalyzerTestMapping if possible (test_code -> internal test)
                mapping_q = await db.execute(select(AnalyzerTestMapping))
                mappings = mapping_q.scalars().all()
                by_code = {m.external_test_code: m.test_id for m in mappings if m.external_test_code}

                # internal test name fallback matcher
                test_ids = [it.test_id for it in items]
                tests_q = await db.execute(select(Test).where(Test.id.in_(test_ids)))
                tests = {t.id: t for t in tests_q.scalars().all()}

                for row in payload.parsed["results"]:
                    code = (row.get("test_code") or "").strip()
                    if not code:
                        continue
                    # find matching order item
                    match_item = None
                    # If we have explicit external code mapping, use it
                    if code in by_code:
                        internal_test_id = by_code[code]
                        match_item = next((it for it in items if it.test_id == internal_test_id), None)
                    # else try match by test name string contains code
                    if not match_item:
                        for it in items:
                            t = tests.get(it.test_id)
                            if t and (code.lower() in (t.name or "").lower()):
                                match_item = it
                                break
                    if not match_item:
                        continue

                    db.add(LabResult(
                        order_item_id=match_item.id,
                        analyzer_message_id=None,  # could be set if you return message id; kept simple
                        analyte_code=code,
                        value=(row.get("value") or None),
                        unit=row.get("unit"),
                        flags=row.get("flags"),
                        ref_range=row.get("ref_range"),
                        raw_record=row.get("raw_record"),
                    ))
                await db.commit()
    except Exception:
        # Do not break ingestion if mapping fails; raw message is still stored.
        pass

    return {"status": "ok"}


@router.post("/ingest")
async def ingest_result(
    payload: AnalyzerIngestIn,
    db: AsyncSession = Depends(get_db),
    x_ingest_token: str | None = Header(default=None),
):
    """Generic ingest endpoint used by the listener service.

    Security: provide header `X-Ingest-Token: <token>` matching settings.INGEST_TOKEN.
    """
    if settings.INGEST_TOKEN and x_ingest_token != settings.INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid ingest token")

    analyzer = None
    if payload.analyzer_id:
        analyzer = (await db.execute(select(Analyzer).where(Analyzer.id == payload.analyzer_id))).scalars().first()
    elif payload.analyzer_name:
        analyzer = (await db.execute(select(Analyzer).where(Analyzer.name == payload.analyzer_name))).scalars().first()

    db.add(AnalyzerMessage(
        analyzer_id=analyzer.id if analyzer else None,
        raw=payload.raw or "",
        meta={
            "format": payload.format,
            "protocol": payload.protocol,
            "sample_id": payload.sample_id,
            "patient_no": payload.patient_no,
            "parsed": payload.parsed,
        }
    ))
    
    await db.commit()

    # Optional: map parsed ASTM results into structured LabResult rows
    try:
        if payload.format == "ASTM" and isinstance(payload.parsed, dict) and payload.parsed.get("results"):
            # Find the most recent lab order matching sample_id. By default, sample_id strategy is patient_no.
            sample_id = payload.sample_id
            if sample_id:
                q = await db.execute(
                    select(LabOrder).where(LabOrder.sample_id == sample_id).order_by(LabOrder.created_at.desc())
                )
                order = q.scalars().first()
            else:
                order = None

            # If we didn't store sample_id on orders yet, fallback: try patient_no -> latest order for that patient
            if not order and payload.patient_no:
                pq = await db.execute(select(Patient).where(Patient.patient_no == payload.patient_no))
                patient = pq.scalars().first()
                if patient:
                    oq = await db.execute(
                        select(LabOrder).where(LabOrder.patient_id == patient.id).order_by(LabOrder.created_at.desc())
                    )
                    order = oq.scalars().first()

            if order:
                # Build mapping test_code -> order_item_id
                items_q = await db.execute(select(LabOrderItem).where(LabOrderItem.order_id == order.id))
                items = items_q.scalars().all()

                # Map by AnalyzerTestMapping if possible (test_code -> internal test)
                mapping_q = await db.execute(select(AnalyzerTestMapping))
                mappings = mapping_q.scalars().all()
                by_code = {m.external_test_code: m.test_id for m in mappings if m.external_test_code}

                # internal test name fallback matcher
                test_ids = [it.test_id for it in items]
                tests_q = await db.execute(select(Test).where(Test.id.in_(test_ids)))
                tests = {t.id: t for t in tests_q.scalars().all()}

                for row in payload.parsed["results"]:
                    code = (row.get("test_code") or "").strip()
                    if not code:
                        continue
                    # find matching order item
                    match_item = None
                    # If we have explicit external code mapping, use it
                    if code in by_code:
                        internal_test_id = by_code[code]
                        match_item = next((it for it in items if it.test_id == internal_test_id), None)
                    # else try match by test name string contains code
                    if not match_item:
                        for it in items:
                            t = tests.get(it.test_id)
                            if t and (code.lower() in (t.name or "").lower()):
                                match_item = it
                                break
                    if not match_item:
                        continue

                    db.add(LabResult(
                        order_item_id=match_item.id,
                        analyzer_message_id=None,  # could be set if you return message id; kept simple
                        analyte_code=code,
                        value=(row.get("value") or None),
                        unit=row.get("unit"),
                        flags=row.get("flags"),
                        ref_range=row.get("ref_range"),
                        raw_record=row.get("raw_record"),
                    ))
                await db.commit()
    except Exception:
        # Do not break ingestion if mapping fails; raw message is still stored.
        pass

    return {"status": "ok"}

