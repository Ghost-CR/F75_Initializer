from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime

from .hid_macos import K_IOHID_REPORT_TYPE_FEATURE, MacHIDDevice, MacHIDTransport, enumerate_hid_macos
from .macos_cli import _format_device_line
from .protocol_core import (
    CABLE_PACKET_SIZE,
    Transaction,
    build_cable_transaction_sequence,
    is_valid_cable_reply,
    parse_time_argument,
)

CABLE_VID = 0x0C45
CABLE_PID = 0x800A


@dataclass(frozen=True)
class CableReplyMatch:
    packet: bytes
    kind: str


def _parse_hex(value: str) -> int:
    return int(value, 16)


def _parse_optional_hex(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value, 16)


def normalize_feature_report(raw_report: bytes, report_id: int = 0) -> bytes:
    if len(raw_report) == CABLE_PACKET_SIZE + 1 and raw_report[0] == report_id:
        return raw_report[1:]
    return raw_report


def match_cable_transaction_reply(raw_report: bytes, tx: Transaction) -> CableReplyMatch | None:
    packet = normalize_feature_report(raw_report)
    if is_valid_cable_reply(packet, tx.expected_reply_prefix, exact=tx.expected_reply):
        return CableReplyMatch(packet=packet, kind="exact" if tx.expected_reply is not None else "prefix")
    return None


def pick_cable_device(
    vid: int = CABLE_VID,
    pid: int = CABLE_PID,
    usage_page: int | None = None,
    usage: int | None = None,
) -> MacHIDDevice:
    devices = enumerate_hid_macos(vid, pid, usage_page, usage)
    if not devices:
        raise FileNotFoundError(
            f"no matching macOS HID cable device found (vid=0x{vid:04x}, pid=0x{pid:04x})"
        )

    def score(device: MacHIDDevice) -> tuple[int, int, int]:
        feature = device.feature_report_bytes or 0
        vendor_usage = 1 if device.usage_page is not None and device.usage_page >= 0xFF00 else 0
        exact_feature = 1 if feature in {CABLE_PACKET_SIZE, CABLE_PACKET_SIZE + 1} else 0
        return exact_feature, vendor_usage, feature

    return sorted(devices, key=score, reverse=True)[0]


def run_cable_rtc_sync(
    when: datetime,
    vid: int = CABLE_VID,
    pid: int = CABLE_PID,
    usage_page: int | None = None,
    usage: int | None = None,
    timeout_seconds: float = 1.0,
    dry_run: bool = False,
    debug: bool = False,
    prefix_report_id: bool = False,
) -> None:
    transactions = build_cable_transaction_sequence(when)

    print(f"target-local-time: {when.isoformat(sep=' ')}")
    for tx in transactions:
        print(f"{tx.name}: out={tx.outgoing.hex()}")

    if dry_run:
        return

    selected = pick_cable_device(vid, pid, usage_page, usage)
    print(f"using-device: {_format_device_line(selected)}")
    feature_report_length = selected.feature_report_bytes or CABLE_PACKET_SIZE

    with MacHIDTransport(
        vid,
        pid,
        selected.usage_page if usage_page is None else usage_page,
        selected.usage if usage is None else usage,
        timeout_seconds=timeout_seconds,
        input_report_bytes=CABLE_PACKET_SIZE,
    ) as transport:
        for tx in transactions:
            written = transport.set_report(
                report_type=K_IOHID_REPORT_TYPE_FEATURE,
                report_id=0,
                payload=tx.outgoing,
                prefix_report_id=prefix_report_id,
            )
            if written != CABLE_PACKET_SIZE:
                raise RuntimeError(f"{tx.name}: short feature write, wrote {written} bytes")

            if tx.read_delay_seconds:
                time.sleep(tx.read_delay_seconds)

            raw_reply = transport.get_report(
                K_IOHID_REPORT_TYPE_FEATURE,
                report_id=0,
                length=feature_report_length,
            )
            if debug:
                print(f"{tx.name}: get_feature_raw={raw_reply.hex()}")
                print(f"{tx.name}: get_feature={normalize_feature_report(raw_reply).hex()}")

            match = match_cable_transaction_reply(raw_reply, tx)
            if match is None:
                raise RuntimeError(f"{tx.name}: unexpected feature reply {raw_reply.hex()}")
            print(f"{tx.name}: in={match.packet.hex()}")
            print(f"{tx.name}: match={match.kind}")

            if tx.post_delay_seconds:
                time.sleep(tx.post_delay_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync the AULA F75 Max RTC over the macOS USB-C cable HID feature interface"
    )
    parser.add_argument("--vid", default=f"{CABLE_VID:04x}", help="USB vendor ID in hex")
    parser.add_argument("--pid", default=f"{CABLE_PID:04x}", help="USB product ID in hex")
    parser.add_argument("--usage-page", help="optional HID usage page in hex")
    parser.add_argument("--usage", help="optional HID usage in hex")
    parser.add_argument("--time", default="now", help="local time as ISO-8601 or the literal 'now'")
    parser.add_argument("--timeout", type=float, default=1.0, help="feature report timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="print packets without opening a device")
    parser.add_argument("--debug", action="store_true", help="print raw feature replies")
    parser.add_argument(
        "--prefix-report-id",
        action="store_true",
        help="send a report-ID-prefixed feature report for investigation",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    run_cable_rtc_sync(
        when=parse_time_argument(args.time),
        vid=_parse_hex(args.vid),
        pid=_parse_hex(args.pid),
        usage_page=_parse_optional_hex(args.usage_page),
        usage=_parse_optional_hex(args.usage),
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
        debug=args.debug,
        prefix_report_id=args.prefix_report_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
