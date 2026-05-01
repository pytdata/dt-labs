#!/usr/bin/env python3
"""
run_analyzer_worker.py
======================
Standalone entry point for the Analyzer Listener Service.

This service runs independently of uvicorn and continuously listens for
incoming TCP connections from automated analyzers (BC-5150, BS-240, etc.).

Usage:
    python run_analyzer_worker.py

Environment variables (same as main app via .env):
    DATABASE_URL  — PostgreSQL async URL

The service:
  1. Reads all active automated analyzers from the database
  2. Starts a TCP server listener for each (or TCP client / serial as configured)
  3. Processes incoming HL7/MLLP or ASTM messages
  4. Stores raw data → analyzer_messages
  5. Attempts patient/order matching → analyzer_ingestions
  6. Writes parsed results → lab_results (linked to order_item)
  7. Sends ACK back to analyzer (HL7) or byte ACK (ASTM)

Ports used by default (configure in DB per analyzer):
  - BC-5150 (HL7/MLLP): port 10001
  - BS-240  (HL7/MLLP): port 10002
  - BS-240  (ASTM/TCP): port 10003

Network: Analyzers are on 192.168.0.x subnet, LIS listens on 0.0.0.0
"""

import asyncio
import logging
import signal
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.logging import setup_logging
from app.services.analyzer_ingestion_service import (
    AnalyzerIngestionRepository,
    AnalyzerIngestionService,
    AnalyzerTCPServerListener,
    AnalyzerTCPClientListener,
    AnalyzerSerialListener,
    AsyncSessionLocal,
)

logger = logging.getLogger("analyzer_worker")


async def main() -> None:
    setup_logging()
    logger.info("=" * 60)
    logger.info("Analyzer Listener Service starting...")
    logger.info("=" * 60)

    service = AnalyzerIngestionService()
    tasks: list[asyncio.Task] = []

    # Load automated analyzers from DB
    async with AsyncSessionLocal() as session:
        repo = AnalyzerIngestionRepository(session)
        analyzers = await repo.get_automated_analyzers()

    if not analyzers:
        logger.warning(
            "No automated analyzers found in the database.\n"
            "Add analyzers via the admin UI at /settings/analyzers/add\n"
            "and set is_automated=True, transport_type='tcp_server', tcp_port=<port>"
        )
        logger.info("Service will wait 30 seconds and retry...")
        await asyncio.sleep(30)
        # Re-check — analyzers may have been added
        async with AsyncSessionLocal() as session:
            repo = AnalyzerIngestionRepository(session)
            analyzers = await repo.get_automated_analyzers()

    for analyzer_row in analyzers:
        transport_type = (getattr(analyzer_row, "transport_type", None) or "").lower()
        name = getattr(analyzer_row, "name", f"id={analyzer_row.id}")
        protocol = getattr(analyzer_row, "protocol_type", "hl7")
        port = getattr(analyzer_row, "tcp_port", None)

        logger.info(
            "Registering listener: name=%s transport=%s protocol=%s port=%s",
            name, transport_type, protocol, port,
        )

        if transport_type == "tcp_server":
            listener = AnalyzerTCPServerListener(analyzer_row, service)
        elif transport_type == "tcp_client":
            listener = AnalyzerTCPClientListener(analyzer_row, service)
        elif transport_type == "serial":
            listener = AnalyzerSerialListener(analyzer_row, service)
        else:
            logger.warning(
                "Analyzer %s has unknown transport_type=%r — skipping", name, transport_type
            )
            continue

        task = asyncio.create_task(listener.run(), name=f"listener-{analyzer_row.id}-{name}")
        tasks.append(task)

    if not tasks:
        logger.warning("No listeners started — check analyzer configuration in DB")
        return

    logger.info("Analyzer Listener Service ready — %d listener(s) active", len(tasks))
    logger.info("Press Ctrl+C to stop")

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()

    def shutdown():
        logger.info("Shutdown signal received — stopping listeners...")
        for task in tasks:
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass  # Windows

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass

    logger.info("Analyzer Listener Service stopped.")


if __name__ == "__main__":
    asyncio.run(main())