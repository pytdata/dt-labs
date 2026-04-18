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
from app.models.lab import AnalyzerIngestion

logger = logging.getLogger(__name__)

VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"
MLLP_END = FS + CR


# -----------------------------------------------------------------------------
# OPTIONAL IMPORTS FROM YOUR PROJECT
# -----------------------------------------------------------------------------
# The service is wired to a typical FastAPI structure. If your exact model names or
# paths differ, only adjust the import section below.

try:
    from app.models.catalog import Analyzer
except Exception:  # pragma: no cover
    Analyzer = None  # type: ignore

try:
    from app.models.lab import Patient
except Exception:  # pragma: no cover
    Patient = None  # type: ignore

try:
    from app.models.lab_test import LabTest
except Exception:  # pragma: no cover
    LabTest = None  # type: ignore

try:
    from app.models.lab_result import LabResult
except Exception:  # pragma: no cover
    LabResult = None  # type: ignore


# -----------------------------------------------------------------------------
# PARSED MESSAGE MODELS
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# LOW-LEVEL HELPERS
# -----------------------------------------------------------------------------

def wrap_mllp(message: str) -> bytes:
    return VT + message.encode("utf-8") + MLLP_END


def unwrap_mllp(payload: bytes) -> list[str]:
    messages: list[str] = []
    start = 0
    while True:
        sb = payload.find(VT, start)
        if sb == -1:
            break
        eb = payload.find(MLLP_END, sb + 1)
        if eb == -1:
            break
        body = payload[sb + 1 : eb]
        messages.append(body.decode("utf-8", errors="replace"))
        start = eb + len(MLLP_END)
    return messages


def parse_hl7_message(message: str) -> dict[str, list[list[str]]]:
    segments: dict[str, list[list[str]]] = {}
    for raw_segment in [seg for seg in message.split("\r") if seg.strip()]:
        fields = raw_segment.split("|")
        seg_name = fields[0]
        segments.setdefault(seg_name, []).append(fields)
    return segments


def get_field(fields: list[str], idx: int) -> str | None:
    return fields[idx] if idx < len(fields) and fields[idx] != "" else None


def split_coded(value: str | None) -> tuple[str | None, str | None, str | None]:
    if not value:
        return None, None, None
    parts = value.split("^")
    return (
        parts[0] if len(parts) > 0 else None,
        parts[1] if len(parts) > 1 else None,
        parts[2] if len(parts) > 2 else None,
    )


def decode_hl7_escapes(value: str) -> str:
    return (
        value.replace(r"\F\", "|")
        .replace(r"\S\", "^")
        .replace(r"\T\", "&")
        .replace(r"\R\", "~")
        .replace(r"\E\", "\\")
        .replace(r"\.br\", "\r")
    )


# -----------------------------------------------------------------------------
# PARSERS
# -----------------------------------------------------------------------------

class AnalyzerParser:
    analyzer_name: str

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        raise NotImplementedError

    def build_ack(self, incoming_message: str, accepted: bool = True, error_text: str | None = None) -> str:
        segments = parse_hl7_message(incoming_message)
        msh = segments["MSH"][0]
        control_id = get_field(msh, 9) or "1"
        processing_id = get_field(msh, 10) or "P"
        charset = get_field(msh, 17) or "UNICODE"
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        ack_code = "AA" if accepted else "AE"
        ack_msh = f"MSH|^~\\&|LIS||||{now}||ACK^R01|1|{processing_id}|2.3.1||||||{charset}"
        msa = f"MSA|{ack_code}|{control_id}"
        if error_text and not accepted:
            msa += f"|{error_text}"
        return ack_msh + "\r" + msa + "\r"


class MindrayBC5150Parser(AnalyzerParser):
    analyzer_name = "Mindray BC-5150"

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        segments = parse_hl7_message(message)
        msh = segments["MSH"][0]
        pid = segments.get("PID", [["PID"]])[0]
        obr = segments["OBR"][0]
        obx_segments = segments.get("OBX", [])

        patient_id = split_coded(get_field(pid, 3))[0] if get_field(pid, 3) else None
        patient_name = get_field(pid, 5)
        sample_id = get_field(obr, 3)
        ordered_at = get_field(obr, 14)
        observed_at = get_field(obr, 7)
        operator = get_field(obr, 32)

        observations: list[Observation] = []
        for seg in obx_segments:
            code, name, system = split_coded(get_field(seg, 3))
            observations.append(
                Observation(
                    code=code or "",
                    name=name or "",
                    coding_system=system or "",
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
            notes="BC-5150 result parsed from HL7 ORU^R01",
            patient_name=patient_name,
            observations=observations,
        )


class MindrayBS240HL7Parser(AnalyzerParser):
    analyzer_name = "Mindray BS-240"

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        segments = parse_hl7_message(message)
        msh = segments["MSH"][0]
        pid = segments.get("PID", [["PID"]])[0]
        obr = segments["OBR"][0]
        obx_segments = segments.get("OBX", [])

        patient_id = get_field(pid, 2) or split_coded(get_field(pid, 3))[0]
        patient_name = get_field(pid, 5)
        sample_barcode = get_field(obr, 2)
        sample_id = get_field(obr, 3)
        ordered_at = get_field(obr, 6)
        observed_at = get_field(obr, 7)
        operator = get_field(obr, 16) or get_field(obr, 34)

        observations: list[Observation] = []
        for seg in obx_segments:
            observations.append(
                Observation(
                    code=get_field(seg, 3) or "",
                    name=get_field(seg, 4) or "",
                    coding_system="",
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
            match_method="sample_id" if sample_id else "sample_barcode" if sample_barcode else "patient_id",
            match_value=sample_id or sample_barcode or patient_id or test_no,
            raw_message=message,
            notes="BS-240 result parsed from HL7 ORU^R01",
            patient_name=patient_name,
            observations=observations,
        )


class MindrayBS240ASTMParser(AnalyzerParser):
    analyzer_name = "Mindray BS-240"

    def parse(self, message: str, transport: str) -> ParsedAnalyzerMessage:
        records = [line for line in message.split("\r") if line.strip()]
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
                patient_id = fields[2] if len(fields) > 2 and fields[2] else None
                patient_name = fields[5] if len(fields) > 5 and fields[5] else None
            elif record_type == "O":
                sample_id = fields[2] if len(fields) > 2 and fields[2] else None
                sample_barcode = fields[3] if len(fields) > 3 and fields[3] else None
                ordered_at = fields[6] if len(fields) > 6 and fields[6] else None
                observed_at = fields[7] if len(fields) > 7 and fields[7] else None
                operator = fields[15] if len(fields) > 15 and fields[15] else None
            elif record_type == "R":
                observations.append(
                    Observation(
                        code=fields[2] if len(fields) > 2 else "",
                        name=fields[3] if len(fields) > 3 else "",
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
            match_method="sample_id" if sample_id else "sample_barcode" if sample_barcode else "patient_id",
            match_value=sample_id or sample_barcode or patient_id or test_no,
            raw_message=message,
            notes="BS-240 result parsed from ASTM",
            patient_name=patient_name,
            observations=observations,
        )


# -----------------------------------------------------------------------------
# REPOSITORY / DB OPERATIONS
# -----------------------------------------------------------------------------

class AnalyzerIngestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_automated_analyzers(self) -> list[Any]:
        if Analyzer is None:
            return []
        result = await self.session.execute(
            select(Analyzer).where(
                Analyzer.is_active == True,  # noqa: E712
                Analyzer.is_automated == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_analyzer_by_id(self, analyzer_id: int) -> Any | None:
        if Analyzer is None:
            return None
        result = await self.session.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
        return result.scalar_one_or_none()

    async def resolve_patient_id(self, parsed: ParsedAnalyzerMessage) -> int | None:
        if Patient is None or not parsed.patient_id:
            return int(parsed.patient_id) if parsed.patient_id and parsed.patient_id.isdigit() else None

        candidate_fields = ["id", "patient_id", "mrn"]
        for field_name in candidate_fields:
            if hasattr(Patient, field_name):
                field = getattr(Patient, field_name)
                result = await self.session.execute(select(Patient).where(field == parsed.patient_id))
                patient = result.scalar_one_or_none()
                if patient is not None:
                    return getattr(patient, "id")
        return None

    async def resolve_lab_test(self, parsed: ParsedAnalyzerMessage) -> Any | None:
        if LabTest is None:
            return None

        candidate_values = [parsed.sample_id, parsed.sample_barcode, parsed.test_no, parsed.patient_id]
        candidate_values = [value for value in candidate_values if value]
        candidate_fields = ["id", "test_no", "sample_id", "barcode"]

        for value in candidate_values:
            for field_name in candidate_fields:
                if hasattr(LabTest, field_name):
                    field = getattr(LabTest, field_name)
                    result = await self.session.execute(select(LabTest).where(field == value))
                    lab_test = result.scalar_one_or_none()
                    if lab_test is not None:
                        return lab_test
        return None

    async def save_ingestion(self, analyzer_row: Any, parsed: ParsedAnalyzerMessage) -> AnalyzerIngestion:
        patient_id = await self.resolve_patient_id(parsed)
        lab_test = await self.resolve_lab_test(parsed)
        test_no_value = str(getattr(lab_test, "id")) if lab_test is not None else parsed.test_no

        row = AnalyzerIngestion(
            analyzer_id=analyzer_row.id,
            patient_id=patient_id,
            test_no=test_no_value,
            match_method=parsed.match_method,
            match_value=parsed.match_value,
            notes=parsed.notes,
            analyzer_message=parsed.raw_message,
            analyzer=parsed.analyzer_name,
            normalized_payload=json.dumps(parsed.to_dict(), ensure_ascii=False),
            ingest_status="matched" if lab_test is not None else "unmatched",
            raw_message_type=parsed.message_type,
            transport_type=parsed.transport,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update_lab_test_and_results(self, analyzer_row: Any, parsed: ParsedAnalyzerMessage) -> None:
        if LabTest is None:
            return

        lab_test = await self.resolve_lab_test(parsed)
        if lab_test is None:
            logger.warning("No lab_test match for analyzer payload. test_no=%s", parsed.test_no)
            return

        if hasattr(lab_test, "status"):
            setattr(lab_test, "status", "completed")
        if hasattr(lab_test, "result_source"):
            setattr(lab_test, "result_source", "analyzer")
        if hasattr(lab_test, "is_result_populated"):
            setattr(lab_test, "is_result_populated", True)
        if hasattr(lab_test, "completed_at"):
            setattr(lab_test, "completed_at", datetime.utcnow())

        # Optional direct write into lab_result table if your project has one.
        if LabResult is not None:
            for obs in parsed.observations:
                result_row = LabResult()
                if hasattr(result_row, "lab_test_id"):
                    setattr(result_row, "lab_test_id", getattr(lab_test, "id"))
                if hasattr(result_row, "test_no"):
                    setattr(result_row, "test_no", str(getattr(lab_test, "id")))
                if hasattr(result_row, "analyte_code"):
                    setattr(result_row, "analyte_code", obs.code)
                if hasattr(result_row, "analyte_name"):
                    setattr(result_row, "analyte_name", obs.name)
                if hasattr(result_row, "result_value"):
                    setattr(result_row, "result_value", obs.value)
                if hasattr(result_row, "units"):
                    setattr(result_row, "units", obs.units)
                if hasattr(result_row, "reference_range"):
                    setattr(result_row, "reference_range", obs.reference_range)
                if hasattr(result_row, "abnormal_flag"):
                    setattr(result_row, "abnormal_flag", obs.abnormal_flag)
                if hasattr(result_row, "status"):
                    setattr(result_row, "status", obs.result_status or "F")
                if hasattr(result_row, "source"):
                    setattr(result_row, "source", analyzer_row.name if hasattr(analyzer_row, "name") else parsed.analyzer_name)
                if hasattr(result_row, "raw_payload"):
                    setattr(result_row, "raw_payload", obs.raw_segment)
                self.session.add(result_row)


# -----------------------------------------------------------------------------
# SERVICE
# -----------------------------------------------------------------------------

class AnalyzerIngestionService:
    def __init__(self) -> None:
        self.bc5150_parser = MindrayBC5150Parser()
        self.bs240_hl7_parser = MindrayBS240HL7Parser()
        self.bs240_astm_parser = MindrayBS240ASTMParser()

    def detect_parser(self, analyzer_name: str, protocol_type: str | None, payload: bytes):
        raw_text = payload.decode("utf-8", errors="replace")
        normalized_protocol = (protocol_type or "auto").lower()

        if analyzer_name == "Mindray BC-5150":
            return self.bc5150_parser

        if analyzer_name == "Mindray BS-240":
            if normalized_protocol == "hl7":
                return self.bs240_hl7_parser
            if normalized_protocol == "astm":
                return self.bs240_astm_parser
            if raw_text.startswith("H|") or "\rH|" in raw_text:
                return self.bs240_astm_parser
            return self.bs240_hl7_parser

        if normalized_protocol == "astm":
            return self.bs240_astm_parser
        return self.bs240_hl7_parser

    async def ingest_payload(
        self,
        analyzer_id: int,
        analyzer_name: str,
        protocol_type: str | None,
        is_automated: bool,
        payload: bytes,
        transport: str,
    ) -> list[AnalyzerIngestion]:
        if not is_automated:
            logger.info("Analyzer %s is not automated; ignoring incoming payload", analyzer_name)
            return []

        parser = self.detect_parser(analyzer_name, protocol_type, payload)
        extracted_messages = unwrap_mllp(payload)
        raw_messages = extracted_messages or [payload.decode("utf-8", errors="replace")]
        saved_rows: list[AnalyzerIngestion] = []

        async with AsyncSessionLocal() as session:
            repo = AnalyzerIngestionRepository(session)
            analyzer_row = await repo.get_analyzer_by_id(analyzer_id)
            if analyzer_row is None:
                raise ValueError(f"Analyzer not found: {analyzer_id}")

            for raw_message in raw_messages:
                parsed = parser.parse(raw_message, transport=transport)
                ingestion_row = await repo.save_ingestion(analyzer_row, parsed)
                await repo.update_lab_test_and_results(analyzer_row, parsed)
                saved_rows.append(ingestion_row)

            await session.commit()
            return saved_rows

    async def simulate_bc5150_result(self, analyzer_id: int, test_id: str, patient_id: str = "1001") -> dict[str, Any]:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        message = (
            f"MSH|^~\\&||Mindray|||{now}||ORU^R01|2|P|2.3.1||||||UNICODE\r"
            f"PID|1||{patient_id}^^^^MR||^Test Patient||20000101000000|Male\r"
            f"PV1|1||LAB^^BED1\r"
            f"OBR|1|{test_id}||00001^Automated Count^99MRC||{now}||||S1||||{now}||||||||||HM||||||||tech1\r"
            f"OBX|1|NM|6690-2^WBC^LN||7.20|10*9/L|4.00-10.00|N||||F|{now}\r"
            f"OBX|2|NM|789-8^RBC^LN||4.80|10*12/L|3.50-5.50|N||||F|{now}\r"
            f"OBX|3|NM|718-7^Hemoglobin^LN||13.8|g/dL|11.0-16.0|N||||F|{now}\r"
        )
        await self.ingest_payload(
            analyzer_id=analyzer_id,
            analyzer_name="Mindray BC-5150",
            protocol_type="hl7",
            is_automated=True,
            payload=wrap_mllp(message),
            transport="simulated-mllp",
        )
        return self.bc5150_parser.parse(message, transport="simulated-mllp").to_dict()

    async def simulate_bs240_result(self, analyzer_id: int, test_id: str, patient_id: str = "1001") -> dict[str, Any]:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        message = (
            f"MSH|^~\\&|Manufacturer|BS240|||{now}||ORU^R01|1|P|2.3.1||||0||ASCII|||\r"
            f"PID|1|{patient_id}|||Test^Patient||19900101000000|M\r"
            f"OBR|1|BAR-{test_id}|{test_id}|Mindray^BS240||{now}|{now}|||collector|||Clinical note|{now}|Serum|sender1|Chemistry\r"
            f"OBX|1|NM|TBIL|TBil|14.2|umol/L|5.0-21.0|N|||F||14.2|{now}|CHEM|tech1\r"
            f"OBX|2|NM|ALT|ALT|22.4|U/L|0-40|N|||F||22.4|{now}|CHEM|tech1\r"
            f"OBX|3|NM|AST|AST|19.1|U/L|0-40|N|||F||19.1|{now}|CHEM|tech1\r"
        )
        await self.ingest_payload(
            analyzer_id=analyzer_id,
            analyzer_name="Mindray BS-240",
            protocol_type="auto",
            is_automated=True,
            payload=wrap_mllp(message),
            transport="simulated-mllp",
        )
        return self.bs240_hl7_parser.parse(message, transport="simulated-mllp").to_dict()


# -----------------------------------------------------------------------------
# LISTENERS
# -----------------------------------------------------------------------------

class AnalyzerTCPServerListener:
    def __init__(self, analyzer_row: Any, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        logger.info("Analyzer connected: %s (%s)", getattr(self.analyzer_row, "name", self.analyzer_row.id), peer)
        buffer = bytearray()

        try:
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
                    payload = bytes(buffer[sb : eb + len(MLLP_END)])
                    del buffer[: eb + len(MLLP_END)]

                    await self.service.ingest_payload(
                        analyzer_id=self.analyzer_row.id,
                        analyzer_name=self.analyzer_row.name,
                        protocol_type=getattr(self.analyzer_row, "protocol_type", "auto"),
                        is_automated=getattr(self.analyzer_row, "is_automated", False),
                        payload=payload,
                        transport="tcp_server",
                    )

                    parser = self.service.detect_parser(
                        self.analyzer_row.name,
                        getattr(self.analyzer_row, "protocol_type", "auto"),
                        payload,
                    )
                    if hasattr(parser, "build_ack"):
                        for raw_message in unwrap_mllp(payload):
                            ack = parser.build_ack(raw_message)
                            writer.write(wrap_mllp(ack))
                            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("Analyzer disconnected: %s", peer)

    async def run(self) -> None:
        host = getattr(self.analyzer_row, "host", "0.0.0.0")
        port = int(getattr(self.analyzer_row, "port", 0))
        server = await asyncio.start_server(self.handle, host, port)
        logger.info("TCP server listener started for %s on %s:%s", self.analyzer_row.name, host, port)
        async with server:
            await server.serve_forever()


class AnalyzerTCPClientListener:
    def __init__(self, analyzer_row: Any, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service

    async def run(self) -> None:
        host = getattr(self.analyzer_row, "host")
        port = int(getattr(self.analyzer_row, "port"))
        reconnect_delay = float(getattr(self.analyzer_row, "reconnect_delay", 5))

        while True:
            try:
                logger.info("Connecting to analyzer %s at %s:%s", self.analyzer_row.name, host, port)
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
                        payload = bytes(buffer[sb : eb + len(MLLP_END)])
                        del buffer[: eb + len(MLLP_END)]

                        await self.service.ingest_payload(
                            analyzer_id=self.analyzer_row.id,
                            analyzer_name=self.analyzer_row.name,
                            protocol_type=getattr(self.analyzer_row, "protocol_type", "auto"),
                            is_automated=getattr(self.analyzer_row, "is_automated", False),
                            payload=payload,
                            transport="tcp_client",
                        )

                writer.close()
                await writer.wait_closed()
            except Exception:
                logger.exception("TCP client listener failed for analyzer %s", self.analyzer_row.name)
                await asyncio.sleep(reconnect_delay)


class AnalyzerSerialListener:
    def __init__(self, analyzer_row: Any, service: AnalyzerIngestionService):
        self.analyzer_row = analyzer_row
        self.service = service

    async def run(self) -> None:
        import serial

        serial_port = getattr(self.analyzer_row, "serial_port")
        baud_rate = int(getattr(self.analyzer_row, "baud_rate", 9600))
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        logger.info("Serial listener started for %s on %s", self.analyzer_row.name, serial_port)
        buffer = bytearray()
        try:
            while True:
                chunk = ser.read(4096)
                if not chunk:
                    await asyncio.sleep(0.05)
                    continue
                buffer.extend(chunk)

                # Supports both MLLP-style traffic and plain ASTM serial records.
                if VT in buffer and MLLP_END in buffer:
                    sb = buffer.find(VT)
                    eb = buffer.find(MLLP_END, sb + 1)
                    if eb != -1:
                        payload = bytes(buffer[sb : eb + len(MLLP_END)])
                        del buffer[: eb + len(MLLP_END)]
                        await self.service.ingest_payload(
                            analyzer_id=self.analyzer_row.id,
                            analyzer_name=self.analyzer_row.name,
                            protocol_type=getattr(self.analyzer_row, "protocol_type", "auto"),
                            is_automated=getattr(self.analyzer_row, "is_automated", False),
                            payload=payload,
                            transport="serial",
                        )
                elif buffer.endswith(CR):
                    payload = bytes(buffer)
                    buffer.clear()
                    await self.service.ingest_payload(
                        analyzer_id=self.analyzer_row.id,
                        analyzer_name=self.analyzer_row.name,
                        protocol_type=getattr(self.analyzer_row, "protocol_type", "auto"),
                        is_automated=getattr(self.analyzer_row, "is_automated", False),
                        payload=payload,
                        transport="serial",
                    )
        finally:
            ser.close()


# -----------------------------------------------------------------------------
# BACKGROUND WORKER BOOTSTRAP
# -----------------------------------------------------------------------------

class AnalyzerWorkerManager:
    def __init__(self) -> None:
        self.service = AnalyzerIngestionService()
        self.tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> list[asyncio.Task[Any]]:
        async with AsyncSessionLocal() as session:
            repo = AnalyzerIngestionRepository(session)
            analyzers = await repo.get_automated_analyzers()

        for analyzer_row in analyzers:
            transport_type = str(getattr(analyzer_row, "transport_type", "")).lower()
            if transport_type == "tcp_server":
                task = asyncio.create_task(AnalyzerTCPServerListener(analyzer_row, self.service).run())
            elif transport_type == "tcp_client":
                task = asyncio.create_task(AnalyzerTCPClientListener(analyzer_row, self.service).run())
            elif transport_type == "serial":
                task = asyncio.create_task(AnalyzerSerialListener(analyzer_row, self.service).run())
            else:
                logger.warning("Unknown transport_type for analyzer %s: %s", analyzer_row.id, transport_type)
                continue

            self.tasks.append(task)
            logger.info(
                "Started analyzer worker: id=%s name=%s transport=%s protocol=%s automated=%s",
                analyzer_row.id,
                getattr(analyzer_row, "name", None),
                transport_type,
                getattr(analyzer_row, "protocol_type", None),
                getattr(analyzer_row, "is_automated", None),
            )
        return self.tasks

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()


worker_manager = AnalyzerWorkerManager()


async def start_analyzer_workers() -> list[asyncio.Task[Any]]:
    return await worker_manager.start()


async def stop_analyzer_workers() -> None:
    await worker_manager.stop()


# -----------------------------------------------------------------------------
# FASTAPI STARTUP INTEGRATION EXAMPLE
# -----------------------------------------------------------------------------
# Add this to your main.py if you want the listeners to start with FastAPI:
#
# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from app.services.analyzer_ingestion_service import start_analyzer_workers, stop_analyzer_workers
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await start_analyzer_workers()
#     yield
#     await stop_analyzer_workers()
#
# app = FastAPI(lifespan=lifespan)
#
# The listeners only start for analyzers where:
# - is_active = True
# - is_automated = True
#
# That matches your workflow: when a test is assigned to an analyzer and that
# analyzer has is_automated=True, the scientist waits for the analyzer listener
# service to populate result data instead of typing results manually.
