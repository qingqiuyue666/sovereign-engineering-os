"""Provider execution receipt tracer-bullet tests — strict typing."""

import unittest

from kernel.runtime.provider_execution_receipt import validate_provider_execution_receipt


class ProviderExecutionReceiptTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "p1", "request_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "response_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "authorization_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "policy_version": "v1", "code_version": "c1", "post_run_health_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "quarantine_ref": "qr1"}

    def test_valid_accepted(self):
        receipt = validate_provider_execution_receipt(self._valid())
        self.assertTrue(receipt.accepted)

    def test_missing_request_digest_rejected(self):
        p = self._valid()
        del p["request_digest"]
        receipt = validate_provider_execution_receipt(p)
        self.assertTrue(any("request_digest" in f for f in receipt.failures))

    def test_digest_none_rejected(self):
        p = self._valid()
        p["request_digest"] = None
        receipt = validate_provider_execution_receipt(p)
        self.assertIn("request_digest_must_not_be_none", receipt.failures)

    def test_digest_bad_prefix_rejected(self):
        p = self._valid()
        p["response_digest"] = "bad:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        receipt = validate_provider_execution_receipt(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_digest_short_hex_rejected(self):
        p = self._valid()
        p["response_digest"] = "sha256:abc"
        receipt = validate_provider_execution_receipt(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_provider_execution_receipt(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        p = self._valid()
        p["secret_value"] = "sk-abc"
        receipt = validate_provider_execution_receipt(p)
        self.assertIn("secret_value_forbidden", receipt.failures)
