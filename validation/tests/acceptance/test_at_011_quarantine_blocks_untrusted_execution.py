"""
AT-011: Quarantine blocks untrusted execution.

Constitutional anchors:
- v11 Section 22.4 Validation Quarantine Enforcement Contract
- v11 Section 24.1 AT-011
- v11 Section 24.2 INV-008 (validation cannot pollute host truth)
- Foundation Section 5.1 test #3 (validation quarantine enforcement)

What this test proves:
  A validation run that does not exit cleanly must be classified as
  invalid, triggering quarantine_breach_suspect taint propagation. The
  receipt produced must reflect this.
"""

from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.quarantine.runner_adapter import (
    QuarantineRun,
    QuarantineState,
    classify_receipt_trust,
)
from kernel.contracts.quarantine_rules import (
    QuarantineAdmissibilityError,
    QuarantineProposal,
    assert_proposal_admissible,
    classify_admissibility,
)


class TestQuarantineBlocksUntrusted(unittest.TestCase):
    """AT-011 / INV-008: quarantine blocks untrusted execution."""

    def test_failed_exit_produces_quarantined_receipt(self) -> None:
        """A run that exits with EXITED_FAILED -> classify as quarantined."""
        run = QuarantineRun(
            quarantine_run_id="qr-fail-test",
            state=QuarantineState.EXITED_FAILED,
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at="2025-01-01T00:01:00+00:00",
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=False,
            env_scrub_violations=[],
            network_attempts=[],
        )
        trust = classify_receipt_trust(run)
        self.assertEqual(trust.class_name, "invalid")
        self.assertIn("quarantine_breach_suspect", trust.taint_to_propagate)

        result = classify_admissibility(run=run, proposal_passed_static=True)
        self.assertEqual(result.receipt_result, "quarantined")

    def test_network_attempt_produces_quarantined_receipt(self) -> None:
        """Network attempts during quarantine -> downgraded trust."""
        run = QuarantineRun(
            quarantine_run_id="qr-network-test",
            state=QuarantineState.EXITED_CLEAN,
            entered_at="2025-01-01T00:00:00+00:00",
            exited_at="2025-01-01T00:01:00+00:00",
            host_pollution_suspected=False,
            workspace_preserved_for_forensics=False,
            env_scrub_violations=[],
            network_attempts=["dns:example.com"],
        )
        trust = classify_receipt_trust(run)
        self.assertEqual(trust.class_name, "downgraded")
        self.assertIn("policy_degraded", trust.taint_to_propagate)

        result = classify_admissibility(run=run, proposal_passed_static=True)
        self.assertEqual(result.receipt_result, "quarantined")

    def test_secret_bearing_proposal_rejected(self) -> None:
        """A proposal that bears secrets must be rejected outright."""
        proposal = QuarantineProposal(
            validator_identity="test-validator",
            validator_version="1.0",
            requested_policy_keys=("network_off", "host_read_only"),
            secret_bearing=True,
        )
        with self.assertRaises(QuarantineAdmissibilityError):
            assert_proposal_admissible(proposal)


if __name__ == "__main__":
    unittest.main()
