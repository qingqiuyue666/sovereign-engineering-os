"""Protected storage interface tracer-bullet tests — strict typing."""

import unittest

from kernel.evidence.protected_storage_interface import validate_protected_storage_request


class ProtectedStorageInterfaceTests(unittest.TestCase):
    def _valid(self):
        return {"storage_request_id": "s1", "artifact_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "policy_version": "v1", "code_version": "c1", "human_approval_token": "tok"}

    def test_valid_accepted(self):
        receipt = validate_protected_storage_request(self._valid())
        self.assertTrue(receipt.accepted)

    def test_live_write_rejected(self):
        p = self._valid()
        p["live_write"] = True
        receipt = validate_protected_storage_request(p)
        self.assertIn("live_write_rejected", receipt.failures)

    def test_missing_human_approval_rejected(self):
        p = self._valid()
        del p["human_approval_token"]
        receipt = validate_protected_storage_request(p)
        self.assertTrue(any("human_approval_token" in f for f in receipt.failures))

    def test_deterministic(self):
        r1 = validate_protected_storage_request(self._valid())
        r2 = validate_protected_storage_request(self._valid())
        self.assertEqual(r1.as_dict(), r2.as_dict())

    # Strict typing tests
    def test_artifact_digest_none_rejected(self):
        p = self._valid()
        p["artifact_digest"] = None
        receipt = validate_protected_storage_request(p)
        self.assertIn("artifact_digest_must_not_be_none", receipt.failures)

    def test_artifact_digest_bad_prefix_rejected(self):
        p = self._valid()
        p["artifact_digest"] = "bad:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        receipt = validate_protected_storage_request(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_live_write_string_rejected(self):
        p = self._valid()
        p["live_write"] = "true"
        receipt = validate_protected_storage_request(p)
        self.assertIn("live_write_must_be_bool", receipt.failures)

    def test_storage_request_id_none_rejected(self):
        p = self._valid()
        p["storage_request_id"] = None
        receipt = validate_protected_storage_request(p)
        self.assertIn("storage_request_id_must_not_be_none", receipt.failures)
