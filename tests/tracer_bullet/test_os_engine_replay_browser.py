"""Read-only tests for the OS engine replay browser."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase
from kernel.os_engine.replay_browser import (
    ReplayBrowserFilter,
    browse_os_engine_replay,
    render_replay_browser_summary,
)
from kernel.os_engine.sqlite_artifact_store import ArtifactType, SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue
from tools.os_engine_replay_browser import main as replay_browser_main


class OSEngineReplayBrowserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_name = "brain.sqlite3"
        self.database = OSDatabase(root=self.root, db_path=self.root / self.db_name)
        self.queue = SQLiteJobQueue(self.database)
        self.artifact_store = SQLiteArtifactStore(
            database=self.database,
            artifact_root=self.root / "artifacts",
        )
        self.artifact_store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _record_successful_job(self, job_id: str = "job_replay_browser") -> str:
        self.queue.create_job(job_id=job_id, job_type="replay_browser_test", input_manifest={"asset": "HFX_008"})
        self.queue.admit_job(job_id)
        self.queue.select_worker(job_id, worker_name="ReplayBrowserWorker")
        self.queue.enqueue_job(job_id)
        self.queue.start_job(job_id)
        artifact_path = self.root / "artifacts" / f"{job_id}.json"
        artifact_path.write_text('{"ok": true}\n', encoding="utf-8")
        artifact = self.artifact_store.record_artifact(
            job_id=job_id,
            local_path=artifact_path,
            artifact_type=ArtifactType.MATERIALIZATION_SUMMARY,
        )
        self.queue.mark_artifact_discovered(job_id, artifact_id=artifact.artifact_id)
        self.queue.mark_artifact_validated(job_id, artifact_id=artifact.artifact_id)
        self.queue.succeed_job(job_id, artifact_ids=[artifact.artifact_id])
        return artifact_path.as_posix()

    def _db_counts(self) -> dict[str, int]:
        with sqlite3.connect(self.root / self.db_name) as connection:
            return {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("jobs", "job_events", "artifacts")
            }

    def test_replay_browser_returns_hash_bound_projection_without_mutating(self) -> None:
        artifact_path = self._record_successful_job()
        before = self._db_counts()

        summary = browse_os_engine_replay(
            self.root,
            ReplayBrowserFilter(job_id="job_replay_browser"),
            db_name=self.db_name,
        )
        rendered = render_replay_browser_summary(summary)

        self.assertTrue(summary.accepted)
        self.assertEqual(summary.job_count, 1)
        self.assertEqual(summary.returned_trace_count, 1)
        self.assertEqual(summary.traces[0].stored_status, "succeeded")
        self.assertEqual(summary.traces[0].projected_status, "succeeded")
        self.assertEqual(summary.traces[0].replay_classification, "exact_event_projection")
        self.assertTrue(summary.traces[0].final_claim_allowed)
        self.assertTrue(summary.traces[0].job_content_hash_valid)
        self.assertTrue(all(event.content_hash_valid for event in summary.traces[0].events))
        self.assertTrue(all(artifact.content_hash_valid for artifact in summary.traces[0].artifacts))
        self.assertFalse(summary.mutation_performed)
        self.assertFalse(summary.execution_performed)
        self.assertFalse(summary.network_accessed)
        self.assertFalse(summary.browser_launched)
        self.assertNotIn(artifact_path, rendered)
        self.assertEqual(before, self._db_counts())

    def test_missing_database_and_missing_job_fail_closed(self) -> None:
        missing = browse_os_engine_replay(self.root / "missing", db_name=self.db_name)
        self.assertFalse(missing.accepted)
        self.assertEqual(missing.failure_codes, ("database_missing",))

        self._record_successful_job()
        missing_job = browse_os_engine_replay(
            self.root,
            ReplayBrowserFilter(job_id="not_recorded"),
            db_name=self.db_name,
        )
        self.assertFalse(missing_job.accepted)
        self.assertIn("job_not_found", missing_job.failure_codes)

    def test_tampered_event_hash_rejects_trace(self) -> None:
        self._record_successful_job()
        with sqlite3.connect(self.root / self.db_name) as connection:
            connection.execute(
                "UPDATE job_events SET content_hash = ? WHERE job_id = ? AND sequence = 2",
                ("0" * 64, "job_replay_browser"),
            )

        summary = browse_os_engine_replay(
            self.root,
            ReplayBrowserFilter(job_id="job_replay_browser"),
            db_name=self.db_name,
        )

        self.assertFalse(summary.accepted)
        self.assertEqual(summary.traces[0].replay_classification, "diagnostic_rejected")
        self.assertIn("event_content_hash_mismatch", summary.traces[0].failure_codes)
        self.assertIn("event_content_hash_mismatch", summary.failure_codes)

    def test_malformed_event_payload_rejects_summary_without_raw_display(self) -> None:
        self._record_successful_job()
        with sqlite3.connect(self.root / self.db_name) as connection:
            connection.execute(
                "UPDATE job_events SET payload_json = ? WHERE job_id = ? AND sequence = 1",
                ("[]", "job_replay_browser"),
            )

        summary = browse_os_engine_replay(
            self.root,
            ReplayBrowserFilter(job_id="job_replay_browser"),
            db_name=self.db_name,
        )
        rendered = render_replay_browser_summary(summary)

        self.assertFalse(summary.accepted)
        self.assertIn("event_payload_must_be_object", summary.failure_codes)
        self.assertFalse(summary.raw_secret_displayed)
        self.assertNotIn("payload_json", rendered)

    def test_cli_prints_read_only_summary(self) -> None:
        self._record_successful_job()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = replay_browser_main_with_args(
                [
                    self.root.as_posix(),
                    "--db-name",
                    self.db_name,
                    "--job-id",
                    "job_replay_browser",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["accepted"])
        self.assertFalse(payload["mutation_performed"])
        self.assertFalse(payload["deletion_performed"])
        self.assertEqual(payload["traces"][0]["projected_status"], "succeeded")

    def test_source_has_no_execution_network_or_browser_launch_surface(self) -> None:
        source = Path("kernel/os_engine/replay_browser.py").read_text(encoding="utf-8")
        cli_source = Path("tools/os_engine_replay_browser.py").read_text(encoding="utf-8")
        combined = source + "\n" + cli_source

        for marker in (
            "subprocess",
            "requests.",
            "urllib.",
            "webbrowser",
            "socket",
            "open_browser",
            "launch_browser",
            "Popen",
            "system(",
        ):
            self.assertNotIn(marker, combined)


def replay_browser_main_with_args(args: list[str]) -> int:
    import sys

    original = sys.argv
    try:
        sys.argv = ["os_engine_replay_browser.py", *args]
        return replay_browser_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    unittest.main()
