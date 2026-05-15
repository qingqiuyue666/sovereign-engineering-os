import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_runtime import run_blender_runtime
from kernel.personal_ai.adapters.blender_runtime_boundary import (
    write_blender_runtime_admission_artifacts,
)
from kernel.personal_ai.io_utils import write_json_atomically


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BlenderRuntimeTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        scene_path = root / "scene.blend"
        scene_path.write_bytes(b"BLENDER_SCENE")
        plan_path = root / "plan.json"
        write_json_atomically(
            plan_path,
            {
                "operations": [
                    {"operation": "add_camera", "parameters": {"name": "Camera"}},
                    {"operation": "render_preview", "parameters": {"samples": 16}},
                ]
            },
        )
        blender_config_path = root / "blender_config.json"
        write_json_atomically(
            blender_config_path,
            {
                "blender_executable": "/Applications/Blender.app",
                "enable_real_blender": False,
                "allow_subprocess": False,
                "allow_arbitrary_python": False,
            },
        )
        return root, scene_path, plan_path, blender_config_path

    def test_fixture_runtime_writes_result_manifest_without_blender_call(self):
        root, scene_path, plan_path, _ = self.make_root()
        output_dir = root / "fixture-output"
        output_dir.mkdir()

        result = run_blender_runtime(scene_path, plan_path, output_dir)
        manifest = read_json(result.result_manifest_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_blender_called)
        self.assertTrue(result.output_manifest_path.exists())
        self.assertTrue(result.preview_evidence_path.exists())
        self.assertFalse(manifest["real_blender_runtime_called"])
        self.assertFalse(manifest["subprocess_execution_performed"])
        self.assertFalse(manifest["arbitrary_python_execution_performed"])

    def test_real_blender_dry_run_requires_admission_and_launches_no_subprocess(self):
        root, scene_path, plan_path, blender_config_path = self.make_root()
        output_dir = root / "blender-dry-run"
        output_dir.mkdir()
        artifacts = write_blender_runtime_admission_artifacts(root)

        result = run_blender_runtime(
            scene_path,
            plan_path,
            output_dir,
            blender_config_path=blender_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        manifest = read_json(result.result_manifest_path)
        dry_run_plan = read_json(result.dry_run_plan_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_blender_called)
        self.assertTrue(manifest["runtime_admission_decision"]["admitted"])
        self.assertFalse(manifest["real_blender_runtime_called"])
        self.assertFalse(manifest["subprocess_execution_performed"])
        self.assertFalse(manifest["arbitrary_python_execution_performed"])
        self.assertFalse(dry_run_plan["real_blender_runtime_called"])
        self.assertFalse(dry_run_plan["subprocess_execution_performed"])

    def test_enable_real_blender_true_is_quarantined(self):
        root, scene_path, plan_path, blender_config_path = self.make_root()
        output_dir = root / "enabled-denied"
        output_dir.mkdir()
        write_json_atomically(
            blender_config_path,
            {
                "blender_executable": "/Applications/Blender.app",
                "enable_real_blender": True,
                "allow_subprocess": False,
                "allow_arbitrary_python": False,
            },
        )
        artifacts = write_blender_runtime_admission_artifacts(root)

        result = run_blender_runtime(
            scene_path,
            plan_path,
            output_dir,
            blender_config_path=blender_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_blender_runtime_called"])
        self.assertFalse(failure["subprocess_execution_performed"])
        self.assertIn("not admitted", failure["error_message"])

    def test_arbitrary_python_config_is_quarantined(self):
        root, scene_path, plan_path, blender_config_path = self.make_root()
        output_dir = root / "python-denied"
        output_dir.mkdir()
        write_json_atomically(
            blender_config_path,
            {
                "enable_real_blender": False,
                "allow_subprocess": False,
                "allow_arbitrary_python": True,
            },
        )
        artifacts = write_blender_runtime_admission_artifacts(root)

        result = run_blender_runtime(
            scene_path,
            plan_path,
            output_dir,
            blender_config_path=blender_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["arbitrary_python_execution_performed"])
        self.assertIn("arbitrary Blender Python", failure["error_message"])

    def test_source_scene_overwrite_plan_uses_failure_bundle(self):
        root, scene_path, plan_path, _ = self.make_root()
        output_dir = root / "overwrite-denied"
        output_dir.mkdir()
        write_json_atomically(
            plan_path,
            {
                "operations": [
                    {
                        "operation": "export_glb_preview",
                        "parameters": {"target_path": scene_path.as_posix()},
                    }
                ]
            },
        )

        result = run_blender_runtime(scene_path, plan_path, output_dir)
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_blender_runtime_called"])
        self.assertFalse(failure["source_asset_overwrite_performed"])
        self.assertIn("overwrite source scene", failure["error_message"])


if __name__ == "__main__":
    unittest.main()
