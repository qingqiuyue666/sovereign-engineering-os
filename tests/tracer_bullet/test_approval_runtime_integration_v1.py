"""Tests for approval runtime integration V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    ZERO_HASH,
    ApprovalRuntimeIntegrationError,
    FileBackedApprovalRuntimeIntegration,
    compute_approval_gated_preflight_response_hash,
    run_approval_gated_minimal_controlled_wal_preflight,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


SOURCE_PATH = Path("kernel/runtime/approval_runtime_integration.py")
TASK_ID = "task-518"
RUN_ID = "run-518"
PREFLIGHT_ID = "preflight-518"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _approval_payloads() -> tuple[dict[str, object], dict[str, object]]:
    request = {
        "approval_request_id": "approval-request-518",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
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
    decision = {
        "approval_decision_id": "approval-decision-518",
        "approval_request_hash": "",
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


def _issue(store: FileBackedApprovalRuntimeIntegration, *, expires_at: str = "2026-05-28T02:00:00+00:00"):
    request, decision = _approval_payloads()
    from kernel.runtime.approval_runtime_contract import build_approval_runtime_request

    built_request = build_approval_runtime_request(
        request,
        created_at="2026-05-28T00:00:00+00:00",
    )
    decision["approval_request_hash"] = built_request.request_hash
    return store.issue_approval(
        request_payload=request,
        decision_payload=decision,
        expires_at=expires_at,
        issued_at="2026-05-28T00:00:00+00:00",
    )


def _admission_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "preflight_id": PREFLIGHT_ID,
        "command_id": "git_status_short",
        "request_hash": _hash("request"),
        "decision_hash": _hash("decision"),
        "admission_record_hash": _hash("admission"),
    }
    payload.update(overrides)
    return payload


def _receipt_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        outcome_type="EXECUTION_RECEIPT",
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
    )
    payload.update(overrides)
    return payload


def _binding_evidence(**overrides: object) -> dict[str, object]:
    payload = _admission_evidence(
        receipt_hash=_hash("receipt"),
        verifier_input_hash=_hash("verifier-input"),
        verifier_binding_hash=_hash("verifier-binding"),
        execution_performed=True,
    )
    payload.update(overrides)
    return payload


def _preflight_evidence(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "preflight_id": PREFLIGHT_ID,
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
    }
    payload.update(overrides)
    return payload


def _gated_payload(approval_hash: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "api_invocation_id": "approval-gated-api-518",
        "wrapper_input_id": "approval-gated-wrapper-input-518",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "preflight_id": PREFLIGHT_ID,
        "requested_at": "2026-05-28T00:00:01+00:00",
        "requester": "operator",
        "human_invoked": True,
        "single_run_scope": True,
        "caller_intent": "run approval-gated WAL preflight",
        "approval_admission_hash": approval_hash,
        "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
        "admission_evidence": _admission_evidence(),
        "outcome_evidence": _receipt_evidence(),
        "verifier_binding_evidence": _binding_evidence(),
        "preflight_result_evidence": _preflight_evidence(),
    }
    payload.update(overrides)
    return payload


class ApprovalRuntimeIntegrationV1Tests(unittest.TestCase):
    def test_valid_approval_is_persisted_bound_to_wal_artifact_and_consumed_once(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            approval = _issue(store)
            appended = []

            response = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(approval.approval_admission_hash),
                store,
                appended.append,
                observed_at="2026-05-28T00:01:00+00:00",
            )
            approval_file = (
                root
                / "approval-runtime"
                / "approvals"
                / (approval.approval_admission_hash.removeprefix("sha256:") + ".json")
            )
            consumption_file = (
                root
                / "approval-runtime"
                / "consumptions"
                / (approval.approval_admission_hash.removeprefix("sha256:") + ".json")
            )
            wal_records = FileBackedRealWalStorage(
                root / "approval-runtime" / "approval.real-wal.jsonl"
            ).read_records()
            artifact_records = FileBackedArtifactStore(root / "artifact-store").read_records()
            approval_file_exists = approval_file.is_file()
            consumption_file_exists = consumption_file.is_file()

        self.assertTrue(response.accepted, response.rejection_reasons)
        self.assertTrue(response.execution_may_proceed)
        self.assertEqual(response.response_hash, compute_approval_gated_preflight_response_hash(response))
        self.assertTrue(approval_file_exists)
        self.assertTrue(consumption_file_exists)
        self.assertEqual(len(appended), 4)
        self.assertTrue(all(record.record_type == "APPROVAL_EVENT" for record in wal_records))
        self.assertGreaterEqual(len(wal_records), 2)
        self.assertEqual(len(artifact_records), 1)
        self.assertEqual(artifact_records[0].record_hash, approval.approval_artifact_record_hash)

    def test_missing_expired_revoked_reused_and_scope_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            missing = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(_hash("missing-approval")),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:01:00+00:00",
            )
            expired = _issue(store, expires_at="2026-05-28T00:00:30+00:00")
            expired_response = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(expired.approval_admission_hash),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:01:00+00:00",
            )

        self.assertFalse(missing.accepted)
        self.assertEqual(missing.preflight_api_response_hash, ZERO_HASH)
        self.assertIn("approval_missing", missing.rejection_reasons)
        self.assertFalse(expired_response.accepted)
        self.assertIn("approval_expired", expired_response.rejection_reasons)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            revoked = _issue(store)
            store.revoke_approval(
                revoked.approval_admission_hash,
                task_id=TASK_ID,
                run_id=RUN_ID,
                reason_code="operator_revoked_before_execution",
                revoked_at="2026-05-28T00:00:30+00:00",
            )
            revoked_response = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(revoked.approval_admission_hash),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:01:00+00:00",
            )

        self.assertFalse(revoked_response.accepted)
        self.assertIn("approval_revoked", revoked_response.rejection_reasons)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            approval = _issue(store)
            accepted = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(approval.approval_admission_hash),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:01:00+00:00",
            )
            reused = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(approval.approval_admission_hash),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:02:00+00:00",
            )
            with self.assertRaisesRegex(ApprovalRuntimeIntegrationError, "approval_scope_mismatch"):
                run_approval_gated_minimal_controlled_wal_preflight(
                    _gated_payload(approval.approval_admission_hash, approval_scope="broad"),
                    store,
                    lambda record: None,
                    observed_at="2026-05-28T00:03:00+00:00",
                )

        self.assertTrue(accepted.accepted)
        self.assertFalse(reused.accepted)
        self.assertIn("approval_reused", reused.rejection_reasons)

    def test_approval_bypass_and_caller_supplied_auto_approval_fail_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            store = FileBackedApprovalRuntimeIntegration(runtime_root=Path(tempdir))
            appended = []
            payload = _gated_payload(_hash("missing"))
            del payload["approval_admission_hash"]
            with self.assertRaisesRegex(ApprovalRuntimeIntegrationError, "approval_admission_hash_required"):
                run_approval_gated_minimal_controlled_wal_preflight(
                    payload,
                    store,
                    appended.append,
                    observed_at="2026-05-28T00:01:00+00:00",
                )
            with self.assertRaisesRegex(ApprovalRuntimeIntegrationError, "caller_supplied_approval_flag_forbidden"):
                run_approval_gated_minimal_controlled_wal_preflight(
                    _gated_payload(
                        _hash("missing"),
                        approved_for_wal_gated_preflight=True,
                    ),
                    store,
                    appended.append,
                    observed_at="2026-05-28T00:01:00+00:00",
                )

        self.assertEqual(appended, [])

    def test_persisted_receipt_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            approval = _issue(store)
            path = (
                root
                / "approval-runtime"
                / "approvals"
                / (approval.approval_admission_hash.removeprefix("sha256:") + ".json")
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["integrated_receipt"]["task_id"] = "tampered"
            path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            response = run_approval_gated_minimal_controlled_wal_preflight(
                _gated_payload(approval.approval_admission_hash),
                store,
                lambda record: None,
                observed_at="2026-05-28T00:01:00+00:00",
            )

        self.assertFalse(response.accepted)
        self.assertTrue(
            any("approval_receipt_invalid" in reason for reason in response.rejection_reasons)
        )

    def test_source_has_no_subprocess_network_provider_browser_or_env_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden = {
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
        self.assertFalse(imports.intersection(forbidden))
        for marker in ("shell=True", "os.system", "Popen", "os.environ", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
