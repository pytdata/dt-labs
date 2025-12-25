from __future__ import annotations
from typing import Any, Dict, Tuple, Optional, List
import re

def _normalize_number(val: str) -> str:
    v = (val or "").strip()
    if v == "":
        return ""
    return v

def parse_astm(raw: str) -> Tuple[Dict[str, Any], Optional[str], Optional[str]]:
    """Parse ASTM E1381-ish records (H/P/O/R/L) into a normalized dict.

    Returns: (parsed_dict, sample_id, patient_no)

    parsed_dict:
      {
        "records": [... raw lines ...],
        "meta": {...},
        "results": [
          {"sample_id": "...", "patient_no": "...", "test_code": "GLU", "value": "5.6", "unit": "mmol/L",
           "flags": "N", "ref_range": "3.9-6.1", "raw_record": "..."}
        ]
      }
    """
    text = (raw or "").replace("\n", "\r")
    lines = [ln for ln in re.split(r"\r\n|\r|\n", text) if ln.strip()]

    patient_no: Optional[str] = None
    sample_id: Optional[str] = None
    instrument_id: Optional[str] = None
    patient_name: Optional[str] = None

    records: List[str] = []
    results: List[Dict[str, Any]] = []

    field_sep = "|"
    comp_sep = "^"

    for line in lines:
        cleaned = line.strip().strip("\x02").strip("\x03")
        if not cleaned:
            continue
        records.append(cleaned)

        rec_type = cleaned[:1]
        parts = cleaned.split(field_sep)

        if rec_type == "H":
            instrument_id = parts[3] if len(parts) > 3 and parts[3] else (parts[4] if len(parts) > 4 else None)

        if rec_type == "P":
            patient_no = parts[2] if len(parts) > 2 and parts[2] else (parts[3] if len(parts) > 3 else patient_no)
            name_field = parts[5] if len(parts) > 5 else ""
            if name_field:
                comps = [c for c in name_field.split(comp_sep) if c]
                if comps:
                    # last^first^middle is common
                    last = comps[0] if len(comps) > 0 else ""
                    first = comps[1] if len(comps) > 1 else ""
                    middle = comps[2] if len(comps) > 2 else ""
                    patient_name = " ".join([p for p in [first, middle, last] if p]).strip() or patient_name

        if rec_type == "O":
            raw_id = parts[2] if len(parts) > 2 else ""
            # if composite, take first component
            if raw_id:
                sid = raw_id.split(comp_sep)[0]
                sample_id = sample_id or sid or raw_id
            if not sample_id and len(parts) > 3 and parts[3]:
                sample_id = parts[3].split(comp_sep)[0]

        if rec_type == "R":
            test_field = parts[2] if len(parts) > 2 else ""
            test_code = ""
            if test_field:
                comps = [c for c in test_field.split(comp_sep) if c]
                test_code = comps[-1] if comps else test_field
            value = parts[3] if len(parts) > 3 else ""
            unit = parts[4] if len(parts) > 4 else ""
            ref_range = parts[5] if len(parts) > 5 else ""
            flags = parts[6] if len(parts) > 6 else ""

            results.append({
                "sample_id": sample_id or "",
                "patient_no": patient_no,
                "patient_name": patient_name,
                "instrument_id": instrument_id,
                "test_code": test_code.strip(),
                "value": _normalize_number(value),
                "unit": unit.strip() or None,
                "flags": flags.strip() or None,
                "ref_range": ref_range.strip() or None,
                "raw_record": cleaned,
            })

    parsed = {
        "records": records,
        "record_count": len(records),
        "meta": {
            "instrument_id": instrument_id,
            "patient_name": patient_name,
        },
        "results": results,
    }
    return parsed, sample_id, patient_no

def parse_csv(raw: str) -> Dict[str, Any]:
    return {"raw": raw, "note": "CSV parsing not implemented yet"}

def parse_xml(raw: str) -> Dict[str, Any]:
    return {"raw": raw, "note": "XML parsing not implemented yet"}
