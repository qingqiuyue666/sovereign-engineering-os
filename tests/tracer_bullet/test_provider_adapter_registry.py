"""Provider adapter registry tracer-bullet tests."""

import unittest

from kernel.runtime.provider_adapter_registry import validate_provider_adapter_registry


class ProviderAdapterRegistryTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "p1", "allowed_provider_types": ["anthropic"], "capability_boundary_ref": "cb1", "context_firewall_binding_ref": "cf1"}

    def test_valid_accepted(self):
        receipt = validate_provider_adapter_registry(self._valid())
        self.assertTrue(receipt.accepted)

    def test_default_enabled_true_rejected(self):
        p = self._valid()
        p["default_enabled"] = True
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("default_enabled_must_be_false", receipt.failures)

    def test_missing_provider_id_rejected(self):
        p = self._valid()
        del p["provider_id"]
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("provider_id_required", receipt.failures)

    def test_missing_capability_boundary_rejected(self):
        p = self._valid()
        del p["capability_boundary_ref"]
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("capability_boundary_ref_required", receipt.failures)
