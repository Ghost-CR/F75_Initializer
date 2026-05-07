from __future__ import annotations

import argparse
import time

from .hid_macos import (
    K_IOHID_REPORT_TYPE_FEATURE,
    K_IOHID_REPORT_TYPE_INPUT,
    MacHIDTransport,
    find_matching_device,
)
from .macos_cli import _format_device_line
from .tft_protocol import (
    SCREEN_CHUNK_BYTES,
    SCREEN_CONTROL_USAGE,
    SCREEN_CONTROL_USAGE_PAGE,
    SCREEN_PIPE_USAGE,
    SCREEN_PIPE_USAGE_PAGE,
    WIRED_PID,
    WIRED_VID,
    build_control_command,
    build_metadata_command,
    build_test_pattern_stream,
    iter_chunks,
)


def _hex(data: bytes) -> str:
    return data.hex()


def probe() -> None:
    stream = build_test_pattern_stream(delay=50)
    chunks = list(iter_chunks(stream.data))

    control_info = find_matching_device(WIRED_VID, WIRED_PID, SCREEN_CONTROL_USAGE_PAGE, SCREEN_CONTROL_USAGE)
    pipe_info = find_matching_device(WIRED_VID, WIRED_PID, SCREEN_PIPE_USAGE_PAGE, SCREEN_PIPE_USAGE)
    print(f"control-device: {_format_device_line(control_info)}")
    print(f"pipe-device: {_format_device_line(pipe_info)}")

    with MacHIDTransport(
        WIRED_VID, WIRED_PID, SCREEN_CONTROL_USAGE_PAGE, SCREEN_CONTROL_USAGE,
        timeout_seconds=2.0, input_report_bytes=64,
    ) as control, MacHIDTransport(
        WIRED_VID, WIRED_PID, SCREEN_PIPE_USAGE_PAGE, SCREEN_PIPE_USAGE,
        timeout_seconds=2.0, input_report_bytes=64,
    ) as pipe:

        def read_control_feature(label: str) -> bytes:
            try:
                data = control.get_report(K_IOHID_REPORT_TYPE_FEATURE, 0, 64)
                print(f"  {label}: control-feature len={len(data)} hex={_hex(data)}")
                return data
            except Exception as exc:
                print(f"  {label}: control-feature ERROR {type(exc).__name__}: {exc}")
                return b""

        def read_pipe_input(label: str) -> bytes:
            try:
                data = pipe.get_report(K_IOHID_REPORT_TYPE_INPUT, 0, 64)
                print(f"  {label}: pipe-input len={len(data)} hex={_hex(data)}")
                return data
            except Exception as exc:
                print(f"  {label}: pipe-input ERROR {type(exc).__name__}: {exc}")
                return b""

        # 1. Begin
        control.set_report(K_IOHID_REPORT_TYPE_FEATURE, 0, build_control_command(bytes([0x04, 0x18])), prefix_report_id=False)
        print("sent: screen-begin")
        time.sleep(0.2)
        read_control_feature("after-begin")

        # 2. Metadata
        control.set_report(K_IOHID_REPORT_TYPE_FEATURE, 0, build_metadata_command(stream.chunk_count), prefix_report_id=False)
        print(f"sent: screen-metadata (chunks={stream.chunk_count})")
        time.sleep(0.05)
        read_control_feature("after-metadata")
        read_pipe_input("after-metadata")

        # 3. Send chunks sequentially and read after each
        for index, chunk in enumerate(chunks[:3], start=1):
            pipe.write(chunk)
            print(f"\nsent: screen-chunk-{index}/{stream.chunk_count} ({len(chunk)} bytes)")
            time.sleep(0.02)
            read_control_feature(f"chunk-{index}-control-feature-immediate")
            read_pipe_input(f"chunk-{index}-pipe-input-immediate")
            time.sleep(0.1)
            read_control_feature(f"chunk-{index}-control-feature-delayed")
            read_pipe_input(f"chunk-{index}-pipe-input-delayed")

        # 4. Exit
        print("\nsent: screen-exit")
        control.set_report(K_IOHID_REPORT_TYPE_FEATURE, 0, build_control_command(bytes([0x04, 0x02])), prefix_report_id=False)
        time.sleep(0.1)
        read_control_feature("after-exit")
        read_pipe_input("after-exit")
        print("\nProbe complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sequential chunk ACK probe for AULA F75 Max screen upload")
    parser.parse_args()
    probe()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
