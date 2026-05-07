from __future__ import annotations

import argparse

from .hid_macos import MacHIDTransport, enumerate_hid_macos, find_matching_device
from .protocol_core import SESSION_INIT_IN, SESSION_INIT_OUT, is_valid_reply, iter_candidate_packets

DONGLE_VID = 0x05AC
DONGLE_PID = 0x024F
DONGLE_VENDOR_USAGE_PAGE_32 = 0xFF60
DONGLE_VENDOR_USAGE = 0x61


def _parse_hex(value: str) -> int:
    return int(value, 16)


def _format_device_line(device) -> str:
    vid = f"{device.vendor_id:04x}" if device.vendor_id is not None else "????"
    pid = f"{device.product_id:04x}" if device.product_id is not None else "????"
    usage_page = f"0x{device.usage_page:04x}" if device.usage_page is not None else "?"
    usage = f"0x{device.usage:04x}" if device.usage is not None else "?"
    in_size = device.input_report_bytes if device.input_report_bytes is not None else "?"
    out_size = device.output_report_bytes if device.output_report_bytes is not None else "?"
    feature_size = device.feature_report_bytes if device.feature_report_bytes is not None else "?"
    name = device.name or "<unknown>"
    transport = device.transport or "?"
    return (
        f"{device.path} vid=0x{vid} pid=0x{pid} usage_page={usage_page}"
        f" usage={usage} in={in_size} out={out_size} feature={feature_size} {transport} {name}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect macOS HID devices for AULA F75 Max")
    parser.add_argument("--vid", default=f"{DONGLE_VID:04x}", help="USB vendor ID in hex")
    parser.add_argument("--pid", default=f"{DONGLE_PID:04x}", help="USB product ID in hex")
    parser.add_argument(
        "--usage-page",
        default=f"{DONGLE_VENDOR_USAGE_PAGE_32:04x}",
        help="HID usage page in hex",
    )
    parser.add_argument(
        "--usage",
        default=f"{DONGLE_VENDOR_USAGE:04x}",
        help="HID usage in hex",
    )
    parser.add_argument("--list", action="store_true", help="list matching macOS HID devices")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="confirm the target macOS HID interface can be found",
    )
    parser.add_argument(
        "--open-probe",
        action="store_true",
        help="open the target macOS HID interface without sending reports",
    )
    parser.add_argument(
        "--session-probe",
        action="store_true",
        help="send the known non-persistent session-init packet and wait for its reply",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="read timeout for open/session probes in seconds",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    vid = _parse_hex(args.vid)
    pid = _parse_hex(args.pid)
    usage_page = _parse_hex(args.usage_page)
    usage = _parse_hex(args.usage)

    if args.list:
        for device in enumerate_hid_macos(vid, pid):
            print(_format_device_line(device))
        return 0

    if args.probe:
        device = find_matching_device(vid, pid, usage_page, usage)
        print(_format_device_line(device))
        return 0

    if args.open_probe:
        with MacHIDTransport(vid, pid, usage_page, usage, timeout_seconds=args.timeout) as transport:
            if transport.device_info is not None:
                print(_format_device_line(transport.device_info))
            print("open=ok")
        return 0

    if args.session_probe:
        with MacHIDTransport(vid, pid, usage_page, usage, timeout_seconds=args.timeout) as transport:
            report_size = transport.report_size or 32
            outgoing = SESSION_INIT_OUT.ljust(report_size, b"\x00")
            written = transport.write(outgoing)
            if written != report_size:
                raise RuntimeError(f"short write, wrote {written} bytes")
            while True:
                raw_report = transport.read_report(max_length=report_size + 1)
                for candidate in iter_candidate_packets(raw_report):
                    exact = is_valid_reply(candidate, SESSION_INIT_OUT[:3], exact=SESSION_INIT_IN)
                    prefix = is_valid_reply(candidate, SESSION_INIT_OUT[:3], exact=None)
                    if exact or prefix:
                        print(f"session-init: out={SESSION_INIT_OUT.hex()}")
                        print(f"session-init: in={candidate.hex()}")
                        print(f"session-init: match={'exact' if exact else 'prefix'}")
                        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
