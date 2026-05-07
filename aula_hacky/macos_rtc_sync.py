from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime

from .hid_macos import MacHIDTransport, find_matching_device
from .macos_cli import (
    DONGLE_PID,
    DONGLE_VENDOR_USAGE,
    DONGLE_VENDOR_USAGE_PAGE_32,
    DONGLE_VID,
    _format_device_line,
)
from .protocol_core import (
    PACKET_SIZE,
    Transaction,
    build_transaction_sequence,
    is_valid_reply,
    iter_candidate_packets,
    parse_time_argument,
)


@dataclass(frozen=True)
class ReplyMatch:
    packet: bytes
    kind: str


def _parse_hex(value: str) -> int:
    return int(value, 16)


def match_transaction_reply(
    raw_report: bytes,
    tx: Transaction,
    allow_prefix_variant: bool = False,
) -> ReplyMatch | None:
    for candidate in iter_candidate_packets(raw_report):
        if tx.expected_reply is not None and is_valid_reply(
            candidate,
            tx.expected_reply_prefix,
            exact=tx.expected_reply,
        ):
            return ReplyMatch(packet=candidate, kind="exact")

        if tx.expected_reply is None and is_valid_reply(candidate, tx.expected_reply_prefix):
            return ReplyMatch(packet=candidate, kind="prefix")

        is_known_dongle_session_variant = tx.name in {"session-init", "session-query"}
        if (allow_prefix_variant or is_known_dongle_session_variant) and is_valid_reply(
            candidate,
            tx.expected_reply_prefix,
            exact=None,
        ):
            return ReplyMatch(packet=candidate, kind="prefix")

    return None


def wait_for_transaction_reply(
    transport: MacHIDTransport,
    tx: Transaction,
    debug: bool = False,
    allow_prefix_variant: bool = False,
) -> ReplyMatch:
    skipped: list[bytes] = []
    while True:
        raw_report = transport.read_report(max_length=(transport.report_size or PACKET_SIZE) + 1)
        if debug:
            print(f"{tx.name}: raw={raw_report.hex()}")

        match = match_transaction_reply(
            raw_report,
            tx,
            allow_prefix_variant=allow_prefix_variant,
        )
        if match is not None:
            if debug:
                for stale in skipped:
                    print(f"{tx.name}: skipped={stale.hex()}")
            return match

        candidates = iter_candidate_packets(raw_report)
        skipped.extend(candidates or [raw_report])


def run_dongle_rtc_sync(
    when: datetime,
    vid: int = DONGLE_VID,
    pid: int = DONGLE_PID,
    usage_page: int = DONGLE_VENDOR_USAGE_PAGE_32,
    usage: int = DONGLE_VENDOR_USAGE,
    timeout_seconds: float = 1.0,
    report_size: int | None = None,
    debug: bool = False,
    dry_run: bool = False,
    allow_prefix_replies: bool = False,
) -> None:
    transactions = build_transaction_sequence(when)

    print(f"target-local-time: {when.isoformat(sep=' ')}")
    for tx in transactions:
        print(f"{tx.name}: out={tx.outgoing.hex()}")

    if dry_run:
        return

    selected = find_matching_device(vid, pid, usage_page, usage)
    print(f"using-device: {_format_device_line(selected)}")

    with MacHIDTransport(
        vid,
        pid,
        usage_page,
        usage,
        timeout_seconds=timeout_seconds,
        input_report_bytes=report_size or PACKET_SIZE,
    ) as transport:
        actual_report_size = report_size or transport.report_size or PACKET_SIZE
        if debug:
            drained = transport.drain_pending_reports()
            for report in drained:
                print(f"drained: {report.hex()}")

        for tx in transactions:
            outgoing = tx.outgoing.ljust(actual_report_size, b"\x00")
            if len(outgoing) != actual_report_size:
                raise RuntimeError(
                    f"{tx.name}: report size {actual_report_size} is smaller than packet size"
                )
            written = transport.write(outgoing)
            if written != actual_report_size:
                raise RuntimeError(f"{tx.name}: short write, wrote {written} bytes")
            match = wait_for_transaction_reply(
                transport,
                tx,
                debug=debug,
                allow_prefix_variant=allow_prefix_replies,
            )
            print(f"{tx.name}: in={match.packet.hex()}")
            print(f"{tx.name}: match={match.kind}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync the AULA F75 Max RTC over the macOS 2.4 GHz dongle HID interface"
    )
    parser.add_argument("--vid", default=f"{DONGLE_VID:04x}", help="USB vendor ID in hex")
    parser.add_argument("--pid", default=f"{DONGLE_PID:04x}", help="USB product ID in hex")
    parser.add_argument(
        "--usage-page",
        default=f"{DONGLE_VENDOR_USAGE_PAGE_32:04x}",
        help="HID usage page in hex",
    )
    parser.add_argument("--usage", default=f"{DONGLE_VENDOR_USAGE:04x}", help="HID usage in hex")
    parser.add_argument("--time", default="now", help="local time as ISO-8601 or the literal 'now'")
    parser.add_argument("--timeout", type=float, default=1.0, help="read timeout per reply in seconds")
    parser.add_argument("--report-size", type=int, help="override output/input report size")
    parser.add_argument("--dry-run", action="store_true", help="print packets without opening a device")
    parser.add_argument("--debug", action="store_true", help="print raw reports while waiting for replies")
    parser.add_argument(
        "--allow-prefix-replies",
        action="store_true",
        help="accept checksum-valid prefix replies for all RTC transactions",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    run_dongle_rtc_sync(
        when=parse_time_argument(args.time),
        vid=_parse_hex(args.vid),
        pid=_parse_hex(args.pid),
        usage_page=_parse_hex(args.usage_page),
        usage=_parse_hex(args.usage),
        timeout_seconds=args.timeout,
        report_size=args.report_size,
        debug=args.debug,
        dry_run=args.dry_run,
        allow_prefix_replies=args.allow_prefix_replies,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
