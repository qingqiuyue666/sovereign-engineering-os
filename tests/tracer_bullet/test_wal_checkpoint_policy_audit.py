import json
import tempfile
import unittest
from pathlib import Path

from kernel.stores.sqlite.wal_checkpoint_policy_audit import (
    run_wal_checkpoint_policy_audit,
)


class WalCheckpointPolicyAuditTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_audit_reports_wal_mode_without_executing_checkpoint(self):
        output_dir = self.make_output_dir()

        result = run_wal_checkpoint_policy_audit(
            repo_root=Path.cwd(),
            output_dir=output_dir,
        )

        self.assertTrue(result.complete)
        self.assertTrue(result.wal_mode_declared)
        self.assertFalse(result.mutating_checkpoint_executed)
        self.assertTrue(result.required_human_approval)
        payload = json.loads(result.report_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["wal_mode_declared"])
        self.assertTrue(payload["synchronous_normal_declared"])
        self.assertTrue(payload["audit_only"])
        self.assertFalse(payload["database_opened"])
        self.assertFalse(payload["pragma_wal_checkpoint_executed"])
        self.assertFalse(payload["wal_truncate_executed"])
        self.assertFalse(payload["sqlite_state_mutated"])

    def test_audit_records_opener_and_snapshot_hash_surfaces(self):
        output_dir = self.make_output_dir()
        result = run_wal_checkpoint_policy_audit(
            repo_root=Path.cwd(),
            output_dir=output_dir,
        )
        payload = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["opener_path"],
            "kernel/stores/sqlite/wal_recovery.py",
        )
        self.assertTrue(payload["opener_required_markers"]["PRAGMA journal_mode=WAL;"])
        self.assertTrue(payload["opener_required_markers"]["PRAGMA synchronous=NORMAL;"])
        self.assertTrue(payload["opener_required_markers"]["PRAGMA foreign_keys=ON;"])
        self.assertTrue(payload["opener_required_markers"]["PRAGMA busy_timeout=5000;"])
        self.assertTrue(payload["migration_mentions_wal_posture"])
        self.assertTrue(payload["snapshot_schema_has_root_hash"])
        self.assertTrue(payload["snapshot_schema_has_file_manifest_hash"])
        self.assertTrue(payload["snapshot_schema_has_artifact_manifest_hash"])

    def test_audit_reports_checkpoint_policy_presence_as_discovery_not_execution(self):
        output_dir = self.make_output_dir()
        result = run_wal_checkpoint_policy_audit(
            repo_root=Path.cwd(),
            output_dir=output_dir,
        )
        payload = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertIn("explicit_checkpoint_policy_found", payload)
        self.assertIn("checkpoint_policy_hits", payload)
        self.assertIn("checkpoint_runner_found", payload)
        self.assertIn("snapshot_trigger_rule_found", payload)
        self.assertIn("wal_size_threshold_rule_found", payload)
        self.assertFalse(payload["mutating_checkpoint_executed"])
        self.assertEqual(payload["recommended_next_step"], "wal_checkpoint_policy_foundation_v1")

    def test_refuses_missing_output_dir_and_existing_report(self):
        root = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            run_wal_checkpoint_policy_audit(
                repo_root=Path.cwd(),
                output_dir=root / "missing",
            )

        run_wal_checkpoint_policy_audit(repo_root=Path.cwd(), output_dir=root)
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_wal_checkpoint_policy_audit(repo_root=Path.cwd(), output_dir=root)

    def test_refuses_missing_repo_root(self):
        output_dir = self.make_output_dir()
        with self.assertRaisesRegex(ValueError, "repo_root is missing"):
            run_wal_checkpoint_policy_audit(
                repo_root=output_dir / "missing-repo",
                output_dir=output_dir,
            )

    def test_audit_module_does_not_execute_checkpoint_or_open_database(self):
        module = Path("kernel/stores/sqlite/wal_checkpoint_policy_audit.py").read_text(
            encoding="utf-8"
        )
        forbidden_runtime_markers = (
            "sqlite3.connect",
            "open_connection(",
            "PRAGMA wal_checkpoint",
            "wal_checkpoint(",
            "SQLITE_CHECKPOINT_TRUNCATE",
            ".execute(\"PRAGMA",
            ".executescript",
        )
        for marker in forbidden_runtime_markers:
            self.assertNotIn(marker, module)

    def test_decision_doc_exists_and_records_audit_only_posture(self):
        text = Path("docs/decisions/wal_checkpoint_policy_audit_v1.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "WAL_CHECKPOINT_POLICY_AUDIT_READY_FOR_LOCAL_TESTS",
            "audit-only",
            "does not execute checkpoint",
            "does not truncate WAL",
            "does not mutate SQLite state",
            "wal_checkpoint_policy_foundation_v1",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
