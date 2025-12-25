
"""ASTM E1381/E1394 parser + normalizer.

We parse logical records (H/P/O/R/L) from a raw ASTM message and
return a flat list of result rows suitable for ingestion.

Notes
- Most lab analyzers that say "ASTM" for LIS connectivity use ASTM E1381
  record types with E1394 message content rules.
- Field separator is usually "|" and component separator "^" (but can vary).
- This parser is tolerant: it extracts the most useful identifiers even when
  optional fields are missing or shifted.

Expected record types:
- H: Header
- P: Patient
- O: Order (contains sample/accession)
- R: Result (analyte/value/unit/flags)
- L: Terminator

You can extend or override mapping per analyzer via the `AnalyzerProfile`
mapping hooks in the integration service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_FIELD_SEP = "|"
DEFAULT_COMPONENT_SEP = "^"

@dataclass
class ParsedResult:
    sample_id: str
    test_name: str                # e.g. "GLU" or "WBC"
    parameter: str | None         # alias of test_name when needed
    value: str | float | int | None
    unit: str | None
    flags: str | None = None
    ref_range: str | None = None
    patient_no: str | None = None
    patient_name: str | None = None
    instrument_id: str | None = None
    raw_record: str | None = None

def _split_fields(line: str, field_sep: str = DEFAULT_FIELD_SEP) -> list[str]:
    # ASTM fields are '|' separated, trailing empties matter but we can keep them.
    return line.split(field_sep)

def _component(field: str, idx: int, comp_sep: str = DEFAULT_COMPONENT_SEP) -> str | None:
    if field is None:
        return None
    parts = field.split(comp_sep)
    if 0 <= idx < len(parts) and parts[idx] != "":
        return parts[idx]
    return None

def _normalize_number(val: str) -> str | float | int | None:
    if val is None:
        return None
    v = str(val).strip()
    if v == "":
        return None
    # Try int, then float
    try:
        if re.match(r"^[+-]?\d+$", v):
            return int(v)
        if re.match(r"^[+-]?(\d+\.?\d*|\d*\.?\d+)$", v):
            return float(v)
    except Exception:
        pass
    return v

import re

def parse_astm_text(raw: str, field_sep: str = DEFAULT_FIELD_SEP, comp_sep: str = DEFAULT_COMPONENT_SEP) -> list[ParsedResult]:
    raw = (raw or "").strip()
    if not raw:
        return []

    # Commonly records are separated by CR. Sometimes you may see LF too.
    lines = [ln for ln in re.split(r"\r\n|\n|\r", raw) if ln.strip()]

    current_patient_no: str | None = None
    current_patient_name: str | None = None
    current_sample_id: str | None = None
    current_instrument: str | None = None

    results: list[ParsedResult] = []

    for line in lines:
        rec_type = line[:1]

        fields = _split_fields(line, field_sep=field_sep)

        # Header: H|\^&|... instrument id often at field 4/5 depending on vendor
        if rec_type == "H":
            # Some emit sender/instrument id at H-4 or H-5; best-effort
            # H|\^&|sender|receiver|...  (varies)
            current_instrument = fields[3] if len(fields) > 3 and fields[3] else (fields[4] if len(fields) > 4 else None)
            continue

        # Patient: P|1|patient_id||last^first...
        if rec_type == "P":
            # patient id often at field 2 or 3
            current_patient_no = fields[2] if len(fields) > 2 and fields[2] else (fields[3] if len(fields) > 3 else None)
            # patient name often at field 5: last^first^middle
            name_field = fields[5] if len(fields) > 5 else ""
            if name_field:
                last = _component(name_field, 0, comp_sep) or ""
                first = _component(name_field, 1, comp_sep) or ""
                middle = _component(name_field, 2, comp_sep) or ""
                current_patient_name = " ".join([p for p in [first, middle, last] if p]).strip() or None
            continue

        # Order: O|1|sample_id|...; sample/accession id is commonly O-3 or O-2
        if rec_type == "O":
            # Some devices: O|1|<specimen_id>||...
            # Others: O|1|<placer>^<filler>|...
            raw_id = fields[2] if len(fields) > 2 else ""
            # If it's composite, take first component
            current_sample_id = _component(raw_id, 0, comp_sep) or raw_id or (fields[3] if len(fields) > 3 else None)
            continue

        # Result: R|1|^^^GLU|5.6|mmol/L|...|N|...
        if rec_type == "R":
            # test identifier typically at R-3 (fields[2]) in some, R-2 (fields[1]) in others
            test_field = fields[2] if len(fields) > 2 else (fields[1] if len(fields) > 1 else "")
            # Often "^^^TEST" => take last non-empty component
            test_name = None
            if test_field:
                comps = [c for c in test_field.split(comp_sep) if c]
                test_name = comps[-1] if comps else test_field
            test_name = (test_name or "").strip()

            value_field = fields[3] if len(fields) > 3 else None
            unit_field = fields[4] if len(fields) > 4 else None
            ref_range = fields[5] if len(fields) > 5 else None
            flags = fields[6] if len(fields) > 6 else None

            results.append(
                ParsedResult(
                    sample_id=current_sample_id or "",
                    test_name=test_name,
                    parameter=test_name or None,
                    value=_normalize_number(value_field) if value_field is not None else None,
                    unit=(unit_field.strip() if unit_field else None),
                    flags=(flags.strip() if flags else None),
                    ref_range=(ref_range.strip() if ref_range else None),
                    patient_no=current_patient_no,
                    patient_name=current_patient_name,
                    instrument_id=current_instrument,
                    raw_record=line,
                )
            )
            continue

        # L: Terminator
        if rec_type == "L":
            # reset per message if desired
            continue

    # Drop empty rows (no test name and no sample)
    results = [r for r in results if (r.test_name or r.sample_id or r.raw_record)]
    return results
