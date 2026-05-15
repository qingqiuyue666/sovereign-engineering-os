import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_provider_boundary import (
    write_model_provider_admission_artifacts,
)
from kernel.personal_ai.adapters.model_provider_runtime import (
    build_optional_live_smoke_status,
    run_model_provider_runtime,
)
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    write_model_provider_request,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import RuntimeAdmissionDecision


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ModelProviderRuntimeTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_path = root / "input.json"
        write_json_atomically(
            input_path,
            {
                "route_type": "spreadsheet_review",
                "recommended_processor_lane": "human_review_only",
            },
        )
        return root, input_path

    def test_mock_provider_runtime_writes_result_manifest_without_network(self):
        root, input_path = self.make_root()
        request_path = root / "mock_request.json"
        output_dir = root / "mock-output"
        output_dir.mkdir()
        write_model_provider_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )

        result = run_model_provider_runtime(request_path, output_dir)
        manifest = read_json(result.result_manifest_path)

        self.assertTrue(result.success)
        self.assertFalse(result.live_provider_called)
        self.assertTrue(result.inference_artifact_path.exists())
        self.assertEqual(manifest["provider"], "deterministic_mock")
        self.assertFalse(manifest["live_provider_called"])
        self.assertFalse(manifest["network_used"])
        self.assertFalse(manifest["api_key_persisted"])
        self.assertFalse(manifest["model_output_can_call_tools"])

    def test_live_provider_dry_run_requires_admission_and_persists_no_key(self):
        root, input_path = self.make_root()
        request_path = root / "live_request.json"
        output_dir = root / "live-output"
        output_dir.mkdir()
        write_model_provider_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
            provider="openai",
        )
        artifacts = write_model_provider_admission_artifacts(
            root,
            provider_id="openai",
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )

        result = run_model_provider_runtime(
            request_path,
            output_dir,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
            environ={"OPENAI_API_KEY": "SHOULD_NOT_BE_PERSISTED"},
        )
        manifest_text = result.result_manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
        dry_run_plan = read_json(result.dry_run_plan_path)

        self.assertTrue(result.success)
        self.assertFalse(result.live_provider_called)
        self.assertTrue(manifest["runtime_admission_decision"]["admitted"])
        self.assertFalse(manifest["live_provider_called"])
        self.assertFalse(manifest["network_used"])
        self.assertTrue(manifest["api_key_present"])
        self.assertFalse(manifest["api_key_persisted"])
        self.assertFalse(manifest["api_key_logged"])
        self.assertFalse(dry_run_plan["network_call_performed"])
        self.assertNotIn("SHOULD_NOT_BE_PERSISTED", manifest_text)

    def test_live_provider_without_admission_is_quarantined(self):
        root, input_path = self.make_root()
        request_path = root / "live_request.json"
        output_dir = root / "live-denied"
        output_dir.mkdir()
        write_model_provider_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
            provider="openai",
        )

        result = run_model_provider_runtime(request_path, output_dir)
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["live_provider_called"])
        self.assertFalse(failure["network_used"])
        self.assertFalse(failure["api_key_persisted"])
        self.assertIn("admission denied", failure["error_message"])

    def test_invalid_mock_output_uses_existing_failure_quarantine(self):
        root, input_path = self.make_root()
        request_path = root / "bad_mock_request.json"
        output_dir = root / "bad-mock"
        output_dir.mkdir()
        write_model_provider_request(
            input_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        request = read_json(request_path)
        request["fixture_response"] = {
            "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
            "authority": "non_authority",
            "can_grant_authority": True,
            "can_edit_files": False,
            "can_call_tools": False,
        }
        write_json_atomically(request_path, request)

        result = run_model_provider_runtime(request_path, output_dir)
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertTrue(failure["invalid_output_quarantined"])
        self.assertFalse(failure["network_used"])

    def test_optional_live_smoke_stays_disabled_without_activation_allowed(self):
        decision = RuntimeAdmissionDecision(
            decision_type="personal_ai_runtime_admission_decision_v1",
            adapter_id="live_model_provider_boundary",
            capability="call_typed_schema_provider",
            runtime_class="live_model_provider",
            admitted=True,
            activation_allowed=False,
            dry_run=True,
            reason_codes=(),
            artifact_hashes={},
            manifest_hash_bound=True,
            runtime_class_policy={},
            activation_sources=("human_approval_artifact",),
        )

        status = build_optional_live_smoke_status(
            "openai",
            decision,
            environ={
                "SEOS_ENABLE_LIVE_MODEL_SMOKE": "true",
                "OPENAI_API_KEY": "SHOULD_NOT_BE_PERSISTED",
            },
        )

        self.assertFalse(status["enabled"])
        self.assertTrue(status["api_key_present"])
        self.assertFalse(status["api_key_value_persisted"])
        self.assertFalse(status["live_call_performed"])


if __name__ == "__main__":
    unittest.main()
