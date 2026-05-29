"""Tests for operator console runtime surface V1."""

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
    admit_operator_console_mutation_route,
    validate_operator_console_runtime_snapshot,
)
from kernel.runtime.watchdog_runtime_integration import (
    FileBackedWatchdogRuntimeIntegration,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import (
    FileBackedSnapshotReplayReconstructor,
)

SOURCE_PATH = Path("kernel/runtime/operator_console_runtime_surface.py")
TASK_ID = "task-524"
RUN_ID = "run-524"
JOB_ID = "job-524"
WORKER_ID = "worker-524"
QUEUE_ID = "queue-524"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _approval_payloads() -> tuple[dict[str, object], dict[str, object]]:
    request = {
        "approval_request_id": "approval-request-524",
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
    built = build_approval_runtime_request(
        request,
        created_at="2026-05-29T00:00:00+00:00",
    )
    decision = {
        "approval_decision_id": "approval-decision-524",
        "approval_request_hash": built.request_hash,
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
    }
    return request, decision


def _build_evidence(root: Path) -> FileBackedOperatorConsoleRuntimeSurface:
    FileBackedRealWalStorage(root / "runtime-wal.jsonl").append(
        record_type="OPERATOR_CONSOLE_EVENT",
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload_hash=_hash("console-evidence"),
        digest_bindings={"console_policy_hash": _hash("console-policy")},
        created_at="2026-05-29T00:00:00+00:00",
    )

    approval_store = FileBackedApprovalRuntimeIntegration(
        runtime_root=root,
        artifact_store_relpath="approval-artifacts",
    )
    request, decision = _approval_payloads()
    approval_store.issue_approval(
        request_payload=request,
        decision_payload=decision,
        expires_at="2026-05-29T02:00:00+00:00",
        issued_at="2026-05-29T00:00:01+00:00",
    )

    queue = DurableJobQueue(path=root / "queue" / "jobs.jsonl", queue_id=QUEUE_ID)
    queue.submit_job(
        job_id=JOB_ID,
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload={"task_descriptor_hash": _hash("task")},
        idempotency_key="idempotency-524",
        max_attempts=2,
        submitted_at="2026-05-29T00:00:02+00:00",
    )
    queue.queue_job(JOB_ID, queued_at="2026-05-29T00:00:03+00:00")
    leased = queue.lease_next(
        worker_id=WORKER_ID,
        leased_at="2026-05-29T00:00:04+00:00",
        lease_timeout_seconds=5,
    )

    FileBackedWatchdogRuntimeIntegration(runtime_root=root).run_manual_sweep(
        {
            "elapsed_ms": 9_000,
            "human_invoked": True,
            "job_id": JOB_ID,
            "lease_id": leased.lease_id,
            "lease_timeout_seconds": 30,
            "max_memory_mb": 256,
            "max_runtime_ms": 60_000,
            "observed_memory_mb": 128,
            "previous_watchdog_receipt_hash": ZERO_HASH,
            "recovery_plan_hash": _hash("recovery"),
            "retry_after": "2026-05-29T00:00:20+00:00",
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
        FileBackedFailureBundleCenterIntegration(runtime_root=root),
        FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root),
        observed_at="2026-05-29T00:00:12+00:00",
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
        created_at="2026-05-29T00:00:13+00:00",
        observed_at="2026-05-29T00:00:14+00:00",
    )

    return FileBackedOperatorConsoleRuntimeSurface(
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
    )


class OperatorConsoleRuntimeSurfaceV1Tests(unittest.TestCase):
    def test_reads_persisted_evidence_as_readonly_snapshot_with_stale_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            surface = _build_evidence(Path(tempdir))
            snapshot = surface.read_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                observed_at="2026-05-29T00:00:15+00:00",
            )

        panel_by_id = {panel.panel_id: panel for panel in snapshot.panels}
        self.assertTrue(validate_operator_console_runtime_snapshot(snapshot))
        self.assertTrue(snapshot.read_only)
        self.assertFalse(snapshot.mutation_enabled)
        self.assertFalse(snapshot.command_enabled)
        self.assertFalse(snapshot.direct_console_edits_enabled)
        self.assertEqual(snapshot.status, "stale")
        self.assertIn("watchdog", snapshot.stale_panel_ids)
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
            self.assertGreater(panel_by_id[panel_id].record_count, 0, panel_id)
            self.assertNotEqual(panel_by_id[panel_id].evidence_hash, ZERO_HASH)

    def test_hash_mismatch_is_red_failure_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            surface = _build_evidence(root)
            store = FileBackedArtifactStore(
                root / "artifact-store",
                store_id="failure-bundle-center-artifacts-v1",
            )
            first_record = store.read_records()[0]
            store.artifact_path(first_record.manifest).write_text(
                "{\"tampered\":true}\n",
                encoding="utf-8",
            )

            snapshot = surface.read_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                observed_at="2026-05-29T00:00:15+00:00",
            )

        artifacts = {panel.panel_id: panel for panel in snapshot.panels}["artifacts"]
        self.assertEqual(snapshot.status, "failure")
        self.assertIn("artifacts", snapshot.red_panel_ids)
        self.assertEqual(artifacts.severity, "red")
        self.assertTrue(
            any("artifact_replay_rejected" in failure for failure in artifacts.failures)
        )

    def test_missing_evidence_is_red_and_does_not_create_missing_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            surface = FileBackedOperatorConsoleRuntimeSurface(
                runtime_root=root,
                wal_source_relpaths=("missing-wal.jsonl",),
                queue_source_relpath="queue/jobs.jsonl",
                queue_id=QUEUE_ID,
                artifact_store_relpath="artifact-store",
            )
            snapshot = surface.read_snapshot(
                task_id=TASK_ID,
                run_id=RUN_ID,
                observed_at="2026-05-29T00:00:15+00:00",
            )

        self.assertEqual(snapshot.status, "failure")
        self.assertIn("wal", snapshot.red_panel_ids)
        self.assertFalse((root / "missing-wal.jsonl").exists())

    def test_direct_console_mutation_is_rejected_before_any_command_surface(self) -> None:
        rejected = admit_operator_console_mutation_route(
            {
                "mutation_route": "direct_console_edit",
                "command": "queue edit",
                "approval_receipt_hash": _hash("approval"),
                "controlled_execution_receipt_hash": _hash("execution"),
            }
        )
        accepted_route = admit_operator_console_mutation_route(
            {
                "mutation_route": "approval_controlled_execution_runtime",
                "approval_receipt_hash": _hash("approval"),
                "controlled_execution_receipt_hash": _hash("execution"),
            }
        )

        self.assertFalse(rejected.accepted)
        self.assertFalse(rejected.console_mutation_performed)
        self.assertIn("controlled_execution_route_required", rejected.failures)
        self.assertTrue(
            any("direct_console_mutation_field_forbidden:command" == failure for failure in rejected.failures)
        )
        self.assertTrue(accepted_route.accepted)
        self.assertTrue(accepted_route.routed_to_controlled_execution)
        self.assertFalse(accepted_route.console_mutation_performed)

    def test_source_has_no_execution_network_or_write_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        forbidden = (
            "import subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "os.environ",
            "os.open",
            ".write_bytes(",
            ".write_text(",
            ".rename(",
            "FileBackedControlledExecutionRuntime(",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
