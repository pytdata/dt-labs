from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models import Analyzer, AnalyzerMessage, LabOrder, LabOrderItem, Test, AnalyzerTestMapping, LabResult
from app.schemas import ASTMResultIn, AnalyzerIngestIn
from app.core.config import settings
from app.services.sample_service import generate_sample_id

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


async def _resolve_order(db: AsyncSession, sample_id: str | None, patient_no: str | None, order_id: str | None = None):
    """Find the most relevant LabOrder and items by sample, order id, or patient."""
    order = None
    items: list[LabOrderItem] = []

    if order_id:
        try:
            oid_int = int(order_id)
            oq = await db.execute(
                select(LabOrder)
                .options(selectinload(LabOrder.items))
                .where(LabOrder.id == oid_int)
            )
            order = oq.scalars().first()
            if order:
                items = list(order.items or [])
        except Exception:
            order = None

    if sample_id:
        q = await db.execute(
            select(LabOrder)
            .options(selectinload(LabOrder.items))
            .where(LabOrder.sample_id == sample_id)
            .order_by(LabOrder.created_at.desc())
        )
        order = q.scalars().first()
        if order:
            items = list(order.items or [])

        # Fallback to lab_order_items.sample_id (older migrations)
        if not order:
            iq = await db.execute(
                select(LabOrderItem)
                .options(
                    selectinload(LabOrderItem.order),
                    selectinload(LabOrderItem.test),
                )
                .where(LabOrderItem.sample_id == sample_id)
                .order_by(LabOrderItem.id.desc())
            )
            it = iq.scalars().first()
            if it:
                order = it.order
                items = [it]

    if not order and patient_no:
        from app.models import Patient  # local import to avoid circular
        pq = await db.execute(select(Patient).where(Patient.patient_no == patient_no))
        patient = pq.scalars().first()
        if patient:
            oq = await db.execute(
                select(LabOrder)
                .options(selectinload(LabOrder.items))
                .where(LabOrder.patient_id == patient.id)
                .order_by(LabOrder.created_at.desc())
            )
            order = oq.scalars().first()
            if order:
                items = list(order.items or [])

    return order, items


def _merge_results(existing: dict | None, incoming: dict[str, dict]) -> dict:
    merged = dict(existing or {})
    for code, row in incoming.items():
        merged[code] = row
    return merged


def _group_results_by_item(
    rows: list[dict],
    items: list[LabOrderItem],
    mappings: list[AnalyzerTestMapping],
    tests: dict[int, Test],
) -> dict[int, dict[str, dict]]:
    by_code = {m.external_test_code: m.test_id for m in mappings if m.external_test_code}
    grouped: dict[int, dict[str, dict]] = {}
    for row in rows:
        code = (row.get("test_code") or "").strip() or (row.get("test_name") or "").strip()
        if not code:
            continue
        match_item = None
        if code in by_code:
            internal_test_id = by_code[code]
            match_item = next((it for it in items if it.test_id == internal_test_id), None)
        if not match_item:
            for it in items:
                t = tests.get(it.test_id)
                if t and (code.lower() in (t.name or "").lower()):
                    match_item = it
                    break
        if not match_item:
            continue

        grouped.setdefault(match_item.id, {})
        grouped[match_item.id][code] = {
            "value": row.get("value"),
            "unit": row.get("unit"),
            "flags": row.get("flags"),
            "ref_range": row.get("ref_range"),
            "source_analyzer": row.get("instrument_id"),
            "raw_record": row.get("raw_record"),
        }
    return grouped


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

    msg = AnalyzerMessage(
        analyzer_id=analyzer.id if analyzer else None,
        raw=payload.raw or "",
        meta={
            "format": payload.format,
            "protocol": payload.protocol,
            "sample_id": payload.sample_id,
            "patient_no": payload.patient_no,
            "order_id": payload.order_id,
            "parsed": payload.parsed,
        }
    )
    db.add(msg)
    await db.flush()

    order = None
    items: list[LabOrderItem] = []
    try:
        order, items = await _resolve_order(db, payload.sample_id, payload.patient_no, payload.order_id)
    except Exception:
        order, items = None, []

    # Optional: map parsed ASTM results into structured LabResult rows
    try:
        if payload.format == "ASTM" and isinstance(payload.parsed, dict) and payload.parsed.get("results") and items:
            mapping_q = await db.execute(select(AnalyzerTestMapping))
            mappings = mapping_q.scalars().all()

            test_ids = [it.test_id for it in items]
            tests_q = await db.execute(select(Test).where(Test.id.in_(test_ids)))
            tests = {t.id: t for t in tests_q.scalars().all()}

            grouped = _group_results_by_item(payload.parsed["results"], items, mappings, tests)

            for item_id, result_rows in grouped.items():
                existing = (await db.execute(
                    select(LabResult)
                    .where(LabResult.order_item_id == item_id)
                    .order_by(LabResult.received_at.desc())
                )).scalars().first()

                merged_results = _merge_results(existing.results if existing else {}, result_rows)
                merged_from = set((existing.merged_from or []))
                if analyzer and analyzer.name:
                    merged_from.add(analyzer.name)

                if existing:
                    existing.results = merged_results
                    existing.merged_from = list(merged_from)
                    existing.analyzer_id = analyzer.id if analyzer else existing.analyzer_id
                    existing.sample_id = existing.sample_id or payload.sample_id or (order.sample_id if order else None) or generate_sample_id()
                else:
                    db.add(LabResult(
                        order_item_id=item_id,
                        analyzer_id=analyzer.id if analyzer else None,
                        analyzer_message_id=msg.id,
                        sample_id=payload.sample_id or (order.sample_id if order else None) or generate_sample_id(),
                        source="analyzer",
                        status="received",
                        results=merged_results,
                        raw_format="ASTM",
                        merged_from=list(merged_from) if merged_from else ( [analyzer.name] if analyzer else [] ),
                    ))
            await db.commit()
    except Exception:
        # Do not break ingestion if mapping fails; raw message is still stored.
        pass

    await db.commit()

    return {"status": "ok", "message_id": msg.id}
