from __future__ import annotations
from typing import Any, Dict, Tuple, Optional, List
import re

FIELD_SEP = "|"
COMP_SEP = "^"


def _component(field: str, idx: int) -> Optional[str]:
    if not field:
        return None
    parts = field.split(COMP_SEP)
    if 0 <= idx < len(parts):
        return parts[idx] or None
    return None


def _normalize_number(val: str) -> str:
    v = (val or "").strip()
    if v == "":
        return ""
    return v


def _normalize_name(name_field: str) -> Optional[str]:
    if not name_field:
        return None
    last = _component(name_field, 0) or ""
    first = _component(name_field, 1) or ""
    middle = _component(name_field, 2) or ""
    name = " ".join([p for p in [first, middle, last] if p]).strip()
    return name or None


def parse_astm(raw: str) -> Tuple[Dict[str, Any], Optional[str], Optional[str]]:
    """Parse ASTM E1381/E1394 messages (H/P/O/R/L records) into a normalized dict.

    Returns: (parsed_dict, sample_id, patient_no)
    """
    text = (raw or "").replace("\n", "\r")
    lines = [ln for ln in re.split(r"\r\n|\r|\n", text) if ln.strip()]

    patient_no: Optional[str] = None
    sample_id: Optional[str] = None
    instrument_id: Optional[str] = None
    patient_name: Optional[str] = None
    order_id: Optional[str] = None

    records: List[str] = []
    results: List[Dict[str, Any]] = []

    for line in lines:
        cleaned = line.strip().strip("\x02").strip("\x03")
        if not cleaned:
            continue
        records.append(cleaned)

        rec_type = cleaned[:1]
        parts = cleaned.split(FIELD_SEP)

        if rec_type == "H":
            instrument_id = parts[3] if len(parts) > 3 and parts[3] else (parts[4] if len(parts) > 4 else None)
            continue

        if rec_type == "P":
            patient_no = parts[2] if len(parts) > 2 and parts[2] else (parts[3] if len(parts) > 3 else patient_no)
            patient_name = _normalize_name(parts[5] if len(parts) > 5 else "")
            continue

        if rec_type == "O":
            raw_id = parts[2] if len(parts) > 2 else ""
            if raw_id:
                sid = _component(raw_id, 0) or raw_id
                sample_id = sample_id or sid
                order_id = _component(raw_id, 1) or order_id
            if not sample_id and len(parts) > 3 and parts[3]:
                sample_id = _component(parts[3], 0) or parts[3]
            continue

        if rec_type == "R":
            test_field = parts[2] if len(parts) > 2 else ""
            test_code = ""
            if test_field:
                comps = [c for c in test_field.split(COMP_SEP) if c]
                test_code = comps[-1] if comps else test_field
            value = parts[3] if len(parts) > 3 else ""
            unit = parts[4] if len(parts) > 4 else ""
            ref_range = parts[5] if len(parts) > 5 else ""
            flags = parts[6] if len(parts) > 6 else ""

            results.append({
                "sample_id": sample_id or "",
                "order_id": order_id,
                "patient_no": patient_no,
                "patient_name": patient_name,
                "instrument_id": instrument_id,
                "test_code": (test_code or "").strip(),
                "test_name": (test_code or "").strip(),
                "value": _normalize_number(value),
                "unit": unit.strip() or None,
                "flags": flags.strip() or None,
                "ref_range": ref_range.strip() or None,
                "raw_record": cleaned,
            })
            continue

        if rec_type == "L":
            # terminator: nothing special for now
            continue

    parsed = {
        "records": records,
        "record_count": len(records),
        "meta": {
            "instrument_id": instrument_id,
            "patient_name": patient_name,
            "order_id": order_id,
        },
        "results": results,
    }
    return parsed, sample_id, patient_no


def parse_csv(raw: str) -> Dict[str, Any]:
    return {"raw": raw, "note": "CSV parsing not implemented yet"}


def parse_xml(raw: str) -> Dict[str, Any]:
    return {"raw": raw, "note": "XML parsing not implemented yet"}
