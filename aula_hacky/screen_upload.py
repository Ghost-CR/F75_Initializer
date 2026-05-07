from __future__ import annotations

import argparse
from pathlib import Path

from .tft_protocol import (
    SCREEN_CHUNK_BYTES,
    SCREEN_CONTROL_USAGE,
    SCREEN_CONTROL_USAGE_PAGE,
    SCREEN_FRAME_BYTES,
    SCREEN_HEADER_BYTES,
    SCREEN_HEIGHT,
    SCREEN_PIPE_USAGE,
    SCREEN_PIPE_USAGE_PAGE,
    SCREEN_WIDTH,
    WIRED_PID,
    WIRED_VID,
    ScreenStream,
    build_control_command,
    build_metadata_command,
    build_screen_stream,
    build_test_pattern_frame,
    build_test_pattern_stream,
    delay_byte_from_seconds,
    iter_chunks,
    load_image_stream,
    padded_stream_length,
    rgb565,
    write_rgb565_le,
)
from .tft_service import TFTService, TFTTransactionError

# Re-export protocol helpers so tests and callers can continue importing from here.
__all__ = [
    "SCREEN_CHUNK_BYTES",
    "SCREEN_CONTROL_USAGE",
    "SCREEN_CONTROL_USAGE_PAGE",
    "SCREEN_FRAME_BYTES",
    "SCREEN_HEADER_BYTES",
    "SCREEN_HEIGHT",
    "SCREEN_PIPE_USAGE",
    "SCREEN_PIPE_USAGE_PAGE",
    "SCREEN_WIDTH",
    "WIRED_PID",
    "WIRED_VID",
    "ScreenStream",
    "build_control_command",
    "build_metadata_command",
    "build_parser",
    "build_screen_stream",
    "build_test_pattern_frame",
    "build_test_pattern_stream",
    "delay_byte_from_seconds",
    "iter_chunks",
    "load_image_stream",
    "main",
    "padded_stream_length",
    "rgb565",
    "write_rgb565_le",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload image/GIF data to the AULA F75 Max TFT screen over USB-C")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--test-pattern", action="store_true", help="upload a generated 128x128 test pattern")
    source.add_argument("--image", help="image/GIF path; requires Pillow")
    parser.add_argument("--max-frames", type=int, default=32, help="maximum GIF frames to upload")
    parser.add_argument("--still-delay", type=int, default=50, help="delay byte for still images/test pattern")
    parser.add_argument("--slot", type=int, default=1, help="screen slot to upload to (0..255, default 1)")
    parser.add_argument("--timeout", type=float, default=1.0, help="HID transport timeout in seconds")
    parser.add_argument("--chunk-delay", type=float, default=0.04, help="delay between chunks when uploading")
    parser.add_argument("--dry-run", action="store_true", help="build stream and print metadata without writing HID")
    parser.add_argument("--debug", action="store_true", help="print control packets and chunk progress")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.max_frames < 1 or args.max_frames > 255:
        parser.error("--max-frames must be in 1..255")
    if args.still_delay < 1 or args.still_delay > 255:
        parser.error("--still-delay must be in 1..255")
    if args.slot < 0 or args.slot > 255:
        parser.error("--slot must be in 0..255")

    if args.test_pattern:
        stream = build_test_pattern_stream(delay=args.still_delay)
        label = "test-pattern"
    else:
        stream = load_image_stream(Path(args.image), args.max_frames, args.still_delay)
        label = str(args.image)

    print(
        f"screen-stream: source={label} frames={stream.frame_count}"
        f" chunks={stream.chunk_count} bytes={len(stream.data)}"
    )
    print(f"screen-metadata: {build_metadata_command(stream.chunk_count).hex()}")
    if args.dry_run:
        return 0

    try:
        TFTService(
            timeout_seconds=args.timeout,
            debug=args.debug,
            chunk_delay_seconds=args.chunk_delay,
        ).upload(stream, slot=args.slot)
    except TFTTransactionError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
