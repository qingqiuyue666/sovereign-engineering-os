"""Branch-wide runtime train integration tests.

Verifies cross-subsystem compatibility:
- Evidence Vault -> Replay compatibility
- Replay -> Patch compatibility
- Patch -> Local Execution Kernel compatibility
- Replay/Patch/Execution -> Operator Daily Run compatibility
- Runtime Receipt Spine validates explicit chain linkage
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


def _make_replay_receipt():
    engine = ReplayEngine()
    anchor = engine.create_anchor(VALID_SHA256, "v1", "code", "env")
    snapshot = engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
    vt = engine.validate_version_tuple("v1", "code", "env")
    binding = engine.bind_evidence(anchor.anchor_id, ["ev-1"])
    return engine.produce_receipt(anchor, snapshot, vt, "strict", binding)


def _make_patch_receipt(replay_hash: str = ""):
    patch = PatchRuntime()
    patch.configure_allowlist(["tools/file.py"])
    patch_request = patch.create_request(
        "patch-1", "tools/file.py", VALID_SHA256_B, VALID_SHA256_C,
        replay_receipt_hash=replay_hash,
    )
    return patch.approve(patch_request)


def _make_execution_receipt(patch_hash: str = ""):
    kernel = LocalExecutionKernel()
    kernel.configure_allowlist(["python3"])
    exec_request = kernel.create_request("exec-1", "test", "python3 -m pytest")
    return kernel.approve(exec_request, patch_receipt_hash=patch_hash)


class TestCrossSubsystemIntegration(unittest.TestCase):
    """Full cross-subsystem integration tests."""

    def test_evidence_to_replay_compatibility(self):
        replay_receipt = _make_replay_receipt()
        evidence = {"artifact_id": "ev-1", "content_hash": VALID_SHA256, "hash_algorithm": "sha256"}
        result = RuntimeReceiptValidator.validate_evidence_to_replay(evidence, replay_receipt.to_dict())
        self.assertTrue(result["compatible"])
        self.assertTrue(replay_receipt.evidence_binding_hash)
        self.assertIn("ev-1", replay_receipt.evidence_artifact_ids)

    def test_replay_to_patch_compatibility(self):
        replay_receipt = _make_replay_receipt()
        patch_receipt = _make_patch_receipt(replay_receipt.canonical_hash)
        result = RuntimeReceiptValidator.validate_replay_to_patch(
            replay_receipt.to_dict(), patch_receipt.to_dict(),
        )
        self.assertTrue(result["compatible"])

    def test_patch_to_execution_compatibility(self):
        patch_receipt = _make_patch_receipt()
        exec_receipt = _make_execution_receipt(patch_receipt.canonical_hash)
        result = RuntimeReceiptValidator.validate_patch_to_execution(
            patch_receipt.to_dict(), exec_receipt.to_dict(),
        )
        self.assertTrue(result["compatible"])

    def test_all_to_operator_compatibility(self):
        replay_receipt = _make_replay_receipt()
        patch_receipt = _make_patch_receipt(replay_receipt.canonical_hash)
        exec_receipt = _make_execution_receipt(patch_receipt.canonical_hash)

        operator = OperatorDailyRun()
        op_request = operator.create_request(
            "run-1", "op-1",
            VALID_SHA256_D,
            replay_receipt.canonical_hash,
            "Review evidence and approve patches with local kernel validation",
            "review-1", "approval-1",
            patch_receipt_hashes=[patch_receipt.canonical_hash],
            execution_receipt_hashes=[exec_receipt.canonical_hash],
        )
        op_receipt = operator.approve(op_request)
        result = RuntimeReceiptValidator.validate_execution_to_operator(
            exec_receipt.to_dict(), op_receipt.to_dict(),
        )
        self.assertTrue(result["compatible"])
        self.assertEqual(op_receipt.status, "approved")

    def test_spine_validates_full_chain(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        self.assertTrue(chain.validate()["chain_valid"])

    def test_spine_rejects_incomplete_chain(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 3)

    def test_recovery_consumes_failure_bundles(self):
        bundle = FailureBundle.create(
            "replay_engine", ["REPLAY_EVIDENCE_CORRUPTED"], ["ev-1", "ev-2"],
        )
        plan = RecoveryPlan.create(bundle.bundle_id, ["restore evidence", "replay evidence"])
        receipt = produce_recovery_receipt(bundle.bundle_id, plan.plan_id, "ready")
        self.assertEqual(receipt.status, "ready")

        bundle2 = FailureBundle.create("patch_runtime", ["PATCH_ALLOWLIST_FAILED"], ["ev-3"])
        plan2 = RecoveryPlan.create(bundle2.bundle_id, ["fix allowlist", "re-run validation"])
        receipt2 = produce_recovery_receipt(bundle2.bundle_id, plan2.plan_id, "ready")
        self.assertEqual(receipt2.status, "ready")


class TestSpineValidatorIntegration(unittest.TestCase):
    """Runtime Receipt Validator cross-subsystem tests."""

    def test_full_spine_validation(self):
        result = RuntimeReceiptValidator.validate_full_spine(
            {"artifact_id": "ev-1", "content_hash": VALID_SHA256, "hash_algorithm": "sha256"},
            {
                "receipt_id": "rp-1", "anchor_id": "a-1", "canonical_hash": VALID_SHA256_B,
                "evidence_binding_valid": True,
                "evidence_binding_hash": VALID_SHA256,
                "evidence_artifact_ids": ["ev-1"],
            },
            {
                "receipt_id": "pt-1", "request_id": "req-1", "canonical_hash": VALID_SHA256_C,
                "replay_receipt_hash": VALID_SHA256_B,
            },
            {
                "receipt_id": "ex-1", "execution_id": "exec-1", "canonical_hash": VALID_SHA256_D,
                "patch_receipt_hash": VALID_SHA256_C,
            },
            {
                "receipt_id": "op-1", "run_id": "run-1", "canonical_hash": VALID_SHA256_E,
                "execution_receipt_hashes": [VALID_SHA256_D],
            },
        )
        self.assertTrue(result["spine_valid"])


class TestAllReceiptsDeterministic(unittest.TestCase):
    """Verify all receipt types are deterministic."""

    def test_replay_receipt_deterministic(self):
        r1 = _make_replay_receipt()
        r2 = _make_replay_receipt()
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_patch_receipt_deterministic(self):
        r1 = _make_patch_receipt(VALID_SHA256)
        r2 = _make_patch_receipt(VALID_SHA256)
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_execution_receipt_deterministic(self):
        r1 = _make_execution_receipt(VALID_SHA256)
        r2 = _make_execution_receipt(VALID_SHA256)
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
                    if "no live provider" in stripped.lower():
                        continue
                    lower = stripped.lower()
                    if "provider execution" in lower and "no" not in lower:
                        self.fail(f"{py_file.name}: claims provider execution")
                    if "live provider execution" in lower:
                        self.fail(f"{py_file.name}: claims live provider execution")

    def test_no_trading_claim(self):
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
