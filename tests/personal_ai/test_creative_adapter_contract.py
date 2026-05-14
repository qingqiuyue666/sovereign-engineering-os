import unittest

from kernel.personal_ai.adapters.creative_adapter_contract import (
    CreativeAdapterFamily,
    CreativeAdapterPolicy,
    build_creative_adapter_policies,
    policy_for_family,
    validate_creative_adapter_policy,
)


class CreativeAdapterContractTests(unittest.TestCase):
    def test_all_required_policy_families_are_registered(self):
        policies = build_creative_adapter_policies()

        self.assertEqual(
            tuple(policy.family for policy in policies),
            CreativeAdapterFamily.all(),
        )
        self.assertEqual(len(policies), 6)

    def test_default_policies_do_not_admit_runtime_or_tool_control(self):
        for policy in build_creative_adapter_policies():
            self.assertFalse(policy.runtime_admitted)
            self.assertFalse(policy.external_tool_control_admitted)
            self.assertTrue(policy.explicit_future_admission_required)
            self.assertFalse(policy.source_asset_overwrite_allowed)
            self.assertTrue(policy.output_manifest_required)
            self.assertTrue(policy.preview_render_evidence_required)
            self.assertTrue(policy.logs_required)
            self.assertTrue(policy.human_approval_required)
            self.assertEqual(validate_creative_adapter_policy(policy), ())

    def test_policy_lookup_is_deterministic(self):
        policy = policy_for_family(CreativeAdapterFamily.BLENDER)

        self.assertEqual(policy.family, CreativeAdapterFamily.BLENDER)
        self.assertEqual(policy.proposed_adapter, "future_blender_controlled_runtime")

    def test_policy_validator_rejects_runtime_admission(self):
        policy = CreativeAdapterPolicy(
            family=CreativeAdapterFamily.COMFYUI,
            proposed_adapter="future_comfyui_controlled_runtime",
            runtime_admitted=True,
            external_tool_control_admitted=True,
            explicit_future_admission_required=False,
            source_asset_overwrite_allowed=True,
        )

        failures = validate_creative_adapter_policy(policy)

        self.assertIn("runtime_must_not_be_admitted", failures)
        self.assertIn("external_tool_control_must_not_be_admitted", failures)
        self.assertIn("future_admission_required", failures)
        self.assertIn("source_asset_overwrite_forbidden", failures)


if __name__ == "__main__":
    unittest.main()
