import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    boundary_for_comfyui_runtime,
    build_comfyui_runtime_boundaries,
    validate_comfyui_runtime_boundary,
    write_comfyui_runtime_admission_artifacts,
)
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ComfyUIRuntimeBoundaryTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_boundaries_keep_fixture_default_and_endpoint_disabled(self):
        boundaries = {
            boundary.runtime_id: boundary
            for boundary in build_comfyui_runtime_boundaries()
        }

        self.assertIn("comfyui_workflow_fixture", boundaries)
        self.assertIn("comfyui_local_endpoint_boundary", boundaries)
        self.assertEqual(
            validate_comfyui_runtime_boundary(boundaries["comfyui_workflow_fixture"]),
            (),
        )
        self.assertEqual(
            validate_comfyui_runtime_boundary(
                boundaries["comfyui_local_endpoint_boundary"]
            ),
            (),
        )
        self.assertTrue(boundaries["comfyui_workflow_fixture"].enabled_by_default)
        self.assertFalse(
            boundaries["comfyui_local_endpoint_boundary"].enabled_by_default
        )
        self.assertTrue(
            boundaries["comfyui_local_endpoint_boundary"].local_endpoint_runtime
        )

    def test_endpoint_admission_artifacts_are_hash_bound_dry_run_only(self):
        root = self.make_root()

        artifacts = write_comfyui_runtime_admission_artifacts(root)
        config = read_json(artifacts.config_path)
        approval = read_json(artifacts.human_approval_path)
        manifest = read_json(artifacts.manifest_path)
        boundary = boundary_for_comfyui_runtime("comfyui_local_endpoint_boundary")

        self.assertEqual(approval["config_sha256"], artifacts.config_sha256)
        self.assertEqual(approval["manifest_sha256"], artifacts.manifest_sha256)
        self.assertEqual(manifest["config_sha256"], artifacts.config_sha256)
        self.assertFalse(config["real_runtime_enabled"])
        self.assertTrue(config["loopback_only"])
        self.assertFalse(config["external_downloads_allowed"])
        self.assertFalse(config["arbitrary_nodes_allowed"])

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

    def test_non_loopback_endpoint_config_is_rejected(self):
        root = self.make_root()

        with self.assertRaisesRegex(ValueError, "loopback"):
            write_comfyui_runtime_admission_artifacts(
                root,
                endpoint="https://example.com:8188",
            )


if __name__ == "__main__":
    unittest.main()
