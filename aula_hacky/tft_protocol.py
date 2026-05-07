from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

WIRED_VID = 0x0C45
WIRED_PID = 0x800A
SCREEN_CONTROL_USAGE_PAGE = 0xFF13
SCREEN_CONTROL_USAGE = 0x0001
SCREEN_PIPE_USAGE_PAGE = 0xFF68
SCREEN_PIPE_USAGE = 0x0061
# TFT resolution is 128x128 RGB565 little-endian, confirmed by hardware testing.
# The box lists 320x240, but the firmware uses 128x128.
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 128
SCREEN_HEADER_BYTES = 256
SCREEN_CHUNK_BYTES = 4096
SCREEN_FRAME_BYTES = SCREEN_WIDTH * SCREEN_HEIGHT * 2


@dataclass(frozen=True)
class ScreenStream:
    data: bytes
    frame_count: int
    chunk_count: int


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def write_rgb565_le(buffer: bytearray, offset: int, r: int, g: int, b: int) -> None:
    value = rgb565(r, g, b)
    buffer[offset] = value & 0xFF
    buffer[offset + 1] = (value >> 8) & 0xFF


def delay_byte_from_seconds(seconds: float) -> int:
    if seconds <= 0:
        seconds = 0.01
    return max(1, min(255, int(round(seconds * 500.0))))


def padded_stream_length(frame_count: int) -> tuple[int, int]:
    payload_length = SCREEN_HEADER_BYTES + (frame_count * SCREEN_FRAME_BYTES)
    chunk_count = math.ceil(payload_length / SCREEN_CHUNK_BYTES)
    return chunk_count * SCREEN_CHUNK_BYTES, chunk_count


def build_screen_stream(frames: Iterable[bytes], delays: Iterable[int]) -> ScreenStream:
    frame_list = list(frames)
    delay_list = list(delays)
    if not frame_list:
        raise ValueError("screen stream needs at least one frame")
    if len(frame_list) > 255:
        raise ValueError("screen stream supports at most 255 frames")
    if len(delay_list) != len(frame_list):
        raise ValueError("delay count must match frame count")

    stream_length, chunk_count = padded_stream_length(len(frame_list))
    stream = bytearray(stream_length)
    stream[0] = len(frame_list)
    for index, delay in enumerate(delay_list):
        if not 1 <= delay <= 255:
            raise ValueError(f"frame delay must be in 1..255, got {delay}")
        stream[1 + index] = delay

    for index, frame in enumerate(frame_list):
        if len(frame) != SCREEN_FRAME_BYTES:
            raise ValueError(
                f"frame {index} must be {SCREEN_FRAME_BYTES} bytes, got {len(frame)}"
            )
        offset = SCREEN_HEADER_BYTES + (index * SCREEN_FRAME_BYTES)
        stream[offset : offset + SCREEN_FRAME_BYTES] = frame

    return ScreenStream(data=bytes(stream), frame_count=len(frame_list), chunk_count=chunk_count)


def build_test_pattern_frame() -> bytes:
    frame = bytearray(SCREEN_FRAME_BYTES)
    for y in range(SCREEN_HEIGHT):
        for x in range(SCREEN_WIDTH):
            r = (x * 255) // (SCREEN_WIDTH - 1)
            g = (y * 255) // (SCREEN_HEIGHT - 1)
            b = 255 - (((x + y) * 255) // ((SCREEN_WIDTH - 1) + (SCREEN_HEIGHT - 1)))
            if x < 4 or y < 4 or x >= SCREEN_WIDTH - 4 or y >= SCREEN_HEIGHT - 4:
                r = g = b = 255
            elif x == y or x + y == SCREEN_WIDTH - 1:
                r = g = b = 255
            offset = ((y * SCREEN_WIDTH) + x) * 2
            write_rgb565_le(frame, offset, r, g, b)
    return bytes(frame)


def build_test_pattern_stream(delay: int = 17) -> ScreenStream:
    return build_screen_stream([build_test_pattern_frame()], [delay])


def load_image_stream(path: Path, max_frames: int, still_delay: int) -> ScreenStream:
    try:
        from PIL import Image, ImageSequence
    except ImportError as exc:
        raise RuntimeError(
            "image/GIF upload needs Pillow installed; use --test-pattern to validate transport without it"
        ) from exc

    image = Image.open(path)
    source_frames = list(ImageSequence.Iterator(image))
    if not source_frames:
        raise ValueError(f"{path} does not contain image frames")

    frames: list[bytes] = []
    delays: list[int] = []
    for source in source_frames[:max_frames]:
        rendered = source.convert("RGBA")
        rendered.thumbnail((SCREEN_WIDTH, SCREEN_HEIGHT))
        canvas = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0, 255))
        x = (SCREEN_WIDTH - rendered.width) // 2
        y = (SCREEN_HEIGHT - rendered.height) // 2
        canvas.alpha_composite(rendered, (x, y))

        frame = bytearray(SCREEN_FRAME_BYTES)
        pixels = canvas.convert("RGB").load()
        for py in range(SCREEN_HEIGHT):
            for px in range(SCREEN_WIDTH):
                r, g, b = pixels[px, py]
                write_rgb565_le(frame, ((py * SCREEN_WIDTH) + px) * 2, r, g, b)
        frames.append(bytes(frame))

        duration_ms = source.info.get("duration")
        if duration_ms is None:
            delays.append(still_delay)
        else:
            delays.append(delay_byte_from_seconds(float(duration_ms) / 1000.0))

    if len(frames) == 1 and not getattr(image, "is_animated", False):
        delays[0] = still_delay
    return build_screen_stream(frames, delays)


def build_metadata_command(chunk_count: int, slot: int = 1) -> bytes:
    if not 0 <= slot <= 255:
        raise ValueError(f"slot must be 0..255, got {slot}")
    command = bytearray(64)
    command[0] = 0x04
    command[1] = 0x72
    command[2] = slot
    command[8] = chunk_count & 0xFF
    command[9] = (chunk_count >> 8) & 0xFF
    return bytes(command)


def build_control_command(prefix: bytes) -> bytes:
    command = bytearray(64)
    command[: len(prefix)] = prefix
    return bytes(command)


def iter_chunks(stream: bytes) -> Iterable[bytes]:
    if len(stream) % SCREEN_CHUNK_BYTES != 0:
        raise ValueError("screen stream length must be a multiple of 4096")
    for offset in range(0, len(stream), SCREEN_CHUNK_BYTES):
        yield stream[offset : offset + SCREEN_CHUNK_BYTES]
