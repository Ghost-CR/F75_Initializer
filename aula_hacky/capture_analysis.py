from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .protocol_core import (
    CABLE_PACKET_SIZE,
    PACKET_SIZE,
    decode_rtc_set_packet,
    validate_cable_reply,
    validate_packet,
)


KNOWN_REPORT_SIZES = (PACKET_SIZE, CABLE_PACKET_SIZE)


@dataclass(frozen=True)
class HidReport:
    frame: int
    timestamp: str
    src: str
    dst: str
    transfer_type: str
    endpoint: str
    setup_request: str
    payload: bytes

    @property
    def direction(self) -> str:
        src = self.src.lower()
        dst = self.dst.lower()
        if "host" in src or dst.endswith(".0"):
            return "host-to-device"
        if "host" in dst or src.endswith(".0"):
            return "device-to-host"
        return "unknown"

    @property
    def report_size(self) -> int:
        return len(self.payload)

    @property
    def payload_hex(self) -> str:
        return self.payload.hex()


def normalize_payload_hex(value: str) -> bytes:
    cleaned = value.replace(":", "").replace(" ", "").strip()
    if not cleaned:
        return b""
    return bytes.fromhex(cleaned)


def strip_report_id(payload: bytes) -> bytes:
    if len(payload) in {PACKET_SIZE + 1, CABLE_PACKET_SIZE + 1} and payload[0] == 0:
        return payload[1:]
    return payload


def report_windows(payload: bytes) -> list[bytes]:
    payload = strip_report_id(payload)
    windows: list[bytes] = []
    for size in KNOWN_REPORT_SIZES:
        if len(payload) == size:
            windows.append(payload)
        elif len(payload) > size:
            for offset in range(0, len(payload) - size + 1):
                windows.append(payload[offset : offset + size])
    return windows


def annotate_payload(payload: bytes) -> str:
    payload = strip_report_id(payload)
    for candidate in report_windows(payload):
        if len(candidate) == PACKET_SIZE:
            if candidate.startswith(bytes([0x02, 0x00, 0x00])):
                return "dongle-session-init"
            if candidate.startswith(bytes([0x20, 0x01, 0x00])):
                return "dongle-session-query"
            if candidate.startswith(bytes([0x0C, 0x10, 0x00, 0x00, 0x01, 0x5A])):
                try:
                    decoded = decode_rtc_set_packet(candidate)
                except ValueError:
                    return "dongle-rtc-set-invalid-checksum"
                return (
                    "dongle-rtc-set "
                    f"{decoded['year']:04d}-{decoded['month']:02d}-{decoded['day']:02d} "
                    f"{decoded['hour']:02d}:{decoded['minute']:02d}:{decoded['second']:02d}"
                )
            if candidate.startswith(bytes([0x0C, 0x10, 0x00, 0x00])):
                try:
                    validate_packet(candidate)
                except ValueError:
                    return "dongle-rtc-ack-invalid-checksum"
                return "dongle-rtc-ack"

        if len(candidate) == CABLE_PACKET_SIZE:
            if candidate.startswith(bytes([0x04, 0x18])):
                return "cable-session-init"
            if candidate.startswith(bytes([0x04, 0x28])):
                return "cable-session-prepare"
            if candidate.startswith(bytes([0x00, 0x01, 0x5A])):
                return "cable-rtc-set"
            if candidate.startswith(bytes([0x04, 0x02])):
                return "cable-session-finalize"
            try:
                validate_cable_reply(candidate, candidate[:2])
            except ValueError:
                pass
    return ""


def parse_tshark_rows(lines: Iterable[str]) -> list[HidReport]:
    reports: list[HidReport] = []
    reader = csv.reader(lines, delimiter="\t")
    for row in reader:
        if len(row) != 8:
            continue
        frame, timestamp, src, dst, transfer_type, endpoint, setup_request, data_hex = row
        payload = normalize_payload_hex(data_hex)
        if not payload:
            continue
        reports.append(
            HidReport(
                frame=int(frame),
                timestamp=timestamp,
                src=src,
                dst=dst,
                transfer_type=transfer_type,
                endpoint=endpoint,
                setup_request=setup_request,
                payload=payload,
            )
        )
    return reports


def tshark_command(args: argparse.Namespace) -> list[str]:
    display_filters = ["usbhid.data"]
    if args.vid:
        display_filters.append(f"usb.idVendor==0x{args.vid.lower()}")
    if args.pid:
        display_filters.append(f"usb.idProduct==0x{args.pid.lower()}")
    if args.bus is not None:
        display_filters.append(f"usb.bus_id=={args.bus}")
    if args.device is not None:
        display_filters.append(f"usb.device_address=={args.device}")
    if args.frame_from is not None:
        display_filters.append(f"frame.number>={args.frame_from}")
    if args.frame_to is not None:
        display_filters.append(f"frame.number<={args.frame_to}")

    return [
        "tshark",
        "-r",
        str(args.capture),
        "-Y",
        " && ".join(display_filters),
        "-T",
        "fields",
        "-e",
        "frame.number",
        "-e",
        "frame.time_epoch",
        "-e",
        "usb.src",
        "-e",
        "usb.dst",
        "-e",
        "usb.transfer_type",
        "-e",
        "usb.endpoint_address",
        "-e",
        "usb.setup.bRequest",
        "-e",
        "usbhid.data",
    ]


def extract_reports(args: argparse.Namespace) -> list[HidReport]:
    completed = subprocess.run(tshark_command(args), check=True, capture_output=True, text=True)
    return parse_tshark_rows(completed.stdout.splitlines())


def write_jsonl(reports: Iterable[HidReport], output: Path) -> None:
    with output.open("w", encoding="utf-8") as handle:
        for report in reports:
            row = asdict(report)
            row["payload"] = report.payload_hex
            row["direction"] = report.direction
            row["report_size"] = report.report_size
            row["annotation"] = annotate_payload(report.payload)
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def diff_payloads(left_hex: str, right_hex: str) -> list[dict[str, str | int]]:
    left = normalize_payload_hex(left_hex)
    right = normalize_payload_hex(right_hex)
    length = max(len(left), len(right))
    changes: list[dict[str, str | int]] = []
    for offset in range(length):
        left_byte = left[offset] if offset < len(left) else None
        right_byte = right[offset] if offset < len(right) else None
        if left_byte == right_byte:
            continue
        changes.append(
            {
                "offset": offset,
                "left": "" if left_byte is None else f"{left_byte:02x}",
                "right": "" if right_byte is None else f"{right_byte:02x}",
            }
        )
    return changes


def command_extract(args: argparse.Namespace) -> int:
    reports = extract_reports(args)
    if args.output:
        write_jsonl(reports, Path(args.output))
        return 0

    for report in reports:
        note = annotate_payload(report.payload)
        suffix = f"\t{note}" if note else ""
        print(
            f"{report.frame}\t{report.direction}\t{report.transfer_type}\t"
            f"{report.endpoint}\t{report.payload_hex}{suffix}"
        )
    return 0


def command_diff(args: argparse.Namespace) -> int:
    left_rows = load_jsonl(Path(args.left))
    right_rows = load_jsonl(Path(args.right))
    pairs = zip(left_rows, right_rows, strict=False)
    for index, (left, right) in enumerate(pairs):
        changes = diff_payloads(left["payload"], right["payload"])
        if not changes:
            continue
        print(
            json.dumps(
                {
                    "index": index,
                    "left_frame": left.get("frame"),
                    "right_frame": right.get("frame"),
                    "left_annotation": left.get("annotation", ""),
                    "right_annotation": right.get("annotation", ""),
                    "changes": changes,
                },
                sort_keys=True,
            )
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and compare AULA HID reports from USBPcap captures")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="extract HID reports from a pcapng via tshark")
    extract.add_argument("capture", help="path to .pcapng capture")
    extract.add_argument("--vid", default="", help="optional USB vendor ID filter, for example 0c45")
    extract.add_argument("--pid", default="", help="optional USB product ID filter, for example 800a")
    extract.add_argument("--bus", type=int, help="optional USB bus id")
    extract.add_argument("--device", type=int, help="optional USB device address")
    extract.add_argument("--frame-from", type=int, help="first frame to inspect")
    extract.add_argument("--frame-to", type=int, help="last frame to inspect")
    extract.add_argument("--output", help="write normalized reports as JSONL")
    extract.set_defaults(func=command_extract)

    diff = subparsers.add_parser("diff", help="byte-diff two extracted JSONL report streams")
    diff.add_argument("left", help="left JSONL file")
    diff.add_argument("right", help="right JSONL file")
    diff.set_defaults(func=command_diff)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
