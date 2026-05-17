"""Provider adapter registry tracer-bullet tests — strict membership checks."""

import unittest

from kernel.runtime.provider_adapter_registry import validate_provider_adapter_registry


class ProviderAdapterRegistryTests(unittest.TestCase):
    def _valid(self):
        return {"provider_id": "anthropic", "allowed_provider_types": ["anthropic"], "capability_boundary_ref": "cb1", "context_firewall_binding_ref": "cf1"}

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
        self.assertIn("provider_id_must_not_be_none", receipt.failures)

    def test_provider_id_none_rejected(self):
        p = self._valid()
        p["provider_id"] = None
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("provider_id_must_not_be_none", receipt.failures)

    def test_provider_id_empty_rejected(self):
        p = self._valid()
        p["provider_id"] = ""
        receipt = validate_provider_adapter_registry(p)
        self.assertTrue(any("provider_id" in f for f in receipt.failures))

    def test_provider_id_not_in_allowed_list_rejected(self):
        p = {"provider_id": "not_allowed", "allowed_provider_types": ["mock"], "capability_boundary_ref": "cb1", "context_firewall_binding_ref": "cf1"}
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("provider_id_not_in_allowed_provider_types", receipt.failures)

    def test_allowed_provider_types_empty_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = []
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("allowed_provider_types_must_be_nonempty", receipt.failures)

    def test_allowed_provider_types_not_list_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = "not_a_list"
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("allowed_provider_types_must_be_list", receipt.failures)

    def test_allowed_provider_types_none_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = None
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("allowed_provider_types_must_not_be_none", receipt.failures)

    def test_allowed_provider_types_contains_nonstring_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = [123, "anthropic"]
        receipt = validate_provider_adapter_registry(p)
        self.assertTrue(any("must_be_string" in f for f in receipt.failures))

    def test_allowed_provider_types_contains_none_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = [None, "anthropic"]
        receipt = validate_provider_adapter_registry(p)
        self.assertTrue(any("must_not_be_none" in f for f in receipt.failures))

    def test_allowed_provider_types_contains_empty_string_rejected(self):
        p = self._valid()
        p["allowed_provider_types"] = ["", "anthropic"]
        receipt = validate_provider_adapter_registry(p)
        self.assertTrue(any("must_be_nonempty_string" in f for f in receipt.failures))

    def test_missing_capability_boundary_rejected(self):
        p = self._valid()
        del p["capability_boundary_ref"]
        receipt = validate_provider_adapter_registry(p)
        self.assertTrue(any("capability_boundary_ref" in f for f in receipt.failures))

    def test_default_enabled_string_rejected(self):
        p = self._valid()
        p["default_enabled"] = "false"
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("default_enabled_must_be_bool", receipt.failures)

    def test_default_enabled_int_rejected(self):
        p = self._valid()
        p["default_enabled"] = 0
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("default_enabled_must_be_bool", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = self._valid()
        p["raw_prompt"] = "test"
        receipt = validate_provider_adapter_registry(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)
