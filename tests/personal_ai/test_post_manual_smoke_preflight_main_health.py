import unittest
from pathlib import Path


class PostManualSmokePreflightMainHealthTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_manual_preflight_files_are_on_mainline(self):
        required_paths = (
            "kernel/personal_ai/real_runtime_manual_smoke_preflight.py",
            "tests/personal_ai/test_real_runtime_manual_smoke_preflight.py",
            "docs/decisions/real_runtime_manual_smoke_preflight_v1.md",
            "docs/usage/manual_runtime_smoke_runbook_v1.md",
            "kernel/personal_ai/real_runtime_smoke_execution_batch.py",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_preflight_remains_non_executing(self):
        module = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        decision = self.read("docs/decisions/real_runtime_manual_smoke_preflight_v1.md")

        for marker in (
            "runtime_execution_performed",
            "model_api_called",
            "browser_launched",
            "comfyui_endpoint_called",
            "blender_launched",
            "creative_software_auto_control_called",
            "external_network_accessed",
            "secret_value_read",
            "secret_value_persisted",
            "arbitrary_subprocess_executed",
            "output_triggered_tool_or_file_authority",
        ):
            self.assertIn(marker, module)
        self.assertIn("Preflight only", decision)
        self.assertIn("does not execute real runtimes", decision)

    def test_preflight_checks_all_runtime_lines(self):
        module = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        for marker in (
            "model_provider",
            "browser",
            "comfyui",
            "blender",
            "creative_tools",
            "_check_model_provider",
            "_check_browser",
            "_check_comfyui",
            "_check_blender",
            "_check_creative_tools",
        ):
            self.assertIn(marker, module)

    def test_preflight_only_checks_openai_key_presence_not_value(self):
        module = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        tests = self.read("tests/personal_ai/test_real_runtime_manual_smoke_preflight.py")

        self.assertIn("OPENAI_API_KEY", module)
        self.assertIn("openai_api_key_present", module)
        self.assertIn("openai_api_key_value_read", module)
        self.assertIn("False", module)
        self.assertIn("secret-value-must-not-be-copied", tests)
        self.assertIn("assertNotIn", tests)

    def test_preflight_rejects_unsafe_browser_comfyui_and_blender_posture(self):
        module = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        for marker in (
            "external_network_allowed_must_be_false",
            "real_user_profile_allowed_must_be_false",
            "credential_persistence_allowed_must_be_false",
            "login_allowed_must_be_false",
            "signup_allowed_must_be_false",
            "account_creation_allowed_must_be_false",
            "payment_allowed_must_be_false",
            "comfyui_endpoint_not_loopback",
            "comfyui_workflow_forbidden_node_type",
            "blender_operation_forbidden_token",
            "blender_operation_not_allowed",
        ):
            self.assertIn(marker, module)

    def test_preflight_module_does_not_import_or_launch_external_runtimes(self):
        module = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        forbidden_markers = (
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
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, module)

    def test_post_manual_smoke_preflight_main_health_document_exists(self):
        text = self.read("docs/decisions/post_manual_smoke_preflight_main_health_v1.md")
        for marker in (
            "POST_MANUAL_SMOKE_PREFLIGHT_MAIN_HEALTH_READY_FOR_LOCAL_TESTS",
            "Manual Preflight Ready",
            "Main Verified",
            "Manual Runbook Documented",
            "Default Disabled",
            "Human Review Required",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
