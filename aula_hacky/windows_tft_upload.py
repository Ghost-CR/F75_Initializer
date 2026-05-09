from __future__ import annotations

import argparse
import time

from pathlib import Path

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
    load_image_stream,
)
from aula_hacky.windows_hid import (
    enumerate_hid_devices,
    hid_get_feature,
    hid_read_input,
    hid_set_feature,
    hid_write_output,
    open_hid_device,
)


class TFTTransactionError(RuntimeError):
    pass


def normalize_hid_path(value: str) -> str:
    """Accept either full HID device path or Windows HID instance id."""
    raw = value.strip()
    if raw.startswith("\\\\?\\"):
        return raw
    lowered = raw.lower()
    if lowered.startswith("hid\\vid_"):
        return r"\\?\\" + lowered.replace("\\", "#") + "#{4d1e55b2-f16f-11cf-88cb-001111000030}"
    return raw


def find_device_paths(vid: int, pid: int, usage_page: int, usage: int):
    for dev in enumerate_hid_devices():
        if dev["vid"] == vid and dev["pid"] == pid and dev["usage_page"] == usage_page and dev["usage"] == usage:
            return dev["path"], dev["feature_report_bytes"], dev["output_report_bytes"], dev["input_report_bytes"]
    raise RuntimeError(f"No device found for vid=0x{vid:04X} pid=0x{pid:04X} usage_page=0x{usage_page:04X} usage=0x{usage:04X}")


def windows_tft_upload(
    stream: ScreenStream,
    slot: int = 1,
    debug: bool = False,
    chunk_delay: float = 0.15,
    control_path: str | None = None,
    pipe_path: str | None = None,
) -> None:
    if control_path is None:
        control_path, control_feature_size, _, _ = find_device_paths(
            WIRED_VID, WIRED_PID, SCREEN_CONTROL_USAGE_PAGE, SCREEN_CONTROL_USAGE
        )
    else:
        control_path = normalize_hid_path(control_path)
        control_feature_size = 65

    if pipe_path is None:
        pipe_path, _, pipe_output_size, pipe_input_size = find_device_paths(
            WIRED_VID, WIRED_PID, SCREEN_PIPE_USAGE_PAGE, SCREEN_PIPE_USAGE
        )
    else:
        pipe_path = normalize_hid_path(pipe_path)
        pipe_output_size = SCREEN_CHUNK_BYTES + 1
        pipe_input_size = 65

    if debug:
        print(f"control: {control_path} feature={control_feature_size}")
        print(f"pipe: {pipe_path} output={pipe_output_size} input={pipe_input_size}")

    control_handle = open_hid_device(control_path)
    pipe_handle = open_hid_device(pipe_path)

    try:
        # 1. Begin command: 04 18 via feature report
        begin_payload = build_control_command(bytes([0x04, 0x18]))
        if debug:
            print(f"begin set: {begin_payload.hex()}")
        hid_set_feature(control_handle, 0, begin_payload)
        time.sleep(0.05)
        
        # Read back response (official software does this)
        resp = hid_get_feature(control_handle, 0, control_feature_size)
        if debug:
            print(f"begin get: {resp.hex()}")
        time.sleep(0.1)

        # 2. Metadata command: 04 72 <slot> ... <chunk_count>
        meta_payload = build_metadata_command(stream.chunk_count, slot)
        if debug:
            print(f"metadata set: {meta_payload.hex()}")
        hid_set_feature(control_handle, 0, meta_payload)
        time.sleep(0.05)
        
        # Read back response (official software does this)
        resp = hid_get_feature(control_handle, 0, control_feature_size)
        if debug:
            print(f"metadata get: {resp.hex()}")
        time.sleep(0.1)

        # 3. Chunks via output reports on MI_02
        for index, chunk in enumerate(iter_chunks(stream.data), start=1):
            if debug:
                print(f"chunk {index}/{stream.chunk_count}")
            hid_write_output(pipe_handle, 0, chunk)
            
            # Read input report between chunks (official software does this)
            try:
                resp = hid_read_input(pipe_handle, 0, pipe_input_size)
                if debug:
                    print(f"  response: {resp.hex()}")
            except TimeoutError:
                if debug:
                    print("  response: timeout (expected)")
            
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
        from aula_hacky.windows_hid import close_handle
        close_handle(control_handle)
        close_handle(pipe_handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows TFT upload diagnostic for AULA F75 Max")
    parser.add_argument("--test-pattern", action="store_true", help="upload test pattern")
    parser.add_argument("--image", type=Path, help="path to GIF/image file to upload")
    parser.add_argument("--max-frames", type=int, default=255, help="max frames from GIF (default 255)")
    parser.add_argument("--still-delay", type=int, default=50, help="delay for still images (default 50)")
    parser.add_argument("--slot", type=int, default=1, help="screen slot (0..255)")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--chunk-delay", type=float, default=0.15)
    parser.add_argument(
        "--control-path",
        help="optional full HID path or HID\\VID_... instance id for control interface (MI_03 / FF13)",
    )
    parser.add_argument(
        "--pipe-path",
        help="optional full HID path or HID\\VID_... instance id for data interface (MI_02 / FF68)",
    )
    args = parser.parse_args()

    if args.slot < 0 or args.slot > 255:
        parser.error("--slot must be 0..255")

    if args.image:
        from aula_hacky.tft_protocol import load_image_stream, prepend_black_buffer
        stream = load_image_stream(args.image, args.max_frames, args.still_delay)
        # AULA F75 firmware has an initial loop glitch that locks onto the first frame.
        # Adding a 1-frame black buffer with minimal delay absorbs this glitch.
        stream = prepend_black_buffer(stream)
    else:
        stream = build_test_pattern_stream(delay=10)
    print(f"Stream: frames={stream.frame_count} chunks={stream.chunk_count} bytes={len(stream.data)}")

    try:
        windows_tft_upload(
            stream,
            slot=args.slot,
            debug=args.debug,
            chunk_delay=args.chunk_delay,
            control_path=args.control_path,
            pipe_path=args.pipe_path,
        )
    except TFTTransactionError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
