"""Evidence vault receipt tracer-bullet tests — strict typing."""

import unittest

from kernel.evidence.evidence_vault_receipt import validate_evidence_vault_receipt


class EvidenceVaultReceiptTests(unittest.TestCase):
    def _valid(self):
        return {"receipt_id": "r1", "artifact_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "storage_classification": "public", "policy_version": "v1", "code_version": "c1"}

    def test_valid_accepted(self):
        receipt = validate_evidence_vault_receipt(self._valid())
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.approved)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_evidence_vault_receipt(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        p = self._valid()
        p["secret_value"] = "sk-abc"
        receipt = validate_evidence_vault_receipt(p)
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_deterministic(self):
        r1 = validate_evidence_vault_receipt(self._valid())
        r2 = validate_evidence_vault_receipt(self._valid())
        self.assertEqual(r1.as_dict(), r2.as_dict())

    # Strict typing tests
    def test_receipt_id_none_rejected(self):
        p = self._valid()
        p["receipt_id"] = None
        receipt = validate_evidence_vault_receipt(p)
        self.assertIn("receipt_id_must_not_be_none", receipt.failures)

    def test_artifact_digest_none_rejected(self):
        p = self._valid()
        p["artifact_digest"] = None
        receipt = validate_evidence_vault_receipt(p)
        self.assertIn("artifact_digest_must_not_be_none", receipt.failures)

    def test_artifact_digest_bad_prefix_rejected(self):
        p = self._valid()
        p["artifact_digest"] = "bad:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        receipt = validate_evidence_vault_receipt(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))
