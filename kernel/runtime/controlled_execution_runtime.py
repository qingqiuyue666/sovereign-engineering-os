"""Controlled execution runtime integration V1.

This module coordinates the local controlled execution lifecycle over the
existing approval, queue, artifact, WAL, snapshot/replay, and failure-bundle
surfaces. It exposes no CLI, loop, network/provider/browser surface, or caller
selected command material.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence

from kernel.execution.minimal_controlled_preflight_api import (
    run_human_invoked_minimal_controlled_preflight,
)
from kernel.execution.minimal_controlled_preflight_sequence import PREFLIGHT_ORDER
from kernel.execution.minimal_controlled_wal_adapter_contract import (
    MinimalControlledWalAdapterRecord,
)
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    ApprovalRuntimeGatedPreflightResponse,
    ApprovalRuntimeIntegrationError,
    FileBackedApprovalRuntimeIntegration,
    run_approval_gated_minimal_controlled_wal_preflight,
)
from kernel.runtime.durable_job_queue import (
    DurableJobQueue,
    DurableJobQueueError,
)
from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
)
from kernel.stores.artifact_store_persistence import (
    ArtifactStorePersistenceError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)
from kernel.stores.snapshot_replay_reconstruction import (
    DEFAULT_ROLLBACK_PLAN_HASH,
    FileBackedSnapshotReplayReconstructor,
    SnapshotReplayOutputReceipt,
    SnapshotReplayReconstructionError,
)

__all__ = [
    "CONTROLLED_EXECUTION_RUNTIME_VERSION",
    "CONTROLLED_EXECUTION_QUEUE_ID",
    "ZERO_HASH",
    "ControlledExecutionRuntimeError",
    "ControlledExecutionRuntimeReceipt",
    "FileBackedControlledExecutionRuntime",
    "compute_controlled_execution_runtime_receipt_hash",
]

CONTROLLED_EXECUTION_RUNTIME_VERSION = "controlled_execution_runtime_v1"
CONTROLLED_EXECUTION_QUEUE_ID = "controlled-execution-runtime-v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_CONTROLLED_ROOT_RELPATH = "controlled-execution"
_RUNTIME_WAL_RELPATH = _CONTROLLED_ROOT_RELPATH + "/execution.real-wal.jsonl"
_QUEUE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/queue/jobs.jsonl"
_ARTIFACT_STORE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/artifacts"
_ARTIFACT_STORE_ID = "controlled-execution-artifacts-v1"
_SNAPSHOT_STORE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/snapshot-replay"
_FAILURE_STORE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/failure-bundles"
_FAILURE_WAL_RELPATH = _FAILURE_STORE_RELPATH + "/failure.real-wal.jsonl"
_FAILURE_ARTIFACT_STORE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/failure-artifacts"
_FAILURE_ARTIFACT_STORE_ID = "controlled-execution-failure-artifacts-v1"
_RECEIPT_STORE_RELPATH = _CONTROLLED_ROOT_RELPATH + "/receipts"

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)

_ALLOWED_PAYLOAD_FIELDS = frozenset(
    {
        "approval_admission_hash",
        "caller_intent",
        "execution_id",
        "human_invoked",
        "idempotency_key",
        "job_id",
        "preflight_id",
        "requested_at",
        "requester",
        "run_id",
        "single_run_scope",
        "snapshot_ref",
        "task_id",
        "use_case_ids",
        "worker_id",
    }
)
_FORBIDDEN_PAYLOAD_FIELDS = frozenset(
    {
        "append_callable",
        "args",
        "argv",
        "auto_reexecution",
        "background",
        "browser",
        "command",
        "command_id",
        "command_ids",
        "command_line",
        "commands",
        "content",
        "cwd",
        "env",
        "environment",
        "executable",
        "executable_path",
        "network",
        "output",
        "parallel",
        "path",
        "payload",
        "provider",
        "raw_output",
        "raw_stderr",
        "raw_stdout",
        "retry",
        "shell",
        "stderr",
        "stdout",
        "steps",
        "subprocess",
        "tasks",
        "timeout",
        "url",
        "workdir",
    }
)
_PREFLIGHT_STATUSES = frozenset(
    {
        "PREFLIGHT_PASSED",
        "PREFLIGHT_FAILED",
        "PREFLIGHT_NOT_ATTEMPTED",
        "PREFLIGHT_PARTIAL_FAILURE",
        "NOT_STARTED",
    }
)
_REJECTED_QUEUE_STATE = "not_queued"
_REJECTED_LEASE_ID = "not_leased"
_REJECTED_WORKER_ID = "not_assigned"


class ControlledExecutionRuntimeError(ValueError):
    """Raised when the controlled execution runtime fails closed."""


@dataclass(frozen=True)
class ControlledExecutionRuntimeReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    execution_id: str
    task_id: str
    run_id: str
    job_id: str
    preflight_id: str
    queue_id: str
    worker_id: str
    lease_id: str
    queue_terminal_state: str
    queue_record_hashes: tuple[str, ...]
    approval_gate_response_hash: str
    approval_consumption_receipt_hash: str
    wal_gated_preflight_response_hash: str
    controlled_preflight_result_hash: str
    controlled_preflight_manifest_hash: str
    execution_performed: bool
    execution_status: str
    result_artifact_record_hash: str
    result_artifact_manifest_hash: str
    execution_wal_record_hash: str
    pre_snapshot_receipt_hash: str
    post_snapshot_receipt_hash: str
    failure_bundle_receipt_hash: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != CONTROLLED_EXECUTION_RUNTIME_VERSION:
            raise ControlledExecutionRuntimeError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ControlledExecutionRuntimeError("accepted_must_be_bool")
        if not isinstance(self.execution_performed, bool):
            raise ControlledExecutionRuntimeError("execution_performed_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        object.__setattr__(
            self,
            "queue_record_hashes",
            _normalize_hash_sequence(self.queue_record_hashes, "queue_record_hashes"),
        )
        for field_name in (
            "execution_id",
            "task_id",
            "run_id",
            "job_id",
            "preflight_id",
            "queue_id",
            "worker_id",
            "lease_id",
            "queue_terminal_state",
            "execution_status",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        if self.execution_status not in _PREFLIGHT_STATUSES:
            raise ControlledExecutionRuntimeError("execution_status_invalid")
        for field_name in (
            "approval_gate_response_hash",
            "approval_consumption_receipt_hash",
            "wal_gated_preflight_response_hash",
            "controlled_preflight_result_hash",
            "controlled_preflight_manifest_hash",
            "result_artifact_record_hash",
            "result_artifact_manifest_hash",
            "execution_wal_record_hash",
            "pre_snapshot_receipt_hash",
            "post_snapshot_receipt_hash",
            "failure_bundle_receipt_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if self.accepted and self.failures:
            raise ControlledExecutionRuntimeError("accepted_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise ControlledExecutionRuntimeError("rejected_receipt_requires_failures")
        evidence_accepts = (
            not self.failures
            and self.execution_performed
            and self.execution_status == "PREFLIGHT_PASSED"
            and self.queue_terminal_state == "succeeded"
            and self.result_artifact_record_hash != ZERO_HASH
            and self.result_artifact_manifest_hash != ZERO_HASH
            and self.execution_wal_record_hash != ZERO_HASH
            and self.pre_snapshot_receipt_hash != ZERO_HASH
            and self.post_snapshot_receipt_hash != ZERO_HASH
            and self.failure_bundle_receipt_hash == ZERO_HASH
        )
        if self.accepted != evidence_accepts:
            raise ControlledExecutionRuntimeError("accepted_must_match_evidence")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_controlled_execution_runtime_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedControlledExecutionRuntime:
    """File-backed controlled execution lifecycle coordinator."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        enabled: bool = False,
        runtime_wal_relpath: str = _RUNTIME_WAL_RELPATH,
        queue_relpath: str = _QUEUE_RELPATH,
        queue_id: str = CONTROLLED_EXECUTION_QUEUE_ID,
        artifact_store_relpath: str = _ARTIFACT_STORE_RELPATH,
        artifact_store_id: str = _ARTIFACT_STORE_ID,
        snapshot_store_relpath: str = _SNAPSHOT_STORE_RELPATH,
        receipt_store_relpath: str = _RECEIPT_STORE_RELPATH,
    ) -> None:
        if not isinstance(enabled, bool):
            raise ControlledExecutionRuntimeError("enabled_must_be_bool")
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.enabled = enabled
        self.runtime_wal_relpath = _validate_relpath_text(
            runtime_wal_relpath,
            "runtime_wal_relpath",
            allow_empty=False,
        )
        self.queue_relpath = _validate_relpath_text(
            queue_relpath,
            "queue_relpath",
            allow_empty=False,
        )
        self.queue_id = _validated_identifier(queue_id, "queue_id")
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=False,
        )
        self.artifact_store_id = _validated_identifier(
            artifact_store_id,
            "artifact_store_id",
        )
        self.snapshot_store_relpath = _validate_relpath_text(
            snapshot_store_relpath,
            "snapshot_store_relpath",
            allow_empty=False,
        )
        self.receipt_store_relpath = _validate_relpath_text(
            receipt_store_relpath,
            "receipt_store_relpath",
            allow_empty=False,
        )

    def run(
        self,
        payload: Mapping[str, object],
        approval_runtime: FileBackedApprovalRuntimeIntegration,
        *,
        observed_at: str | None = None,
    ) -> ControlledExecutionRuntimeReceipt:
        observed = _timestamp(observed_at)
        data, admission_failures = _admit_payload(payload)
        if not self.enabled:
            return self._rejected_receipt(
                data,
                ("controlled_execution_runtime_disabled", *admission_failures),
                persist=False,
            )
        if admission_failures:
            return self._rejected_receipt(data, admission_failures, persist=False)
        if not isinstance(approval_runtime, FileBackedApprovalRuntimeIntegration):
            return self._rejected_receipt(
                data,
                ("approval_runtime_required",),
                persist=False,
            )

        try:
            approval_gate = run_approval_gated_minimal_controlled_wal_preflight(
                _approval_gate_payload(data, observed_at=observed),
                approval_runtime,
                self._append_wal_adapter_record,
                observed_at=observed,
            )
        except (ApprovalRuntimeIntegrationError, RealWalStorageError, ValueError) as exc:
            return self._rejected_receipt(
                data,
                ("approval_gate_failed:" + exc.__class__.__name__, str(exc)),
                persist=False,
            )

        if not approval_gate.accepted:
            failure_receipt_hash = self._record_failure_bundle(
                failure_kind="approval_rejection",
                data=data,
                approval_gate=approval_gate,
                evidence_hashes={
                    "approval_gate_response_hash": approval_gate.response_hash,
                    "approval_consumption_receipt_hash": (
                        approval_gate.approval_consumption_receipt_hash
                    ),
                },
                result_artifact_record_hash=ZERO_HASH,
                snapshot_reconstruction_hash=ZERO_HASH,
                original_failure=None,
                observed_at=observed,
            )
            return self._rejected_receipt(
                data,
                approval_gate.rejection_reasons,
                approval_gate=approval_gate,
                failure_bundle_receipt_hash=failure_receipt_hash,
                persist=True,
            )

        queue = self._queue()
        try:
            queue.submit_job(
                job_id=str(data["job_id"]),
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                payload=_queue_submit_payload(data, approval_gate),
                idempotency_key=str(data["idempotency_key"]),
                max_attempts=1,
                priority=50,
                submitted_at=observed,
            )
            queue.queue_job(str(data["job_id"]), queued_at=observed)
            leased = queue.lease_next(
                worker_id=str(data["worker_id"]),
                leased_at=observed,
                lease_timeout_seconds=300,
            )
        except DurableJobQueueError as exc:
            failure_receipt_hash = self._record_failure_bundle(
                failure_kind="queue_invalid_transition",
                data=data,
                approval_gate=approval_gate,
                evidence_hashes={
                    "approval_gate_response_hash": approval_gate.response_hash,
                    "queue_failure_hash": _sha256_text(exc.__class__.__name__),
                },
                result_artifact_record_hash=ZERO_HASH,
                snapshot_reconstruction_hash=ZERO_HASH,
                original_failure=exc,
                observed_at=observed,
            )
            return self._rejected_receipt(
                data,
                ("queue_lifecycle_failed:" + exc.__class__.__name__, str(exc)),
                approval_gate=approval_gate,
                queue_record_hashes=self._queue_record_hashes(),
                failure_bundle_receipt_hash=failure_receipt_hash,
                persist=True,
            )

        pre_snapshot = self._capture_snapshot(
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            snapshot_kind="pre_execution",
            observed_at=observed,
        )
        if not pre_snapshot.accepted:
            terminal_state = self._fail_leased_job(
                queue,
                job_id=str(data["job_id"]),
                lease_id=leased.lease_id,
                reason="pre_execution_snapshot_rejected",
                observed_at=observed,
            )
            failure_receipt_hash = self._record_failure_bundle(
                failure_kind="replay_reconstruction_failure",
                data=data,
                approval_gate=approval_gate,
                evidence_hashes={
                    "pre_snapshot_receipt_hash": pre_snapshot.receipt_hash,
                },
                result_artifact_record_hash=ZERO_HASH,
                snapshot_reconstruction_hash=pre_snapshot.receipt_hash,
                original_failure=None,
                observed_at=observed,
            )
            return self._rejected_receipt(
                data,
                ("pre_execution_snapshot_rejected", *pre_snapshot.failures),
                approval_gate=approval_gate,
                queue_terminal_state=terminal_state,
                worker_id=str(data["worker_id"]),
                lease_id=leased.lease_id,
                queue_record_hashes=self._queue_record_hashes(),
                pre_snapshot_receipt_hash=pre_snapshot.receipt_hash,
                failure_bundle_receipt_hash=failure_receipt_hash,
                persist=True,
            )

        try:
            execution_response = run_human_invoked_minimal_controlled_preflight(
                _execution_boundary_payload(data, observed_at=observed)
            )
        except Exception as exc:  # noqa: BLE001 - fail closed around the boundary.
            terminal_state = self._fail_leased_job(
                queue,
                job_id=str(data["job_id"]),
                lease_id=leased.lease_id,
                reason="execution_boundary_exception",
                observed_at=observed,
            )
            failure_receipt_hash = self._record_failure_bundle(
                failure_kind="execution_boundary_failure",
                data=data,
                approval_gate=approval_gate,
                evidence_hashes={
                    "pre_snapshot_receipt_hash": pre_snapshot.receipt_hash,
                    "execution_exception_hash": _sha256_text(exc.__class__.__name__),
                },
                result_artifact_record_hash=ZERO_HASH,
                snapshot_reconstruction_hash=pre_snapshot.receipt_hash,
                original_failure=exc,
                observed_at=observed,
            )
            return self._rejected_receipt(
                data,
                ("execution_boundary_failed:" + exc.__class__.__name__,),
                approval_gate=approval_gate,
                queue_terminal_state=terminal_state,
                worker_id=str(data["worker_id"]),
                lease_id=leased.lease_id,
                queue_record_hashes=self._queue_record_hashes(),
                pre_snapshot_receipt_hash=pre_snapshot.receipt_hash,
                failure_bundle_receipt_hash=failure_receipt_hash,
                persist=True,
            )

        execution_status = str(execution_response.preflight_result.overall_status)
        result_artifact = self._write_result_artifact(
            data=data,
            approval_gate=approval_gate,
            execution_response=execution_response,
            pre_snapshot=pre_snapshot,
            observed_at=observed,
        )
        execution_wal_record_hash = self._append_execution_result_wal(
            data=data,
            approval_gate=approval_gate,
            execution_response=execution_response,
            result_artifact_record_hash=result_artifact.record_hash,
            result_artifact_manifest_hash=result_artifact.manifest.manifest_hash,
            pre_snapshot_receipt_hash=pre_snapshot.receipt_hash,
            queue_record_hashes=self._queue_record_hashes(),
            observed_at=observed,
        )

        failures: tuple[str, ...] = ()
        failure_bundle_receipt_hash = ZERO_HASH
        if (
            execution_status == "PREFLIGHT_PASSED"
            and execution_response.execution_performed is True
        ):
            terminal = queue.succeed_job(
                job_id=str(data["job_id"]),
                lease_id=leased.lease_id,
                completion_payload={
                    "execution_wal_record_hash": execution_wal_record_hash,
                    "preflight_result_hash": (
                        execution_response.preflight_result.preflight_result_hash
                    ),
                    "result_artifact_record_hash": result_artifact.record_hash,
                },
                succeeded_at=observed,
            )
            queue_terminal_state = terminal.state
        else:
            failure_bundle_receipt_hash = self._record_failure_bundle(
                failure_kind="execution_boundary_failure",
                data=data,
                approval_gate=approval_gate,
                evidence_hashes={
                    "controlled_preflight_result_hash": (
                        execution_response.preflight_result.preflight_result_hash
                    ),
                    "controlled_preflight_manifest_hash": (
                        execution_response.evidence_manifest.manifest_hash
                    ),
                    "execution_wal_record_hash": execution_wal_record_hash,
                },
                result_artifact_record_hash=result_artifact.record_hash,
                snapshot_reconstruction_hash=pre_snapshot.receipt_hash,
                original_failure=None,
                observed_at=observed,
            )
            terminal = self._fail_leased_job(
                queue,
                job_id=str(data["job_id"]),
                lease_id=leased.lease_id,
                reason="controlled_execution_preflight_failed",
                observed_at=observed,
            )
            queue_terminal_state = terminal
            failures = (
                "controlled_execution_preflight_failed:" + execution_status,
                *_normalize_failure_texts(
                    execution_response.preflight_result.failure_reasons
                ),
            )

        post_snapshot = self._capture_snapshot(
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            snapshot_kind="post_execution",
            observed_at=observed,
        )
        if not post_snapshot.accepted:
            failures = (
                *failures,
                "post_execution_snapshot_rejected",
                *post_snapshot.failures,
            )
            if failure_bundle_receipt_hash == ZERO_HASH:
                failure_bundle_receipt_hash = self._record_failure_bundle(
                    failure_kind="replay_reconstruction_failure",
                    data=data,
                    approval_gate=approval_gate,
                    evidence_hashes={
                        "post_snapshot_receipt_hash": post_snapshot.receipt_hash,
                    },
                    result_artifact_record_hash=result_artifact.record_hash,
                    snapshot_reconstruction_hash=post_snapshot.receipt_hash,
                    original_failure=None,
                    observed_at=observed,
                )

        receipt = ControlledExecutionRuntimeReceipt(
            integration_version=CONTROLLED_EXECUTION_RUNTIME_VERSION,
            accepted=not failures,
            failures=failures,
            execution_id=str(data["execution_id"]),
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            preflight_id=str(data["preflight_id"]),
            queue_id=self.queue_id,
            worker_id=str(data["worker_id"]),
            lease_id=leased.lease_id,
            queue_terminal_state=queue_terminal_state,
            queue_record_hashes=self._queue_record_hashes(),
            approval_gate_response_hash=approval_gate.response_hash,
            approval_consumption_receipt_hash=(
                approval_gate.approval_consumption_receipt_hash
            ),
            wal_gated_preflight_response_hash=approval_gate.preflight_api_response_hash,
            controlled_preflight_result_hash=(
                execution_response.preflight_result.preflight_result_hash
            ),
            controlled_preflight_manifest_hash=(
                execution_response.evidence_manifest.manifest_hash
            ),
            execution_performed=execution_response.execution_performed,
            execution_status=execution_status,
            result_artifact_record_hash=result_artifact.record_hash,
            result_artifact_manifest_hash=result_artifact.manifest.manifest_hash,
            execution_wal_record_hash=execution_wal_record_hash,
            pre_snapshot_receipt_hash=pre_snapshot.receipt_hash,
            post_snapshot_receipt_hash=post_snapshot.receipt_hash,
            failure_bundle_receipt_hash=failure_bundle_receipt_hash,
        )
        self._persist_receipt(receipt)
        return receipt

    def _queue(self) -> DurableJobQueue:
        return DurableJobQueue(
            path=self._resolve_relpath(self.queue_relpath, "queue_relpath"),
            queue_id=self.queue_id,
        )

    def _append_wal_adapter_record(
        self,
        record: MinimalControlledWalAdapterRecord,
    ) -> None:
        if not isinstance(record, MinimalControlledWalAdapterRecord):
            raise ControlledExecutionRuntimeError("wal_adapter_record_required")
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        FileBackedRealWalStorage(wal_path).append(
            record_type="MINIMAL_CONTROLLED_EXECUTION",
            task_id=record.task_id,
            run_id=record.run_id,
            payload_hash=record.record_hash,
            digest_bindings={
                "wal_adapter_record_hash": record.record_hash,
                "wal_adapter_record_material_hash": _sha256_json(record.as_dict()),
                "wal_adapter_record_type_hash": _sha256_text(record.record_type),
                "wal_adapter_sequence_hash": _sha256_text(str(record.sequence)),
            },
            created_at=record.created_at,
        )

    def _write_result_artifact(
        self,
        *,
        data: Mapping[str, object],
        approval_gate: ApprovalRuntimeGatedPreflightResponse,
        execution_response: object,
        pre_snapshot: SnapshotReplayOutputReceipt,
        observed_at: str,
    ):
        artifact_root = self._resolve_relpath(
            self.artifact_store_relpath,
            "artifact_store_relpath",
        )
        material = _execution_result_material(
            data=data,
            approval_gate=approval_gate,
            execution_response=execution_response,
            pre_snapshot=pre_snapshot,
            queue_record_hashes=self._queue_record_hashes(),
        )
        try:
            return FileBackedArtifactStore(
                artifact_root,
                store_id=self.artifact_store_id,
            ).write_json_artifact(
                artifact_type="worker_receipt",
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                payload=material,
                provenance_hash=_sha256_json(material),
                metadata={
                    "execution_id": str(data["execution_id"]),
                    "execution_status": str(
                        execution_response.preflight_result.overall_status
                    ),
                    "integration_version": CONTROLLED_EXECUTION_RUNTIME_VERSION,
                },
                created_at=observed_at,
            )
        except (ArtifactStorePersistenceError, ValueError) as exc:
            raise ControlledExecutionRuntimeError(
                "result_artifact_write_failed:" + str(exc)
            ) from exc

    def _append_execution_result_wal(
        self,
        *,
        data: Mapping[str, object],
        approval_gate: ApprovalRuntimeGatedPreflightResponse,
        execution_response: object,
        result_artifact_record_hash: str,
        result_artifact_manifest_hash: str,
        pre_snapshot_receipt_hash: str,
        queue_record_hashes: Sequence[str],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        material = {
            "approval_gate_response_hash": approval_gate.response_hash,
            "controlled_preflight_manifest_hash": (
                execution_response.evidence_manifest.manifest_hash
            ),
            "controlled_preflight_result_hash": (
                execution_response.preflight_result.preflight_result_hash
            ),
            "execution_id": str(data["execution_id"]),
            "execution_performed": execution_response.execution_performed,
            "execution_status": str(execution_response.preflight_result.overall_status),
            "pre_snapshot_receipt_hash": pre_snapshot_receipt_hash,
            "queue_record_hashes_hash": _sha256_json(tuple(queue_record_hashes)),
            "result_artifact_manifest_hash": result_artifact_manifest_hash,
            "result_artifact_record_hash": result_artifact_record_hash,
        }
        payload_hash = _sha256_json(material)
        try:
            receipt = FileBackedRealWalStorage(wal_path).append(
                record_type="MINIMAL_CONTROLLED_EXECUTION",
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                payload_hash=payload_hash,
                digest_bindings={
                    "approval_gate_response_hash": approval_gate.response_hash,
                    "controlled_preflight_manifest_hash": (
                        execution_response.evidence_manifest.manifest_hash
                    ),
                    "controlled_preflight_result_hash": (
                        execution_response.preflight_result.preflight_result_hash
                    ),
                    "execution_material_hash": payload_hash,
                    "pre_snapshot_receipt_hash": pre_snapshot_receipt_hash,
                    "queue_record_hashes_hash": _sha256_json(tuple(queue_record_hashes)),
                    "result_artifact_manifest_hash": result_artifact_manifest_hash,
                    "result_artifact_record_hash": result_artifact_record_hash,
                },
                created_at=observed_at,
            )
        except RealWalStorageError as exc:
            raise ControlledExecutionRuntimeError(
                "execution_wal_append_failed:" + str(exc)
            ) from exc
        return receipt.record_hash

    def _capture_snapshot(
        self,
        *,
        task_id: str,
        run_id: str,
        snapshot_kind: str,
        observed_at: str,
    ) -> SnapshotReplayOutputReceipt:
        try:
            return FileBackedSnapshotReplayReconstructor(
                runtime_root=self.runtime_root,
                wal_source_relpath=self.runtime_wal_relpath,
                artifact_store_relpath=self.artifact_store_relpath,
                queue_source_relpath=self.queue_relpath,
                queue_id=self.queue_id,
                snapshot_store_relpath=self.snapshot_store_relpath,
                artifact_store_id=self.artifact_store_id,
            ).capture_snapshot(
                task_id=task_id,
                run_id=run_id,
                snapshot_kind=snapshot_kind,
                rollback_plan_hash=DEFAULT_ROLLBACK_PLAN_HASH,
                created_at=observed_at,
                observed_at=observed_at,
            )
        except SnapshotReplayReconstructionError as exc:
            return SnapshotReplayOutputReceipt(
                output_receipt_version="snapshot_replay_output_receipt_v1",
                accepted=False,
                failures=("snapshot_capture_failed:" + str(exc),),
                task_id=task_id,
                run_id=run_id,
                input_manifest_hash=ZERO_HASH,
                expected_snapshot_root_hash=ZERO_HASH,
                observed_snapshot_root_hash=ZERO_HASH,
                snapshot_id="untrusted-replay-rejected",
                snapshot_manifest_hash=ZERO_HASH,
                snapshot_manifest_relpath="",
                observed_at=observed_at,
            )

    def _record_failure_bundle(
        self,
        *,
        failure_kind: str,
        data: Mapping[str, object],
        approval_gate: ApprovalRuntimeGatedPreflightResponse | None,
        evidence_hashes: Mapping[str, str],
        result_artifact_record_hash: str,
        snapshot_reconstruction_hash: str,
        original_failure: BaseException | None,
        observed_at: str,
    ) -> str:
        center = FileBackedFailureBundleCenterIntegration(
            runtime_root=self.runtime_root,
            failure_store_relpath=_FAILURE_STORE_RELPATH,
            failure_wal_relpath=_FAILURE_WAL_RELPATH,
            artifact_store_relpath=_FAILURE_ARTIFACT_STORE_RELPATH,
            artifact_store_id=_FAILURE_ARTIFACT_STORE_ID,
        )
        receipt = center.record_critical_failure(
            failure_kind=failure_kind,
            task_id=str(data["task_id"]),
            job_id=str(data["job_id"]),
            run_id=str(data["run_id"]),
            context_hashes=_failure_context_hashes(
                data=data,
                approval_gate=approval_gate,
                queue_record_hashes=self._queue_record_hashes(),
                wal_pointer_hash=self._last_runtime_wal_hash(),
                result_artifact_record_hash=result_artifact_record_hash,
            ),
            recovery_plan_hash=_sha256_text(
                "manual-review:" + str(data["execution_id"])
            ),
            snapshot_reconstruction_hash=snapshot_reconstruction_hash,
            evidence_hashes=evidence_hashes,
            original_failure=original_failure,
            observed_at=observed_at,
        )
        return receipt.receipt_hash

    def _fail_leased_job(
        self,
        queue: DurableJobQueue,
        *,
        job_id: str,
        lease_id: str,
        reason: str,
        observed_at: str,
    ) -> str:
        try:
            state = queue.fail_job(
                job_id=job_id,
                lease_id=lease_id,
                reason=reason,
                failed_at=observed_at,
                dead_letter_on_exhaustion=True,
            )
            return state.state
        except DurableJobQueueError:
            return "queue_failure_not_recorded"

    def _queue_record_hashes(self) -> tuple[str, ...]:
        try:
            return tuple(record.record_hash for record in self._queue().records)
        except DurableJobQueueError:
            return ()

    def _last_runtime_wal_hash(self) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        if not wal_path.exists():
            return ZERO_HASH
        try:
            records = FileBackedRealWalStorage(wal_path).read_records()
        except RealWalStorageError:
            return ZERO_HASH
        return ZERO_HASH if not records else records[-1].record_hash

    def _rejected_receipt(
        self,
        data: Mapping[str, object],
        failures: Sequence[str],
        *,
        approval_gate: ApprovalRuntimeGatedPreflightResponse | None = None,
        queue_terminal_state: str = _REJECTED_QUEUE_STATE,
        worker_id: str = _REJECTED_WORKER_ID,
        lease_id: str = _REJECTED_LEASE_ID,
        queue_record_hashes: Sequence[str] = (),
        pre_snapshot_receipt_hash: str = ZERO_HASH,
        failure_bundle_receipt_hash: str = ZERO_HASH,
        persist: bool,
    ) -> ControlledExecutionRuntimeReceipt:
        receipt = ControlledExecutionRuntimeReceipt(
            integration_version=CONTROLLED_EXECUTION_RUNTIME_VERSION,
            accepted=False,
            failures=tuple(_normalize_failure_texts(failures)),
            execution_id=_safe_identity(data, "execution_id", "unknown-execution"),
            task_id=_safe_identity(data, "task_id", "unknown-task"),
            run_id=_safe_identity(data, "run_id", "unknown-run"),
            job_id=_safe_identity(data, "job_id", "unknown-job"),
            preflight_id=_safe_identity(data, "preflight_id", "unknown-preflight"),
            queue_id=self.queue_id,
            worker_id=worker_id,
            lease_id=lease_id,
            queue_terminal_state=queue_terminal_state,
            queue_record_hashes=tuple(queue_record_hashes),
            approval_gate_response_hash=ZERO_HASH
            if approval_gate is None
            else approval_gate.response_hash,
            approval_consumption_receipt_hash=ZERO_HASH
            if approval_gate is None
            else approval_gate.approval_consumption_receipt_hash,
            wal_gated_preflight_response_hash=ZERO_HASH
            if approval_gate is None
            else approval_gate.preflight_api_response_hash,
            controlled_preflight_result_hash=ZERO_HASH,
            controlled_preflight_manifest_hash=ZERO_HASH,
            execution_performed=False,
            execution_status="NOT_STARTED",
            result_artifact_record_hash=ZERO_HASH,
            result_artifact_manifest_hash=ZERO_HASH,
            execution_wal_record_hash=ZERO_HASH,
            pre_snapshot_receipt_hash=pre_snapshot_receipt_hash,
            post_snapshot_receipt_hash=ZERO_HASH,
            failure_bundle_receipt_hash=failure_bundle_receipt_hash,
        )
        if persist:
            self._persist_receipt(receipt)
        return receipt

    def _persist_receipt(self, receipt: ControlledExecutionRuntimeReceipt) -> None:
        relpath = (
            self.receipt_store_relpath
            + "/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        _write_json_no_overwrite(
            self._resolve_relpath(relpath, "receipt_relpath"),
            receipt.as_dict(),
            equivalence_excluded_keys=(),
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        clean = _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / clean
        current = self.runtime_root
        for part in PurePosixPath(clean).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ControlledExecutionRuntimeError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise ControlledExecutionRuntimeError(field_name + "_escapes_runtime_root")
        return resolved


def compute_controlled_execution_runtime_receipt_hash(
    receipt: ControlledExecutionRuntimeReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, ControlledExecutionRuntimeReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _admit_payload(payload: Mapping[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    if not isinstance(payload, Mapping):
        return _fallback_data(), ("payload_must_be_mapping",)
    data = dict(payload)
    failures: list[str] = []
    forbidden = sorted(_FORBIDDEN_PAYLOAD_FIELDS.intersection(data))
    if forbidden:
        failures.append("payload_field_forbidden:" + ",".join(forbidden))
    extra = sorted(set(data) - _ALLOWED_PAYLOAD_FIELDS)
    if extra:
        failures.append("payload_field_not_allowed:" + ",".join(extra))
    for field_name in (
        "approval_admission_hash",
        "execution_id",
        "idempotency_key",
        "job_id",
        "preflight_id",
        "requested_at",
        "requester",
        "run_id",
        "task_id",
        "worker_id",
    ):
        if not isinstance(data.get(field_name), str) or not data[field_name]:
            failures.append(field_name + "_required")
    if isinstance(data.get("approval_admission_hash"), str):
        try:
            _require_sha256(data["approval_admission_hash"], "approval_admission_hash")
        except ControlledExecutionRuntimeError as exc:
            failures.append(str(exc))
    for field_name in ("human_invoked", "single_run_scope"):
        if data.get(field_name) is not True:
            failures.append(field_name + "_required_true")
    for field_name in ("caller_intent", "snapshot_ref"):
        if field_name in data and (
            not isinstance(data[field_name], str) or not data[field_name]
        ):
            failures.append(field_name + "_must_be_nonempty_string")
    if "use_case_ids" in data:
        use_case_ids = data["use_case_ids"]
        if not isinstance(use_case_ids, (list, tuple)) or isinstance(
            use_case_ids,
            (str, bytes),
        ):
            failures.append("use_case_ids_must_be_sequence")
        elif not all(isinstance(value, str) and value for value in use_case_ids):
            failures.append("use_case_ids_must_be_nonempty_strings")
    try:
        _scan_json_safety(data)
    except ControlledExecutionRuntimeError as exc:
        failures.append(str(exc))
    return {**_fallback_data(), **data}, tuple(_dedupe(failures))


def _approval_gate_payload(data: Mapping[str, object], *, observed_at: str) -> dict[str, object]:
    request_hash = _sha256_json(
        {
            "execution_id": data["execution_id"],
            "stage": "controlled_execution_runtime_admission",
            "task_id": data["task_id"],
        }
    )
    decision_hash = _sha256_json(
        {
            "approval_admission_hash": data["approval_admission_hash"],
            "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
            "stage": "controlled_execution_runtime_approval_gate",
        }
    )
    admission_hash = _sha256_json(
        {
            "decision_hash": decision_hash,
            "request_hash": request_hash,
            "stage": "controlled_execution_runtime_queue_admission",
        }
    )
    planned_failure_hash = _sha256_json(
        {
            "admission_hash": admission_hash,
            "execution_id": data["execution_id"],
            "execution_performed": False,
            "stage": "append_before_execution_gate",
        }
    )
    verifier_input_hash = _sha256_json(
        {
            "admission_hash": admission_hash,
            "execution_id": data["execution_id"],
            "request_hash": request_hash,
        }
    )
    verifier_binding_hash = _sha256_json(
        {
            "decision_hash": decision_hash,
            "failure_bundle_hash": planned_failure_hash,
            "verifier_input_hash": verifier_input_hash,
        }
    )
    preflight_hash = _sha256_json(
        {
            "execution_id": data["execution_id"],
            "execution_performed": False,
            "ordered_command_ids": PREFLIGHT_ORDER,
            "stage": "controlled_execution_preflight_gate",
        }
    )
    child_hashes = _planned_child_hashes(data)
    base = {
        "command_id": "controlled_execution_runtime",
        "created_at": observed_at,
        "decision_hash": decision_hash,
        "preflight_id": data["preflight_id"],
        "request_hash": request_hash,
        "run_id": data["run_id"],
        "task_id": data["task_id"],
    }
    return {
        "admission_evidence": {
            **base,
            "admission_record_hash": admission_hash,
        },
        "api_invocation_id": "controlled-execution-approval-gate-" + str(data["execution_id"]),
        "approval_admission_hash": data["approval_admission_hash"],
        "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
        "caller_intent": str(
            data.get("caller_intent", "run controlled execution runtime")
        ),
        "human_invoked": True,
        "outcome_evidence": {
            **base,
            "failure_bundle_hash": planned_failure_hash,
            "outcome_type": "EXECUTION_FAILURE",
            "execution_performed": False,
        },
        "preflight_id": data["preflight_id"],
        "preflight_result_evidence": {
            "child_admission_hashes": child_hashes["child_admission_hashes"],
            "child_decision_hashes": child_hashes["child_decision_hashes"],
            "child_failure_bundle_hashes": child_hashes["child_failure_bundle_hashes"],
            "child_receipt_hashes": ("", ""),
            "child_request_hashes": child_hashes["child_request_hashes"],
            "child_verifier_binding_hashes": child_hashes[
                "child_verifier_binding_hashes"
            ],
            "child_verifier_input_hashes": child_hashes["child_verifier_input_hashes"],
            "execution_performed": False,
            "ordered_command_ids": PREFLIGHT_ORDER,
            "post_snapshot_hashes": child_hashes["post_snapshot_hashes"],
            "pre_snapshot_hashes": child_hashes["pre_snapshot_hashes"],
            "preflight_id": data["preflight_id"],
            "preflight_result_hash": preflight_hash,
            "run_id": data["run_id"],
            "task_id": data["task_id"],
        },
        "requested_at": observed_at,
        "requester": data["requester"],
        "run_id": data["run_id"],
        "single_run_scope": True,
        "task_id": data["task_id"],
        "verifier_binding_evidence": {
            **base,
            "admission_record_hash": admission_hash,
            "execution_performed": False,
            "failure_bundle_hash": planned_failure_hash,
            "verifier_binding_hash": verifier_binding_hash,
            "verifier_input_hash": verifier_input_hash,
        },
        "wrapper_input_id": "controlled-execution-wrapper-" + str(data["execution_id"]),
    }


def _planned_child_hashes(data: Mapping[str, object]) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for field_name in (
        "child_request_hashes",
        "child_decision_hashes",
        "child_admission_hashes",
        "child_verifier_input_hashes",
        "child_verifier_binding_hashes",
        "child_failure_bundle_hashes",
        "pre_snapshot_hashes",
        "post_snapshot_hashes",
    ):
        result[field_name] = tuple(
            _sha256_json(
                {
                    "command_id": command_id,
                    "execution_id": data["execution_id"],
                    "field": field_name,
                    "preflight_id": data["preflight_id"],
                }
            )
            for command_id in PREFLIGHT_ORDER
        )
    return result


def _queue_submit_payload(
    data: Mapping[str, object],
    approval_gate: ApprovalRuntimeGatedPreflightResponse,
) -> dict[str, object]:
    return {
        "approval_gate_response_hash": approval_gate.response_hash,
        "approval_scope_hash": _sha256_text(APPROVAL_RUNTIME_EXECUTION_SCOPE),
        "execution_id_hash": _sha256_text(str(data["execution_id"])),
        "human_invoked": True,
        "preflight_id_hash": _sha256_text(str(data["preflight_id"])),
        "single_run_scope": True,
        "wal_gated_preflight_response_hash": approval_gate.preflight_api_response_hash,
    }


def _execution_boundary_payload(
    data: Mapping[str, object],
    *,
    observed_at: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "caller_intent": str(
            data.get("caller_intent", "run controlled execution preflight")
        ),
        "preflight_id": data["preflight_id"],
        "requested_at": observed_at,
        "requester": data["requester"],
        "run_id": data["run_id"],
        "snapshot_ref": str(data.get("snapshot_ref", "controlled-execution-runtime")),
        "task_id": data["task_id"],
        "use_case_ids": tuple(
            data.get("use_case_ids", ("uc_520_controlled_execution_runtime",))
        ),
    }
    return payload


def _execution_result_material(
    *,
    data: Mapping[str, object],
    approval_gate: ApprovalRuntimeGatedPreflightResponse,
    execution_response: object,
    pre_snapshot: SnapshotReplayOutputReceipt,
    queue_record_hashes: Sequence[str],
) -> dict[str, object]:
    failure_reasons = tuple(execution_response.preflight_result.failure_reasons)
    return {
        "approval_consumption_receipt_hash": approval_gate.approval_consumption_receipt_hash,
        "approval_gate_response_hash": approval_gate.response_hash,
        "controlled_preflight_manifest_hash": (
            execution_response.evidence_manifest.manifest_hash
        ),
        "controlled_preflight_result_hash": (
            execution_response.preflight_result.preflight_result_hash
        ),
        "execution_id_hash": _sha256_text(str(data["execution_id"])),
        "execution_performed": execution_response.execution_performed,
        "execution_status": str(execution_response.preflight_result.overall_status),
        "failure_reasons_hash": _sha256_json(failure_reasons),
        "job_id_hash": _sha256_text(str(data["job_id"])),
        "lease_scope_hash": _sha256_text(str(data["worker_id"])),
        "ordered_command_ids_hash": _sha256_json(PREFLIGHT_ORDER),
        "pre_snapshot_receipt_hash": pre_snapshot.receipt_hash,
        "queue_record_hashes_hash": _sha256_json(tuple(queue_record_hashes)),
        "wal_gated_preflight_response_hash": approval_gate.preflight_api_response_hash,
    }


def _failure_context_hashes(
    *,
    data: Mapping[str, object],
    approval_gate: ApprovalRuntimeGatedPreflightResponse | None,
    queue_record_hashes: Sequence[str],
    wal_pointer_hash: str,
    result_artifact_record_hash: str,
) -> dict[str, str]:
    approval_hash = ZERO_HASH if approval_gate is None else approval_gate.response_hash
    return {
        "approval_rejection_context_hash": approval_hash,
        "artifact_ids_hash": result_artifact_record_hash
        if result_artifact_record_hash != ZERO_HASH
        else _sha256_text("artifact:none"),
        "corruption_evidence_hash": _sha256_text("corruption:none"),
        "hash_mismatch_context_hash": _sha256_text("hash-mismatch:none"),
        "job_context_hash": _sha256_text(str(data["job_id"])),
        "missing_record_context_hash": _sha256_text("missing-record:none"),
        "queue_transition_context_hash": _sha256_json(tuple(queue_record_hashes)),
        "replay_snapshot_context_hash": _sha256_text("snapshot:pending"),
        "run_context_hash": _sha256_text(str(data["run_id"])),
        "task_context_hash": _sha256_text(str(data["task_id"])),
        "wal_pointer_hash": wal_pointer_hash
        if wal_pointer_hash != ZERO_HASH
        else _sha256_text("wal:none"),
        "watchdog_failure_context_hash": _sha256_text("watchdog:none"),
        "worker_failure_context_hash": _sha256_text(str(data["worker_id"])),
    }


def _fallback_data() -> dict[str, object]:
    return {
        "approval_admission_hash": ZERO_HASH,
        "execution_id": "unknown-execution",
        "idempotency_key": "unknown-idempotency",
        "job_id": "unknown-job",
        "preflight_id": "unknown-preflight",
        "requested_at": "1970-01-01T00:00:00+00:00",
        "requester": "unknown-requester",
        "run_id": "unknown-run",
        "task_id": "unknown-task",
        "worker_id": "unknown-worker",
    }


def _safe_identity(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name)
    if isinstance(value, str) and value:
        return value
    return default


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ControlledExecutionRuntimeError("failures_must_be_sequence")
    failures = tuple(_normalize_failure_texts(value))
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _normalize_failure_texts(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        return (str(value),)
    return tuple(str(item) for item in value if str(item))


def _normalize_hash_sequence(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ControlledExecutionRuntimeError(field_name + "_must_be_sequence")
    normalized = tuple(str(item) for item in value)
    for item in normalized:
        _require_sha256(item, field_name)
    return normalized


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        _require_sha256(current, field_name)
        if current != expected:
            raise ControlledExecutionRuntimeError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise ControlledExecutionRuntimeError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise ControlledExecutionRuntimeError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise ControlledExecutionRuntimeError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise ControlledExecutionRuntimeError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise ControlledExecutionRuntimeError(field_name + "_required")
    if "\\" in value:
        raise ControlledExecutionRuntimeError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ControlledExecutionRuntimeError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _validated_identifier(value: object, field_name: str) -> str:
    _require_nonempty_string(value, field_name)
    text = str(value)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,95}", text):
        raise ControlledExecutionRuntimeError(field_name + "_invalid")
    return text


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise ControlledExecutionRuntimeError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise ControlledExecutionRuntimeError(field_name + "_secret_like")


def _scan_json_safety(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_PAYLOAD_FIELDS:
                raise ControlledExecutionRuntimeError(
                    "unsafe_payload_field_forbidden:" + ".".join(path + (key_text,))
                )
            if _SECRET_KEY_PATTERN.search(key_text) and not key_text.endswith("_hash"):
                if key_text not in {"approval_admission_hash", "idempotency_key"}:
                    raise ControlledExecutionRuntimeError(
                        "unsafe_payload_field_secret_like:" + ".".join(path + (key_text,))
                    )
            _scan_json_safety(item, path=path + (key_text,))
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_json_safety(item, path=path + (str(index),))
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        lowered = value.lower()
        for marker in (
            "api_key=",
            "authorization:",
            "bearer ",
            "os." + "environ",
            "password=",
            "private_key",
            "secret=",
            "token=",
        ):
            if marker in lowered:
                raise ControlledExecutionRuntimeError(
                    "unsafe_payload_value_forbidden:" + ".".join(path)
                )
        return
    raise ControlledExecutionRuntimeError(
        "unsafe_payload_value_type:" + ".".join(path)
    )


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ControlledExecutionRuntimeError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ControlledExecutionRuntimeError(field_name + "_must_be_sha256")


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ControlledExecutionRuntimeError("timestamp_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _write_json_no_overwrite(
    path: Path,
    payload: Mapping[str, object],
    *,
    equivalence_excluded_keys: tuple[str, ...],
) -> None:
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    if path.exists():
        if path.is_symlink():
            raise ControlledExecutionRuntimeError("receipt_target_is_symlink")
        if not path.is_file():
            raise ControlledExecutionRuntimeError("receipt_target_not_file")
        if path.read_bytes() == data:
            return
        if equivalence_excluded_keys and _same_except_keys(
            path,
            payload,
            equivalence_excluded_keys,
        ):
            return
        raise ControlledExecutionRuntimeError("receipt_target_mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ControlledExecutionRuntimeError("receipt_parent_is_symlink")
    temp_path = path.with_name(
        "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
    )
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise ControlledExecutionRuntimeError("receipt_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        if path.exists():
            raise ControlledExecutionRuntimeError("receipt_target_exists")
        temp_path.rename(path)
        _fsync_parent(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _same_except_keys(
    path: Path,
    payload: Mapping[str, object],
    excluded_keys: tuple[str, ...],
) -> bool:
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(existing, Mapping):
        return False
    existing_clean = dict(existing)
    payload_clean = dict(payload)
    for key in excluded_keys:
        existing_clean.pop(key, None)
        payload_clean.pop(key, None)
    return _json_ready(existing_clean) == _json_ready(payload_clean)


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
