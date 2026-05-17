"""Evidence vault boundary tracer-bullet tests."""

import json
import unittest
from pathlib import Path

from kernel.evidence.evidence_vault_boundary import validate_evidence_vault_boundary

POLICY_PATH = Path("governance/evidence/evidence_vault_boundary_policy_v1.json")


class EvidenceVaultBoundaryPolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())


class EvidenceVaultBoundaryTests(unittest.TestCase):
    def _valid(self):
        return {"artifact_digest": "sha256:abc", "policy_version": "v1", "code_version": "c1"}

    def test_default_disabled_rejected(self):
        p = self._valid()
        p["vault_enabled"] = True
        receipt = validate_evidence_vault_boundary(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("vault_enabled_rejected_default_disabled", receipt.failures)

    def test_valid_accepted(self):
        receipt = validate_evidence_vault_boundary(self._valid())
        self.assertTrue(receipt.accepted)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)


class EvidenceVaultReceiptTests(unittest.TestCase):
    def _valid(self):
        from kernel.evidence.evidence_vault_receipt import validate_evidence_vault_receipt
        return validate_evidence_vault_receipt

    def test_valid_accepted(self):
        from kernel.evidence.evidence_vault_receipt import validate_evidence_vault_receipt
        receipt = validate_evidence_vault_receipt({"receipt_id": "r1", "artifact_digest": "sha256:abc", "storage_classification": "public", "policy_version": "v1", "code_version": "c1"})
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.approved)


class ProtectedStorageInterfaceTests(unittest.TestCase):
    def _valid(self):
        from kernel.evidence.protected_storage_interface import validate_protected_storage_request
        return validate_protected_storage_request

    def test_live_write_rejected(self):
        from kernel.evidence.protected_storage_interface import validate_protected_storage_request
        receipt = validate_protected_storage_request({"storage_request_id": "s1", "artifact_digest": "sha256:abc", "policy_version": "v1", "code_version": "c1", "live_write": True, "human_approval_token": "tok"})
        self.assertIn("live_write_rejected", receipt.failures)
