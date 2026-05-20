"""Runbook coverage tests for local Sovereign OS landing."""

from __future__ import annotations

import unittest
from pathlib import Path


class SovereignOsLocalLandingRunbookTests(unittest.TestCase):
    def test_runbook_contains_required_operator_sections_and_boundaries(self) -> None:
        path = Path("docs/operator/sovereign_os_local_landing_runbook_v1.md")
        text = path.read_text(encoding="utf-8")
        for phrase in (
            "Bootstrap Local OS Runtime",
            "Run SQLite ResourceWarning Check",
            "Run Desktop Headless Smoke",
            "Run Context-Pack Worker",
            "Run HFX_008 Dry-Run Landing Chain",
            "Inspect SQLite Job And Artifact State",
            "Close Resources",
            "Quarantine Failure",
            "Proceed Later To Real HFX_008 Proof",
            "Claim Boundary",
            "final_claim_allowed=false",
            "Do not claim final HFX_008 completion",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
