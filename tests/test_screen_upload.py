from __future__ import annotations

from unittest import TestCase

from aula_hacky.screen_upload import (
    SCREEN_CHUNK_BYTES,
    SCREEN_FRAME_BYTES,
    SCREEN_HEADER_BYTES,
    build_metadata_command,
    build_screen_stream,
    build_test_pattern_frame,
    build_test_pattern_stream,
    delay_byte_from_seconds,
    iter_chunks,
    padded_stream_length,
    rgb565,
)


class ScreenUploadTests(TestCase):
    def test_rgb565_matches_known_values(self) -> None:
        self.assertEqual(rgb565(255, 0, 0), 0xF800)
        self.assertEqual(rgb565(0, 255, 0), 0x07E0)
        self.assertEqual(rgb565(0, 0, 255), 0x001F)
        self.assertEqual(rgb565(255, 255, 255), 0xFFFF)

    def test_delay_byte_from_seconds_uses_two_millisecond_units(self) -> None:
        self.assertEqual(delay_byte_from_seconds(0.01), 5)
        self.assertEqual(delay_byte_from_seconds(0), 5)
        self.assertEqual(delay_byte_from_seconds(1.0), 255)

    def test_padded_stream_length_for_one_frame(self) -> None:
        length, chunks = padded_stream_length(1)

        self.assertEqual(length, 9 * SCREEN_CHUNK_BYTES)
        self.assertEqual(chunks, 9)

    def test_build_screen_stream_layout(self) -> None:
        frame = bytes([0x12]) * SCREEN_FRAME_BYTES
        stream = build_screen_stream([frame], [50])

        self.assertEqual(stream.frame_count, 1)
        self.assertEqual(stream.chunk_count, 9)
        self.assertEqual(stream.data[0], 1)
        self.assertEqual(stream.data[1], 50)
        self.assertEqual(
            stream.data[SCREEN_HEADER_BYTES : SCREEN_HEADER_BYTES + 8],
            bytes([0x12]) * 8,
        )

    def test_test_pattern_stream_shape(self) -> None:
        frame = build_test_pattern_frame()
        stream = build_test_pattern_stream()

        self.assertEqual(len(frame), SCREEN_FRAME_BYTES)
        self.assertEqual(stream.frame_count, 1)
        self.assertEqual(stream.chunk_count, 9)

    def test_metadata_command_encodes_chunk_count_little_endian(self) -> None:
        command = build_metadata_command(0x1234)

        self.assertEqual(command[:3], bytes([0x04, 0x72, 0x01]))
        self.assertEqual(command[8:10], bytes([0x34, 0x12]))
        self.assertEqual(len(command), 64)

    def test_metadata_command_accepts_custom_slot(self) -> None:
        command = build_metadata_command(0x0005, slot=3)

        self.assertEqual(command[:3], bytes([0x04, 0x72, 0x03]))
        self.assertEqual(command[8:10], bytes([0x05, 0x00]))

    def test_metadata_command_rejects_invalid_slot(self) -> None:
        with self.assertRaises(ValueError):
            build_metadata_command(1, slot=-1)
        with self.assertRaises(ValueError):
            build_metadata_command(1, slot=256)

    def test_iter_chunks(self) -> None:
        chunks = list(iter_chunks(bytes(range(256)) * 16))

        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), SCREEN_CHUNK_BYTES)
