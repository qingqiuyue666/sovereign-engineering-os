import unittest
from pathlib import Path


class FinalRuntimeReadinessAuditTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_all_runtime_chain_files_exist(self):
        required_paths = (
            # model provider
            "kernel/personal_ai/model_provider_manual_live_smoke_cli.py",
            "kernel/personal_ai/adapters/model_provider_transport_adapter.py",
            "kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py",
            "kernel/personal_ai/adapters/openai_explicit_transport.py",
            # browser
            "kernel/personal_ai/adapters/browser_local_smoke.py",
            "kernel/personal_ai/adapters/browser_controlled_local_smoke_runner.py",
            "kernel/personal_ai/adapters/browser_playwright_disabled_local_adapter.py",
            "kernel/personal_ai/adapters/browser_playwright_real_package_admission.py",
            "kernel/personal_ai/adapters/browser_playwright_loopback_transport_package.py",
            # ComfyUI
            "kernel/personal_ai/adapters/comfyui_controlled_runtime.py",
            "kernel/personal_ai/adapters/comfyui_endpoint_admission_disabled_runner.py",
            # Blender
            "kernel/personal_ai/adapters/blender_controlled_runtime.py",
            "kernel/personal_ai/adapters/blender_runtime_admission_disabled_runner.py",
            # creative handoff / runtime control plane
            "kernel/personal_ai/adapters/creative_handoff_package.py",
            "kernel/personal_ai/runtime_admission_gate.py",
            "kernel/personal_ai/task_graph.py",
            # local harness
            "policy/agent_execution_policy.yaml",
            "scripts/agent_run_checks.py",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_no_runtime_dependency_added_to_pyproject(self):
        pyproject = self.read("pyproject.toml").lower()
        for dependency_name in (
            "playwright",
            "selenium",
            "comfyui",
            "bpy",
            "blender",
        ):
            self.assertNotIn(dependency_name, pyproject)

    def test_browser_runtime_remains_default_disabled_and_loopback_only(self):
        files = (
            "kernel/personal_ai/adapters/browser_controlled_local_smoke_runner.py",
            "kernel/personal_ai/adapters/browser_playwright_disabled_local_adapter.py",
            "kernel/personal_ai/adapters/browser_playwright_real_package_admission.py",
            "kernel/personal_ai/adapters/browser_playwright_loopback_transport_package.py",
        )
        for path in files:
            text = self.read(path)
            self.assertIn("loopback", text.lower(), path)
            self.assertIn("external_network", text, path)
            self.assertIn("credential", text.lower(), path)
            self.assertIn("required_human_approval", text, path)
            self.assertNotIn("from playwright", text, path)
            self.assertNotIn("import playwright", text, path)
            self.assertNotIn("sync_playwright", text, path)
            self.assertNotIn("async_playwright", text, path)
            self.assertNotIn("chromium.launch", text, path)

    def test_model_provider_remains_manual_and_gated(self):
        cli = self.read("kernel/personal_ai/model_provider_manual_live_smoke_cli.py")
        runner = self.read(
            "kernel/personal_ai/adapters/model_provider_disabled_live_smoke_runner.py"
        )
        transport = self.read("kernel/personal_ai/adapters/openai_explicit_transport.py")

        for marker in (
            "--allow-live-smoke",
            "--allow-network",
            "--confirm-manual-live-smoke",
            "--use-stdlib-openai-transport",
        ):
            self.assertIn(marker, cli)
        self.assertIn("SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE", runner)
        self.assertIn("SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT", transport)
        self.assertIn("OPENAI_API_KEY", transport)
        self.assertIn("api_key_value_persisted", transport)
        self.assertIn("api_key_value_logged", transport)
        self.assertIn("raw_provider_response_persisted", transport)

    def test_comfyui_and_blender_runners_remain_disabled_without_injected_transport(self):
        comfy = self.read(
            "kernel/personal_ai/adapters/comfyui_endpoint_admission_disabled_runner.py"
        )
        blender = self.read(
            "kernel/personal_ai/adapters/blender_runtime_admission_disabled_runner.py"
        )

        self.assertIn("allow_endpoint_runner: bool = False", comfy)
        self.assertIn("SEOS_ENABLE_COMFYUI_ENDPOINT_DISABLED_RUNNER", comfy)
        self.assertIn("missing_explicit_comfyui_transport", comfy)
        self.assertIn("external_downloads_allowed", comfy)
        self.assertIn("arbitrary_node_execution_allowed", comfy)
        self.assertIn("model_download_allowed", comfy)

        self.assertIn("allow_blender_runner: bool = False", blender)
        self.assertIn("SEOS_ENABLE_BLENDER_RUNTIME_ADMISSION_DISABLED_RUNNER", blender)
        self.assertIn("missing_explicit_blender_transport", blender)
        self.assertIn("subprocess_allowed", blender)
        self.assertIn("arbitrary_python_allowed", blender)
        self.assertIn("source_asset_overwrite_allowed", blender)
        self.assertNotIn("subprocess.Popen", blender)
        self.assertNotIn("os.system", blender)

    def test_creative_tools_remain_handoff_policy_only(self):
        creative = self.read("kernel/personal_ai/adapters/creative_handoff_package.py")
        decision = self.read("docs/decisions/runtime_live_boundary_completion_batch_v1.md")

        self.assertIn("handoff", creative.lower())
        self.assertIn("AE", decision)
        self.assertIn("Unreal", decision)
        self.assertIn("Houdini", decision)
        self.assertIn("ZBrush", decision)
        self.assertIn("not automatically controlled", decision)

    def test_normal_runtime_tests_use_fake_or_injected_transports(self):
        runtime_tests = (
            "tests/personal_ai/test_model_provider_manual_live_smoke_cli.py",
            "tests/personal_ai/test_browser_controlled_local_smoke_runner.py",
            "tests/personal_ai/test_browser_playwright_disabled_local_adapter.py",
            "tests/personal_ai/test_runtime_live_boundary_completion_batch.py",
        )
        for path in runtime_tests:
            text = self.read(path)
            self.assertNotIn("sync_playwright", text, path)
            self.assertNotIn("async_playwright", text, path)
            self.assertNotIn("chromium.launch", text, path)
            self.assertNotIn("subprocess.Popen", text, path)
            self.assertNotIn("OPENAI_API_KEY=", text, path)

    def test_agent_harness_policy_keeps_live_runtime_forbidden_by_default(self):
        policy = self.read("policy/agent_execution_policy.yaml")
        harness = self.read("scripts/agent_run_checks.py")

        self.assertIn("live_runtime_forbidden_by_default: true", policy)
        self.assertIn("merge_forbidden: true", policy)
        self.assertIn("delete_branch_forbidden: true", policy)
        self.assertIn("live_model_api_default_call", policy)
        self.assertIn("real_browser_automation", policy)
        self.assertIn("real_comfyui_endpoint_call", policy)
        self.assertIn("real_blender_subprocess", policy)
        self.assertIn("creative_software_control", policy)
        self.assertIn("live_runtime_executed", harness)
        self.assertIn("secrets_read", harness)

    def test_final_runtime_readiness_audit_document_exists(self):
        text = self.read("docs/decisions/final_runtime_readiness_audit_v1.md")
        for marker in (
            "FINAL_RUNTIME_READINESS_AUDIT_READY_FOR_LOCAL_TESTS",
            "Model provider",
            "Browser",
            "ComfyUI",
            "Blender",
            "Creative tools",
            "Default Disabled",
            "Human Review Required",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
