from __future__ import annotations
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path when running as a script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from .manager import AnalyzerRuntimeManager

async def main():
    print("[listener] Starting Analyzer Listener Service")
    # print(f"[listener] DB: {settings.DATABASE_URL}")
    print(f"[listener] DB: {settings.DB_URL}")
    mgr = AnalyzerRuntimeManager()
    await mgr.run()

if __name__ == "__main__":
    asyncio.run(main())
