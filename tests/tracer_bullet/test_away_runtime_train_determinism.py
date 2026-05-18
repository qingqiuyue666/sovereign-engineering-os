"""Branch-wide runtime train determinism tests.

Verifies all receipt types across all subsystems are deterministic:
identical inputs always produce identical receipt IDs and canonical hashes.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64
VALID_SHA256_C = "c" * 64


class TestAllReceiptsDeterministic(unittest.TestCase):
    """Every receipt type must be deterministic."""

    def test_replay_anchor_deterministic(self):
        from replay_engine import ReplayAnchor
        a1 = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        a2 = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        self.assertEqual(a1.anchor_id, a2.anchor_id)
        self.assertEqual(a1.canonical_hash, a2.canonical_hash)

    def test_replay_snapshot_deterministic(self):
        from replay_engine import ReplaySnapshot
        s1 = ReplaySnapshot.create(VALID_SHA256, 10, "ev")
        s2 = ReplaySnapshot.create(VALID_SHA256, 10, "ev")
        self.assertEqual(s1.snapshot_id, s2.snapshot_id)

    def test_replay_version_tuple_deterministic(self):
        from replay_engine import ReplayVersionTuple
        v1 = ReplayVersionTuple.create("v1", "code", "env")
        v2 = ReplayVersionTuple.create("v1", "code", "env")
        self.assertEqual(v1.tuple_id, v2.tuple_id)

    def test_replay_receipt_deterministic(self):
        from replay_engine.replay_receipt import produce_replay_receipt
        r1 = produce_replay_receipt("a", "s", "v", "ready", "strict", True)
        r2 = produce_replay_receipt("a", "s", "v", "ready", "strict", True)
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_replay_readiness_deterministic(self):
        from replay_engine.replay_receipt import produce_readiness_receipt
        r1 = produce_readiness_receipt("a", "s", "v", {"g1": True, "g2": True})
        r2 = produce_readiness_receipt("a", "s", "v", {"g2": True, "g1": True})
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_replay_failure_deterministic(self):
        from replay_engine.replay_receipt import produce_failure_receipt
        r1 = produce_failure_receipt("a", "reason", "CODE")
        r2 = produce_failure_receipt("a", "reason", "CODE")
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_replay_evidence_binding_deterministic(self):
        from replay_engine import ReplayEvidenceBinding
        b1 = ReplayEvidenceBinding.create("a", ["ev-2", "ev-1"])
        b2 = ReplayEvidenceBinding.create("a", ["ev-1", "ev-2"])
        self.assertEqual(b1.binding_id, b2.binding_id)
        self.assertEqual(b1.canonical_hash, b2.canonical_hash)

    def test_patch_request_deterministic(self):
        from patch_runtime import PatchRequest
        r1 = PatchRequest.create("p1", "tools/f.py", VALID_SHA256, VALID_SHA256_B)
        r2 = PatchRequest.create("p1", "tools/f.py", VALID_SHA256, VALID_SHA256_B)
        self.assertEqual(r1.request_id, r2.request_id)

    def test_patch_receipt_deterministic(self):
        from patch_runtime import PatchRequest, produce_patch_receipt
        req = PatchRequest.create("p1", "tools/f.py", VALID_SHA256, VALID_SHA256_B)
        preflight = {"preflight_passed": True, "target_in_allowlist": True}
        r1 = produce_patch_receipt(req, preflight)
        r2 = produce_patch_receipt(req, preflight)
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_patch_rollback_deterministic(self):
        from patch_runtime import PatchRollback
        r1 = PatchRollback.create("p1", VALID_SHA256, "revert")
        r2 = PatchRollback.create("p1", VALID_SHA256, "revert")
        self.assertEqual(r1.rollback_id, r2.rollback_id)

    def test_execution_request_deterministic(self):
        from local_execution_kernel import ExecutionRequest
        r1 = ExecutionRequest.create("e1", "test", "python3 -m pytest")
        r2 = ExecutionRequest.create("e1", "test", "python3 -m pytest")
        self.assertEqual(r1.request_id, r2.request_id)

    def test_execution_receipt_deterministic(self):
        from local_execution_kernel import produce_execution_receipt
        preflight = {"preflight_passed": True, "allowlist_valid": True}
        r1 = produce_execution_receipt("e1", "approved", "test", preflight)
        r2 = produce_execution_receipt("e1", "approved", "test", preflight)
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_operator_request_deterministic(self):
        from operator_daily_run import DailyRunRequest
        r1 = DailyRunRequest.create(
            "r1", "o1", VALID_SHA256, VALID_SHA256_B,
            "Review", "rev-1", "app-1",
        )
        r2 = DailyRunRequest.create(
            "r1", "o1", VALID_SHA256, VALID_SHA256_B,
            "Review", "rev-1", "app-1",
        )
        self.assertEqual(r1.request_id, r2.request_id)

    def test_operator_receipt_deterministic(self):
        from operator_daily_run import produce_operator_run_receipt
        r1 = produce_operator_run_receipt("r1", "o1", "approved", True, True, True, True)
        r2 = produce_operator_run_receipt("r1", "o1", "approved", True, True, True, True)
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_recovery_bundle_deterministic(self):
        from runtime_recovery import FailureBundle
        b1 = FailureBundle.create("mod", ["C1", "C2"], ["ev-2", "ev-1"])
        b2 = FailureBundle.create("mod", ["C2", "C1"], ["ev-1", "ev-2"])
        self.assertEqual(b1.bundle_id, b2.bundle_id)

    def test_recovery_plan_deterministic(self):
        from runtime_recovery import RecoveryPlan
        p1 = RecoveryPlan.create("b1", ["step a", "step b"])
        p2 = RecoveryPlan.create("b1", ["step a", "step b"])
        self.assertEqual(p1.plan_id, p2.plan_id)

    def test_recovery_receipt_deterministic(self):
        from runtime_recovery import produce_recovery_receipt
        r1 = produce_recovery_receipt("b1", "p1", "ready")
        r2 = produce_recovery_receipt("b1", "p1", "ready")
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_spine_chain_hash_deterministic(self):
        from runtime_spine import RuntimeReceiptChain
        c1 = RuntimeReceiptChain()
        c2 = RuntimeReceiptChain()
        for c in (c1, c2):
            c.set_evidence_vault_receipt(VALID_SHA256)
            c.set_replay_receipt(VALID_SHA256_B)
            c.set_patch_receipt(VALID_SHA256_C)
            c.set_execution_receipt("d" * 64)
            c.set_operator_run_receipt("e" * 64)
        self.assertEqual(c1.chain_hash(), c2.chain_hash())

    def test_canonical_hashes_deterministic_across_modules(self):
        """All canonical hash classes produce deterministic results."""
        from replay_engine import ReplayCanonicalHash
        from patch_runtime import PatchCanonicalHash
        from local_execution_kernel import ExecutionCanonicalHash
        from operator_daily_run import OperatorRunCanonicalHash
        from runtime_spine import RuntimeSpineCanonicalHash
        from runtime_recovery import RuntimeRecoveryCanonicalHash

        for cls in [
            ReplayCanonicalHash, PatchCanonicalHash, ExecutionCanonicalHash,
            OperatorRunCanonicalHash, RuntimeSpineCanonicalHash, RuntimeRecoveryCanonicalHash,
        ]:
            h1 = cls.canonical_hash("x", "y", "z")
            h2 = cls.canonical_hash("x", "y", "z")
            self.assertEqual(h1, h2, f"{cls.__name__} not deterministic")

    def test_no_wall_clock_in_any_hash(self):
        """No wall-clock time in any hash generation."""
        import hashlib
        # All our hash functions use sha256 or blake2b with deterministic inputs
        # Verify that datetime is not imported in canonical hash modules
        hash_modules = [
            "tools/replay_engine/replay_canonical_hash.py",
            "tools/patch_runtime/patch_canonical_hash.py",
            "tools/local_execution_kernel/execution_canonical_hash.py",
            "tools/operator_daily_run/operator_run_canonical_hash.py",
            "tools/runtime_spine/runtime_spine_canonical_hash.py",
            "tools/runtime_recovery/runtime_recovery_canonical_hash.py",
        ]
        for mod in hash_modules:
            with open(ROOT / mod) as f:
                src = f.read()
            self.assertNotIn("datetime", src, f"{mod} imports datetime")
            self.assertNotIn("time.time", src, f"{mod} uses time.time")
            self.assertNotIn("time.monotonic", src, f"{mod} uses time.monotonic")


if __name__ == "__main__":
    unittest.main()
