"""
Replay Browser Readonly V1 acceptance.

The replay browser must reconstruct OS-engine job history from captured WAL
records without mutating storage or exceeding captured evidence.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase
from kernel.os_engine.replay_browser import ReplayBrowserFilter, browse_os_engine_replay
from kernel.os_engine.sqlite_artifact_store import ArtifactType, SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue


class ReplayBrowserReadonlyAcceptanceTests(unittest.TestCase):
    def test_browser_reconstructs_job_trace_readonly_and_rejects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_name = "acceptance.sqlite3"
            database = OSDatabase(root=root, db_path=root / db_name)
            queue = SQLiteJobQueue(database)
            store = SQLiteArtifactStore(database=database, artifact_root=root / "artifacts")
            store.initialize()

            queue.create_job(job_id="job_acceptance", job_type="acceptance", input_manifest={"asset": "HFX_008"})
            queue.admit_job("job_acceptance")
            queue.enqueue_job("job_acceptance")
            queue.start_job("job_acceptance")
            artifact_path = root / "artifacts" / "acceptance.json"
            artifact_path.write_text('{"accepted": true}\n', encoding="utf-8")
            artifact = store.record_artifact(
                job_id="job_acceptance",
                local_path=artifact_path,
                artifact_type=ArtifactType.MATERIALIZATION_SUMMARY,
            )
            queue.mark_artifact_discovered("job_acceptance", artifact_id=artifact.artifact_id)
            queue.mark_artifact_validated("job_acceptance", artifact_id=artifact.artifact_id)
            queue.succeed_job("job_acceptance", artifact_ids=[artifact.artifact_id])

            before = _counts(root / db_name)
            accepted = browse_os_engine_replay(
                root,
                ReplayBrowserFilter(job_id="job_acceptance"),
                db_name=db_name,
            )

            self.assertTrue(accepted.accepted)
            self.assertEqual(accepted.traces[0].projected_status, "succeeded")
            self.assertEqual(accepted.traces[0].event_count, 7)
            self.assertTrue(accepted.traces[0].audit_hash)
            self.assertFalse(accepted.mutation_performed)
            self.assertFalse(accepted.execution_performed)
            self.assertEqual(before, _counts(root / db_name))

            with sqlite3.connect(root / db_name) as connection:
                connection.execute(
                    "UPDATE jobs SET current_status = ? WHERE job_id = ?",
                    ("running", "job_acceptance"),
                )

            rejected = browse_os_engine_replay(
                root,
                ReplayBrowserFilter(job_id="job_acceptance"),
                db_name=db_name,
            )

            self.assertFalse(rejected.accepted)
            self.assertIn("job_status_projection_mismatch", rejected.failure_codes)
            self.assertEqual(rejected.traces[0].replay_classification, "diagnostic_rejected")


def _counts(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("jobs", "job_events", "artifacts")
        }


if __name__ == "__main__":
    unittest.main()
