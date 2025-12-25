from __future__ import annotations

"""Utility helpers for sample / barcode handling.

This keeps sample-id creation in one place so both the web views and API can
use the same format. The format is short but sortable and includes a daily
prefix so BS-240 and FT-320 runs can be merged reliably.
"""

from datetime import datetime
import uuid


def generate_sample_id() -> str:
    """Generate a sortable sample identifier.

    Example: ``S-20250101-0001``. If multiple calls are made within the same
    second, a short suffix avoids collisions.
    """

    now = datetime.utcnow()
    base = now.strftime("S-%Y%m%d-%H%M%S")
    # UUID4 gives us randomness; we only keep 4 chars to keep the ID short.
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{base}-{suffix}"


def generate_barcode_payload(sample_id: str) -> str:
    """Return the payload string to encode in a barcode/QR.

    Keeping this centralized lets the printing UI or API call it without
    duplicating business rules.
    """

    return sample_id

