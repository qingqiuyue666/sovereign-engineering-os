"""Tracer bullet tests for the SQLite-backed durable job queue."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase, UnsafePayloadError
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue, SQLiteJobQueueError, projected_jobs_to_json


class OSEngineSQLiteJobQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3")
        self.queue = SQLiteJobQueue(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _created(self, job_id: str = "job_queue", *, human_review_required: bool = False, dry_run: bool = False) -> None:
        self.queue.create_job(
            job_id=job_id,
            job_type="test",
            input_manifest={"asset": "HFX_008"},
            human_review_required=human_review_required,
            dry_run=dry_run,
        )

    def test_create_enqueue_start_succeed_path(self) -> None:
        self._created()
        self.queue.admit_job("job_queue")
        self.queue.select_worker("job_queue", worker_name="TestWorker")
        self.queue.enqueue_job("job_queue")
        self.queue.start_job("job_queue")
        self.queue.mark_artifact_discovered("job_queue", artifact_id="artifact_1")
        self.queue.mark_artifact_validated("job_queue", artifact_id="artifact_1")
        self.queue.succeed_job("job_queue", artifact_ids=["artifact_1"])
        state = self.queue.get_job_state("job_queue")
        self.assertEqual(state.current_status, "succeeded")
        self.assertTrue(state.final_claim_allowed)

    def test_failure_and_quarantine_paths_require_reasons(self) -> None:
        self._created("job_failed")
        self.queue.admit_job("job_failed")
        with self.assertRaises(SQLiteJobQueueError):
            self.queue.fail_job("job_failed", reason="")
        self.queue.fail_job("job_failed", reason="unit failure")
        self.assertEqual(self.queue.get_job_state("job_failed").current_status, "failed")

        self._created("job_quarantine")
        self.queue.admit_job("job_quarantine")
        self.queue.enqueue_job("job_quarantine")
        with self.assertRaises(SQLiteJobQueueError):
            self.queue.quarantine_job("job_quarantine", reason="")
        self.queue.quarantine_job("job_quarantine", reason="unsafe output")
        self.assertEqual(self.queue.get_job_state("job_quarantine").current_status, "quarantined")

    def test_human_review_path_preserves_required_gate(self) -> None:
        self._created("job_review", human_review_required=True)
        self.queue.admit_job("job_review")
        self.queue.enqueue_job("job_review")
        self.queue.start_job("job_review")
        self.queue.mark_artifact_discovered("job_review", artifact_id="artifact_review")
        self.queue.request_human_review("job_review", artifact_id="artifact_review", reason="visual review")
        state = self.queue.get_job_state("job_review")
        self.assertEqual(state.current_status, "requires_human_review")
        self.assertTrue(state.human_review_required)
        self.queue.approve_human_review("job_review", artifact_id="artifact_review", reviewer="operator")
        self.queue.succeed_job("job_review", artifact_ids=["artifact_review"])
        self.assertTrue(self.queue.get_job_state("job_review").final_claim_allowed)

    def test_dry_run_physical_proof_claim_is_blocked(self) -> None:
        self._created("job_dry", dry_run=True)
        self.queue.admit_job("job_dry")
        self.queue.enqueue_job("job_dry")
        self.queue.start_job("job_dry")
        self.queue.mark_artifact_discovered("job_dry", artifact_id="artifact_dry")
        with self.assertRaises(SQLiteJobQueueError):
            self.queue.succeed_job("job_dry", artifact_ids=["artifact_dry"], physical_proof=True)

    def test_replay_after_reopen_returns_same_state(self) -> None:
        self._created()
        self.queue.admit_job("job_queue")
        self.queue.enqueue_job("job_queue")
        first_hash = self.queue.deterministic_snapshot_hash()
        reopened = SQLiteJobQueue(OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3"))
        self.assertEqual(first_hash, reopened.deterministic_snapshot_hash())
        self.assertEqual(reopened.get_job_state("job_queue").current_status, "pending")

    def test_illegal_transition_secret_payload_and_deterministic_serialization_are_rejected_or_stable(self) -> None:
        self._created()
        with self.assertRaises(SQLiteJobQueueError):
            self.queue.start_job("job_queue")
        with self.assertRaises(UnsafePayloadError):
            self.queue.create_job(job_id="job_secret", job_type="test", input_manifest={"env": {"TOKEN": "raw"}})
        self.queue.admit_job("job_queue")
        once = projected_jobs_to_json(self.queue.list_jobs())
        twice = projected_jobs_to_json(self.queue.list_jobs())
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
