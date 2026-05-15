import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_provider_activation_package import (
    build_model_provider_activation_package,
    validate_model_provider_activation_package,
)


class ModelProviderActivationPackageTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_builds_controlled_activation_package_without_live_call(self):
        output_dir = self.make_output_dir()

        result = build_model_provider_activation_package(
            output_dir,
            provider_id="openai",
            schema_name="job_route_classification_v1",
            reviewer_id="reviewer-1",
            environ={"OPENAI_API_KEY": "present-but-not-persisted"},
        )

        self.assertTrue(result.complete)
        self.assertFalse(result.live_provider_called)
        self.assertFalse(result.network_used)
        plan = json.loads(result.activation_plan_path.read_text(encoding="utf-8"))
        validation = json.loads(result.validation_path.read_text(encoding="utf-8"))
        self.assertEqual(
            plan["package_type"],
            "personal_ai_model_provider_controlled_activation_package_v1",
        )
        self.assertFalse(plan["activation_enabled"])
        self.assertTrue(plan["dry_run_only"])
        self.assertFalse(plan["network_call_allowed"])
        self.assertFalse(plan["network_call_performed"])
        self.assertFalse(plan["live_provider_call_performed"])
        self.assertFalse(plan["api_key_value_persisted"])
        self.assertFalse(plan["api_key_value_logged"])
        self.assertNotIn("present-but-not-persisted", result.activation_plan_path.read_text(encoding="utf-8"))
        self.assertTrue(plan["api_key_present"])
        self.assertTrue(plan["runtime_admission_decision"]["admitted"])
        self.assertFalse(plan["runtime_admission_decision"]["activation_allowed"])
        self.assertTrue(validation["complete"])
        self.assertFalse(validation["live_provider_called"])
        self.assertFalse(validation["network_used"])

    def test_rejects_mock_provider_for_activation_package(self):
        output_dir = self.make_output_dir()

        with self.assertRaisesRegex(ValueError, "only for live provider"):
            build_model_provider_activation_package(
                output_dir,
                provider_id="deterministic_mock",
                schema_name="job_route_classification_v1",
                reviewer_id="reviewer-1",
            )

    def test_requires_reviewer_id(self):
        output_dir = self.make_output_dir()

        with self.assertRaisesRegex(ValueError, "reviewer_id is required"):
            build_model_provider_activation_package(
                output_dir,
                provider_id="openai",
                schema_name="job_route_classification_v1",
                reviewer_id=" ",
            )

    def test_validate_detects_tampered_activation_plan(self):
        output_dir = self.make_output_dir()
        result = build_model_provider_activation_package(
            output_dir,
            provider_id="openai",
            schema_name="job_route_classification_v1",
            reviewer_id="reviewer-1",
        )
        plan = json.loads(result.activation_plan_path.read_text(encoding="utf-8"))
        plan["network_call_allowed"] = True
        result.activation_plan_path.write_text(json.dumps(plan), encoding="utf-8")

        validation = validate_model_provider_activation_package(output_dir)

        self.assertFalse(validation["complete"])
        self.assertIn("network_call_allowed_must_be_false", validation["failures"])

    def test_validation_output_refuses_overwrite(self):
        output_dir = self.make_output_dir()
        result = build_model_provider_activation_package(
            output_dir,
            provider_id="openai",
            schema_name="job_route_classification_v1",
            reviewer_id="reviewer-1",
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            validate_model_provider_activation_package(
                output_dir,
                result.validation_path,
            )


if __name__ == "__main__":
    unittest.main()
