from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from aula_hacky.macos_cable_rtc_sync import match_cable_transaction_reply, normalize_feature_report
from aula_hacky.protocol_core import CABLE_PACKET_SIZE, CABLE_SESSION_INIT_IN, build_cable_transaction_sequence


class MacOSCableRTCSyncTests(TestCase):
    def test_normalizes_report_id_prefixed_feature_report(self) -> None:
        raw = b"\x00" + CABLE_SESSION_INIT_IN

        self.assertEqual(normalize_feature_report(raw), CABLE_SESSION_INIT_IN)

    def test_leaves_raw_feature_report_unchanged(self) -> None:
        self.assertEqual(normalize_feature_report(CABLE_SESSION_INIT_IN), CABLE_SESSION_INIT_IN)

    def test_matches_exact_cable_feature_reply(self) -> None:
        tx = build_cable_transaction_sequence(datetime(2026, 3, 20, 11, 10, 18))[0]
        raw = b"\x00" + CABLE_SESSION_INIT_IN

        match = match_cable_transaction_reply(raw, tx)

        self.assertIsNotNone(match)
        self.assertEqual(match.packet, CABLE_SESSION_INIT_IN)
        self.assertEqual(match.kind, "exact")

    def test_rejects_wrong_length_feature_reply(self) -> None:
        tx = build_cable_transaction_sequence(datetime(2026, 3, 20, 11, 10, 18))[0]

        self.assertIsNone(match_cable_transaction_reply(b"\x00" * (CABLE_PACKET_SIZE - 1), tx))
