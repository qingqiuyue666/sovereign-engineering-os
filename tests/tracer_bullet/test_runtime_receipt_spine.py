"""Runtime receipt spine integration tests.

Tests:
- Evidence Vault -> Replay compatibility
- Replay -> Patch compatibility
- Patch -> Execution compatibility
- Execution -> Operator Run compatibility
- Deterministic receipt chain hash
- Missing chain link rejected
- Mismatched artifact IDs rejected
- Raw payload rejected
- No network/subprocess/live provider/trading
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from runtime_spine import (  # type: ignore[import-not-found]
    RuntimeReceiptChain,
    RuntimeReceiptValidator,
    RuntimeSpineCanonicalHash,
    RuntimeSpineSecurity,
)

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64
VALID_SHA256_C = "c" * 64
VALID_SHA256_D = "d" * 64
VALID_SHA256_E = "e" * 64


class TestRuntimeReceiptChain(unittest.TestCase):
    """Receipt chain tests."""

    def test_empty_chain_invalid(self):
        chain = RuntimeReceiptChain()
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 5)

    def test_partial_chain_invalid(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("patch", result["missing_links"])

    def test_full_chain_valid(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertTrue(result["chain_valid"])
        self.assertEqual(result["link_count"], 5)

    def test_chain_hash_deterministic(self):
        chain1 = RuntimeReceiptChain()
        for h in [VALID_SHA256, VALID_SHA256_B, VALID_SHA256_C, VALID_SHA256_D, VALID_SHA256_E]:
            chain1.set_evidence_vault_receipt(VALID_SHA256)
            chain1.set_replay_receipt(VALID_SHA256_B)
            chain1.set_patch_receipt(VALID_SHA256_C)
            chain1.set_execution_receipt(VALID_SHA256_D)
            chain1.set_operator_run_receipt(VALID_SHA256_E)

        chain2 = RuntimeReceiptChain()
        chain2.set_evidence_vault_receipt(VALID_SHA256)
        chain2.set_replay_receipt(VALID_SHA256_B)
        chain2.set_patch_receipt(VALID_SHA256_C)
        chain2.set_execution_receipt(VALID_SHA256_D)
        chain2.set_operator_run_receipt(VALID_SHA256_E)

        self.assertEqual(chain1.chain_hash(), chain2.chain_hash())

    def test_enforce_raises_on_incomplete(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        with self.assertRaises(ValueError):
            chain.enforce()

    def test_enforce_passes_on_complete(self):
        chain = RuntimeReceiptChain()
        for h in [VALID_SHA256, VALID_SHA256_B, VALID_SHA256_C, VALID_SHA256_D, VALID_SHA256_E]:
            chain.set_evidence_vault_receipt(VALID_SHA256)
            chain.set_replay_receipt(VALID_SHA256_B)
            chain.set_patch_receipt(VALID_SHA256_C)
            chain.set_execution_receipt(VALID_SHA256_D)
            chain.set_operator_run_receipt(VALID_SHA256_E)
        chain.enforce()  # should not raise

    def test_reject_invalid_hash_length(self):
        chain = RuntimeReceiptChain()
        with self.assertRaises(ValueError):
            chain.set_evidence_vault_receipt("short")

    def test_missing_link_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        # Missing patch, execution, operator
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 3)

    def test_reset(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.reset()
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 5)


class TestRuntimeReceiptValidator(unittest.TestCase):
    """Receipt compatibility validation tests."""

    def _ev_receipt(self):
        return {"artifact_id": "ev-1", "content_hash": VALID_SHA256, "hash_algorithm": "sha256"}

    def _rp_receipt(self):
        return {"receipt_id": "rp-1", "anchor_id": "a-1", "canonical_hash": VALID_SHA256_B}

    def _pt_receipt(self):
        return {"receipt_id": "pt-1", "request_id": "req-1", "canonical_hash": VALID_SHA256_C}

    def _ex_receipt(self):
        return {"receipt_id": "ex-1", "execution_id": "exec-1", "canonical_hash": VALID_SHA256_D}

    def _op_receipt(self):
        return {"receipt_id": "op-1", "run_id": "run-1", "canonical_hash": VALID_SHA256_E}

    def test_evidence_to_replay_compatible(self):
        result = RuntimeReceiptValidator.validate_evidence_to_replay(
            self._ev_receipt(), self._rp_receipt(),
        )
        self.assertTrue(result["compatible"])

    def test_evidence_to_replay_missing_fields(self):
        result = RuntimeReceiptValidator.validate_evidence_to_replay(
            {}, self._rp_receipt(),
        )
        self.assertFalse(result["compatible"])

    def test_replay_to_patch_compatible(self):
        result = RuntimeReceiptValidator.validate_replay_to_patch(
            self._rp_receipt(), self._pt_receipt(),
        )
        self.assertTrue(result["compatible"])

    def test_patch_to_execution_compatible(self):
        result = RuntimeReceiptValidator.validate_patch_to_execution(
            self._pt_receipt(), self._ex_receipt(),
        )
        self.assertTrue(result["compatible"])

    def test_execution_to_operator_compatible(self):
        result = RuntimeReceiptValidator.validate_execution_to_operator(
            self._ex_receipt(), self._op_receipt(),
        )
        self.assertTrue(result["compatible"])

    def test_raw_payload_rejected(self):
        bad_ev = {**self._ev_receipt(), "raw_payload": "secret data"}
        result = RuntimeReceiptValidator.validate_evidence_to_replay(
            bad_ev, self._rp_receipt(),
        )
        self.assertFalse(result["compatible"])
        self.assertIn("raw_payload_detected", result["issues"])

    def test_raw_data_rejected(self):
        bad_rp = {**self._rp_receipt(), "raw_data": "sensitive"}
        result = RuntimeReceiptValidator.validate_evidence_to_replay(
            self._ev_receipt(), bad_rp,
        )
        self.assertFalse(result["compatible"])
        self.assertIn("raw_payload_detected", result["issues"])

    def test_full_spine_valid(self):
        result = RuntimeReceiptValidator.validate_full_spine(
            self._ev_receipt(), self._rp_receipt(), self._pt_receipt(),
            self._ex_receipt(), self._op_receipt(),
        )
        self.assertTrue(result["spine_valid"])
        self.assertTrue(result["spine_hash"])

    def test_full_spine_invalid_on_missing(self):
        result = RuntimeReceiptValidator.validate_full_spine(
            {}, self._rp_receipt(), self._pt_receipt(),
            self._ex_receipt(), self._op_receipt(),
        )
        self.assertFalse(result["spine_valid"])

    def test_pair_hash_deterministic(self):
        r1 = RuntimeReceiptValidator.validate_evidence_to_replay(
            self._ev_receipt(), self._rp_receipt(),
        )
        r2 = RuntimeReceiptValidator.validate_evidence_to_replay(
            self._ev_receipt(), self._rp_receipt(),
        )
        self.assertEqual(r1["pair_hash"], r2["pair_hash"])


class TestRuntimeSpineCanonicalHash(unittest.TestCase):
    """Spine canonical hash tests."""

    def test_canonical_hash(self):
        h = RuntimeSpineCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(len(h), 64)

    def test_deterministic(self):
        h1 = RuntimeSpineCanonicalHash.canonical_hash("a", "b")
        h2 = RuntimeSpineCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(h1, h2)

    def test_chain_hash(self):
        h = RuntimeSpineCanonicalHash.chain_hash([VALID_SHA256, VALID_SHA256_B])
        self.assertEqual(len(h), 64)

    def test_spine_hash(self):
        h = RuntimeSpineCanonicalHash.spine_hash([VALID_SHA256, VALID_SHA256_B])
        self.assertEqual(len(h), 64)


class TestRuntimeSpineSecurity(unittest.TestCase):
    """Spine security tests."""

    def test_no_raw_payload_clean(self):
        self.assertTrue(RuntimeSpineSecurity.validate_no_raw_payload({"id": "1"}))

    def test_no_raw_payload_rejected(self):
        self.assertFalse(RuntimeSpineSecurity.validate_no_raw_payload({"raw_payload": "data"}))

    def test_validate_all_clean(self):
        result = RuntimeSpineSecurity.validate_all_no_raw_payload([
            {"id": "1"}, {"id": "2"},
        ])
        self.assertTrue(result["valid"])

    def test_validate_all_with_raw(self):
        result = RuntimeSpineSecurity.validate_all_no_raw_payload([
            {"id": "1"}, {"raw_payload": "data"},
        ])
        self.assertFalse(result["valid"])

    def test_security_gates(self):
        gates = RuntimeSpineSecurity.security_gates()
        self.assertTrue(all(gates.values()))


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in spine modules."""

    def test_no_forbidden_imports(self):
        spine_dir = ROOT / "tools" / "runtime_spine"
        for py_file in spine_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name}")
            self.assertNotIn("import socket", src, f"{py_file.name}")
            self.assertNotIn("import requests", src, f"{py_file.name}")
            self.assertNotIn("from urllib", src, f"{py_file.name}")

    def test_no_env_reads(self):
        spine_dir = ROOT / "tools" / "runtime_spine"
        for py_file in spine_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name}")
            self.assertNotIn("os.environ", src, f"{py_file.name}")


if __name__ == "__main__":
    unittest.main()
