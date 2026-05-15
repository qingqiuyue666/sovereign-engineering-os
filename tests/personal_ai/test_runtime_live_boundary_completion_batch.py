import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_runtime_admission_disabled_runner import (
    run_blender_runtime_admission_disabled_runner,
)
from kernel.personal_ai.adapters.browser_playwright_loopback_transport_package import (
    build_browser_playwright_loopback_transport_package,
)
from kernel.personal_ai.adapters.browser_playwright_real_package_admission import (
    build_browser_playwright_real_package_admission,
)
from kernel.personal_ai.adapters.comfyui_endpoint_admission_disabled_runner import (
    run_comfyui_endpoint_disabled_runner,
)


class RuntimeLiveBoundaryCompletionBatchTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_json(self, path: Path, payload: dict) -> Path:
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_browser_playwright_loopback_package_denies_by_default(self):
        root = self.make_output_dir()
        admission = build_browser_playwright_real_package_admission(root / "admission" if False else root)
        run_dir = self.make_output_dir()

        result = build_browser_playwright_loopback_transport_package(
            admission.admission_path,
            run_dir,
        )

        self.assertEqual(result.status, "disabled_by_callsite")
        self.assertFalse(result.playwright_dependency_added)
        self.assertFalse(result.playwright_imported)
        self.assertFalse(result.browser_launched)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["external_network_used"])
        self.assertTrue(payload["loopback_only"])

    def test_browser_playwright_loopback_package_uses_injected_transport_only_after_gates(self):
        admission_dir = self.make_output_dir()
        admission = build_browser_playwright_real_package_admission(admission_dir)
        run_dir = self.make_output_dir()
        calls = []

        def transport(request):
            calls.append(request)
            self.assertTrue(request["loopback_only"])
            self.assertFalse(request["external_network_allowed"])
            self.assertTrue(request["isolated_temp_profile_required"])
            self.assertFalse(request["real_user_profile_allowed"])
            return {"status": "ok"}

        result = build_browser_playwright_loopback_transport_package(
            admission.admission_path,
            run_dir,
            environ={"SEOS_ENABLE_BROWSER_PLAYWRIGHT_LOOPBACK_TRANSPORT_PACKAGE": "true"},
            allow_transport_package=True,
            loopback_transport=transport,
        )

        self.assertEqual(result.status, "completed_via_explicit_loopback_transport_package")
        self.assertEqual(len(calls), 1)
        self.assertFalse(result.playwright_imported)
        self.assertFalse(result.browser_launched)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["transport_response_validation"]["complete"])

    def test_comfyui_endpoint_runner_denies_by_default_and_uses_fake_transport_after_gates(self):
        root = self.make_output_dir()
        workflow_path = self.write_json(
            root / "workflow.json",
            {"nodes": [{"id": "1", "type": "LoadImage"}, {"id": "2", "type": "KSampler"}]},
        )
        denied_dir = root / "denied"
        denied_dir.mkdir()
        denied = run_comfyui_endpoint_disabled_runner(workflow_path, denied_dir)
        self.assertEqual(denied.status, "disabled_by_callsite")
        self.assertFalse(denied.real_endpoint_called)

        run_dir = root / "run"
        run_dir.mkdir()
        calls = []

        def transport(request):
            calls.append(request)
            self.assertTrue(request["loopback_only"])
            self.assertFalse(request["external_network_allowed"])
            self.assertFalse(request["arbitrary_node_execution_allowed"])
            return {"status": "ok"}

        result = run_comfyui_endpoint_disabled_runner(
            workflow_path,
            run_dir,
            environ={"SEOS_ENABLE_COMFYUI_ENDPOINT_DISABLED_RUNNER": "true"},
            allow_endpoint_runner=True,
            comfyui_transport=transport,
        )
        self.assertEqual(result.status, "completed_via_explicit_comfyui_transport")
        self.assertEqual(len(calls), 1)
        self.assertTrue(result.real_endpoint_called)
        self.assertFalse(result.external_network_used)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["workflow_response_validation"]["complete"])

    def test_comfyui_endpoint_runner_rejects_external_endpoint_and_forbidden_node(self):
        root = self.make_output_dir()
        workflow_path = self.write_json(root / "workflow.json", {"nodes": [{"id": "1", "type": "PythonScript"}]})
        run_dir = root / "run"
        run_dir.mkdir()
        result = run_comfyui_endpoint_disabled_runner(
            workflow_path,
            run_dir,
            endpoint_url="https://example.com",
            allow_endpoint_runner=True,
        )
        self.assertEqual(result.status, "failed_closed")
        self.assertFalse(result.real_endpoint_called)

    def test_blender_runtime_runner_denies_by_default_and_uses_fake_transport_after_gates(self):
        root = self.make_output_dir()
        scene = root / "scene.blend"
        scene.write_bytes(b"fake-blender-scene")
        plan = self.write_json(root / "operations.json", {"operations": [{"operation": "add_camera"}]})
        denied_dir = root / "denied"
        denied_dir.mkdir()
        denied = run_blender_runtime_admission_disabled_runner(scene, plan, denied_dir)
        self.assertEqual(denied.status, "disabled_by_callsite")
        self.assertFalse(denied.blender_runtime_called)

        run_dir = root / "run"
        run_dir.mkdir()
        calls = []

        def transport(request):
            calls.append(request)
            self.assertFalse(request["subprocess_allowed"])
            self.assertFalse(request["arbitrary_python_allowed"])
            self.assertFalse(request["external_network_allowed"])
            return {"status": "ok"}

        result = run_blender_runtime_admission_disabled_runner(
            scene,
            plan,
            run_dir,
            environ={"SEOS_ENABLE_BLENDER_RUNTIME_ADMISSION_DISABLED_RUNNER": "true"},
            allow_blender_runner=True,
            blender_transport=transport,
        )
        self.assertEqual(result.status, "completed_via_explicit_blender_transport")
        self.assertEqual(len(calls), 1)
        self.assertTrue(result.blender_runtime_called)
        self.assertFalse(result.subprocess_used)
        self.assertFalse(result.arbitrary_python_used)
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["operation_response_validation"]["complete"])

    def test_blender_runtime_runner_rejects_forbidden_operation_token(self):
        root = self.make_output_dir()
        scene = root / "scene.blend"
        scene.write_bytes(b"fake-blender-scene")
        plan = self.write_json(root / "operations.json", {"operations": [{"operation": "add_camera", "parameters": {"script": "exec('bad')"}}]})
        run_dir = root / "run"
        run_dir.mkdir()
        result = run_blender_runtime_admission_disabled_runner(
            scene,
            plan,
            run_dir,
            environ={"SEOS_ENABLE_BLENDER_RUNTIME_ADMISSION_DISABLED_RUNNER": "true"},
            allow_blender_runner=True,
        )
        self.assertEqual(result.status, "failed_closed")
        self.assertFalse(result.blender_runtime_called)

    def test_batch_modules_do_not_import_runtime_packages_or_launch_tools(self):
        paths = (
            "kernel/personal_ai/adapters/browser_playwright_loopback_transport_package.py",
            "kernel/personal_ai/adapters/comfyui_endpoint_admission_disabled_runner.py",
            "kernel/personal_ai/adapters/blender_runtime_admission_disabled_runner.py",
        )
        forbidden = (
            "from playwright",
            "import playwright",
            "subprocess.Popen",
            "os.system",
            "sync_playwright",
            "async_playwright",
            "chromium.launch",
        )
        for path in paths:
            text = Path(path).read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, path)


if __name__ == "__main__":
    unittest.main()
