"""
AT-008: Approval barrier rejects on root drift.

Constitutional anchors:
- v11 Section 22.3 Atomic Approval Barrier Contract
- v11 Section 24.1 AT-008
- v11 Section 24.2 INV-006 (no approval time-travel across drift)
- v11 Section 24.2 INV-007 (concurrent serialization one-winner rule)
- Foundation Section 5.1 test #2 (barrier rejection test, root drift)

What this test proves:
  Approve at root R1, then simulate drift to R2 before seal.
  The seal-time barrier re-evaluation must fail closed and the
  approval must not time-travel into execution authority.
"""

from __future__ import annotations

import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.lifecycle.stage_types import Stage
from kernel.services.approval_service import ApprovalBarrierFailed
from kernel.contracts.barrier_rules import (
    BarrierInputs,
    BarrierVerdict,
    REASON_ROOT_DRIFT,
    evaluate_barrier,
)


class TestApprovalRootDrift(unittest.TestCase):
    """AT-008 / INV-006: approval barrier rejects on root drift."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_root_drift_fails_barrier(self) -> None:
        """Approve at root R1, observe drift to R2 -> barrier must fail."""
        now = datetime.now(timezone.utc)
        inputs = BarrierInputs(
            approval_id="ap-test-drift",
            approval_state="approved",
            approval_policy_version="phase1_approval_policy_v1",
            originating_root_revision_id="rev-R1",
            reviewed_patch_hash="hash-patch-1",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=["vr-1"],
            approval_expires_at=(now + timedelta(hours=24)).isoformat(),
            # Live truth has drifted to R2.
            current_root_revision_id="rev-R2",
            current_context_artifact_id="ctx-1",
            current_patch_hash="hash-patch-1",
            current_policy_version="phase1_approval_policy_v1",
            receipts_live={"vr-1": {"result": "pass", "invalidated_at": None}},
            task_superseded=False,
            now_iso=now.isoformat(),
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, REASON_ROOT_DRIFT)

    def test_context_drift_fails_barrier(self) -> None:
        """Approve with context C1, observe drift to C2 -> barrier must fail."""
        now = datetime.now(timezone.utc)
        inputs = BarrierInputs(
            approval_id="ap-test-ctx-drift",
            approval_state="approved",
            approval_policy_version="phase1_approval_policy_v1",
            originating_root_revision_id="rev-R1",
            reviewed_patch_hash="hash-patch-1",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=["vr-1"],
            approval_expires_at=(now + timedelta(hours=24)).isoformat(),
            current_root_revision_id="rev-R1",
            # Context has drifted.
            current_context_artifact_id="ctx-2",
            current_patch_hash="hash-patch-1",
            current_policy_version="phase1_approval_policy_v1",
            receipts_live={"vr-1": {"result": "pass", "invalidated_at": None}},
            task_superseded=False,
            now_iso=now.isoformat(),
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, "context_drift")

    def test_expired_approval_fails_barrier(self) -> None:
        """An expired approval must not pass the barrier."""
        now = datetime.now(timezone.utc)
        inputs = BarrierInputs(
            approval_id="ap-test-expired",
            approval_state="approved",
            approval_policy_version="phase1_approval_policy_v1",
            originating_root_revision_id="rev-R1",
            reviewed_patch_hash="hash-patch-1",
            reviewed_context_artifact_id="ctx-1",
            required_receipt_ids=["vr-1"],
            # Already expired.
            approval_expires_at=(now - timedelta(hours=1)).isoformat(),
            current_root_revision_id="rev-R1",
            current_context_artifact_id="ctx-1",
            current_patch_hash="hash-patch-1",
            current_policy_version="phase1_approval_policy_v1",
            receipts_live={"vr-1": {"result": "pass", "invalidated_at": None}},
            task_superseded=False,
            now_iso=now.isoformat(),
        )
        verdict = evaluate_barrier(inputs)
        self.assertFalse(verdict.passes)
        self.assertEqual(verdict.reason_code, "approval_expired")

    def test_no_drift_passes_barrier(self) -> None:
        """With no drift, the barrier must pass (golden-path baseline)."""
        now = datetime.now(timezone.utc)
        inputs = BarrierInputs(
            approval_id="ap-test-ok",
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
        verdict = evaluate_barrier(inputs)
        self.assertTrue(verdict.passes)


if __name__ == "__main__":
    unittest.main()
