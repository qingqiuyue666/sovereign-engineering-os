"""Provider execution receipt tracer-bullet tests."""

import unittest

from kernel.runtime.provider_execution_receipt import validate_provider_execution_receipt


class ProviderExecutionReceiptTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "p1", "request_digest": "sha256:abc", "response_digest": "sha256:abc", "authorization_digest": "sha256:abc", "policy_version": "v1", "code_version": "c1", "post_run_health_digest": "sha256:abc", "quarantine_ref": "qr1"}

    def test_valid_accepted(self):
        receipt = validate_provider_execution_receipt(self._valid())
        self.assertTrue(receipt.accepted)

    def test_missing_request_digest_rejected(self):
        p = self._valid()
        del p["request_digest"]
        receipt = validate_provider_execution_receipt(p)
        self.assertIn("request_digest_required", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_provider_execution_receipt(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)
