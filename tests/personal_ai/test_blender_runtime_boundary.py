import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_runtime_boundary import (
    boundary_for_blender_runtime,
    build_blender_runtime_boundaries,
    validate_blender_runtime_boundary,
    write_blender_runtime_admission_artifacts,
)
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BlenderRuntimeBoundaryTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_boundaries_keep_fixture_default_and_real_blender_disabled(self):
        boundaries = {
            boundary.runtime_id: boundary
            for boundary in build_blender_runtime_boundaries()
        }

        self.assertIn("blender_operation_fixture", boundaries)
        self.assertIn("blender_real_runtime_boundary", boundaries)
        self.assertEqual(
            validate_blender_runtime_boundary(boundaries["blender_operation_fixture"]),
            (),
        )
        self.assertEqual(
            validate_blender_runtime_boundary(boundaries["blender_real_runtime_boundary"]),
            (),
        )
        self.assertTrue(boundaries["blender_operation_fixture"].enabled_by_default)
        self.assertFalse(boundaries["blender_real_runtime_boundary"].enabled_by_default)
        self.assertTrue(boundaries["blender_real_runtime_boundary"].real_blender_runtime)

    def test_real_blender_admission_artifacts_are_hash_bound_dry_run_only(self):
        root = self.make_root()

        artifacts = write_blender_runtime_admission_artifacts(root)
        config = read_json(artifacts.config_path)
        approval = read_json(artifacts.human_approval_path)
        manifest = read_json(artifacts.manifest_path)
        boundary = boundary_for_blender_runtime("blender_real_runtime_boundary")

        self.assertEqual(approval["config_sha256"], artifacts.config_sha256)
        self.assertEqual(approval["manifest_sha256"], artifacts.manifest_sha256)
        self.assertEqual(manifest["config_sha256"], artifacts.config_sha256)
        self.assertFalse(config["real_runtime_enabled"])
        self.assertFalse(config["arbitrary_python_allowed"])
        self.assertFalse(config["subprocess_launch_allowed"])
        self.assertFalse(config["source_asset_overwrite_allowed"])

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

    def test_real_blender_activation_without_dry_run_is_not_admitted(self):
        root = self.make_root()
        artifacts = write_blender_runtime_admission_artifacts(root, dry_run=False)
        boundary = boundary_for_blender_runtime("blender_real_runtime_boundary")

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

        self.assertFalse(decision.admitted)
        self.assertFalse(decision.activation_allowed)
        self.assertIn(
            "runtime_class_not_activation_admitted",
            decision.reason_codes,
        )


if __name__ == "__main__":
    unittest.main()
