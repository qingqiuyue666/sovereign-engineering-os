import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
)
from kernel.personal_ai.adapters.adapter_registry import (
    DCC_MEDIA_POLICY_CAPABILITY,
    admit_adapter_capability,
    find_adapter_entry,
    validate_dcc_media_policy_registry_binding,
)
from kernel.personal_ai.adapters.creative_adapter_contract import (
    build_creative_adapter_policies,
)


class DCCMediaAdapterRegistryIntegrationAcceptanceTests(unittest.TestCase):
    def test_dcc_media_policy_boundaries_are_audit_bound_and_not_executable(self):
        self.assertEqual(validate_dcc_media_policy_registry_binding(), ())

        for policy in build_creative_adapter_policies():
            entry = find_adapter_entry(policy.proposed_adapter)

            self.assertIn(DCC_MEDIA_POLICY_CAPABILITY, entry.capabilities)
            self.assertTrue(entry.boundary.requires_explicit_future_admission())
            self.assertFalse(entry.boundary.output_write_allowed)
            self.assertFalse(entry.boundary.input_mutation_allowed)
            self.assertFalse(entry.boundary.overwrite_existing_allowed)

            decision = admit_adapter_capability(
                AdapterCapabilityRequest(
                    adapter_id=entry.adapter_id,
                    capability=DCC_MEDIA_POLICY_CAPABILITY,
                    mode=entry.mode,
                    risk_class=entry.risk_class,
                    boundary=AdapterExecutionBoundary(
                        external_tool_control_allowed=True,
                    ),
                )
            )

            self.assertFalse(decision.admitted)
            self.assertIn("adapter_not_admitted", decision.reason_codes)
            self.assertIn("request_boundary_is_not_safe", decision.reason_codes)


if __name__ == "__main__":
    unittest.main()
