import unittest
from pathlib import Path


class PostWalCheckpointMainHealthTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = Path(path)
        self.assertTrue(file_path.is_file(), path)
        return file_path.read_text(encoding="utf-8")

    def test_wal_checkpoint_track_files_are_on_mainline(self):
        required_paths = (
            "kernel/stores/sqlite/wal_checkpoint_policy_audit.py",
            "tests/tracer_bullet/test_wal_checkpoint_policy_audit.py",
            "docs/decisions/wal_checkpoint_policy_audit_v1.md",
            "kernel/stores/sqlite/wal_checkpoint_policy.py",
            "tests/tracer_bullet/test_wal_checkpoint_policy.py",
            "docs/decisions/wal_checkpoint_policy_foundation_v1.md",
            "kernel/stores/sqlite/wal_checkpoint_observation_collector.py",
            "tests/tracer_bullet/test_wal_checkpoint_observation_collector.py",
            "docs/decisions/wal_checkpoint_observation_collector_v1.md",
            "kernel/stores/sqlite/wal_checkpoint_plan_audit.py",
            "tests/tracer_bullet/test_wal_checkpoint_plan_audit.py",
            "docs/decisions/wal_checkpoint_plan_audit_integration_v1.md",
        )
        for path in required_paths:
            self.assertTrue(Path(path).is_file(), path)

    def test_policy_audit_remains_audit_only(self):
        module = self.read("kernel/stores/sqlite/wal_checkpoint_policy_audit.py")
        decision = self.read("docs/decisions/wal_checkpoint_policy_audit_v1.md")
        for marker in (
            "audit_only",
            "database_opened",
            "pragma_wal_checkpoint_executed",
            "wal_truncate_executed",
            "sqlite_state_mutated",
            "mutating_checkpoint_executed",
        ):
            self.assertIn(marker, module)
        self.assertIn("audit-only", decision)
        self.assertIn("does not execute checkpoint", decision)
        self.assertIn("does not truncate WAL", decision)
        self.assertIn("does not mutate SQLite state", decision)

    def test_policy_planner_remains_non_executing(self):
        module = self.read("kernel/stores/sqlite/wal_checkpoint_policy.py")
        decision = self.read("docs/decisions/wal_checkpoint_policy_foundation_v1.md")
        for marker in (
            "planner_only",
            "execution_allowed",
            "truncate_allowed",
            "database_opened",
            "pragma_wal_checkpoint_executed",
            "wal_truncate_executed",
            "sqlite_state_mutated",
            "mutating_checkpoint_executed",
        ):
            self.assertIn(marker, module)
        self.assertIn("planner-only", decision)
        self.assertIn("does not execute checkpoint", decision)
        self.assertIn("does not truncate WAL", decision)

    def test_observation_collector_remains_observation_only(self):
        module = self.read("kernel/stores/sqlite/wal_checkpoint_observation_collector.py")
        decision = self.read("docs/decisions/wal_checkpoint_observation_collector_v1.md")
        for marker in (
            "database_opened_read_only",
            "database_opened_for_write",
            "write_transaction_opened",
            "checkpoint_executed",
            "pragma_wal_checkpoint_executed",
            "wal_truncate_executed",
            "sqlite_state_mutated",
        ):
            self.assertIn(marker, module)
        self.assertIn("observation-only", decision)
        self.assertIn("does not execute checkpoint", decision)
        self.assertIn("does not truncate WAL", decision)
        self.assertIn("does not mutate SQLite state", decision)

    def test_plan_audit_integration_remains_non_mutating(self):
        module = self.read("kernel/stores/sqlite/wal_checkpoint_plan_audit.py")
        decision = self.read("docs/decisions/wal_checkpoint_plan_audit_integration_v1.md")
        for marker in (
            "collect_wal_checkpoint_observation",
            "build_wal_checkpoint_plan",
            "write_json_atomically",
            "execution_allowed",
            "truncate_allowed",
            "database_opened_for_write",
            "write_transaction_opened",
            "checkpoint_executed",
            "pragma_wal_checkpoint_executed",
            "wal_truncate_executed",
            "sqlite_state_mutated",
            "mutating_checkpoint_executed",
            "planner_only",
            "observation_only",
        ):
            self.assertIn(marker, module)
        self.assertIn("non-mutating", decision)
        self.assertIn("execution_allowed: false", decision)
        self.assertIn("truncate_allowed: false", decision)
        self.assertIn("mutating_checkpoint_executed: false", decision)

    def test_wal_checkpoint_track_modules_do_not_contain_forbidden_runtime_markers(self):
        paths = (
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
            "subprocess",
        )
        for path in paths:
            source = self.read(path)
            for marker in forbidden_markers:
                self.assertNotIn(marker, source, path + " contains " + marker)

    def test_post_wal_checkpoint_main_health_decision_exists(self):
        text = self.read("docs/decisions/post_wal_checkpoint_main_health_v1.md")
        for marker in (
            "POST_WAL_CHECKPOINT_MAIN_HEALTH_READY_FOR_LOCAL_TESTS",
            "WAL Checkpoint Policy Audit Ready",
            "WAL Checkpoint Policy Foundation Ready",
            "WAL Checkpoint Observation Collector Ready",
            "WAL Checkpoint Plan Audit Integration Ready",
            "No Checkpoint Execution",
            "No WAL Truncation",
            "Main Verified",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
