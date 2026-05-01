#!/usr/bin/env python3
"""
run_simulator.py
================
Analyzer Simulator Service — sends realistic analyzer results to the LIS.

This service simulates what the real Mindray BC-5150 and BS-240 analyzers
would send over TCP/MLLP or ASTM, allowing full end-to-end testing of the
integration pipeline BEFORE connecting real hardware.

Usage:
    # Simulate BC-5150 sending one haematology result
    python run_simulator.py --analyzer bc5150 --patient P001 --sample S001 --port 10001

    # Simulate BS-240 sending one chemistry result (HL7 mode)
    python run_simulator.py --analyzer bs240_hl7 --patient P002 --sample S002 --port 10002

    # Simulate BS-240 ASTM mode
    python run_simulator.py --analyzer bs240_astm --patient P003 --sample S003 --port 10003

    # Interactive mode (menu-driven)
    python run_simulator.py --interactive

Environment:
    LIS_HOST  : Host where the analyzer worker is listening (default: 127.0.0.1)
    LIS_PORT  : Override port (default depends on analyzer type)
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.logging import setup_logging

logger = logging.getLogger("analyzer_simulator")

# ---------------------------------------------------------------------------
# MLLP / ASTM byte constants
# ---------------------------------------------------------------------------
VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"
MLLP_END = FS + CR

ENQ = bytes([0x05])
ACK_BYTE = bytes([0x06])
NAK_BYTE = bytes([0x15])
EOT = bytes([0x04])
STX = bytes([0x02])
ETX = bytes([0x03])


def wrap_mllp(message: str) -> bytes:
    return VT + message.encode("utf-8") + MLLP_END


def astm_checksum(data: bytes) -> str:
    """Calculate ASTM checksum: sum of ASCII values mod 256, formatted as 2 hex digits."""
    total = sum(data) % 256
    return f"{total:02X}"


def build_astm_frame(frame_no: int, data: str, is_last: bool = False) -> bytes:
    """Build a single ASTM E1381 data frame."""
    frame_num = str(frame_no % 8).encode("ascii")
    content = data.encode("ascii")
    end_byte = ETX if is_last else bytes([0x17])  # ETX or ETB
    checksum_input = frame_num + content + end_byte
    checksum = astm_checksum(checksum_input).encode("ascii")
    return STX + frame_num + content + end_byte + checksum + b"\r\n"


# ===========================================================================
# BC-5150 HAEMATOLOGY SIMULATOR
# ===========================================================================

class BC5150Simulator:
    """
    Simulates Mindray BC-5150 Haematology Analyzer.
    Sends HL7 v2.3.1 ORU^R01 message over TCP with MLLP framing.

    Full CBC panel with LOINC codes as per manufacturer documentation.
    """

    DEFAULT_PORT = 10001

    def build_message(self, patient_id: str, sample_id: str) -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        msg_ctrl = f"BC{now}"
        msg = (
            f"MSH|^~\\&|BC5150|Mindray|||{now}||ORU^R01|{msg_ctrl}|P|2.3.1||||||UNICODE\r"
            f"PID|1||{patient_id}^^^^MR||TestPatient^Sim||19850101000000|M\r"
            f"PV1|1||LAB^^BED1\r"
            f"OBR|1|{sample_id}|{sample_id}|00001^CBC^99MRC||{now}||||{sample_id}||||{now}||||||||||HM||||||||tech1\r"
            # Complete Blood Count parameters with LOINC codes
            f"OBX|1|NM|6690-2^WBC^LN||7.20|10*9/L|4.00-10.00|N||||F|||{now}\r"
            f"OBX|2|NM|789-8^RBC^LN||4.80|10*12/L|3.50-5.50|N||||F|||{now}\r"
            f"OBX|3|NM|718-7^HGB^LN||13.8|g/dL|11.0-16.0|N||||F|||{now}\r"
            f"OBX|4|NM|4544-3^HCT^LN||41.2|%|36.0-48.0|N||||F|||{now}\r"
            f"OBX|5|NM|787-2^MCV^LN||85.8|fL|80.0-100.0|N||||F|||{now}\r"
            f"OBX|6|NM|785-6^MCH^LN||28.8|pg|27.0-34.0|N||||F|||{now}\r"
            f"OBX|7|NM|786-4^MCHC^LN||33.5|g/dL|31.0-37.0|N||||F|||{now}\r"
            f"OBX|8|NM|777-3^PLT^LN||218.0|10*9/L|150.0-400.0|N||||F|||{now}\r"
            f"OBX|9|NM|26511-6^NEU%^LN||58.2|%|50.0-70.0|N||||F|||{now}\r"
            f"OBX|10|NM|26474-7^LYM%^LN||31.4|%|20.0-40.0|N||||F|||{now}\r"
            f"OBX|11|NM|26484-6^MONO%^LN||7.2|%|3.0-12.0|N||||F|||{now}\r"
            f"OBX|12|NM|26449-9^EOS%^LN||2.4|%|0.5-5.0|N||||F|||{now}\r"
            f"OBX|13|NM|30180-4^BASO%^LN||0.8|%|0.0-1.0|N||||F|||{now}\r"
        )
        return msg

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        logger.info("BC-5150 simulator connecting to %s:%d...", host, port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except ConnectionRefusedError:
            logger.error("Connection refused — is the analyzer worker running on %s:%d?", host, port)
            return False

        message = self.build_message(patient_id, sample_id)
        mllp_payload = wrap_mllp(message)

        logger.info("Sending BC-5150 HL7 ORU^R01 (patient=%s sample=%s)", patient_id, sample_id)
        writer.write(mllp_payload)
        await writer.drain()

        # Wait for ACK
        try:
            ack_data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            if ack_data:
                ack_text = ack_data.decode("utf-8", errors="replace")
                if "AA" in ack_text:
                    logger.info("✓ BC-5150: ACK received (AA — Application Accept)")
                elif "AE" in ack_text:
                    logger.warning("✗ BC-5150: ACK received but AE (Application Error)")
                else:
                    logger.info("BC-5150: Response received: %r", ack_text[:100])
            else:
                logger.warning("BC-5150: No ACK received")
        except asyncio.TimeoutError:
            logger.warning("BC-5150: ACK timeout — message may still have been processed")

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        logger.info("BC-5150 simulation complete")
        return True


# ===========================================================================
# BS-240 CHEMISTRY SIMULATOR — HL7 MODE
# ===========================================================================

class BS240HL7Simulator:
    """
    Simulates Mindray BS-240 Chemistry Analyzer in HL7 mode.
    Sends HL7 v2.3.1 ORU^R01 over TCP with MLLP framing.

    Full chemistry panel as per BS-240 documentation.
    MSH-16 = 0 (result message, not query).
    """

    DEFAULT_PORT = 10002

    def build_message(self, patient_id: str, sample_id: str) -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        barcode = f"BAR-{sample_id}"
        msg_ctrl = f"BS{now}"
        msg = (
            f"MSH|^~\\&|BS240|Mindray|||{now}||ORU^R01|{msg_ctrl}|P|2.3.1||||0||ASCII|||\r"
            f"PID|1|{patient_id}|||TestPatient^Sim||19900101000000|M\r"
            f"OBR|1|{barcode}|{sample_id}|Chemistry^BS240||{now}|{now}|||phlebotomist|||Clinical chem|{now}|Serum|sender1|Chemistry\r"
            # Liver Function Tests
            f"OBX|1|NM|TBIL|TBil|14.2|umol/L|5.0-21.0|N|||F||14.2|{now}|CHEM|tech1\r"
            f"OBX|2|NM|DBIL|DBil|4.1|umol/L|0.0-8.0|N|||F||4.1|{now}|CHEM|tech1\r"
            f"OBX|3|NM|IBIL|IBil|10.1|umol/L|0.0-14.0|N|||F||10.1|{now}|CHEM|tech1\r"
            f"OBX|4|NM|ALT|ALT|22.4|U/L|0-40|N|||F||22.4|{now}|CHEM|tech1\r"
            f"OBX|5|NM|AST|AST|19.1|U/L|0-40|N|||F||19.1|{now}|CHEM|tech1\r"
            f"OBX|6|NM|ALP|ALP|78.3|U/L|38-126|N|||F||78.3|{now}|CHEM|tech1\r"
            f"OBX|7|NM|GGT|GGT|31.2|U/L|7-64|N|||F||31.2|{now}|CHEM|tech1\r"
            # Renal Function
            f"OBX|8|NM|BUN|BUN|5.2|mmol/L|2.9-8.2|N|||F||5.2|{now}|CHEM|tech1\r"
            f"OBX|9|NM|CREA|Creatinine|78.5|umol/L|53-115|N|||F||78.5|{now}|CHEM|tech1\r"
            f"OBX|10|NM|UA|Uric Acid|285.0|umol/L|208-428|N|||F||285.0|{now}|CHEM|tech1\r"
            # Proteins
            f"OBX|11|NM|TP|Total Protein|70.8|g/L|60-80|N|||F||70.8|{now}|CHEM|tech1\r"
            f"OBX|12|NM|ALB|Albumin|42.3|g/L|35-55|N|||F||42.3|{now}|CHEM|tech1\r"
            f"OBX|13|NM|GLOB|Globulin|28.5|g/L|20-35|N|||F||28.5|{now}|CHEM|tech1\r"
            # Lipids
            f"OBX|14|NM|CHOL|Cholesterol|4.82|mmol/L|0-5.17|N|||F||4.82|{now}|CHEM|tech1\r"
            f"OBX|15|NM|TG|Triglycerides|1.38|mmol/L|0-1.70|N|||F||1.38|{now}|CHEM|tech1\r"
            f"OBX|16|NM|HDL|HDL Cholesterol|1.42|mmol/L|1.04-2.33|N|||F||1.42|{now}|CHEM|tech1\r"
            f"OBX|17|NM|LDL|LDL Cholesterol|2.77|mmol/L|0-3.37|N|||F||2.77|{now}|CHEM|tech1\r"
            # Glucose
            f"OBX|18|NM|GLU|Glucose|5.1|mmol/L|3.9-6.1|N|||F||5.1|{now}|CHEM|tech1\r"
        )
        return msg

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        logger.info("BS-240 (HL7) simulator connecting to %s:%d...", host, port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except ConnectionRefusedError:
            logger.error("Connection refused — is the analyzer worker running on %s:%d?", host, port)
            return False

        message = self.build_message(patient_id, sample_id)
        mllp_payload = wrap_mllp(message)

        logger.info("Sending BS-240 HL7 ORU^R01 (patient=%s sample=%s)", patient_id, sample_id)
        writer.write(mllp_payload)
        await writer.drain()

        try:
            ack_data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            if ack_data:
                ack_text = ack_data.decode("utf-8", errors="replace")
                if "AA" in ack_text:
                    logger.info("✓ BS-240 HL7: ACK received (AA — Application Accept)")
                elif "AE" in ack_text:
                    logger.warning("✗ BS-240 HL7: ACK received but AE (Application Error)")
                else:
                    logger.info("BS-240 HL7: Response: %r", ack_text[:100])
        except asyncio.TimeoutError:
            logger.warning("BS-240 HL7: ACK timeout — message may still have been processed")

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        logger.info("BS-240 HL7 simulation complete")
        return True


# ===========================================================================
# BS-240 CHEMISTRY SIMULATOR — ASTM MODE
# ===========================================================================

class BS240ASTMSimulator:
    """
    Simulates Mindray BS-240 Chemistry Analyzer in ASTM E1394-97 mode.

    ASTM E1381 byte-level handshake:
      Analyzer  →  ENQ         (I want to send data)
      LIS       →  ACK         (OK, go ahead)
      Analyzer  →  [STX][fn][data][CR][checksum][ETX][CR][LF]  (data frame)
      LIS       →  ACK         (frame received)
      ... repeat for each record ...
      Analyzer  →  EOT         (transmission complete)
    """

    DEFAULT_PORT = 10003

    def build_records(self, patient_id: str, sample_id: str) -> list[str]:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        barcode = f"BAR-{sample_id}"
        return [
            f"H|\\^&|||BS240^Mindray^1.0|||||||P|E 1394-97|{now}",
            f"P|1|{patient_id}|||TestPatient^Sim||19900101|M",
            f"O|1|{sample_id}|{barcode}|^^^CHEM||{now}|{now}|||N||||Serum",
            f"R|1|TBIL|14.2|umol/L|5.0-21.0|N|||F",
            f"R|2|DBIL|4.1|umol/L|0.0-8.0|N|||F",
            f"R|3|IBIL|10.1|umol/L|0.0-14.0|N|||F",
            f"R|4|ALT|22.4|U/L|0-40|N|||F",
            f"R|5|AST|19.1|U/L|0-40|N|||F",
            f"R|6|ALP|78.3|U/L|38-126|N|||F",
            f"R|7|GGT|31.2|U/L|7-64|N|||F",
            f"R|8|BUN|5.2|mmol/L|2.9-8.2|N|||F",
            f"R|9|CREA|78.5|umol/L|53-115|N|||F",
            f"R|10|TP|70.8|g/L|60-80|N|||F",
            f"R|11|ALB|42.3|g/L|35-55|N|||F",
            f"R|12|GLU|5.1|mmol/L|3.9-6.1|N|||F",
            f"L|1|N",
        ]

    async def send(self, host: str, port: int, patient_id: str, sample_id: str) -> bool:
        logger.info("BS-240 (ASTM) simulator connecting to %s:%d...", host, port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except ConnectionRefusedError:
            logger.error("Connection refused — is the analyzer worker running on %s:%d?", host, port)
            return False

        records = self.build_records(patient_id, sample_id)

        # Step 1: Send ENQ
        logger.info("Sending ASTM ENQ...")
        writer.write(ENQ)
        await writer.drain()

        # Wait for ACK
        try:
            resp = await asyncio.wait_for(reader.read(1), timeout=5.0)
            if not resp or resp[0] != 0x06:
                logger.error("Expected ACK after ENQ, got: %r", resp)
                writer.close()
                return False
            logger.debug("Received ACK for ENQ")
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for ACK after ENQ")
            writer.close()
            return False

        # Step 2: Send each record as a frame
        frame_no = 1
        for i, record in enumerate(records):
            is_last = (i == len(records) - 1)
            frame = build_astm_frame(frame_no, record, is_last=is_last)
            logger.debug("Sending frame %d: %s", frame_no, record[:40])
            writer.write(frame)
            await writer.drain()

            # Wait for ACK per frame
            try:
                resp = await asyncio.wait_for(reader.read(1), timeout=5.0)
                if not resp or resp[0] not in (0x06, 0x15):
                    logger.warning("Unexpected response for frame %d: %r", frame_no, resp)
                elif resp[0] == 0x15:
                    logger.warning("NAK received for frame %d — retransmitting not implemented", frame_no)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for frame %d ACK", frame_no)

            frame_no = (frame_no % 7) + 1

        # Step 3: Send EOT
        logger.info("Sending ASTM EOT...")
        writer.write(EOT)
        await writer.drain()

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        logger.info("✓ BS-240 ASTM simulation complete (patient=%s sample=%s)", patient_id, sample_id)
        return True


# ===========================================================================
# INTERACTIVE / CLI RUNNER
# ===========================================================================

async def run_interactive(host: str) -> None:
    """Interactive menu for running simulations."""
    print("\n" + "=" * 60)
    print("  Analyzer Simulator — Interactive Mode")
    print("=" * 60)
    print(f"  LIS Host: {host}")
    print()

    simulators = {
        "1": ("BC-5150 Haematology (HL7/MLLP)", BC5150Simulator(), BC5150Simulator.DEFAULT_PORT),
        "2": ("BS-240 Chemistry (HL7/MLLP)", BS240HL7Simulator(), BS240HL7Simulator.DEFAULT_PORT),
        "3": ("BS-240 Chemistry (ASTM/TCP)", BS240ASTMSimulator(), BS240ASTMSimulator.DEFAULT_PORT),
    }

    while True:
        print("Select analyzer to simulate:")
        for key, (name, _, _) in simulators.items():
            print(f"  [{key}] {name}")
        print("  [q] Quit")
        print()

        choice = input("Choice: ").strip().lower()
        if choice == "q":
            break

        if choice not in simulators:
            print("Invalid choice.\n")
            continue

        name, simulator, default_port = simulators[choice]
        print(f"\nSimulating: {name}")

        patient_id = input(f"Patient ID (default: P001): ").strip() or "P001"
        sample_id = input(f"Sample ID (default: S001): ").strip() or "S001"
        port_input = input(f"LIS port (default: {default_port}): ").strip()
        port = int(port_input) if port_input.isdigit() else default_port

        print()
        await simulator.send(host, port, patient_id, sample_id)
        print()


async def run_once(
    analyzer: str, host: str, port: int | None, patient_id: str, sample_id: str
) -> None:
    """Run a single simulation and exit."""
    sim_map = {
        "bc5150": (BC5150Simulator(), BC5150Simulator.DEFAULT_PORT),
        "bs240_hl7": (BS240HL7Simulator(), BS240HL7Simulator.DEFAULT_PORT),
        "bs240_astm": (BS240ASTMSimulator(), BS240ASTMSimulator.DEFAULT_PORT),
    }

    if analyzer not in sim_map:
        logger.error("Unknown analyzer: %s. Choose from: %s", analyzer, list(sim_map.keys()))
        sys.exit(1)

    simulator, default_port = sim_map[analyzer]
    actual_port = port or default_port

    success = await simulator.send(host, actual_port, patient_id, sample_id)
    sys.exit(0 if success else 1)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Analyzer Simulator — sends realistic test results to the LIS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--analyzer",
        choices=["bc5150", "bs240_hl7", "bs240_astm"],
        help="Analyzer type to simulate",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("LIS_HOST", "127.0.0.1"),
        help="LIS host (default: 127.0.0.1 or LIS_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="LIS port (default: 10001/10002/10003 depending on analyzer)",
    )
    parser.add_argument("--patient", default="P001", help="Patient ID to embed in message (default: P001)")
    parser.add_argument("--sample", default="S001", help="Sample ID to embed in message (default: S001)")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive menu to select analyzer and parameters",
    )

    args = parser.parse_args()

    if args.interactive or not args.analyzer:
        asyncio.run(run_interactive(args.host))
    else:
        asyncio.run(run_once(args.analyzer, args.host, args.port, args.patient, args.sample))


if __name__ == "__main__":
    main()