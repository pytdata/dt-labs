from __future__ import annotations
import asyncio
from typing import Dict, Any
from sqlalchemy import select
from app.models import Analyzer
from .db import AsyncSessionLocal
from .connectors import tcp_stream, TCPConfig, serial_stream, SerialConfig
from .parser import parse_astm, parse_csv, parse_xml
from .client import LISClient
from app.core.config import settings

class AnalyzerRuntimeManager:
    def __init__(self) -> None:
        self.tasks: list[asyncio.Task] = []
        self.stop_event = asyncio.Event()
        self.client = LISClient(
            base_url=getattr(settings, "LIS_BASE_URL", "http://127.0.0.1:8000"),
            token=settings.INGEST_TOKEN,
        )

    async def load_analyzers(self) -> list[Analyzer]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Analyzer).where(Analyzer.is_active == True))
            return result.scalars().all()

    async def run(self) -> None:
        analyzers = await self.load_analyzers()
        if not analyzers:
            print("[listener] No active analyzers found.")
        for a in analyzers:
            t = asyncio.create_task(self._run_one(a), name=f"analyzer-{a.id}")
            self.tasks.append(t)

        await self.stop_event.wait()
        for t in self.tasks:
            t.cancel()

    async def _run_one(self, analyzer: Analyzer) -> None:
        print(f"[listener] Starting {analyzer.name} ({analyzer.connection_type}, {analyzer.result_format})")
        buffer = bytearray()
        last_data = asyncio.get_event_loop().time()

        async def flush_if_ready(force: bool = False):
            nonlocal buffer, last_data
            now = asyncio.get_event_loop().time()
            if buffer and (force or (now - last_data) > 1.0):
                raw = buffer.decode(errors="ignore")
                buffer = bytearray()
                await self._handle_payload(analyzer, raw)

        try:
            if analyzer.connection_type == "tcp":
                if not analyzer.tcp_ip or not analyzer.tcp_port:
                    print(f"[listener] Missing TCP config for {analyzer.name}")
                    return
                async for chunk in tcp_stream(TCPConfig(analyzer.tcp_ip, int(analyzer.tcp_port))):
                    buffer.extend(chunk)
                    last_data = asyncio.get_event_loop().time()
                    # ASTM often ends with EOT (0x04)
                    if b"\x04" in chunk:
                        await flush_if_ready(force=True)
                    else:
                        await flush_if_ready(force=False)

            elif analyzer.connection_type == "serial":
                if not analyzer.serial_port:
                    print(f"[listener] Missing Serial config for {analyzer.name}")
                    return
                cfg = SerialConfig(
                    port=analyzer.serial_port,
                    baudrate=analyzer.baud_rate or 9600,
                    parity=(analyzer.parity or "N")[0],
                    stopbits=int(analyzer.stop_bits or 1),
                    bytesize=int(analyzer.data_bits or 8),
                )
                async for chunk in serial_stream(cfg):
                    buffer.extend(chunk)
                    last_data = asyncio.get_event_loop().time()
                    if b"\x04" in chunk:
                        await flush_if_ready(force=True)
                    else:
                        await flush_if_ready(force=False)
            else:
                print(f"[listener] Unsupported connection type for {analyzer.name}: {analyzer.connection_type}")
                return
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"[listener] {analyzer.name} error: {e}")
        finally:
            try:
                await flush_if_ready(force=True)
            except Exception:
                pass

    async def _handle_payload(self, analyzer: Analyzer, raw: str) -> None:
        fmt = (analyzer.result_format or "ASTM").upper()
        parsed: Dict[str, Any] = {}
        sample_id = None
        patient_no = None

        if fmt == "ASTM":
            parsed, sample_id, patient_no = parse_astm(raw)
        elif fmt == "CSV":
            parsed = parse_csv(raw)
        elif fmt == "XML":
            parsed = parse_xml(raw)
        else:
            parsed = {"raw": raw, "note": f"Unknown format: {fmt}"}

        payload = {
            "analyzer_id": analyzer.id,
            "analyzer_name": analyzer.name,
            "format": fmt,
            "protocol": analyzer.protocol,
            "sample_id": sample_id,
            "patient_no": patient_no,
            "raw": raw,
            "parsed": parsed,
        }
        await self.client.post_ingest(payload)
        print(f"[listener] Ingested payload from {analyzer.name} (sample={sample_id})")
def _resolve_identifier(self, analyzer: Analyzer, sample_id: str | None, patient_no: str | None, parsed: Dict[str, Any]) -> tuple[str | None, str | None]:
    """Resolve which identifier to use for matching in LIS.

    Returns (identifier_value, identifier_source)
    """
    order_id = None
    try:
        order_id = (parsed or {}).get("meta", {}).get("order_id")
    except Exception:
        order_id = None

    candidates = {
        "patient_no": patient_no,
        "sample_id": sample_id,
        "order_id": order_id,
    }

    primary = (getattr(analyzer, "patient_id_source", None) or "patient_no").strip().lower()
    if primary in candidates and candidates[primary]:
        return candidates[primary], primary

    fallbacks_raw = (getattr(analyzer, "patient_id_fallbacks", None) or "").strip()
    fallbacks = [x.strip().lower() for x in fallbacks_raw.split(",") if x.strip()] if fallbacks_raw else []
    # Safe default fallbacks
    for fb in (fallbacks or ["sample_id", "order_id"]):
        if fb in candidates and candidates[fb]:
            return candidates[fb], fb

    return None, None


