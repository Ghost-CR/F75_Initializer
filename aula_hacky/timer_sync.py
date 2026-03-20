from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .cli import (
    CABLE_PID,
    CABLE_VID,
    DEFAULT_INTERFACE,
    DONGLE_PID,
    DONGLE_VID,
    _format_device_line,
    _run_cable_flow,
    _run_dongle_flow,
    _wait_for_matching_reply,
)
from .hidraw_linux import HidrawTransport, enumerate_hidraw
from .protocol import (
    CABLE_PACKET_SIZE,
    PACKET_SIZE,
    build_cable_transaction_sequence,
    build_transaction_sequence,
    is_valid_cable_reply,
    parse_time_argument,
)

DEFAULT_STATE_FILE = Path("/tmp/aula-hacky-poll-state.json")
DEFAULT_PROBE_INTERVAL_SECONDS = 30.0


def _pick_default_device():
    devices = enumerate_hidraw()
    for vid, pid in ((CABLE_VID, CABLE_PID), (DONGLE_VID, DONGLE_PID)):
        for device in devices:
            if (
                device.vendor_id == vid
                and device.product_id == pid
                and device.interface_number == DEFAULT_INTERFACE
                and os.path.exists(device.path)
            ):
                return device
    return None


def _device_key(device) -> str:
    return f"{device.vendor_id:04x}:{device.product_id:04x}:{device.interface_number}:{device.path}"


def _load_state(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle)
    tmp_path.replace(path)


def _clear_state(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _probe_dongle(transport: HidrawTransport, tx, report_size: int, debug: bool) -> bool:
    outgoing = tx.outgoing.ljust(report_size, b"\x00")
    if len(outgoing) != report_size:
        return False
    written = transport.write(outgoing)
    if written != report_size:
        return False
    _wait_for_matching_reply(transport, tx, debug)
    return True


def _probe_cable(transport: HidrawTransport, tx, debug: bool) -> bool:
    feature_request = b"\x00" + tx.outgoing
    transport.set_feature(feature_request)
    if tx.read_delay_seconds:
        time.sleep(tx.read_delay_seconds)
    raw_reply = transport.get_feature(0, CABLE_PACKET_SIZE + 1)
    reply = raw_reply[1:] if len(raw_reply) == CABLE_PACKET_SIZE + 1 and raw_reply[0] == 0 else raw_reply
    if debug:
        print(f"{tx.name}: probe_get_feature_raw={raw_reply.hex()}")
        print(f"{tx.name}: probe_get_feature={reply.hex()}")
    return is_valid_cable_reply(reply, tx.expected_reply_prefix, exact=tx.expected_reply)


def _probe_device(selected, timeout: float, debug: bool) -> bool:
    when = parse_time_argument("now")
    is_cable = selected.vendor_id == CABLE_VID and selected.product_id == CABLE_PID
    tx = (
        build_cable_transaction_sequence(when)[0]
        if is_cable
        else build_transaction_sequence(when)[0]
    )

    with HidrawTransport(selected.path, timeout_seconds=timeout) as transport:
        if is_cable:
            return _probe_cable(transport, tx, debug)
        report_size = selected.output_report_bytes or selected.input_report_bytes or PACKET_SIZE
        transport.report_size = report_size
        return _probe_dongle(transport, tx, report_size, debug)


def _sync_device(selected, when, timeout: float, debug: bool) -> None:
    is_cable = selected.vendor_id == CABLE_VID and selected.product_id == CABLE_PID
    transactions = build_cable_transaction_sequence(when) if is_cable else build_transaction_sequence(when)

    print(f"target-local-time: {when.isoformat(sep=' ')}")
    print(f"using-device: {_format_device_line(selected)}")

    with HidrawTransport(selected.path, timeout_seconds=timeout) as transport:
        if is_cable:
            _run_cable_flow(transport, transactions, debug)
        else:
            report_size = selected.output_report_bytes or selected.input_report_bytes or PACKET_SIZE
            transport.report_size = report_size
            _run_dongle_flow(transport, transactions, report_size, debug)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Poll for a supported keyboard interface and sync its RTC when present"
    )
    parser.add_argument(
        "--time",
        default="now",
        help="local time as ISO-8601 or the literal 'now'",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="read timeout for each reply in seconds",
    )
    parser.add_argument("--debug", action="store_true", help="print packet exchange details")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="stay silent when no supported device is present",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help="path to the poll state file",
    )
    parser.add_argument(
        "--probe-interval",
        type=float,
        default=DEFAULT_PROBE_INTERVAL_SECONDS,
        help="seconds between lightweight liveness probes after a successful sync",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_file)
    now = time.time()
    selected = _pick_default_device()

    if selected is None:
        _clear_state(state_path)
        if not args.quiet:
            print("no supported cable or dongle interface present")
        return 0

    state = _load_state(state_path)
    current_key = _device_key(selected)
    state_key = state.get("device_key")
    synced = state.get("synced") is True and state_key == current_key
    last_probe_at = float(state.get("last_probe_at", 0.0) or 0.0)

    if synced and now - last_probe_at < args.probe_interval:
        return 0

    if synced:
        try:
            if _probe_device(selected, args.timeout, args.debug):
                state["last_probe_at"] = now
                _save_state(state_path, state)
                return 0
        except Exception:
            pass
        state = {"device_key": current_key, "synced": False, "last_probe_at": now}
        _save_state(state_path, state)
        return 0

    when = parse_time_argument(args.time)
    _sync_device(selected, when, args.timeout, args.debug)
    _save_state(
        state_path,
        {
            "device_key": current_key,
            "synced": True,
            "last_probe_at": now,
            "last_sync_at": now,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
