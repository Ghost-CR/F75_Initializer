#!/usr/bin/env python3
"""
Capture exact bytes sent by macOS uploader to keyboard.
Run on macOS with: python tools/capture_macos.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aula_hacky.tft_protocol import (
    SCREEN_CHUNK_BYTES,
    build_control_command,
    build_metadata_command,
    build_test_pattern_stream,
    iter_chunks,
)
from aula_hacky.hid_macos import (
    K_IOHID_REPORT_TYPE_FEATURE,
    MacHIDTransport,
    find_matching_device,
)
from aula_hacky.tft_protocol import (
    SCREEN_CONTROL_USAGE,
    SCREEN_CONTROL_USAGE_PAGE,
    SCREEN_PIPE_USAGE,
    SCREEN_PIPE_USAGE_PAGE,
    WIRED_PID,
    WIRED_VID,
)
from tools.byte_logger import ByteLogger


def main() -> int:
    logger = ByteLogger(output_dir="logs", platform="macos")
    
    print("macOS Buffer Capture for AULA F75 Max")
    print(f"Logging to: {logger.log_file}")
    print("=" * 60)
    
    stream = build_test_pattern_stream(delay=10)
    print(f"Stream: {stream.frame_count} frames, {stream.chunk_count} chunks")
    
    # Open devices
    control = MacHIDTransport(
        WIRED_VID, WIRED_PID,
        SCREEN_CONTROL_USAGE_PAGE, SCREEN_CONTROL_USAGE,
        timeout_seconds=1.0,
        input_report_bytes=64,
    )
    pipe = MacHIDTransport(
        WIRED_VID, WIRED_PID,
        SCREEN_PIPE_USAGE_PAGE, SCREEN_PIPE_USAGE,
        timeout_seconds=1.0,
        input_report_bytes=64,
    )
    
    control.__enter__()
    pipe.__enter__()
    
    try:
        pipe.drain_pending_reports()
        
        # 1. Begin command
        begin_payload = build_control_command(bytes([0x04, 0x18]))
        print(f"\n[1] Begin: {begin_payload.hex()}")
        logger.log_feature_set(0, begin_payload, "begin")
        control.set_report(
            K_IOHID_REPORT_TYPE_FEATURE,
            report_id=0,
            payload=begin_payload,
            prefix_report_id=False,
        )
        time.sleep(0.2)
        
        # 2. Metadata command
        meta_payload = build_metadata_command(stream.chunk_count, slot=1)
        print(f"[2] Metadata: {meta_payload.hex()}")
        logger.log_feature_set(0, meta_payload, "metadata")
        control.set_report(
            K_IOHID_REPORT_TYPE_FEATURE,
            report_id=0,
            payload=meta_payload,
            prefix_report_id=False,
        )
        time.sleep(0.05)
        
        # 3. Chunks
        for index, chunk in enumerate(iter_chunks(stream.data), start=1):
            print(f"[3.{index}] Chunk {index}/{stream.chunk_count}: {chunk[:16].hex()}...")
            logger.log_output(0, chunk, f"chunk_{index}")
            pipe.write(chunk)
            time.sleep(0.04)
        
        # 4. Exit command
        exit_payload = build_control_command(bytes([0x04, 0x02]))
        print(f"[4] Exit: {exit_payload.hex()}")
        logger.log_feature_set(0, exit_payload, "exit")
        control.set_report(
            K_IOHID_REPORT_TYPE_FEATURE,
            report_id=0,
            payload=exit_payload,
            prefix_report_id=False,
        )
        
        print(f"\n✅ Capture complete. Log: {logger.log_file}")
        
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return 1
    finally:
        pipe.__exit__(None, None, None)
        control.__exit__(None, None, None)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
