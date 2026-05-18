"""Runtime recovery receipt tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from runtime_recovery import (  # type: ignore[import-not-found]
    FailureBundle,
    RecoveryPlan,
    produce_recovery_receipt,
)


class TestRecoveryReceiptIntegration(unittest.TestCase):
    """End-to-end recovery receipt integration tests."""

    def test_full_recovery_flow(self):
        # Create failure bundle
        bundle = FailureBundle.create(
            "replay_engine",
            ["REPLAY_EVIDENCE_CORRUPTED"],
            ["ev-1", "ev-2"],
        )
        self.assertTrue(bundle.is_valid)

        # Create recovery plan
        plan = RecoveryPlan.create(
            bundle.bundle_id,
            ["restore evidence from backup", "replay evidence", "validate output"],
        )
        self.assertTrue(plan.is_valid)
        self.assertTrue(plan.rollback_compatible)
        self.assertFalse(plan.is_destructive)

        # Produce recovery receipt
        receipt = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        self.assertEqual(receipt.status, "ready")
        self.assertTrue(receipt.no_recovery_execution)
        self.assertTrue(receipt.rollback_compatible)

    def test_recovery_with_multiple_failures(self):
        bundle = FailureBundle.create(
            "patch_runtime",
            ["PATCH_VALIDATION_FAILED", "PATCH_ALLOWLIST_FAILED"],
            ["ev-1", "ev-2", "ev-3"],
        )
        self.assertEqual(len(bundle.failure_codes), 2)
        self.assertEqual(len(bundle.evidence_ids), 3)

        plan = RecoveryPlan.create(
            bundle.bundle_id,
            ["validate allowlist", "re-run validation", "check evidence integrity"],
        )
        receipt = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        self.assertEqual(receipt.status, "ready")

    def test_destructive_plan_rejected(self):
        bundle = FailureBundle.create("module", ["FAILURE"], ["ev-1"])
        with self.assertRaises(ValueError):
            RecoveryPlan.create(bundle.bundle_id, ["production_deploy fix"])

    def test_receipt_deterministic_across_runs(self):
        bundle = FailureBundle.create("module", ["CODE"], ["ev-1"])
        plan = RecoveryPlan.create(bundle.bundle_id, ["restore"])
        r1 = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        r2 = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        self.assertEqual(r1.receipt_id, r2.receipt_id)


if __name__ == "__main__":
    unittest.main()
