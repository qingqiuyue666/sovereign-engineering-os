"""Tracer-bullet tests for capability boundary, adapter registry, and evidence binding."""

import unittest

from tools.provider_transport.provider_adapter_registry import (
    ProviderAdapterDescriptor,
    ProviderAdapterRegistry,
    FORBIDDEN_CAPABILITIES,
    FORBIDDEN_PROVIDERS,
    KNOWN_PROVIDERS,
    KNOWN_CAPABILITIES,
    validate_adapter_descriptor,
    register_provider_adapter,
    get_provider_adapter,
    list_registered_providers,
)
from tools.provider_transport.provider_capability_boundary import (
    CapabilityBoundaryResult,
    validate_capability_boundary,
    PROVIDER_CAPABILITY_MAP,
)
from tools.provider_transport.provider_evidence_binding import (
    EvidenceBindingResult,
    validate_evidence_binding,
)


class ProviderAdapterRegistryTests(unittest.TestCase):
    """Tests for provider adapter registration and validation."""

    def _descriptor(self):
        return ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"fetch_price", "validate_asset"}),
            boundary_ref="boundary-finance-v1",
            enabled=False,
            dry_run_only=True,
            no_network=True,
        )

    # --- registration ---

    def test_register_valid_adapter(self):
        registry = ProviderAdapterRegistry()
        registry.register(self._descriptor())
        self.assertTrue(registry.is_registered("mock-finance"))

    def test_register_all_known_providers(self):
        registry = ProviderAdapterRegistry()
        for pid in KNOWN_PROVIDERS:
            desc = ProviderAdapterDescriptor(
                provider_id=pid,
                capabilities=frozenset({"mock_execute"}),
                boundary_ref="boundary-v1",
            )
            registry.register(desc)
        self.assertEqual(len(registry.list_providers()), 4)

    # --- forbidden provider rejection ---

    def test_register_live_broker_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="live-broker",
            capabilities=frozenset({"mock_execute"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_register_live_exchange_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="live-exchange",
            capabilities=frozenset({"mock_execute"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_register_live_payment_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="live-payment",
            capabilities=frozenset({"mock_execute"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_register_live_bank_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="live-bank",
            capabilities=frozenset({"mock_execute"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    # --- unknown provider ---

    def test_register_unknown_provider_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="openai-gpt-5",
            capabilities=frozenset({"mock_execute"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    # --- forbidden capability ---

    def test_register_forbidden_capability_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"live_trade"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_live_transfer_capability_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"live_transfer"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_live_withdrawal_capability_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"live_withdrawal"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_live_deposit_capability_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"live_deposit"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    def test_live_order_capability_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset({"live_order"}),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    # --- empty capabilities ---

    def test_empty_capabilities_rejected(self):
        registry = ProviderAdapterRegistry()
        desc = ProviderAdapterDescriptor(
            provider_id="mock-finance",
            capabilities=frozenset(),
            boundary_ref="boundary-v1",
        )
        with self.assertRaises(ValueError):
            registry.register(desc)

    # --- get and list ---

    def test_get_unregistered_returns_none(self):
        registry = ProviderAdapterRegistry()
        self.assertIsNone(registry.get("mock-finance"))

    def test_list_providers_empty_initially(self):
        registry = ProviderAdapterRegistry()
        self.assertEqual(len(registry.list_providers()), 0)

    def test_register_multiple_providers(self):
        registry = ProviderAdapterRegistry()
        for pid in ("mock-finance", "mock-news"):
            desc = ProviderAdapterDescriptor(
                provider_id=pid,
                capabilities=frozenset({"mock_execute"}),
                boundary_ref="boundary-v1",
            )
            registry.register(desc)
        self.assertEqual(len(registry.list_providers()), 2)
        self.assertIn("mock-finance", registry.list_providers())
        self.assertIn("mock-news", registry.list_providers())

    # --- descriptor defaults ---

    def test_descriptor_default_enabled_false(self):
        desc = self._descriptor()
        self.assertFalse(desc.enabled)

    def test_descriptor_default_dry_run_only_true(self):
        desc = self._descriptor()
        self.assertTrue(desc.dry_run_only)

    def test_descriptor_default_no_network_true(self):
        desc = self._descriptor()
        self.assertTrue(desc.no_network)


class AdapterDescriptorValidationTests(unittest.TestCase):
    """Tests for validate_adapter_descriptor — raw dict validation."""

    def _valid_dict(self):
        return {
            "provider_id": "mock-finance",
            "capabilities": ["fetch_price", "validate_asset"],
            "boundary_ref": "boundary-v1",
            "enabled": False,
            "dry_run_only": True,
        }

    def test_valid_accepted(self):
        result = validate_adapter_descriptor(self._valid_dict())
        self.assertTrue(result["valid"], result["failures"])

    # --- missing fields ---

    def test_missing_provider_id_rejected(self):
        p = self._valid_dict()
        del p["provider_id"]
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("provider_id" in f for f in result["failures"]))

    def test_missing_capabilities_rejected(self):
        p = self._valid_dict()
        del p["capabilities"]
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertIn("capabilities_must_not_be_none", result["failures"])

    def test_missing_boundary_ref_rejected(self):
        p = self._valid_dict()
        del p["boundary_ref"]
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("boundary_ref" in f for f in result["failures"]))

    # --- forbidden provider ---

    def test_forbidden_provider_rejected(self):
        p = self._valid_dict()
        p["provider_id"] = "live-broker"
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_provider" in f for f in result["failures"]))

    # --- forbidden capability ---

    def test_forbidden_capability_rejected(self):
        p = self._valid_dict()
        p["capabilities"] = ["live_trade"]
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden_capability" in f for f in result["failures"]))

    # --- empty capabilities ---

    def test_empty_capabilities_rejected(self):
        p = self._valid_dict()
        p["capabilities"] = []
        result = validate_adapter_descriptor(p)
        self.assertFalse(result["valid"])
        self.assertIn("capabilities_must_not_be_empty", result["failures"])

    # --- non-mapping ---

    def test_non_mapping_rejected(self):
        result = validate_adapter_descriptor(["list"])
        self.assertFalse(result["valid"])
        self.assertIn("payload_must_be_mapping", result["failures"])


class CapabilityBoundaryTests(unittest.TestCase):
    """Tests for capability boundary enforcement per provider."""

    def test_allowed_capability_accepted(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price"}))
        self.assertTrue(result.valid, result.failures)

    def test_unsupported_capability_for_provider_rejected(self):
        """mock-news does not support fetch_price."""
        result = validate_capability_boundary("mock-news", frozenset({"fetch_price"}))
        self.assertFalse(result.valid)
        self.assertTrue(any("capability_not_allowed_for_provider" in f for f in result.failures))

    def test_forbidden_capability_rejected(self):
        result = validate_capability_boundary("mock-finance", frozenset({"live_trade"}))
        self.assertFalse(result.valid)
        self.assertTrue(any("forbidden_capability" in f for f in result.failures))

    def test_unknown_capability_rejected(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fly_to_moon"}))
        self.assertFalse(result.valid)
        self.assertTrue(any("unknown_capability" in f for f in result.failures))

    def test_multiple_allowed_capabilities(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price", "calculate_risk", "mock_execute"}))
        self.assertTrue(result.valid, result.failures)

    def test_mixed_allowed_and_rejected(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price", "live_trade"}))
        self.assertFalse(result.valid)
        self.assertTrue(any("forbidden_capability" in f for f in result.failures))

    # --- per-provider boundary ---

    def test_mock_finance_allowed_caps(self):
        for cap in PROVIDER_CAPABILITY_MAP["mock-finance"]:
            result = validate_capability_boundary("mock-finance", frozenset({cap}))
            self.assertTrue(result.valid, f"{cap} should be allowed for mock-finance")

    def test_mock_market_data_allowed_caps(self):
        for cap in PROVIDER_CAPABILITY_MAP["mock-market-data"]:
            result = validate_capability_boundary("mock-market-data", frozenset({cap}))
            self.assertTrue(result.valid, f"{cap} should be allowed for mock-market-data")

    def test_mock_news_allowed_caps(self):
        for cap in PROVIDER_CAPABILITY_MAP["mock-news"]:
            result = validate_capability_boundary("mock-news", frozenset({cap}))
            self.assertTrue(result.valid, f"{cap} should be allowed for mock-news")

    def test_mock_weather_allowed_caps(self):
        for cap in PROVIDER_CAPABILITY_MAP["mock-weather"]:
            result = validate_capability_boundary("mock-weather", frozenset({cap}))
            self.assertTrue(result.valid, f"{cap} should be allowed for mock-weather")

    # --- result fields ---

    def test_result_has_rejected_capabilities(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price", "live_trade", "fly_to_moon"}))
        self.assertIn("live_trade", result.rejected_capabilities)
        self.assertIn("fly_to_moon", result.rejected_capabilities)

    def test_result_has_allowed_capabilities(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price", "calculate_risk"}))
        self.assertIn("fetch_price", result.allowed_capabilities)
        self.assertIn("calculate_risk", result.allowed_capabilities)

    def test_result_as_dict(self):
        result = validate_capability_boundary("mock-finance", frozenset({"fetch_price"}))
        d = result.as_dict()
        self.assertTrue(d["valid"])
        self.assertEqual(d["provider_id"], "mock-finance")

    # --- empty capabilities ---

    def test_empty_capabilities_rejected(self):
        result = validate_capability_boundary("mock-finance", frozenset())
        self.assertFalse(result.valid)

    # --- all forbidden caps rejected ---

    def test_all_forbidden_caps_rejected(self):
        for cap in FORBIDDEN_CAPABILITIES:
            result = validate_capability_boundary("mock-finance", frozenset({cap}))
            self.assertFalse(result.valid, f"{cap} should be rejected")


class EvidenceBindingTests(unittest.TestCase):
    """Tests for evidence binding placeholder validation."""

    def test_valid_binding_accepted(self):
        result = validate_evidence_binding("ev-hash-001")
        self.assertTrue(result.valid, result.failures)

    def test_binding_present(self):
        result = validate_evidence_binding("ev-hash-001")
        self.assertTrue(result.binding_present)

    def test_binding_hash_produced(self):
        result = validate_evidence_binding("ev-hash-001")
        self.assertTrue(len(result.binding_hash) == 64)

    def test_binding_deterministic_hash(self):
        a = validate_evidence_binding("ev-hash-001")
        b = validate_evidence_binding("ev-hash-001")
        self.assertEqual(a.binding_hash, b.binding_hash)

    def test_different_binding_different_hash(self):
        a = validate_evidence_binding("ev-hash-001")
        b = validate_evidence_binding("ev-hash-002")
        self.assertNotEqual(a.binding_hash, b.binding_hash)

    # --- missing binding ---

    def test_missing_binding_rejected_when_required(self):
        result = validate_evidence_binding("", require_present=True)
        self.assertFalse(result.valid)
        self.assertIn("evidence_binding_required", result.failures)

    def test_missing_binding_accepted_when_not_required(self):
        result = validate_evidence_binding("", require_present=False)
        self.assertTrue(result.valid)

    def test_whitespace_only_binding_rejected(self):
        result = validate_evidence_binding("   ", require_present=True)
        self.assertFalse(result.valid)

    # --- as_dict ---

    def test_as_dict(self):
        result = validate_evidence_binding("ev-001")
        d = result.as_dict()
        self.assertTrue(d["valid"])
        self.assertTrue(d["binding_present"])


if __name__ == "__main__":
    unittest.main()
