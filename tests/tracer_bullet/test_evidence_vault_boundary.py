"""Evidence vault boundary tracer-bullet tests — strict typing."""

import json
import unittest
from pathlib import Path

from kernel.evidence.evidence_vault_boundary import validate_evidence_vault_boundary

POLICY_PATH = Path("governance/evidence/evidence_vault_boundary_policy_v1.json")


class EvidenceVaultBoundaryTests(unittest.TestCase):
    def _valid(self):
        return {"artifact_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "policy_version": "v1", "code_version": "c1"}

    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())

    def test_valid_accepted(self):
        receipt = validate_evidence_vault_boundary(self._valid())
        self.assertTrue(receipt.accepted)

    def test_default_disabled_rejected(self):
        p = self._valid()
        p["vault_enabled"] = True
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("vault_enabled_rejected_default_disabled", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    # Strict typing tests
    def test_artifact_digest_none_rejected(self):
        p = self._valid()
        p["artifact_digest"] = None
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("artifact_digest_must_not_be_none", receipt.failures)

    def test_artifact_digest_bad_prefix_rejected(self):
        p = self._valid()
        p["artifact_digest"] = "bad:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        receipt = validate_evidence_vault_boundary(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_artifact_digest_short_rejected(self):
        p = self._valid()
        p["artifact_digest"] = "sha256:abc"
        receipt = validate_evidence_vault_boundary(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_policy_version_none_rejected(self):
        p = self._valid()
        p["policy_version"] = None
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("policy_version_must_not_be_none", receipt.failures)

    def test_vault_enabled_string_rejected(self):
        p = self._valid()
        p["vault_enabled"] = "true"
        receipt = validate_evidence_vault_boundary(p)
        self.assertIn("vault_enabled_must_be_bool", receipt.failures)
