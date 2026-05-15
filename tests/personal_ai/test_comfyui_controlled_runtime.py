import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.comfyui_controlled_runtime import (
    run_comfyui_controlled_fixture,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ComfyUIControlledRuntimeTests(unittest.TestCase):
    def build_workspace(self, workflow=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "output"
        package_root = root / "packages"
        output_dir.mkdir()
        package_root.mkdir()
        workflow_path = root / "workflow.json"
        write_json_atomically(workflow_path, workflow or self.safe_workflow())
        asset_path = root / "asset.png"
        asset_path.write_bytes(b"RAW_ASSET_SENTINEL_BYTES")
        return root, workflow_path, asset_path, output_dir, package_root

    def safe_workflow(self):
        return {
            "nodes": [
                {"id": "load", "type": "LoadImage", "inputs": {"image": "asset.png"}},
                {"id": "preview", "type": "PreviewImage", "inputs": {"source": "load"}},
                {"id": "save", "type": "SaveImage", "inputs": {"source": "preview"}},
            ]
        }

    def test_runs_local_fixture_contract_and_writes_hash_bound_evidence(self):
        _, workflow_path, asset_path, output_dir, package_root = self.build_workspace()

        result = run_comfyui_controlled_fixture(
            workflow_path,
            output_dir,
            input_asset_paths=(asset_path,),
        )
        manifest = read_json(result.output_manifest_path)
        evidence = read_json(result.preview_evidence_path)
        manifest_text = result.output_manifest_path.read_text(encoding="utf-8")
        evidence_text = result.preview_evidence_path.read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertFalse(manifest["runtime_admitted"])
        self.assertFalse(manifest["real_comfyui_endpoint_called"])
        self.assertFalse(evidence["real_comfyui_endpoint_called"])
        self.assertEqual(manifest["workflow_sha256"], sha256_file(workflow_path))
        self.assertEqual(
            manifest["input_assets"][0]["sha256"],
            sha256_file(asset_path),
        )
        self.assertNotIn("RAW_ASSET_SENTINEL_BYTES", manifest_text)
        self.assertNotIn("RAW_ASSET_SENTINEL_BYTES", evidence_text)

        delivery = build_runtime_delivery_package(
            output_dir,
            package_root,
            package_id="comfyui-delivery",
        )
        self.assertIn("comfyui_output_manifest", delivery.packaged_artifacts)
        self.assertIn("comfyui_preview_evidence", delivery.packaged_artifacts)

    def test_rejects_forbidden_nodes_and_writes_failure_quarantine(self):
        _, workflow_path, _, output_dir, _ = self.build_workspace(
            {
                "nodes": [
                    {
                        "id": "bad",
                        "type": "PythonScript",
                        "inputs": {"code": "print(1)"},
                    }
                ]
            }
        )

        result = run_comfyui_controlled_fixture(workflow_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("not allowed", failure["error_message"])
        self.assertFalse(failure["real_comfyui_endpoint_called"])
        self.assertFalse(failure["arbitrary_node_execution_performed"])

    def test_rejects_external_download_inputs(self):
        _, workflow_path, _, output_dir, _ = self.build_workspace(
            {
                "nodes": [
                    {
                        "id": "load",
                        "type": "LoadImage",
                        "inputs": {"image_url": "https://example.test/asset.png"},
                    }
                ]
            }
        )

        result = run_comfyui_controlled_fixture(workflow_path, output_dir)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("forbidden", failure["error_message"])
        self.assertFalse(failure["external_downloads_performed"])

    def test_real_endpoint_config_is_loopback_only_and_still_deferred(self):
        root, workflow_path, _, output_dir, _ = self.build_workspace()
        endpoint_path = root / "endpoint.json"
        write_json_atomically(
            endpoint_path,
            {
                "endpoint": "http://127.0.0.1:8188",
                "enable_real_endpoint": True,
            },
        )

        result = run_comfyui_controlled_fixture(
            workflow_path,
            output_dir,
            endpoint_config_path=endpoint_path,
        )
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("not admitted", failure["error_message"])
        self.assertFalse(failure["real_comfyui_endpoint_called"])

    def test_refuses_output_overwrite(self):
        _, workflow_path, _, output_dir, _ = self.build_workspace()
        (output_dir / "comfyui_output_manifest.json").write_text(
            "{}",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            run_comfyui_controlled_fixture(workflow_path, output_dir)


if __name__ == "__main__":
    unittest.main()
