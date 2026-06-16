from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_durationus_semantics import scan_text


class DurationUsSemanticsScannerTests(unittest.TestCase):
    def test_blocks_durationus_to_d_alias(self) -> None:
        findings = scan_text(Path("scripts/example.py"), 'df["D"] = df["DurationUS"]\n')

        self.assertTrue(any("D_column_from_DurationUS" in finding for finding in findings))
        self.assertTrue(any("direct DurationUS use requires" in finding for finding in findings))

    def test_allows_technical_durationus_with_marker(self) -> None:
        findings = scan_text(
            Path("scripts/example.py"),
            'duration = df["DurationUS"]  # durationus-ok: integrity read\n',
        )

        self.assertEqual(findings, [])

    def test_blocks_raw_sequence_duration_reconstruction_without_marker(self) -> None:
        findings = scan_text(
            Path("scripts/example.py"),
            'cols = ["StartDateTime", "EndDateTime"]\n'
            "D = (to_ns(end_values) - to_ns(start_values)) // 1000\n",
        )

        self.assertTrue(any("sequence-duration-ok" in finding for finding in findings))

    def test_allows_raw_sequence_duration_reconstruction_with_marker(self) -> None:
        findings = scan_text(
            Path("scripts/example.py"),
            "# sequence-duration-ok: composed-object audit fixture\n"
            'cols = ["StartDateTime", "EndDateTime"]\n'
            "D = (to_ns(end_values) - to_ns(start_values)) // 1000\n",
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
