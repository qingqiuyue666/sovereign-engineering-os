import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    run_model_fixture,
    write_model_fixture_request,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ModelTypedSchemaRuntimeTests(unittest.TestCase):
    def build_workspace(self, payload=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "output"
        output_dir.mkdir()
        input_path = root / "input.json"
        write_json_atomically(
            input_path,
            payload
            or {
                "route_type": "spreadsheet_route",
                "recommended_processor_lane": "spreadsheet_review",
                "next_allowed_action": "human_review_only",
                "artifacts": [
                    {"relative_path": "a.csv", "category": "spreadsheet"},
                    {"relative_path": "b.txt", "category": "document"},
                ],
            },
        )
        return root, input_path, output_dir

    def test_runs_deterministic_route_classification_fixture(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_model_fixture_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )

        result = run_model_fixture(request_path, output_dir)
        artifact = read_json(result.inference_artifact_path)

        self.assertTrue(result.success)
        self.assertEqual(artifact["provider"], "deterministic_mock")
        self.assertFalse(artifact["network_used"])
        self.assertFalse(artifact["api_key_used"])
        self.assertFalse(artifact["model_output_can_grant_authority"])
        self.assertEqual(
            artifact["typed_output"]["route_type"],
            "spreadsheet_route",
        )

    def test_summarizes_artifact_profile_without_raw_content(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_model_fixture_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.ARTIFACT_PROFILE_SUMMARY,
        )

        result = run_model_fixture(request_path, output_dir)
        typed_output = read_json(result.inference_artifact_path)["typed_output"]

        self.assertEqual(typed_output["artifact_count"], 2)
        self.assertEqual(
            typed_output["category_counts"],
            {"document": 1, "spreadsheet": 1},
        )

    def test_generates_next_step_recommendation(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_model_fixture_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.NEXT_STEP_RECOMMENDATION,
        )

        result = run_model_fixture(request_path, output_dir)
        typed_output = read_json(result.inference_artifact_path)["typed_output"]

        self.assertEqual(typed_output["recommendation"], "human_review_only")
        self.assertTrue(typed_output["requires_human_approval"])

    def test_rejects_invalid_json_like_fixture_output_with_failure_bundle(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_json_atomically(
            request_path,
            {
                "request_type": "personal_ai_execution_os_v2_model_request",
                "request_version": 1,
                "provider": "deterministic_mock",
                "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
                "input_artifact_path": input_path.as_posix(),
                "input_artifact_sha256": sha256_file(input_path),
                "network_allowed": False,
                "api_key_required": False,
                "tool_calls_allowed": False,
                "file_edits_allowed": False,
                "fixture_response_json": "{not-json",
            },
        )

        result = run_model_fixture(request_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertEqual(failure["failure_type"], "personal_ai_execution_os_v2_model_failure_bundle")
        self.assertFalse(failure["network_used"])
        self.assertFalse(failure["model_output_granted_authority"])

    def test_rejects_fixture_output_that_grants_authority(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_json_atomically(
            request_path,
            {
                "request_type": "personal_ai_execution_os_v2_model_request",
                "request_version": 1,
                "provider": "deterministic_mock",
                "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
                "input_artifact_path": input_path.as_posix(),
                "input_artifact_sha256": sha256_file(input_path),
                "network_allowed": False,
                "api_key_required": False,
                "tool_calls_allowed": False,
                "file_edits_allowed": False,
                "fixture_response": {
                    "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
                    "authority": "kernel_authority",
                    "can_grant_authority": True,
                    "can_edit_files": False,
                    "can_call_tools": False,
                    "route_type": "spreadsheet_route",
                    "recommended_processor_lane": "spreadsheet_review",
                    "confidence": "fixture",
                },
            },
        )

        result = run_model_fixture(request_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("authority", failure["error_message"])

    def test_rejects_live_provider_api_key_network_file_edit_and_tool_call(self):
        root, input_path, output_dir = self.build_workspace()
        request_path = root / "model_request.json"
        write_json_atomically(
            request_path,
            {
                "request_type": "personal_ai_execution_os_v2_model_request",
                "request_version": 1,
                "provider": "openai",
                "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
                "input_artifact_path": input_path.as_posix(),
                "input_artifact_sha256": sha256_file(input_path),
                "network_allowed": True,
                "api_key_required": True,
                "api_key": "dummy-test-value",
                "tool_calls_allowed": True,
                "file_edits_allowed": True,
            },
        )

        result = run_model_fixture(request_path, output_dir)
        failure_text = result.failure_bundle_path.read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertNotIn("dummy-test-value", failure_text)


if __name__ == "__main__":
    unittest.main()
