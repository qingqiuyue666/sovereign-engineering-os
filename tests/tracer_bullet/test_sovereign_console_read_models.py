"""Read-model tests for bounded Sovereign Console snapshots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.ui.read_models import ReadModelProvider, fake_phase1_snapshot
from kernel.os_engine.database import OSDatabase
from kernel.os_engine.sqlite_artifact_store import ArtifactType, SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue


class SovereignConsoleReadModelTests(unittest.TestCase):
    def test_fake_snapshot_is_safe_and_dashboard_ready(self) -> None:
        snapshot = fake_phase1_snapshot()
        self.assertEqual(snapshot.runtime_status, "Available")
        self.assertGreaterEqual(snapshot.queue_depth, 0)
        self.assertTrue(snapshot.latest_jobs)
        self.assertFalse(snapshot.is_sync_lost())

    def test_runtime_snapshot_reads_bounded_sqlite_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            runtime_root = Path(temp_dir_name)
            _seed_runtime(runtime_root)
            provider = ReadModelProvider(runtime_root=runtime_root, job_limit=10, event_limit=20)
            snapshot = provider.snapshot_runtime_status()

        self.assertTrue(snapshot.database_available)
        self.assertEqual(snapshot.wal_status, "WAL")
        self.assertEqual(snapshot.queue_depth, 1)
        self.assertEqual(len(snapshot.latest_jobs), 1)
        job = snapshot.latest_jobs[0]
        self.assertEqual(job.job_id, "ui_read_model_job")
        self.assertEqual(job.status, "Pending")
        self.assertEqual(job.worker, "git-worker")
        self.assertEqual(job.event_count, 4)
        self.assertEqual(job.artifact_count, 1)

    def test_selected_job_metadata_uses_limited_job_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            runtime_root = Path(temp_dir_name)
            _seed_runtime(runtime_root)
            provider = ReadModelProvider(runtime_root=runtime_root)
            snapshot = provider.snapshot_selected_job("ui_read_model_job")

        self.assertEqual(len(snapshot.latest_jobs), 1)
        metadata = snapshot.latest_jobs[0].metadata()
        self.assertEqual(metadata["job_id"], "ui_read_model_job")
        self.assertEqual(metadata["job_type"], "git")
        self.assertEqual(metadata["human_review_required"], False)

    def test_source_uses_limit_and_does_not_mutate_database(self) -> None:
        source = Path("apps/ui/read_models.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.upper().count("LIMIT"), 8)
        forbidden = ("INSERT ", "UPDATE ", "DELETE ", "CREATE ", "DROP ", "ALTER ", "REPLACE ")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source.upper())


def _seed_runtime(runtime_root: Path) -> None:
    database = OSDatabase(root=runtime_root, db_path=runtime_root / "os_engine.sqlite3")
    database.initialize()
    queue = SQLiteJobQueue(database)
    artifact_store = SQLiteArtifactStore(database=database, artifact_root=runtime_root / "artifacts")
    artifact_store.initialize()
    queue.create_job(
        job_id="ui_read_model_job",
        job_type="git",
        input_manifest={"command": ["git", "status", "--short"]},
        output_dir=str(runtime_root / "artifacts"),
        human_review_required=False,
        dry_run=True,
        local_only=True,
    )
    queue.admit_job("ui_read_model_job")
    queue.select_worker("ui_read_model_job", worker_name="git-worker")
    queue.enqueue_job("ui_read_model_job")
    artifact_path = runtime_root / "artifacts" / "read_model_summary.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('{"ok": true}\n', encoding="utf-8")
    artifact_store.record_artifact(
        job_id="ui_read_model_job",
        local_path=artifact_path,
        artifact_type=ArtifactType.AUDIT_JSON,
        local_only=True,
        safe_to_publish=False,
    )
    queue.close()
    artifact_store.close()
    database.close()


if __name__ == "__main__":
    unittest.main()
