"""Failure bundle center integration V1.

This module persists digest-only failure bundle evidence, binds it to the real
WAL backend, writes a local failure-bundle artifact, and produces the existing
failure bundle center contract manifest. It never stores raw stdout, stderr,
tracebacks, commands, environment data, provider payloads, or credentials.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from kernel.runtime.failure_bundle_center_contract import (
    FailureBundleCenterManifest,
    FailureBundleReference,
    build_failure_bundle_center_manifest,
    build_failure_bundle_reference,
    validate_failure_bundle_center_manifest,
    validate_failure_bundle_reference,
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
    "FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION",
    "FAILURE_BUNDLE_CRITICAL_KINDS",
    "ZERO_HASH",
    "FailureBundleCenterIntegratedReceipt",
    "FailureBundleCenterIntegrationError",
    "FileBackedFailureBundleCenterIntegration",
    "compute_failure_bundle_digest",
    "compute_failure_bundle_center_integrated_receipt_hash",
]

FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION = "failure_bundle_center_integration_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,95}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "args",
        "argv",
        "body",
        "command",
        "command_line",
        "content",
        "cwd",
        "env",
        "environment",
        "executable",
        "executable_path",
        "filesystem_path",
        "output",
        "path",
        "payload",
        "prompt",
        "raw_bytes",
        "raw_content",
        "raw_log",
        "raw_output",
        "raw_stderr",
        "raw_stdout",
        "stderr",
        "stdout",
        "subprocess",
        "text",
        "timeout",
        "traceback",
        "url",
        "value",
        "workdir",
    }
)
_FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "credential",
    "private_key",
    "provider_response",
    "raw",
    "secret",
)
_CONTEXT_FIELDS = (
    "task_context_hash",
    "job_context_hash",
    "run_context_hash",
    "wal_pointer_hash",
    "artifact_ids_hash",
    "replay_snapshot_context_hash",
    "approval_rejection_context_hash",
    "queue_transition_context_hash",
    "corruption_evidence_hash",
    "watchdog_failure_context_hash",
    "worker_failure_context_hash",
    "missing_record_context_hash",
    "hash_mismatch_context_hash",
)


class FailureBundleCenterIntegrationError(ValueError):
    """Raised when failure bundle center integration fails closed."""


@dataclass(frozen=True)
class _CriticalFailureSpec:
    failure_stage: str
    failure_code: str
    failure_class: str
    severity: str
    retry_decision: str
    quarantine_required: bool
    required_contexts: tuple[str, ...]


FAILURE_BUNDLE_CRITICAL_KINDS: dict[str, _CriticalFailureSpec] = {
    "wal_corruption": _CriticalFailureSpec(
        failure_stage="wal",
        failure_code="wal_corruption_detected",
        failure_class="corruption_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("wal_pointer_hash", "corruption_evidence_hash"),
    ),
    "artifact_corruption": _CriticalFailureSpec(
        failure_stage="artifact_store",
        failure_code="artifact_corruption_detected",
        failure_class="corruption_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("artifact_ids_hash", "corruption_evidence_hash"),
    ),
    "queue_invalid_transition": _CriticalFailureSpec(
        failure_stage="queue_transition",
        failure_code="queue_invalid_transition",
        failure_class="queue_failure",
        severity="policy_blocked",
        retry_decision="manual_review_required",
        quarantine_required=True,
        required_contexts=("queue_transition_context_hash", "wal_pointer_hash"),
    ),
    "approval_rejection": _CriticalFailureSpec(
        failure_stage="approval",
        failure_code="approval_rejected",
        failure_class="approval_failure",
        severity="operator_blocked",
        retry_decision="manual_review_required",
        quarantine_required=True,
        required_contexts=("approval_rejection_context_hash", "wal_pointer_hash"),
    ),
    "replay_reconstruction_failure": _CriticalFailureSpec(
        failure_stage="replay_reconstruction",
        failure_code="replay_reconstruction_failed",
        failure_class="replay_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("replay_snapshot_context_hash",),
    ),
    "missing_record": _CriticalFailureSpec(
        failure_stage="evidence_replay",
        failure_code="missing_record",
        failure_class="missing_evidence_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("missing_record_context_hash", "wal_pointer_hash"),
    ),
    "hash_mismatch": _CriticalFailureSpec(
        failure_stage="evidence_replay",
        failure_code="hash_mismatch",
        failure_class="corruption_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("hash_mismatch_context_hash", "corruption_evidence_hash"),
    ),
    "worker_timeout": _CriticalFailureSpec(
        failure_stage="worker",
        failure_code="worker_timeout",
        failure_class="worker_failure",
        severity="retryable",
        retry_decision="retry_after_backoff",
        quarantine_required=False,
        required_contexts=("worker_failure_context_hash", "watchdog_failure_context_hash"),
    ),
    "watchdog_resource_breach": _CriticalFailureSpec(
        failure_stage="watchdog",
        failure_code="watchdog_resource_breach",
        failure_class="watchdog_failure",
        severity="terminal",
        retry_decision="no_retry_terminal",
        quarantine_required=True,
        required_contexts=("watchdog_failure_context_hash", "worker_failure_context_hash"),
    ),
}


@dataclass(frozen=True)
class FailureBundleCenterIntegratedReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    failure_bundle_id: str
    task_id: str
    job_id: str
    run_id: str
    failure_kind: str
    failure_stage: str
    failure_code: str
    failure_class: str
    severity: str
    retry_decision: str
    quarantine_required: bool
    bundle_digest: str
    failure_wal_record_hash: str
    failure_artifact_record_hash: str
    artifact_manifest_hash: str
    snapshot_reconstruction_hash: str
    recovery_plan_hash: str
    failure_reference_hash: str
    center_manifest_hash: str
    original_failure_type: str
    minimal_receipt: bool
    persisted_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION:
            raise FailureBundleCenterIntegrationError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise FailureBundleCenterIntegrationError("accepted_must_be_bool")
        if not isinstance(self.quarantine_required, bool):
            raise FailureBundleCenterIntegrationError("quarantine_required_must_be_bool")
        if not isinstance(self.minimal_receipt, bool):
            raise FailureBundleCenterIntegrationError("minimal_receipt_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise FailureBundleCenterIntegrationError("accepted_receipt_has_failures")
        if not self.accepted and not self.failures:
            raise FailureBundleCenterIntegrationError("rejected_receipt_requires_failures")
        for field_name in (
            "failure_bundle_id",
            "task_id",
            "job_id",
            "run_id",
            "failure_kind",
            "failure_stage",
            "failure_code",
            "failure_class",
            "severity",
            "retry_decision",
            "original_failure_type",
            "persisted_at",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "artifact_manifest_hash",
            "bundle_digest",
            "center_manifest_hash",
            "failure_artifact_record_hash",
            "failure_reference_hash",
            "failure_wal_record_hash",
            "recovery_plan_hash",
            "snapshot_reconstruction_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        _parse_timestamp(self.persisted_at, "persisted_at")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_failure_bundle_center_integrated_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))


class FileBackedFailureBundleCenterIntegration:
    """File-backed failure bundle center bound to WAL and artifact evidence."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        failure_store_relpath: str = "failure-bundle-center",
        failure_wal_relpath: str = "failure-bundle-center/failure.real-wal.jsonl",
        artifact_store_relpath: str = "artifact-store",
        artifact_store_id: str = "failure-bundle-center-artifacts-v1",
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.failure_store_relpath = _validate_relpath_text(
            failure_store_relpath,
            "failure_store_relpath",
        )
        self.failure_wal_relpath = _validate_relpath_text(
            failure_wal_relpath,
            "failure_wal_relpath",
        )
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
        )
        _require_nonempty_string(artifact_store_id, "artifact_store_id")
        self.artifact_store_id = artifact_store_id

    def record_critical_failure(
        self,
        *,
        failure_kind: str,
        task_id: str,
        job_id: str,
        run_id: str,
        context_hashes: Mapping[str, str],
        recovery_plan_hash: str,
        snapshot_reconstruction_hash: str = ZERO_HASH,
        stdout_digest: str | None = None,
        stderr_digest: str | None = None,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
        evidence_hashes: Mapping[str, str] | None = None,
        original_failure: BaseException | None = None,
        observed_at: str | None = None,
    ) -> FailureBundleCenterIntegratedReceipt:
        spec = _failure_spec(failure_kind)
        observed = _timestamp(observed_at)
        for field_name, value in (
            ("task_id", task_id),
            ("job_id", job_id),
            ("run_id", run_id),
        ):
            _require_nonempty_string(value, field_name)
        _require_sha256(recovery_plan_hash, "recovery_plan_hash")
        _require_sha256(snapshot_reconstruction_hash, "snapshot_reconstruction_hash")
        stdout_digest = _optional_sha256(stdout_digest, "stdout_digest")
        stderr_digest = _optional_sha256(stderr_digest, "stderr_digest")
        if not isinstance(stdout_truncated, bool):
            raise FailureBundleCenterIntegrationError("stdout_truncated_must_be_bool")
        if not isinstance(stderr_truncated, bool):
            raise FailureBundleCenterIntegrationError("stderr_truncated_must_be_bool")
        context = _normalize_context_hashes(context_hashes)
        _require_spec_context(spec, context)
        extra_evidence = _normalize_evidence_hashes(evidence_hashes or {})
        original_failure_type = _sanitize_exception_type(original_failure)
        bundle_material = _bundle_material(
            context_hashes=context,
            evidence_hashes=extra_evidence,
            failure_kind=failure_kind,
            job_id=job_id,
            original_failure_type=original_failure_type,
            recovery_plan_hash=recovery_plan_hash,
            run_id=run_id,
            snapshot_reconstruction_hash=snapshot_reconstruction_hash,
            spec=spec,
            stderr_digest=stderr_digest,
            stderr_truncated=stderr_truncated,
            stdout_digest=stdout_digest,
            stdout_truncated=stdout_truncated,
            task_id=task_id,
        )
        failure_bundle_id = _failure_bundle_id(bundle_material)
        bundle_payload = {
            **bundle_material,
            "bundle_digest": compute_failure_bundle_digest(bundle_material),
            "failure_bundle_id": failure_bundle_id,
        }
        bundle_payload["bundle_digest"] = compute_failure_bundle_digest(bundle_payload)

        try:
            wal_record_hash = self._append_failure_wal(
                bundle_payload,
                context_hashes=context,
                evidence_hashes=extra_evidence,
                task_id=task_id,
                run_id=run_id,
                created_at=observed,
            )
            artifact_receipt = self._write_failure_artifact(
                bundle_payload,
                task_id=task_id,
                run_id=run_id,
                observed_at=observed,
            )
            reference = self._build_reference(
                artifact_manifest_hash=artifact_receipt.manifest.manifest_hash,
                bundle_payload=bundle_payload,
                recovery_plan_hash=recovery_plan_hash,
                snapshot_reconstruction_hash=snapshot_reconstruction_hash,
                stderr_digest=stderr_digest,
                stderr_truncated=stderr_truncated,
                stdout_digest=stdout_digest,
                stdout_truncated=stdout_truncated,
                wal_record_hash=wal_record_hash,
                observed_at=observed,
            )
            manifest = self._build_manifest(
                reference=reference,
                recovery_plan_hash=recovery_plan_hash,
                run_id=run_id,
                task_id=task_id,
                wal_head_hash=wal_record_hash,
                created_at=observed,
            )
            receipt = FailureBundleCenterIntegratedReceipt(
                integration_version=FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION,
                accepted=True,
                failures=(),
                failure_bundle_id=failure_bundle_id,
                task_id=task_id,
                job_id=job_id,
                run_id=run_id,
                failure_kind=failure_kind,
                failure_stage=spec.failure_stage,
                failure_code=spec.failure_code,
                failure_class=spec.failure_class,
                severity=spec.severity,
                retry_decision=spec.retry_decision,
                quarantine_required=spec.quarantine_required,
                bundle_digest=str(bundle_payload["bundle_digest"]),
                failure_wal_record_hash=wal_record_hash,
                failure_artifact_record_hash=artifact_receipt.record_hash,
                artifact_manifest_hash=artifact_receipt.manifest.manifest_hash,
                snapshot_reconstruction_hash=snapshot_reconstruction_hash,
                recovery_plan_hash=recovery_plan_hash,
                failure_reference_hash=reference.reference_hash,
                center_manifest_hash=manifest.manifest_hash,
                original_failure_type=original_failure_type,
                minimal_receipt=False,
                persisted_at=observed,
            )
            self._write_json_no_overwrite(
                self._bundle_relpath(failure_bundle_id),
                {
                    "bundle": bundle_payload,
                    "failure_reference": reference.as_dict(),
                    "integration_receipt": receipt.as_dict(),
                },
            )
            self._write_json_no_overwrite(
                self._manifest_relpath(manifest.manifest_hash),
                {
                    "failure_references": (reference.as_dict(),),
                    "manifest": manifest.as_dict(),
                },
            )
            self._write_json_no_overwrite(
                self._receipt_relpath(receipt.receipt_hash),
                receipt.as_dict(),
            )
            return receipt
        except (ArtifactStorePersistenceError, FailureBundleCenterIntegrationError, OSError, RealWalStorageError) as exc:
            return self._minimal_receipt(
                failure_kind=failure_kind,
                failure_bundle_id=failure_bundle_id,
                task_id=task_id,
                job_id=job_id,
                run_id=run_id,
                spec=spec,
                recovery_plan_hash=recovery_plan_hash,
                snapshot_reconstruction_hash=snapshot_reconstruction_hash,
                original_failure_type=original_failure_type,
                observed_at=observed,
                failure="failure_bundle_write_failed:" + exc.__class__.__name__,
            )

    def read_persisted_bundle(self, failure_bundle_id: str) -> dict[str, object]:
        _require_nonempty_string(failure_bundle_id, "failure_bundle_id")
        path = self._resolve_relpath(
            self._bundle_relpath(failure_bundle_id),
            "failure_bundle_relpath",
        )
        payload = _read_json_object(path, "failure_bundle")
        bundle = payload.get("bundle")
        if not isinstance(bundle, Mapping):
            raise FailureBundleCenterIntegrationError("failure_bundle_payload_missing")
        expected = compute_failure_bundle_digest(bundle)
        if bundle.get("bundle_digest") != expected:
            raise FailureBundleCenterIntegrationError("failure_bundle_digest_mismatch")
        reference_payload = payload.get("failure_reference")
        if not isinstance(reference_payload, Mapping):
            raise FailureBundleCenterIntegrationError("failure_reference_payload_missing")
        reference = FailureBundleReference(
            failure_bundle_id=str(reference_payload["failure_bundle_id"]),
            task_id=str(reference_payload["task_id"]),
            run_id=str(reference_payload["run_id"]),
            failure_stage=str(reference_payload["failure_stage"]),
            failure_code=str(reference_payload["failure_code"]),
            failure_class=str(reference_payload["failure_class"]),
            severity=str(reference_payload["severity"]),
            retry_decision=str(reference_payload["retry_decision"]),
            bundle_digest=str(reference_payload["bundle_digest"]),
            wal_record_hash=str(reference_payload["wal_record_hash"]),
            artifact_manifest_hash=str(reference_payload["artifact_manifest_hash"]),
            snapshot_reconstruction_hash=str(reference_payload["snapshot_reconstruction_hash"]),
            recovery_plan_hash=str(reference_payload["recovery_plan_hash"]),
            stdout_digest=reference_payload.get("stdout_digest"),  # type: ignore[arg-type]
            stderr_digest=reference_payload.get("stderr_digest"),  # type: ignore[arg-type]
            stdout_truncated=reference_payload["stdout_truncated"],  # type: ignore[arg-type]
            stderr_truncated=reference_payload["stderr_truncated"],  # type: ignore[arg-type]
            quarantine_required=reference_payload["quarantine_required"],  # type: ignore[arg-type]
            contract_version=str(reference_payload["contract_version"]),
            code_version=str(reference_payload["code_version"]),
            reference_hash=str(reference_payload["reference_hash"]),
            observed_at=str(reference_payload["observed_at"]),
        )
        if not validate_failure_bundle_reference(reference):
            raise FailureBundleCenterIntegrationError("failure_reference_invalid")
        return _json_ready(payload)

    def read_center_manifest(self, manifest_hash: str) -> FailureBundleCenterManifest:
        _require_sha256(manifest_hash, "manifest_hash")
        path = self._resolve_relpath(
            self._manifest_relpath(manifest_hash),
            "failure_manifest_relpath",
        )
        payload = _read_json_object(path, "failure_manifest")
        manifest_payload = payload.get("manifest")
        if not isinstance(manifest_payload, Mapping):
            raise FailureBundleCenterIntegrationError("failure_manifest_payload_missing")
        manifest = FailureBundleCenterManifest(
            manifest_id=str(manifest_payload["manifest_id"]),
            task_id=str(manifest_payload["task_id"]),
            run_id=str(manifest_payload["run_id"]),
            wal_head_hash=str(manifest_payload["wal_head_hash"]),
            recovery_plan_hash=str(manifest_payload["recovery_plan_hash"]),
            failure_reference_hashes=tuple(manifest_payload["failure_reference_hashes"]),  # type: ignore[arg-type]
            center_root_hash=str(manifest_payload["center_root_hash"]),
            quarantine_required=manifest_payload["quarantine_required"],  # type: ignore[arg-type]
            retryable_failure_count=manifest_payload["retryable_failure_count"],  # type: ignore[arg-type]
            terminal_failure_count=manifest_payload["terminal_failure_count"],  # type: ignore[arg-type]
            contract_version=str(manifest_payload["contract_version"]),
            code_version=str(manifest_payload["code_version"]),
            manifest_hash=str(manifest_payload["manifest_hash"]),
            created_at=str(manifest_payload["created_at"]),
        )
        if manifest.manifest_hash != manifest_hash:
            raise FailureBundleCenterIntegrationError("failure_manifest_hash_mismatch")
        if not validate_failure_bundle_center_manifest(manifest):
            raise FailureBundleCenterIntegrationError("failure_manifest_invalid")
        return manifest

    def _append_failure_wal(
        self,
        bundle_payload: Mapping[str, object],
        *,
        context_hashes: Mapping[str, str],
        evidence_hashes: Mapping[str, str],
        task_id: str,
        run_id: str,
        created_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(self.failure_wal_relpath, "failure_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        digest_bindings: dict[str, str] = {
            "bundle_digest": str(bundle_payload["bundle_digest"]),
            "recovery_plan": str(bundle_payload["recovery_plan_hash"]),
            "snapshot_reconstruction": str(bundle_payload["snapshot_reconstruction_hash"]),
        }
        for name, digest in context_hashes.items():
            digest_bindings[name.removesuffix("_hash")] = digest
        for name, digest in evidence_hashes.items():
            digest_bindings["evidence_" + name.removesuffix("_hash")] = digest
        receipt = FileBackedRealWalStorage(wal_path).append(
            record_type="FAILURE_BUNDLE_EVENT",
            task_id=task_id,
            run_id=run_id,
            payload_hash=str(bundle_payload["bundle_digest"]),
            digest_bindings=digest_bindings,
            created_at=created_at,
        )
        return receipt.record_hash

    def _write_failure_artifact(
        self,
        bundle_payload: Mapping[str, object],
        *,
        task_id: str,
        run_id: str,
        observed_at: str,
    ):
        artifact_root = self._resolve_relpath(
            self.artifact_store_relpath,
            "artifact_store_relpath",
        )
        return FileBackedArtifactStore(
            artifact_root,
            store_id=self.artifact_store_id,
        ).write_json_artifact(
            artifact_type="failure_bundle",
            task_id=task_id,
            run_id=run_id,
            payload=bundle_payload,
            provenance_hash=str(bundle_payload["bundle_digest"]),
            metadata={
                "failure_bundle_id": str(bundle_payload["failure_bundle_id"]),
                "failure_kind": str(bundle_payload["failure_kind"]),
                "integration_version": FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION,
            },
            created_at=observed_at,
            quarantine_marker="clean",
        )

    def _build_reference(
        self,
        *,
        artifact_manifest_hash: str,
        bundle_payload: Mapping[str, object],
        recovery_plan_hash: str,
        snapshot_reconstruction_hash: str,
        stderr_digest: str | None,
        stderr_truncated: bool,
        stdout_digest: str | None,
        stdout_truncated: bool,
        wal_record_hash: str,
        observed_at: str,
    ) -> FailureBundleReference:
        reference = build_failure_bundle_reference(
            {
                "artifact_manifest_hash": artifact_manifest_hash,
                "bundle_digest": str(bundle_payload["bundle_digest"]),
                "failure_bundle_id": str(bundle_payload["failure_bundle_id"]),
                "failure_class": str(bundle_payload["failure_class"]),
                "failure_code": str(bundle_payload["failure_code"]),
                "failure_stage": str(bundle_payload["failure_stage"]),
                "quarantine_required": bundle_payload["quarantine_required"],
                "recovery_plan_hash": recovery_plan_hash,
                "retry_decision": str(bundle_payload["retry_decision"]),
                "run_id": str(bundle_payload["run_id"]),
                "severity": str(bundle_payload["severity"]),
                "snapshot_reconstruction_hash": snapshot_reconstruction_hash,
                "stderr_digest": stderr_digest,
                "stderr_truncated": stderr_truncated,
                "stdout_digest": stdout_digest,
                "stdout_truncated": stdout_truncated,
                "task_id": str(bundle_payload["task_id"]),
                "wal_record_hash": wal_record_hash,
            },
            observed_at=observed_at,
        )
        if not validate_failure_bundle_reference(reference):
            raise FailureBundleCenterIntegrationError("failure_reference_invalid")
        return reference

    def _build_manifest(
        self,
        *,
        reference: FailureBundleReference,
        recovery_plan_hash: str,
        run_id: str,
        task_id: str,
        wal_head_hash: str,
        created_at: str,
    ) -> FailureBundleCenterManifest:
        manifest_id = "failure-center-" + _sha256_json(
            {
                "failure_reference_hash": reference.reference_hash,
                "run_id": run_id,
                "task_id": task_id,
            }
        ).removeprefix("sha256:")[:32]
        manifest = build_failure_bundle_center_manifest(
            manifest_id=manifest_id,
            task_id=task_id,
            run_id=run_id,
            wal_head_hash=wal_head_hash,
            recovery_plan_hash=recovery_plan_hash,
            references=(reference,),
            created_at=created_at,
        )
        if not validate_failure_bundle_center_manifest(manifest):
            raise FailureBundleCenterIntegrationError("failure_manifest_invalid")
        return manifest

    def _minimal_receipt(
        self,
        *,
        failure_kind: str,
        failure_bundle_id: str,
        task_id: str,
        job_id: str,
        run_id: str,
        spec: _CriticalFailureSpec,
        recovery_plan_hash: str,
        snapshot_reconstruction_hash: str,
        original_failure_type: str,
        observed_at: str,
        failure: str,
    ) -> FailureBundleCenterIntegratedReceipt:
        return FailureBundleCenterIntegratedReceipt(
            integration_version=FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION,
            accepted=False,
            failures=(failure,),
            failure_bundle_id="minimal-" + failure_bundle_id,
            task_id=task_id,
            job_id=job_id,
            run_id=run_id,
            failure_kind=failure_kind,
            failure_stage=spec.failure_stage,
            failure_code=spec.failure_code,
            failure_class=spec.failure_class,
            severity=spec.severity,
            retry_decision=spec.retry_decision,
            quarantine_required=True,
            bundle_digest=ZERO_HASH,
            failure_wal_record_hash=ZERO_HASH,
            failure_artifact_record_hash=ZERO_HASH,
            artifact_manifest_hash=ZERO_HASH,
            snapshot_reconstruction_hash=snapshot_reconstruction_hash,
            recovery_plan_hash=recovery_plan_hash,
            failure_reference_hash=ZERO_HASH,
            center_manifest_hash=ZERO_HASH,
            original_failure_type=original_failure_type,
            minimal_receipt=True,
            persisted_at=observed_at,
        )

    def _bundle_relpath(self, failure_bundle_id: str) -> str:
        return self.failure_store_relpath + "/bundles/" + failure_bundle_id + ".json"

    def _manifest_relpath(self, manifest_hash: str) -> str:
        return (
            self.failure_store_relpath
            + "/manifests/"
            + manifest_hash.removeprefix("sha256:")
            + ".json"
        )

    def _receipt_relpath(self, receipt_hash: str) -> str:
        return (
            self.failure_store_relpath
            + "/receipts/"
            + receipt_hash.removeprefix("sha256:")
            + ".json"
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        _validate_relpath_text(relpath, field_name)
        candidate = self.runtime_root / relpath
        current = self.runtime_root
        for part in PurePosixPath(relpath).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise FailureBundleCenterIntegrationError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise FailureBundleCenterIntegrationError(field_name + "_escapes_runtime_root")
        return resolved

    def _write_json_no_overwrite(
        self,
        relpath: str,
        payload: Mapping[str, object],
    ) -> None:
        path = self._resolve_relpath(relpath, "failure_write_relpath")
        data = (_canonical_json(payload) + "\n").encode("utf-8")
        if path.exists():
            if path.is_symlink():
                raise FailureBundleCenterIntegrationError("failure_write_target_is_symlink")
            if not path.is_file():
                raise FailureBundleCenterIntegrationError("failure_write_target_not_file")
            if path.read_bytes() == data:
                return
            raise FailureBundleCenterIntegrationError("failure_write_target_mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.is_symlink():
            raise FailureBundleCenterIntegrationError("failure_write_parent_is_symlink")
        temp_path = path.with_name(
            "." + path.name + ".tmp-" + _sha256_bytes(data).removeprefix("sha256:")[:16]
        )
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            try:
                written = 0
                while written < len(data):
                    count = os.write(fd, data[written:])
                    if count <= 0:
                        raise FailureBundleCenterIntegrationError("failure_write_failed")
                    written += count
                os.fsync(fd)
            finally:
                os.close(fd)
            if path.exists():
                raise FailureBundleCenterIntegrationError("failure_write_target_exists")
            temp_path.rename(path)
            _fsync_parent(path)
        except Exception:
            try:
                temp_path.unlink()
            except OSError:
                pass
            raise


def compute_failure_bundle_digest(bundle: Mapping[str, object]) -> str:
    data = _json_ready(dict(bundle))
    data.pop("bundle_digest", None)
    return _sha256_json(data)


def compute_failure_bundle_center_integrated_receipt_hash(
    receipt: FailureBundleCenterIntegratedReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if hasattr(receipt, "as_dict") else _json_ready(dict(receipt))  # type: ignore[arg-type]
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _bundle_material(
    *,
    context_hashes: Mapping[str, str],
    evidence_hashes: Mapping[str, str],
    failure_kind: str,
    job_id: str,
    original_failure_type: str,
    recovery_plan_hash: str,
    run_id: str,
    snapshot_reconstruction_hash: str,
    spec: _CriticalFailureSpec,
    stderr_digest: str | None,
    stderr_truncated: bool,
    stdout_digest: str | None,
    stdout_truncated: bool,
    task_id: str,
) -> dict[str, object]:
    return {
        "bundle_schema_version": FAILURE_BUNDLE_CENTER_INTEGRATION_VERSION,
        "context_hashes": dict(context_hashes),
        "evidence_hashes": dict(evidence_hashes),
        "failure_class": spec.failure_class,
        "failure_code": spec.failure_code,
        "failure_kind": failure_kind,
        "failure_stage": spec.failure_stage,
        "job_id": job_id,
        "original_failure_type": original_failure_type,
        "quarantine_required": spec.quarantine_required,
        "recovery_plan_hash": recovery_plan_hash,
        "retry_decision": spec.retry_decision,
        "run_id": run_id,
        "severity": spec.severity,
        "snapshot_reconstruction_hash": snapshot_reconstruction_hash,
        "stderr_digest": stderr_digest,
        "stderr_truncated": stderr_truncated,
        "stdout_digest": stdout_digest,
        "stdout_truncated": stdout_truncated,
        "task_id": task_id,
    }


def _failure_bundle_id(bundle_material: Mapping[str, object]) -> str:
    return "failure-bundle-" + _sha256_json(bundle_material).removeprefix("sha256:")[:32]


def _failure_spec(failure_kind: str) -> _CriticalFailureSpec:
    _require_nonempty_string(failure_kind, "failure_kind")
    try:
        return FAILURE_BUNDLE_CRITICAL_KINDS[failure_kind]
    except KeyError as exc:
        raise FailureBundleCenterIntegrationError("failure_kind_not_supported") from exc


def _require_spec_context(
    spec: _CriticalFailureSpec,
    context_hashes: Mapping[str, str],
) -> None:
    missing = [
        field
        for field in spec.required_contexts
        if context_hashes.get(field, ZERO_HASH) == ZERO_HASH
    ]
    if missing:
        raise FailureBundleCenterIntegrationError(
            "failure_context_missing:" + ",".join(missing)
        )


def _normalize_context_hashes(context_hashes: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(context_hashes, Mapping):
        raise FailureBundleCenterIntegrationError("context_hashes_must_be_mapping")
    unknown = sorted(str(key) for key in context_hashes if str(key) not in _CONTEXT_FIELDS)
    if unknown:
        raise FailureBundleCenterIntegrationError("context_hash_unknown:" + ",".join(unknown))
    normalized = {field: ZERO_HASH for field in _CONTEXT_FIELDS}
    for key, value in context_hashes.items():
        key_text = str(key)
        _require_sha256(value, key_text)
        normalized[key_text] = str(value)
    return normalized


def _normalize_evidence_hashes(evidence_hashes: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(evidence_hashes, Mapping):
        raise FailureBundleCenterIntegrationError("evidence_hashes_must_be_mapping")
    normalized: dict[str, str] = {}
    for key, value in evidence_hashes.items():
        key_text = str(key)
        _require_safe_binding_name(key_text, "evidence_hash_name")
        _require_sha256(value, key_text)
        normalized[key_text] = str(value)
    return dict(sorted(normalized.items()))


def _read_json_object(path: Path, label: str) -> dict[str, object]:
    if not path.exists():
        raise FailureBundleCenterIntegrationError(label + "_missing")
    if path.is_symlink():
        raise FailureBundleCenterIntegrationError(label + "_is_symlink")
    if not path.is_file():
        raise FailureBundleCenterIntegrationError(label + "_not_file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FailureBundleCenterIntegrationError(label + "_invalid_json") from exc
    if not isinstance(payload, Mapping):
        raise FailureBundleCenterIntegrationError(label + "_must_be_mapping")
    return _json_ready(payload)


def _sanitize_exception_type(exception: BaseException | None) -> str:
    if exception is None:
        return "None"
    candidate = exception.__class__.__name__
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", candidate):
        return candidate
    return "SanitizedException"


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise FailureBundleCenterIntegrationError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise FailureBundleCenterIntegrationError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise FailureBundleCenterIntegrationError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise FailureBundleCenterIntegrationError(field_name + "_required")
    if "\\" in value:
        raise FailureBundleCenterIntegrationError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise FailureBundleCenterIntegrationError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise FailureBundleCenterIntegrationError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise FailureBundleCenterIntegrationError(field_name + "_secret_like")


def _require_safe_binding_name(value: str, field_name: str) -> None:
    if not _SAFE_NAME_PATTERN.fullmatch(value):
        raise FailureBundleCenterIntegrationError(field_name + "_invalid")
    if (
        value in _FORBIDDEN_EXACT_KEYS
        or any(fragment in value for fragment in _FORBIDDEN_KEY_FRAGMENTS)
        or _SECRET_KEY_PATTERN.search(value)
    ):
        raise FailureBundleCenterIntegrationError(field_name + "_forbidden")


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise FailureBundleCenterIntegrationError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value)
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _optional_sha256(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    _require_sha256(value, field_name)
    return value


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    _require_nonempty_string(value, "timestamp")
    _parse_timestamp(value, "timestamp")
    return value


def _parse_timestamp(value: str, field_name: str) -> datetime:
    _require_nonempty_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FailureBundleCenterIntegrationError(field_name + "_must_be_isoformat") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise FailureBundleCenterIntegrationError(field_name + "_required")
    if _SECRET_KEY_PATTERN.search(value):
        raise FailureBundleCenterIntegrationError(field_name + "_secret_like")
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            raise FailureBundleCenterIntegrationError(field_name + "_secret_value")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise FailureBundleCenterIntegrationError(field_name + "_must_be_sha256")


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        _require_sha256(current, field_name)
        if current != expected:
            raise FailureBundleCenterIntegrationError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _canonical_json(payload: object) -> str:
    _reject_forbidden_material(payload)
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            result[key_text] = _json_ready(item)
        return result
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise FailureBundleCenterIntegrationError(
        "json_value_type_forbidden:" + type(value).__name__
    )


def _reject_forbidden_material(value: object, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise FailureBundleCenterIntegrationError("failure_material_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key in _FORBIDDEN_EXACT_KEYS:
                raise FailureBundleCenterIntegrationError("failure_material_field_forbidden:" + key_path)
            if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise FailureBundleCenterIntegrationError("failure_material_field_forbidden:" + key_path)
            if _SECRET_KEY_PATTERN.search(key) and not key.endswith("_hash"):
                raise FailureBundleCenterIntegrationError("failure_material_field_forbidden:" + key_path)
            _reject_forbidden_material(nested, path=key_path)
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_forbidden_material(nested, path=f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise FailureBundleCenterIntegrationError("failure_material_secret_value")


def _sha256_json(payload: object) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _dedupe(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)
