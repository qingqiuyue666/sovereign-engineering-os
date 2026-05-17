"""Provider execution plane tracer-bullet tests."""

import unittest

from kernel.runtime.provider_execution_plane import validate_provider_execution_plane


class ProviderExecutionPlaneTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "p1", "request_digest": "sha256:abc", "authorization_digest": "sha256:abc", "policy_version": "v1", "code_version": "c1"}

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

    def test_valid_accepted(self):
        receipt = validate_provider_execution_plane(self._valid())
        self.assertTrue(receipt.accepted)
