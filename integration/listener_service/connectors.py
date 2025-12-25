from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Optional

@dataclass
class TCPConfig:
    host: str
    port: int

async def tcp_stream(cfg: TCPConfig) -> AsyncIterator[bytes]:
    """Connect to analyzer via TCP and yield chunks."""
    reader, writer = await asyncio.open_connection(cfg.host, cfg.port)
    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                await asyncio.sleep(0.2)
                continue
            yield chunk
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

@dataclass
class SerialConfig:
    port: str
    baudrate: int = 9600
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8

async def serial_stream(cfg: SerialConfig) -> AsyncIterator[bytes]:
    """Async serial reader. Requires pyserial-asyncio."""
    import serial_asyncio  # type: ignore

    reader, writer = await serial_asyncio.open_serial_connection(
        url=cfg.port,
        baudrate=cfg.baudrate,
        parity=cfg.parity,
        stopbits=cfg.stopbits,
        bytesize=cfg.bytesize,
    )
    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                await asyncio.sleep(0.2)
                continue
            yield chunk
    finally:
        writer.close()
