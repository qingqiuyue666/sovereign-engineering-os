"""Acceptance tests for Approval Runtime Integration V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.approval_runtime_contract import build_approval_runtime_request
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    FileBackedApprovalRuntimeIntegration,
    run_approval_gated_minimal_controlled_wal_preflight,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class ApprovalRuntimeIntegrationAcceptanceV1Tests(unittest.TestCase):
    def test_valid_approval_allows_one_wal_gated_preflight_then_reuse_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            request_payload = {
                "approval_request_id": "approval-request-acceptance-518",
                "task_id": "task-acceptance-518",
                "run_id": "run-acceptance-518",
                "review_packet_hash": _hash("review"),
                "promotion_receipt_hash": _hash("promotion"),
                "wal_head_hash": _hash("wal-head"),
                "artifact_manifest_hash": _hash("artifact-manifest"),
                "snapshot_reconstruction_hash": _hash("snapshot-reconstruction"),
                "capability_token_hash": _hash("capability"),
                "risk_decision_hash": _hash("risk"),
                "requested_action": "approve_next_manual_stage",
                "human_invoked": True,
                "production_autonomy_requested": False,
                "live_execution_requested": False,
            }
            request = build_approval_runtime_request(
                request_payload,
                created_at="2026-05-28T00:00:00+00:00",
            )
            approval = store.issue_approval(
                request_payload=request_payload,
                decision_payload={
                    "approval_decision_id": "approval-decision-acceptance-518",
                    "approval_request_hash": request.request_hash,
                    "task_id": "task-acceptance-518",
                    "run_id": "run-acceptance-518",
                    "operator_id_hash": _hash("operator"),
                    "operator_action": "approved",
                    "decision_reason_code": "operator_explicit_decision",
                    "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
                    "rollback_plan_hash": None,
                    "human_attested": True,
                    "production_autonomy_enabled": False,
                    "live_execution_enabled": False,
                },
                expires_at="2026-05-28T02:00:00+00:00",
                issued_at="2026-05-28T00:00:00+00:00",
            )
            payload = _gated_payload(
                approval.approval_admission_hash,
                task_id="task-acceptance-518",
                run_id="run-acceptance-518",
                preflight_id="preflight-acceptance-518",
            )
            appended = []
            accepted = run_approval_gated_minimal_controlled_wal_preflight(
                payload,
                store,
                appended.append,
                observed_at="2026-05-28T00:01:00+00:00",
            )
            reused = run_approval_gated_minimal_controlled_wal_preflight(
                payload,
                store,
                lambda record: None,
                observed_at="2026-05-28T00:02:00+00:00",
            )
            wal_records = FileBackedRealWalStorage(
                root / "approval-runtime" / "approval.real-wal.jsonl"
            ).read_records()
            artifacts = FileBackedArtifactStore(root / "artifact-store").read_records()

        self.assertTrue(accepted.accepted, accepted.rejection_reasons)
        self.assertTrue(accepted.execution_may_proceed)
        self.assertEqual(len(appended), 4)
        self.assertFalse(reused.accepted)
        self.assertIn("approval_reused", reused.rejection_reasons)
        self.assertGreaterEqual(len(wal_records), 3)
        self.assertEqual(len(artifacts), 1)


def _admission_evidence(*, task_id: str, run_id: str, preflight_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": task_id,
        "run_id": run_id,
        "preflight_id": preflight_id,
        "command_id": "git_status_short",
        "request_hash": _hash("request"),
        "decision_hash": _hash("decision"),
        "admission_record_hash": _hash("admission"),
    }
    payload.update(overrides)
    return payload


def _gated_payload(approval_hash: str, *, task_id: str, run_id: str, preflight_id: str) -> dict[str, object]:
    admission = _admission_evidence(
        task_id=task_id,
        run_id=run_id,
        preflight_id=preflight_id,
    )
    return {
        "api_invocation_id": "approval-gated-api-acceptance-518",
        "wrapper_input_id": "approval-gated-wrapper-input-acceptance-518",
        "task_id": task_id,
        "run_id": run_id,
        "preflight_id": preflight_id,
        "requested_at": "2026-05-28T00:00:01+00:00",
        "requester": "operator",
        "human_invoked": True,
        "single_run_scope": True,
        "caller_intent": "run approval-gated WAL preflight",
        "approval_admission_hash": approval_hash,
        "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
        "admission_evidence": admission,
        "outcome_evidence": {
            **admission,
            "outcome_type": "EXECUTION_RECEIPT",
            "receipt_hash": _hash("receipt"),
            "verifier_input_hash": _hash("verifier-input"),
            "verifier_binding_hash": _hash("verifier-binding"),
        },
        "verifier_binding_evidence": {
            **admission,
            "receipt_hash": _hash("receipt"),
            "verifier_input_hash": _hash("verifier-input"),
            "verifier_binding_hash": _hash("verifier-binding"),
            "execution_performed": True,
        },
        "preflight_result_evidence": {
            "task_id": task_id,
            "run_id": run_id,
            "preflight_id": preflight_id,
            "preflight_result_hash": _hash("preflight-result"),
            "ordered_command_ids": ("git_status_short", "git_diff_check"),
            "child_request_hashes": (_hash("request-1"), _hash("request-2")),
            "child_decision_hashes": (_hash("decision-1"), _hash("decision-2")),
            "child_admission_hashes": (_hash("admission-1"), _hash("admission-2")),
            "child_receipt_hashes": (_hash("receipt-1"), _hash("receipt-2")),
            "child_failure_bundle_hashes": ("", ""),
            "child_verifier_input_hashes": (
                _hash("verifier-input-1"),
                _hash("verifier-input-2"),
            ),
            "child_verifier_binding_hashes": (
                _hash("verifier-binding-1"),
                _hash("verifier-binding-2"),
            ),
            "pre_snapshot_hashes": (_hash("pre-snapshot-1"), _hash("pre-snapshot-2")),
            "post_snapshot_hashes": (_hash("post-snapshot-1"), _hash("post-snapshot-2")),
            "execution_performed": True,
        },
    }


if __name__ == "__main__":
    unittest.main()
