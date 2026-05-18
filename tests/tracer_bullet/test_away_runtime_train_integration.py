"""Branch-wide runtime train integration tests.

Verifies cross-subsystem compatibility:
- Evidence Vault -> Replay compatibility
- Replay -> Patch compatibility
- Patch -> Local Execution Kernel compatibility
- Replay/Patch/Execution -> Operator Daily Run compatibility
- Runtime Receipt Spine validates chain
- Runtime Recovery consumes failure bundles
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from replay_engine import ReplayEngine, ReplayCanonicalHash
from patch_runtime import PatchRuntime, PatchCanonicalHash
from local_execution_kernel import LocalExecutionKernel, ExecutionCanonicalHash
from operator_daily_run import OperatorDailyRun
from runtime_spine import RuntimeReceiptChain, RuntimeReceiptValidator
from runtime_recovery import FailureBundle, RecoveryPlan, produce_recovery_receipt

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64
VALID_SHA256_C = "c" * 64
VALID_SHA256_D = "d" * 64
VALID_SHA256_E = "e" * 64


class TestCrossSubsystemIntegration(unittest.TestCase):
    """Full cross-subsystem integration tests."""

    def test_evidence_to_replay_compatibility(self):
        """Evidence Vault receipts are compatible with Replay Engine."""
        engine = ReplayEngine()
        anchor = engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = engine.validate_version_tuple("v1", "code", "env")
        receipt = engine.produce_receipt(anchor, snapshot, vt, "strict")

        # Replay receipt has all required fields for spine validation
        self.assertTrue(receipt.canonical_hash)
        self.assertTrue(receipt.anchor_id)
        self.assertTrue(receipt.snapshot_id)
        self.assertEqual(receipt.module_version, "v1")

    def test_replay_to_patch_compatibility(self):
        """Replay Engine receipts are compatible with Patch Runtime."""
        engine = ReplayEngine()
        anchor = engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = engine.validate_version_tuple("v1", "code", "env")
        replay_receipt = engine.produce_receipt(anchor, snapshot, vt, "strict")

        patch = PatchRuntime()
        patch.configure_allowlist(["tools/file.py"])
        patch_request = patch.create_request(
            "patch-1", "tools/file.py", VALID_SHA256_B, VALID_SHA256_C,
        )
        patch_receipt = patch.approve(patch_request)

        self.assertEqual(replay_receipt.module_version, "v1")
        self.assertEqual(patch_receipt.module_version, "v1")
        self.assertTrue(replay_receipt.canonical_hash)
        self.assertTrue(patch_receipt.canonical_hash)

    def test_patch_to_execution_compatibility(self):
        """Patch Runtime receipts are compatible with Execution Kernel."""
        patch = PatchRuntime()
        patch.configure_allowlist(["tools/file.py"])
        patch_request = patch.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
        )
        patch_receipt = patch.approve(patch_request)

        kernel = LocalExecutionKernel()
        kernel.configure_allowlist(["python3"])
        exec_request = kernel.create_request("exec-1", "test", "python3 -m pytest")
        exec_receipt = kernel.approve(exec_request)

        self.assertEqual(patch_receipt.module_version, "v1")
        self.assertEqual(exec_receipt.module_version, "v1")

    def test_all_to_operator_compatibility(self):
        """Replay/Patch/Execution receipts bind into Operator Daily Run."""
        engine = ReplayEngine()
        anchor = engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = engine.validate_version_tuple("v1", "code", "env")
        replay_receipt = engine.produce_receipt(anchor, snapshot, vt, "strict")

        patch = PatchRuntime()
        patch.configure_allowlist(["tools/file.py"])
        patch_request = patch.create_request(
            "patch-1", "tools/file.py", VALID_SHA256_B, VALID_SHA256_C,
        )
        patch_receipt = patch.approve(patch_request)

        kernel = LocalExecutionKernel()
        kernel.configure_allowlist(["python3"])
        exec_request = kernel.create_request("exec-1", "test", "python3 -m pytest")
        exec_receipt = kernel.approve(exec_request)

        operator = OperatorDailyRun()
        op_request = operator.create_request(
            "run-1", "op-1",
            VALID_SHA256_D,
            replay_receipt.canonical_hash,
            "Review evidence and approve patches",
            "review-1", "approval-1",
            patch_receipt_hashes=[patch_receipt.canonical_hash],
            execution_receipt_hashes=[exec_receipt.canonical_hash],
        )
        op_receipt = operator.approve(op_request)
        self.assertEqual(op_receipt.status, "approved")
        self.assertTrue(op_receipt.no_production_action)

    def test_spine_validates_full_chain(self):
        """Runtime Receipt Spine validates the full chain."""
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        self.assertTrue(chain.validate()["chain_valid"])

    def test_spine_rejects_incomplete_chain(self):
        """Runtime Receipt Spine rejects incomplete chains."""
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        # Missing patch, execution, operator
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 3)

    def test_recovery_consumes_failure_bundles(self):
        """Runtime Recovery consumes failure bundles from any subsystem."""
        # Failure from replay
        bundle = FailureBundle.create(
            "replay_engine",
            ["REPLAY_EVIDENCE_CORRUPTED"],
            ["ev-1", "ev-2"],
        )
        plan = RecoveryPlan.create(
            bundle.bundle_id,
            ["restore evidence", "replay evidence"],
        )
        receipt = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        self.assertEqual(receipt.status, "ready")

        # Failure from patch
        bundle2 = FailureBundle.create(
            "patch_runtime",
            ["PATCH_ALLOWLIST_FAILED"],
            ["ev-3"],
        )
        plan2 = RecoveryPlan.create(
            bundle2.bundle_id,
            ["fix allowlist", "re-run validation"],
        )
        receipt2 = produce_recovery_receipt(bundle2.bundle_id, plan2.plan_id, "ready")
        self.assertEqual(receipt2.status, "ready")


class TestSpineValidatorIntegration(unittest.TestCase):
    """Runtime Receipt Validator cross-subsystem tests."""

    def test_full_spine_validation(self):
        result = RuntimeReceiptValidator.validate_full_spine(
            {"artifact_id": "ev-1", "content_hash": VALID_SHA256, "hash_algorithm": "sha256"},
            {"receipt_id": "rp-1", "anchor_id": "a-1", "canonical_hash": VALID_SHA256_B},
            {"receipt_id": "pt-1", "request_id": "req-1", "canonical_hash": VALID_SHA256_C},
            {"receipt_id": "ex-1", "execution_id": "exec-1", "canonical_hash": VALID_SHA256_D},
            {"receipt_id": "op-1", "run_id": "run-1", "canonical_hash": VALID_SHA256_E},
        )
        self.assertTrue(result["spine_valid"])


class TestAllReceiptsDeterministic(unittest.TestCase):
    """Verify all receipt types are deterministic."""

    def test_replay_receipt_deterministic(self):
        engine1 = ReplayEngine()
        engine2 = ReplayEngine()
        for eng in (engine1, engine2):
            anchor = eng.create_anchor(VALID_SHA256, "v1", "code", "env")
            snapshot = eng.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
            vt = eng.validate_version_tuple("v1", "code", "env")
            receipt = eng.produce_receipt(anchor, snapshot, vt, "strict")
            if eng is engine1:
                r1 = receipt
            else:
                r2 = receipt
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_patch_receipt_deterministic(self):
        p1 = PatchRuntime()
        p1.configure_allowlist(["tools/file.py"])
        req1 = p1.create_request("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        r1 = p1.approve(req1)

        p2 = PatchRuntime()
        p2.configure_allowlist(["tools/file.py"])
        req2 = p2.create_request("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        r2 = p2.approve(req2)

        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_execution_receipt_deterministic(self):
        k1 = LocalExecutionKernel()
        k1.configure_allowlist(["python3"])
        req1 = k1.create_request("exec-1", "test", "python3 -m pytest")
        r1 = k1.approve(req1)

        k2 = LocalExecutionKernel()
        k2.configure_allowlist(["python3"])
        req2 = k2.create_request("exec-1", "test", "python3 -m pytest")
        r2 = k2.approve(req2)

        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_operator_receipt_deterministic(self):
        o1 = OperatorDailyRun()
        req1 = o1.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review evidence", "review-1", "approval-1",
        )
        r1 = o1.approve(req1)

        o2 = OperatorDailyRun()
        req2 = o2.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review evidence", "review-1", "approval-1",
        )
        r2 = o2.approve(req2)

        self.assertEqual(r1.receipt_id, r2.receipt_id)


class TestNoRuntimeClaims(unittest.TestCase):
    """Verify no runtime claims about provider live execution or trading."""

    def test_no_provider_live_claim(self):
        """No runtime module claims provider live execution capability."""
        runtime_modules = [
            "tools/replay_engine",
            "tools/patch_runtime",
            "tools/local_execution_kernel",
            "tools/operator_daily_run",
            "tools/runtime_spine",
            "tools/runtime_recovery",
        ]
        for mod_path in runtime_modules:
            for py_file in (ROOT / mod_path).glob("*.py"):
                with open(py_file) as f:
                    lines = f.readlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("#"):
                        continue
                    if "forbidden" in stripped.lower() or "FORBIDDEN" in stripped:
                        continue
                    if "no live provider" in stripped.lower():
                        continue
                    # Check for claims of capability
                    lower = stripped.lower()
                    if "provider execution" in lower and "no" not in lower:
                        self.fail(f"{py_file.name}: claims provider execution")
                    if "live provider execution" in lower:
                        self.fail(f"{py_file.name}: claims live provider execution")

    def test_no_trading_claim(self):
        """No runtime module claims trading execution capability."""
        runtime_modules = [
            "tools/replay_engine", "tools/patch_runtime",
            "tools/local_execution_kernel", "tools/operator_daily_run",
            "tools/runtime_spine", "tools/runtime_recovery",
        ]
        for mod_path in runtime_modules:
            for py_file in (ROOT / mod_path).glob("*.py"):
                with open(py_file) as f:
                    lines = f.readlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("#"):
                        continue
                    if "forbidden" in stripped.lower() or "FORBIDDEN" in stripped:
                        continue
                    if "no trading" in stripped.lower():
                        continue
                    if "trading execution" in stripped.lower():
                        self.fail(f"{py_file.name}: claims trading execution")

    def test_no_network_imports_anywhere(self):
        """All runtime modules are free of network imports."""
        runtime_modules = [
            "tools/replay_engine", "tools/patch_runtime",
            "tools/local_execution_kernel", "tools/operator_daily_run",
            "tools/runtime_spine", "tools/runtime_recovery",
        ]
        for mod_path in runtime_modules:
            for py_file in (ROOT / mod_path).glob("*.py"):
                with open(py_file) as f:
                    src = f.read()
                self.assertNotIn("import subprocess", src, f"{py_file.name}")
                self.assertNotIn("import socket", src, f"{py_file.name}")
                self.assertNotIn("import requests", src, f"{py_file.name}")
                self.assertNotIn("import anthropic", src, f"{py_file.name}")
                self.assertNotIn("import openai", src, f"{py_file.name}")

    def test_no_env_reads_anywhere(self):
        """All runtime modules are free of env reads."""
        runtime_modules = [
            "tools/replay_engine", "tools/patch_runtime",
            "tools/local_execution_kernel", "tools/operator_daily_run",
            "tools/runtime_spine", "tools/runtime_recovery",
        ]
        for mod_path in runtime_modules:
            for py_file in (ROOT / mod_path).glob("*.py"):
                with open(py_file) as f:
                    src = f.read()
                self.assertNotIn("dotenv", src, f"{py_file.name}")
                self.assertNotIn("os.environ", src, f"{py_file.name}")
                self.assertNotIn("os.getenv", src, f"{py_file.name}")


if __name__ == "__main__":
    unittest.main()
