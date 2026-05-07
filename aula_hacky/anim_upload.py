from __future__ import annotations

import argparse
import math

from aula_hacky.tft_protocol import (
    SCREEN_FRAME_BYTES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    build_screen_stream,
    write_rgb565_le,
)
from aula_hacky.tft_service import TFTService


def build_rainbow_wheel_frame(frame_index: int, total_frames: int) -> bytes:
    frame = bytearray(SCREEN_FRAME_BYTES)
    angle_offset = (frame_index / total_frames) * 360
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    max_distance = SCREEN_WIDTH * 0.7

    for y in range(SCREEN_HEIGHT):
        for x in range(SCREEN_WIDTH):
            cx = x - center_x
            cy = y - center_y
            angle = math.degrees(math.atan2(cy, cx)) + angle_offset
            distance = math.sqrt(cx * cx + cy * cy)

            hue = (angle % 360) / 360.0
            h = hue * 6
            i = int(h)
            f = h - i
            q = 1 - f

            if i % 6 == 0:
                r, g, b = 1.0, f, 0.0
            elif i % 6 == 1:
                r, g, b = q, 1.0, 0.0
            elif i % 6 == 2:
                r, g, b = 0.0, 1.0, f
            elif i % 6 == 3:
                r, g, b = 0.0, q, 1.0
            elif i % 6 == 4:
                r, g, b = f, 0.0, 1.0
            else:
                r, g, b = 1.0, 0.0, q

            edge_darken = max(0.0, 1.0 - distance / max_distance)
            r *= edge_darken
            g *= edge_darken
            b *= edge_darken

            if abs(cx) < 2 or abs(cy) < 2:
                r = g = b = 1.0
            if x < 3 or y < 3 or x >= SCREEN_WIDTH - 3 or y >= SCREEN_HEIGHT - 3:
                r = g = b = 1.0

            offset = ((y * SCREEN_WIDTH) + x) * 2
            write_rgb565_le(frame, offset, int(r * 255), int(g * 255), int(b * 255))

    return bytes(frame)


def build_black_frame() -> bytes:
    return bytes(SCREEN_FRAME_BYTES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload animated rainbow wheel with black buffer frame")
    parser.add_argument("--frames", type=int, default=8, help="number of animation frames")
    parser.add_argument("--delay", type=int, default=255, help="frame delay in firmware units (~2ms each)")
    parser.add_argument("--slot", type=int, default=1, help="screen slot to upload to (0..255, default 1)")
    parser.add_argument("--chunk-delay", type=float, default=0.04, help="delay between 4096-byte chunks")
    parser.add_argument("--debug", action="store_true", help="print debug info")
    parser.add_argument("--no-buffer", action="store_true", help="do not prepend a black buffer frame")
    args = parser.parse_args()

    if args.frames < 1 or args.frames > 254:
        parser.error("--frames must be 1..254 (room for optional buffer frame)")
    if args.delay < 1 or args.delay > 255:
        parser.error("--delay must be 1..255")
    if args.slot < 0 or args.slot > 255:
        parser.error("--slot must be in 0..255")

    frames = []
    delays = []

    # Buffer frame: black, shown only briefly (minimal delay)
    # This absorbs the firmware's initial loop glitch.
    if not args.no_buffer:
        frames.append(build_black_frame())
        delays.append(1)  # 1 unit = ~2ms, barely visible

    for i in range(args.frames):
        frames.append(build_rainbow_wheel_frame(i, args.frames))
        delays.append(args.delay)

    stream = build_screen_stream(frames, delays)
    print(f"Animation: {len(frames)} frames (inc. buffer={not args.no_buffer}), delay={args.delay}, chunks={stream.chunk_count}")

    TFTService(
        timeout_seconds=1.0,
        debug=args.debug,
        chunk_delay_seconds=args.chunk_delay,
    ).upload(stream, slot=args.slot)

    print("Animation uploaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
