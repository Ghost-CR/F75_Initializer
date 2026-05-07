from __future__ import annotations

import argparse
import time
from datetime import datetime

from .hidraw_linux import HidrawTransport, enumerate_hidraw, find_matching_device
from .protocol_core import (
    CABLE_PACKET_SIZE,
    PACKET_SIZE,
    build_cable_transaction_sequence,
    build_transaction_sequence,
    is_valid_cable_reply,
    is_valid_reply,
    iter_candidate_packets,
    parse_time_argument,
)

DEFAULT_VID = 0x0C45
DEFAULT_PID = 0x800A
DEFAULT_INTERFACE = 3

CABLE_VID = 0x0C45
CABLE_PID = 0x800A
DONGLE_VID = 0x05AC
DONGLE_PID = 0x024F


def _format_device_line(device) -> str:
    vid = f"{device.vendor_id:04x}" if device.vendor_id is not None else "????"
    pid = f"{device.product_id:04x}" if device.product_id is not None else "????"
    interface = str(device.interface_number) if device.interface_number is not None else "?"
    name = device.name or "<unknown>"
    in_size = device.input_report_bytes if device.input_report_bytes is not None else "?"
    out_size = device.output_report_bytes if device.output_report_bytes is not None else "?"
    return f"{device.path} vid=0x{vid} pid=0x{pid} iface={interface} in={in_size} out={out_size} {name}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set the keyboard RTC over the vendor HID channel")
    parser.add_argument("--device", help="explicit hidraw device, for example /dev/hidraw3")
    parser.add_argument("--vid", default=f"{DEFAULT_VID:04x}", help="USB vendor ID in hex")
    parser.add_argument("--pid", default=f"{DEFAULT_PID:04x}", help="USB product ID in hex")
    parser.add_argument(
        "--interface",
        type=int,
        default=DEFAULT_INTERFACE,
        help="USB interface number for the vendor HID endpoint",
    )
    parser.add_argument(
        "--time",
        default="now",
        help="local time as ISO-8601 or the literal 'now'",
    )
    parser.add_argument("--list", action="store_true", help="list hidraw devices and exit")
    parser.add_argument("--dry-run", action="store_true", help="print packets without opening a device")
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="read timeout for each reply in seconds",
    )
    parser.add_argument(
        "--report-size",
        type=int,
        help="override report size used for writes and reads; defaults to the device descriptor size",
    )
    parser.add_argument("--debug", action="store_true", help="print raw reports while waiting for replies")
    return parser


def _parse_hex(value: str) -> int:
    return int(value, 16)


def _wait_for_matching_reply(transport: HidrawTransport, tx, debug: bool) -> bytes:
    skipped: list[bytes] = []
    while True:
        raw_report = transport.read_report(max_length=transport.report_size or 64)
        if debug:
            print(f"{tx.name}: raw={raw_report.hex()}")

        for candidate in iter_candidate_packets(raw_report):
            if is_valid_reply(candidate, tx.expected_reply_prefix, exact=tx.expected_reply):
                for stale in skipped:
                    print(f"{tx.name}: skipped={stale.hex()}")
                return candidate
            skipped.append(candidate)

        if not iter_candidate_packets(raw_report):
            skipped.append(raw_report)


def _run_dongle_flow(transport: HidrawTransport, transactions, report_size: int, debug: bool) -> None:
    drained = transport.drain_pending_reports()
    if debug and drained:
        for report in drained:
            print(f"drained: {report.hex()}")
    for tx in transactions:
        outgoing = tx.outgoing.ljust(report_size, b"\x00")
        if len(outgoing) != report_size:
            raise RuntimeError(f"{tx.name}: report size {report_size} is smaller than packet size")
        written = transport.write(outgoing)
        if written != report_size:
            raise RuntimeError(f"{tx.name}: short write, wrote {written} bytes")
        reply = _wait_for_matching_reply(transport, tx, debug)
        print(f"{tx.name}: in={reply.hex()}")


def _run_cable_flow(transport: HidrawTransport, transactions, debug: bool) -> None:
    for tx in transactions:
        feature_request = b"\x00" + tx.outgoing
        echoed = transport.set_feature(feature_request)
        if debug:
            print(f"{tx.name}: set_feature_echo={echoed.hex()}")
        if tx.read_delay_seconds:
            time.sleep(tx.read_delay_seconds)
        raw_reply = transport.get_feature(0, CABLE_PACKET_SIZE + 1)
        reply = raw_reply[1:] if len(raw_reply) == CABLE_PACKET_SIZE + 1 and raw_reply[0] == 0 else raw_reply
        if debug:
            print(f"{tx.name}: get_feature_raw={raw_reply.hex()}")
            print(f"{tx.name}: get_feature={reply.hex()}")
        if not is_valid_cable_reply(reply, tx.expected_reply_prefix, exact=tx.expected_reply):
            raise RuntimeError(f"{tx.name}: unexpected feature reply {reply.hex()}")
        print(f"{tx.name}: in={reply.hex()}")
        if tx.post_delay_seconds:
            time.sleep(tx.post_delay_seconds)


def _pick_default_device():
    devices = enumerate_hidraw()
    for vid, pid in ((CABLE_VID, CABLE_PID), (DONGLE_VID, DONGLE_PID)):
        for device in devices:
            if (
                device.vendor_id == vid
                and device.product_id == pid
                and device.interface_number == DEFAULT_INTERFACE
            ):
                return device
    raise FileNotFoundError("no supported cable or dongle interface found")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        for device in enumerate_hidraw():
            print(_format_device_line(device))
        return 0

    when = parse_time_argument(args.time)
    if args.device:
        selected = find_matching_device(device=args.device)
    elif args.vid == f"{DEFAULT_VID:04x}" and args.pid == f"{DEFAULT_PID:04x}" and args.interface == DEFAULT_INTERFACE:
        selected = _pick_default_device()
    else:
        selected = find_matching_device(
            vendor_id=_parse_hex(args.vid),
            product_id=_parse_hex(args.pid),
            interface_number=args.interface,
        )
    is_cable = selected.vendor_id == CABLE_VID and selected.product_id == CABLE_PID
    transactions = build_cable_transaction_sequence(when) if is_cable else build_transaction_sequence(when)

    print(f"target-local-time: {when.isoformat(sep=' ')}")
    for tx in transactions:
        print(f"{tx.name}: out={tx.outgoing.hex()}")
    print(f"using-device: {_format_device_line(selected)}")

    if args.dry_run:
        return 0

    with HidrawTransport(selected.path, timeout_seconds=args.timeout) as transport:
        if is_cable:
            _run_cable_flow(transport, transactions, args.debug)
        else:
            report_size = (
                args.report_size
                or selected.output_report_bytes
                or selected.input_report_bytes
                or PACKET_SIZE
            )
            transport.report_size = report_size
            _run_dongle_flow(transport, transactions, report_size, args.debug)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
