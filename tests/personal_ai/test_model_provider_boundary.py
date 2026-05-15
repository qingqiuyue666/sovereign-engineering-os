import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_provider_boundary import (
    boundary_for_provider,
    build_model_provider_boundaries,
    validate_model_provider_boundary,
    write_model_provider_admission_artifacts,
)
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ModelProviderBoundaryTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_provider_boundaries_keep_mock_default_and_live_disabled(self):
        boundaries = {
            boundary.provider_id: boundary
            for boundary in build_model_provider_boundaries()
        }

        self.assertIn("deterministic_mock", boundaries)
        self.assertIn("openai", boundaries)
        self.assertEqual(
            validate_model_provider_boundary(boundaries["deterministic_mock"]),
            (),
        )
        self.assertEqual(validate_model_provider_boundary(boundaries["openai"]), ())
        self.assertTrue(boundaries["deterministic_mock"].default_provider)
        self.assertTrue(boundaries["deterministic_mock"].enabled_by_default)
        self.assertFalse(boundaries["deterministic_mock"].live_provider_runtime)
        self.assertFalse(boundaries["openai"].enabled_by_default)
        self.assertFalse(boundaries["openai"].admitted_by_default)
        self.assertTrue(boundaries["openai"].live_provider_runtime)
        self.assertEqual(boundaries["openai"].api_key_env_var, "OPENAI_API_KEY")

    def test_live_provider_admission_artifacts_are_hash_bound_dry_run_only(self):
        root = self.make_root()

        artifacts = write_model_provider_admission_artifacts(
            root,
            provider_id="openai",
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        config = read_json(artifacts.config_path)
        approval = read_json(artifacts.human_approval_path)
        manifest = read_json(artifacts.manifest_path)
        boundary = boundary_for_provider("openai")

        self.assertEqual(approval["config_sha256"], artifacts.config_sha256)
        self.assertEqual(approval["manifest_sha256"], artifacts.manifest_sha256)
        self.assertEqual(manifest["config_sha256"], artifacts.config_sha256)
        self.assertFalse(config["real_runtime_enabled"])
        self.assertFalse(config["api_key_persisted"])
        self.assertFalse(config["api_key_logged"])
        self.assertNotIn("SHOULD_NOT_APPEAR", artifacts.config_path.read_text())

        decision = evaluate_runtime_admission(
            RuntimeAdmissionRequest(
                adapter_id=boundary.adapter_id,
                capability=boundary.capability,
                runtime_class=boundary.runtime_class,
                config_artifact_path=artifacts.config_path,
                human_approval_artifact_path=artifacts.human_approval_path,
                manifest_artifact_path=artifacts.manifest_path,
                dry_run=True,
                activation_sources=("human_approval_artifact",),
            )
        )

        self.assertTrue(decision.admitted)
        self.assertFalse(decision.activation_allowed)
        self.assertEqual(decision.reason_codes, ())

    def test_mock_provider_admission_artifacts_can_admit_local_activation(self):
        root = self.make_root()

        artifacts = write_model_provider_admission_artifacts(
            root,
            provider_id="deterministic_mock",
            schema_name=ModelFixtureSchema.NEXT_STEP_RECOMMENDATION,
            dry_run=False,
        )
        boundary = boundary_for_provider("deterministic_mock")
        decision = evaluate_runtime_admission(
            RuntimeAdmissionRequest(
                adapter_id=boundary.adapter_id,
                capability=boundary.capability,
                runtime_class=boundary.runtime_class,
                config_artifact_path=artifacts.config_path,
                human_approval_artifact_path=artifacts.human_approval_path,
                manifest_artifact_path=artifacts.manifest_path,
                dry_run=False,
                activation_sources=("human_approval_artifact",),
            )
        )

        self.assertTrue(decision.admitted)
        self.assertTrue(decision.activation_allowed)


if __name__ == "__main__":
    unittest.main()
