"""Branch-wide runtime train receipt chain tests.

Verifies the full receipt chain across all subsystems:
Evidence Vault -> Replay -> Patch -> Execution -> Operator Daily Run.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from runtime_spine import RuntimeReceiptChain, RuntimeReceiptValidator

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64
VALID_SHA256_C = "c" * 64
VALID_SHA256_D = "d" * 64
VALID_SHA256_E = "e" * 64


class TestFullReceiptChain(unittest.TestCase):
    """Full 5-link receipt chain tests."""

    def test_complete_chain_valid(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertTrue(result["chain_valid"])
        self.assertEqual(result["link_count"], 5)
        self.assertEqual(result["total_links"], 5)
        self.assertEqual(len(result["missing_links"]), 0)

    def test_missing_evidence_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("evidence_vault", result["missing_links"])

    def test_missing_replay_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("replay", result["missing_links"])

    def test_missing_patch_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_execution_receipt(VALID_SHA256_D)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("patch", result["missing_links"])

    def test_missing_execution_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_operator_run_receipt(VALID_SHA256_E)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("execution", result["missing_links"])

    def test_missing_operator_rejected(self):
        chain = RuntimeReceiptChain()
        chain.set_evidence_vault_receipt(VALID_SHA256)
        chain.set_replay_receipt(VALID_SHA256_B)
        chain.set_patch_receipt(VALID_SHA256_C)
        chain.set_execution_receipt(VALID_SHA256_D)
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertIn("operator_run", result["missing_links"])

    def test_empty_chain_rejected(self):
        chain = RuntimeReceiptChain()
        result = chain.validate()
        self.assertFalse(result["chain_valid"])
        self.assertEqual(len(result["missing_links"]), 5)
        self.assertEqual(result["link_count"], 0)

    def test_chain_hash_deterministic(self):
        c1 = RuntimeReceiptChain()
        c2 = RuntimeReceiptChain()
        for c in (c1, c2):
            c.set_evidence_vault_receipt(VALID_SHA256)
            c.set_replay_receipt(VALID_SHA256_B)
            c.set_patch_receipt(VALID_SHA256_C)
            c.set_execution_receipt(VALID_SHA256_D)
            c.set_operator_run_receipt(VALID_SHA256_E)
        self.assertEqual(c1.chain_hash(), c2.chain_hash())

    def test_chain_hash_changes_with_different_links(self):
        c1 = RuntimeReceiptChain()
        c1.set_evidence_vault_receipt(VALID_SHA256)
        c1.set_replay_receipt(VALID_SHA256_B)
        c1.set_patch_receipt(VALID_SHA256_C)
        c1.set_execution_receipt(VALID_SHA256_D)
        c1.set_operator_run_receipt(VALID_SHA256_E)

        c2 = RuntimeReceiptChain()
        c2.set_evidence_vault_receipt("f" * 64)
        c2.set_replay_receipt(VALID_SHA256_B)
        c2.set_patch_receipt(VALID_SHA256_C)
        c2.set_execution_receipt(VALID_SHA256_D)
        c2.set_operator_run_receipt(VALID_SHA256_E)

        self.assertNotEqual(c1.chain_hash(), c2.chain_hash())

    def test_spine_validator_full_chain(self):
        result = RuntimeReceiptValidator.validate_full_spine(
            {"artifact_id": "ev-1", "content_hash": VALID_SHA256, "hash_algorithm": "sha256"},
            {"receipt_id": "rp-1", "anchor_id": "a-1", "canonical_hash": VALID_SHA256_B},
            {"receipt_id": "pt-1", "request_id": "req-1", "canonical_hash": VALID_SHA256_C},
            {"receipt_id": "ex-1", "execution_id": "exec-1", "canonical_hash": VALID_SHA256_D},
            {"receipt_id": "op-1", "run_id": "run-1", "canonical_hash": VALID_SHA256_E},
        )
        self.assertTrue(result["spine_valid"])
        self.assertEqual(len(result["pairs"]), 4)
        # Check all pair names
        pair_names = list(result["pairs"].keys())
        self.assertIn("evidence->replay", pair_names)
        self.assertIn("replay->patch", pair_names)
        self.assertIn("patch->execution", pair_names)
        self.assertIn("execution->operator", pair_names)


if __name__ == "__main__":
    unittest.main()
