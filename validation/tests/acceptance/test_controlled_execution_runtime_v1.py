"""Acceptance coverage for controlled execution runtime V1."""

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
from kernel.runtime.controlled_execution_runtime import (
    ZERO_HASH,
    FileBackedControlledExecutionRuntime,
)


TASK_ID = "task-520-acceptance"
RUN_ID = "run-520-acceptance"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _issue_approval(store: FileBackedApprovalRuntimeIntegration):
    request = {
        "approval_request_id": "approval-request-520-acceptance",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "review_packet_hash": _hash("review-520-acceptance"),
        "promotion_receipt_hash": _hash("promotion-520-acceptance"),
        "wal_head_hash": _hash("wal-head-520-acceptance"),
        "artifact_manifest_hash": _hash("artifact-520-acceptance"),
        "snapshot_reconstruction_hash": _hash("snapshot-520-acceptance"),
        "capability_token_hash": _hash("capability-520-acceptance"),
        "risk_decision_hash": _hash("risk-520-acceptance"),
        "requested_action": "approve_next_manual_stage",
        "human_invoked": True,
        "production_autonomy_requested": False,
        "live_execution_requested": False,
    }
    decision = {
        "approval_decision_id": "approval-decision-520-acceptance",
        "approval_request_hash": "",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "operator_id_hash": _hash("operator-520-acceptance"),
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


class ControlledExecutionRuntimeAcceptanceV1Tests(unittest.TestCase):
    def test_controlled_execution_runtime_acceptance_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            approval_store = FileBackedApprovalRuntimeIntegration(
                runtime_root=root,
                artifact_store_relpath="approval-artifacts",
            )
            approval = _issue_approval(approval_store)
            runtime = FileBackedControlledExecutionRuntime(
                runtime_root=root,
                enabled=True,
            )

            receipt = runtime.run(
                {
                    "approval_admission_hash": approval.approval_admission_hash,
                    "caller_intent": "run controlled execution runtime acceptance",
                    "execution_id": "execution-520-acceptance",
                    "human_invoked": True,
                    "idempotency_key": "idempotency-520-acceptance",
                    "job_id": "job-520-acceptance",
                    "preflight_id": "preflight-520-acceptance",
                    "requested_at": "2026-05-29T00:00:10+00:00",
                    "requester": "operator",
                    "run_id": RUN_ID,
                    "single_run_scope": True,
                    "snapshot_ref": "snapshot-ref-520-acceptance",
                    "task_id": TASK_ID,
                    "use_case_ids": ("uc_520_controlled_execution_runtime",),
                    "worker_id": "worker-520-acceptance",
                },
                approval_store,
                observed_at="2026-05-29T00:00:30+00:00",
            )

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertTrue(receipt.execution_performed)
        self.assertEqual(receipt.execution_status, "PREFLIGHT_PASSED")
        self.assertEqual(receipt.queue_terminal_state, "succeeded")
        self.assertNotEqual(receipt.result_artifact_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.execution_wal_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.post_snapshot_receipt_hash, ZERO_HASH)


if __name__ == "__main__":
    unittest.main()
