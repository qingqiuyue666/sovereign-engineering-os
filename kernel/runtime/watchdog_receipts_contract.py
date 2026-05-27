"""Watchdog receipts contract v1.

This module defines deterministic, digest-only receipts for resource watchdog
policy and observations. It does not launch work, kill work, persist diagnostics,
call providers, open browsers, or start background loops. Observation timestamps
are metadata and excluded from content hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "WatchdogPolicyReceipt",
    "WatchdogObservationReceipt",
    "build_watchdog_policy_receipt",
    "build_watchdog_observation_receipt",
    "validate_watchdog_policy_receipt",
    "validate_watchdog_observation_receipt",
    "validate_watchdog_observation_chain",
]

_CONTRACT_VERSION = "watchdog-receipts-contract-v1"
_CODE_VERSION = "0.1.0"
_GENESIS_HASH = "sha256:" + ("0" * 64)

_ALLOWED_STATES = frozenset(
    {
        "ok",
        "deadline_exceeded",
        "memory_exceeded",
        "stream_limit_exceeded",
        "worker_exit_nonzero",
        "cancelled",
    }
)
_TERMINAL_STATES = frozenset(
    {
        "deadline_exceeded",
        "memory_exceeded",
        "stream_limit_exceeded",
        "worker_exit_nonzero",
        "cancelled",
    }
)
_DIGEST_STREAM_KEYS = frozenset(
    {
        "stderr_digest",
        "stderr_truncated",
        "stdout_digest",
        "stdout_truncated",
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
class WatchdogPolicyReceipt:
    """Digest-only watchdog policy receipt."""

    watchdog_policy_id: str
    task_id: str
    run_id: str
    queue_job_hash: str
    worker_admission_receipt_hash: str
    max_runtime_ms: int
    max_memory_mb: int
    stdout_limit_bytes: int
    stderr_limit_bytes: int
    kill_allowed: bool
    retry_allowed: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    policy_hash: str = ""
    created_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "kill_allowed": self.kill_allowed,
            "max_memory_mb": self.max_memory_mb,
            "max_runtime_ms": self.max_runtime_ms,
            "queue_job_hash": self.queue_job_hash,
            "retry_allowed": self.retry_allowed,
            "run_id": self.run_id,
            "stderr_limit_bytes": self.stderr_limit_bytes,
            "stdout_limit_bytes": self.stdout_limit_bytes,
            "task_id": self.task_id,
            "watchdog_policy_id": self.watchdog_policy_id,
            "worker_admission_receipt_hash": self.worker_admission_receipt_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["created_at"] = self.created_at
        payload["policy_hash"] = self.policy_hash
        return payload


@dataclass(frozen=True)
class WatchdogObservationReceipt:
    """Digest-only watchdog observation receipt with chain links."""

    watchdog_observation_id: str
    watchdog_policy_hash: str
    task_id: str
    run_id: str
    sequence: int
    previous_receipt_hash: str
    observed_state: str
    elapsed_ms: int
    observed_memory_mb: int
    stdout_digest: str | None
    stderr_digest: str | None
    stdout_truncated: bool
    stderr_truncated: bool
    wal_record_hash: str
    artifact_manifest_hash: str
    failure_bundle_hash: str | None
    quarantine_required: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    receipt_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "artifact_manifest_hash": self.artifact_manifest_hash,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "elapsed_ms": self.elapsed_ms,
            "failure_bundle_hash": self.failure_bundle_hash,
            "observed_memory_mb": self.observed_memory_mb,
            "observed_state": self.observed_state,
            "previous_receipt_hash": self.previous_receipt_hash,
            "quarantine_required": self.quarantine_required,
            "receipt_sequence": self.sequence,
            "run_id": self.run_id,
            "stderr_digest": self.stderr_digest,
            "stderr_truncated": self.stderr_truncated,
            "stdout_digest": self.stdout_digest,
            "stdout_truncated": self.stdout_truncated,
            "task_id": self.task_id,
            "wal_record_hash": self.wal_record_hash,
            "watchdog_observation_id": self.watchdog_observation_id,
            "watchdog_policy_hash": self.watchdog_policy_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["observed_at"] = self.observed_at
        payload["receipt_hash"] = self.receipt_hash
        return payload


def build_watchdog_policy_receipt(
    payload: Mapping[str, Any],
    *,
    created_at: str | None = None,
) -> WatchdogPolicyReceipt:
    """Build a deterministic watchdog policy receipt."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    max_runtime_ms = _positive_int_field(payload, "max_runtime_ms")
    max_memory_mb = _positive_int_field(payload, "max_memory_mb")
    stdout_limit_bytes = _positive_int_field(payload, "stdout_limit_bytes")
    stderr_limit_bytes = _positive_int_field(payload, "stderr_limit_bytes")
    kill_allowed = _bool_field(payload, "kill_allowed")
    retry_allowed = _bool_field(payload, "retry_allowed")
    if kill_allowed is not False:
        raise ValueError("kill_allowed_must_be_false_for_receipt_contract")
    if retry_allowed is not False:
        raise ValueError("retry_allowed_must_be_false_for_receipt_contract")

    material = {
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "kill_allowed": kill_allowed,
        "max_memory_mb": max_memory_mb,
        "max_runtime_ms": max_runtime_ms,
        "queue_job_hash": _digest_field(payload, "queue_job_hash"),
        "retry_allowed": retry_allowed,
        "run_id": _string_field(payload, "run_id"),
        "stderr_limit_bytes": stderr_limit_bytes,
        "stdout_limit_bytes": stdout_limit_bytes,
        "task_id": _string_field(payload, "task_id"),
        "watchdog_policy_id": _string_field(payload, "watchdog_policy_id"),
        "worker_admission_receipt_hash": _digest_field(payload, "worker_admission_receipt_hash"),
    }
    observed = _observed_at(created_at)
    return WatchdogPolicyReceipt(
        watchdog_policy_id=str(material["watchdog_policy_id"]),
        task_id=str(material["task_id"]),
        run_id=str(material["run_id"]),
        queue_job_hash=str(material["queue_job_hash"]),
        worker_admission_receipt_hash=str(material["worker_admission_receipt_hash"]),
        max_runtime_ms=max_runtime_ms,
        max_memory_mb=max_memory_mb,
        stdout_limit_bytes=stdout_limit_bytes,
        stderr_limit_bytes=stderr_limit_bytes,
        kill_allowed=kill_allowed,
        retry_allowed=retry_allowed,
        policy_hash=digest_payload(material),
        created_at=observed,
    )


def build_watchdog_observation_receipt(
    payload: Mapping[str, Any],
    *,
    observed_at: str | None = None,
) -> WatchdogObservationReceipt:
    """Build a deterministic watchdog observation receipt."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    observed_state = _string_field(payload, "observed_state")
    failure_bundle_hash = _optional_digest_field(payload, "failure_bundle_hash")
    quarantine_required = _bool_field(payload, "quarantine_required")
    sequence = _positive_int_field(payload, "sequence")
    previous_receipt_hash = _digest_field(payload, "previous_receipt_hash")
    if observed_state not in _ALLOWED_STATES:
        raise ValueError("observed_state_not_allowed")
    if sequence == 1 and previous_receipt_hash != _GENESIS_HASH:
        raise ValueError("first_watchdog_receipt_requires_genesis_previous_hash")
    if observed_state in _TERMINAL_STATES:
        if failure_bundle_hash is None:
            raise ValueError("terminal_watchdog_state_requires_failure_bundle_hash")
        if quarantine_required is not True:
            raise ValueError("terminal_watchdog_state_requires_quarantine")
    else:
        if failure_bundle_hash is not None:
            raise ValueError("ok_watchdog_state_must_not_have_failure_bundle_hash")
        if quarantine_required is not False:
            raise ValueError("ok_watchdog_state_must_not_require_quarantine")

    material = {
        "artifact_manifest_hash": _digest_field(payload, "artifact_manifest_hash"),
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "elapsed_ms": _nonnegative_int_field(payload, "elapsed_ms"),
        "failure_bundle_hash": failure_bundle_hash,
        "observed_memory_mb": _nonnegative_int_field(payload, "observed_memory_mb"),
        "observed_state": observed_state,
        "previous_receipt_hash": previous_receipt_hash,
        "quarantine_required": quarantine_required,
        "receipt_sequence": sequence,
        "run_id": _string_field(payload, "run_id"),
        "stderr_digest": _optional_digest_field(payload, "stderr_digest"),
        "stderr_truncated": _bool_field(payload, "stderr_truncated"),
        "stdout_digest": _optional_digest_field(payload, "stdout_digest"),
        "stdout_truncated": _bool_field(payload, "stdout_truncated"),
        "task_id": _string_field(payload, "task_id"),
        "wal_record_hash": _digest_field(payload, "wal_record_hash"),
        "watchdog_observation_id": _string_field(payload, "watchdog_observation_id"),
        "watchdog_policy_hash": _digest_field(payload, "watchdog_policy_hash"),
    }
    observed = _observed_at(observed_at)
    return WatchdogObservationReceipt(
        watchdog_observation_id=str(material["watchdog_observation_id"]),
        watchdog_policy_hash=str(material["watchdog_policy_hash"]),
        task_id=str(material["task_id"]),
        run_id=str(material["run_id"]),
        sequence=sequence,
        previous_receipt_hash=previous_receipt_hash,
        observed_state=observed_state,
        elapsed_ms=int(material["elapsed_ms"]),
        observed_memory_mb=int(material["observed_memory_mb"]),
        stdout_digest=material["stdout_digest"],
        stderr_digest=material["stderr_digest"],
        stdout_truncated=bool(material["stdout_truncated"]),
        stderr_truncated=bool(material["stderr_truncated"]),
        wal_record_hash=str(material["wal_record_hash"]),
        artifact_manifest_hash=str(material["artifact_manifest_hash"]),
        failure_bundle_hash=failure_bundle_hash,
        quarantine_required=quarantine_required,
        receipt_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_watchdog_policy_receipt(receipt: WatchdogPolicyReceipt) -> bool:
    if not isinstance(receipt, WatchdogPolicyReceipt):
        return False
    for value in (
        receipt.watchdog_policy_id,
        receipt.task_id,
        receipt.run_id,
        receipt.contract_version,
        receipt.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    for value in (receipt.queue_job_hash, receipt.worker_admission_receipt_hash):
        if not strict_digest(value):
            return False
    for value in (
        receipt.max_runtime_ms,
        receipt.max_memory_mb,
        receipt.stdout_limit_bytes,
        receipt.stderr_limit_bytes,
    ):
        if not _positive_int(value):
            return False
    if receipt.kill_allowed is not False:
        return False
    if receipt.retry_allowed is not False:
        return False
    return receipt.policy_hash == digest_payload(receipt.deterministic_material())


def validate_watchdog_observation_receipt(receipt: WatchdogObservationReceipt) -> bool:
    if not isinstance(receipt, WatchdogObservationReceipt):
        return False
    for value in (
        receipt.watchdog_observation_id,
        receipt.task_id,
        receipt.run_id,
        receipt.contract_version,
        receipt.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    if not strict_digest(receipt.watchdog_policy_hash):
        return False
    if not _positive_int(receipt.sequence):
        return False
    if not strict_digest(receipt.previous_receipt_hash):
        return False
    if receipt.sequence == 1 and receipt.previous_receipt_hash != _GENESIS_HASH:
        return False
    if receipt.observed_state not in _ALLOWED_STATES:
        return False
    if not _nonnegative_int(receipt.elapsed_ms):
        return False
    if not _nonnegative_int(receipt.observed_memory_mb):
        return False
    for value in (receipt.stdout_digest, receipt.stderr_digest):
        if value is not None and not strict_digest(value):
            return False
    if not strict_bool(receipt.stdout_truncated):
        return False
    if not strict_bool(receipt.stderr_truncated):
        return False
    if not strict_digest(receipt.wal_record_hash):
        return False
    if not strict_digest(receipt.artifact_manifest_hash):
        return False
    if receipt.observed_state in _TERMINAL_STATES:
        if not strict_digest(receipt.failure_bundle_hash):
            return False
        if receipt.quarantine_required is not True:
            return False
    else:
        if receipt.failure_bundle_hash is not None:
            return False
        if receipt.quarantine_required is not False:
            return False
    return receipt.receipt_hash == digest_payload(receipt.deterministic_material())


def validate_watchdog_observation_chain(
    receipts: Sequence[WatchdogObservationReceipt],
) -> tuple[str, ...]:
    """Return fail-closed chain validation failures for watchdog receipts."""

    if not isinstance(receipts, Sequence) or not receipts:
        return ("watchdog_receipts_required",)
    failures: list[str] = []
    previous_hash = _GENESIS_HASH
    policy_hash: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    for index, receipt in enumerate(receipts, start=1):
        if not validate_watchdog_observation_receipt(receipt):
            failures.append(f"receipt_{index}_invalid")
            continue
        if receipt.sequence != index:
            failures.append(f"receipt_{index}_sequence_gap")
        if receipt.previous_receipt_hash != previous_hash:
            failures.append(f"receipt_{index}_previous_hash_mismatch")
        if policy_hash is None:
            policy_hash = receipt.watchdog_policy_hash
            task_id = receipt.task_id
            run_id = receipt.run_id
        elif (
            receipt.watchdog_policy_hash != policy_hash
            or receipt.task_id != task_id
            or receipt.run_id != run_id
        ):
            failures.append(f"receipt_{index}_identity_mismatch")
        previous_hash = receipt.receipt_hash
    return tuple(failures)


def _require_mapping(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("watchdog_receipt_payload_must_be_mapping")


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


def _positive_int_field(payload: Mapping[str, Any], field: str) -> int:
    value = payload.get(field)
    if not _positive_int(value):
        raise ValueError(f"{field}_must_be_positive_integer")
    return int(value)


def _nonnegative_int_field(payload: Mapping[str, Any], field: str) -> int:
    value = payload.get(field)
    if not _nonnegative_int(value):
        raise ValueError(f"{field}_must_be_nonnegative_integer")
    return int(value)


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _reject_forbidden_material(value: Any, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("watchdog_receipt_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key not in _DIGEST_STREAM_KEYS:
                if key in _FORBIDDEN_EXACT_KEYS:
                    raise ValueError(f"forbidden_watchdog_material_field_{key_path}")
                if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                    raise ValueError(f"forbidden_watchdog_material_field_{key_path}")
            _reject_forbidden_material(nested, path=key_path)
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_forbidden_material(nested, path=f"{path}[{index}]")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    return value
