import unittest
from pathlib import Path


class PostRealRuntimeSmokeMainHealthTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_real_runtime_smoke_batch_files_are_on_mainline(self):
        required_paths = (
            "kernel/personal_ai/real_runtime_smoke_execution_batch.py",
            "tests/personal_ai/test_real_runtime_smoke_execution_batch.py",
            "docs/decisions/real_runtime_smoke_execution_batch_v1.md",
            "docs/decisions/final_runtime_readiness_audit_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_real_runtime_smoke_batch_remains_default_disabled(self):
        module = self.read("kernel/personal_ai/real_runtime_smoke_execution_batch.py")
        decision = self.read("docs/decisions/real_runtime_smoke_execution_batch_v1.md")

        self.assertIn("allow_batch: bool = False", module)
        self.assertIn("SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH", module)
        self.assertIn("default_live_execution_enabled", module)
        self.assertIn("False", module)
        self.assertIn("Manual Execution Only", decision)
        self.assertIn("Default Disabled", decision)
        self.assertIn("Human Review Required", decision)

    def test_runtime_smoke_batch_has_all_runtime_lines(self):
        module = self.read("kernel/personal_ai/real_runtime_smoke_execution_batch.py")
        for marker in (
            "model_provider",
            "browser",
            "comfyui",
            "blender",
            "creative_tools",
            "real_model_smoke_entry_called",
            "real_browser_smoke_entry_called",
            "real_comfyui_smoke_entry_called",
            "real_blender_smoke_entry_called",
            "creative_software_auto_control_called",
        ):
            self.assertIn(marker, module)

    def test_no_external_runtime_dependency_added(self):
        pyproject = self.read("pyproject.toml").lower()
        for dependency_name in (
            "playwright",
            "selenium",
            "comfyui",
            "bpy",
            "blender",
        ):
            self.assertNotIn(dependency_name, pyproject)

    def test_runtime_smoke_batch_does_not_import_or_launch_external_tools(self):
        module = self.read("kernel/personal_ai/real_runtime_smoke_execution_batch.py")
        forbidden_markers = (
            "from playwright",
            "import playwright",
            "sync_playwright",
            "async_playwright",
            "chromium.launch",
            "firefox.launch",
            "webkit.launch",
            "subprocess.Popen",
            "os.system",
            "import bpy",
            "from bpy",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, module)

    def test_runtime_smoke_batch_keeps_secret_and_output_authority_denied(self):
        module = self.read("kernel/personal_ai/real_runtime_smoke_execution_batch.py")
        for marker in (
            "secrets_persisted",
            "raw_provider_response_persisted",
            "raw_image_payload_persisted",
            "output_triggered_tool_or_file_authority",
            "arbitrary_subprocess_allowed",
            "tool_calls_allowed",
            "file_edits_allowed",
        ):
            self.assertIn(marker, module)

    def test_post_real_runtime_smoke_main_health_document_exists(self):
        text = self.read("docs/decisions/post_real_runtime_smoke_main_health_v1.md")
        for marker in (
            "POST_REAL_RUNTIME_SMOKE_MAIN_HEALTH_READY_FOR_LOCAL_TESTS",
            "Real Runtime Smoke Entry Ready",
            "Main Verified",
            "Manual Execution Only",
            "Default Disabled",
            "Human Review Required",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
