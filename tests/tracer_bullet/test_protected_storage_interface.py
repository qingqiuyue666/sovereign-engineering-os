"""Protected storage interface tracer-bullet tests."""

import unittest

from kernel.evidence.protected_storage_interface import validate_protected_storage_request


class ProtectedStorageInterfaceTests(unittest.TestCase):
    def _valid(self):
        return {"storage_request_id": "s1", "artifact_digest": "sha256:abc", "policy_version": "v1", "code_version": "c1", "human_approval_token": "tok"}

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
        self.assertIn("human_approval_token_required", receipt.failures)

    def test_deterministic(self):
        r1 = validate_protected_storage_request(self._valid())
        r2 = validate_protected_storage_request(self._valid())
        self.assertEqual(r1.as_dict(), r2.as_dict())
