import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.model_adapter_contract import (
    ModelFixtureSchema,
    ModelRuntimePaths,
    build_model_fixture_capability_request,
    build_model_provider_registry,
    find_model_provider,
)


class ModelAdapterContractTests(unittest.TestCase):
    def test_model_fixture_request_is_mock_runtime_only(self):
        request = build_model_fixture_capability_request()

        self.assertEqual(request.adapter_id, "mock_model_typed_schema_runtime")
        self.assertEqual(request.mode, AdapterMode.MOCK_RUNTIME)
        self.assertEqual(request.risk_class, AdapterRiskClass.MOCK_MODEL)
        self.assertTrue(request.boundary.is_runtime_safe_for_current_branch())

    def test_allowed_schemas_are_fixed(self):
        self.assertEqual(
            ModelFixtureSchema.allowed(),
            (
                "job_route_classification_v1",
                "artifact_profile_summary_v1",
                "next_step_recommendation_v1",
            ),
        )
        self.assertEqual(
            ModelRuntimePaths().inference_artifact_file,
            "model_inference_artifact.json",
        )

    def test_provider_registry_keeps_live_provider_disabled_by_default(self):
        registry = build_model_provider_registry()
        providers = {entry.provider_id: entry for entry in registry}

        self.assertTrue(providers["deterministic_mock"].admitted)
        self.assertTrue(providers["deterministic_mock"].enabled_by_default)
        self.assertFalse(providers["deterministic_mock"].live_provider_runtime)
        self.assertFalse(providers["openai"].admitted)
        self.assertFalse(providers["openai"].enabled_by_default)
        self.assertTrue(providers["openai"].live_provider_runtime)
        self.assertEqual(providers["openai"].api_key_env_var, "OPENAI_API_KEY")
        self.assertFalse(providers["openai"].policy["api_key_persistence_allowed"])
        self.assertFalse(providers["openai"].policy["api_key_logging_allowed"])
        self.assertFalse(providers["openai"].policy["real_provider_calls_allowed"])
        self.assertEqual(find_model_provider("openai").provider_kind, "live")


if __name__ == "__main__":
    unittest.main()
