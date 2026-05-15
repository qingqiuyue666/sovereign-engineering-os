import unittest
from pathlib import Path


class RuntimeAndWalMainHealthTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_runtime_and_wal_health_files_are_on_mainline(self):
        required_paths = (
            "kernel/personal_ai/real_runtime_smoke_execution_batch.py",
            "kernel/personal_ai/real_runtime_manual_smoke_preflight.py",
            "docs/usage/manual_runtime_smoke_runbook_v1.md",
            "docs/decisions/real_runtime_manual_smoke_preflight_v1.md",
            "docs/decisions/post_manual_smoke_preflight_main_health_v1.md",
            "kernel/stores/sqlite/wal_checkpoint_policy_audit.py",
            "kernel/stores/sqlite/wal_checkpoint_policy.py",
            "kernel/stores/sqlite/wal_checkpoint_observation_collector.py",
            "kernel/stores/sqlite/wal_checkpoint_plan_audit.py",
            "docs/decisions/post_wal_checkpoint_main_health_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_runtime_track_remains_default_disabled_and_manual_review_required(self):
        preflight = self.read("kernel/personal_ai/real_runtime_manual_smoke_preflight.py")
        runbook = self.read("docs/usage/manual_runtime_smoke_runbook_v1.md")
        post_health = self.read("docs/decisions/post_manual_smoke_preflight_main_health_v1.md")

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
            self.assertIn(marker, preflight)
        self.assertIn("Manual", runbook)
        self.assertIn("Default Disabled", post_health)
        self.assertIn("Human Review Required", post_health)

    def test_wal_track_remains_non_mutating(self):
        post_health = self.read("docs/decisions/post_wal_checkpoint_main_health_v1.md")
        plan_audit = self.read("kernel/stores/sqlite/wal_checkpoint_plan_audit.py")
        observation = self.read("kernel/stores/sqlite/wal_checkpoint_observation_collector.py")
        planner = self.read("kernel/stores/sqlite/wal_checkpoint_policy.py")

        for marker in (
            "No Checkpoint Execution",
            "No WAL Truncation",
            "WAL Checkpoint Track Main Verified",
        ):
            self.assertIn(marker, post_health)
        for marker in (
            "execution_allowed",
            "truncate_allowed",
            "checkpoint_executed",
            "wal_truncate_executed",
            "sqlite_state_mutated",
            "mutating_checkpoint_executed",
        ):
            self.assertIn(marker, plan_audit)
        self.assertIn("database_opened_for_write", observation)
        self.assertIn("planner_only", planner)

    def test_runtime_and_wal_modules_do_not_contain_forbidden_runtime_markers(self):
        paths = (
            "kernel/personal_ai/real_runtime_manual_smoke_preflight.py",
            "kernel/stores/sqlite/wal_checkpoint_policy_audit.py",
            "kernel/stores/sqlite/wal_checkpoint_policy.py",
            "kernel/stores/sqlite/wal_checkpoint_observation_collector.py",
            "kernel/stores/sqlite/wal_checkpoint_plan_audit.py",
        )
        forbidden_markers = (
            "PRAGMA wal_checkpoint",
            "wal_checkpoint(",
            "SQLITE_CHECKPOINT_TRUNCATE",
            ".executescript",
            "DELETE FROM",
            "UPDATE ",
            "INSERT INTO",
            "TRUNCATE",
            "os.system",
            "subprocess.Popen",
            "chromium.launch",
            "import bpy",
            "from bpy",
        )
        for path in paths:
            source = self.read(path)
            for marker in forbidden_markers:
                self.assertNotIn(marker, source, path + " contains " + marker)

    def test_runtime_and_wal_main_health_decision_exists(self):
        text = self.read("docs/decisions/runtime_and_wal_main_health_v1.md")
        for marker in (
            "RUNTIME_AND_WAL_MAIN_HEALTH_READY_FOR_LOCAL_TESTS",
            "Real Runtime Smoke Entry Ready",
            "Manual Preflight Ready",
            "Default Disabled",
            "Human Review Required",
            "WAL Checkpoint Track Main Verified",
            "No Checkpoint Execution",
            "No WAL Truncation",
            "Main Verified",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
