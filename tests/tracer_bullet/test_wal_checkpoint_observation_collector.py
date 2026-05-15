import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kernel.stores.sqlite.wal_checkpoint_observation_collector import (
    collect_wal_checkpoint_observation,
    write_wal_checkpoint_observation,
)
from kernel.stores.sqlite.wal_checkpoint_policy import build_wal_checkpoint_plan


class WalCheckpointObservationCollectorTests(unittest.TestCase):
    def make_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_missing_wal_uses_zero_metadata_without_opening_database(self):
        root = self.make_dir()
        db_path = root / "state.db"

        result = collect_wal_checkpoint_observation(
            db_path=db_path,
            now_seconds=1000,
            snapshot_creation_pending=False,
        )

        self.assertEqual(result.observation.wal_pages, 0)
        self.assertEqual(result.observation.wal_bytes, 0)
        self.assertEqual(result.observation.age_seconds, 0)
        self.assertFalse(result.database_opened_read_only)
        self.assertFalse(result.checkpoint_executed)
        self.assertFalse(result.wal_truncate_executed)
        self.assertFalse(result.sqlite_state_mutated)
        self.assertFalse(result.payload["checkpoint_executed"])
        self.assertFalse(result.payload["pragma_wal_checkpoint_executed"])
        self.assertFalse(result.payload["wal_truncate_executed"])
        self.assertFalse(result.payload["sqlite_state_mutated"])

    def test_existing_wal_metadata_is_collected_with_override_page_size(self):
        root = self.make_dir()
        db_path = root / "state.sqlite"
        wal_path = root / "state.sqlite-wal"
        db_path.write_bytes(b"sqlite-placeholder")
        wal_path.write_bytes(b"x" * 9000)
        os.utime(wal_path, (400, 400))

        result = collect_wal_checkpoint_observation(
            db_path=db_path,
            now_seconds=1000,
            snapshot_creation_pending=True,
            dirty_tail_detected=True,
            mid_segment_corruption_detected=False,
            page_size_override=4096,
        )

        self.assertEqual(result.observation.wal_bytes, 9000)
        self.assertEqual(result.observation.wal_pages, 3)
        self.assertEqual(result.observation.age_seconds, 600)
        self.assertTrue(result.observation.snapshot_creation_pending)
        self.assertTrue(result.observation.dirty_tail_detected)
        self.assertFalse(result.observation.mid_segment_corruption_detected)
        self.assertFalse(result.database_opened_read_only)
        self.assertEqual(result.payload["page_size"], 4096)
        self.assertEqual(result.payload["estimated_wal_pages"], 3)

    def test_readonly_page_size_probe_uses_sqlite_metadata_without_mutation(self):
        root = self.make_dir()
        db_path = root / "state.sqlite3"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("PRAGMA page_size=8192;")
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY);")
            conn.commit()
        finally:
            conn.close()
        wal_path = root / "state.sqlite3-wal"
        wal_path.write_bytes(b"x" * 9000)

        result = collect_wal_checkpoint_observation(
            db_path=db_path,
            now_seconds=1000,
            snapshot_creation_pending=False,
            allow_readonly_page_size_query=True,
        )

        self.assertEqual(result.observation.wal_pages, 2)
        self.assertTrue(result.database_opened_read_only)
        self.assertFalse(result.sqlite_state_mutated)
        self.assertFalse(result.checkpoint_executed)
        self.assertFalse(result.wal_truncate_executed)
        self.assertEqual(result.payload["page_size"], 8192)
        self.assertTrue(result.payload["database_opened_read_only"])
        self.assertFalse(result.payload["database_opened_for_write"])
        self.assertFalse(result.payload["write_transaction_opened"])

    def test_collected_observation_feeds_existing_checkpoint_planner(self):
        root = self.make_dir()
        db_path = root / "state.db"
        wal_path = root / "state.db-wal"
        wal_path.write_bytes(b"x" * 8192)

        observation = collect_wal_checkpoint_observation(
            db_path=db_path,
            now_seconds=1000,
            snapshot_creation_pending=True,
            page_size_override=4096,
        ).observation
        plan = build_wal_checkpoint_plan(
            {
                "policy_id": "wal-policy-v1",
                "max_wal_pages": 2,
                "max_wal_bytes": 100_000,
                "max_age_seconds": 9999,
                "trigger_on_snapshot": True,
                "manual_checkpoint_allowed": True,
                "truncate_allowed": False,
                "created_at": "2026-05-15T00:00:00Z",
                "version": "v1",
            },
            observation,
        )

        self.assertTrue(plan.checkpoint_required)
        self.assertIn("wal_pages_threshold_reached", plan.plan["reason_codes"])
        self.assertIn("snapshot_trigger_pending", plan.plan["reason_codes"])
        self.assertFalse(plan.execution_allowed)
        self.assertFalse(plan.mutating_checkpoint_executed)

    def test_write_observation_requires_preexisting_output_dir_and_no_overwrite(self):
        root = self.make_dir()
        db_path = root / "state.db"
        with self.assertRaisesRegex(ValueError, "output_dir is missing"):
            write_wal_checkpoint_observation(
                db_path=db_path,
                output_dir=root / "missing",
                now_seconds=1000,
            )

        result = write_wal_checkpoint_observation(
            db_path=db_path,
            output_dir=root,
            now_seconds=1000,
            snapshot_creation_pending=True,
        )
        self.assertIsNotNone(result.observation_path)
        payload = json.loads((root / "wal_checkpoint_observation.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["observation_type"], "seos_wal_checkpoint_observation_v1")
        self.assertTrue(payload["snapshot_creation_pending"])
        self.assertTrue(payload["planner_compatible"])

        with self.assertRaisesRegex(ValueError, "already exists"):
            write_wal_checkpoint_observation(
                db_path=db_path,
                output_dir=root,
                now_seconds=1000,
            )

    def test_rejects_invalid_inputs(self):
        root = self.make_dir()
        with self.assertRaisesRegex(ValueError, "db_path suffix is not allowed"):
            collect_wal_checkpoint_observation(db_path=root / "state.txt", now_seconds=1)
        with self.assertRaisesRegex(ValueError, "now_seconds must be integer"):
            collect_wal_checkpoint_observation(db_path=root / "state.db", now_seconds=True)
        with self.assertRaisesRegex(ValueError, "now_seconds must be non-negative"):
            collect_wal_checkpoint_observation(db_path=root / "state.db", now_seconds=-1)
        with self.assertRaisesRegex(ValueError, "snapshot_creation_pending must be boolean"):
            collect_wal_checkpoint_observation(
                db_path=root / "state.db",
                now_seconds=1,
                snapshot_creation_pending="yes",
            )
        with self.assertRaisesRegex(ValueError, "page_size_override must be positive"):
            collect_wal_checkpoint_observation(
                db_path=root / "state.db",
                now_seconds=1,
                page_size_override=0,
            )

    def test_rejects_symlink_db_path(self):
        root = self.make_dir()
        target = root / "target.db"
        target.write_bytes(b"placeholder")
        link = root / "link.db"
        link.symlink_to(target)

        with self.assertRaisesRegex(ValueError, "symlink is forbidden"):
            collect_wal_checkpoint_observation(db_path=link, now_seconds=1)

    def test_collector_module_does_not_execute_checkpoint_or_truncate(self):
        module = Path("kernel/stores/sqlite/wal_checkpoint_observation_collector.py").read_text(
            encoding="utf-8"
        )
        forbidden_runtime_markers = (
            "PRAGMA wal_checkpoint",
            "wal_checkpoint(",
            "SQLITE_CHECKPOINT_TRUNCATE",
            ".executescript",
            "DELETE FROM",
            "UPDATE ",
            "INSERT INTO",
            "TRUNCATE",
        )
        for marker in forbidden_runtime_markers:
            self.assertNotIn(marker, module)
        self.assertIn("PRAGMA page_size;", module)
        self.assertIn("mode=ro", module)

    def test_decision_doc_exists_and_records_observation_only_posture(self):
        text = Path("docs/decisions/wal_checkpoint_observation_collector_v1.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "WAL_CHECKPOINT_OBSERVATION_COLLECTOR_READY_FOR_LOCAL_TESTS",
            "observation-only",
            "does not execute checkpoint",
            "does not truncate WAL",
            "does not mutate SQLite state",
            "wal_checkpoint_plan",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
