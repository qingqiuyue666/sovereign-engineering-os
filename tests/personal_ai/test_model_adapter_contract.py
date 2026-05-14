import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.model_adapter_contract import (
    ModelFixtureSchema,
    ModelRuntimePaths,
    build_model_fixture_capability_request,
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


if __name__ == "__main__":
    unittest.main()
