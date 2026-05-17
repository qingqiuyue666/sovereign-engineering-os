"""Provider execution plane tracer-bullet tests — strict typing."""

import unittest

from kernel.runtime.provider_execution_plane import validate_provider_execution_plane


class ProviderExecutionPlaneTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "p1", "request_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "authorization_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "policy_version": "v1", "code_version": "c1"}

    def test_valid_accepted(self):
        receipt = validate_provider_execution_plane(self._valid())
        self.assertTrue(receipt.accepted)

    def test_default_disabled_rejected(self):
        p = self._valid()
        p["provider_enabled"] = True
        receipt = validate_provider_execution_plane(p)
        self.assertIn("provider_enabled_rejected_default_disabled", receipt.failures)

    def test_network_access_rejected(self):
        p = self._valid()
        p["network_access"] = True
        receipt = validate_provider_execution_plane(p)
        self.assertIn("network_access_rejected", receipt.failures)

    def test_tool_calls_rejected(self):
        p = self._valid()
        p["tool_calls_enabled"] = True
        receipt = validate_provider_execution_plane(p)
        self.assertIn("tool_calls_enabled_rejected", receipt.failures)

    def test_production_autonomy_rejected(self):
        p = self._valid()
        p["production_autonomy"] = True
        receipt = validate_provider_execution_plane(p)
        self.assertIn("production_autonomy_rejected", receipt.failures)

    # Strict typing negative tests
    def test_provider_id_none_rejected(self):
        p = self._valid()
        p["provider_id"] = None
        receipt = validate_provider_execution_plane(p)
        self.assertIn("provider_id_must_not_be_none", receipt.failures)

    def test_provider_id_empty_rejected(self):
        p = self._valid()
        p["provider_id"] = ""
        receipt = validate_provider_execution_plane(p)
        self.assertTrue(any("provider_id" in f for f in receipt.failures))

    def test_digest_bad_prefix_rejected(self):
        p = self._valid()
        p["request_digest"] = "bad:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        receipt = validate_provider_execution_plane(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_digest_short_hex_rejected(self):
        p = self._valid()
        p["request_digest"] = "sha256:abc"
        receipt = validate_provider_execution_plane(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_digest_uppercase_rejected(self):
        p = self._valid()
        p["request_digest"] = "sha256:ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"
        receipt = validate_provider_execution_plane(p)
        self.assertTrue(any("valid_digest" in f for f in receipt.failures))

    def test_boolean_gate_as_string_rejected(self):
        p = self._valid()
        p["provider_enabled"] = "true"
        receipt = validate_provider_execution_plane(p)
        self.assertIn("provider_enabled_must_be_bool", receipt.failures)

    def test_boolean_gate_as_int_rejected(self):
        p = self._valid()
        p["production_autonomy"] = 1
        receipt = validate_provider_execution_plane(p)
        self.assertIn("production_autonomy_must_be_bool", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_provider_execution_plane(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)
