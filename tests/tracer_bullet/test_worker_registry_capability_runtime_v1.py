"""Tests for worker registry capability runtime V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.approval_runtime_contract import build_approval_runtime_request
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    FileBackedApprovalRuntimeIntegration,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.runtime.worker_registry_capability_runtime import (
    ZERO_HASH,
    FileBackedWorkerRegistryCapabilityRuntime,
    compute_worker_registry_capability_runtime_receipt_hash,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "worker_registry_capability_runtime.py"
TASK_ID = "task-521"
RUN_ID = "run-521"
JOB_ID = "job-521"
WORKER_ID = "worker-521"
OBSERVED_AT = "2026-05-29T00:00:30+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _approval_payloads() -> tuple[dict[str, object], dict[str, object]]:
    request = {
        "approval_request_id": "approval-request-521",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "review_packet_hash": _hash("review-521"),
        "promotion_receipt_hash": _hash("promotion-521"),
        "wal_head_hash": _hash("wal-head-521"),
        "artifact_manifest_hash": _hash("artifact-manifest-521"),
        "snapshot_reconstruction_hash": _hash("snapshot-521"),
        "capability_token_hash": _hash("approval-capability-521"),
        "risk_decision_hash": _hash("risk-521"),
        "requested_action": "approve_next_manual_stage",
        "human_invoked": True,
        "production_autonomy_requested": False,
        "live_execution_requested": False,
    }
    decision = {
        "approval_decision_id": "approval-decision-521",
        "approval_request_hash": "",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "operator_id_hash": _hash("operator-521"),
        "operator_action": "approved",
        "decision_reason_code": "operator_explicit_decision",
        "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
        "rollback_plan_hash": None,
        "human_attested": True,
        "production_autonomy_enabled": False,
        "live_execution_enabled": False,
    }
    built = build_approval_runtime_request(
        request,
        created_at="2026-05-29T00:00:00+00:00",
    )
    decision["approval_request_hash"] = built.request_hash
    return request, decision


def _issue_approval(store: FileBackedApprovalRuntimeIntegration):
    request, decision = _approval_payloads()
    return store.issue_approval(
        request_payload=request,
        decision_payload=decision,
        expires_at="2026-05-29T01:00:00+00:00",
        issued_at="2026-05-29T00:00:00+00:00",
    )


def _queue(root: Path, *, job_id: str = JOB_ID, priority: int = 50) -> DurableJobQueue:
    queue = DurableJobQueue(
        path=root / "queue" / "jobs.jsonl",
        queue_id="worker-registry-capability-test-queue",
    )
    queue.submit_job(
        job_id=job_id,
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload={
            "requested_task_class": "static_contract_check",
            "task_descriptor_hash": _hash("task-descriptor-521"),
        },
        idempotency_key="idempotency-" + job_id,
        priority=priority,
        submitted_at="2026-05-29T00:00:10+00:00",
    )
    queue.queue_job(job_id, queued_at="2026-05-29T00:00:20+00:00")
    return queue


def _payload(approval_hash: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_admission_hash": approval_hash,
        "artifact_manifest_hash": _hash("artifact-manifest-worker-521"),
        "capability_hashes": (_hash("worker-capability-521"),),
        "evidence_requirement_hashes": (_hash("worker-evidence-521"),),
        "expires_at": "2026-05-29T01:00:00+00:00",
        "human_approval_required": True,
        "idempotency_key_hash": _hash("idempotency-job-521"),
        "input_contract_hash": _hash("input-contract-521"),
        "issue_nonce": "issue-worker-521",
        "job_id": JOB_ID,
        "max_memory_mb": 256,
        "max_runtime_ms": 60_000,
        "output_contract_hash": _hash("output-contract-521"),
        "policy_hash": _hash("policy-521"),
        "registry_policy_hash": _hash("registry-policy-521"),
        "requested_task_class": "static_contract_check",
        "run_id": RUN_ID,
        "stderr_limit_bytes": 4096,
        "stdout_limit_bytes": 4096,
        "task_classes": ("static_contract_check",),
        "task_descriptor_hash": _hash("task-descriptor-521"),
        "task_id": TASK_ID,
        "worker_id": WORKER_ID,
        "worker_kind": "local_deterministic",
    }
    payload.update(overrides)
    return payload


def _authorize(root: Path, *, expires_at: str = "2026-05-29T01:00:00+00:00"):
    approval_store = FileBackedApprovalRuntimeIntegration(
        runtime_root=root,
        artifact_store_relpath="approval-artifacts",
    )
    approval = _issue_approval(approval_store)
    queue = _queue(root)
    runtime = FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root)
    receipt = runtime.authorize_worker_for_queue_job(
        _payload(approval.approval_admission_hash, expires_at=expires_at),
        queue,
        approval_store,
        observed_at=OBSERVED_AT,
    )
    return runtime, queue, receipt


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


class WorkerRegistryCapabilityRuntimeV1Tests(unittest.TestCase):
    def test_authorization_binds_admission_approval_queue_watchdog_wal_and_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, receipt = _authorize(root)

            wal_records = FileBackedRealWalStorage(
                root / "worker-registry-runtime" / "worker-registry.real-wal.jsonl"
            ).read_records()
            artifact_store = FileBackedArtifactStore(
                root / "worker-registry-runtime" / "artifacts",
                store_id="worker-registry-capability-artifacts-v1",
            )
            artifact_records = artifact_store.read_records()
            artifact_payload = json.loads(
                artifact_store.artifact_path(artifact_records[0].manifest).read_text(
                    encoding="utf-8"
                )
            )
            queue_state = queue.get_job_state(JOB_ID)

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.event_type, "authorization_issued")
        self.assertEqual(receipt.queue_state, "queued")
        self.assertEqual(queue_state.state, "queued")
        self.assertNotEqual(receipt.worker_admission_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.registry_manifest_hash, ZERO_HASH)
        self.assertNotEqual(receipt.capability_token_hash, ZERO_HASH)
        self.assertNotEqual(receipt.capability_issue_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.watchdog_policy_hash, ZERO_HASH)
        self.assertNotEqual(receipt.worker_state_wal_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.approval_consumption_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.artifact_record_hash, ZERO_HASH)
        self.assertEqual(
            receipt.receipt_hash,
            compute_worker_registry_capability_runtime_receipt_hash(receipt),
        )
        self.assertTrue(
            any(record.record_type == "WORKER_REGISTRY_EVENT" for record in wal_records)
        )
        self.assertEqual(len(artifact_records), 1)
        forbidden_artifact_keys = {
            "argv",
            "command",
            "content",
            "cwd",
            "env",
            "path",
            "raw_stderr",
            "raw_stdout",
            "secret",
            "stderr",
            "stdout",
            "token",
        }
        self.assertFalse(_artifact_payload_keys(artifact_payload).intersection(forbidden_artifact_keys))

    def test_authorized_worker_consumes_once_and_leases_only_bound_queue_job(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, issued = _authorize(root)

            consumed = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-worker-521",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )
            second = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-worker-521-second",
                now="2026-05-29T00:00:50+00:00",
                observed_at="2026-05-29T00:00:50+00:00",
            )
            leased_state = queue.get_job_state(JOB_ID)

        self.assertTrue(consumed.accepted, consumed.failures)
        self.assertEqual(consumed.event_type, "capability_consumed")
        self.assertEqual(consumed.queue_state, "leased")
        self.assertEqual(leased_state.state, "leased")
        self.assertTrue(leased_state.lease_id)
        self.assertEqual(consumed.queue_record_hash, leased_state.last_event_hash)
        self.assertFalse(second.accepted)
        self.assertIn("capability_already_consumed", second.failures)

    def test_wrong_worker_revoked_expired_and_quarantined_capabilities_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, issued = _authorize(root)
            wrong_worker = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id="worker-521-unauthorized",
                job_id=JOB_ID,
                consume_nonce="consume-wrong-worker",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )
            queued_after_wrong_worker = queue.get_job_state(JOB_ID)

        self.assertFalse(wrong_worker.accepted)
        self.assertIn("worker_id_mismatch", wrong_worker.failures)
        self.assertEqual(queued_after_wrong_worker.state, "queued")

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, issued = _authorize(root)
            revoked = runtime.revoke_capability(
                capability_token_id=issued.capability_token_id,
                reason="operator_cancelled_worker",
                revoked_at="2026-05-29T00:00:35+00:00",
                observed_at="2026-05-29T00:00:35+00:00",
            )
            after_revoke = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-revoked-worker",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )

        self.assertTrue(revoked.accepted, revoked.failures)
        self.assertFalse(after_revoke.accepted)
        self.assertIn("capability_revoked", after_revoke.failures)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, issued = _authorize(
                root,
                expires_at="2026-05-29T00:00:35+00:00",
            )
            expired = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-expired-worker",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )

        self.assertFalse(expired.accepted)
        self.assertIn("capability_expired", expired.failures)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime, queue, issued = _authorize(root)
            quarantine = runtime.quarantine_worker(
                worker_id=WORKER_ID,
                reason="watchdog_terminal_failure",
                failure_bundle_hash=_hash("failure-bundle-521"),
                task_id=TASK_ID,
                run_id=RUN_ID,
                job_id=JOB_ID,
                observed_at="2026-05-29T00:00:35+00:00",
            )
            quarantined = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-quarantined-worker",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )

        self.assertTrue(quarantine.accepted, quarantine.failures)
        self.assertEqual(quarantine.quarantine_state, "quarantined")
        self.assertFalse(quarantined.accepted)
        self.assertIn("worker_quarantined", quarantined.failures)

    def test_authorization_rejects_unauthorized_queue_and_bypass_material(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            approval_store = FileBackedApprovalRuntimeIntegration(
                runtime_root=root,
                artifact_store_relpath="approval-artifacts",
            )
            approval = _issue_approval(approval_store)
            queue = _queue(root)
            runtime = FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root)

            missing = runtime.authorize_worker_for_queue_job(
                _payload(approval.approval_admission_hash, job_id="job-521-missing"),
                queue,
                approval_store,
                observed_at=OBSERVED_AT,
            )
            bypass = runtime.authorize_worker_for_queue_job(
                _payload(approval.approval_admission_hash, command="run something"),
                queue,
                approval_store,
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(missing.accepted)
        self.assertIn("queue_job_missing", missing.failures)
        self.assertFalse(bypass.accepted)
        self.assertTrue(
            any("payload_field_forbidden:command" in failure for failure in bypass.failures)
        )

    def test_source_has_no_direct_network_provider_browser_env_or_process_launch_surface(self) -> None:
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
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in ("shell=True", "os.system", "Popen", "os.environ", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
