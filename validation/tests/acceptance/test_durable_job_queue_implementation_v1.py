"""Acceptance tests for Durable Job Queue Implementation V1."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.durable_job_queue import (
    REAL_WAL_BINDING_STATUS,
    DurableJobQueue,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


class DurableJobQueueImplementationAcceptanceV1Tests(unittest.TestCase):
    def test_queue_replays_durable_lifecycle_and_records_real_wal_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "durable-queue.jsonl"
            queue = DurableJobQueue(path=path, queue_id="acceptance-queue")
            queue.submit_job(
                job_id="job-acceptance",
                task_id="task-acceptance",
                run_id="run-acceptance",
                payload={"workload": "bounded_acceptance"},
                idempotency_key="acceptance-idempotency-key",
                max_attempts=2,
                submitted_at="2026-05-27T00:00:00+00:00",
            )
            queue.queue_job("job-acceptance", queued_at="2026-05-27T00:00:01+00:00")
            first_lease = queue.lease_next(
                worker_id="acceptance-worker",
                leased_at="2026-05-27T00:00:02+00:00",
                lease_timeout_seconds=5,
            )
            queue.fail_job(
                job_id="job-acceptance",
                lease_id=first_lease.lease_id,
                reason="acceptance_retry",
                failed_at="2026-05-27T00:00:03+00:00",
                retry_after="2026-05-27T00:00:04+00:00",
            )
            second_lease = queue.lease_next(
                worker_id="acceptance-worker",
                leased_at="2026-05-27T00:00:05+00:00",
                lease_timeout_seconds=5,
            )
            queue.succeed_job(
                job_id="job-acceptance",
                lease_id=second_lease.lease_id,
                completion_payload={"completion_ref": "acceptance-receipt"},
                succeeded_at="2026-05-27T00:00:06+00:00",
            )

            reopened = DurableJobQueue(path=path, queue_id="acceptance-queue")
            state = reopened.get_job_state("job-acceptance")
            summary = reopened.summary()
            wal_records = FileBackedRealWalStorage(reopened.wal_path).read_records()

            self.assertTrue(reopened.projection.accepted)
            self.assertEqual(state.state, "succeeded")
            self.assertEqual(state.attempt, 2)
            self.assertEqual(summary["event_count"], 6)
            self.assertEqual(summary["real_wal_binding_status"], REAL_WAL_BINDING_STATUS)
            self.assertEqual(len(wal_records), 6)
            self.assertEqual(
                [event.wal_record_hash for event in reopened.events],
                [record.record_hash for record in wal_records],
            )
            self.assertTrue(reopened.wal_binding_status().available)
            self.assertEqual(reopened.wal_binding_status().blocker, "")


if __name__ == "__main__":
    unittest.main()
