"""Runtime recovery failure bundle tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from runtime_recovery import (  # type: ignore[import-not-found]
    FailureBundle,
    RecoveryPlan,
    RecoveryReceipt,
    produce_recovery_receipt,
    RuntimeRecoveryCanonicalHash,
)


class TestFailureBundle(unittest.TestCase):
    """Failure bundle tests."""

    def test_create_valid_bundle(self):
        bundle = FailureBundle.create("replay_engine", ["REPLAY_GATE_FAILED"], ["ev-1", "ev-2"])
        self.assertTrue(bundle.is_valid)
        self.assertTrue(bundle.bundle_id)
        self.assertTrue(bundle.canonical_hash)
        self.assertTrue(bundle.failure_hash)
        self.assertEqual(bundle.failed_module, "replay_engine")

    def test_reject_empty_module(self):
        with self.assertRaises(ValueError):
            FailureBundle.create("", ["CODE"], ["ev-1"])

    def test_reject_empty_failure_codes(self):
        with self.assertRaises(ValueError):
            FailureBundle.create("module", [], ["ev-1"])

    def test_reject_empty_evidence(self):
        with self.assertRaises(ValueError):
            FailureBundle.create("module", ["CODE"], [])

    def test_reject_invalid_evidence_id(self):
        with self.assertRaises(ValueError):
            FailureBundle.create("module", ["CODE"], ["ev-1", ""])

    def test_bundle_deterministic(self):
        b1 = FailureBundle.create("module", ["CODE_A", "CODE_B"], ["ev-2", "ev-1"])
        b2 = FailureBundle.create("module", ["CODE_B", "CODE_A"], ["ev-1", "ev-2"])
        self.assertEqual(b1.bundle_id, b2.bundle_id)
        self.assertEqual(b1.canonical_hash, b2.canonical_hash)

    def test_bundle_no_raw_payload(self):
        bundle = FailureBundle.create("module", ["CODE"], ["ev-1"])
        d = bundle.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestRecoveryPlan(unittest.TestCase):
    """Recovery plan tests."""

    def test_create_valid_plan(self):
        plan = RecoveryPlan.create("bundle-1", ["restore snapshot", "replay evidence"])
        self.assertTrue(plan.is_valid)
        self.assertTrue(plan.plan_id)
        self.assertTrue(plan.rollback_compatible)
        self.assertFalse(plan.is_destructive)

    def test_reject_empty_bundle_id(self):
        with self.assertRaises(ValueError):
            RecoveryPlan.create("", ["step"])

    def test_reject_empty_steps(self):
        with self.assertRaises(ValueError):
            RecoveryPlan.create("bundle-1", [])

    def test_reject_destructive_recovery(self):
        with self.assertRaises(ValueError):
            RecoveryPlan.create("bundle-1", ["production_mutation step"])

    def test_reject_network_recovery(self):
        with self.assertRaises(ValueError):
            RecoveryPlan.create("bundle-1", ["network_call to external"])

    def test_reject_main_mutation(self):
        with self.assertRaises(ValueError):
            RecoveryPlan.create("bundle-1", ["main_mutation on git"])

    def test_plan_deterministic(self):
        p1 = RecoveryPlan.create("bundle-1", ["step a", "step b"])
        p2 = RecoveryPlan.create("bundle-1", ["step a", "step b"])
        self.assertEqual(p1.plan_id, p2.plan_id)

    def test_plan_no_raw_payload(self):
        plan = RecoveryPlan.create("bundle-1", ["restore snapshot"])
        d = plan.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestRecoveryReceipt(unittest.TestCase):
    """Recovery receipt tests."""

    def test_produce_receipt(self):
        receipt = produce_recovery_receipt("bundle-1", "plan-1", "ready")
        self.assertEqual(receipt.status, "ready")
        self.assertTrue(receipt.rollback_compatible)
        self.assertFalse(receipt.is_destructive)
        self.assertTrue(receipt.no_recovery_execution)

    def test_reject_invalid_status(self):
        with self.assertRaises(ValueError):
            produce_recovery_receipt("bundle-1", "plan-1", "invalid")

    def test_reject_empty_bundle_id(self):
        with self.assertRaises(ValueError):
            produce_recovery_receipt("", "plan-1", "ready")

    def test_reject_empty_plan_id(self):
        with self.assertRaises(ValueError):
            produce_recovery_receipt("bundle-1", "", "ready")

    def test_receipt_deterministic(self):
        r1 = produce_recovery_receipt("bundle-1", "plan-1", "ready")
        r2 = produce_recovery_receipt("bundle-1", "plan-1", "ready")
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_no_raw_payload(self):
        receipt = produce_recovery_receipt("bundle-1", "plan-1", "ready")
        d = receipt.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestRuntimeRecoveryCanonicalHash(unittest.TestCase):
    """Recovery canonical hash tests."""

    def test_canonical_hash(self):
        h = RuntimeRecoveryCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(len(h), 64)

    def test_deterministic(self):
        h1 = RuntimeRecoveryCanonicalHash.canonical_hash("a", "b")
        h2 = RuntimeRecoveryCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(h1, h2)


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in recovery modules."""

    def test_no_forbidden_imports(self):
        rec_dir = ROOT / "tools" / "runtime_recovery"
        for py_file in rec_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name}")
            self.assertNotIn("import socket", src, f"{py_file.name}")
            self.assertNotIn("import requests", src, f"{py_file.name}")
            self.assertNotIn("from urllib", src, f"{py_file.name}")

    def test_no_env_reads(self):
        rec_dir = ROOT / "tools" / "runtime_recovery"
        for py_file in rec_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name}")
            self.assertNotIn("os.environ", src, f"{py_file.name}")


if __name__ == "__main__":
    unittest.main()
