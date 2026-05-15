import unittest
from pathlib import Path


POLICY_PATH = Path("policy/agent_execution_policy.yaml")
HARNESS_PATH = Path("scripts/agent_run_checks.py")


class AgentExecutionPolicyTests(unittest.TestCase):
    def read_policy(self) -> str:
        self.assertTrue(POLICY_PATH.is_file())
        return POLICY_PATH.read_text(encoding="utf-8")

    def read_harness(self) -> str:
        self.assertTrue(HARNESS_PATH.is_file())
        return HARNESS_PATH.read_text(encoding="utf-8")

    def test_policy_forbids_main_merge_delete_tag_and_live_runtime(self):
        policy = self.read_policy()

        self.assertIn("main_branch_write_forbidden: true", policy)
        self.assertIn("merge_forbidden: true", policy)
        self.assertIn("delete_branch_forbidden: true", policy)
        self.assertIn("tag_release_forbidden: true", policy)
        self.assertIn("live_runtime_forbidden_by_default: true", policy)

    def test_policy_requires_review_for_kernel_and_live_runtime_surfaces(self):
        policy = self.read_policy()

        self.assertIn("kernel/", policy)
        self.assertIn("kernel/personal_ai/runtime_admission_gate.py", policy)
        self.assertIn("kernel/personal_ai/adapters/openai_explicit_transport.py", policy)
        self.assertIn("kernel/personal_ai/task_graph.py", policy)
        self.assertIn("kernel_runtime_changes_require_human_review: true", policy)
        self.assertIn("live_runtime_changes_require_human_review: true", policy)
        self.assertIn("admission_or_approval_changes_require_human_review: true", policy)

    def test_policy_lists_forbidden_commands_and_secret_paths(self):
        policy = self.read_policy()

        for marker in (
            "sudo",
            "rm -rf",
            "chmod -R",
            "chown -R",
            "killall",
            "pkill",
            "launchctl",
            "osascript",
            "defaults write",
            "security",
            "ssh-keygen",
            "curl | sh",
            "wget | sh",
            "npm install -g",
            "brew install",
            ".env",
            ".ssh/",
        ):
            self.assertIn(marker, policy)

    def test_policy_blocks_unrestricted_runtime_activation(self):
        policy = self.read_policy()

        for marker in (
            "live_model_api_default_call",
            "real_browser_automation",
            "playwright_or_selenium_launch",
            "real_comfyui_endpoint_call",
            "real_blender_subprocess",
            "creative_software_control",
            "os_automation",
            "unrestricted_network",
            "arbitrary_subprocess",
            "model_output_tool_call",
            "model_output_file_edit",
        ):
            self.assertIn(marker, policy)

    def test_harness_is_repo_local_and_sanitizes_secret_environment(self):
        harness = self.read_harness()

        self.assertIn("_find_repo_root", harness)
        self.assertIn("_assert_inside_repo", harness)
        self.assertIn("_sanitized_env", harness)
        self.assertIn("OPENAI_API_KEY", harness)
        self.assertIn("ANTHROPIC_API_KEY", harness)
        self.assertIn("GEMINI_API_KEY", harness)
        self.assertIn("DEEPSEEK_API_KEY", harness)
        self.assertIn("live_runtime_executed", harness)
        self.assertIn("secrets_read", harness)
        self.assertIn("merge_performed", harness)
        self.assertIn("branch_deleted", harness)

    def test_harness_runs_fixed_check_set_without_merge_or_delete(self):
        harness = self.read_harness()

        self.assertIn("python3", harness)
        self.assertIn("unittest", harness)
        self.assertIn("make", harness)
        self.assertIn("ci", harness)
        self.assertIn("git", harness)
        self.assertIn("diff", harness)
        self.assertIn("status", harness)
        self.assertNotIn("git merge", harness)
        self.assertNotIn("git push origin main", harness)
        self.assertNotIn("git branch -d", harness)
        self.assertNotIn("git tag", harness)


if __name__ == "__main__":
    unittest.main()
