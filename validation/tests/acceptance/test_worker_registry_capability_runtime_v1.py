"""Acceptance coverage for worker registry capability runtime V1."""

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
from kernel.runtime.worker_registry_capability_runtime import (
    ZERO_HASH,
    FileBackedWorkerRegistryCapabilityRuntime,
)


TASK_ID = "task-521-acceptance"
RUN_ID = "run-521-acceptance"
JOB_ID = "job-521-acceptance"
WORKER_ID = "worker-521-acceptance"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _issue_approval(store: FileBackedApprovalRuntimeIntegration):
    request = {
        "approval_request_id": "approval-request-521-acceptance",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "review_packet_hash": _hash("review-521-acceptance"),
        "promotion_receipt_hash": _hash("promotion-521-acceptance"),
        "wal_head_hash": _hash("wal-head-521-acceptance"),
        "artifact_manifest_hash": _hash("artifact-521-acceptance"),
        "snapshot_reconstruction_hash": _hash("snapshot-521-acceptance"),
        "capability_token_hash": _hash("capability-521-acceptance"),
        "risk_decision_hash": _hash("risk-521-acceptance"),
        "requested_action": "approve_next_manual_stage",
        "human_invoked": True,
        "production_autonomy_requested": False,
        "live_execution_requested": False,
    }
    decision = {
        "approval_decision_id": "approval-decision-521-acceptance",
        "approval_request_hash": "",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "operator_id_hash": _hash("operator-521-acceptance"),
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
    return store.issue_approval(
        request_payload=request,
        decision_payload=decision,
        expires_at="2026-05-29T01:00:00+00:00",
        issued_at="2026-05-29T00:00:00+00:00",
    )


class WorkerRegistryCapabilityRuntimeAcceptanceV1Tests(unittest.TestCase):
    def test_worker_registry_capability_acceptance_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            approval_store = FileBackedApprovalRuntimeIntegration(
                runtime_root=root,
                artifact_store_relpath="approval-artifacts",
            )
            approval = _issue_approval(approval_store)
            queue = DurableJobQueue(
                path=root / "queue" / "jobs.jsonl",
                queue_id="worker-registry-capability-acceptance-queue",
            )
            queue.submit_job(
                job_id=JOB_ID,
                task_id=TASK_ID,
                run_id=RUN_ID,
                payload={
                    "requested_task_class": "static_contract_check",
                    "task_descriptor_hash": _hash("task-descriptor-521-acceptance"),
                },
                idempotency_key="idempotency-521-acceptance",
                submitted_at="2026-05-29T00:00:10+00:00",
            )
            queue.queue_job(JOB_ID, queued_at="2026-05-29T00:00:20+00:00")
            runtime = FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root)

            issued = runtime.authorize_worker_for_queue_job(
                {
                    "approval_admission_hash": approval.approval_admission_hash,
                    "artifact_manifest_hash": _hash("artifact-manifest-worker-521-acceptance"),
                    "capability_hashes": (_hash("worker-capability-521-acceptance"),),
                    "evidence_requirement_hashes": (_hash("worker-evidence-521-acceptance"),),
                    "expires_at": "2026-05-29T01:00:00+00:00",
                    "human_approval_required": True,
                    "idempotency_key_hash": _hash("idempotency-521-acceptance"),
                    "input_contract_hash": _hash("input-contract-521-acceptance"),
                    "issue_nonce": "issue-worker-521-acceptance",
                    "job_id": JOB_ID,
                    "max_memory_mb": 256,
                    "max_runtime_ms": 60_000,
                    "output_contract_hash": _hash("output-contract-521-acceptance"),
                    "policy_hash": _hash("policy-521-acceptance"),
                    "registry_policy_hash": _hash("registry-policy-521-acceptance"),
                    "requested_task_class": "static_contract_check",
                    "run_id": RUN_ID,
                    "stderr_limit_bytes": 4096,
                    "stdout_limit_bytes": 4096,
                    "task_classes": ("static_contract_check",),
                    "task_descriptor_hash": _hash("task-descriptor-521-acceptance"),
                    "task_id": TASK_ID,
                    "worker_id": WORKER_ID,
                    "worker_kind": "local_deterministic",
                },
                queue,
                approval_store,
                observed_at="2026-05-29T00:00:30+00:00",
            )
            consumed = runtime.consume_capability_for_queue_job(
                capability_token_id=issued.capability_token_id,
                queue=queue,
                worker_id=WORKER_ID,
                job_id=JOB_ID,
                consume_nonce="consume-worker-521-acceptance",
                now="2026-05-29T00:00:40+00:00",
                observed_at="2026-05-29T00:00:40+00:00",
            )
            leased = queue.get_job_state(JOB_ID)

        self.assertTrue(issued.accepted, issued.failures)
        self.assertTrue(consumed.accepted, consumed.failures)
        self.assertEqual(leased.state, "leased")
        self.assertNotEqual(issued.worker_admission_receipt_hash, ZERO_HASH)
        self.assertNotEqual(issued.watchdog_policy_hash, ZERO_HASH)
        self.assertNotEqual(consumed.worker_state_wal_record_hash, ZERO_HASH)


if __name__ == "__main__":
    unittest.main()
