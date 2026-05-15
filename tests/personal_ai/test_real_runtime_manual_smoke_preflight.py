import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.browser_playwright_real_package_admission import (
    build_browser_playwright_real_package_admission,
)
from kernel.personal_ai.real_runtime_manual_smoke_preflight import (
    run_real_runtime_manual_smoke_preflight,
)


class RealRuntimeManualSmokePreflightTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_json(self, path: Path, payload: dict) -> Path:
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_preflight_runs_without_executing_runtime_or_reading_secret_values(self):
        root = self.make_output_dir()
        model_plan = self.write_json(root / "model_plan.json", {"plan": "fixture"})
        admission_dir = root / "admission"
        admission_dir.mkdir()
        browser_admission = build_browser_playwright_real_package_admission(admission_dir)
        workflow = self.write_json(
            root / "workflow.json",
            {"nodes": [{"id": "1", "type": "LoadImage"}, {"id": "2", "type": "KSampler"}]},
        )
        scene = root / "scene.blend"
        scene.write_bytes(b"fake-blender-scene")
        operations = self.write_json(
            root / "operations.json",
            {"operations": [{"operation": "add_camera"}]},
        )
        report_dir = root / "report"
        report_dir.mkdir()

        result = run_real_runtime_manual_smoke_preflight(
            output_dir=report_dir,
            environ={
                "SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH": "true",
                "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE": "true",
                "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT": "true",
                "OPENAI_API_KEY": "secret-value-must-not-be-copied",
            },
            model_plan_path=model_plan,
            browser_admission_path=browser_admission.admission_path,
            comfyui_workflow_path=workflow,
            comfyui_endpoint_url="http://127.0.0.1:8188",
            blender_scene_path=scene,
            blender_operation_plan_path=operations,
        )

        self.assertTrue(result.complete)
        self.assertEqual(result.checked_runtime_count, 5)
        self.assertEqual(result.ready_runtime_count, 5)
        self.assertFalse(result.runtime_execution_performed)
        self.assertFalse(result.secret_value_read)
        payload = json.loads(result.report_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["model_api_called"])
        self.assertFalse(payload["browser_launched"])
        self.assertFalse(payload["comfyui_endpoint_called"])
        self.assertFalse(payload["blender_launched"])
        self.assertFalse(payload["external_network_accessed"])
        self.assertFalse(payload["secret_value_read"])
        self.assertNotIn("secret-value-must-not-be-copied", json.dumps(payload, sort_keys=True))

    def test_missing_model_flags_and_key_are_reported_without_reading_secret(self):
        root = self.make_output_dir()
        model_plan = self.write_json(root / "model_plan.json", {"plan": "fixture"})
        report_dir = root / "report"
        report_dir.mkdir()

        result = run_real_runtime_manual_smoke_preflight(
            output_dir=report_dir,
            environ={},
            model_plan_path=model_plan,
        )

        payload = json.loads(result.report_path.read_text(encoding="utf-8"))
        model = payload["checks"]["model_provider"]
        self.assertFalse(model["ready"])
        self.assertIn("SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH_missing_or_not_true", model["failures"])
        self.assertIn("SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE_missing_or_not_true", model["failures"])
        self.assertIn("SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT_missing_or_not_true", model["failures"])
        self.assertIn("OPENAI_API_KEY_missing", model["failures"])
        self.assertFalse(model["openai_api_key_value_read"])

    def test_browser_preflight_rejects_tampered_external_network_posture(self):
        root = self.make_output_dir()
        admission_dir = root / "admission"
        admission_dir.mkdir()
        admission = build_browser_playwright_real_package_admission(admission_dir)
        payload = json.loads(admission.admission_path.read_text(encoding="utf-8"))
        payload["external_network_allowed"] = True
        tampered = root / "tampered_browser_admission.json"
        tampered.write_text(json.dumps(payload), encoding="utf-8")
        report_dir = root / "report"
        report_dir.mkdir()

        result = run_real_runtime_manual_smoke_preflight(
            output_dir=report_dir,
            browser_admission_path=tampered,
        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        browser = report["checks"]["browser"]
        self.assertFalse(browser["ready"])
        self.assertIn("external_network_allowed_must_be_false", browser["failures"])

    def test_comfyui_preflight_rejects_external_endpoint_and_forbidden_node(self):
        root = self.make_output_dir()
        workflow = self.write_json(root / "workflow.json", {"nodes": [{"id": "1", "type": "PythonScript"}]})
        report_dir = root / "report"
        report_dir.mkdir()

        result = run_real_runtime_manual_smoke_preflight(
            output_dir=report_dir,
            comfyui_workflow_path=workflow,
            comfyui_endpoint_url="https://example.com",
        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        comfyui = report["checks"]["comfyui"]
        self.assertFalse(comfyui["ready"])
        self.assertIn("comfyui_endpoint_not_loopback", comfyui["failures"])
        self.assertIn("comfyui_workflow_forbidden_node_type", comfyui["failures"])

    def test_blender_preflight_rejects_forbidden_operation_token(self):
        root = self.make_output_dir()
        scene = root / "scene.blend"
        scene.write_bytes(b"fake-blender-scene")
        plan = self.write_json(
            root / "operations.json",
            {"operations": [{"operation": "add_camera", "parameters": {"script": "exec('bad')"}}]},
        )
        report_dir = root / "report"
        report_dir.mkdir()

        result = run_real_runtime_manual_smoke_preflight(
            output_dir=report_dir,
            blender_scene_path=scene,
            blender_operation_plan_path=plan,
        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        blender = report["checks"]["blender"]
        self.assertFalse(blender["ready"])
        self.assertIn("blender_operation_forbidden_token", blender["failures"])

    def test_refuses_missing_output_dir_and_existing_report(self):
        root = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            run_real_runtime_manual_smoke_preflight(output_dir=root / "missing")

        report_dir = root / "report"
        report_dir.mkdir()
        run_real_runtime_manual_smoke_preflight(output_dir=report_dir)
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_real_runtime_manual_smoke_preflight(output_dir=report_dir)

    def test_module_does_not_import_or_launch_external_runtimes(self):
        module = Path("kernel/personal_ai/real_runtime_manual_smoke_preflight.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "run_openai",
            "stdlib_openai",
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


if __name__ == "__main__":
    unittest.main()
