from __future__ import annotations
import httpx
from typing import Any, Dict, Optional

class LISClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def post_ingest(self, payload: Dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/integration/ingest",
                json=payload,
                headers={"X-Ingest-Token": self.token},
            )
            r.raise_for_status()
