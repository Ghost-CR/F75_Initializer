from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from aula_hacky.macos_rtc_sync import match_transaction_reply
from aula_hacky.protocol_core import SESSION_INIT_IN, build_transaction_sequence


class MacOSRTCSyncTests(TestCase):
    def test_accepts_known_session_init_prefix_variant(self) -> None:
        tx = build_transaction_sequence(datetime(2026, 3, 20, 10, 7, 53))[0]
        macos_reply = bytes.fromhex(
            "02000040300000450c0a801001ffff000000000000000000000000000000005c"
        )

        match = match_transaction_reply(macos_reply, tx)

        self.assertIsNotNone(match)
        self.assertEqual(match.packet, macos_reply)
        self.assertEqual(match.kind, "prefix")

    def test_prefers_exact_reply_when_available(self) -> None:
        tx = build_transaction_sequence(datetime(2026, 3, 20, 10, 7, 53))[0]

        match = match_transaction_reply(SESSION_INIT_IN, tx)

        self.assertIsNotNone(match)
        self.assertEqual(match.packet, SESSION_INIT_IN)
        self.assertEqual(match.kind, "exact")

    def test_accepts_known_session_query_prefix_variant(self) -> None:
        tx = build_transaction_sequence(datetime(2026, 3, 20, 10, 7, 53))[1]
        macos_reply = bytes.fromhex(
            "2001004100000000000000000000000000000000000000000000000000000062"
        )

        match = match_transaction_reply(macos_reply, tx)

        self.assertIsNotNone(match)
        self.assertEqual(match.packet, macos_reply)
        self.assertEqual(match.kind, "prefix")

    def test_rejects_rtc_prefix_variant_by_default(self) -> None:
        tx = build_transaction_sequence(datetime(2026, 3, 20, 10, 7, 53))[2]
        echoed_rtc_command = tx.outgoing

        self.assertIsNone(match_transaction_reply(echoed_rtc_command, tx))
        self.assertIsNotNone(
            match_transaction_reply(echoed_rtc_command, tx, allow_prefix_variant=True)
        )
