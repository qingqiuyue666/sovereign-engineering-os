"""
AT-010: Quarantine cannot pollute host truth.

Constitutional anchors:
- v11 Section 22.4 Validation Quarantine Enforcement Contract
- v11 Section 24.1 AT-010
- v11 Section 24.2 INV-008 (validation cannot pollute host truth)
- Foundation Section 3 item 13 (macOS quarantine guarantee classification)

What this test proves:
  If host cache mutation is detected during a validation quarantine run,
  the receipt must be invalidated and taint must propagate. The
  quarantine runner adapter's classify_receipt_trust function must
  downgrade trust on any pollution suspicion.
"""

from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.quarantine.runner_adapter import (
    QuarantineRun,
    QuarantineState,
    ReceiptTrust,
    classify_receipt_trust,
    declared_posture,
    QUARANTINE_GUARANTEE_LEVEL,
    QuarantineGuaranteeLevel,
)


class TestQuarantineNoPollution(unittest.TestCase):
    """AT-010 / INV-008: quarantine must not pollute host truth."""

    def test_host_pollution_suspected_invalidates_receipt(self) -> None:
        """If host_pollution_suspected=True, receipt trust is INVALID."""
        run = QuarantineRun(
            quarantine_run_id="qr-pollution-test",
            state=QuarantineState.EXITED_TAINTED,
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at="2025-01-01T00:01:00+00:00",
            host_pollution_suspected=True,
            workspace_preserved_for_forensics=True,
            env_scrub_violations=[],
            network_attempts=[],
        )
        trust = classify_receipt_trust(run)
        self.assertEqual(trust.class_name, "invalid")
        self.assertIn("quarantine_breach_suspect", trust.taint_to_propagate)

    def test_clean_exit_trusted(self) -> None:
        """Clean exit with no violations -> receipt trust is TRUSTED."""
        run = QuarantineRun(
            quarantine_run_id="qr-clean-test",
            state=QuarantineState.EXITED_CLEAN,
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at="2025-01-01T00:01:00+00:00",
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=False,
            env_scrub_violations=[],
            network_attempts=[],
        )
        trust = classify_receipt_trust(run)
        self.assertEqual(trust.class_name, "trusted")
        self.assertEqual(len(trust.taint_to_propagate), 0)

    def test_env_scrub_violation_downgrades(self) -> None:
        """Env-scrub violations downgrade trust and propagate taint."""
        run = QuarantineRun(
            quarantine_run_id="qr-env-scrub-test",
            state=QuarantineState.EXITED_CLEAN,
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at="2025-01-01T00:01:00+00:00",
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=False,
            env_scrub_violations=["HOME=/real/home"],
            network_attempts=[],
        )
        trust = classify_receipt_trust(run)
        self.assertEqual(trust.class_name, "downgraded")
        self.assertIn("policy_degraded", trust.taint_to_propagate)

    def test_declared_posture_is_bounded_quarantine(self) -> None:
        """Phase-1 declared posture must be bounded_quarantine."""
        self.assertEqual(
            QUARANTINE_GUARANTEE_LEVEL,
            QuarantineGuaranteeLevel.BOUNDED_QUARANTINE,
        )
        posture = declared_posture()
        self.assertEqual(posture["guarantee_level"], "bounded_quarantine")
        self.assertTrue(posture["policy"]["network_off"])
        self.assertTrue(posture["policy"]["host_read_only"])


if __name__ == "__main__":
    unittest.main()
