from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass

from .hid_macos import (
    K_IOHID_REPORT_TYPE_FEATURE,
    K_IOHID_REPORT_TYPE_INPUT,
    K_IOHID_REPORT_TYPE_OUTPUT,
    MacHIDError,
    MacHIDTransport,
)
from .macos_cli import (
    DONGLE_PID,
    DONGLE_VENDOR_USAGE,
    DONGLE_VENDOR_USAGE_PAGE_32,
    DONGLE_VID,
)
from .protocol_core import SESSION_INIT_IN, SESSION_INIT_OUT, is_valid_reply, iter_candidate_packets


@dataclass(frozen=True)
class ProbeCase:
    usage_page: int
    report_size: int
    seize: bool
    write_report_type: int
    write_report_id: int
    payload_shape: str
    read_strategy: str


def _parse_hex(value: str) -> int:
    return int(value, 16)


def _report_type_name(report_type: int) -> str:
    if report_type == K_IOHID_REPORT_TYPE_INPUT:
        return "input"
    if report_type == K_IOHID_REPORT_TYPE_OUTPUT:
        return "output"
    if report_type == K_IOHID_REPORT_TYPE_FEATURE:
        return "feature"
    return str(report_type)


def _payload_for(shape: str, report_size: int) -> tuple[int, bytes, bool]:
    packet = SESSION_INIT_OUT.ljust(report_size, b"\x00")
    if shape == "raw":
        return 0, packet, False
    if shape == "prefix-zero":
        return 0, packet, True
    if shape == "first-byte-id":
        return SESSION_INIT_OUT[0], SESSION_INIT_OUT[1:].ljust(report_size - 1, b"\x00"), False
    if shape == "first-byte-id-prefix":
        return SESSION_INIT_OUT[0], SESSION_INIT_OUT[1:].ljust(report_size - 1, b"\x00"), True
    raise ValueError(f"unknown payload shape: {shape}")


def _candidate_match(raw_report: bytes) -> tuple[str, list[bytes]]:
    candidates = iter_candidate_packets(raw_report)
    exact = any(
        is_valid_reply(candidate, SESSION_INIT_OUT[:3], exact=SESSION_INIT_IN)
        for candidate in candidates
    )
    if exact:
        return "EXACT", candidates
    prefix = any(
        is_valid_reply(candidate, SESSION_INIT_OUT[:3], exact=None)
        for candidate in candidates
    )
    if prefix:
        return "PREFIX", candidates
    return "MISS", candidates


def _read_with_strategy(transport: MacHIDTransport, strategy: str, report_size: int) -> bytes:
    if strategy == "callback":
        return transport.read_report(max_length=report_size + 1)
    if strategy == "get-input-id0":
        return transport.get_report(K_IOHID_REPORT_TYPE_INPUT, 0, report_size + 1)
    if strategy == "get-feature-id0":
        return transport.get_report(K_IOHID_REPORT_TYPE_FEATURE, 0, report_size + 1)
    raise ValueError(f"unknown read strategy: {strategy}")


def _run_case(args: argparse.Namespace, case: ProbeCase) -> tuple[str, str]:
    report_id, payload, prefix_report_id = _payload_for(case.payload_shape, case.report_size)
    label = (
        f"usage_page=0x{case.usage_page:04x} report_size={case.report_size}"
        f" seize={int(case.seize)} write={_report_type_name(case.write_report_type)}"
        f" report_id={report_id} shape={case.payload_shape} read={case.read_strategy}"
    )
    try:
        with MacHIDTransport(
            args.vid,
            args.pid,
            case.usage_page,
            args.usage,
            timeout_seconds=args.timeout,
            input_report_bytes=case.report_size,
            seize=case.seize,
        ) as transport:
            transport.drain_pending_reports()
            written = transport.set_report(
                report_type=case.write_report_type,
                report_id=report_id,
                payload=payload,
                prefix_report_id=prefix_report_id,
            )
            raw_report = _read_with_strategy(transport, case.read_strategy, case.report_size)
            status, candidates = _candidate_match(raw_report)
            detail = (
                f"{label} write_len={written} raw={raw_report.hex()}"
                f" candidates={[candidate.hex() for candidate in candidates]}"
            )
            return detail, status
    except Exception as exc:
        return f"{label} error={type(exc).__name__}: {exc}", "MISS"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe macOS IOKit HID report semantics with the non-persistent session-init packet"
    )
    parser.add_argument("--vid", type=lambda value: int(value, 16), default=DONGLE_VID)
    parser.add_argument("--pid", type=lambda value: int(value, 16), default=DONGLE_PID)
    parser.add_argument("--usage", type=lambda value: int(value, 16), default=DONGLE_VENDOR_USAGE)
    parser.add_argument("--timeout", type=float, default=0.4)
    parser.add_argument("--stop-on-match", action="store_true")
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="only treat the byte-exact Linux capture reply as a match",
    )
    parser.add_argument(
        "--usage-pages",
        nargs="*",
        default=[f"{DONGLE_VENDOR_USAGE_PAGE_32:04x}", "ff59"],
        help="usage pages to test in hex",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.usage_pages = [_parse_hex(value) for value in args.usage_pages]

    cases = [
        ProbeCase(
            usage_page=usage_page,
            report_size=64 if usage_page == 0xFF59 else 32,
            seize=seize,
            write_report_type=write_report_type,
            write_report_id=0,
            payload_shape=payload_shape,
            read_strategy=read_strategy,
        )
        for usage_page, seize, write_report_type, payload_shape, read_strategy in itertools.product(
            args.usage_pages,
            (False, True),
            (K_IOHID_REPORT_TYPE_OUTPUT, K_IOHID_REPORT_TYPE_FEATURE),
            ("raw", "prefix-zero", "first-byte-id", "first-byte-id-prefix"),
            ("callback", "get-input-id0", "get-feature-id0"),
        )
    ]

    matched_any = False
    for index, case in enumerate(cases, start=1):
        detail, status = _run_case(args, case)
        matched = status == "EXACT" or (status == "PREFIX" and not args.exact_only)
        print(f"{index:03d} {status} {detail}")
        matched_any = matched_any or matched
        if matched and args.stop_on_match:
            return 0
    if not matched_any:
        raise SystemExit("no matrix case produced the expected session-init reply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
