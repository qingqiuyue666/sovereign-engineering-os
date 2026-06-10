"""Acceptance tests for Operator Console Runtime Surface V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.approval_runtime_contract import build_approval_runtime_request
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    FileBackedApprovalRuntimeIntegration,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
)
from kernel.runtime.operator_console_runtime_surface import (
    ZERO_HASH,
    FileBackedOperatorConsoleRuntimeSurface,
)
from kernel.runtime.watchdog_runtime_integration import (
    FileBackedWatchdogRuntimeIntegration,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import (
    FileBackedSnapshotReplayReconstructor,
)

TASK_ID = "task-acceptance-524"
RUN_ID = "run-acceptance-524"
JOB_ID = "job-acceptance-524"
WORKER_ID = "worker-acceptance-524"
QUEUE_ID = "queue-acceptance-524"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class OperatorConsoleRuntimeSurfaceAcceptanceV1Tests(unittest.TestCase):
    def test_console_reads_full_persisted_runtime_evidence_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            FileBackedRealWalStorage(root / "runtime-wal.jsonl").append(
                record_type="OPERATOR_CONSOLE_EVENT",
                task_id=TASK_ID,
                run_id=RUN_ID,
                payload_hash=_hash("console"),
                digest_bindings={"operator_console_policy_hash": _hash("policy")},
                created_at="2026-05-29T00:10:00+00:00",
            )
            approval_store = FileBackedApprovalRuntimeIntegration(
                runtime_root=root,
                artifact_store_relpath="approval-artifacts",
            )
            request_payload = _approval_request_payload()
            request = build_approval_runtime_request(
                request_payload,
                created_at="2026-05-29T00:10:01+00:00",
            )
            approval_store.issue_approval(
                request_payload=request_payload,
                decision_payload={
                    "approval_decision_id": "approval-decision-acceptance-524",
                    "approval_request_hash": request.request_hash,
                    "task_id": TASK_ID,
                    "run_id": RUN_ID,
                    "operator_id_hash": _hash("operator"),
                    "operator_action": "approved",
                    "decision_reason_code": "operator_explicit_decision",
                    "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
                    "rollback_plan_hash": None,
                    "human_attested": True,
                    "production_autonomy_enabled": False,
                    "live_execution_enabled": False,
                },
                expires_at="2026-05-29T02:00:00+00:00",
                issued_at="2026-05-29T00:10:01+00:00",
            )
            queue = DurableJobQueue(
                path=root / "queue" / "jobs.jsonl",
                queue_id=QUEUE_ID,
            )
            queue.submit_job(
                job_id=JOB_ID,
                task_id=TASK_ID,
                run_id=RUN_ID,
                payload={"task_descriptor_hash": _hash("task")},
                idempotency_key="acceptance-524",
                max_attempts=2,
                submitted_at="2026-05-29T00:10:02+00:00",
            )
            queue.queue_job(JOB_ID, queued_at="2026-05-29T00:10:03+00:00")
            leased = queue.lease_next(
                worker_id=WORKER_ID,
                leased_at="2026-05-29T00:10:04+00:00",
                lease_timeout_seconds=300,
            )
            watchdog_receipt = FileBackedWatchdogRuntimeIntegration(
                runtime_root=root
            ).record_heartbeat(
                {
                    "elapsed_ms": 1_000,
                    "human_invoked": False,
                    "job_id": JOB_ID,
                    "lease_id": leased.lease_id,
                    "lease_timeout_seconds": 300,
                    "max_memory_mb": 512,
                    "max_runtime_ms": 60_000,
                    "observed_memory_mb": 128,
                    "previous_watchdog_receipt_hash": ZERO_HASH,
                    "recovery_plan_hash": _hash("recovery"),
                    "retry_after": "2026-05-29T00:10:30+00:00",
                    "run_id": RUN_ID,
                    "snapshot_reconstruction_hash": _hash("snapshot"),
                    "stderr_digest": _hash("stderr"),
                    "stderr_truncated": False,
                    "stdout_digest": _hash("stdout"),
                    "stdout_truncated": False,
                    "task_id": TASK_ID,
                    "watchdog_policy_hash": _hash("watchdog-policy"),
                    "worker_id": WORKER_ID,
                },
                queue,
                observed_at="2026-05-29T00:10:05+00:00",
            )
            failure_receipt = FileBackedFailureBundleCenterIntegration(
                runtime_root=root
            ).record_critical_failure(
                failure_kind="missing_record",
                task_id=TASK_ID,
                job_id=JOB_ID,
                run_id=RUN_ID,
                context_hashes={
                    "missing_record_context_hash": _hash("missing-record"),
                    "wal_pointer_hash": watchdog_receipt.watchdog_wal_record_hash,
                },
                recovery_plan_hash=_hash("recovery"),
                snapshot_reconstruction_hash=_hash("snapshot"),
                observed_at="2026-05-29T00:10:06+00:00",
            )
            FileBackedWorkerRegistryCapabilityRuntime(
                runtime_root=root
            ).quarantine_worker(
                worker_id=WORKER_ID,
                reason="acceptance_missing_record",
                failure_bundle_hash=failure_receipt.bundle_digest,
                task_id=TASK_ID,
                run_id=RUN_ID,
                job_id=JOB_ID,
                observed_at="2026-05-29T00:10:07+00:00",
            )
            FileBackedSnapshotReplayReconstructor(
                runtime_root=root,
                wal_source_relpath="runtime-wal.jsonl",
                artifact_store_relpath="artifact-store",
                artifact_store_id="failure-bundle-center-artifacts-v1",
                queue_source_relpath="queue/jobs.jsonl",
                queue_id=QUEUE_ID,
            ).capture_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                created_at="2026-05-29T00:10:08+00:00",
                observed_at="2026-05-29T00:10:09+00:00",
            )

            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            snapshot = FileBackedOperatorConsoleRuntimeSurface(
                runtime_root=root,
                wal_source_relpaths=(
                    "runtime-wal.jsonl",
                    "queue/jobs.jsonl.real-wal.jsonl",
                    "approval-runtime/approval.real-wal.jsonl",
                    "artifact-store/artifact-store.real-wal.jsonl",
                    "failure-bundle-center/failure.real-wal.jsonl",
                    "worker-registry-runtime/worker-registry.real-wal.jsonl",
                    "watchdog-runtime/watchdog.real-wal.jsonl",
                ),
                queue_source_relpath="queue/jobs.jsonl",
                queue_id=QUEUE_ID,
                artifact_store_relpath="artifact-store",
                artifact_store_id="failure-bundle-center-artifacts-v1",
            ).read_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                observed_at="2026-05-29T00:10:10+00:00",
            )
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

        panel_by_id = {panel.panel_id: panel for panel in snapshot.panels}
        self.assertEqual(snapshot.status, "ok")
        self.assertTrue(snapshot.read_only)
        self.assertFalse(snapshot.direct_console_edits_enabled)
        self.assertFalse(snapshot.mutation_enabled)
        self.assertEqual(before, after)
        for panel_id in (
            "wal",
            "queue",
            "artifacts",
            "approvals",
            "failures",
            "replay",
            "workers",
            "watchdog",
        ):
            self.assertEqual(panel_by_id[panel_id].status, "ok", panel_id)
            self.assertGreater(panel_by_id[panel_id].record_count, 0, panel_id)


def _approval_request_payload() -> dict[str, object]:
    return {
        "approval_request_id": "approval-request-acceptance-524",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "review_packet_hash": _hash("review"),
        "promotion_receipt_hash": _hash("promotion"),
        "wal_head_hash": _hash("wal-head"),
        "artifact_manifest_hash": _hash("artifact-manifest"),
        "snapshot_reconstruction_hash": _hash("snapshot"),
        "capability_token_hash": _hash("capability"),
        "risk_decision_hash": _hash("risk"),
        "requested_action": "approve_next_manual_stage",
        "human_invoked": True,
        "production_autonomy_requested": False,
        "live_execution_requested": False,
    }


if __name__ == "__main__":
    unittest.main()
