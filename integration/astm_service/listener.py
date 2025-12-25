"""ASTM Listener Service (multi-analyzer).

Run this as a separate process on the on-prem server.
It accepts ASTM frames (TCP or Serial), normalizes them to JSON, and POSTs them to the FastAPI endpoint.
"""

import asyncio
import json
from pathlib import Path
import requests
from .parser import parse_astm_text

CONFIG = json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))
API_URL = CONFIG["api_url"]

async def handle_payload(analyzer_name: str, raw_text: str) -> None:
    results = parse_astm_text(raw_text)
    if not results:
        return
    for r in results:
        payload = {
            "analyzer_name": analyzer_name,
            "sample_id": r.sample_id,
            "patient_no": r.patient_no,
            "test_name": r.test_name,
            "parameter": r.parameter,
            "value": r.value,
            "unit": r.unit,
            "raw": r.raw,
        }
        try:
            requests.post(API_URL, json=payload, timeout=10)
        except Exception:
            # logging handled at system level for now
            pass

async def main():
    # MVP placeholder: you will replace this with real TCP/serial listeners per device.
    # Keeping this file so the repo already has the integration "service slot".
    print("ASTM service scaffold ready. Configure listeners per analyzer in this file.")

if __name__ == "__main__":
    asyncio.run(main())
