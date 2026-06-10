"""Tests for controlled execution runtime V1."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kernel.runtime.approval_runtime_contract import build_approval_runtime_request
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    FileBackedApprovalRuntimeIntegration,
)
from kernel.runtime.controlled_execution_runtime import (
    CONTROLLED_EXECUTION_QUEUE_ID,
    ZERO_HASH,
    FileBackedControlledExecutionRuntime,
    compute_controlled_execution_runtime_receipt_hash,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


SOURCE_PATH = Path("kernel/runtime/controlled_execution_runtime.py")
TASK_ID = "task-520"
RUN_ID = "run-520"
OBSERVED_AT = "2026-05-29T00:00:30+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _approval_payloads() -> tuple[dict[str, object], dict[str, object]]:
    request = {
        "approval_request_id": "approval-request-520",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "review_packet_hash": _hash("review-520"),
        "promotion_receipt_hash": _hash("promotion-520"),
        "wal_head_hash": _hash("wal-head-520"),
        "artifact_manifest_hash": _hash("artifact-manifest-520"),
        "snapshot_reconstruction_hash": _hash("snapshot-520"),
        "capability_token_hash": _hash("capability-520"),
        "risk_decision_hash": _hash("risk-520"),
        "requested_action": "approve_next_manual_stage",
        "human_invoked": True,
        "production_autonomy_requested": False,
        "live_execution_requested": False,
    }
    decision = {
        "approval_decision_id": "approval-decision-520",
        "approval_request_hash": "",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "operator_id_hash": _hash("operator-520"),
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


def _issue_approval(store: FileBackedApprovalRuntimeIntegration, *, expires_at: str = "2026-05-29T01:00:00+00:00"):
    request, decision = _approval_payloads()
    return store.issue_approval(
        request_payload=request,
        decision_payload=decision,
        expires_at=expires_at,
        issued_at="2026-05-29T00:00:00+00:00",
    )


def _payload(approval_hash: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_admission_hash": approval_hash,
        "caller_intent": "run controlled execution runtime",
        "execution_id": "execution-520",
        "human_invoked": True,
        "idempotency_key": "idempotency-520",
        "job_id": "job-520",
        "preflight_id": "preflight-520",
        "requested_at": "2026-05-29T00:00:10+00:00",
        "requester": "operator",
        "run_id": RUN_ID,
        "single_run_scope": True,
        "snapshot_ref": "snapshot-ref-520",
        "task_id": TASK_ID,
        "use_case_ids": ("uc_520_controlled_execution_runtime",),
        "worker_id": "worker-520",
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


@dataclass(frozen=True)
class _FakePreflightResult:
    overall_status: str
    preflight_result_hash: str
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _FakeEvidenceManifest:
    manifest_hash: str


@dataclass(frozen=True)
class _FakePreflightResponse:
    preflight_result: _FakePreflightResult
    evidence_manifest: _FakeEvidenceManifest
    execution_performed: bool


class ControlledExecutionRuntimeV1Tests(unittest.TestCase):
    def test_successful_lifecycle_binds_approval_queue_execution_artifact_wal_snapshot_and_receipt(self) -> None:
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
                _payload(approval.approval_admission_hash),
                approval_store,
                observed_at=OBSERVED_AT,
            )

            wal_records = FileBackedRealWalStorage(
                root / "controlled-execution" / "execution.real-wal.jsonl"
            ).read_records()
            artifact_store = FileBackedArtifactStore(
                root / "controlled-execution" / "artifacts",
                store_id="controlled-execution-artifacts-v1",
            )
            artifact_records = artifact_store.read_records()
            artifact_payload = json.loads(
                artifact_store.artifact_path(artifact_records[0].manifest).read_text(
                    encoding="utf-8"
                )
            )
            queue_records = DurableJobQueue(
                path=root / "controlled-execution" / "queue" / "jobs.jsonl",
                queue_id=CONTROLLED_EXECUTION_QUEUE_ID,
            ).records

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertTrue(receipt.execution_performed)
        self.assertEqual(receipt.queue_terminal_state, "succeeded")
        self.assertEqual(
            receipt.receipt_hash,
            compute_controlled_execution_runtime_receipt_hash(receipt),
        )
        self.assertNotEqual(receipt.approval_gate_response_hash, ZERO_HASH)
        self.assertNotEqual(receipt.result_artifact_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.execution_wal_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.pre_snapshot_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.post_snapshot_receipt_hash, ZERO_HASH)
        self.assertEqual(receipt.failure_bundle_receipt_hash, ZERO_HASH)
        self.assertEqual(wal_records[-1].record_type, "MINIMAL_CONTROLLED_EXECUTION")
        self.assertTrue(
            any(
                record.record_type == "MINIMAL_CONTROLLED_EXECUTION"
                for record in wal_records
            )
        )
        self.assertEqual(len(artifact_records), 1)
        self.assertEqual(queue_records[-1].event.event_type, "JOB_SUCCEEDED")
        forbidden_artifact_keys = {
            "argv",
            "command",
            "command_line",
            "content",
            "cwd",
            "env",
            "path",
            "raw_stderr",
            "raw_stdout",
            "stderr",
            "stdout",
            "subprocess",
        }
        self.assertFalse(_artifact_payload_keys(artifact_payload).intersection(forbidden_artifact_keys))

    def test_default_disabled_and_direct_bypass_fields_fail_before_controlled_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "runtime-root"
            approval_store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            disabled = FileBackedControlledExecutionRuntime(runtime_root=root)
            disabled_receipt = disabled.run(
                _payload(ZERO_HASH),
                approval_store,
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(disabled_receipt.accepted)
        self.assertIn("controlled_execution_runtime_disabled", disabled_receipt.failures)
        self.assertFalse(root.exists())

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            approval_store = FileBackedApprovalRuntimeIntegration(runtime_root=root)
            runtime = FileBackedControlledExecutionRuntime(
                runtime_root=root,
                enabled=True,
            )
            bypass_receipt = runtime.run(
                _payload(ZERO_HASH, command_id="git_status_short"),
                approval_store,
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(bypass_receipt.accepted)
        self.assertTrue(
            any("payload_field_forbidden:command_id" in failure for failure in bypass_receipt.failures)
        )
        self.assertFalse((root / "controlled-execution").exists())

    def test_approval_rejection_stops_before_queue_and_execution_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            approval_store = FileBackedApprovalRuntimeIntegration(
                runtime_root=root,
                artifact_store_relpath="approval-artifacts",
            )
            expired = _issue_approval(
                approval_store,
                expires_at="2026-05-29T00:00:20+00:00",
            )
            runtime = FileBackedControlledExecutionRuntime(
                runtime_root=root,
                enabled=True,
            )

            receipt = runtime.run(
                _payload(expired.approval_admission_hash),
                approval_store,
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(receipt.accepted)
        self.assertIn("approval_expired", receipt.failures)
        self.assertFalse(receipt.execution_performed)
        self.assertEqual(receipt.queue_record_hashes, ())
        self.assertNotEqual(receipt.failure_bundle_receipt_hash, ZERO_HASH)
        self.assertFalse((root / "controlled-execution" / "queue" / "jobs.jsonl").exists())

    def test_execution_failure_writes_result_artifact_transition_wal_and_failure_bundle(self) -> None:
        fake_response = _FakePreflightResponse(
            preflight_result=_FakePreflightResult(
                overall_status="PREFLIGHT_FAILED",
                preflight_result_hash=_hash("failed-preflight-result"),
                failure_reasons=("git_diff_check:NONZERO_EXIT",),
            ),
            evidence_manifest=_FakeEvidenceManifest(
                manifest_hash=_hash("failed-evidence-manifest"),
            ),
            execution_performed=True,
        )
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
            with mock.patch(
                "kernel.runtime.controlled_execution_runtime.run_human_invoked_minimal_controlled_preflight",
                return_value=fake_response,
            ):
                receipt = runtime.run(
                    _payload(approval.approval_admission_hash),
                    approval_store,
                    observed_at=OBSERVED_AT,
                )

            wal_records = FileBackedRealWalStorage(
                root / "controlled-execution" / "execution.real-wal.jsonl"
            ).read_records()
            failure_wal_records = FileBackedRealWalStorage(
                root
                / "controlled-execution"
                / "failure-bundles"
                / "failure.real-wal.jsonl"
            ).read_records()

        self.assertFalse(receipt.accepted)
        self.assertTrue(receipt.execution_performed)
        self.assertEqual(receipt.execution_status, "PREFLIGHT_FAILED")
        self.assertNotEqual(receipt.result_artifact_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.execution_wal_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.failure_bundle_receipt_hash, ZERO_HASH)
        self.assertEqual(wal_records[-1].record_type, "MINIMAL_CONTROLLED_EXECUTION")
        self.assertEqual(failure_wal_records[-1].record_type, "FAILURE_BUNDLE_EVENT")

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
