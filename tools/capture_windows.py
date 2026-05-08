#!/usr/bin/env python3
"""
Capture exact bytes sent by Windows uploader to keyboard.
Run on Windows with: python tools/capture_windows.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aula_hacky.tft_protocol import (
    SCREEN_CHUNK_BYTES,
    build_control_command,
    build_metadata_command,
    build_test_pattern_stream,
    iter_chunks,
)
from aula_hacky.windows_hid import (
    enumerate_hid_devices,
    hid_set_feature,
    hid_write_output,
    open_hid_device,
)
from tools.byte_logger import ByteLogger


def find_device_paths(vid: int, pid: int, usage_page: int, usage: int):
    for dev in enumerate_hid_devices():
        if (dev["vid"] == vid and dev["pid"] == pid and 
            dev["usage_page"] == usage_page and dev["usage"] == usage):
            return dev["path"], dev["feature_report_bytes"], dev["output_report_bytes"]
    raise RuntimeError(f"No device found")


def main() -> int:
    logger = ByteLogger(output_dir="logs", platform="windows")
    
    print("Windows Buffer Capture for AULA F75 Max")
    print(f"Logging to: {logger.log_file}")
    print("=" * 60)
    
    stream = build_test_pattern_stream(delay=10)
    print(f"Stream: {stream.frame_count} frames, {stream.chunk_count} chunks")
    
    # Use manual paths (known working)
    control_path = r"\\?\hid#vid_0c45&pid_800a&mi_03#8&5e1a8cd&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
    pipe_path = r"\\?\hid#vid_0c45&pid_800a&mi_02#8&1da53512&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
    
    control_handle = open_hid_device(control_path)
    pipe_handle = open_hid_device(pipe_path)
    
    try:
        # 1. Begin command
        begin_payload = build_control_command(bytes([0x04, 0x18]))
        print(f"\n[1] Begin: {begin_payload.hex()}")
        logger.log_feature_set(0, begin_payload, "begin")
        hid_set_feature(control_handle, 0, begin_payload)
        time.sleep(0.2)
        
        # 2. Metadata command
        meta_payload = build_metadata_command(stream.chunk_count, slot=1)
        print(f"[2] Metadata: {meta_payload.hex()}")
        logger.log_feature_set(0, meta_payload, "metadata")
        hid_set_feature(control_handle, 0, meta_payload)
        time.sleep(0.05)
        
        # 3. Chunks
        for index, chunk in enumerate(iter_chunks(stream.data), start=1):
            print(f"[3.{index}] Chunk {index}/{stream.chunk_count}: {chunk[:16].hex()}...")
            logger.log_output(0, chunk, f"chunk_{index}")
            hid_write_output(pipe_handle, 0, chunk)
            time.sleep(0.04)
        
        # 4. Exit command
        exit_payload = build_control_command(bytes([0x04, 0x02]))
        print(f"[4] Exit: {exit_payload.hex()}")
        logger.log_feature_set(0, exit_payload, "exit")
        hid_set_feature(control_handle, 0, exit_payload)
        
        print(f"\n✅ Capture complete. Log: {logger.log_file}")
        
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return 1
    finally:
        from ctypes import wintypes
        ctypes.windll.kernel32.CloseHandle(pipe_handle)
        ctypes.windll.kernel32.CloseHandle(control_handle)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
