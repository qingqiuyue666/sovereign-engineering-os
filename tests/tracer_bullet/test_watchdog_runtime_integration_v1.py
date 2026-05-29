"""Tests for watchdog runtime integration V1."""

from __future__ import annotations

import ast
import hashlib
import json
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
    compute_watchdog_runtime_receipt_hash,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "watchdog_runtime_integration.py"
TASK_ID = "task-523"
RUN_ID = "run-523"
JOB_ID = "job-523"
WORKER_ID = "worker-523"
OBSERVED_AT = "2026-05-29T00:03:20+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _queue(root: Path, *, max_attempts: int = 2) -> DurableJobQueue:
    queue = DurableJobQueue(
        path=root / "queue" / "jobs.jsonl",
        queue_id="watchdog-runtime-test-queue",
    )
    queue.submit_job(
        job_id=JOB_ID,
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload={"task_descriptor_hash": _hash("task-523")},
        idempotency_key="idempotency-523-" + str(max_attempts),
        max_attempts=max_attempts,
        submitted_at="2026-05-29T00:03:00+00:00",
    )
    queue.queue_job(JOB_ID, queued_at="2026-05-29T00:03:01+00:00")
    return queue


def _leased_queue(root: Path, *, max_attempts: int = 2, timeout: int = 5) -> DurableJobQueue:
    queue = _queue(root, max_attempts=max_attempts)
    queue.lease_next(
        worker_id=WORKER_ID,
        leased_at="2026-05-29T00:03:02+00:00",
        lease_timeout_seconds=timeout,
    )
    return queue


def _payload(queue: DurableJobQueue, **overrides: object) -> dict[str, object]:
    state = queue.get_job_state(JOB_ID)
    payload: dict[str, object] = {
        "elapsed_ms": 1_000,
        "human_invoked": True,
        "job_id": JOB_ID,
        "lease_id": state.lease_id,
        "lease_timeout_seconds": 30,
        "max_memory_mb": 256,
        "max_runtime_ms": 60_000,
        "observed_memory_mb": 128,
        "previous_watchdog_receipt_hash": ZERO_HASH,
        "recovery_plan_hash": _hash("recovery-plan-523"),
        "retry_after": "2026-05-29T00:03:21+00:00",
        "run_id": RUN_ID,
        "snapshot_reconstruction_hash": _hash("snapshot-523"),
        "stderr_digest": _hash("stderr-523"),
        "stderr_truncated": False,
        "stdout_digest": _hash("stdout-523"),
        "stdout_truncated": False,
        "task_id": TASK_ID,
        "watchdog_policy_hash": _hash("watchdog-policy-523"),
        "worker_id": WORKER_ID,
    }
    payload.update(overrides)
    return payload


def _artifact_payload_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_artifact_payload_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_artifact_payload_keys(item))
    return keys


class WatchdogRuntimeIntegrationV1Tests(unittest.TestCase):
    def test_heartbeat_extends_lease_and_records_wal_artifact_and_operator_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _leased_queue(root, timeout=60)
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)

            receipt = runtime.record_heartbeat(
                _payload(queue, human_invoked=False),
                queue,
                observed_at="2026-05-29T00:03:10+00:00",
            )
            wal_records = FileBackedRealWalStorage(
                root / "watchdog-runtime" / "watchdog.real-wal.jsonl"
            ).read_records()
            artifacts = FileBackedArtifactStore(
                root / "watchdog-runtime" / "artifacts",
                store_id="watchdog-runtime-artifacts-v1",
            ).read_records()
            operator_state = runtime.read_operator_watchdog_state(JOB_ID)
            queue_state = queue.get_job_state(JOB_ID)

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.event_type, "heartbeat_recorded")
        self.assertEqual(queue_state.state, "leased")
        self.assertEqual(receipt.queue_record_hash, queue_state.last_event_hash)
        self.assertFalse(receipt.background_daemon_enabled)
        self.assertFalse(receipt.stale_lease_detected)
        self.assertFalse(receipt.resource_breach_detected)
        self.assertEqual(receipt.receipt_hash, compute_watchdog_runtime_receipt_hash(receipt))
        self.assertEqual(wal_records[0].record_type, "WATCHDOG_EVENT")
        self.assertEqual(artifacts[0].manifest.artifact_type, "audit_json")
        self.assertEqual(operator_state.queue_state, "leased")
        self.assertEqual(operator_state.latest_watchdog_receipt_hash, receipt.watchdog_observation_hash)

    def test_manual_sweep_recovers_stale_lease_records_failure_bundle_and_quarantines_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _leased_queue(root, max_attempts=2, timeout=5)
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)
            failure_center = FileBackedFailureBundleCenterIntegration(runtime_root=root)
            worker_runtime = FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root)

            receipt = runtime.run_manual_sweep(
                _payload(queue),
                queue,
                failure_center,
                worker_runtime,
                observed_at=OBSERVED_AT,
            )
            queue_state = queue.get_job_state(JOB_ID)
            failure_bundle = failure_center.read_persisted_bundle(receipt.failure_bundle_id)

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.event_type, "resource_breach_recorded")
        self.assertTrue(receipt.stale_lease_detected)
        self.assertTrue(receipt.stale_lease_recovered)
        self.assertTrue(receipt.retry_scheduled)
        self.assertFalse(receipt.dead_lettered)
        self.assertEqual(queue_state.state, "queued")
        self.assertNotEqual(receipt.failure_bundle_hash, ZERO_HASH)
        self.assertNotEqual(receipt.failure_bundle_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.worker_quarantine_receipt_hash, ZERO_HASH)
        self.assertIn("bundle", failure_bundle)

    def test_manual_sweep_links_dead_letter_and_resource_breach(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _leased_queue(root, max_attempts=1, timeout=60)
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)

            receipt = runtime.run_manual_sweep(
                _payload(queue, observed_memory_mb=512),
                queue,
                FileBackedFailureBundleCenterIntegration(runtime_root=root),
                FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root),
                observed_at="2026-05-29T00:03:10+00:00",
            )
            queue_state = queue.get_job_state(JOB_ID)

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertTrue(receipt.resource_breach_detected)
        self.assertFalse(receipt.stale_lease_detected)
        self.assertTrue(receipt.dead_lettered)
        self.assertFalse(receipt.retry_scheduled)
        self.assertEqual(queue_state.state, "dead_lettered")
        self.assertNotEqual(receipt.failure_bundle_hash, ZERO_HASH)
        self.assertNotEqual(receipt.worker_quarantine_receipt_hash, ZERO_HASH)

    def test_manual_sweep_fail_closed_without_human_invocation_or_with_bypass_material(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _leased_queue(root)
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)
            before_records = len(queue.records)

            not_human = runtime.run_manual_sweep(
                _payload(queue, human_invoked=False),
                queue,
                FileBackedFailureBundleCenterIntegration(runtime_root=root),
                FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root),
                observed_at=OBSERVED_AT,
            )
            bypass = runtime.run_manual_sweep(
                _payload(queue, command="run raw command"),
                queue,
                FileBackedFailureBundleCenterIntegration(runtime_root=root),
                FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root),
                observed_at=OBSERVED_AT,
            )
            after_records = len(queue.records)

        self.assertFalse(not_human.accepted)
        self.assertIn("human_invoked_required_true", not_human.failures)
        self.assertFalse(bypass.accepted)
        self.assertTrue(any("unsafe_watchdog_field:command" in failure for failure in bypass.failures))
        self.assertEqual(after_records, before_records)
        self.assertEqual(not_human.watchdog_wal_record_hash, ZERO_HASH)
        self.assertEqual(bypass.artifact_manifest_hash, ZERO_HASH)

    def test_artifact_payload_and_source_keep_watchdog_runtime_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _leased_queue(root, timeout=60)
            runtime = FileBackedWatchdogRuntimeIntegration(runtime_root=root)
            receipt = runtime.record_heartbeat(
                _payload(queue, human_invoked=False),
                queue,
                observed_at="2026-05-29T00:03:10+00:00",
            )
            artifact_store = FileBackedArtifactStore(
                root / "watchdog-runtime" / "artifacts",
                store_id="watchdog-runtime-artifacts-v1",
            )
            artifact_record = artifact_store.read_records()[0]
            artifact_payload = json.loads(
                artifact_store.artifact_path(artifact_record.manifest).read_text(
                    encoding="utf-8"
                )
            )

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertFalse(
            _artifact_payload_keys(artifact_payload).intersection(
                {
                    "argv",
                    "command",
                    "content",
                    "credential",
                    "cwd",
                    "env",
                    "path",
                    "raw",
                    "secret",
                    "stderr",
                    "stdout",
                    "token",
                }
            )
        )

        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
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
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in ("os.environ", "Popen", "shell=True", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
