import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_playwright_real_package_admission import (
    build_browser_playwright_real_package_admission,
)
from kernel.personal_ai.real_runtime_smoke_execution_batch import (
    run_real_runtime_smoke_execution_batch,
)


class RealRuntimeSmokeExecutionBatchTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_json(self, path: Path, payload: dict) -> Path:
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_batch_denies_by_default_without_any_runtime_entry(self):
        root = self.make_output_dir()

        result = run_real_runtime_smoke_execution_batch(output_dir=root)

        self.assertEqual(result.status, "disabled_by_callsite")
        self.assertFalse(result.real_model_smoke_entry_called)
        self.assertFalse(result.real_browser_smoke_entry_called)
        self.assertFalse(result.real_comfyui_smoke_entry_called)
        self.assertFalse(result.real_blender_smoke_entry_called)
        self.assertFalse(result.creative_software_auto_control_called)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["default_live_execution_enabled"])
        self.assertFalse(payload["secrets_persisted"])
        self.assertFalse(payload["arbitrary_subprocess_allowed"])

    def test_batch_denies_without_environment_flag(self):
        root = self.make_output_dir()

        result = run_real_runtime_smoke_execution_batch(
            output_dir=root,
            allow_batch=True,
        )

        self.assertEqual(result.status, "disabled_by_environment_flag")
        self.assertFalse(result.real_model_smoke_entry_called)

    def test_batch_requires_artifacts_for_enabled_entries(self):
        root = self.make_output_dir()

        result = run_real_runtime_smoke_execution_batch(
            output_dir=root,
            environ={"SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH": "true"},
            allow_batch=True,
            allow_browser_smoke=True,
        )

        self.assertEqual(result.status, "failed_closed")
        self.assertIsNotNone(result.failure_path)
        payload = json.loads(result.failure_path.read_text(encoding="utf-8"))
        self.assertIn("browser_admission_path", payload["reason"])

    def test_batch_requires_preexisting_output_directory(self):
        root = self.make_output_dir()

        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            run_real_runtime_smoke_execution_batch(output_dir=root / "missing-run-dir")

    def test_batch_runs_fake_browser_comfyui_and_blender_entries_after_gates(self):
        root = self.make_output_dir()
        admission_dir = root / "admission"
        admission_dir.mkdir()
        admission = build_browser_playwright_real_package_admission(admission_dir)
        workflow = self.write_json(
            root / "workflow.json",
            {"nodes": [{"id": "1", "type": "LoadImage"}, {"id": "2", "type": "KSampler"}]},
        )
        scene = root / "scene.blend"
        scene.write_bytes(b"fake-blender-scene")
        operation_plan = self.write_json(
            root / "operations.json",
            {"operations": [{"operation": "add_camera"}]},
        )
        calls = {"browser": 0, "comfyui": 0, "blender": 0}

        def browser_transport(request):
            calls["browser"] += 1
            self.assertTrue(request["loopback_only"])
            self.assertFalse(request["external_network_allowed"])
            self.assertFalse(request["real_user_profile_allowed"])
            return {"status": "ok"}

        def comfyui_transport(request):
            calls["comfyui"] += 1
            self.assertTrue(request["loopback_only"])
            self.assertFalse(request["external_network_allowed"])
            self.assertFalse(request["arbitrary_node_execution_allowed"])
            return {"status": "ok"}

        def blender_transport(request):
            calls["blender"] += 1
            self.assertFalse(request["subprocess_allowed"])
            self.assertFalse(request["arbitrary_python_allowed"])
            self.assertFalse(request["external_network_allowed"])
            return {"status": "ok"}

        run_dir = root / "run"
        run_dir.mkdir()
        result = run_real_runtime_smoke_execution_batch(
            output_dir=run_dir,
            environ={"SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH": "true"},
            allow_batch=True,
            browser_admission_path=admission.admission_path,
            allow_browser_smoke=True,
            browser_transport=browser_transport,
            comfyui_workflow_path=workflow,
            allow_comfyui_smoke=True,
            comfyui_transport=comfyui_transport,
            blender_scene_path=scene,
            blender_operation_plan_path=operation_plan,
            allow_blender_smoke=True,
            blender_transport=blender_transport,
        )

        self.assertEqual(result.status, "completed_with_manual_runtime_smoke_entries")
        self.assertTrue(result.real_browser_smoke_entry_called)
        self.assertTrue(result.real_comfyui_smoke_entry_called)
        self.assertTrue(result.real_blender_smoke_entry_called)
        self.assertFalse(result.real_model_smoke_entry_called)
        self.assertFalse(result.creative_software_auto_control_called)
        self.assertEqual(calls, {"browser": 1, "comfyui": 1, "blender": 1})
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["default_live_execution_enabled"])
        self.assertFalse(payload["secrets_persisted"])
        self.assertFalse(payload["external_network_allowed_by_default"])
        self.assertFalse(payload["arbitrary_subprocess_allowed"])
        self.assertFalse(payload["output_triggered_tool_or_file_authority"])
        self.assertFalse(payload["creative_tools"]["ae_auto_control_called"])
        self.assertFalse(payload["creative_tools"]["unreal_auto_control_called"])
        self.assertFalse(payload["creative_tools"]["houdini_auto_control_called"])
        self.assertFalse(payload["creative_tools"]["zbrush_auto_control_called"])

    def test_batch_modules_do_not_import_external_runtime_packages_or_subprocess(self):
        module = Path("kernel/personal_ai/real_runtime_smoke_execution_batch.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "from playwright",
            "import playwright",
            "sync_playwright",
            "async_playwright",
            "chromium.launch",
            "subprocess.Popen",
            "os.system",
            "import bpy",
            "from bpy",
        ):
            self.assertNotIn(marker, module)

    def test_batch_document_exists_and_records_manual_only_posture(self):
        text = Path("docs/decisions/real_runtime_smoke_execution_batch_v1.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "REAL_RUNTIME_SMOKE_EXECUTION_BATCH_READY_FOR_LOCAL_TESTS",
            "Manual Execution Only",
            "Default Disabled",
            "normal tests use fake or injected transports",
            "no credential persistence",
            "no arbitrary subprocess",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
