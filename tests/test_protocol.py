from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from aula_hacky.protocol_core import (
    CABLE_RTC_SET_IN_EXAMPLE,
    CABLE_SESSION_FINALIZE_IN,
    CABLE_SESSION_FINALIZE_OUT,
    CABLE_SESSION_INIT_IN,
    CABLE_SESSION_INIT_OUT,
    CABLE_SESSION_PREPARE_IN,
    CABLE_SESSION_PREPARE_OUT,
    PACKET_SIZE,
    RTC_SET_ACK,
    SESSION_INIT_IN,
    SESSION_INIT_OUT,
    SESSION_QUERY_IN,
    SESSION_QUERY_OUT,
    build_rtc_set_packet,
    build_cable_rgb_transaction_sequence,
    build_cable_rtc_set_packet,
    build_cable_transaction_sequence,
    build_transaction_sequence,
    build_wireless_rgb_commit_packet,
    build_wireless_rgb_led_mode_packet,
    build_wireless_rgb_mode_packet,
    checksum,
    decode_rtc_set_packet,
    is_valid_cable_reply,
    iter_candidate_packets,
    validate_packet,
    validate_reply,
)


class ProtocolTests(TestCase):
    def test_legacy_protocol_module_reexports_core_builders(self) -> None:
        from aula_hacky import protocol

        self.assertIs(protocol.build_rtc_set_packet, build_rtc_set_packet)
        self.assertIs(protocol.build_cable_rtc_set_packet, build_cable_rtc_set_packet)

    def test_observed_packets_have_valid_checksums(self) -> None:
        for packet in (
            SESSION_INIT_OUT,
            SESSION_INIT_IN,
            SESSION_QUERY_OUT,
            SESSION_QUERY_IN,
            RTC_SET_ACK,
            bytes.fromhex("0c100000015a1a03140a07350005000000aa55000000000000000000000000f2"),
        ):
            self.assertEqual(len(packet), PACKET_SIZE)
            validate_packet(packet)

    def test_build_rtc_packet_reproduces_capture(self) -> None:
        when = datetime(2026, 3, 20, 10, 7, 53)
        actual = build_rtc_set_packet(when)
        expected = bytes.fromhex(
            "0c100000015a1a03140a07350005000000aa55000000000000000000000000f2"
        )
        self.assertEqual(actual, expected)

    def test_checksum_byte_matches_sum(self) -> None:
        packet = build_rtc_set_packet(datetime(2026, 3, 20, 10, 7, 53))
        self.assertEqual(packet[-1], checksum(packet[:-1]))

    def test_decode_rtc_packet(self) -> None:
        decoded = decode_rtc_set_packet(
            bytes.fromhex("0c100000015a1a03140a07350005000000aa55000000000000000000000000f2")
        )
        self.assertEqual(
            decoded,
            {
                "year": 2026,
                "month": 3,
                "day": 20,
                "hour": 10,
                "minute": 7,
                "second": 53,
            },
        )

    def test_transaction_sequence_shapes(self) -> None:
        txs = build_transaction_sequence(datetime(2026, 3, 20, 10, 7, 53))
        self.assertEqual([tx.name for tx in txs], ["session-init", "session-query", "rtc-set"])
        validate_reply(SESSION_INIT_IN, txs[0].expected_reply_prefix, txs[0].expected_reply)
        validate_reply(SESSION_QUERY_IN, txs[1].expected_reply_prefix, txs[1].expected_reply)
        validate_reply(RTC_SET_ACK, txs[2].expected_reply_prefix, txs[2].expected_reply)

    def test_iter_candidate_packets_finds_embedded_packet(self) -> None:
        raw = b"\x00\x11" + SESSION_QUERY_IN + b"\x00" * 7
        candidates = iter_candidate_packets(raw)
        self.assertIn(SESSION_QUERY_IN, candidates)

    def test_build_cable_rtc_packet_reproduces_capture(self) -> None:
        when = datetime(2026, 3, 20, 11, 10, 18)
        actual = build_cable_rtc_set_packet(when)
        expected = bytes.fromhex(
            "00015a1a03140b0a120005000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa55"
        )
        self.assertEqual(actual, expected)

    def test_cable_transaction_sequence_shapes(self) -> None:
        txs = build_cable_transaction_sequence(datetime(2026, 3, 20, 11, 10, 18))
        self.assertEqual(
            [tx.name for tx in txs],
            ["cable-session-init", "cable-session-prepare", "cable-rtc-set", "cable-session-finalize"],
        )
        self.assertTrue(
            is_valid_cable_reply(CABLE_SESSION_INIT_IN, txs[0].expected_reply_prefix, txs[0].expected_reply)
        )
        self.assertTrue(
            is_valid_cable_reply(
                CABLE_SESSION_PREPARE_IN, txs[1].expected_reply_prefix, txs[1].expected_reply
            )
        )
        self.assertTrue(is_valid_cable_reply(CABLE_RTC_SET_IN_EXAMPLE, txs[2].expected_reply_prefix))
        self.assertTrue(
            is_valid_cable_reply(CABLE_SESSION_FINALIZE_IN, txs[3].expected_reply_prefix, txs[3].expected_reply)
        )

    def test_wireless_rgb_packets_reproduce_public_reverse_engineering(self) -> None:
        self.assertEqual(
            build_wireless_rgb_mode_packet(1),
            bytes.fromhex("0501002000000000000000000000000000aa5500000000000000000000000025"),
        )
        self.assertEqual(
            build_wireless_rgb_commit_packet(),
            bytes.fromhex("0f0000000000000000000000000000000000000000000000000000000000000f"),
        )
        self.assertEqual(
            build_wireless_rgb_led_mode_packet(
                mode=1,
                brightness=5,
                speed=3,
                direction=0,
                colorful=0,
                color=0x3366CC,
            ),
            bytes.fromhex("05100001cc663300000000000503000000aa5500000000000000000000000082"),
        )

    def test_cable_rgb_sequence_reproduces_public_reverse_engineering(self) -> None:
        txs = build_cable_rgb_transaction_sequence(
            mode=1,
            brightness=5,
            speed=3,
            direction=0,
            colorful=0,
            color=0x3366CC,
        )
        self.assertEqual(
            [tx.name for tx in txs],
            [
                "cable-rgb-begin",
                "cable-rgb-select",
                "cable-rgb-payload",
                "cable-rgb-apply",
                "cable-rgb-finish",
            ],
        )
        self.assertEqual(txs[1].outgoing[:9], bytes.fromhex("041300000000000001"))
        self.assertEqual(
            txs[2].outgoing[:16],
            bytes.fromhex("01cc663300000000000503000000aa55"),
        )
        self.assertEqual(txs[4].outgoing[:2], bytes.fromhex("04f0"))
