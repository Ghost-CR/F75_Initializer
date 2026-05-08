#!/usr/bin/env python3
"""
Windows TFT upload v2 - Uses PowerShell-based HID enumeration.
"""

from __future__ import annotations

import argparse
import time

from aula_hacky.tft_protocol import (
    SCREEN_CHUNK_BYTES,
    SCREEN_CONTROL_USAGE,
    SCREEN_CONTROL_USAGE_PAGE,
    SCREEN_PIPE_USAGE,
    SCREEN_PIPE_USAGE_PAGE,
    WIRED_PID,
    WIRED_VID,
    ScreenStream,
    build_control_command,
    build_metadata_command,
    build_test_pattern_stream,
    iter_chunks,
)
from aula_hacky.windows_hid_ps import (
    CloseHandle,
    find_aula_devices,
    hid_set_feature,
    hid_write_output,
    open_hid_device,
)


class TFTTransactionError(RuntimeError):
    pass


def find_device_paths(vid: int, pid: int, usage_page: int, usage: int):
    devices = find_aula_devices()
    for dev in devices:
        if (dev["vid"] == vid and dev["pid"] == pid and 
            dev["usage_page"] == usage_page and dev["usage"] == usage):
            return dev["path"], dev["feature_report_bytes"], dev["output_report_bytes"]
    raise RuntimeError(f"No device found for vid=0x{vid:04X} pid=0x{pid:04X} usage_page=0x{usage_page:04X} usage=0x{usage:04X}")


def windows_tft_upload(stream: ScreenStream, slot: int = 1, debug: bool = False, chunk_delay: float = 0.04) -> None:
    control_path, control_feature_size, _ = find_device_paths(
        WIRED_VID, WIRED_PID, SCREEN_CONTROL_USAGE_PAGE, SCREEN_CONTROL_USAGE
    )
    pipe_path, _, pipe_output_size = find_device_paths(
        WIRED_VID, WIRED_PID, SCREEN_PIPE_USAGE_PAGE, SCREEN_PIPE_USAGE
    )

    if debug:
        print(f"control: {control_path} feature={control_feature_size}")
        print(f"pipe: {pipe_path} output={pipe_output_size}")

    control_handle = open_hid_device(control_path)
    pipe_handle = open_hid_device(pipe_path)

    try:
        # 1. Begin command: 04 18 via feature report (65 bytes with report ID)
        begin_payload = build_control_command(bytes([0x04, 0x18]))
        if debug:
            print(f"begin: {begin_payload.hex()}")
        hid_set_feature(control_handle, 0, begin_payload)
        time.sleep(0.2)

        # 2. Metadata command: 04 72 <slot> ... <chunk_count>
        meta_payload = build_metadata_command(stream.chunk_count, slot)
        if debug:
            print(f"metadata: {meta_payload.hex()}")
        hid_set_feature(control_handle, 0, meta_payload)
        time.sleep(0.05)

        # 3. Chunks via output reports on MI_02 (4097 bytes: 1 report ID + 4096 payload)
        for index, chunk in enumerate(iter_chunks(stream.data), start=1):
            if debug:
                print(f"chunk {index}/{stream.chunk_count}")
            hid_write_output(pipe_handle, 0, chunk)
            time.sleep(chunk_delay)

        # 4. Exit command: 04 02
        time.sleep(0.1)
        exit_payload = build_control_command(bytes([0x04, 0x02]))
        if debug:
            print(f"exit: {exit_payload.hex()}")
        hid_set_feature(control_handle, 0, exit_payload)

        print(f"Upload completed: {stream.frame_count} frames, {stream.chunk_count} chunks, slot {slot}")

    except Exception as exc:
        raise TFTTransactionError(f"Upload failed: {exc}") from exc
    finally:
        CloseHandle(pipe_handle)
        CloseHandle(control_handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows TFT upload for AULA F75 Max")
    parser.add_argument("--test-pattern", action="store_true", help="upload test pattern")
    parser.add_argument("--slot", type=int, default=1, help="screen slot (0..255)")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--chunk-delay", type=float, default=0.04)
    args = parser.parse_args()

    if args.slot < 0 or args.slot > 255:
        parser.error("--slot must be 0..255")

    stream = build_test_pattern_stream(delay=10)
    print(f"Stream: frames={stream.frame_count} chunks={stream.chunk_count} bytes={len(stream.data)}")

    try:
        windows_tft_upload(stream, slot=args.slot, debug=args.debug, chunk_delay=args.chunk_delay)
    except TFTTransactionError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
