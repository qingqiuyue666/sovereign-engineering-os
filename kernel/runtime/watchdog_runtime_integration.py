"""Watchdog runtime integration V1.

This module wires watchdog receipts to the durable queue, worker quarantine,
failure bundle, artifact, and real WAL surfaces. It exposes only explicit
heartbeat and human-invoked sweep calls; it does not start a background daemon,
launch work, kill processes, call providers, open browsers, or inspect
credential-bearing state.
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

from kernel.runtime.durable_job_queue import (
    DurableJobQueue,
    DurableJobQueueError,
    DurableJobQueueTransitionError,
)
from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
    FailureBundleCenterIntegratedReceipt,
    FailureBundleCenterIntegrationError,
)
from kernel.runtime.watchdog_receipts_contract import (
    WatchdogObservationReceipt,
    build_watchdog_observation_receipt,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
    WorkerRegistryCapabilityRuntimeReceipt,
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
    "WATCHDOG_RUNTIME_INTEGRATION_VERSION",
    "ZERO_HASH",
    "FileBackedWatchdogRuntimeIntegration",
    "WatchdogOperatorState",
    "WatchdogRuntimeIntegrationError",
    "WatchdogRuntimeReceipt",
    "compute_watchdog_operator_state_hash",
    "compute_watchdog_runtime_receipt_hash",
]

WATCHDOG_RUNTIME_INTEGRATION_VERSION = "watchdog_runtime_integration_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_RUNTIME_ROOT_RELPATH = "watchdog-runtime"
_RUNTIME_WAL_RELPATH = _RUNTIME_ROOT_RELPATH + "/watchdog.real-wal.jsonl"
_ARTIFACT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/artifacts"
_ARTIFACT_STORE_ID = "watchdog-runtime-artifacts-v1"
_RECEIPT_STORE_RELPATH = _RUNTIME_ROOT_RELPATH + "/receipts"
_OPERATOR_STATE_RELPATH = _RUNTIME_ROOT_RELPATH + "/operator-state"

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)
_FORBIDDEN_FIELD_MARKERS = (
    "api_key",
    "argv",
    "body",
    "command",
    "content",
    "credential",
    "cwd",
    "env",
    "executable",
    "output",
    "path",
    "payload",
    "prompt",
    "provider_response",
    "raw",
    "secret",
    "stderr",
    "stdout",
    "subprocess",
    "text",
    "token",
    "traceback",
    "url",
    "value",
)
_DIGEST_STREAM_KEYS = frozenset(
    {
        "stderr_digest",
        "stderr_truncated",
        "stdout_digest",
        "stdout_truncated",
    }
)
_EVENT_TYPES = frozenset(
    {
        "heartbeat_recorded",
        "manual_sweep_completed",
        "resource_breach_recorded",
        "watchdog_rejected",
    }
)


class WatchdogRuntimeIntegrationError(ValueError):
    """Raised when watchdog runtime integration fails closed."""


@dataclass(frozen=True)
class WatchdogOperatorState:
    integration_version: str
    task_id: str
    run_id: str
    job_id: str
    worker_id_hash: str
    queue_state: str
    latest_event_type: str
    latest_watchdog_receipt_hash: str
    latest_queue_record_hash: str
    latest_failure_bundle_hash: str
    stale_lease_detected: bool
    resource_breach_detected: bool
    quarantine_state: str
    background_daemon_enabled: bool
    operator_state_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != WATCHDOG_RUNTIME_INTEGRATION_VERSION:
            raise WatchdogRuntimeIntegrationError("operator_state_version_invalid")
        for field_name in ("task_id", "run_id", "job_id", "queue_state", "latest_event_type", "quarantine_state"):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "latest_failure_bundle_hash",
            "latest_queue_record_hash",
            "latest_watchdog_receipt_hash",
            "worker_id_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "background_daemon_enabled",
            "resource_breach_detected",
            "stale_lease_detected",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise WatchdogRuntimeIntegrationError(field_name + "_must_be_bool")
        if self.background_daemon_enabled is not False:
            raise WatchdogRuntimeIntegrationError("background_daemon_must_be_disabled")
        _install_or_verify_hash(self, "operator_state_hash", compute_watchdog_operator_state_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class WatchdogRuntimeReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    event_type: str
    task_id: str
    run_id: str
    job_id: str
    worker_id_hash: str
    lease_id_hash: str
    queue_state_before: str
    queue_state_after: str
    watchdog_policy_hash: str
    watchdog_observation_hash: str
    previous_watchdog_receipt_hash: str
    watchdog_wal_record_hash: str
    artifact_record_hash: str
    artifact_manifest_hash: str
    failure_bundle_id: str
    failure_bundle_hash: str
    failure_bundle_receipt_hash: str
    worker_quarantine_receipt_hash: str
    queue_record_hash: str
    stale_lease_detected: bool
    stale_lease_recovered: bool
    retry_scheduled: bool
    dead_lettered: bool
    resource_breach_detected: bool
    quarantine_required: bool
    human_invoked: bool
    background_daemon_enabled: bool
    operator_state_hash: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != WATCHDOG_RUNTIME_INTEGRATION_VERSION:
            raise WatchdogRuntimeIntegrationError("integration_version_invalid")
        if self.event_type not in _EVENT_TYPES:
            raise WatchdogRuntimeIntegrationError("watchdog_event_type_invalid")
        if not isinstance(self.accepted, bool):
            raise WatchdogRuntimeIntegrationError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise WatchdogRuntimeIntegrationError("accepted_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise WatchdogRuntimeIntegrationError("rejected_receipt_requires_failures")
        for field_name in (
            "task_id",
            "run_id",
            "job_id",
            "queue_state_before",
            "queue_state_after",
            "failure_bundle_id",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "artifact_manifest_hash",
            "artifact_record_hash",
            "failure_bundle_hash",
            "failure_bundle_receipt_hash",
            "lease_id_hash",
            "operator_state_hash",
            "previous_watchdog_receipt_hash",
            "queue_record_hash",
            "watchdog_observation_hash",
            "watchdog_policy_hash",
            "watchdog_wal_record_hash",
            "worker_id_hash",
            "worker_quarantine_receipt_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "background_daemon_enabled",
            "dead_lettered",
            "human_invoked",
            "quarantine_required",
            "resource_breach_detected",
            "retry_scheduled",
            "stale_lease_detected",
            "stale_lease_recovered",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise WatchdogRuntimeIntegrationError(field_name + "_must_be_bool")
        if self.background_daemon_enabled is not False:
            raise WatchdogRuntimeIntegrationError("background_daemon_must_be_disabled")
        if self.accepted:
            for field_name in (
                "artifact_manifest_hash",
                "artifact_record_hash",
                "operator_state_hash",
                "queue_record_hash",
                "watchdog_observation_hash",
                "watchdog_wal_record_hash",
            ):
                if getattr(self, field_name) == ZERO_HASH:
                    raise WatchdogRuntimeIntegrationError(field_name + "_required_when_accepted")
        _install_or_verify_hash(self, "receipt_hash", compute_watchdog_runtime_receipt_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedWatchdogRuntimeIntegration:
    """Manual watchdog runtime integration over real queue and evidence stores."""

    background_daemon_enabled = False

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        runtime_wal_relpath: str = _RUNTIME_WAL_RELPATH,
        artifact_store_relpath: str = _ARTIFACT_STORE_RELPATH,
        artifact_store_id: str = _ARTIFACT_STORE_ID,
        receipt_store_relpath: str = _RECEIPT_STORE_RELPATH,
        operator_state_relpath: str = _OPERATOR_STATE_RELPATH,
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.runtime_wal_relpath = _validate_relpath_text(runtime_wal_relpath, "runtime_wal_relpath")
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
        )
        self.artifact_store_id = _validated_identifier(artifact_store_id, "artifact_store_id")
        self.receipt_store_relpath = _validate_relpath_text(
            receipt_store_relpath,
            "receipt_store_relpath",
        )
        self.operator_state_relpath = _validate_relpath_text(
            operator_state_relpath,
            "operator_state_relpath",
        )

    def record_heartbeat(
        self,
        payload: Mapping[str, object],
        queue: DurableJobQueue,
        *,
        observed_at: str | None = None,
    ) -> WatchdogRuntimeReceipt:
        observed = _timestamp(observed_at)
        data, failures = _admit_payload(payload, require_human=False)
        if not isinstance(queue, DurableJobQueue):
            failures = (*failures, "durable_queue_required")
        if failures:
            return _rejected_receipt(data, failures, event_type="watchdog_rejected")
        try:
            before = queue.get_job_state(str(data["job_id"]))
            if before.state != "leased":
                return _rejected_receipt(data, ("queue_job_not_leased",), event_type="watchdog_rejected")
            after = queue.heartbeat(
                job_id=str(data["job_id"]),
                lease_id=str(data["lease_id"]),
                heartbeat_at=observed,
                lease_timeout_seconds=int(data["lease_timeout_seconds"]),
            )
            return self._record_observation(
                data=data,
                event_type="heartbeat_recorded",
                observed_state="ok",
                queue_state_before=before.state,
                queue_state_after=after.state,
                queue_record_hash=after.last_event_hash,
                stale_lease_detected=False,
                stale_lease_recovered=False,
                retry_scheduled=False,
                dead_lettered=False,
                resource_breach_detected=False,
                failure_bundle=None,
                quarantine=None,
                observed_at=observed,
            )
        except (DurableJobQueueError, DurableJobQueueTransitionError, WatchdogRuntimeIntegrationError, ValueError) as exc:
            return _rejected_receipt(
                data,
                ("watchdog_heartbeat_failed:" + exc.__class__.__name__, str(exc)),
                event_type="watchdog_rejected",
            )

    def run_manual_sweep(
        self,
        payload: Mapping[str, object],
        queue: DurableJobQueue,
        failure_center: FileBackedFailureBundleCenterIntegration,
        worker_runtime: FileBackedWorkerRegistryCapabilityRuntime,
        *,
        observed_at: str | None = None,
    ) -> WatchdogRuntimeReceipt:
        observed = _timestamp(observed_at)
        data, failures = _admit_payload(payload, require_human=True)
        if not isinstance(queue, DurableJobQueue):
            failures = (*failures, "durable_queue_required")
        if not isinstance(failure_center, FileBackedFailureBundleCenterIntegration):
            failures = (*failures, "failure_center_required")
        if not isinstance(worker_runtime, FileBackedWorkerRegistryCapabilityRuntime):
            failures = (*failures, "worker_runtime_required")
        if failures:
            return _rejected_receipt(data, failures, event_type="watchdog_rejected")

        try:
            before = queue.get_job_state(str(data["job_id"]))
            if before.state != "leased":
                return _rejected_receipt(data, ("queue_job_not_leased",), event_type="watchdog_rejected")
            if before.lease_id != data["lease_id"]:
                return _rejected_receipt(data, ("lease_id_mismatch",), event_type="watchdog_rejected")
            latest_lease = _latest_lease_event(queue, str(data["job_id"]), str(data["lease_id"]))
            stale = _is_expired(latest_lease.lease_expires_at, observed)
            breach_state = _resource_breach_state(data)
            unsafe = stale or breach_state != "ok"
            failure_bundle: FailureBundleCenterIntegratedReceipt | None = None
            quarantine: WorkerRegistryCapabilityRuntimeReceipt | None = None
            queue_after = before
            if unsafe:
                failure_bundle = failure_center.record_critical_failure(
                    failure_kind="watchdog_resource_breach",
                    task_id=str(data["task_id"]),
                    job_id=str(data["job_id"]),
                    run_id=str(data["run_id"]),
                    context_hashes=_failure_context_hashes(data, queue_state=before),
                    recovery_plan_hash=str(data["recovery_plan_hash"]),
                    snapshot_reconstruction_hash=str(data["snapshot_reconstruction_hash"]),
                    stdout_digest=data.get("stdout_digest"),  # type: ignore[arg-type]
                    stderr_digest=data.get("stderr_digest"),  # type: ignore[arg-type]
                    stdout_truncated=bool(data["stdout_truncated"]),
                    stderr_truncated=bool(data["stderr_truncated"]),
                    evidence_hashes={
                        "queue_record_hash": before.last_event_hash,
                        "watchdog_policy_hash": str(data["watchdog_policy_hash"]),
                    },
                    original_failure=RuntimeError("watchdog_runtime_detected_unsafe_state"),
                    observed_at=observed,
                )
                if not failure_bundle.accepted:
                    return _rejected_receipt(
                        data,
                        ("failure_bundle_rejected", *failure_bundle.failures),
                        event_type="watchdog_rejected",
                    )
                if stale:
                    recovered = queue.recover_expired_leases(
                        now=observed,
                        retry_after=str(data["retry_after"]),
                    )
                    matching = [state for state in recovered if state.job_id == data["job_id"]]
                    if not matching:
                        return _rejected_receipt(
                            data,
                            ("stale_lease_not_recovered",),
                            event_type="watchdog_rejected",
                        )
                    queue_after = matching[0]
                else:
                    queue_after = queue.fail_job(
                        job_id=str(data["job_id"]),
                        lease_id=str(data["lease_id"]),
                        reason="watchdog_resource_breach",
                        failed_at=observed,
                        retry_after=str(data["retry_after"]),
                    )
                quarantine = worker_runtime.quarantine_worker(
                    worker_id=str(data["worker_id"]),
                    reason="watchdog_runtime_detected_unsafe_state",
                    failure_bundle_hash=failure_bundle.bundle_digest,
                    task_id=str(data["task_id"]),
                    run_id=str(data["run_id"]),
                    job_id=str(data["job_id"]),
                    observed_at=observed,
                )
            observed_state = "deadline_exceeded" if stale else breach_state
            return self._record_observation(
                data=data,
                event_type="resource_breach_recorded" if unsafe else "manual_sweep_completed",
                observed_state=observed_state,
                queue_state_before=before.state,
                queue_state_after=queue_after.state,
                queue_record_hash=queue_after.last_event_hash,
                stale_lease_detected=stale,
                stale_lease_recovered=stale and queue_after.state in {"queued", "dead_lettered", "failed"},
                retry_scheduled=queue_after.state == "queued" and unsafe,
                dead_lettered=queue_after.state == "dead_lettered",
                resource_breach_detected=breach_state != "ok",
                failure_bundle=failure_bundle,
                quarantine=quarantine,
                observed_at=observed,
            )
        except (
            ArtifactStorePersistenceError,
            DurableJobQueueError,
            DurableJobQueueTransitionError,
            FailureBundleCenterIntegrationError,
            RealWalStorageError,
            WatchdogRuntimeIntegrationError,
            ValueError,
        ) as exc:
            return _rejected_receipt(
                data,
                ("watchdog_sweep_failed:" + exc.__class__.__name__, str(exc)),
                event_type="watchdog_rejected",
            )

    def read_operator_watchdog_state(self, job_id: str) -> WatchdogOperatorState:
        _require_nonempty_string(job_id, "job_id")
        payload = _read_json_object(
            self._resolve_relpath(_operator_state_relpath(self.operator_state_relpath, job_id), "operator_state_relpath"),
            "watchdog_operator_state",
        )
        return WatchdogOperatorState(**payload)  # type: ignore[arg-type]

    def _record_observation(
        self,
        *,
        data: Mapping[str, object],
        event_type: str,
        observed_state: str,
        queue_state_before: str,
        queue_state_after: str,
        queue_record_hash: str,
        stale_lease_detected: bool,
        stale_lease_recovered: bool,
        retry_scheduled: bool,
        dead_lettered: bool,
        resource_breach_detected: bool,
        failure_bundle: FailureBundleCenterIntegratedReceipt | None,
        quarantine: WorkerRegistryCapabilityRuntimeReceipt | None,
        observed_at: str,
    ) -> WatchdogRuntimeReceipt:
        failure_bundle_hash = ZERO_HASH if failure_bundle is None else failure_bundle.bundle_digest
        failure_bundle_id = "not-recorded" if failure_bundle is None else failure_bundle.failure_bundle_id
        failure_bundle_receipt_hash = ZERO_HASH if failure_bundle is None else failure_bundle.receipt_hash
        quarantine_receipt_hash = ZERO_HASH if quarantine is None else quarantine.receipt_hash
        material = {
            "elapsed_ms": data["elapsed_ms"],
            "event_type": event_type,
            "failure_bundle_hash": failure_bundle_hash,
            "job_id_hash": _sha256_text(str(data["job_id"])),
            "queue_record_hash": queue_record_hash,
            "queue_state_after_hash": _sha256_text(queue_state_after),
            "resource_breach_detected": resource_breach_detected,
            "stale_lease_detected": stale_lease_detected,
            "watchdog_policy_hash": data["watchdog_policy_hash"],
            "worker_id_hash": _sha256_text(str(data["worker_id"])),
        }
        wal_hash = self._append_watchdog_wal(
            data=data,
            event_type=event_type,
            material=material,
            observed_at=observed_at,
        )
        artifact = self._write_watchdog_artifact(
            data=data,
            event_type=event_type,
            failure_bundle_hash=failure_bundle_hash,
            queue_record_hash=queue_record_hash,
            queue_state_after=queue_state_after,
            resource_breach_detected=resource_breach_detected,
            stale_lease_detected=stale_lease_detected,
            wal_hash=wal_hash,
            observed_at=observed_at,
        )
        observation = _build_observation(
            data=data,
            artifact_manifest_hash=artifact.manifest.manifest_hash,
            failure_bundle_hash=None if failure_bundle is None else failure_bundle.bundle_digest,
            observed_state=observed_state,
            wal_hash=wal_hash,
            observed_at=observed_at,
        )
        operator_state = WatchdogOperatorState(
            integration_version=WATCHDOG_RUNTIME_INTEGRATION_VERSION,
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            worker_id_hash=_sha256_text(str(data["worker_id"])),
            queue_state=queue_state_after,
            latest_event_type=event_type,
            latest_watchdog_receipt_hash=observation.receipt_hash,
            latest_queue_record_hash=queue_record_hash,
            latest_failure_bundle_hash=failure_bundle_hash,
            stale_lease_detected=stale_lease_detected,
            resource_breach_detected=resource_breach_detected,
            quarantine_state="quarantined" if quarantine is not None and quarantine.accepted else "not_quarantined",
            background_daemon_enabled=False,
        )
        receipt = WatchdogRuntimeReceipt(
            integration_version=WATCHDOG_RUNTIME_INTEGRATION_VERSION,
            accepted=True,
            failures=(),
            event_type=event_type,
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            worker_id_hash=_sha256_text(str(data["worker_id"])),
            lease_id_hash=_sha256_text(str(data["lease_id"])),
            queue_state_before=queue_state_before,
            queue_state_after=queue_state_after,
            watchdog_policy_hash=str(data["watchdog_policy_hash"]),
            watchdog_observation_hash=observation.receipt_hash,
            previous_watchdog_receipt_hash=str(data["previous_watchdog_receipt_hash"]),
            watchdog_wal_record_hash=wal_hash,
            artifact_record_hash=artifact.record_hash,
            artifact_manifest_hash=artifact.manifest.manifest_hash,
            failure_bundle_id=failure_bundle_id,
            failure_bundle_hash=failure_bundle_hash,
            failure_bundle_receipt_hash=failure_bundle_receipt_hash,
            worker_quarantine_receipt_hash=quarantine_receipt_hash,
            queue_record_hash=queue_record_hash,
            stale_lease_detected=stale_lease_detected,
            stale_lease_recovered=stale_lease_recovered,
            retry_scheduled=retry_scheduled,
            dead_lettered=dead_lettered,
            resource_breach_detected=resource_breach_detected,
            quarantine_required=quarantine is not None,
            human_invoked=bool(data["human_invoked"]),
            background_daemon_enabled=False,
            operator_state_hash=operator_state.operator_state_hash,
        )
        self._persist_observation(observation)
        self._persist_operator_state(operator_state)
        self._persist_receipt(receipt)
        return receipt

    def _append_watchdog_wal(
        self,
        *,
        data: Mapping[str, object],
        event_type: str,
        material: Mapping[str, object],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.runtime_wal_relpath, "runtime_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        receipt = FileBackedRealWalStorage(wal_path).append(
            record_type="WATCHDOG_EVENT",
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            payload_hash=_sha256_json(
                {
                    "event_type": event_type,
                    "integration_version": WATCHDOG_RUNTIME_INTEGRATION_VERSION,
                    "material": _json_ready(material),
                }
            ),
            digest_bindings={
                "event_hash": _sha256_text(event_type),
                "queue_record_hash": str(material["queue_record_hash"]),
                "watchdog_policy_hash": str(data["watchdog_policy_hash"]),
                "worker_id_hash": _sha256_text(str(data["worker_id"])),
            },
            created_at=observed_at,
        )
        return receipt.record_hash

    def _write_watchdog_artifact(
        self,
        *,
        data: Mapping[str, object],
        event_type: str,
        failure_bundle_hash: str,
        queue_record_hash: str,
        queue_state_after: str,
        resource_breach_detected: bool,
        stale_lease_detected: bool,
        wal_hash: str,
        observed_at: str,
    ):
        material = {
            "elapsed_ms": data["elapsed_ms"],
            "event_hash": _sha256_text(event_type),
            "failure_bundle_hash": failure_bundle_hash,
            "job_id_hash": _sha256_text(str(data["job_id"])),
            "lease_id_hash": _sha256_text(str(data["lease_id"])),
            "observed_memory_mb": data["observed_memory_mb"],
            "queue_record_hash": queue_record_hash,
            "queue_state_hash": _sha256_text(queue_state_after),
            "resource_breach_detected": resource_breach_detected,
            "runtime_version_hash": _sha256_text(WATCHDOG_RUNTIME_INTEGRATION_VERSION),
            "stale_lease_detected": stale_lease_detected,
            "watchdog_policy_hash": data["watchdog_policy_hash"],
            "watchdog_wal_hash": wal_hash,
            "worker_id_hash": _sha256_text(str(data["worker_id"])),
        }
        artifact_root = self._resolve_relpath(
            self.artifact_store_relpath,
            "artifact_store_relpath",
        )
        return FileBackedArtifactStore(
            artifact_root,
            store_id=self.artifact_store_id,
        ).write_json_artifact(
            artifact_type="audit_json",
            task_id=str(data["task_id"]),
            run_id=str(data["run_id"]),
            payload=material,
            provenance_hash=_sha256_json(material),
            metadata={
                "event_type_hash": _sha256_text(event_type),
                "runtime_version": WATCHDOG_RUNTIME_INTEGRATION_VERSION,
                "watchdog_policy_hash": str(data["watchdog_policy_hash"]),
            },
            created_at=observed_at,
        )

    def _persist_observation(self, observation: WatchdogObservationReceipt) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(
                self.receipt_store_relpath
                + "/observation-"
                + observation.receipt_hash.removeprefix("sha256:")
                + ".json",
                "watchdog_observation_relpath",
            ),
            observation.as_dict(),
        )

    def _persist_receipt(self, receipt: WatchdogRuntimeReceipt) -> None:
        _write_json_no_overwrite(
            self._resolve_relpath(
                self.receipt_store_relpath
                + "/runtime-"
                + receipt.receipt_hash.removeprefix("sha256:")
                + ".json",
                "watchdog_runtime_receipt_relpath",
            ),
            receipt.as_dict(),
        )

    def _persist_operator_state(self, state: WatchdogOperatorState) -> None:
        _write_json_replace(
            self._resolve_relpath(
                _operator_state_relpath(self.operator_state_relpath, state.job_id),
                "operator_state_relpath",
            ),
            state.as_dict(),
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        clean = _validate_relpath_text(relpath, field_name)
        candidate = self.runtime_root / clean
        current = self.runtime_root
        for part in PurePosixPath(clean).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise WatchdogRuntimeIntegrationError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise WatchdogRuntimeIntegrationError(field_name + "_escapes_runtime_root")
        return resolved


def compute_watchdog_operator_state_hash(
    state: WatchdogOperatorState | Mapping[str, object],
) -> str:
    data = state.as_dict() if isinstance(state, WatchdogOperatorState) else dict(state)
    data.pop("operator_state_hash", None)
    return _sha256_json(data)


def compute_watchdog_runtime_receipt_hash(
    receipt: WatchdogRuntimeReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, WatchdogRuntimeReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _admit_payload(
    payload: Mapping[str, object],
    *,
    require_human: bool,
) -> tuple[dict[str, object], tuple[str, ...]]:
    if not isinstance(payload, Mapping):
        return _fallback_data(), ("payload_must_be_mapping",)
    data = {**_fallback_data(), **dict(payload)}
    failures: list[str] = []
    extra = sorted(set(data) - set(_fallback_data()))
    if extra:
        failures.append("payload_field_not_allowed:" + ",".join(extra))
    try:
        _scan_safety(data)
    except WatchdogRuntimeIntegrationError as exc:
        failures.append(str(exc))
    for field_name in (
        "job_id",
        "lease_id",
        "run_id",
        "task_id",
        "worker_id",
    ):
        if not _nonempty_string(data.get(field_name)):
            failures.append(field_name + "_required")
    for field_name in (
        "previous_watchdog_receipt_hash",
        "recovery_plan_hash",
        "snapshot_reconstruction_hash",
        "watchdog_policy_hash",
    ):
        if not _is_sha256(data.get(field_name)):
            failures.append(field_name + "_must_be_sha256")
    try:
        _parse_timestamp(str(data.get("retry_after")))
    except WatchdogRuntimeIntegrationError:
        failures.append("retry_after_must_be_isoformat")
    for field_name in (
        "elapsed_ms",
        "lease_timeout_seconds",
        "max_memory_mb",
        "max_runtime_ms",
        "observed_memory_mb",
    ):
        value = data.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(field_name + "_must_be_nonnegative_int")
    for field_name in ("lease_timeout_seconds", "max_memory_mb", "max_runtime_ms"):
        value = data.get(field_name)
        if isinstance(value, int) and not isinstance(value, bool) and value <= 0:
            failures.append(field_name + "_must_be_positive_int")
    for field_name in ("stderr_digest", "stdout_digest"):
        value = data.get(field_name)
        if value is not None and not _is_sha256(value):
            failures.append(field_name + "_must_be_sha256_or_none")
    for field_name in ("stderr_truncated", "stdout_truncated", "human_invoked"):
        if not isinstance(data.get(field_name), bool):
            failures.append(field_name + "_must_be_bool")
    if require_human and data.get("human_invoked") is not True:
        failures.append("human_invoked_required_true")
    return data, tuple(_dedupe(failures))


def _fallback_data() -> dict[str, object]:
    return {
        "elapsed_ms": 0,
        "human_invoked": False,
        "job_id": "unknown-job",
        "lease_id": "unknown-lease",
        "lease_timeout_seconds": 60,
        "max_memory_mb": 1,
        "max_runtime_ms": 1,
        "observed_memory_mb": 0,
        "previous_watchdog_receipt_hash": ZERO_HASH,
        "recovery_plan_hash": ZERO_HASH,
        "retry_after": "1970-01-01T00:00:00+00:00",
        "run_id": "unknown-run",
        "snapshot_reconstruction_hash": ZERO_HASH,
        "stderr_digest": None,
        "stderr_truncated": False,
        "stdout_digest": None,
        "stdout_truncated": False,
        "task_id": "unknown-task",
        "watchdog_policy_hash": ZERO_HASH,
        "worker_id": "unknown-worker",
    }


def _build_observation(
    *,
    data: Mapping[str, object],
    artifact_manifest_hash: str,
    failure_bundle_hash: str | None,
    observed_state: str,
    wal_hash: str,
    observed_at: str,
) -> WatchdogObservationReceipt:
    return build_watchdog_observation_receipt(
        {
            "artifact_manifest_hash": artifact_manifest_hash,
            "elapsed_ms": data["elapsed_ms"],
            "failure_bundle_hash": failure_bundle_hash,
            "observed_memory_mb": data["observed_memory_mb"],
            "observed_state": observed_state,
            "previous_receipt_hash": data["previous_watchdog_receipt_hash"],
            "quarantine_required": failure_bundle_hash is not None,
            "run_id": data["run_id"],
            "sequence": 1 if data["previous_watchdog_receipt_hash"] == ZERO_HASH else 2,
            "stderr_digest": data.get("stderr_digest"),
            "stderr_truncated": data["stderr_truncated"],
            "stdout_digest": data.get("stdout_digest"),
            "stdout_truncated": data["stdout_truncated"],
            "task_id": data["task_id"],
            "wal_record_hash": wal_hash,
            "watchdog_observation_id": "watchdog-observation-" + _sha256_json(
                {
                    "job_id": data["job_id"],
                    "observed_at": observed_at,
                    "state": observed_state,
                }
            ).removeprefix("sha256:")[:24],
            "watchdog_policy_hash": data["watchdog_policy_hash"],
        },
        observed_at=observed_at,
    )


def _failure_context_hashes(
    data: Mapping[str, object],
    *,
    queue_state: object,
) -> dict[str, str]:
    return {
        "queue_transition_context_hash": getattr(queue_state, "last_event_hash"),
        "wal_pointer_hash": getattr(queue_state, "last_event_hash"),
        "watchdog_failure_context_hash": _sha256_json(
            {
                "elapsed_ms": data["elapsed_ms"],
                "job_id_hash": _sha256_text(str(data["job_id"])),
                "observed_memory_mb": data["observed_memory_mb"],
                "watchdog_policy_hash": data["watchdog_policy_hash"],
            }
        ),
        "worker_failure_context_hash": _sha256_text(str(data["worker_id"])),
    }


def _resource_breach_state(data: Mapping[str, object]) -> str:
    if int(data["observed_memory_mb"]) > int(data["max_memory_mb"]):
        return "memory_exceeded"
    if bool(data["stdout_truncated"]) or bool(data["stderr_truncated"]):
        return "stream_limit_exceeded"
    if int(data["elapsed_ms"]) > int(data["max_runtime_ms"]):
        return "deadline_exceeded"
    return "ok"


def _latest_lease_event(queue: DurableJobQueue, job_id: str, lease_id: str):
    matches = [
        event
        for event in queue.events
        if event.job_id == job_id
        and event.lease_id == lease_id
        and event.event_type in {"JOB_HEARTBEAT", "JOB_LEASED"}
    ]
    if not matches:
        raise WatchdogRuntimeIntegrationError("lease_event_missing")
    return matches[-1]


def _is_expired(expires_at: str, observed_at: str) -> bool:
    if not _nonempty_string(expires_at):
        raise WatchdogRuntimeIntegrationError("lease_expiry_missing")
    return _parse_timestamp(expires_at) <= _parse_timestamp(observed_at)


def _operator_state_relpath(root: str, job_id: str) -> str:
    return root + "/" + _sha256_text(job_id).removeprefix("sha256:") + ".json"


def _rejected_receipt(
    data: Mapping[str, object],
    failures: Sequence[str],
    *,
    event_type: str,
) -> WatchdogRuntimeReceipt:
    return WatchdogRuntimeReceipt(
        integration_version=WATCHDOG_RUNTIME_INTEGRATION_VERSION,
        accepted=False,
        failures=tuple(_normalize_failure_texts(failures)),
        event_type=event_type,
        task_id=_safe_identity(data, "task_id", "unknown-task"),
        run_id=_safe_identity(data, "run_id", "unknown-run"),
        job_id=_safe_identity(data, "job_id", "unknown-job"),
        worker_id_hash=_sha256_text(_safe_identity(data, "worker_id", "unknown-worker")),
        lease_id_hash=_sha256_text(_safe_identity(data, "lease_id", "unknown-lease")),
        queue_state_before="unknown",
        queue_state_after="unknown",
        watchdog_policy_hash=_safe_digest(data, "watchdog_policy_hash"),
        watchdog_observation_hash=ZERO_HASH,
        previous_watchdog_receipt_hash=_safe_digest(data, "previous_watchdog_receipt_hash"),
        watchdog_wal_record_hash=ZERO_HASH,
        artifact_record_hash=ZERO_HASH,
        artifact_manifest_hash=ZERO_HASH,
        failure_bundle_id="not-recorded",
        failure_bundle_hash=ZERO_HASH,
        failure_bundle_receipt_hash=ZERO_HASH,
        worker_quarantine_receipt_hash=ZERO_HASH,
        queue_record_hash=ZERO_HASH,
        stale_lease_detected=False,
        stale_lease_recovered=False,
        retry_scheduled=False,
        dead_lettered=False,
        resource_breach_detected=False,
        quarantine_required=False,
        human_invoked=bool(data.get("human_invoked") is True),
        background_daemon_enabled=False,
        operator_state_hash=ZERO_HASH,
    )


def _safe_identity(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name)
    if (
        isinstance(value, str)
        and value
        and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", value)
        and not _SECRET_KEY_PATTERN.search(value)
    ):
        return value
    return default


def _safe_digest(data: Mapping[str, object], field_name: str) -> str:
    value = data.get(field_name)
    return str(value) if _is_sha256(value) else ZERO_HASH


def _scan_safety(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered not in _DIGEST_STREAM_KEYS and any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise WatchdogRuntimeIntegrationError(
                    "unsafe_watchdog_field:" + ".".join(path + (key_text,))
                )
            _scan_safety(item, path=path + (key_text,))
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_safety(item, path=path + (str(index),))
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
            raise WatchdogRuntimeIntegrationError(
                "unsafe_watchdog_value_sensitive:" + ".".join(path)
            )
        return
    raise WatchdogRuntimeIntegrationError("unsafe_watchdog_value_type:" + ".".join(path))


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise WatchdogRuntimeIntegrationError("failures_must_be_sequence")
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
            raise WatchdogRuntimeIntegrationError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise WatchdogRuntimeIntegrationError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise WatchdogRuntimeIntegrationError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise WatchdogRuntimeIntegrationError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise WatchdogRuntimeIntegrationError(field_name + "_required")
    if "\\" in value:
        raise WatchdogRuntimeIntegrationError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise WatchdogRuntimeIntegrationError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _validated_identifier(value: object, field_name: str) -> str:
    _require_nonempty_string(value, field_name)
    text = str(value)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,95}", text):
        raise WatchdogRuntimeIntegrationError(field_name + "_invalid")
    return text


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise WatchdogRuntimeIntegrationError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise WatchdogRuntimeIntegrationError(field_name + "_secret_like")


def _write_json_no_overwrite(path: Path, payload: Mapping[str, object]) -> None:
    data = (_canonical_json(payload) + "\n").encode("utf-8")
    if path.exists():
        if path.is_symlink():
            raise WatchdogRuntimeIntegrationError("json_target_is_symlink")
        if not path.is_file():
            raise WatchdogRuntimeIntegrationError("json_target_not_file")
        if path.read_bytes() == data:
            return
        raise WatchdogRuntimeIntegrationError("json_target_mismatch")
    _write_bytes_replace(path, data, allow_replace=False)


def _write_json_replace(path: Path, payload: Mapping[str, object]) -> None:
    _write_bytes_replace(path, (_canonical_json(payload) + "\n").encode("utf-8"), allow_replace=True)


def _write_bytes_replace(path: Path, data: bytes, *, allow_replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise WatchdogRuntimeIntegrationError("json_parent_is_symlink")
    temp_path = path.with_name("." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16])
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            count = os.write(fd, data[written:])
            if count <= 0:
                raise WatchdogRuntimeIntegrationError("json_write_failed")
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        if path.exists() and not allow_replace:
            raise WatchdogRuntimeIntegrationError("json_target_exists")
        temp_path.replace(path)
        _fsync_parent(path)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _read_json_object(path: Path, label: str) -> dict[str, object]:
    if not path.exists():
        raise WatchdogRuntimeIntegrationError(label + "_missing")
    if path.is_symlink():
        raise WatchdogRuntimeIntegrationError(label + "_is_symlink")
    if not path.is_file():
        raise WatchdogRuntimeIntegrationError(label + "_not_file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WatchdogRuntimeIntegrationError(label + "_invalid_json") from exc
    if not isinstance(payload, Mapping):
        raise WatchdogRuntimeIntegrationError(label + "_must_be_mapping")
    return _json_ready(payload)  # type: ignore[return-value]


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not _nonempty_string(value):
        raise WatchdogRuntimeIntegrationError(field_name + "_required")


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _require_sha256(value: object, field_name: str) -> None:
    if not _is_sha256(value):
        raise WatchdogRuntimeIntegrationError(field_name + "_must_be_sha256")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


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
        raise WatchdogRuntimeIntegrationError("timestamp_must_be_isoformat") from exc
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
