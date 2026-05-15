import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.comfyui_runtime import run_comfyui_runtime
from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    write_comfyui_runtime_admission_artifacts,
)
from kernel.personal_ai.io_utils import write_json_atomically


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ComfyUIRuntimeTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        workflow_path = root / "workflow.json"
        asset_path = root / "asset.png"
        asset_path.write_bytes(b"COMFYUI_ASSET")
        write_json_atomically(
            workflow_path,
            {
                "nodes": [
                    {"id": "load", "type": "LoadImage", "inputs": {"image": "asset.png"}},
                    {"id": "preview", "type": "PreviewImage", "inputs": {"source": "load"}},
                ]
            },
        )
        endpoint_config_path = root / "endpoint.json"
        write_json_atomically(
            endpoint_config_path,
            {
                "endpoint": "http://127.0.0.1:8188",
                "enable_real_endpoint": False,
            },
        )
        return root, workflow_path, asset_path, endpoint_config_path

    def test_fixture_runtime_writes_result_manifest_without_endpoint_call(self):
        root, workflow_path, asset_path, _ = self.make_root()
        output_dir = root / "fixture-output"
        output_dir.mkdir()

        result = run_comfyui_runtime(
            workflow_path,
            output_dir,
            input_asset_paths=(asset_path,),
        )
        manifest = read_json(result.result_manifest_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_endpoint_called)
        self.assertTrue(result.output_manifest_path.exists())
        self.assertTrue(result.preview_evidence_path.exists())
        self.assertFalse(manifest["real_comfyui_endpoint_called"])
        self.assertFalse(manifest["network_used"])
        self.assertFalse(manifest["external_downloads_performed"])

    def test_endpoint_dry_run_requires_admission_and_calls_no_endpoint(self):
        root, workflow_path, asset_path, endpoint_config_path = self.make_root()
        output_dir = root / "endpoint-dry-run"
        output_dir.mkdir()
        artifacts = write_comfyui_runtime_admission_artifacts(root)

        result = run_comfyui_runtime(
            workflow_path,
            output_dir,
            input_asset_paths=(asset_path,),
            endpoint_config_path=endpoint_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        manifest = read_json(result.result_manifest_path)
        dry_run_plan = read_json(result.dry_run_plan_path)

        self.assertTrue(result.success)
        self.assertFalse(result.real_endpoint_called)
        self.assertTrue(manifest["runtime_admission_decision"]["admitted"])
        self.assertFalse(manifest["real_comfyui_endpoint_called"])
        self.assertFalse(manifest["network_used"])
        self.assertFalse(dry_run_plan["network_call_performed"])
        self.assertFalse(dry_run_plan["external_downloads_performed"])
        self.assertFalse(dry_run_plan["arbitrary_node_execution_performed"])

    def test_external_endpoint_is_quarantined_without_network_call(self):
        root, workflow_path, _, _ = self.make_root()
        output_dir = root / "external-denied"
        output_dir.mkdir()
        endpoint_config_path = root / "external_endpoint.json"
        write_json_atomically(
            endpoint_config_path,
            {"endpoint": "https://example.com:8188", "enable_real_endpoint": False},
        )
        artifacts = write_comfyui_runtime_admission_artifacts(root)

        result = run_comfyui_runtime(
            workflow_path,
            output_dir,
            endpoint_config_path=endpoint_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_comfyui_endpoint_called"])
        self.assertFalse(failure["network_used"])
        self.assertIn("loopback", failure["error_message"])

    def test_enable_real_endpoint_true_is_quarantined(self):
        root, workflow_path, _, _ = self.make_root()
        output_dir = root / "real-enabled-denied"
        output_dir.mkdir()
        endpoint_config_path = root / "enabled_endpoint.json"
        write_json_atomically(
            endpoint_config_path,
            {"endpoint": "http://localhost:8188", "enable_real_endpoint": True},
        )
        artifacts = write_comfyui_runtime_admission_artifacts(root)

        result = run_comfyui_runtime(
            workflow_path,
            output_dir,
            endpoint_config_path=endpoint_config_path,
            admission_config_path=artifacts.config_path,
            admission_approval_path=artifacts.human_approval_path,
            admission_manifest_path=artifacts.manifest_path,
        )
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_comfyui_endpoint_called"])
        self.assertIn("not admitted", failure["error_message"])

    def test_forbidden_workflow_node_uses_failure_bundle(self):
        root, workflow_path, _, _ = self.make_root()
        output_dir = root / "bad-workflow"
        output_dir.mkdir()
        write_json_atomically(
            workflow_path,
            {"nodes": [{"id": "bad", "type": "PythonScript", "inputs": {}}]},
        )

        result = run_comfyui_runtime(workflow_path, output_dir)
        failure = read_json(result.failure_quarantine_path)

        self.assertFalse(result.success)
        self.assertFalse(failure["real_comfyui_endpoint_called"])
        self.assertIn("not allowed", failure["error_message"])


if __name__ == "__main__":
    unittest.main()
