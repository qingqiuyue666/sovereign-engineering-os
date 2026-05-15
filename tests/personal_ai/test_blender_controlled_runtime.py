import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_controlled_runtime import (
    run_blender_controlled_fixture,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BlenderControlledRuntimeTests(unittest.TestCase):
    def build_workspace(self, plan=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "output"
        package_root = root / "packages"
        output_dir.mkdir()
        package_root.mkdir()
        scene_path = root / "scene.blend"
        scene_path.write_bytes(b"BLENDER_SCENE_SENTINEL_BYTES")
        plan_path = root / "operation_plan.json"
        write_json_atomically(plan_path, plan or self.safe_plan())
        return root, scene_path, plan_path, output_dir, package_root

    def safe_plan(self):
        return {
            "operations": [
                {
                    "operation": "create_collection",
                    "parameters": {"name": "fixture_collection"},
                },
                {
                    "operation": "add_mesh_primitive",
                    "parameters": {"primitive": "cube", "name": "fixture_cube"},
                },
                {
                    "operation": "render_preview",
                    "parameters": {"view": "camera", "samples": 8},
                },
            ]
        }

    def test_runs_local_fixture_contract_and_writes_hash_bound_evidence(self):
        _, scene_path, plan_path, output_dir, package_root = self.build_workspace()

        result = run_blender_controlled_fixture(
            scene_path,
            plan_path,
            output_dir,
        )
        manifest = read_json(result.output_manifest_path)
        evidence = read_json(result.preview_evidence_path)
        manifest_text = result.output_manifest_path.read_text(encoding="utf-8")
        evidence_text = result.preview_evidence_path.read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertFalse(manifest["runtime_admitted"])
        self.assertFalse(manifest["real_blender_runtime_called"])
        self.assertFalse(evidence["real_blender_runtime_called"])
        self.assertFalse(evidence["arbitrary_python_execution_performed"])
        self.assertEqual(manifest["scene_sha256"], sha256_file(scene_path))
        self.assertEqual(manifest["operation_plan_sha256"], sha256_file(plan_path))
        self.assertNotIn("BLENDER_SCENE_SENTINEL_BYTES", manifest_text)
        self.assertNotIn("BLENDER_SCENE_SENTINEL_BYTES", evidence_text)

        delivery = build_runtime_delivery_package(
            output_dir,
            package_root,
            package_id="blender-delivery",
        )
        self.assertIn("blender_output_manifest", delivery.packaged_artifacts)
        self.assertIn("blender_preview_evidence", delivery.packaged_artifacts)

    def test_rejects_arbitrary_python_execution_and_writes_failure_quarantine(self):
        _, scene_path, plan_path, output_dir, _ = self.build_workspace(
            {
                "operations": [
                    {
                        "operation": "add_mesh_primitive",
                        "parameters": {"python": "import bpy; exec('bad')"},
                    }
                ]
            }
        )

        result = run_blender_controlled_fixture(scene_path, plan_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("forbidden runtime token", failure["error_message"])
        self.assertFalse(failure["real_blender_runtime_called"])
        self.assertFalse(failure["arbitrary_python_execution_performed"])
        self.assertFalse(failure["subprocess_execution_performed"])

    def test_rejects_unallowlisted_operations(self):
        _, scene_path, plan_path, output_dir, _ = self.build_workspace(
            {"operations": [{"operation": "run_python", "parameters": {}}]}
        )

        result = run_blender_controlled_fixture(scene_path, plan_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("not allowed", failure["error_message"])

    def test_rejects_source_scene_overwrite_path(self):
        root, scene_path, plan_path, output_dir, _ = self.build_workspace(
            {
                "operations": [
                    {
                        "operation": "export_glb_preview",
                        "parameters": {"target_path": ""},
                    }
                ]
            }
        )
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

        result = run_blender_controlled_fixture(scene_path, plan_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertEqual(root, scene_path.parent)
        self.assertFalse(result.success)
        self.assertIn("must not overwrite source scene", failure["error_message"])
        self.assertFalse(failure["source_asset_overwrite_performed"])

    def test_rejects_symlink_scene(self):
        root, scene_path, plan_path, output_dir, _ = self.build_workspace()
        link_path = root / "scene_link.blend"
        link_path.symlink_to(scene_path)

        result = run_blender_controlled_fixture(link_path, plan_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("must not be a symlink", failure["error_message"])

    def test_refuses_output_overwrite(self):
        _, scene_path, plan_path, output_dir, _ = self.build_workspace()
        (output_dir / "blender_output_manifest.json").write_text(
            "{}",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            run_blender_controlled_fixture(scene_path, plan_path, output_dir)


if __name__ == "__main__":
    unittest.main()
