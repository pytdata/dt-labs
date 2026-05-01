#!/usr/bin/env python3
"""
run_analyzer_worker.py
======================
Standalone entry point for the Analyzer Listener Service.

This service runs independently of uvicorn and continuously listens for
incoming connections from automated analyzers (BC-5150, BS-240, etc.).

Usage:
    python run_analyzer_worker.py

Environment variables (same as main app via .env):
    DATABASE_URL  — PostgreSQL async URL

Behaviour
---------
If analyzers ARE registered in the DB (is_automated=True):
  • Starts a dedicated TCP/serial listener for EACH analyzer
  • Processes HL7/MLLP or ASTM messages, stores results, sends ACK

If NO analyzers are in the DB yet (first run / fresh install):
  • Enters DISCOVERY MODE automatically
  • TCP: binds discovery ports 3000, 3001, 3002 and waits for ANY device to connect
  • Serial: scans all available serial/USB ports for connected devices
  • On first contact the device is fingerprinted (BC-5150, BS-240, etc.)
  • Auto-registers the device in the DB as an Analyzer row
  • Spawns a dedicated listener immediately so no results are lost

Storage flow (both modes):
  raw bytes → analyzer_messages.raw      (AnalyzerMessage)
             → analyzer_ingestions        (AnalyzerIngestion - match attempt)
             → lab_results.results        (LabResult JSON) ← linked to order_item

Default discovery ports (when no analyzers in DB):
  3000  — BS-240  (HL7/MLLP or ASTM)
  3001  — BC-5150 (HL7/MLLP)
  3002  — spare / future analyzer

Network: Analyzers are on 192.168.0.x subnet, LIS listens on 0.0.0.0
"""

import asyncio
import logging
import signal
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.analyzer_ingestion_service import AnalyzerWorkerManager

logger = logging.getLogger("analyzer_worker")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def main() -> None:
    setup_logging()
    logger.info("=" * 60)
    logger.info("Analyzer Listener Service starting...")
    logger.info("=" * 60)

    manager = AnalyzerWorkerManager()

    # Wire up graceful shutdown
    loop = asyncio.get_running_loop()

    def shutdown() -> None:
        logger.info("Shutdown signal received — stopping all listeners...")
        asyncio.create_task(manager.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass  # Windows fallback

    # Start all listeners (or discovery mode if DB is empty)
    tasks = await manager.start()

    if not tasks:
        logger.error(
            "No listener tasks started — check database connectivity and analyzer configuration."
        )
        return

    logger.info(
        "Analyzer Listener Service ready — %d task(s) running. Press Ctrl+C to stop.",
        len(tasks),
    )

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    finally:
        await manager.stop()

    logger.info("Analyzer Listener Service stopped.")


if __name__ == "__main__":
    asyncio.run(main())