import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRegistryEntry,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.adapter_registry import (
    DEFAULT_ADAPTER_REGISTRY,
    admit_adapter_capability,
    build_default_adapter_registry,
    find_adapter_entry,
    validate_adapter_registry_entry,
)


class AdapterRegistryTests(unittest.TestCase):
    def test_default_registry_is_deterministic_and_unique(self):
        first = build_default_adapter_registry()
        second = build_default_adapter_registry()

        self.assertEqual([entry.to_dict() for entry in first], [entry.to_dict() for entry in second])
        self.assertEqual(
            len({entry.adapter_id for entry in DEFAULT_ADAPTER_REGISTRY}),
            len(DEFAULT_ADAPTER_REGISTRY),
        )

    def test_admitted_entries_validate_fail_closed(self):
        for entry in DEFAULT_ADAPTER_REGISTRY:
            failures = validate_adapter_registry_entry(entry)
            if entry.admission_status == AdapterAdmissionStatus.ADMITTED:
                self.assertEqual(failures, ())
                self.assertTrue(entry.boundary.is_runtime_safe_for_current_branch())

    def test_creative_policy_entry_is_deferred_not_runtime_admitted(self):
        entry = find_adapter_entry("creative_adapter_policy")

        self.assertEqual(entry.admission_status, AdapterAdmissionStatus.DEFERRED)
        self.assertTrue(entry.boundary.requires_explicit_future_admission())
        self.assertIn("adapter_not_admitted", admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability="record_future_creative_controls",
                mode=entry.mode,
                risk_class=entry.risk_class,
                boundary=AdapterExecutionBoundary(external_tool_control_allowed=True),
            )
        ).reason_codes)

    def test_live_model_provider_boundary_is_deferred_not_runtime_admitted(self):
        entry = find_adapter_entry("live_model_provider_boundary")

        self.assertEqual(entry.admission_status, AdapterAdmissionStatus.DEFERRED)
        self.assertEqual(entry.mode, AdapterMode.FUTURE_EXTERNAL)
        self.assertEqual(entry.risk_class, AdapterRiskClass.LIVE_MODEL_PROVIDER)
        self.assertTrue(entry.boundary.requires_explicit_future_admission())
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability="call_typed_schema_provider",
                mode=entry.mode,
                risk_class=entry.risk_class,
                boundary=AdapterExecutionBoundary(network_allowed=True),
            )
        )
        self.assertFalse(decision.admitted)
        self.assertIn("adapter_not_admitted", decision.reason_codes)

    def test_admits_registered_safe_capability(self):
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id="xlsx_readonly_runtime",
                capability="inspect_local_xlsx_metadata",
                mode=AdapterMode.READONLY,
                risk_class=AdapterRiskClass.LOCAL_READONLY,
            )
        )

        self.assertTrue(decision.admitted)
        self.assertEqual(decision.admission_status, AdapterAdmissionStatus.ADMITTED)
        self.assertEqual(decision.reason_codes, ())

    def test_rejects_unknown_capability_and_unsafe_request_boundary(self):
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id="xlsx_readonly_runtime",
                capability="fetch_url",
                mode=AdapterMode.READONLY,
                risk_class=AdapterRiskClass.LOCAL_READONLY,
                boundary=AdapterExecutionBoundary(network_allowed=True),
            )
        )

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.admission_status, AdapterAdmissionStatus.REJECTED)
        self.assertEqual(
            decision.reason_codes,
            ("capability_not_registered", "request_boundary_is_not_safe"),
        )

    def test_rejects_entry_missing_required_controls(self):
        entry = AdapterRegistryEntry(
            adapter_id="unsafe",
            adapter_name="Unsafe",
            mode=AdapterMode.READONLY,
            risk_class=AdapterRiskClass.LOCAL_READONLY,
            admission_status=AdapterAdmissionStatus.ADMITTED,
            capabilities=("inspect",),
            required_controls=("human_approval",),
        )

        self.assertEqual(
            validate_adapter_registry_entry(entry),
            ("required_controls_missing",),
        )


if __name__ == "__main__":
    unittest.main()
