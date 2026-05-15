
import json

import os

import sqlite3

import tempfile

import unittest

from pathlib import Path

from kernel.stores.sqlite.wal_checkpoint_plan_audit import (

    WalCheckpointPlanAuditResult,

    run_wal_checkpoint_plan_audit,

)

class WalCheckpointPlanAuditIntegrationTests(unittest.TestCase):

    def make_dir(self) -> Path:

        temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(temp_dir.cleanup)

        return Path(temp_dir.name)

    def policy(self, **overrides):

        payload = {

            "policy_id": "wal-policy-v1",

            "max_wal_pages": 1000,

            "max_wal_bytes": 4_000_000,

            "max_age_seconds": 600,

            "trigger_on_snapshot": True,

            "manual_checkpoint_allowed": True,

            "truncate_allowed": False,

            "created_at": "2026-05-15T00:00:00Z",

            "version": "v1",

        }

        payload.update(overrides)

        return payload

    def test_integration_emits_report_without_mutation(self):

        root = self.make_dir()

        db_path = root / "state.db"

        wal_path = root / "state.db-wal"

        wal_path.write_bytes(b"x" * 8192)

        result = run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(max_wal_pages=2),

            now_seconds=1000,

            page_size_override=4096,

        )

        self.assertIsInstance(result, WalCheckpointPlanAuditResult)

        self.assertTrue(result.report_path.is_file())

        report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["report_type"], "seos_wal_checkpoint_plan_audit_v1")

        self.assertTrue(report["complete"])

        self.assertIn("observation", report)

        self.assertIn("policy", report)

        self.assertIn("plan", report)

        self.assertFalse(report["execution_allowed"])

        self.assertFalse(report["truncate_allowed"])

        self.assertFalse(report["database_opened_for_write"])

        self.assertFalse(report["write_transaction_opened"])

        self.assertFalse(report["checkpoint_executed"])

        self.assertFalse(report["pragma_wal_checkpoint_executed"])

        self.assertFalse(report["wal_truncate_executed"])

        self.assertFalse(report["sqlite_state_mutated"])

        self.assertFalse(report["mutating_checkpoint_executed"])

        self.assertTrue(report["planner_only"])

        self.assertTrue(report["observation_only"])

    def test_wal_pages_threshold_requires_checkpoint_but_not_execution(self):

        root = self.make_dir()

        db_path = root / "state.db"

        (root / "state.db-wal").write_bytes(b"x" * 8192)

        result = run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(max_wal_pages=2),

            now_seconds=1000,

            page_size_override=4096,

        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertTrue(report["checkpoint_required"])

        self.assertIn("wal_pages_threshold_reached", report["reason_codes"])

        self.assertEqual(report["recommended_mode"], "passive")

        self.assertFalse(report["execution_allowed"])

        self.assertFalse(report["mutating_checkpoint_executed"])

    def test_snapshot_trigger_requires_checkpoint(self):

        root = self.make_dir()

        db_path = root / "state.db"

        result = run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(max_wal_pages=9999, trigger_on_snapshot=True),

            now_seconds=1000,

            snapshot_creation_pending=True,

        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertTrue(report["checkpoint_required"])

        self.assertIn("snapshot_trigger_pending", report["reason_codes"])

        self.assertFalse(report["execution_allowed"])

    def test_no_threshold_does_not_require_checkpoint(self):

        root = self.make_dir()

        db_path = root / "state.db"

        result = run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(max_wal_pages=9999, max_wal_bytes=9999, max_age_seconds=9999),

            now_seconds=1000,

        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertFalse(report["checkpoint_required"])

        self.assertEqual(report["reason_codes"], [])

        self.assertEqual(report["recommended_mode"], "none")

        self.assertFalse(report["execution_allowed"])

    def test_readonly_page_size_query_propagates_read_only_flag(self):

        root = self.make_dir()

        db_path = root / "state.sqlite3"

        conn = sqlite3.connect(str(db_path))

        try:

            conn.execute("PRAGMA page_size=8192;")

            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY);")

            conn.commit()

        finally:

            conn.close()

        (root / "state.sqlite3-wal").write_bytes(b"x" * 9000)

        result = run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(max_wal_pages=9999),

            now_seconds=1000,

            allow_readonly_page_size_query=True,

        )

        report = json.loads(result.report_path.read_text(encoding="utf-8"))

        self.assertTrue(report["database_opened_read_only"])

        self.assertFalse(report["database_opened_for_write"])

        self.assertFalse(report["write_transaction_opened"])

        self.assertFalse(report["sqlite_state_mutated"])

    def test_output_dir_must_preexist_and_no_overwrite(self):

        root = self.make_dir()

        db_path = root / "state.db"

        with self.assertRaisesRegex(ValueError, "output_dir is missing"):

            run_wal_checkpoint_plan_audit(

                db_path=db_path,

                output_dir=root / "missing",

                policy=self.policy(),

            )

        run_wal_checkpoint_plan_audit(

            db_path=db_path,

            output_dir=root,

            policy=self.policy(),

            now_seconds=1000,

        )

        with self.assertRaisesRegex(ValueError, "already exists"):

            run_wal_checkpoint_plan_audit(

                db_path=db_path,

                output_dir=root,

                policy=self.policy(),

                now_seconds=1000,

            )

    def test_module_does_not_contain_forbidden_runtime_markers(self):

        source = Path("kernel/stores/sqlite/wal_checkpoint_plan_audit.py").read_text(

            encoding="utf-8"

        )

        for marker in (

            "PRAGMA wal_checkpoint",

            "wal_checkpoint(",

            "SQLITE_CHECKPOINT_TRUNCATE",

            ".executescript",

            "DELETE FROM",

            "UPDATE ",

            "INSERT INTO",

            "TRUNCATE",

            "sqlite3.connect",

            "os.system",

            "subprocess",

        ):

            self.assertNotIn(marker, source)

    def test_decision_doc_exists_and_records_integration_posture(self):

        text = Path("docs/decisions/wal_checkpoint_plan_audit_integration_v1.md").read_text(

            encoding="utf-8"

        )

        for marker in (

            "WAL_CHECKPOINT_PLAN_AUDIT_INTEGRATION_READY_FOR_LOCAL_TESTS",

            "non-mutating",

            "observation",

            "policy",

            "plan",

            "execution_allowed: false",

            "truncate_allowed: false",

            "mutating_checkpoint_executed: false",

        ):

            self.assertIn(marker, text)

if __name__ == "__main__":

    unittest.main()

