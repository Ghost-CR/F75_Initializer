from __future__ import annotations

from unittest import TestCase

from aula_hacky.capture_analysis import (
    annotate_payload,
    diff_payloads,
    normalize_payload_hex,
    parse_tshark_rows,
    strip_report_id,
)
from aula_hacky.protocol_core import CABLE_SESSION_INIT_IN, SESSION_INIT_IN


class CaptureAnalysisTests(TestCase):
    def test_normalize_payload_hex_accepts_colons_and_spaces(self) -> None:
        self.assertEqual(normalize_payload_hex("02:00 00"), b"\x02\x00\x00")

    def test_strip_report_id_for_known_prefixed_report_sizes(self) -> None:
        self.assertEqual(strip_report_id(b"\x00" + SESSION_INIT_IN), SESSION_INIT_IN)
        self.assertEqual(strip_report_id(b"\x00" + CABLE_SESSION_INIT_IN), CABLE_SESSION_INIT_IN)

    def test_annotates_known_dongle_and_cable_reports(self) -> None:
        self.assertEqual(annotate_payload(SESSION_INIT_IN), "dongle-session-init")
        self.assertEqual(annotate_payload(CABLE_SESSION_INIT_IN), "cable-session-init")

    def test_parse_tshark_rows(self) -> None:
        rows = parse_tshark_rows(
            [
                "12\t1770000000.0\t1.0\t1.7\t0x01\t0x85\t\t02:00:00\n",
                "bad\trow\n",
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].frame, 12)
        self.assertEqual(rows[0].payload, b"\x02\x00\x00")

    def test_diff_payloads_reports_offsets(self) -> None:
        self.assertEqual(
            diff_payloads("010203", "010304"),
            [
                {"offset": 1, "left": "02", "right": "03"},
                {"offset": 2, "left": "03", "right": "04"},
            ],
        )
