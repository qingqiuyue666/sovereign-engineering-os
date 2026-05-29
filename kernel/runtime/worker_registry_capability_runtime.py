"""Worker registry capability runtime V1.

This module closes the worker registry runtime boundary over the existing
digest-only admission, approval, durable queue, watchdog, artifact, and real
WAL surfaces. It issues only single-use queue-job capabilities, starts no
worker loops, launches no processes, and exposes no provider, browser, or
network surface.
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

from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    ApprovalRuntimeConsumptionReceipt,
    ApprovalRuntimeIntegrationError,
    FileBackedApprovalRuntimeIntegration,
)
from kernel.runtime.durable_job_queue import (
    DurableJobQueue,
    DurableJobQueueError,
    DurableJobQueueTransitionError,
)
from kernel.runtime.watchdog_receipts_contract import (
    WatchdogPolicyReceipt,
    build_watchdog_policy_receipt,
)
from kernel.runtime.worker_registry_admission_contract import (
    WorkerAdmissionDeclaration,
    WorkerAdmissionReceipt,
    WorkerAdmissionRequest,
    WorkerRegistryAdmissionManifest,
    admit_worker_request,
    build_worker_admission_declaration,
    build_worker_admission_request,
    build_worker_registry_admission_manifest,
)
from kernel.stores.artifact_store_persistence import (
    ArtifactStorePersistenceError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageError,
)

__all__ = [
    "WORKER_CAPABILITY_SCOPE",
    "WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION",
    "ZERO_HASH",
    "FileBackedWorkerRegistryCapabilityRuntime",
    "WorkerCapabilityToken",
    "WorkerRegistryCapabilityRuntimeReceipt",
    "WorkerRegistryCapabilityRuntimeError",
    "compute_worker_capability_hash",
    "compute_worker_registry_capability_runtime_receipt_hash",
]

WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION = "worker_registry_capability_runtime_v1"
WORKER_CAPABILITY_SCOPE = "authorized_queue_job_processing"
ZERO_HASH = "sha256:" + ("0" * 64)

_RUNTIME_ROOT_RELPATH = "worker-registry-runtime"
_RUNTIME_WAL_RELPATH = _RUNTIME_ROOT_RELPATH + "/worker-registry.real-wal.jsonl"
_STATE_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/state"
_ARTIFACT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/artifacts"
_ARTIFACT_STORE_ID = "worker-registry-capability-artifacts-v1"
_RECEIPT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/receipts"

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)

_ALLOWED_AUTHORIZE_FIELDS = frozenset(
    {
        "approval_admission_hash",
        "artifact_manifest_hash",
        "browser_enabled",
        "capability_hashes",
        "dcc_enabled",
        "evidence_requirement_hashes",
        "expires_at",
        "human_approval_required",
        "idempotency_key_hash",
        "input_contract_hash",
        "issue_nonce",
        "job_id",
        "live_execution_enabled",
        "max_memory_mb",
        "max_runtime_ms",
        "mcp_enabled",
        "network_enabled",
        "output_contract_hash",
        "policy_hash",
        "provider_calls_enabled",
        "registry_policy_hash",
        "requested_task_class",
        "run_id",
        "stderr_limit_bytes",
        "stdout_limit_bytes",
        "task_classes",
        "task_descriptor_hash",
        "task_id",
        "worker_id",
        "worker_kind",
    }
)
_FORBIDDEN_AUTHORIZE_FIELDS = frozenset(
    {
        "args",
        "argv",
        "body",
        "command",
        "command_id",
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
        "path",
        "payload",
        "prompt",
        "raw_output",
        "raw_stderr",
        "raw_stdout",
        "retry",
        "shell",
        "stderr",
        "stdout",
        "steps",
        "subprocess",
        "timeout",
        "url",
        "workdir",
    }
)
_RECEIPT_EVENT_TYPES = frozenset(
    {
        "authorization_issued",
        "authorization_rejected",
        "capability_consumed",
        "capability_consume_rejected",
        "capability_revoked",
        "capability_revoke_rejected",
        "worker_quarantined",
    }
)
_SURFACE_FLAGS = (
    "live_execution_enabled",
    "provider_calls_enabled",
    "network_enabled",
    "browser_enabled",
    "dcc_enabled",
    "mcp_enabled",
)


class WorkerRegistryCapabilityRuntimeError(ValueError):
    """Raised when the worker capability runtime fails closed."""


@dataclass(frozen=True)
class WorkerCapabilityToken:
    """Single-use authority descriptor bound to one queued worker job."""

    capability_token_id: str
    worker_id: str
    task_id: str
    run_id: str
    job_id: str
    requested_task_class: str
    queue_job_hash: str
    worker_admission_receipt_hash: str
    approval_consumption_receipt_hash: str
    watchdog_policy_hash: str
    scope: str
    issued_at: str
    expires_at: str
    issue_nonce_hash: str
    single_use: bool = True
    capability_token_hash: str = ""

    def __post_init__(self) -> None:
        if self.scope != WORKER_CAPABILITY_SCOPE:
            raise WorkerRegistryCapabilityRuntimeError("capability_scope_invalid")
        for field_name in (
            "capability_token_id",
            "worker_id",
            "task_id",
            "run_id",
            "job_id",
            "requested_task_class",
            "scope",
            "issued_at",
            "expires_at",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "queue_job_hash",
            "worker_admission_receipt_hash",
            "approval_consumption_receipt_hash",
            "watchdog_policy_hash",
            "issue_nonce_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if self.single_use is not True:
            raise WorkerRegistryCapabilityRuntimeError("capability_must_be_single_use")
        if _parse_timestamp(self.expires_at) <= _parse_timestamp(self.issued_at):
            raise WorkerRegistryCapabilityRuntimeError("capability_expires_at_must_follow_issued_at")
        _install_or_verify_hash(
            self,
            "capability_token_hash",
            compute_worker_capability_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_consumption_receipt_hash": self.approval_consumption_receipt_hash,
            "expires_at": self.expires_at,
            "issue_nonce_hash": self.issue_nonce_hash,
            "issued_at": self.issued_at,
            "job_id": self.job_id,
            "queue_job_hash": self.queue_job_hash,
            "requested_task_class": self.requested_task_class,
            "run_id": self.run_id,
            "scope": self.scope,
            "single_use": self.single_use,
            "task_id": self.task_id,
            "watchdog_policy_hash": self.watchdog_policy_hash,
            "worker_admission_receipt_hash": self.worker_admission_receipt_hash,
            "worker_id": self.worker_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["capability_token_hash"] = self.capability_token_hash
        payload["capability_token_id"] = self.capability_token_id
        return payload


@dataclass(frozen=True)
class WorkerRegistryCapabilityRuntimeReceipt:
    """Deterministic receipt for worker admission/capability state changes."""

    integration_version: str
    event_type: str
    accepted: bool
    failures: tuple[str, ...]
    worker_id: str
    task_id: str
    run_id: str
    job_id: str
    queue_state: str
    worker_admission_receipt_hash: str
    registry_manifest_hash: str
    capability_token_id: str
    capability_token_hash: str
    capability_issue_receipt_hash: str
    capability_consume_receipt_hash: str
    capability_revoke_receipt_hash: str
    watchdog_policy_hash: str
    worker_state_wal_record_hash: str
    queue_record_hash: str
    approval_consumption_receipt_hash: str
    artifact_record_hash: str
    artifact_manifest_hash: str
    quarantine_state: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION:
            raise WorkerRegistryCapabilityRuntimeError("integration_version_invalid")
        if self.event_type not in _RECEIPT_EVENT_TYPES:
            raise WorkerRegistryCapabilityRuntimeError("receipt_event_type_invalid")
        if not isinstance(self.accepted, bool):
            raise WorkerRegistryCapabilityRuntimeError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise WorkerRegistryCapabilityRuntimeError("accepted_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise WorkerRegistryCapabilityRuntimeError("rejected_receipt_requires_failures")
        for field_name in (
            "worker_id",
            "task_id",
            "run_id",
            "job_id",
            "queue_state",
            "capability_token_id",
            "quarantine_state",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "worker_admission_receipt_hash",
            "registry_manifest_hash",
            "capability_token_hash",
            "capability_issue_receipt_hash",
            "capability_consume_receipt_hash",
            "capability_revoke_receipt_hash",
            "watchdog_policy_hash",
            "worker_state_wal_record_hash",
            "queue_record_hash",
            "approval_consumption_receipt_hash",
            "artifact_record_hash",
            "artifact_manifest_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_worker_registry_capability_runtime_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedWorkerRegistryCapabilityRuntime:
    """File-backed worker registry admission and capability coordinator."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        runtime_wal_relpath: str = _RUNTIME_WAL_RELPATH,
        state_store_relpath: str = _STATE_STORE_RELPATH,
        artifact_store_relpath: str = _ARTIFACT_STORE_RELPATH,
        artifact_store_id: str = _ARTIFACT_STORE_ID,
        receipt_store_relpath: str = _RECEIPT_STORE_RELPATH,
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.runtime_wal_relpath = _validate_relpath_text(
            runtime_wal_relpath,
            "runtime_wal_relpath",
            allow_empty=False,
        )
        self.state_store_relpath = _validate_relpath_text(
            state_store_relpath,
            "state_store_relpath",
            allow_empty=False,
        )
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=False,
        )
        self.artifact_store_id = _validated_identifier(
            artifact_store_id,
            "artifact_store_id",
        )
        self.receipt_store_relpath = _validate_relpath_text(
            receipt_store_relpath,
            "receipt_store_relpath",
            allow_empty=False,
        )

    def authorize_worker_for_queue_job(
        self,
        payload: Mapping[str, object],
        queue: DurableJobQueue,
        approval_runtime: FileBackedApprovalRuntimeIntegration | None = None,
        *,
        observed_at: str | None = None,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        observed = _timestamp(observed_at)
        data, failures = _admit_authorize_payload(payload)
        if not isinstance(queue, DurableJobQueue):
            failures = (*failures, "durable_queue_required")
        if failures:
            return self._rejected_receipt(
                data,
                failures,
                event_type="authorization_rejected",
                observed_at=observed,
            )

        queue_state = _safe_get_job_state(queue, str(data["job_id"]))
        if queue_state is None:
            return self._rejected_receipt(
                data,
                ("queue_job_missing",),
                event_type="authorization_rejected",
                observed_at=observed,
            )
        if queue_state.task_id != data["task_id"] or queue_state.run_id != data["run_id"]:
            return self._rejected_receipt(
                data,
                ("queue_job_identity_mismatch",),
                event_type="authorization_rejected",
                queue_state=queue_state.state,
                queue_record_hash=queue_state.last_event_hash,
                observed_at=observed,
            )
        if queue_state.state != "queued":
            return self._rejected_receipt(
                data,
                ("queue_job_not_queued",),
                event_type="authorization_rejected",
                queue_state=queue_state.state,
                queue_record_hash=queue_state.last_event_hash,
                observed_at=observed,
            )

        approval_consumption = self._consume_approval_if_required(
            data,
            approval_runtime,
            observed_at=observed,
        )
        if isinstance(approval_consumption, WorkerRegistryCapabilityRuntimeReceipt):
            return approval_consumption

        try:
            declaration = build_worker_admission_declaration(
                _declaration_payload(data),
                declared_at=observed,
            )
            request = build_worker_admission_request(
                _admission_request_payload(
                    data,
                    queue_job_hash=queue_state.last_event_hash,
                    wal_head_hash=self._last_runtime_wal_hash(),
                    approval_consumption=approval_consumption,
                ),
                requested_at=observed,
            )
            admission_wal_hash = self._append_worker_wal(
                event_name="worker_admission_requested",
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                material={
                    "admission_request_hash": request.request_hash,
                    "declaration_hash": declaration.declaration_hash,
                    "queue_job_hash": queue_state.last_event_hash,
                    "worker_id_hash": _sha256_text(str(data["worker_id"])),
                },
                digest_bindings={
                    "admission_request_hash": request.request_hash,
                    "declaration_hash": declaration.declaration_hash,
                    "queue_job_hash": queue_state.last_event_hash,
                    "worker_id_hash": _sha256_text(str(data["worker_id"])),
                },
                observed_at=observed,
            )
            admission = admit_worker_request(
                declaration,
                request,
                wal_record_hash=admission_wal_hash,
                admitted_at=observed,
            )
            if not admission.admitted:
                state_wal_hash = self._append_worker_wal(
                    event_name="worker_admission_rejected",
                    task_id=str(data["task_id"]),
                    run_id=str(data["run_id"]),
                    material={
                        "admission_receipt_hash": admission.receipt_hash,
                        "failure_hash": _sha256_json(admission.failure_reasons),
                    },
                    digest_bindings={
                        "admission_receipt_hash": admission.receipt_hash,
                        "failure_reason_hash": _sha256_json(admission.failure_reasons),
                    },
                    observed_at=observed,
                )
                return self._rejected_receipt(
                    data,
                    admission.failure_reasons,
                    event_type="authorization_rejected",
                    queue_state=queue_state.state,
                    worker_admission_receipt_hash=admission.receipt_hash,
                    worker_state_wal_record_hash=state_wal_hash,
                    queue_record_hash=queue_state.last_event_hash,
                    approval_consumption_receipt_hash=approval_consumption.receipt_hash,
                    observed_at=observed,
                )
            manifest = self._build_registry_manifest(
                data=data,
                declaration=declaration,
                wal_head_hash=admission_wal_hash,
                observed_at=observed,
            )
            watchdog = self._build_watchdog_policy(
                data=data,
                queue_job_hash=queue_state.last_event_hash,
                admission=admission,
                observed_at=observed,
            )
            capability = _build_worker_capability(
                data=data,
                queue_job_hash=queue_state.last_event_hash,
                admission=admission,
                approval_consumption=approval_consumption,
                watchdog=watchdog,
                issued_at=observed,
            )
            issue_wal_hash = self._append_worker_wal(
                event_name="worker_capability_issued",
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                material={
                    "admission_receipt_hash": admission.receipt_hash,
                    "capability_hash": capability.capability_token_hash,
                    "manifest_hash": manifest.manifest_hash,
                    "queue_job_hash": queue_state.last_event_hash,
                    "watchdog_policy_hash": watchdog.policy_hash,
                },
                digest_bindings={
                    "admission_receipt_hash": admission.receipt_hash,
                    "capability_hash": capability.capability_token_hash,
                    "manifest_hash": manifest.manifest_hash,
                    "queue_job_hash": queue_state.last_event_hash,
                    "watchdog_policy_hash": watchdog.policy_hash,
                },
                observed_at=observed,
            )
            artifact = self._write_worker_receipt_artifact(
                data=data,
                capability=capability,
                admission=admission,
                manifest=manifest,
                watchdog=watchdog,
                queue_record_hash=queue_state.last_event_hash,
                observed_at=observed,
            )
        except (
            ArtifactStorePersistenceError,
            RealWalStorageError,
            WorkerRegistryCapabilityRuntimeError,
            ValueError,
        ) as exc:
            return self._rejected_receipt(
                data,
                ("worker_authorization_failed:" + exc.__class__.__name__, str(exc)),
                event_type="authorization_rejected",
                queue_state=queue_state.state,
                queue_record_hash=queue_state.last_event_hash,
                approval_consumption_receipt_hash=approval_consumption.receipt_hash,
                observed_at=observed,
            )

        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="authorization_issued",
            accepted=True,
            failures=(),
            worker_id=str(data["worker_id"]),
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            queue_state=queue_state.state,
            worker_admission_receipt_hash=admission.receipt_hash,
            registry_manifest_hash=manifest.manifest_hash,
            capability_token_id=capability.capability_token_id,
            capability_token_hash=capability.capability_token_hash,
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=watchdog.policy_hash,
            worker_state_wal_record_hash=issue_wal_hash,
            queue_record_hash=queue_state.last_event_hash,
            approval_consumption_receipt_hash=approval_consumption.receipt_hash,
            artifact_record_hash=artifact.record_hash,
            artifact_manifest_hash=artifact.manifest.manifest_hash,
            quarantine_state="not_quarantined",
        )
        receipt = _replace_issue_receipt_hash(receipt)
        self._persist_capability(capability, receipt)
        self._persist_receipt(receipt)
        return receipt

    def consume_capability_for_queue_job(
        self,
        *,
        capability_token_id: str,
        queue: DurableJobQueue,
        worker_id: str,
        job_id: str,
        consume_nonce: str,
        now: str | None = None,
        observed_at: str | None = None,
        lease_timeout_seconds: int = 60,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        observed = _timestamp(observed_at)
        active_now = _timestamp(now)
        failures: list[str] = []
        if not isinstance(queue, DurableJobQueue):
            failures.append("durable_queue_required")
        if not _nonempty_string(capability_token_id):
            failures.append("capability_token_id_required")
        if not _nonempty_string(worker_id):
            failures.append("worker_id_required")
        if not _nonempty_string(job_id):
            failures.append("job_id_required")
        if not _nonempty_string(consume_nonce):
            failures.append("consume_nonce_required")
        if not isinstance(lease_timeout_seconds, int) or isinstance(lease_timeout_seconds, bool):
            failures.append("lease_timeout_seconds_must_be_int")
        elif lease_timeout_seconds <= 0:
            failures.append("lease_timeout_seconds_must_be_positive")

        capability = None
        if not failures:
            capability = self._read_capability(capability_token_id, failures)
        if capability is not None:
            self._append_capability_consume_failures(
                capability,
                queue,
                worker_id=worker_id,
                job_id=job_id,
                active_now=active_now,
                consume_nonce=consume_nonce,
                failures=failures,
            )

        if failures or capability is None:
            return self._consume_rejection_receipt(
                capability=capability,
                capability_token_id=capability_token_id,
                worker_id=worker_id,
                job_id=job_id,
                failures=failures or ["unknown_capability"],
                observed_at=observed,
            )

        try:
            leased = queue.lease_next(
                worker_id=worker_id,
                leased_at=observed,
                lease_timeout_seconds=lease_timeout_seconds,
            )
        except DurableJobQueueError as exc:
            return self._consume_rejection_receipt(
                capability=capability,
                capability_token_id=capability_token_id,
                worker_id=worker_id,
                job_id=job_id,
                failures=("queue_lease_failed:" + exc.__class__.__name__, str(exc)),
                observed_at=observed,
            )
        if leased.job_id != capability.job_id:
            return self._consume_rejection_receipt(
                capability=capability,
                capability_token_id=capability_token_id,
                worker_id=worker_id,
                job_id=job_id,
                failures=("queue_leased_unexpected_job",),
                queue_state=leased.state,
                queue_record_hash=leased.last_event_hash,
                observed_at=observed,
            )

        consume_nonce_hash = _sha256_text(consume_nonce)
        consume_wal_hash = self._append_worker_wal(
            event_name="worker_capability_consumed",
            task_id=capability.task_id,
            run_id=capability.run_id,
            material={
                "capability_hash": capability.capability_token_hash,
                "consume_nonce_hash": consume_nonce_hash,
                "leased_queue_record_hash": leased.last_event_hash,
                "queue_job_hash": capability.queue_job_hash,
                "worker_id_hash": _sha256_text(worker_id),
            },
            digest_bindings={
                "capability_hash": capability.capability_token_hash,
                "consume_nonce_hash": consume_nonce_hash,
                "leased_queue_record_hash": leased.last_event_hash,
                "queue_job_hash": capability.queue_job_hash,
                "worker_id_hash": _sha256_text(worker_id),
            },
            observed_at=observed,
        )
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="capability_consumed",
            accepted=True,
            failures=(),
            worker_id=worker_id,
            task_id=capability.task_id,
            run_id=capability.run_id,
            job_id=capability.job_id,
            queue_state=leased.state,
            worker_admission_receipt_hash=capability.worker_admission_receipt_hash,
            registry_manifest_hash=ZERO_HASH,
            capability_token_id=capability.capability_token_id,
            capability_token_hash=capability.capability_token_hash,
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=capability.watchdog_policy_hash,
            worker_state_wal_record_hash=consume_wal_hash,
            queue_record_hash=leased.last_event_hash,
            approval_consumption_receipt_hash=capability.approval_consumption_receipt_hash,
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="not_quarantined",
        )
        receipt = _replace_consume_receipt_hash(receipt)
        self._persist_consumption(capability, consume_nonce_hash, receipt)
        self._persist_receipt(receipt)
        return receipt

    def revoke_capability(
        self,
        *,
        capability_token_id: str,
        reason: str,
        revoked_at: str | None = None,
        observed_at: str | None = None,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        observed = _timestamp(observed_at)
        revoked = _timestamp(revoked_at)
        failures: list[str] = []
        if not _nonempty_string(capability_token_id):
            failures.append("capability_token_id_required")
        if not _nonempty_string(reason):
            failures.append("revocation_reason_required")
        capability = None
        if not failures:
            capability = self._read_capability(capability_token_id, failures)
        if capability is not None and self._path_exists(self._revocation_relpath(capability)):
            failures.append("capability_already_revoked")
        if failures or capability is None:
            return self._revoke_rejection_receipt(
                capability=capability,
                capability_token_id=capability_token_id,
                failures=failures or ["unknown_capability"],
                observed_at=observed,
            )

        reason_hash = _sha256_text(reason)
        revoke_wal_hash = self._append_worker_wal(
            event_name="worker_capability_revoked",
            task_id=capability.task_id,
            run_id=capability.run_id,
            material={
                "capability_hash": capability.capability_token_hash,
                "reason_hash": reason_hash,
                "revoked_at": revoked,
            },
            digest_bindings={
                "capability_hash": capability.capability_token_hash,
                "reason_hash": reason_hash,
            },
            observed_at=observed,
        )
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="capability_revoked",
            accepted=True,
            failures=(),
            worker_id=capability.worker_id,
            task_id=capability.task_id,
            run_id=capability.run_id,
            job_id=capability.job_id,
            queue_state="not_leased",
            worker_admission_receipt_hash=capability.worker_admission_receipt_hash,
            registry_manifest_hash=ZERO_HASH,
            capability_token_id=capability.capability_token_id,
            capability_token_hash=capability.capability_token_hash,
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=capability.watchdog_policy_hash,
            worker_state_wal_record_hash=revoke_wal_hash,
            queue_record_hash=capability.queue_job_hash,
            approval_consumption_receipt_hash=capability.approval_consumption_receipt_hash,
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="not_quarantined",
        )
        receipt = _replace_revoke_receipt_hash(receipt)
        self._persist_revocation(capability, reason_hash, receipt, revoked_at=revoked)
        self._persist_receipt(receipt)
        return receipt

    def quarantine_worker(
        self,
        *,
        worker_id: str,
        reason: str,
        failure_bundle_hash: str,
        task_id: str,
        run_id: str,
        job_id: str,
        observed_at: str | None = None,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        observed = _timestamp(observed_at)
        for field_name, value in (
            ("worker_id", worker_id),
            ("reason", reason),
            ("task_id", task_id),
            ("run_id", run_id),
            ("job_id", job_id),
        ):
            _require_nonempty_string(value, field_name)
        _require_sha256(failure_bundle_hash, "failure_bundle_hash")
        reason_hash = _sha256_text(reason)
        quarantine_wal_hash = self._append_worker_wal(
            event_name="worker_quarantined",
            task_id=task_id,
            run_id=run_id,
            material={
                "failure_bundle_hash": failure_bundle_hash,
                "job_id_hash": _sha256_text(job_id),
                "reason_hash": reason_hash,
                "worker_id_hash": _sha256_text(worker_id),
            },
            digest_bindings={
                "failure_bundle_hash": failure_bundle_hash,
                "job_id_hash": _sha256_text(job_id),
                "reason_hash": reason_hash,
                "worker_id_hash": _sha256_text(worker_id),
            },
            observed_at=observed,
        )
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="worker_quarantined",
            accepted=True,
            failures=(),
            worker_id=worker_id,
            task_id=task_id,
            run_id=run_id,
            job_id=job_id,
            queue_state="not_leased",
            worker_admission_receipt_hash=ZERO_HASH,
            registry_manifest_hash=ZERO_HASH,
            capability_token_id="not-issued",
            capability_token_hash=ZERO_HASH,
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=ZERO_HASH,
            worker_state_wal_record_hash=quarantine_wal_hash,
            queue_record_hash=ZERO_HASH,
            approval_consumption_receipt_hash=ZERO_HASH,
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="quarantined",
        )
        self._persist_quarantine(worker_id, reason_hash, failure_bundle_hash, receipt)
        self._persist_receipt(receipt)
        return receipt

    def _consume_approval_if_required(
        self,
        data: Mapping[str, object],
        approval_runtime: FileBackedApprovalRuntimeIntegration | None,
        *,
        observed_at: str,
    ) -> ApprovalRuntimeConsumptionReceipt | WorkerRegistryCapabilityRuntimeReceipt:
        if data["human_approval_required"] is not True:
            return ApprovalRuntimeConsumptionReceipt(
                integration_version="approval_runtime_integration_v1",
                accepted=True,
                failures=(),
                approval_id="approval-not-required",
                approval_admission_hash=ZERO_HASH,
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                preflight_id="worker-admission-" + str(data["job_id"]),
                approval_scope=APPROVAL_RUNTIME_EXECUTION_SCOPE,
                consumption_wal_record_hash=ZERO_HASH,
                consumed_at=observed_at,
            )
        if not isinstance(approval_runtime, FileBackedApprovalRuntimeIntegration):
            return self._rejected_receipt(
                data,
                ("approval_runtime_required",),
                event_type="authorization_rejected",
                observed_at=observed_at,
            )
        try:
            receipt = approval_runtime.consume_for_preflight(
                approval_admission_hash=str(data["approval_admission_hash"]),
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                preflight_id="worker-admission-" + str(data["job_id"]),
                approval_scope=APPROVAL_RUNTIME_EXECUTION_SCOPE,
                consumed_at=observed_at,
            )
        except (ApprovalRuntimeIntegrationError, ValueError) as exc:
            return self._rejected_receipt(
                data,
                ("approval_consumption_failed:" + exc.__class__.__name__, str(exc)),
                event_type="authorization_rejected",
                observed_at=observed_at,
            )
        if not receipt.accepted:
            return self._rejected_receipt(
                data,
                receipt.failures,
                event_type="authorization_rejected",
                approval_consumption_receipt_hash=receipt.receipt_hash,
                observed_at=observed_at,
            )
        return receipt

    def _build_registry_manifest(
        self,
        *,
        data: Mapping[str, object],
        declaration: WorkerAdmissionDeclaration,
        wal_head_hash: str,
        observed_at: str,
    ) -> WorkerRegistryAdmissionManifest:
        return build_worker_registry_admission_manifest(
            manifest_id="worker-registry-" + str(data["job_id"]),
            registry_policy_hash=str(data["registry_policy_hash"]),
            wal_head_hash=wal_head_hash,
            declarations=(declaration,),
            created_at=observed_at,
        )

    def _build_watchdog_policy(
        self,
        *,
        data: Mapping[str, object],
        queue_job_hash: str,
        admission: WorkerAdmissionReceipt,
        observed_at: str,
    ) -> WatchdogPolicyReceipt:
        return build_watchdog_policy_receipt(
            {
                "watchdog_policy_id": "watchdog-worker-" + str(data["job_id"]),
                "task_id": data["task_id"],
                "run_id": data["run_id"],
                "queue_job_hash": queue_job_hash,
                "worker_admission_receipt_hash": admission.receipt_hash,
                "max_runtime_ms": data["max_runtime_ms"],
                "max_memory_mb": data["max_memory_mb"],
                "stdout_limit_bytes": data["stdout_limit_bytes"],
                "stderr_limit_bytes": data["stderr_limit_bytes"],
                "kill_allowed": False,
                "retry_allowed": False,
            },
            created_at=observed_at,
        )

    def _append_capability_consume_failures(
        self,
        capability: WorkerCapabilityToken,
        queue: DurableJobQueue,
        *,
        worker_id: str,
        job_id: str,
        active_now: str,
        consume_nonce: str,
        failures: list[str],
    ) -> None:
        if capability.worker_id != worker_id:
            failures.append("worker_id_mismatch")
        if capability.job_id != job_id:
            failures.append("job_id_mismatch")
        if capability.scope != WORKER_CAPABILITY_SCOPE:
            failures.append("capability_scope_mismatch")
        if _parse_timestamp(capability.expires_at) <= _parse_timestamp(active_now):
            failures.append("capability_expired")
        if self._path_exists(self._revocation_relpath(capability)):
            failures.append("capability_revoked")
        if self._path_exists(self._consumption_relpath(capability)):
            failures.append("capability_already_consumed")
        if self._consume_nonce_seen(_sha256_text(consume_nonce)):
            failures.append("consume_nonce_reused")
        if self._worker_quarantined(capability.worker_id):
            failures.append("worker_quarantined")
        queue_state = _safe_get_job_state(queue, capability.job_id)
        if queue_state is None:
            failures.append("queue_job_missing")
            return
        if queue_state.state != "queued":
            failures.append("queue_job_not_queued")
        if queue_state.last_event_hash != capability.queue_job_hash:
            failures.append("queue_job_hash_mismatch")
        selected = _next_queued_job_state(queue)
        if selected is None:
            failures.append("no_queued_jobs")
        elif selected.job_id != capability.job_id:
            failures.append("authorized_job_not_next_in_queue")

    def _consume_rejection_receipt(
        self,
        *,
        capability: WorkerCapabilityToken | None,
        capability_token_id: str,
        worker_id: str,
        job_id: str,
        failures: Sequence[str],
        queue_state: str = "not_leased",
        queue_record_hash: str = ZERO_HASH,
        observed_at: str,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        data = _data_from_capability_or_fallback(
            capability,
            capability_token_id=capability_token_id,
            worker_id=worker_id,
            job_id=job_id,
        )
        wal_hash = self._append_rejection_wal(
            event_name="worker_capability_consume_rejected",
            data=data,
            capability=capability,
            failures=failures,
            observed_at=observed_at,
        )
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="capability_consume_rejected",
            accepted=False,
            failures=tuple(_normalize_failure_texts(failures)),
            worker_id=str(data["worker_id"]),
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            queue_state=queue_state,
            worker_admission_receipt_hash=str(data["worker_admission_receipt_hash"]),
            registry_manifest_hash=ZERO_HASH,
            capability_token_id=capability_token_id or "not-issued",
            capability_token_hash=str(data["capability_token_hash"]),
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=str(data["watchdog_policy_hash"]),
            worker_state_wal_record_hash=wal_hash,
            queue_record_hash=queue_record_hash,
            approval_consumption_receipt_hash=str(data["approval_consumption_receipt_hash"]),
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="quarantined"
            if "worker_quarantined" in failures
            else "not_quarantined",
        )
        self._persist_receipt(receipt)
        return receipt

    def _revoke_rejection_receipt(
        self,
        *,
        capability: WorkerCapabilityToken | None,
        capability_token_id: str,
        failures: Sequence[str],
        observed_at: str,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        data = _data_from_capability_or_fallback(
            capability,
            capability_token_id=capability_token_id,
            worker_id="unknown-worker",
            job_id="unknown-job",
        )
        wal_hash = self._append_rejection_wal(
            event_name="worker_capability_revoke_rejected",
            data=data,
            capability=capability,
            failures=failures,
            observed_at=observed_at,
        )
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type="capability_revoke_rejected",
            accepted=False,
            failures=tuple(_normalize_failure_texts(failures)),
            worker_id=str(data["worker_id"]),
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            queue_state="not_leased",
            worker_admission_receipt_hash=str(data["worker_admission_receipt_hash"]),
            registry_manifest_hash=ZERO_HASH,
            capability_token_id=capability_token_id or "not-issued",
            capability_token_hash=str(data["capability_token_hash"]),
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=str(data["watchdog_policy_hash"]),
            worker_state_wal_record_hash=wal_hash,
            queue_record_hash=ZERO_HASH,
            approval_consumption_receipt_hash=str(data["approval_consumption_receipt_hash"]),
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="not_quarantined",
        )
        self._persist_receipt(receipt)
        return receipt

    def _rejected_receipt(
        self,
        data: Mapping[str, object],
        failures: Sequence[str],
        *,
        event_type: str,
        queue_state: str = "not_queued",
        worker_admission_receipt_hash: str = ZERO_HASH,
        registry_manifest_hash: str = ZERO_HASH,
        capability_token_id: str = "not-issued",
        capability_token_hash: str = ZERO_HASH,
        watchdog_policy_hash: str = ZERO_HASH,
        worker_state_wal_record_hash: str = ZERO_HASH,
        queue_record_hash: str = ZERO_HASH,
        approval_consumption_receipt_hash: str = ZERO_HASH,
        observed_at: str,
    ) -> WorkerRegistryCapabilityRuntimeReceipt:
        receipt = WorkerRegistryCapabilityRuntimeReceipt(
            integration_version=WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
            event_type=event_type,
            accepted=False,
            failures=tuple(_normalize_failure_texts(failures)),
            worker_id=_safe_identity(data, "worker_id", "unknown-worker"),
            task_id=_safe_identity(data, "task_id", "unknown-task"),
            run_id=_safe_identity(data, "run_id", "unknown-run"),
            job_id=_safe_identity(data, "job_id", "unknown-job"),
            queue_state=queue_state,
            worker_admission_receipt_hash=worker_admission_receipt_hash,
            registry_manifest_hash=registry_manifest_hash,
            capability_token_id=capability_token_id,
            capability_token_hash=capability_token_hash,
            capability_issue_receipt_hash=ZERO_HASH,
            capability_consume_receipt_hash=ZERO_HASH,
            capability_revoke_receipt_hash=ZERO_HASH,
            watchdog_policy_hash=watchdog_policy_hash,
            worker_state_wal_record_hash=worker_state_wal_record_hash,
            queue_record_hash=queue_record_hash,
            approval_consumption_receipt_hash=approval_consumption_receipt_hash,
            artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            quarantine_state="not_quarantined",
        )
        if worker_state_wal_record_hash != ZERO_HASH or approval_consumption_receipt_hash != ZERO_HASH:
            self._persist_receipt(receipt)
        _ = observed_at
        return receipt

    def _append_rejection_wal(
        self,
        *,
        event_name: str,
        data: Mapping[str, object],
        capability: WorkerCapabilityToken | None,
        failures: Sequence[str],
        observed_at: str,
    ) -> str:
        capability_hash = ZERO_HASH if capability is None else capability.capability_token_hash
        try:
            return self._append_worker_wal(
                event_name=event_name,
                task_id=str(data["task_id"]),
                run_id=str(data["run_id"]),
                material={
                    "capability_hash": capability_hash,
                    "event_name": event_name,
                    "failure_hash": _sha256_json(tuple(_normalize_failure_texts(failures))),
                    "worker_id_hash": _sha256_text(str(data["worker_id"])),
                },
                digest_bindings={
                    "capability_hash": capability_hash,
                    "failure_reason_hash": _sha256_json(tuple(_normalize_failure_texts(failures))),
                    "worker_id_hash": _sha256_text(str(data["worker_id"])),
                },
                observed_at=observed_at,
            )
        except (RealWalStorageError, WorkerRegistryCapabilityRuntimeError):
            return ZERO_HASH

    def _append_worker_wal(
        self,
        *,
        event_name: str,
        task_id: str,
        run_id: str,
        material: Mapping[str, object],
        digest_bindings: Mapping[str, str],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        payload_hash = _sha256_json(
            {
                "event_name": event_name,
                "integration_version": WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
                "material": _json_ready(material),
            }
        )
        receipt = FileBackedRealWalStorage(wal_path).append(
            record_type="WORKER_REGISTRY_EVENT",
            task_id=task_id,
            run_id=run_id,
            payload_hash=payload_hash,
            digest_bindings=digest_bindings,
            created_at=observed_at,
        )
        return receipt.record_hash

    def _write_worker_receipt_artifact(
        self,
        *,
        data: Mapping[str, object],
        capability: WorkerCapabilityToken,
        admission: WorkerAdmissionReceipt,
        manifest: WorkerRegistryAdmissionManifest,
        watchdog: WatchdogPolicyReceipt,
        queue_record_hash: str,
        observed_at: str,
    ):
        material = {
            "admission_receipt_hash": admission.receipt_hash,
            "approval_consumption_receipt_hash": capability.approval_consumption_receipt_hash,
            "capability_hash": capability.capability_token_hash,
            "capability_id_hash": _sha256_text(capability.capability_token_id),
            "job_id_hash": _sha256_text(capability.job_id),
            "queue_job_hash": queue_record_hash,
            "registry_manifest_hash": manifest.manifest_hash,
            "requested_task_class_hash": _sha256_text(str(data["requested_task_class"])),
            "runtime_version_hash": _sha256_text(WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION),
            "watchdog_policy_hash": watchdog.policy_hash,
            "worker_id_hash": _sha256_text(capability.worker_id),
        }
        root = self._resolve_relpath(self.artifact_store_relpath, "artifact_store_relpath")
        return FileBackedArtifactStore(
            root,
            store_id=self.artifact_store_id,
        ).write_json_artifact(
            artifact_type="worker_receipt",
            task_id=capability.task_id,
            run_id=capability.run_id,
            payload=material,
            provenance_hash=_sha256_json(material),
            metadata={
                "capability_hash": capability.capability_token_hash,
                "runtime_version": WORKER_REGISTRY_CAPABILITY_RUNTIME_VERSION,
                "worker_id_hash": _sha256_text(capability.worker_id),
            },
            created_at=observed_at,
        )

    def _persist_capability(
        self,
        capability: WorkerCapabilityToken,
        receipt: WorkerRegistryCapabilityRuntimeReceipt,
    ) -> None:
        payload = {
            "capability": capability.as_dict(),
            "issue_receipt": receipt.as_dict(),
        }
        _write_json_no_overwrite(
            self._resolve_relpath(self._capability_relpath(capability), "capability_relpath"),
            payload,
        )
        _write_json_no_overwrite(
            self._resolve_relpath(self._capability_index_relpath(capability.capability_token_id), "capability_index_relpath"),
            {
                "capability_token_hash": capability.capability_token_hash,
                "capability_token_id_hash": _sha256_text(capability.capability_token_id),
            },
        )

    def _persist_consumption(
        self,
        capability: WorkerCapabilityToken,
        consume_nonce_hash: str,
        receipt: WorkerRegistryCapabilityRuntimeReceipt,
    ) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(self._consumption_relpath(capability), "capability_consumption_relpath"),
            {
                "capability_hash": capability.capability_token_hash,
                "consume_nonce_hash": consume_nonce_hash,
                "consume_receipt": receipt.as_dict(),
            },
        )

    def _persist_revocation(
        self,
        capability: WorkerCapabilityToken,
        reason_hash: str,
        receipt: WorkerRegistryCapabilityRuntimeReceipt,
        *,
        revoked_at: str,
    ) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(self._revocation_relpath(capability), "capability_revocation_relpath"),
            {
                "capability_hash": capability.capability_token_hash,
                "reason_hash": reason_hash,
                "revoked_at": revoked_at,
                "revoke_receipt": receipt.as_dict(),
            },
        )

    def _persist_quarantine(
        self,
        worker_id: str,
        reason_hash: str,
        failure_bundle_hash: str,
        receipt: WorkerRegistryCapabilityRuntimeReceipt,
    ) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(self._quarantine_relpath(worker_id, receipt.receipt_hash), "worker_quarantine_relpath"),
            {
                "failure_bundle_hash": failure_bundle_hash,
                "quarantine_receipt": receipt.as_dict(),
                "reason_hash": reason_hash,
                "worker_id_hash": _sha256_text(worker_id),
            },
        )

    def _persist_receipt(self, receipt: WorkerRegistryCapabilityRuntimeReceipt) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(self._receipt_relpath(receipt.receipt_hash), "receipt_relpath"),
            receipt.as_dict(),
        )

    def _read_capability(
        self,
        capability_token_id: str,
        failures: list[str],
    ) -> WorkerCapabilityToken | None:
        index_path = self._resolve_relpath(
            self._capability_index_relpath(capability_token_id),
            "capability_index_relpath",
        )
        if not index_path.exists():
            failures.append("unknown_capability")
            return None
        if index_path.is_symlink() or not index_path.is_file():
            failures.append("capability_index_invalid")
            return None
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(index, Mapping):
                raise WorkerRegistryCapabilityRuntimeError("capability_index_must_be_mapping")
            capability_hash = str(index["capability_token_hash"])
            _require_sha256(capability_hash, "capability_token_hash")
            path = self._resolve_relpath(
                self._capability_relpath_from_hash(capability_hash),
                "capability_relpath",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise WorkerRegistryCapabilityRuntimeError("capability_record_must_be_mapping")
            capability = WorkerCapabilityToken(**dict(payload["capability"]))  # type: ignore[arg-type]
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            failures.append("capability_record_invalid:" + str(exc))
            return None
        if capability.capability_token_id != capability_token_id:
            failures.append("capability_id_mismatch")
        return capability

    def _last_runtime_wal_hash(self) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        if not wal_path.exists():
            return ZERO_HASH
        try:
            records = FileBackedRealWalStorage(wal_path).read_records()
        except RealWalStorageError:
            return ZERO_HASH
        return ZERO_HASH if not records else records[-1].record_hash

    def _worker_quarantined(self, worker_id: str) -> bool:
        path = self._resolve_relpath(
            self._worker_quarantine_root_relpath(worker_id),
            "worker_quarantine_root_relpath",
        )
        if not path.exists():
            return False
        if path.is_symlink() or not path.is_dir():
            return True
        return any(item.is_file() for item in path.iterdir())

    def _consume_nonce_seen(self, consume_nonce_hash: str) -> bool:
        root = self._resolve_relpath(
            self.state_store_relpath + "/consumptions",
            "capability_consumption_root_relpath",
        )
        if not root.exists():
            return False
        for path in root.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return True
            if isinstance(payload, Mapping) and payload.get("consume_nonce_hash") == consume_nonce_hash:
                return True
        return False

    def _path_exists(self, relpath: str) -> bool:
        return self._resolve_relpath(relpath, "state_relpath").exists()

    def _capability_relpath(self, capability: WorkerCapabilityToken) -> str:
        return self._capability_relpath_from_hash(capability.capability_token_hash)

    def _capability_relpath_from_hash(self, capability_hash: str) -> str:
        return (
            self.state_store_relpath
            + "/capabilities/"
            + capability_hash.removeprefix("sha256:")
            + ".json"
        )

    def _capability_index_relpath(self, capability_token_id: str) -> str:
        return (
            self.state_store_relpath
            + "/capability-index/"
            + _sha256_text(capability_token_id).removeprefix("sha256:")
            + ".json"
        )

    def _consumption_relpath(self, capability: WorkerCapabilityToken) -> str:
        return (
            self.state_store_relpath
            + "/consumptions/"
            + capability.capability_token_hash.removeprefix("sha256:")
            + ".json"
        )

    def _revocation_relpath(self, capability: WorkerCapabilityToken) -> str:
        return (
            self.state_store_relpath
            + "/revocations/"
            + capability.capability_token_hash.removeprefix("sha256:")
            + ".json"
        )

    def _worker_quarantine_root_relpath(self, worker_id: str) -> str:
        return (
            self.state_store_relpath
            + "/quarantines/"
            + _sha256_text(worker_id).removeprefix("sha256:")
        )

    def _quarantine_relpath(self, worker_id: str, receipt_hash: str) -> str:
        return (
            self._worker_quarantine_root_relpath(worker_id)
            + "/"
            + receipt_hash.removeprefix("sha256:")
            + ".json"
        )

    def _receipt_relpath(self, receipt_hash: str) -> str:
        return (
            self.receipt_store_relpath
            + "/"
            + receipt_hash.removeprefix("sha256:")
            + ".json"
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        clean = _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / clean
        current = self.runtime_root
        for part in PurePosixPath(clean).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise WorkerRegistryCapabilityRuntimeError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise WorkerRegistryCapabilityRuntimeError(field_name + "_escapes_runtime_root")
        return resolved


def compute_worker_capability_hash(
    capability: WorkerCapabilityToken | Mapping[str, object],
) -> str:
    data = capability.as_dict() if isinstance(capability, WorkerCapabilityToken) else dict(capability)
    data.pop("capability_token_hash", None)
    data.pop("capability_token_id", None)
    return _sha256_json(data)


def compute_worker_registry_capability_runtime_receipt_hash(
    receipt: WorkerRegistryCapabilityRuntimeReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, WorkerRegistryCapabilityRuntimeReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _admit_authorize_payload(payload: Mapping[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    if not isinstance(payload, Mapping):
        return _fallback_data(), ("payload_must_be_mapping",)
    data = {**_fallback_data(), **dict(payload)}
    failures: list[str] = []
    forbidden = sorted(_FORBIDDEN_AUTHORIZE_FIELDS.intersection(data))
    if forbidden:
        failures.append("payload_field_forbidden:" + ",".join(forbidden))
    extra = sorted(set(data) - set(_fallback_data()) - _ALLOWED_AUTHORIZE_FIELDS)
    if extra:
        failures.append("payload_field_not_allowed:" + ",".join(extra))

    for field_name in (
        "artifact_manifest_hash",
        "idempotency_key_hash",
        "input_contract_hash",
        "output_contract_hash",
        "policy_hash",
        "registry_policy_hash",
        "task_descriptor_hash",
    ):
        _append_digest_failure(data.get(field_name), field_name, failures)
    for field_name in ("job_id", "requested_task_class", "run_id", "task_id", "worker_id", "worker_kind"):
        if not _nonempty_string(data.get(field_name)):
            failures.append(field_name + "_required")
    for field_name in ("expires_at", "issue_nonce"):
        if not _nonempty_string(data.get(field_name)):
            failures.append(field_name + "_required")

    task_classes = data.get("task_classes")
    if not isinstance(task_classes, (list, tuple)) or isinstance(task_classes, (str, bytes)):
        failures.append("task_classes_must_be_sequence")
    elif not task_classes or not all(_nonempty_string(item) for item in task_classes):
        failures.append("task_classes_must_be_nonempty_strings")
    else:
        data["task_classes"] = tuple(str(item) for item in task_classes)

    for field_name in ("capability_hashes", "evidence_requirement_hashes"):
        value = data.get(field_name)
        if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
            failures.append(field_name + "_must_be_sequence")
        elif not value:
            failures.append(field_name + "_must_be_nonempty")
        else:
            normalized = tuple(str(item) for item in value)
            if not all(_is_sha256(item) for item in normalized):
                failures.append(field_name + "_must_be_sha256_sequence")
            data[field_name] = normalized

    if data.get("human_approval_required") not in (True, False):
        failures.append("human_approval_required_must_be_bool")
    if data.get("human_approval_required") is True:
        _append_digest_failure(data.get("approval_admission_hash"), "approval_admission_hash", failures)
    else:
        data["approval_admission_hash"] = ZERO_HASH

    for field_name in _SURFACE_FLAGS:
        if data.get(field_name, False) is not False:
            failures.append(field_name + "_must_be_false")
        data[field_name] = False

    for field_name in ("max_runtime_ms", "max_memory_mb", "stdout_limit_bytes", "stderr_limit_bytes"):
        value = data.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(field_name + "_must_be_positive_int")

    if _nonempty_string(data.get("expires_at")):
        try:
            if _parse_timestamp(str(data["expires_at"])) <= _parse_timestamp(_timestamp(None)):
                pass
        except WorkerRegistryCapabilityRuntimeError as exc:
            failures.append("expires_at_invalid:" + str(exc))

    try:
        _scan_json_safety(data)
    except WorkerRegistryCapabilityRuntimeError as exc:
        failures.append(str(exc))
    return data, tuple(_dedupe(failures))


def _declaration_payload(data: Mapping[str, object]) -> dict[str, object]:
    return {
        "browser_enabled": False,
        "capability_hashes": data["capability_hashes"],
        "dcc_enabled": False,
        "evidence_requirement_hashes": data["evidence_requirement_hashes"],
        "human_approval_required": data["human_approval_required"],
        "input_contract_hash": data["input_contract_hash"],
        "live_execution_enabled": False,
        "mcp_enabled": False,
        "network_enabled": False,
        "output_contract_hash": data["output_contract_hash"],
        "policy_hash": data["policy_hash"],
        "provider_calls_enabled": False,
        "task_classes": data["task_classes"],
        "worker_id": data["worker_id"],
        "worker_kind": data["worker_kind"],
    }


def _admission_request_payload(
    data: Mapping[str, object],
    *,
    queue_job_hash: str,
    wal_head_hash: str,
    approval_consumption: ApprovalRuntimeConsumptionReceipt,
) -> dict[str, object]:
    return {
        "admission_request_id": "worker-admission-" + str(data["job_id"]),
        "approval_receipt_hash": (
            None
            if data["human_approval_required"] is not True
            else approval_consumption.receipt_hash
        ),
        "artifact_manifest_hash": data["artifact_manifest_hash"],
        "human_invoked": True,
        "idempotency_key_hash": data["idempotency_key_hash"],
        "queue_job_hash": queue_job_hash,
        "requested_task_class": data["requested_task_class"],
        "run_id": data["run_id"],
        "task_descriptor_hash": data["task_descriptor_hash"],
        "task_id": data["task_id"],
        "wal_head_hash": wal_head_hash,
        "worker_id": data["worker_id"],
    }


def _build_worker_capability(
    *,
    data: Mapping[str, object],
    queue_job_hash: str,
    admission: WorkerAdmissionReceipt,
    approval_consumption: ApprovalRuntimeConsumptionReceipt,
    watchdog: WatchdogPolicyReceipt,
    issued_at: str,
) -> WorkerCapabilityToken:
    issue_nonce_hash = _sha256_text(str(data["issue_nonce"]))
    material = {
        "approval_consumption_receipt_hash": approval_consumption.receipt_hash,
        "expires_at": data["expires_at"],
        "issue_nonce_hash": issue_nonce_hash,
        "issued_at": issued_at,
        "job_id": data["job_id"],
        "queue_job_hash": queue_job_hash,
        "requested_task_class": data["requested_task_class"],
        "run_id": data["run_id"],
        "scope": WORKER_CAPABILITY_SCOPE,
        "task_id": data["task_id"],
        "watchdog_policy_hash": watchdog.policy_hash,
        "worker_admission_receipt_hash": admission.receipt_hash,
        "worker_id": data["worker_id"],
    }
    capability_hash = _sha256_json({**material, "single_use": True})
    capability_id = "cap_worker_" + capability_hash.removeprefix("sha256:")[:32]
    return WorkerCapabilityToken(
        capability_token_id=capability_id,
        worker_id=str(data["worker_id"]),
        task_id=str(data["task_id"]),
        run_id=str(data["run_id"]),
        job_id=str(data["job_id"]),
        requested_task_class=str(data["requested_task_class"]),
        queue_job_hash=queue_job_hash,
        worker_admission_receipt_hash=admission.receipt_hash,
        approval_consumption_receipt_hash=approval_consumption.receipt_hash,
        watchdog_policy_hash=watchdog.policy_hash,
        scope=WORKER_CAPABILITY_SCOPE,
        issued_at=issued_at,
        expires_at=str(data["expires_at"]),
        issue_nonce_hash=issue_nonce_hash,
    )


def _safe_get_job_state(queue: DurableJobQueue, job_id: str):
    try:
        return queue.get_job_state(job_id)
    except DurableJobQueueError:
        return None


def _next_queued_job_state(queue: DurableJobQueue):
    try:
        states = [state for state in queue.list_job_states() if state.state == "queued"]
        if not states:
            return None
        priorities = _queue_priorities(queue)
        first_sequences = _queue_first_sequences(queue)
        return sorted(
            states,
            key=lambda state: (
                priorities.get(state.job_id, 100),
                first_sequences.get(state.job_id, 0),
                state.job_id,
            ),
        )[0]
    except DurableJobQueueError:
        return None


def _queue_priorities(queue: DurableJobQueue) -> dict[str, int]:
    priorities: dict[str, int] = {}
    for record in queue.records:
        if record.event.event_type == "JOB_SUBMITTED":
            value = record.payload.get("priority")
            if isinstance(value, int) and not isinstance(value, bool):
                priorities[record.event.job_id] = value
    return priorities


def _queue_first_sequences(queue: DurableJobQueue) -> dict[str, int]:
    sequences: dict[str, int] = {}
    for record in queue.records:
        sequences.setdefault(record.event.job_id, record.event.sequence)
    return sequences


def _replace_issue_receipt_hash(
    receipt: WorkerRegistryCapabilityRuntimeReceipt,
) -> WorkerRegistryCapabilityRuntimeReceipt:
    base = receipt.as_dict()
    base["capability_issue_receipt_hash"] = receipt.receipt_hash
    base.pop("receipt_hash", None)
    return WorkerRegistryCapabilityRuntimeReceipt(**base)  # type: ignore[arg-type]


def _replace_consume_receipt_hash(
    receipt: WorkerRegistryCapabilityRuntimeReceipt,
) -> WorkerRegistryCapabilityRuntimeReceipt:
    base = receipt.as_dict()
    base["capability_consume_receipt_hash"] = receipt.receipt_hash
    base.pop("receipt_hash", None)
    return WorkerRegistryCapabilityRuntimeReceipt(**base)  # type: ignore[arg-type]


def _replace_revoke_receipt_hash(
    receipt: WorkerRegistryCapabilityRuntimeReceipt,
) -> WorkerRegistryCapabilityRuntimeReceipt:
    base = receipt.as_dict()
    base["capability_revoke_receipt_hash"] = receipt.receipt_hash
    base.pop("receipt_hash", None)
    return WorkerRegistryCapabilityRuntimeReceipt(**base)  # type: ignore[arg-type]


def _data_from_capability_or_fallback(
    capability: WorkerCapabilityToken | None,
    *,
    capability_token_id: str,
    worker_id: str,
    job_id: str,
) -> dict[str, object]:
    if capability is None:
        return {
            "approval_consumption_receipt_hash": ZERO_HASH,
            "capability_token_hash": ZERO_HASH,
            "capability_token_id": capability_token_id or "not-issued",
            "job_id": job_id or "unknown-job",
            "run_id": "unknown-run",
            "task_id": "unknown-task",
            "watchdog_policy_hash": ZERO_HASH,
            "worker_admission_receipt_hash": ZERO_HASH,
            "worker_id": worker_id or "unknown-worker",
        }
    return {
        "approval_consumption_receipt_hash": capability.approval_consumption_receipt_hash,
        "capability_token_hash": capability.capability_token_hash,
        "capability_token_id": capability.capability_token_id,
        "job_id": capability.job_id,
        "run_id": capability.run_id,
        "task_id": capability.task_id,
        "watchdog_policy_hash": capability.watchdog_policy_hash,
        "worker_admission_receipt_hash": capability.worker_admission_receipt_hash,
        "worker_id": worker_id or capability.worker_id,
    }


def _fallback_data() -> dict[str, object]:
    return {
        "approval_admission_hash": ZERO_HASH,
        "artifact_manifest_hash": ZERO_HASH,
        "capability_hashes": (),
        "evidence_requirement_hashes": (),
        "expires_at": "1970-01-01T00:00:00+00:00",
        "human_approval_required": True,
        "idempotency_key_hash": ZERO_HASH,
        "input_contract_hash": ZERO_HASH,
        "issue_nonce": "unknown-issue",
        "job_id": "unknown-job",
        "max_memory_mb": 1,
        "max_runtime_ms": 1,
        "output_contract_hash": ZERO_HASH,
        "policy_hash": ZERO_HASH,
        "registry_policy_hash": ZERO_HASH,
        "requested_task_class": "unknown-task-class",
        "run_id": "unknown-run",
        "stderr_limit_bytes": 1,
        "stdout_limit_bytes": 1,
        "task_classes": (),
        "task_descriptor_hash": ZERO_HASH,
        "task_id": "unknown-task",
        "worker_id": "unknown-worker",
        "worker_kind": "unknown-worker-kind",
    }


def _safe_identity(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name)
    if isinstance(value, str) and value:
        return value
    return default


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise WorkerRegistryCapabilityRuntimeError("failures_must_be_sequence")
    failures = tuple(_normalize_failure_texts(value))
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _normalize_failure_texts(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        return (str(value),)
    return tuple(str(item) for item in value if str(item))


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        _require_sha256(current, field_name)
        if current != expected:
            raise WorkerRegistryCapabilityRuntimeError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise WorkerRegistryCapabilityRuntimeError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise WorkerRegistryCapabilityRuntimeError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise WorkerRegistryCapabilityRuntimeError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_required")
    if "\\" in value:
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _validated_identifier(value: object, field_name: str) -> str:
    _require_nonempty_string(value, field_name)
    text = str(value)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,95}", text):
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_invalid")
    return text


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_secret_like")


def _scan_json_safety(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_AUTHORIZE_FIELDS:
                raise WorkerRegistryCapabilityRuntimeError(
                    "unsafe_payload_field_forbidden:" + ".".join(path + (key_text,))
                )
            if _SECRET_KEY_PATTERN.search(key_text) and not key_text.endswith("_hash"):
                if key_text not in {"approval_admission_hash"}:
                    raise WorkerRegistryCapabilityRuntimeError(
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
                raise WorkerRegistryCapabilityRuntimeError(
                    "unsafe_payload_value_forbidden:" + ".".join(path)
                )
        return
    raise WorkerRegistryCapabilityRuntimeError(
        "unsafe_payload_value_type:" + ".".join(path)
    )


def _write_json_no_overwrite(path: Path, payload: Mapping[str, object]) -> None:
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    if path.exists():
        if path.is_symlink():
            raise WorkerRegistryCapabilityRuntimeError("state_target_is_symlink")
        if not path.is_file():
            raise WorkerRegistryCapabilityRuntimeError("state_target_not_file")
        if path.read_bytes() == data:
            return
        raise WorkerRegistryCapabilityRuntimeError("state_target_mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise WorkerRegistryCapabilityRuntimeError("state_parent_is_symlink")
    temp_path = path.with_name(
        "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
    )
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise WorkerRegistryCapabilityRuntimeError("state_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        if path.exists():
            raise WorkerRegistryCapabilityRuntimeError("state_target_exists")
        temp_path.rename(path)
        _fsync_parent(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _append_digest_failure(value: object, field_name: str, failures: list[str]) -> None:
    if not _is_sha256(value):
        failures.append(field_name + "_must_be_sha256")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not _nonempty_string(value):
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_required")


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _require_sha256(value: object, field_name: str) -> None:
    if not _is_sha256(value):
        raise WorkerRegistryCapabilityRuntimeError(field_name + "_must_be_sha256")


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    parsed = _parse_timestamp(value)
    return parsed.isoformat()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerRegistryCapabilityRuntimeError("timestamp_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


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
