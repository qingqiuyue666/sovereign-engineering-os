"""Acceptance tests for watchdog runtime integration V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
)
from kernel.runtime.watchdog_runtime_integration import (
    ZERO_HASH,
    FileBackedWatchdogRuntimeIntegration,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class WatchdogRuntimeIntegrationAcceptanceV1Tests(unittest.TestCase):
    def test_manual_sweep_records_stale_lease_recovery_and_operator_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = DurableJobQueue(
                path=root / "queue" / "jobs.jsonl",
                queue_id="watchdog-acceptance-queue",
            )
            queue.submit_job(
                job_id="job-watchdog-acceptance",
                task_id="task-watchdog-acceptance",
                run_id="run-watchdog-acceptance",
                payload={"task_descriptor_hash": _hash("acceptance-task")},
                idempotency_key="watchdog-acceptance-idempotency",
                max_attempts=2,
                submitted_at="2026-05-29T00:03:00+00:00",
            )
            queue.queue_job(
                "job-watchdog-acceptance",
                queued_at="2026-05-29T00:03:01+00:00",
            )
            leased = queue.lease_next(
                worker_id="worker-watchdog-acceptance",
                leased_at="2026-05-29T00:03:02+00:00",
                lease_timeout_seconds=5,
            )
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)

            receipt = runtime.run_manual_sweep(
                {
                    "elapsed_ms": 9_000,
                    "human_invoked": True,
                    "job_id": "job-watchdog-acceptance",
                    "lease_id": leased.lease_id,
                    "lease_timeout_seconds": 30,
                    "max_memory_mb": 256,
                    "max_runtime_ms": 60_000,
                    "observed_memory_mb": 128,
                    "previous_watchdog_receipt_hash": ZERO_HASH,
                    "recovery_plan_hash": _hash("acceptance-recovery"),
                    "retry_after": "2026-05-29T00:03:21+00:00",
                    "run_id": "run-watchdog-acceptance",
                    "snapshot_reconstruction_hash": _hash("acceptance-snapshot"),
                    "stderr_digest": _hash("acceptance-stderr"),
                    "stderr_truncated": False,
                    "stdout_digest": _hash("acceptance-stdout"),
                    "stdout_truncated": False,
                    "task_id": "task-watchdog-acceptance",
                    "watchdog_policy_hash": _hash("acceptance-policy"),
                    "worker_id": "worker-watchdog-acceptance",
                },
                queue,
                FileBackedFailureBundleCenterIntegration(runtime_root=root),
                FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root),
                observed_at="2026-05-29T00:03:20+00:00",
            )
            state = queue.get_job_state("job-watchdog-acceptance")
            operator_state = runtime.read_operator_watchdog_state("job-watchdog-acceptance")
            wal_records = FileBackedRealWalStorage(
                root / "watchdog-runtime" / "watchdog.real-wal.jsonl"
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertTrue(receipt.stale_lease_detected)
        self.assertTrue(receipt.stale_lease_recovered)
        self.assertTrue(receipt.retry_scheduled)
        self.assertEqual(state.state, "queued")
        self.assertEqual(operator_state.queue_state, "queued")
        self.assertNotEqual(receipt.failure_bundle_hash, ZERO_HASH)
        self.assertNotEqual(receipt.worker_quarantine_receipt_hash, ZERO_HASH)
        self.assertEqual(wal_records[0].record_type, "WATCHDOG_EVENT")
        self.assertFalse(receipt.background_daemon_enabled)


if __name__ == "__main__":
    unittest.main()
