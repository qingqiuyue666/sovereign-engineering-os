"""Tracer bullet tests for Durable Job Queue Implementation V1."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.durable_job_queue import (
    REAL_WAL_BINDING_BLOCKER,
    DurableJobQueue,
    DurableJobQueueDuplicateError,
    DurableJobQueueError,
    DurableJobQueueReplayError,
    DurableJobQueueTransitionError,
)


SOURCE_PATH = Path("kernel/runtime/durable_job_queue.py")


class DurableJobQueueImplementationV1Tests(unittest.TestCase):
    def test_submit_queue_lease_success_persists_and_replays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.jsonl"
            queue = DurableJobQueue(path=path, queue_id="queue-001")

            queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "acceptance_fixture"},
                idempotency_key="idem-001",
                submitted_at="2026-05-27T00:00:00+00:00",
            )
            queue.queue_job("job-001", queued_at="2026-05-27T00:00:01+00:00")
            leased = queue.lease_next(
                worker_id="worker-001",
                leased_at="2026-05-27T00:00:02+00:00",
            )
            succeeded = queue.succeed_job(
                job_id="job-001",
                lease_id=leased.lease_id,
                completion_payload={"completion_ref": "receipt-001"},
                succeeded_at="2026-05-27T00:00:03+00:00",
            )

            reopened = DurableJobQueue(path=path, queue_id="queue-001")

            self.assertEqual(succeeded.state, "succeeded")
            self.assertTrue(reopened.projection.accepted)
            self.assertEqual(reopened.get_job_state("job-001").state, "succeeded")
            self.assertEqual(len(reopened.events), 4)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 4)
            self.assertFalse(reopened.wal_binding_status().available)
            self.assertEqual(reopened.wal_binding_status().blocker, REAL_WAL_BINDING_BLOCKER)

    def test_event_hashes_are_deterministic_for_supplied_material(self) -> None:
        event_hashes: list[str] = []
        record_hashes: list[str] = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                queue = DurableJobQueue(path=Path(tmp) / "queue.jsonl", queue_id="queue-001")
                queue.submit_job(
                    job_id="job-001",
                    task_id="task-001",
                    run_id="run-001",
                    payload={"kind": "deterministic"},
                    idempotency_key="idem-001",
                    submitted_at="2026-05-27T00:00:00+00:00",
                )
                event_hashes.append(queue.events[0].event_hash)
                record_hashes.append(queue.records[0].record_hash)

        self.assertEqual(event_hashes[0], event_hashes[1])
        self.assertEqual(record_hashes[0], record_hashes[1])

    def test_idempotency_duplicate_is_noop_and_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = DurableJobQueue(path=Path(tmp) / "queue.jsonl", queue_id="queue-001")
            first = queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "duplicate"},
                idempotency_key="idem-001",
            )
            second = queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "duplicate"},
                idempotency_key="idem-001",
            )

            self.assertEqual(first.last_event_hash, second.last_event_hash)
            self.assertEqual(len(queue.records), 1)
            with self.assertRaises(DurableJobQueueDuplicateError):
                queue.submit_job(
                    job_id="job-002",
                    task_id="task-001",
                    run_id="run-001",
                    payload={"kind": "changed"},
                    idempotency_key="idem-001",
                )

    def test_retry_and_dead_letter_lifecycle_is_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = DurableJobQueue(path=Path(tmp) / "queue.jsonl", queue_id="queue-001")
            queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "retry"},
                idempotency_key="idem-001",
                max_attempts=2,
                submitted_at="2026-05-27T00:00:00+00:00",
            )
            queue.queue_job("job-001", queued_at="2026-05-27T00:00:01+00:00")
            first_lease = queue.lease_next(
                worker_id="worker-001",
                leased_at="2026-05-27T00:00:02+00:00",
            )
            retry = queue.fail_job(
                job_id="job-001",
                lease_id=first_lease.lease_id,
                reason="transient_failure",
                failed_at="2026-05-27T00:00:03+00:00",
                retry_after="2026-05-27T00:00:04+00:00",
            )
            second_lease = queue.lease_next(
                worker_id="worker-001",
                leased_at="2026-05-27T00:00:05+00:00",
            )
            dead = queue.fail_job(
                job_id="job-001",
                lease_id=second_lease.lease_id,
                reason="max_attempts_exhausted",
                failed_at="2026-05-27T00:00:06+00:00",
            )

            reopened = DurableJobQueue(path=Path(tmp) / "queue.jsonl", queue_id="queue-001")

            self.assertEqual(retry.state, "queued")
            self.assertEqual(dead.state, "dead_lettered")
            self.assertEqual(dead.dead_letter_reason, "max_attempts_exhausted")
            self.assertEqual(reopened.get_job_state("job-001").state, "dead_lettered")
            self.assertEqual(len(reopened.events), 6)

    def test_expired_lease_recovery_is_manual_retry_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = DurableJobQueue(path=Path(tmp) / "queue.jsonl", queue_id="queue-001")
            queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "lease_recovery"},
                idempotency_key="idem-001",
                max_attempts=2,
                submitted_at="2026-05-27T00:00:00+00:00",
            )
            queue.queue_job("job-001", queued_at="2026-05-27T00:00:01+00:00")
            queue.lease_next(
                worker_id="worker-001",
                leased_at="2026-05-27T00:00:02+00:00",
                lease_timeout_seconds=5,
            )

            recovered = queue.recover_expired_leases(now="2026-05-27T00:00:08+00:00")
            second_recovery = queue.recover_expired_leases(now="2026-05-27T00:00:09+00:00")

            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0].state, "queued")
            self.assertEqual(second_recovery, ())
            self.assertEqual(len(queue.events), 4)

    def test_invalid_transition_secret_payload_and_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.jsonl"
            queue = DurableJobQueue(path=path, queue_id="queue-001")
            queue.submit_job(
                job_id="job-001",
                task_id="task-001",
                run_id="run-001",
                payload={"kind": "guard"},
                idempotency_key="idem-001",
            )
            with self.assertRaises(DurableJobQueueTransitionError):
                queue.succeed_job(job_id="job-001", lease_id="lease-missing")
            with self.assertRaises(DurableJobQueueError):
                queue.submit_job(
                    job_id="job-002",
                    task_id="task-001",
                    run_id="run-001",
                    payload={"env": {"TOKEN": "blocked"}},
                    idempotency_key="idem-002",
                )

            raw = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            raw["record_hash"] = "sha256:" + ("0" * 64)
            path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(DurableJobQueueReplayError):
                DurableJobQueue(path=path, queue_id="queue-001")

    def test_source_has_no_runtime_autonomy_or_pr514_import(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertFalse(
            imported_roots.intersection(
                {
                    "argparse",
                    "asyncio",
                    "httpx",
                    "openai",
                    "playwright",
                    "requests",
                    "schedule",
                    "selenium",
                    "socket",
                    "subprocess",
                    "threading",
                    "urllib",
                    "webbrowser",
                }
            )
        )
        self.assertNotIn("kernel.stores.real_wal_storage", source)
        self.assertNotIn("while True", source)


if __name__ == "__main__":
    unittest.main()
