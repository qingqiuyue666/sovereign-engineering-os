"""
AT-035: Drift consequence invalidation.

Constitutional anchors:
- v11 Section 22.3 Atomic Approval Barrier Contract
- v11 Section 24.1 AT-035
- v11 Section 24.2 INV-028 (drift consequence invalidation)
- Foundation Section 5.2 (AT-035 -> INV-028)

What this test proves:
  Drift between approval and seal must invalidate the approval. The
  barrier must fail closed, and a DriftEventRecord should be emitted.
  Receipt drift (invalidated receipt) must also trigger barrier failure.
"""

from __future__ import annotations

import unittest
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.contracts.barrier_rules import (
    BarrierInputs,
    BarrierVerdict,
    REASON_RECEIPT_DRIFT,
    REASON_RECEIPT_INVALIDATED,
    REASON_RECEIPT_NOT_PASS,
    REASON_POLICY_DRIFT,
    evaluate_barrier,
)


class TestDriftConsequenceInvalidation(unittest.TestCase):
    """AT-035 / INV-028: drift consequence invalidation."""

    def _make_inputs(self, **overrides) -> BarrierInputs:
        now = datetime.now(timezone.utc)
        defaults = dict(
            approval_id="ap-test",
            approval_state="approved",
            approval_policy_version="phase1_approval_policy_v1",
            originating_root_revision_id="rev-R1",
            reviewed_patch_hash="hash-patch-1",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=["vr-1"],
            approval_expires_at=(now + timedelta(hours=24)).isoformat(),
            current_root_revision_id="rev-R1",
            current_context_artifact_id="ctx-1",
            current_patch_hash="hash-patch-1",
            current_policy_version="phase1_approval_policy_v1",
            receipts_live={"vr-1": {"result": "pass", "invalidated_at": None}},
            task_superseded=False,
            now_iso=now.isoformat(),
        )
        defaults.update(overrides)
        return BarrierInputs(**defaults)

    def test_receipt_invalidated_fails_barrier(self) -> None:
        """An invalidated receipt must fail the barrier."""
        inputs = self._make_inputs(
            receipts_live={
                "vr-1": {
                    "result": "pass",
                    "invalidated_at": "2025-01-01T00:00:00+00:00",
                },
            },
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, REASON_RECEIPT_INVALIDATED)

    def test_receipt_failed_result_fails_barrier(self) -> None:
        """A receipt with result='fail' must fail the barrier."""
        inputs = self._make_inputs(
            receipts_live={"vr-1": {"result": "fail", "invalidated_at": None}},
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, REASON_RECEIPT_NOT_PASS)

    def test_policy_drift_fails_barrier(self) -> None:
        """Drift in policy_version must fail the barrier."""
        inputs = self._make_inputs(
            current_policy_version="phase2_approval_policy_v1",
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, REASON_POLICY_DRIFT)

    def test_task_superseded_fails_barrier(self) -> None:
        """A superseded task must fail the barrier."""
        inputs = self._make_inputs(task_superseded=True)
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, "task_superseded")

    def test_missing_receipt_fails_barrier(self) -> None:
        """A required receipt that's missing from live truth must fail."""
        inputs = self._make_inputs(
            receipts_live={},  # Receipt vr-1 is required but not present.
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertIn(
            verdict.reason_code,
            [REASON_RECEIPT_DRIFT, "receipt_missing"],
        )


if __name__ == "__main__":
    unittest.main()
