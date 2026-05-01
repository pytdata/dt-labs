"""
Analyzer Ingestion Service
==========================
Handles incoming data from automated laboratory analyzers:
  - Mindray BC-5150  (Haematology)  → HL7 v2.3.1 / MLLP over TCP
  - Mindray BS-240   (Chemistry)    → HL7 v2.3.1 / MLLP over TCP  OR  ASTM E1394-97 over TCP

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Analyzer (BC-5150 / BS-240)                                    │
  │    └──[TCP connect]──► LIS TCP Server (this service)           │
  │         ◄──[ACK]──────── LIS sends ACK^R01                     │
  └─────────────────────────────────────────────────────────────────┘

Storage flow:
  raw bytes  → analyzer_messages.raw  (AnalyzerMessage)
             → analyzer_ingestions    (AnalyzerIngestion - match attempt)
             → lab_results.results    (LabResult JSON)  ← linked to order_item
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.catalog import Analyzer
from app.models.lab import (
    AnalyzerIngestion,
    AnalyzerMessage,
    LabOrderItem,
    LabResult,
    Patient,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MLLP framing constants  (HL7 Minimal Lower Layer Protocol)
# ---------------------------------------------------------------------------
VT: bytes = b"\x0b"        # Vertical Tab  — start of MLLP frame
FS: bytes = b"\x1c"        # File Separator — end of message body
CR: bytes = b"\x0d"        # Carriage Return
MLLP_END: bytes = FS + CR  # \x1c\x0d

# ---------------------------------------------------------------------------
# ASTM framing constants
# ---------------------------------------------------------------------------
ENQ: int = 0x05  # Enquiry   — analyzer wants to send
ACK: int = 0x06  # Acknowledge
NAK: int = 0x15  # Negative Acknowledge
EOT: int = 0x04  # End of Transmission
STX: int = 0x02  # Start of text (data frame start)
ETX: int = 0x03  # End of text (data frame end)
ETB: int = 0x17  # End of Transmission Block (intermediate frame)


# ===========================================================================
# PARSED DATA STRUCTURES
# ===========================================================================

@dataclass
class Observation:
    code: str
    name: str
    coding_system: str
    value_type: str
    value: str
    units: str | None = None
    reference_range: str | None = None
    abnormal_flag: str | None = None
    result_status: str | None = None
    observed_at: str | None = None
    raw_segment: str | None = None


@dataclass
class ParsedAnalyzerMessage:
    analyzer_name: str
    transport: str
    message_type: str
    message_control_id: str | None
    test_no: str
    patient_id: str | None
    sample_id: str | None
    sample_barcode: str | None
    ordered_at: str | None
    observed_at: str | None
    operator: str | None
    match_method: str
    match_value: str
    raw_message: str
    notes: str | None = None
    patient_name: str | None = None
    observations: list[Observation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzer_name": self.analyzer_name,
            "transport": self.transport,
            "message_type": self.message_type,
            "message_control_id": self.message_control_id,
            "test_no": self.test_no,
            "patient_id": self.patient_id,
            "sample_id": self.sample_id,
            "sample_barcode": self.sample_barcode,
            "ordered_at": self.ordered_at,
            "observed_at": self.observed_at,
            "operator": self.operator,
            "match_method": self.match_method,
            "match_value": self.match_value,
            "notes": self.notes,
            "patient_name": self.patient_name,
            "observations": [obs.__dict__ for obs in self.observations],
        }


# ===========================================================================
# LOW-LEVEL HL7 / MLLP HELPERS
# ===========================================================================

def wrap_mllp(message: str) -> bytes:
    """Wrap an HL7 message string in MLLP framing."""
    return VT + message.encode("utf-8") + MLLP_END


def unwrap_mllp(payload: bytes) -> list[str]:
    """Extract one or more HL7 message strings from raw MLLP bytes."""
    messages: list[str] = []
    start = 0
    while True:
        sb = payload.find(VT, start)
        if sb == -1:
            break
        eb = payload.find(MLLP_END, sb + 1)
        if eb == -1:
            break
        body = payload[sb + 1: eb]
        messages.append(body.decode("utf-8", errors="replace"))
        start = eb + len(MLLP_END)
    return messages


def parse_hl7_message(message: str) -> dict[str, list[list[str]]]:
    """Parse raw HL7 text into {segment_name: [fields_list]}."""
    segments: dict[str, list[list[str]]] = {}
    for raw_segment in [seg for seg in message.split("\r") if seg.strip()]:
        fields = raw_segment.split("|")
        seg_name = fields[0]
        segments.setdefault(seg_name, []).append(fields)
    return segments


def get_field(fields: list[str], idx: int) -> str | None:
    """Safely get a field from a parsed HL7 segment."""
    return fields[idx] if idx < len(fields) and fields[idx] != "" else None


def split_coded(value: str | None) -> tuple[str | None, str | None, str | None]:
    """Split a HL7 CWE/CE component like '6690-2^WBC^LN' into (code, name, system)."""
    if not value:
        return None, None, None
    parts = value.split("^")
    return (
        parts[0] if len(parts) > 0 else None,
        parts[1] if len(parts) > 1 else None,
        parts[2] if len(parts) > 2 else None,
    )


def decode_hl7_escapes(value: str) -> str:
    """Decode HL7 escape sequences in field values."""
    return (
        value.replace(r"\F\ ", "|")
        .replace(r"\S\ ", "^")
        .replace(r"\T\ ", "&")
        .replace(r"\R\ ", "~")
        .replace(r"\E\ ", "\\")
        .replace(r"\.br\ ", "\r")
    )


def build_hl7_ack(incoming_message: str, accepted: bool = True, error_text: str | None = None) -> str:
    """Build an HL7 ACK^R01 response for an incoming ORU^R01 message."""
    try:
        segments = parse_hl7_message(incoming_message)
        msh = segments["MSH"][0]
        control_id = get_field(msh, 9) or "1"
        processing_id = get_field(msh, 10) or "P"
        charset = get_field(msh, 17) or "UNICODE"
    except Exception:
        control_id = "1"
        processing_id = "P"
        charset = "UNICODE"

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ack_code = "AA" if accepted else "AE"
    ack_msh = f"MSH|^~\\&|LIS||||{now}||ACK^R01|1|{processing_id}|2.3.1||||||{charset}"
    msa = f"MSA|{ack_code}|{control_id}"
    if error_text and not accepted:
        msa += f"|{error_text}"
    return ack_msh + "\r" + msa + "\r"


# ===========================================================================
# HL7 PARSERS
# ===========================================================================

class AnalyzerParser:
    """Base class for all analyzer message parsers."""
    analyzer_name: str = "Unknown"

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        raise NotImplementedError

    def can_handle(self, payload_bytes: bytes) -> bool:
        """Return True if this parser can handle the raw payload."""
        return False


class MindrayBC5150Parser(AnalyzerParser):
    """
    Parser for Mindray BC-5150 Haematology Analyzer.

    Protocol: HL7 v2.3.1 over TCP with MLLP framing
    Message:  ORU^R01
    Segments: MSH → PID → PV1 → OBR → OBX...
    OBX-3:    LOINC codes  e.g. 6690-2^WBC^LN, 789-8^RBC^LN, 718-7^HGB^LN
    """
    analyzer_name = "Mindray BC-5150"

    def can_handle(self, payload_bytes: bytes) -> bool:
        return VT in payload_bytes

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        segments = parse_hl7_message(message)
        msh = segments.get("MSH", [[]])[0]
        pid = segments.get("PID", [["PID"]])[0]
        obr_list = segments.get("OBR", [[]])
        obr = obr_list[0] if obr_list else []
        obx_segments = segments.get("OBX", [])

        # PID-3: Patient identifier list  (CX: id^^^assigning_authority^id_type)
        patient_id = split_coded(get_field(pid, 3))[0] if get_field(pid, 3) else None
        patient_name = get_field(pid, 5)

        # OBR fields per BC-5150 HL7 spec
        sample_id = get_field(obr, 3)      # OBR-3: Filler order number (sample ID)
        ordered_at = get_field(obr, 14)    # OBR-14: Specimen received date/time
        observed_at = get_field(obr, 7)    # OBR-7: Observation date/time
        operator = get_field(obr, 32)      # OBR-32: Principal result interpreter

        observations: list[Observation] = []
        for seg in obx_segments:
            code, name, system = split_coded(get_field(seg, 3))
            observations.append(
                Observation(
                    code=code or "",
                    name=name or "",
                    coding_system=system or "LN",    # BC-5150 uses LOINC
                    value_type=get_field(seg, 2) or "",
                    value=decode_hl7_escapes(get_field(seg, 5) or ""),
                    units=get_field(seg, 6),
                    reference_range=get_field(seg, 7),
                    abnormal_flag=get_field(seg, 8),
                    result_status=get_field(seg, 11),
                    observed_at=get_field(seg, 14),
                    raw_segment="|".join(seg),
                )
            )

        test_no = sample_id or patient_id or "UNKNOWN"
        return ParsedAnalyzerMessage(
            analyzer_name=self.analyzer_name,
            transport=transport,
            message_type=get_field(msh, 8) or "ORU^R01",
            message_control_id=get_field(msh, 9),
            test_no=test_no,
            patient_id=patient_id,
            sample_id=sample_id,
            sample_barcode=None,
            ordered_at=ordered_at,
            observed_at=observed_at,
            operator=operator,
            match_method="sample_id",
            match_value=sample_id or test_no,
            raw_message=message,
            notes="BC-5150 haematology result (HL7 ORU^R01)",
            patient_name=patient_name,
            observations=observations,
        )


class MindrayBS240HL7Parser(AnalyzerParser):
    """
    Parser for Mindray BS-240 Chemistry Analyzer — HL7 mode.

    Protocol: HL7 v2.3.1 over TCP with MLLP framing
    Message:  ORU^R01
    Segments: MSH → PID → OBR → OBX...
    OBX-3:    test code  e.g. TBIL, ALT, AST, TP, ALB, GLOB
    OBX-4:    test name  (BS-240 specific — used as human-readable name)
    MSH-16:   0 = result message (not a query)
    """
    analyzer_name = "Mindray BS-240"

    def can_handle(self, payload_bytes: bytes) -> bool:
        return VT in payload_bytes

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        segments = parse_hl7_message(message)
        msh = segments.get("MSH", [[]])[0]
        pid = segments.get("PID", [["PID"]])[0]
        obr_list = segments.get("OBR", [[]])
        obr = obr_list[0] if obr_list else []
        obx_segments = segments.get("OBX", [])

        # BS-240: PID-2 is patient ID, PID-3 is alternative
        patient_id = get_field(pid, 2) or split_coded(get_field(pid, 3))[0]
        patient_name = get_field(pid, 5)

        # OBR fields per BS-240 HL7 spec
        sample_barcode = get_field(obr, 2)   # OBR-2: Placer order number (barcode)
        sample_id = get_field(obr, 3)         # OBR-3: Filler order number
        ordered_at = get_field(obr, 6)        # OBR-6: Requested date/time
        observed_at = get_field(obr, 7)       # OBR-7: Observation date/time
        operator = get_field(obr, 16) or get_field(obr, 34)  # OBR-16: Ordering provider

        observations: list[Observation] = []
        for seg in obx_segments:
            # BS-240: OBX-3 is test code, OBX-4 is test name/sub-ID
            observations.append(
                Observation(
                    code=get_field(seg, 3) or "",
                    name=get_field(seg, 4) or get_field(seg, 3) or "",
                    coding_system="",           # BS-240 uses local codes
                    value_type=get_field(seg, 2) or "",
                    value=decode_hl7_escapes(get_field(seg, 5) or ""),
                    units=get_field(seg, 6),
                    reference_range=get_field(seg, 7),
                    abnormal_flag=get_field(seg, 8),
                    result_status=get_field(seg, 11),
                    observed_at=get_field(seg, 14),
                    raw_segment="|".join(seg),
                )
            )

        test_no = sample_id or sample_barcode or patient_id or "UNKNOWN"
        mm = "sample_id" if sample_id else ("sample_barcode" if sample_barcode else "patient_id")
        return ParsedAnalyzerMessage(
            analyzer_name=self.analyzer_name,
            transport=transport,
            message_type=get_field(msh, 8) or "ORU^R01",
            message_control_id=get_field(msh, 9),
            test_no=test_no,
            patient_id=patient_id,
            sample_id=sample_id,
            sample_barcode=sample_barcode,
            ordered_at=ordered_at,
            observed_at=observed_at,
            operator=operator,
            match_method=mm,
            match_value=sample_id or sample_barcode or patient_id or test_no,
            raw_message=message,
            notes="BS-240 chemistry result (HL7 ORU^R01)",
            patient_name=patient_name,
            observations=observations,
        )


class MindrayBS240ASTMParser(AnalyzerParser):
    """
    Parser for Mindray BS-240 Chemistry Analyzer — ASTM E1394-97 mode.

    Protocol: ASTM E1394-97 over TCP
    Handshake: ENQ → ACK → [frames] → EOT
    Records:   H (header) | P (patient) | O (order) | R (result) | L (terminator)
    Framing:   <STX> frame_no data <CR> checksum <ETX|ETB> (per ASTM E1381)
    """
    analyzer_name = "Mindray BS-240"

    def can_handle(self, payload_bytes: bytes) -> bool:
        # ASTM messages start with H| after STX framing is stripped
        text = payload_bytes.decode("latin-1", errors="replace")
        return text.lstrip().startswith("H|") or "\rH|" in text

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        records = [line.strip() for line in message.split("\r") if line.strip()]
        patient_id: str | None = None
        patient_name: str | None = None
        sample_id: str | None = None
        sample_barcode: str | None = None
        ordered_at: str | None = None
        observed_at: str | None = None
        operator: str | None = None
        observations: list[Observation] = []

        for rec in records:
            fields = rec.split("|")
            record_type = fields[0]

            if record_type == "P":
                # P|1|patient_id|||name|...
                patient_id = fields[2] if len(fields) > 2 and fields[2] else None
                patient_name = fields[5] if len(fields) > 5 and fields[5] else None

            elif record_type == "O":
                # O|1|sample_id|barcode|test_id||order_dt|obs_dt|...
                sample_id = fields[2] if len(fields) > 2 and fields[2] else None
                sample_barcode = fields[3] if len(fields) > 3 and fields[3] else None
                ordered_at = fields[6] if len(fields) > 6 and fields[6] else None
                observed_at = fields[7] if len(fields) > 7 and fields[7] else None
                operator = fields[15] if len(fields) > 15 and fields[15] else None

            elif record_type == "R":
                # R|seq|test_code|value|units|range|flags|...
                observations.append(
                    Observation(
                        code=fields[2] if len(fields) > 2 else "",
                        name=fields[3] if len(fields) > 3 else (fields[2] if len(fields) > 2 else ""),
                        coding_system="ASTM",
                        value_type="NM",
                        value=fields[4] if len(fields) > 4 else "",
                        units=fields[5] if len(fields) > 5 else None,
                        reference_range=fields[6] if len(fields) > 6 else None,
                        abnormal_flag=fields[7] if len(fields) > 7 else None,
                        result_status="F",
                        observed_at=observed_at,
                        raw_segment=rec,
                    )
                )

        test_no = sample_id or sample_barcode or patient_id or "UNKNOWN"
        mm = "sample_id" if sample_id else ("sample_barcode" if sample_barcode else "patient_id")
        return ParsedAnalyzerMessage(
            analyzer_name=self.analyzer_name,
            transport=transport,
            message_type="ASTM_RESULT",
            message_control_id=None,
            test_no=test_no,
            patient_id=patient_id,
            sample_id=sample_id,
            sample_barcode=sample_barcode,
            ordered_at=ordered_at,
            observed_at=observed_at,
            operator=operator,
            match_method=mm,
            match_value=sample_id or sample_barcode or patient_id or test_no,
            raw_message=message,
            notes="BS-240 chemistry result (ASTM E1394-97)",
            patient_name=patient_name,
            observations=observations,
        )


# ===========================================================================
# PARSER REGISTRY — add new analyzers here
# ===========================================================================
_PARSER_REGISTRY: list[AnalyzerParser] = [
    MindrayBC5150Parser(),
    MindrayBS240HL7Parser(),
    MindrayBS240ASTMParser(),
]

# Name → preferred parser (HL7 or ASTM)  keyed by lower(name)
_NAME_TO_PARSERS: dict[str, list[AnalyzerParser]] = {
    "mindray bc-5150": [MindrayBC5150Parser()],
    "mindray bs-240": [MindrayBS240HL7Parser(), MindrayBS240ASTMParser()],
}


def detect_parser(analyzer_name: str, protocol_type: str | None, payload: bytes) -> AnalyzerParser:
    """
    Select the correct parser based on analyzer name, configured protocol, and raw payload.
    Priority: name-based lookup → protocol_type hint → payload auto-detection.
    """
    name_lower = analyzer_name.lower()
    protocol_lower = (protocol_type or "auto").lower()

    # Exact name lookup
    for key, parsers in _NAME_TO_PARSERS.items():
        if key in name_lower:
            if len(parsers) == 1:
                return parsers[0]
            # Multiple parsers for this device — disambiguate by protocol hint or payload
            for p in parsers:
                if protocol_lower == "astm" and isinstance(p, MindrayBS240ASTMParser):
                    return p
                if protocol_lower == "hl7" and isinstance(p, MindrayBS240HL7Parser):
                    return p
            # Auto-detect from payload
            for p in parsers:
                if p.can_handle(payload):
                    return p
            return parsers[0]

    # Fallback: generic detection
    text = payload.decode("utf-8", errors="replace")
    if text.lstrip().startswith("H|") or "\rH|" in text:
        return MindrayBS240ASTMParser()
    return MindrayBS240HL7Parser()


# ===========================================================================
# DATABASE REPOSITORY
# ===========================================================================

class AnalyzerIngestionRepository:
    """All DB operations for the ingestion pipeline."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_automated_analyzers(self) -> list[Analyzer]:
        """Return all active, automated analyzers (is_automated=True)."""
        result = await self.session.execute(
            select(Analyzer).where(
                Analyzer.is_active == True,    # noqa: E712
                Analyzer.is_automated == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_analyzer_by_id(self, analyzer_id: int) -> Analyzer | None:
        result = await self.session.execute(
            select(Analyzer).where(Analyzer.id == analyzer_id)
        )
        return result.scalar_one_or_none()

    async def resolve_patient_db_id(self, parsed: ParsedAnalyzerMessage) -> int | None:
        """Try to find the DB patient.id from the analyzer-supplied patient identifier."""
        if not parsed.patient_id:
            return None
        # Try matching on patient_no field
        result = await self.session.execute(
            select(Patient).where(Patient.patient_no == parsed.patient_id)
        )
        patient = result.scalar_one_or_none()
        if patient:
            return patient.id
        # Try numeric id match
        if parsed.patient_id.isdigit():
            result = await self.session.execute(
                select(Patient).where(Patient.id == int(parsed.patient_id))
            )
            patient = result.scalar_one_or_none()
            if patient:
                return patient.id
        return None

    async def resolve_order_item(self, parsed: ParsedAnalyzerMessage) -> LabOrderItem | None:
        """
        Try to find a LabOrderItem that matches this analyzer result.
        Matching strategy: sample_id on LabOrderItem → then lab order sample_id.
        """
        candidates = [v for v in [parsed.sample_id, parsed.sample_barcode] if v]
        for candidate in candidates:
            result = await self.session.execute(
                select(LabOrderItem).where(LabOrderItem.sample_id == candidate)
            )
            item = result.scalar_one_or_none()
            if item:
                return item
        return None

    async def save_raw_message(
        self, analyzer_id: int, raw_text: str, meta: dict | None = None
    ) -> AnalyzerMessage:
        """Store the raw analyzer message in analyzer_messages table."""
        msg = AnalyzerMessage(
            analyzer_id=analyzer_id,
            raw=raw_text,
            meta=meta or {},
        )
        self.session.add(msg)
        await self.session.flush()  # get msg.id
        return msg

    async def save_ingestion(
        self,
        analyzer_row: Analyzer,
        parsed: ParsedAnalyzerMessage,
        analyzer_message: AnalyzerMessage,
    ) -> AnalyzerIngestion:
        """Record the ingestion attempt (matched or unmatched) in analyzer_ingestions."""
        patient_db_id = await self.resolve_patient_db_id(parsed)
        order_item = await self.resolve_order_item(parsed)

        ingestion = AnalyzerIngestion(
            analyzer_message_id=analyzer_message.id,
            analyzer_id=analyzer_row.id,
            patient_id=patient_db_id,
            order_item_id=order_item.id if order_item else None,
            match_method=parsed.match_method,
            match_value=parsed.match_value,
            status="matched" if order_item else "unmatched",
            notes=parsed.notes,
        )
        self.session.add(ingestion)
        await self.session.flush()
        return ingestion

    async def save_lab_results(
        self,
        analyzer_row: Analyzer,
        parsed: ParsedAnalyzerMessage,
        analyzer_message: AnalyzerMessage,
        order_item: LabOrderItem | None,
    ) -> LabResult | None:
        """
        Write parsed observations into lab_results table.
        The results JSON contains all observations from this analyzer run.
        Only creates a LabResult if we have an order_item to link to.
        """
        if order_item is None:
            logger.warning(
                "Cannot save lab results — no matching order_item for %s value=%s",
                parsed.match_method,
                parsed.match_value,
            )
            return None

        # Build results JSON: list of dicts, one per observation
        results_json = [obs.__dict__ for obs in parsed.observations]

        # Check if a LabResult already exists for this order_item
        existing = await self.session.execute(
            select(LabResult).where(LabResult.order_item_id == order_item.id)
        )
        lab_result = existing.scalar_one_or_none()

        if lab_result:
            # Update existing result
            lab_result.results = results_json
            lab_result.analyzer_id = analyzer_row.id
            lab_result.analyzer_message_id = analyzer_message.id
            lab_result.source = "analyzer"
            lab_result.status = "received"
            lab_result.raw_format = parsed.message_type
            logger.info("Updated existing LabResult id=%s for order_item=%s", lab_result.id, order_item.id)
        else:
            # Create new result
            lab_result = LabResult(
                order_item_id=order_item.id,
                analyzer_id=analyzer_row.id,
                analyzer_message_id=analyzer_message.id,
                source="analyzer",
                status="received",
                results=results_json,
                raw_format=parsed.message_type,
            )
            self.session.add(lab_result)
            await self.session.flush()
            logger.info("Created new LabResult id=%s for order_item=%s", lab_result.id, order_item.id)

        # Update LabOrderItem status to indicate result received
        order_item.stage = "resulted"  # type: ignore[attr-defined]
        return lab_result


# ===========================================================================
# INGESTION SERVICE
# ===========================================================================

class AnalyzerIngestionService:
    """
    Main service that processes raw bytes arriving from an analyzer:
      1. Detect protocol (HL7/MLLP or ASTM)
      2. Parse the message
      3. Store raw → AnalyzerMessage
      4. Match to patient/order → AnalyzerIngestion
      5. Write parsed results → LabResult
    """

    async def process_payload(
        self,
        analyzer_row: Analyzer,
        payload: bytes,
        transport: str,
    ) -> list[AnalyzerIngestion]:
        """
        Process raw bytes from an analyzer TCP connection.
        Returns list of AnalyzerIngestion records created.
        """
        protocol_type = getattr(analyzer_row, "protocol_type", None)
        parser = detect_parser(analyzer_row.name, protocol_type, payload)

        # Extract individual messages from MLLP framing (or treat as single message)
        raw_messages = unwrap_mllp(payload)
        if not raw_messages:
            raw_messages = [payload.decode("utf-8", errors="replace")]

        saved_ingestions: list[AnalyzerIngestion] = []

        async with AsyncSessionLocal() as session:
            repo = AnalyzerIngestionRepository(session)

            for raw_message in raw_messages:
                try:
                    parsed = parser.parse(raw_message, transport=transport)

                    # 1. Store raw message
                    analyzer_message = await repo.save_raw_message(
                        analyzer_id=analyzer_row.id,
                        raw_text=raw_message,
                        meta={
                            "transport": transport,
                            "protocol": protocol_type,
                            "analyzer": analyzer_row.name,
                            "parsed_type": parsed.message_type,
                        },
                    )

                    # 2. Save ingestion record (match attempt)
                    ingestion = await repo.save_ingestion(analyzer_row, parsed, analyzer_message)
                    saved_ingestions.append(ingestion)

                    # 3. Try to resolve order_item and save lab results
                    order_item = await repo.resolve_order_item(parsed)
                    await repo.save_lab_results(analyzer_row, parsed, analyzer_message, order_item)

                    logger.info(
                        "Ingested analyzer message: analyzer=%s status=%s match=%s:%s",
                        analyzer_row.name,
                        ingestion.status,
                        parsed.match_method,
                        parsed.match_value,
                    )

                except Exception:
                    logger.exception(
                        "Failed to process message from analyzer %s", analyzer_row.name
                    )

            await session.commit()

        return saved_ingestions

    def build_ack_for_payload(self, analyzer_row: Analyzer, payload: bytes) -> bytes | None:
        """Build an MLLP-wrapped ACK response for the analyzer (HL7 only)."""
        protocol_type = getattr(analyzer_row, "protocol_type", None)
        if (protocol_type or "").lower() == "astm":
            return None  # ASTM uses byte-level ACK, handled separately

        raw_messages = unwrap_mllp(payload)
        if not raw_messages:
            return None
        ack_str = build_hl7_ack(raw_messages[0], accepted=True)
        return wrap_mllp(ack_str)


# ===========================================================================
# TCP SERVER LISTENER (LIS acts as server, analyzer connects to it)
# ===========================================================================

class AnalyzerTCPServerListener:
    """
    Async TCP server that listens for connections from an analyzer.

    Both BC-5150 (HL7/MLLP) and BS-240 (HL7/MLLP or ASTM) use this mode:
      - LIS opens a TCP port
      - Analyzer is configured with LIS IP + port
      - Analyzer connects and sends ORU^R01 (HL7) or H/P/O/R records (ASTM)
      - LIS responds with ACK (HL7) or byte-level ACK (ASTM)

    For ASTM protocol (BS-240 ASTM mode), the full ENQ/ACK/EOT handshake
    is handled inside the connection handler.
    """

    def __init__(self, analyzer_row: Analyzer, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service

    async def _handle_hl7_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a connection from an analyzer sending HL7/MLLP."""
        buffer = bytearray()
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            # Process complete MLLP frames
            while VT in buffer and MLLP_END in buffer:
                sb = buffer.find(VT)
                eb = buffer.find(MLLP_END, sb + 1)
                if eb == -1:
                    break
                payload = bytes(buffer[sb: eb + len(MLLP_END)])
                del buffer[: eb + len(MLLP_END)]

                # Process the message
                await self.service.process_payload(
                    analyzer_row=self.analyzer_row,
                    payload=payload,
                    transport="tcp_server_hl7",
                )

                # Send ACK back to analyzer
                ack_bytes = self.service.build_ack_for_payload(self.analyzer_row, payload)
                if ack_bytes:
                    writer.write(ack_bytes)
                    await writer.drain()

    async def _handle_astm_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle a connection from BS-240 in ASTM mode.

        ASTM E1381 handshake:
          Analyzer → ENQ  (I want to send data)
          LIS      → ACK  (OK, go ahead)
          Analyzer → STX frame_no data CR checksum ETX  (data frame)
          LIS      → ACK  (frame received)
          ... more frames ...
          Analyzer → EOT  (done)
          LIS      (processes all accumulated frames)
        """
        message_buffer = bytearray()

        while True:
            byte_data = await reader.read(1)
            if not byte_data:
                break
            byte_val = byte_data[0]

            if byte_val == ENQ:
                # Analyzer wants to transmit — send ACK
                writer.write(bytes([ACK]))
                await writer.drain()
                logger.debug("ASTM ENQ received from %s, sent ACK", self.analyzer_row.name)

            elif byte_val == EOT:
                # End of transmission — process accumulated message
                logger.debug("ASTM EOT from %s, processing %d bytes", self.analyzer_row.name, len(message_buffer))
                if message_buffer:
                    payload = bytes(message_buffer)
                    message_buffer.clear()
                    await self.service.process_payload(
                        analyzer_row=self.analyzer_row,
                        payload=payload,
                        transport="tcp_server_astm",
                    )

            elif byte_val == STX:
                # Start of data frame — read until ETX or ETB
                frame_data = bytearray()
                while True:
                    fb = await reader.read(1)
                    if not fb:
                        break
                    fv = fb[0]
                    if fv in (ETX, ETB):
                        # Read 2-byte checksum after ETX/ETB
                        await reader.read(2)
                        break
                    if fv != CR:  # skip leading frame number byte
                        frame_data.extend(fb)
                # Strip first byte (frame sequence number)
                if frame_data:
                    message_buffer.extend(frame_data[1:])
                    message_buffer.extend(b"\r")
                # Acknowledge the frame
                writer.write(bytes([ACK]))
                await writer.drain()

    async def handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.info(
            "Analyzer connected to LIS: name=%s peer=%s",
            self.analyzer_row.name,
            peer,
        )
        try:
            protocol_type = (getattr(self.analyzer_row, "protocol_type", None) or "hl7").lower()
            if protocol_type == "astm":
                await self._handle_astm_connection(reader, writer)
            else:
                # HL7/MLLP (default, covers BC-5150 and BS-240 HL7 mode)
                await self._handle_hl7_connection(reader, writer)
        except asyncio.IncompleteReadError:
            logger.debug("Analyzer %s closed connection", self.analyzer_row.name)
        except Exception:
            logger.exception("Error handling connection from analyzer %s", self.analyzer_row.name)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("Analyzer disconnected: name=%s peer=%s", self.analyzer_row.name, peer)

    async def run(self) -> None:
        host = "0.0.0.0"  # Listen on all interfaces
        port = self.analyzer_row.tcp_port
        if not port:
            logger.error(
                "No tcp_port configured for analyzer %s — cannot start TCP server listener",
                self.analyzer_row.name,
            )
            return

        try:
            server = await asyncio.start_server(self.handle, host, port)
        except OSError as e:
            logger.error(
                "Cannot start TCP server for analyzer %s on port %d: %s",
                self.analyzer_row.name,
                port,
                e,
            )
            return

        logger.info(
            "Analyzer TCP server listening: analyzer=%s port=%d protocol=%s",
            self.analyzer_row.name,
            port,
            getattr(self.analyzer_row, "protocol_type", "hl7"),
        )
        async with server:
            await server.serve_forever()


# ===========================================================================
# TCP CLIENT LISTENER (LIS connects out to analyzer)
# ===========================================================================

class AnalyzerTCPClientListener:
    """
    LIS connects to a static-IP analyzer as a TCP client.
    Less common but supported for analyzers that act as servers.
    """

    def __init__(self, analyzer_row: Analyzer, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service
        self.reconnect_delay = 5.0

    async def run(self) -> None:
        host = self.analyzer_row.tcp_ip
        port = self.analyzer_row.tcp_port
        if not host or not port:
            logger.error("Analyzer %s missing tcp_ip/tcp_port for tcp_client mode", self.analyzer_row.name)
            return

        while True:
            try:
                logger.info("Connecting to analyzer %s at %s:%d", self.analyzer_row.name, host, port)
                reader, writer = await asyncio.open_connection(host, port)
                buffer = bytearray()

                while True:
                    chunk = await reader.read(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)

                    while VT in buffer and MLLP_END in buffer:
                        sb = buffer.find(VT)
                        eb = buffer.find(MLLP_END, sb + 1)
                        if eb == -1:
                            break
                        payload = bytes(buffer[sb: eb + len(MLLP_END)])
                        del buffer[: eb + len(MLLP_END)]

                        await self.service.process_payload(
                            analyzer_row=self.analyzer_row,
                            payload=payload,
                            transport="tcp_client",
                        )

                        ack_bytes = self.service.build_ack_for_payload(self.analyzer_row, payload)
                        if ack_bytes:
                            writer.write(ack_bytes)
                            await writer.drain()

                writer.close()
                await writer.wait_closed()
                logger.info("Analyzer %s closed connection, will reconnect in %ss", self.analyzer_row.name, self.reconnect_delay)

            except Exception:
                logger.exception("TCP client listener error for analyzer %s", self.analyzer_row.name)

            await asyncio.sleep(self.reconnect_delay)


# ===========================================================================
# SERIAL LISTENER
# ===========================================================================

class AnalyzerSerialListener:
    """
    Serial/RS-232 connection listener.
    Supports both MLLP-framed HL7 and raw ASTM over serial.
    """

    def __init__(self, analyzer_row: Analyzer, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service

    async def run(self) -> None:
        try:
            import serial  # type: ignore[import]
        except ImportError:
            logger.error("pyserial not installed — cannot start serial listener for %s", self.analyzer_row.name)
            return

        serial_port = self.analyzer_row.serial_port
        baud_rate = self.analyzer_row.baud_rate or 9600

        if not serial_port:
            logger.error("Analyzer %s missing serial_port", self.analyzer_row.name)
            return

        logger.info("Serial listener starting: analyzer=%s port=%s baud=%d", self.analyzer_row.name, serial_port, baud_rate)
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        buffer = bytearray()

        try:
            while True:
                chunk = ser.read(4096)
                if not chunk:
                    await asyncio.sleep(0.05)
                    continue
                buffer.extend(chunk)

                if VT in buffer and MLLP_END in buffer:
                    sb = buffer.find(VT)
                    eb = buffer.find(MLLP_END, sb + 1)
                    if eb != -1:
                        payload = bytes(buffer[sb: eb + len(MLLP_END)])
                        del buffer[: eb + len(MLLP_END)]
                        await self.service.process_payload(
                            analyzer_row=self.analyzer_row,
                            payload=payload,
                            transport="serial",
                        )
                elif CR in buffer:
                    payload = bytes(buffer)
                    buffer.clear()
                    await self.service.process_payload(
                        analyzer_row=self.analyzer_row,
                        payload=payload,
                        transport="serial",
                    )
        finally:
            ser.close()


# ===========================================================================
# WORKER MANAGER — orchestrates all analyzer listeners
# ===========================================================================

# ===========================================================================
# AUTO-DISCOVERY: fingerprint an unknown device from its first message
# ===========================================================================

# Known device fingerprints — matched against the first payload from a device
# Each entry: (label, name, manufacturer, model, transport_type, protocol_type, result_format)
_DEVICE_FINGERPRINTS: list[tuple[str, str, str, str, str, str, str]] = [
    # HL7 MSH-3 (sending application) patterns
    ("bc5150",  "Mindray BC-5150",  "Mindray", "BC-5150", "tcp_server", "hl7",  "HL7"),
    ("bc-5150", "Mindray BC-5150",  "Mindray", "BC-5150", "tcp_server", "hl7",  "HL7"),
    ("bc5000",  "Mindray BC-5000",  "Mindray", "BC-5000", "tcp_server", "hl7",  "HL7"),
    ("bs240",   "Mindray BS-240",   "Mindray", "BS-240",  "tcp_server", "hl7",  "HL7"),
    ("bs-240",  "Mindray BS-240",   "Mindray", "BS-240",  "tcp_server", "hl7",  "HL7"),
    ("bs480",   "Mindray BS-480",   "Mindray", "BS-480",  "tcp_server", "hl7",  "HL7"),
    ("bs-480",  "Mindray BS-480",   "Mindray", "BS-480",  "tcp_server", "hl7",  "HL7"),
    ("sysmex",  "Sysmex XN-Series", "Sysmex",  "XN",      "tcp_server", "hl7",  "HL7"),
    ("cobas",   "Roche Cobas",      "Roche",   "Cobas",   "tcp_server", "hl7",  "HL7"),
    # ASTM H-record sender patterns
    ("bs-240",  "Mindray BS-240",   "Mindray", "BS-240",  "tcp_server", "astm", "ASTM"),
    ("mindray", "Mindray Analyzer", "Mindray", "Unknown", "tcp_server", "hl7",  "HL7"),
]


def _fingerprint_payload(payload: bytes, peer_ip: str, port: int) -> dict | None:
    """
    Examine the first payload from an unknown device and return a dict of
    Analyzer fields if we can identify the device, or None if unknown.

    Strategies (in order):
      1. MLLP-wrapped HL7 → parse MSH-3 (sending application) and MSH-4 (facility)
      2. ASTM H record    → parse H|...|sender_name field
      3. Raw HL7 (no MLLP wrapping)
      4. Fallback: create a generic "Unknown Analyzer @ {ip}:{port}" entry
    """
    text = payload.decode("utf-8", errors="replace").strip()

    # ── 1. HL7/MLLP ────────────────────────────────────────────────────────
    if VT in payload:
        messages = unwrap_mllp(payload)
        for msg in messages:
            if msg.startswith("MSH"):
                fields = msg.split("|")
                sending_app = (fields[2] if len(fields) > 2 else "").lower().strip()
                sending_fac = (fields[3] if len(fields) > 3 else "").lower().strip()
                combined = f"{sending_app} {sending_fac}"
                for key, name, mfr, model, tt, pt, rf in _DEVICE_FINGERPRINTS:
                    if key in combined:
                        return dict(
                            name=name, manufacturer=mfr, model=model,
                            transport_type=tt, protocol_type=pt,
                            result_format=rf, connection_type="tcp",
                            tcp_ip=peer_ip, tcp_port=port,
                            is_automated=True, is_active=True,
                            notes=f"Auto-registered on first contact from {peer_ip}:{port}",
                        )
                # Unknown HL7 device — register generically with sender app name
                app_label = (fields[2] if len(fields) > 2 else "Unknown").strip()
                return dict(
                    name=f"{app_label} @ {peer_ip}" if app_label else f"HL7-Device @ {peer_ip}",
                    manufacturer=None, model=None,
                    transport_type="tcp_server", protocol_type="hl7",
                    result_format="HL7", connection_type="tcp",
                    tcp_ip=peer_ip, tcp_port=port,
                    is_automated=True, is_active=True,
                    notes=f"Auto-registered HL7 device from {peer_ip}:{port}. MSH-3={fields[2] if len(fields)>2 else '?'}",
                )

    # ── 2. ASTM H record ────────────────────────────────────────────────────
    if text.startswith("H|") or text.startswith("\x02H|") or "\rH|" in text:
        # H|delimiter|message_ctrl|...|sender_name|...
        lines = text.replace("\x02", "").replace("\x03", "").split("\r")
        h_line = next((l for l in lines if l.startswith("H|")), None)
        if h_line:
            h_fields = h_line.split("|")
            sender = (h_fields[4] if len(h_fields) > 4 else "").lower().strip()
            for key, name, mfr, model, tt, pt, rf in _DEVICE_FINGERPRINTS:
                if key in sender or key in text.lower():
                    return dict(
                        name=name, manufacturer=mfr, model=model,
                        transport_type="tcp_server", protocol_type="astm",
                        result_format="ASTM", connection_type="tcp",
                        tcp_ip=peer_ip, tcp_port=port,
                        is_automated=True, is_active=True,
                        notes=f"Auto-registered ASTM device from {peer_ip}:{port}",
                    )
        return dict(
            name=f"ASTM-Device @ {peer_ip}",
            manufacturer=None, model=None,
            transport_type="tcp_server", protocol_type="astm",
            result_format="ASTM", connection_type="tcp",
            tcp_ip=peer_ip, tcp_port=port,
            is_automated=True, is_active=True,
            notes=f"Auto-registered ASTM device from {peer_ip}:{port}",
        )

    # ── 3. Raw HL7 (no MLLP) ───────────────────────────────────────────────
    if text.startswith("MSH|"):
        fields = text.split("|")
        app_label = (fields[2] if len(fields) > 2 else "Unknown").strip()
        combined = app_label.lower()
        for key, name, mfr, model, tt, pt, rf in _DEVICE_FINGERPRINTS:
            if key in combined:
                return dict(
                    name=name, manufacturer=mfr, model=model,
                    transport_type="tcp_server", protocol_type="hl7",
                    result_format="HL7", connection_type="tcp",
                    tcp_ip=peer_ip, tcp_port=port,
                    is_automated=True, is_active=True,
                    notes=f"Auto-registered on first contact from {peer_ip}:{port}",
                )
        return dict(
            name=f"{app_label} @ {peer_ip}" if app_label else f"HL7-Device @ {peer_ip}",
            manufacturer=None, model=None,
            transport_type="tcp_server", protocol_type="hl7",
            result_format="HL7", connection_type="tcp",
            tcp_ip=peer_ip, tcp_port=port,
            is_automated=True, is_active=True,
            notes=f"Auto-registered from {peer_ip}:{port}",
        )

    # ── 4. Completely unknown ───────────────────────────────────────────────
    return None


async def _auto_register_analyzer(fingerprint: dict) -> Analyzer | None:
    """
    Look up an analyzer by name (or tcp_ip+tcp_port).  If it already exists,
    return it.  Otherwise INSERT a new Analyzer row and return it.
    """
    async with AsyncSessionLocal() as session:
        # Check by name first
        existing = (await session.execute(
            select(Analyzer).where(Analyzer.name == fingerprint["name"])
        )).scalar_one_or_none()

        if existing:
            logger.info(
                "Auto-discovery: analyzer already registered — name=%s id=%s",
                existing.name, existing.id,
            )
            return existing

        # Check by IP+port (in case same device reconnects with different MSH-3)
        if fingerprint.get("tcp_ip") and fingerprint.get("tcp_port"):
            existing = (await session.execute(
                select(Analyzer).where(
                    Analyzer.tcp_ip == fingerprint["tcp_ip"],
                    Analyzer.tcp_port == fingerprint["tcp_port"],
                )
            )).scalar_one_or_none()
            if existing:
                logger.info(
                    "Auto-discovery: analyzer already registered by IP:port — name=%s id=%s",
                    existing.name, existing.id,
                )
                return existing

        # Create new
        analyzer = Analyzer(**fingerprint)
        session.add(analyzer)
        try:
            await session.commit()
            await session.refresh(analyzer)
            logger.info(
                "Auto-discovery: NEW analyzer registered — name=%s id=%s ip=%s port=%s protocol=%s",
                analyzer.name, analyzer.id,
                fingerprint.get("tcp_ip"), fingerprint.get("tcp_port"),
                fingerprint.get("protocol_type"),
            )
            return analyzer
        except Exception:
            await session.rollback()
            logger.exception("Auto-discovery: failed to register analyzer %s", fingerprint.get("name"))
            return None


class AnalyzerDiscoveryListener:
    """
    Catch-all TCP server that listens on one or more well-known discovery ports.

    When ANY device connects (even one not yet in the DB), it:
      1. Reads the first chunk of data (the first HL7 or ASTM message)
      2. Fingerprints the device (model/manufacturer/protocol)
      3. Auto-registers it in the DB as an Analyzer row
      4. Processes the message through the normal ingestion pipeline
      5. Future connections from that device are handled by a dedicated
         AnalyzerTCPServerListener started by AnalyzerWorkerManager on reload

    This solves the bootstrap problem: "no analyzers in DB → nothing listening"
    """

    # Default well-known ports to listen on when discovery mode is active.
    # Covers Mindray BC-5150 (3001), BS-240 (3000), and a spare (3002).
    DEFAULT_DISCOVERY_PORTS: list[int] = [3000, 3001, 3002]

    def __init__(
        self,
        service: AnalyzerIngestionService,
        ports: list[int] | None = None,
    ) -> None:
        self.service = service
        self.ports = ports or self.DEFAULT_DISCOVERY_PORTS
        self._servers: list[asyncio.AbstractServer] = []
        self._spawned_listeners: dict[int, asyncio.Task[Any]] = {}  # analyzer_id → task

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        listen_port: int,
    ) -> None:
        """Handle one inbound connection in discovery mode."""
        peer = writer.get_extra_info("peername") or ("unknown", 0)
        peer_ip = peer[0] if peer else "unknown"
        logger.info(
            "Discovery listener: connection from %s on port %d",
            peer_ip, listen_port,
        )

        # ── Read the first chunk ────────────────────────────────────────────
        try:
            first_chunk = await asyncio.wait_for(reader.read(8192), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("Discovery: timeout waiting for first data from %s", peer_ip)
            writer.close()
            return
        except Exception:
            logger.exception("Discovery: error reading from %s", peer_ip)
            writer.close()
            return

        if not first_chunk:
            logger.debug("Discovery: empty first chunk from %s — closing", peer_ip)
            writer.close()
            return

        # ── Fingerprint ─────────────────────────────────────────────────────
        fingerprint = _fingerprint_payload(first_chunk, peer_ip, listen_port)
        if fingerprint is None:
            logger.warning(
                "Discovery: cannot fingerprint payload from %s:%d — "
                "registering as generic device (payload preview: %r)",
                peer_ip, listen_port, first_chunk[:80],
            )
            fingerprint = dict(
                name=f"Unknown-Device @ {peer_ip}:{listen_port}",
                manufacturer=None, model=None,
                transport_type="tcp_server", protocol_type="hl7",
                result_format="HL7", connection_type="tcp",
                tcp_ip=peer_ip, tcp_port=listen_port,
                is_automated=True, is_active=True,
                notes=(
                    f"Auto-registered unknown device from {peer_ip}:{listen_port}. "
                    f"Payload preview: {first_chunk[:80]!r}"
                ),
            )

        # ── Auto-register in DB ─────────────────────────────────────────────
        analyzer_row = await _auto_register_analyzer(fingerprint)
        if analyzer_row is None:
            logger.error("Discovery: could not register device from %s — dropping connection", peer_ip)
            writer.close()
            return

        # ── Spawn a dedicated listener for this analyzer if not already running ──
        analyzer_id = analyzer_row.id
        existing_task = self._spawned_listeners.get(analyzer_id)
        if existing_task is None or existing_task.done():
            dedicated = AnalyzerTCPServerListener(analyzer_row, self.service)
            task = asyncio.create_task(
                dedicated.run(),
                name=f"analyzer-listener-{analyzer_id}-spawned",
            )
            self._spawned_listeners[analyzer_id] = task
            logger.info(
                "Discovery: spawned dedicated listener for %s on port %d",
                analyzer_row.name,
                analyzer_row.tcp_port or listen_port,
            )

        # ── Process THIS first message through the ingestion pipeline ────────
        protocol_type = (getattr(analyzer_row, "protocol_type", None) or "hl7").lower()
        transport_label = "tcp_discovery_hl7" if "hl7" in protocol_type else "tcp_discovery_astm"
        await self.service.process_payload(
            analyzer_row=analyzer_row,
            payload=first_chunk,
            transport=transport_label,
        )

        # ── Send ACK if HL7 ─────────────────────────────────────────────────
        if "hl7" in protocol_type or VT in first_chunk:
            ack_bytes = self.service.build_ack_for_payload(analyzer_row, first_chunk)
            if ack_bytes:
                try:
                    writer.write(ack_bytes)
                    await writer.drain()
                except Exception:
                    pass

        # ── Continue reading (subsequent messages in same connection) ────────
        # Re-use the HL7 handler logic from AnalyzerTCPServerListener
        dedicated_listener = AnalyzerTCPServerListener(analyzer_row, self.service)
        try:
            if "astm" in protocol_type and VT not in first_chunk:
                await dedicated_listener._handle_astm_connection(reader, writer)
            else:
                await dedicated_listener._handle_hl7_connection(reader, writer)
        except Exception:
            logger.exception("Discovery: error in continued handling for %s", analyzer_row.name)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run(self) -> None:
        """Start all discovery port servers and serve forever."""
        for port in self.ports:
            try:
                server = await asyncio.start_server(
                    lambda r, w, p=port: self._handle_connection(r, w, p),
                    "0.0.0.0",
                    port,
                )
                self._servers.append(server)
                logger.info(
                    "Analyzer discovery listener active on port %d "
                    "(will auto-register any connecting device)",
                    port,
                )
            except OSError as exc:
                logger.warning(
                    "Discovery: cannot bind port %d — %s "
                    "(port may already be in use by a dedicated listener)",
                    port, exc,
                )

        if not self._servers:
            logger.error("Discovery: failed to bind ANY discovery port — giving up")
            return

        # Serve until cancelled
        try:
            await asyncio.gather(*[s.serve_forever() for s in self._servers])
        except asyncio.CancelledError:
            pass
        finally:
            for s in self._servers:
                s.close()

    async def stop(self) -> None:
        """Stop all discovery servers and spawned listener tasks."""
        for s in self._servers:
            s.close()
        for task in self._spawned_listeners.values():
            task.cancel()
        if self._spawned_listeners:
            await asyncio.gather(*self._spawned_listeners.values(), return_exceptions=True)
        self._spawned_listeners.clear()
        logger.info("Discovery listener stopped")


# ===========================================================================
# SERIAL PORT SCANNER  (auto-discovery over RS-232 / USB-Serial)
# ===========================================================================

class SerialPortScanner:
    """
    Scans available serial ports and tries to identify any connected analyzer.

    How it works:
      1. Enumerate all available serial ports (pyserial required)
      2. Open each port at common baud rates (9600, 19200, 38400, 115200)
      3. Send a passive probe (empty bytes / ENQ byte) and read any response
      4. Fingerprint the response
      5. Auto-register in DB and hand off to AnalyzerSerialListener

    NOTE: pyserial is required but optional — serial scanning is skipped
    gracefully if it is not installed.
    """

    COMMON_BAUD_RATES: list[int] = [9600, 19200, 38400, 115200, 57600, 4800, 2400]
    PROBE_TIMEOUT_S: float = 2.0

    def __init__(self, service: AnalyzerIngestionService) -> None:
        self.service = service
        self._spawned_tasks: list[asyncio.Task[Any]] = []

    async def scan_and_register(self) -> list[Analyzer]:
        """
        Scan serial ports and return a list of newly discovered (or already
        registered) Analyzer rows.
        """
        try:
            import serial  # type: ignore
            import serial.tools.list_ports  # type: ignore
        except ImportError:
            logger.info(
                "SerialPortScanner: pyserial not installed — "
                "serial port discovery skipped. Install with: pip install pyserial"
            )
            return []

        discovered: list[Analyzer] = []
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            logger.info("SerialPortScanner: no serial ports found on this system")
            return []

        logger.info("SerialPortScanner: found %d serial port(s): %s",
                    len(ports), [p.device for p in ports])

        for port_info in ports:
            device = port_info.device
            analyzer = await self._probe_port(serial, device)
            if analyzer:
                discovered.append(analyzer)

        return discovered

    async def _probe_port(self, serial_module: Any, device: str) -> Analyzer | None:
        """Open a serial port, probe it, and try to identify the device."""
        for baud in self.COMMON_BAUD_RATES:
            try:
                # Run blocking serial I/O in executor to avoid blocking event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._blocking_probe,
                    serial_module, device, baud,
                )
                if result:
                    payload, used_baud = result
                    logger.info(
                        "SerialPortScanner: got response from %s @ %d baud (%d bytes)",
                        device, used_baud, len(payload),
                    )
                    fingerprint = _fingerprint_payload(payload, device, 0)
                    if fingerprint:
                        # Override connection fields for serial
                        fingerprint.update({
                            "connection_type": "serial",
                            "transport_type": "serial",
                            "serial_port": device,
                            "baud_rate": used_baud,
                            "tcp_ip": None,
                            "tcp_port": None,
                        })
                        analyzer = await _auto_register_analyzer(fingerprint)
                        if analyzer:
                            return analyzer
            except Exception as exc:
                logger.debug("SerialPortScanner: %s @ %d baud — %s", device, baud, exc)

        logger.debug("SerialPortScanner: no analyzer found on %s", device)
        return None

    def _blocking_probe(
        self, serial_module: Any, device: str, baud: int
    ) -> tuple[bytes, int] | None:
        """Blocking probe — must be run in executor."""
        try:
            with serial_module.Serial(
                device, baud,
                timeout=self.PROBE_TIMEOUT_S,
                write_timeout=1.0,
            ) as ser:
                # Send ENQ — ASTM devices respond with ACK or begin transmitting
                ser.write(bytes([ENQ]))
                import time
                time.sleep(self.PROBE_TIMEOUT_S)
                waiting = ser.in_waiting
                if waiting > 0:
                    return ser.read(waiting), baud
        except Exception:
            pass
        return None

    async def start_serial_listeners(self, analyzers: list[Analyzer]) -> list[asyncio.Task[Any]]:
        """Start AnalyzerSerialListener tasks for all discovered serial analyzers."""
        tasks: list[asyncio.Task[Any]] = []
        for analyzer_row in analyzers:
            listener = AnalyzerSerialListener(analyzer_row, self.service)
            task = asyncio.create_task(
                listener.run(),
                name=f"analyzer-serial-listener-{analyzer_row.id}",
            )
            tasks.append(task)
            self._spawned_tasks.append(task)
            logger.info(
                "SerialPortScanner: started serial listener for %s on %s @ %s baud",
                analyzer_row.name,
                getattr(analyzer_row, "serial_port", "?"),
                getattr(analyzer_row, "baud_rate", "?"),
            )
        return tasks


# ===========================================================================
# ANALYZER WORKER MANAGER
# ===========================================================================

class AnalyzerWorkerManager:
    """
    Loads all automated analyzers from the database and starts the appropriate
    listener task for each one based on its transport_type.

    If NO automated analyzers exist in the DB yet, the manager automatically
    enters DISCOVERY MODE:
      - TCP:    AnalyzerDiscoveryListener binds on well-known ports (3000-3002)
                and auto-registers any device that connects
      - Serial: SerialPortScanner probes available COM/USB-serial ports and
                auto-registers any analyzer it finds

    Once a device is discovered and registered, a dedicated listener is spawned
    immediately for that connection so results are not lost.

    Called from FastAPI lifespan (startup/shutdown).
    """

    def __init__(self) -> None:
        self.service = AnalyzerIngestionService()
        self.tasks: list[asyncio.Task[Any]] = []
        self._discovery_listener: AnalyzerDiscoveryListener | None = None
        self._serial_scanner: SerialPortScanner | None = None

    async def start(self) -> list[asyncio.Task[Any]]:
        """Load automated analyzers and start listeners (or discovery mode)."""
        async with AsyncSessionLocal() as session:
            repo = AnalyzerIngestionRepository(session)
            analyzers = await repo.get_automated_analyzers()

        if not analyzers:
            logger.info(
                "No automated analyzers found in DB — starting DISCOVERY MODE. "
                "The LIS will auto-register any analyzer that connects on ports %s "
                "or is found on a serial port.",
                AnalyzerDiscoveryListener.DEFAULT_DISCOVERY_PORTS,
            )
            await self._start_discovery_mode()
            return self.tasks

        # Normal mode — start a dedicated listener for each registered analyzer
        for analyzer_row in analyzers:
            transport_type = (getattr(analyzer_row, "transport_type", None) or "").lower()

            if transport_type == "tcp_server":
                listener = AnalyzerTCPServerListener(analyzer_row, self.service)
            elif transport_type == "tcp_client":
                listener = AnalyzerTCPClientListener(analyzer_row, self.service)
            elif transport_type == "serial":
                listener = AnalyzerSerialListener(analyzer_row, self.service)
            else:
                logger.warning(
                    "Analyzer id=%s name=%s has unknown transport_type=%r — skipping",
                    analyzer_row.id,
                    getattr(analyzer_row, "name", "?"),
                    transport_type,
                )
                continue

            task = asyncio.create_task(
                listener.run(),
                name=f"analyzer-listener-{analyzer_row.id}",
            )
            task.add_done_callback(self._on_task_done)
            self.tasks.append(task)

            logger.info(
                "Started analyzer listener: id=%s name=%s transport=%s protocol=%s",
                analyzer_row.id,
                getattr(analyzer_row, "name", "?"),
                transport_type,
                getattr(analyzer_row, "protocol_type", "?"),
            )

        return self.tasks

    async def _start_discovery_mode(self) -> None:
        """Start TCP discovery listener and serial scanner in background."""
        # TCP discovery
        self._discovery_listener = AnalyzerDiscoveryListener(self.service)
        discovery_task = asyncio.create_task(
            self._discovery_listener.run(),
            name="analyzer-discovery-tcp",
        )
        discovery_task.add_done_callback(self._on_task_done)
        self.tasks.append(discovery_task)

        # Serial scanner (runs once at startup, spawns persistent listeners)
        self._serial_scanner = SerialPortScanner(self.service)
        serial_task = asyncio.create_task(
            self._run_serial_scan(),
            name="analyzer-discovery-serial",
        )
        serial_task.add_done_callback(self._on_task_done)
        self.tasks.append(serial_task)

    async def _run_serial_scan(self) -> None:
        """Run serial scanner and add any spawned tasks to self.tasks."""
        assert self._serial_scanner is not None
        discovered = await self._serial_scanner.scan_and_register()
        new_tasks = await self._serial_scanner.start_serial_listeners(discovered)
        self.tasks.extend(new_tasks)

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        """Callback when a listener task ends unexpectedly."""
        if task.cancelled():
            logger.info("Analyzer listener task cancelled: %s", task.get_name())
        elif task.exception():
            logger.error(
                "Analyzer listener task failed: %s — %s",
                task.get_name(),
                task.exception(),
            )

    async def stop(self) -> None:
        """Cancel all running listener tasks."""
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        if self._discovery_listener:
            await self._discovery_listener.stop()
        logger.info("All analyzer listener tasks stopped")


# ===========================================================================
# SIMULATOR CLASSES (for testing — used by run_simulator.py and API endpoints)
# ===========================================================================

class BC5150Simulator:
    """Programmatic interface to BC5150Simulator (imported from run_simulator if needed)."""

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        msg_ctrl = f"BC{now}"
        message = (
            f"MSH|^~\\&|BC5150|Mindray|||{now}||ORU^R01|{msg_ctrl}|P|2.3.1||||||UNICODE\r"
            f"PID|1||{patient_id}^^^^MR||SimPatient^Test||19850101000000|M\r"
            f"PV1|1||LAB^^BED1\r"
            f"OBR|1|{sample_id}|{sample_id}|00001^CBC^99MRC||{now}||||{sample_id}||||{now}||||||||||HM||||||||tech1\r"
            f"OBX|1|NM|6690-2^WBC^LN||7.20|10*9/L|4.00-10.00|N||||F|||{now}\r"
            f"OBX|2|NM|789-8^RBC^LN||4.80|10*12/L|3.50-5.50|N||||F|||{now}\r"
            f"OBX|3|NM|718-7^HGB^LN||13.8|g/dL|11.0-16.0|N||||F|||{now}\r"
            f"OBX|4|NM|4544-3^HCT^LN||41.2|%|36.0-48.0|N||||F|||{now}\r"
            f"OBX|5|NM|787-2^MCV^LN||85.8|fL|80.0-100.0|N||||F|||{now}\r"
            f"OBX|6|NM|785-6^MCH^LN||28.8|pg|27.0-34.0|N||||F|||{now}\r"
            f"OBX|7|NM|786-4^MCHC^LN||33.5|g/dL|31.0-37.0|N||||F|||{now}\r"
            f"OBX|8|NM|777-3^PLT^LN||218.0|10*9/L|150.0-400.0|N||||F|||{now}\r"
        )
        mllp_payload = wrap_mllp(message)
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(mllp_payload)
            await writer.drain()
            try:
                ack = await asyncio.wait_for(reader.read(4096), timeout=10.0)
                logger.info("BC5150Simulator ACK: %r", ack[:50] if ack else b"(none)")
            except asyncio.TimeoutError:
                logger.warning("BC5150Simulator: ACK timeout")
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            logger.exception("BC5150Simulator.send failed")
            return False


class BS240HL7Simulator:
    """Sends a BS-240 chemistry HL7 result to the LIS."""

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        barcode = f"BAR-{sample_id}"
        msg_ctrl = f"BS{now}"
        message = (
            f"MSH|^~\\&|BS240|Mindray|||{now}||ORU^R01|{msg_ctrl}|P|2.3.1||||0||ASCII|||\r"
            f"PID|1|{patient_id}|||SimPatient^Test||19900101000000|M\r"
            f"OBR|1|{barcode}|{sample_id}|Chemistry^BS240||{now}|{now}|||phlebotomist|||Clinical chem|{now}|Serum|sender1|Chemistry\r"
            f"OBX|1|NM|TBIL|TBil|14.2|umol/L|5.0-21.0|N|||F||14.2|{now}|CHEM|tech1\r"
            f"OBX|2|NM|ALT|ALT|22.4|U/L|0-40|N|||F||22.4|{now}|CHEM|tech1\r"
            f"OBX|3|NM|AST|AST|19.1|U/L|0-40|N|||F||19.1|{now}|CHEM|tech1\r"
            f"OBX|4|NM|ALP|ALP|78.3|U/L|38-126|N|||F||78.3|{now}|CHEM|tech1\r"
            f"OBX|5|NM|BUN|BUN|5.2|mmol/L|2.9-8.2|N|||F||5.2|{now}|CHEM|tech1\r"
            f"OBX|6|NM|CREA|Creatinine|78.5|umol/L|53-115|N|||F||78.5|{now}|CHEM|tech1\r"
            f"OBX|7|NM|GLU|Glucose|5.1|mmol/L|3.9-6.1|N|||F||5.1|{now}|CHEM|tech1\r"
        )
        mllp_payload = wrap_mllp(message)
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(mllp_payload)
            await writer.drain()
            try:
                ack = await asyncio.wait_for(reader.read(4096), timeout=10.0)
                logger.info("BS240HL7Simulator ACK: %r", ack[:50] if ack else b"(none)")
            except asyncio.TimeoutError:
                logger.warning("BS240HL7Simulator: ACK timeout")
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            logger.exception("BS240HL7Simulator.send failed")
            return False


class BS240ASTMSimulator:
    """Sends a BS-240 chemistry ASTM E1394-97 result to the LIS."""

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        barcode = f"BAR-{sample_id}"

        records = [
            f"H|\\^&|||BS240^Mindray^1.0|||||||P|E 1394-97|{now}",
            f"P|1|{patient_id}|||SimPatient^Test||19900101|M",
            f"O|1|{sample_id}|{barcode}|^^^CHEM||{now}|{now}|||N||||Serum",
            "R|1|TBIL|14.2|umol/L|5.0-21.0|N|||F",
            "R|2|ALT|22.4|U/L|0-40|N|||F",
            "R|3|AST|19.1|U/L|0-40|N|||F",
            "R|4|GLU|5.1|mmol/L|3.9-6.1|N|||F",
            "L|1|N",
        ]

        def _astm_checksum(data: bytes) -> str:
            return f"{sum(data) % 256:02X}"

        def _build_frame(frame_no: int, data: str, is_last: bool) -> bytes:
            fn = str(frame_no % 8).encode("ascii")
            content = data.encode("ascii")
            end_byte = b"\x03" if is_last else b"\x17"
            chk = _astm_checksum(fn + content + end_byte).encode("ascii")
            return b"\x02" + fn + content + end_byte + chk + b"\r\n"

        try:
            reader, writer = await asyncio.open_connection(host, port)
            # Send ENQ
            writer.write(bytes([0x05]))
            await writer.drain()
            resp = await asyncio.wait_for(reader.read(1), timeout=5.0)
            if not resp or resp[0] != 0x06:
                logger.error("BS240ASTMSimulator: no ACK after ENQ")
                writer.close()
                return False

            for i, rec in enumerate(records):
                frame = _build_frame(i + 1, rec, is_last=(i == len(records) - 1))
                writer.write(frame)
                await writer.drain()
                try:
                    await asyncio.wait_for(reader.read(1), timeout=3.0)
                except asyncio.TimeoutError:
                    pass

            writer.write(bytes([0x04]))  # EOT
            await writer.drain()
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("BS240ASTMSimulator: sent %d records", len(records))
            return True
        except Exception:
            logger.exception("BS240ASTMSimulator.send failed")
            return False


# ===========================================================================
# MODULE-LEVEL SINGLETON (used by FastAPI lifespan)
# ===========================================================================

_worker_manager = AnalyzerWorkerManager()


async def start_analyzer_workers() -> list[asyncio.Task[Any]]:
    """Start all analyzer listener workers. Called on FastAPI startup."""
    return await _worker_manager.start()


async def stop_analyzer_workers() -> None:
    """Stop all analyzer listener workers. Called on FastAPI shutdown."""
    await _worker_manager.stop()