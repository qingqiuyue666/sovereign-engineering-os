"""Failure bundle center contract v1.

This module defines a digest-only aggregation boundary for failure evidence.
It does not persist bundles, execute recovery, run workers, call providers, or
start background control loops. Observation timestamps are metadata and are
excluded from deterministic hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "FailureBundleReference",
    "FailureBundleCenterManifest",
    "build_failure_bundle_reference",
    "build_failure_bundle_center_manifest",
    "validate_failure_bundle_reference",
    "validate_failure_bundle_center_manifest",
]

_CONTRACT_VERSION = "failure-bundle-center-contract-v1"
_CODE_VERSION = "0.1.0"

_ALLOWED_SEVERITIES = frozenset(
    {
        "retryable",
        "terminal",
        "policy_blocked",
        "operator_blocked",
    }
)
_ALLOWED_RETRY_DECISIONS = frozenset(
    {
        "retry_after_backoff",
        "manual_review_required",
        "no_retry_terminal",
    }
)
_TERMINAL_SEVERITIES = frozenset({"terminal", "policy_blocked", "operator_blocked"})

_DIGEST_OUTPUT_FIELDS = frozenset(
    {
        "stdout_digest",
        "stderr_digest",
        "stdout_truncated",
        "stderr_truncated",
    }
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "argv",
        "body",
        "command",
        "content",
        "cwd",
        "env",
        "executable",
        "filesystem_path",
        "output",
        "path",
        "payload",
        "prompt",
        "stderr",
        "stdout",
        "text",
        "timeout",
        "traceback",
        "value",
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


@dataclass(frozen=True)
class FailureBundleReference:
    """Digest-only reference to one failure bundle and its evidence anchors."""

    failure_bundle_id: str
    task_id: str
    run_id: str
    failure_stage: str
    failure_code: str
    failure_class: str
    severity: str
    retry_decision: str
    bundle_digest: str
    wal_record_hash: str
    artifact_manifest_hash: str
    snapshot_reconstruction_hash: str
    recovery_plan_hash: str
    stdout_digest: str | None
    stderr_digest: str | None
    stdout_truncated: bool
    stderr_truncated: bool
    quarantine_required: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    reference_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "artifact_manifest_hash": self.artifact_manifest_hash,
            "bundle_digest": self.bundle_digest,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "failure_bundle_id": self.failure_bundle_id,
            "failure_class": self.failure_class,
            "failure_code": self.failure_code,
            "failure_stage": self.failure_stage,
            "quarantine_required": self.quarantine_required,
            "recovery_plan_hash": self.recovery_plan_hash,
            "retry_decision": self.retry_decision,
            "run_id": self.run_id,
            "severity": self.severity,
            "snapshot_reconstruction_hash": self.snapshot_reconstruction_hash,
            "stderr_digest": self.stderr_digest,
            "stderr_truncated": self.stderr_truncated,
            "stdout_digest": self.stdout_digest,
            "stdout_truncated": self.stdout_truncated,
            "task_id": self.task_id,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["observed_at"] = self.observed_at
        payload["reference_hash"] = self.reference_hash
        return payload


@dataclass(frozen=True)
class FailureBundleCenterManifest:
    """Deterministic center manifest for a run's failure bundle evidence."""

    manifest_id: str
    task_id: str
    run_id: str
    wal_head_hash: str
    recovery_plan_hash: str
    failure_reference_hashes: tuple[str, ...]
    center_root_hash: str
    quarantine_required: bool
    retryable_failure_count: int
    terminal_failure_count: int
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    manifest_hash: str = ""
    created_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "center_root_hash": self.center_root_hash,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "failure_reference_hashes": self.failure_reference_hashes,
            "manifest_id": self.manifest_id,
            "quarantine_required": self.quarantine_required,
            "recovery_plan_hash": self.recovery_plan_hash,
            "retryable_failure_count": self.retryable_failure_count,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "terminal_failure_count": self.terminal_failure_count,
            "wal_head_hash": self.wal_head_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["created_at"] = self.created_at
        payload["manifest_hash"] = self.manifest_hash
        return payload


def build_failure_bundle_reference(
    payload: Mapping[str, Any],
    *,
    observed_at: str | None = None,
) -> FailureBundleReference:
    """Build one validated digest-only failure bundle reference."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    failure_bundle_id = _string_field(payload, "failure_bundle_id")
    task_id = _string_field(payload, "task_id")
    run_id = _string_field(payload, "run_id")
    failure_stage = _string_field(payload, "failure_stage")
    failure_code = _string_field(payload, "failure_code")
    failure_class = _string_field(payload, "failure_class")
    severity = _string_field(payload, "severity")
    retry_decision = _string_field(payload, "retry_decision")
    stdout_digest = _optional_digest_field(payload, "stdout_digest")
    stderr_digest = _optional_digest_field(payload, "stderr_digest")
    stdout_truncated = _bool_field(payload, "stdout_truncated")
    stderr_truncated = _bool_field(payload, "stderr_truncated")
    quarantine_required = _bool_field(payload, "quarantine_required")

    if severity not in _ALLOWED_SEVERITIES:
        raise ValueError("failure_severity_not_allowed")
    if retry_decision not in _ALLOWED_RETRY_DECISIONS:
        raise ValueError("retry_decision_not_allowed")
    if severity == "retryable" and retry_decision != "retry_after_backoff":
        raise ValueError("retryable_failure_requires_retry_after_backoff")
    if severity in _TERMINAL_SEVERITIES and retry_decision == "retry_after_backoff":
        raise ValueError("terminal_failure_must_not_retry_after_backoff")
    if severity in _TERMINAL_SEVERITIES and quarantine_required is not True:
        raise ValueError("terminal_failure_requires_quarantine")

    material = {
        "artifact_manifest_hash": _digest_field(payload, "artifact_manifest_hash"),
        "bundle_digest": _digest_field(payload, "bundle_digest"),
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "failure_bundle_id": failure_bundle_id,
        "failure_class": failure_class,
        "failure_code": failure_code,
        "failure_stage": failure_stage,
        "quarantine_required": quarantine_required,
        "recovery_plan_hash": _digest_field(payload, "recovery_plan_hash"),
        "retry_decision": retry_decision,
        "run_id": run_id,
        "severity": severity,
        "snapshot_reconstruction_hash": _digest_field(payload, "snapshot_reconstruction_hash"),
        "stderr_digest": stderr_digest,
        "stderr_truncated": stderr_truncated,
        "stdout_digest": stdout_digest,
        "stdout_truncated": stdout_truncated,
        "task_id": task_id,
        "wal_record_hash": _digest_field(payload, "wal_record_hash"),
    }
    observed = _observed_at(observed_at)
    return FailureBundleReference(
        failure_bundle_id=failure_bundle_id,
        task_id=task_id,
        run_id=run_id,
        failure_stage=failure_stage,
        failure_code=failure_code,
        failure_class=failure_class,
        severity=severity,
        retry_decision=retry_decision,
        bundle_digest=str(material["bundle_digest"]),
        wal_record_hash=str(material["wal_record_hash"]),
        artifact_manifest_hash=str(material["artifact_manifest_hash"]),
        snapshot_reconstruction_hash=str(material["snapshot_reconstruction_hash"]),
        recovery_plan_hash=str(material["recovery_plan_hash"]),
        stdout_digest=stdout_digest,
        stderr_digest=stderr_digest,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        quarantine_required=quarantine_required,
        reference_hash=digest_payload(material),
        observed_at=observed,
    )


def build_failure_bundle_center_manifest(
    *,
    manifest_id: str,
    task_id: str,
    run_id: str,
    wal_head_hash: str,
    recovery_plan_hash: str,
    references: Sequence[FailureBundleReference],
    created_at: str | None = None,
) -> FailureBundleCenterManifest:
    """Build a deterministic center manifest for validated references."""

    for field, value in (
        ("manifest_id", manifest_id),
        ("task_id", task_id),
        ("run_id", run_id),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(wal_head_hash):
        raise ValueError("wal_head_hash_must_be_valid_digest")
    if not strict_digest(recovery_plan_hash):
        raise ValueError("recovery_plan_hash_must_be_valid_digest")
    if not isinstance(references, Sequence) or not references:
        raise ValueError("failure_references_must_be_nonempty_sequence")

    reference_hashes: list[str] = []
    bundle_ids: set[str] = set()
    retryable_count = 0
    terminal_count = 0
    quarantine_required = False

    for reference in references:
        if not validate_failure_bundle_reference(reference):
            raise ValueError("failure_bundle_reference_invalid")
        if reference.task_id != task_id or reference.run_id != run_id:
            raise ValueError("failure_bundle_reference_identity_mismatch")
        if reference.failure_bundle_id in bundle_ids:
            raise ValueError("duplicate_failure_bundle_id")
        if reference.reference_hash in reference_hashes:
            raise ValueError("duplicate_failure_reference_hash")
        if reference.recovery_plan_hash != recovery_plan_hash:
            raise ValueError("failure_bundle_recovery_plan_hash_mismatch")
        bundle_ids.add(reference.failure_bundle_id)
        reference_hashes.append(reference.reference_hash)
        if reference.severity == "retryable":
            retryable_count += 1
        if reference.severity in _TERMINAL_SEVERITIES:
            terminal_count += 1
        quarantine_required = quarantine_required or reference.quarantine_required

    center_root_hash = digest_payload({"failure_reference_hashes": tuple(reference_hashes)})
    material = {
        "center_root_hash": center_root_hash,
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "failure_reference_hashes": tuple(reference_hashes),
        "manifest_id": manifest_id,
        "quarantine_required": quarantine_required,
        "recovery_plan_hash": recovery_plan_hash,
        "retryable_failure_count": retryable_count,
        "run_id": run_id,
        "task_id": task_id,
        "terminal_failure_count": terminal_count,
        "wal_head_hash": wal_head_hash,
    }
    observed = _observed_at(created_at)
    return FailureBundleCenterManifest(
        manifest_id=manifest_id,
        task_id=task_id,
        run_id=run_id,
        wal_head_hash=wal_head_hash,
        recovery_plan_hash=recovery_plan_hash,
        failure_reference_hashes=tuple(reference_hashes),
        center_root_hash=center_root_hash,
        quarantine_required=quarantine_required,
        retryable_failure_count=retryable_count,
        terminal_failure_count=terminal_count,
        manifest_hash=digest_payload(material),
        created_at=observed,
    )


def validate_failure_bundle_reference(reference: FailureBundleReference) -> bool:
    if not isinstance(reference, FailureBundleReference):
        return False
    for value in (
        reference.failure_bundle_id,
        reference.task_id,
        reference.run_id,
        reference.failure_stage,
        reference.failure_code,
        reference.failure_class,
        reference.contract_version,
        reference.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    if reference.severity not in _ALLOWED_SEVERITIES:
        return False
    if reference.retry_decision not in _ALLOWED_RETRY_DECISIONS:
        return False
    if reference.severity == "retryable" and reference.retry_decision != "retry_after_backoff":
        return False
    if reference.severity in _TERMINAL_SEVERITIES:
        if reference.retry_decision == "retry_after_backoff":
            return False
        if reference.quarantine_required is not True:
            return False
    if not strict_bool(reference.stdout_truncated):
        return False
    if not strict_bool(reference.stderr_truncated):
        return False
    if not strict_bool(reference.quarantine_required):
        return False
    for value in (
        reference.bundle_digest,
        reference.wal_record_hash,
        reference.artifact_manifest_hash,
        reference.snapshot_reconstruction_hash,
        reference.recovery_plan_hash,
    ):
        if not strict_digest(value):
            return False
    for value in (reference.stdout_digest, reference.stderr_digest):
        if value is not None and not strict_digest(value):
            return False
    return reference.reference_hash == digest_payload(reference.deterministic_material())


def validate_failure_bundle_center_manifest(manifest: FailureBundleCenterManifest) -> bool:
    if not isinstance(manifest, FailureBundleCenterManifest):
        return False
    for value in (
        manifest.manifest_id,
        manifest.task_id,
        manifest.run_id,
        manifest.contract_version,
        manifest.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    if not strict_digest(manifest.wal_head_hash):
        return False
    if not strict_digest(manifest.recovery_plan_hash):
        return False
    if not manifest.failure_reference_hashes:
        return False
    if len(set(manifest.failure_reference_hashes)) != len(manifest.failure_reference_hashes):
        return False
    if not all(strict_digest(value) for value in manifest.failure_reference_hashes):
        return False
    if not strict_digest(manifest.center_root_hash):
        return False
    if manifest.center_root_hash != digest_payload(
        {"failure_reference_hashes": manifest.failure_reference_hashes}
    ):
        return False
    if not strict_bool(manifest.quarantine_required):
        return False
    if not _nonnegative_int(manifest.retryable_failure_count):
        return False
    if not _nonnegative_int(manifest.terminal_failure_count):
        return False
    return manifest.manifest_hash == digest_payload(manifest.deterministic_material())


def _require_mapping(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("failure_bundle_reference_payload_must_be_mapping")


def _string_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_nonempty_string(value):
        raise ValueError(f"{field}_must_be_nonempty_string")
    return str(value)


def _digest_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _optional_digest_field(payload: Mapping[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _bool_field(payload: Mapping[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not strict_bool(value):
        raise ValueError(f"{field}_must_be_bool")
    return bool(value)


def _reject_forbidden_material(value: Any, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("failure_bundle_reference_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key not in _DIGEST_OUTPUT_FIELDS:
                if key in _FORBIDDEN_EXACT_KEYS:
                    raise ValueError(f"forbidden_failure_material_field_{key_path}")
                if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                    raise ValueError(f"forbidden_failure_material_field_{key_path}")
            _reject_forbidden_material(nested, path=key_path)
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_forbidden_material(nested, path=f"{path}[{index}]")


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    return value
