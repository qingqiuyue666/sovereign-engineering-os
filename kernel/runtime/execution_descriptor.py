"""Deterministic runtime execution descriptor validation foundation.

This module provides strict validation of RuntimeExecutionDescriptor inputs
against policy boundaries. It enforces:

- dry_run=true, provider_enabled=false, network_access=false, production_autonomy=false
- All booleans must be actual bool (not strings, ints, or None)
- All required strings must be non-empty, non-whitespace strings
- All digests must match sha256:<64 lowercase hex>
- Forbidden fields rejected (raw_prompt, raw_provider_response, secret_value, etc.)

No provider calls, no network, no SQLite, no file mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.runtime._strict_validation import (
    strict_bool,
    strict_digest,
    strict_nonempty_string,
)

__all__ = [
    "ExecutionDescriptorReceipt",
    "ExecutionDescriptorRejection",
    "validate_execution_descriptor",
]

_REQUIRED_STRING_FIELDS: tuple[str, ...] = (
    "task_id",
    "run_id",
    "execution_id",
    "stage",
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS: tuple[str, ...] = (
    "input_digest",
    "task_manifest_digest",
    "operator_intent_digest",
)

_REQUIRED_BOOL_FIELDS: tuple[str, ...] = (
    "dry_run",
    "provider_enabled",
    "network_access",
    "production_autonomy",
)

_REQUIRED_BOOL_VALUES: dict[str, bool] = {
    "dry_run": True,
    "provider_enabled": False,
    "network_access": False,
    "production_autonomy": False,
}

_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "provider_api_key",
    "live_network_target",
    "autonomy_directive",
)


class ExecutionDescriptorRejection(ValueError):
    """Raised when an execution descriptor violates a policy boundary."""


@dataclass(frozen=True)
class ExecutionDescriptorReceipt:
    """Deterministic receipt from execution descriptor validation."""

    accepted: bool
    failures: tuple[str, ...]
    execution_id: str
    task_id: str
    run_id: str
    policy_version: str
    code_version: str
    descriptor_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "descriptor_digest": self.descriptor_digest,
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def _safe_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def validate_execution_descriptor(payload: Mapping[str, object]) -> ExecutionDescriptorReceipt:
    """Validate a RuntimeExecutionDescriptor against policy boundaries.

    Returns an ExecutionDescriptorReceipt with accepted=True and empty failures
    if the descriptor passes all gates. Otherwise accepted=False with failures
    listing all rejection reasons.

    Checks (in order):
    1. Input must be a Mapping
    2. Forbidden fields must be absent
    3. Required string fields must be present, non-empty, non-whitespace strings
    4. Required digest fields must match sha256:<64 lowercase hex>
    5. Required boolean fields must be present and actual bool type
    6. Required boolean values must match expected (dry_run=true, others=false)
    """
    if not isinstance(payload, Mapping):
        raise ExecutionDescriptorRejection("execution_descriptor_must_be_a_mapping")

    failures: list[str] = []

    # Gate 1: forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    # Gate 2: required string fields — must be non-empty, non-whitespace strings
    for field in _REQUIRED_STRING_FIELDS:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not strict_nonempty_string(value):
            if isinstance(value, str):
                failures.append(f"{field}_must_be_nonempty_string")
            else:
                failures.append(f"{field}_must_be_string")

    # Gate 3: required digest fields — must match sha256:<64 lowercase hex>
    for field in _REQUIRED_DIGEST_FIELDS:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not strict_digest(value):
            if isinstance(value, str):
                failures.append(f"{field}_must_be_valid_digest")
            else:
                failures.append(f"{field}_must_be_string")

    # Gate 4: required boolean fields — must be actual bool, not string/int
    for field in _REQUIRED_BOOL_FIELDS:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not strict_bool(value):
            failures.append(f"{field}_must_be_bool")

    # Gate 5: required boolean values — enforce expected values
    for field, expected in _REQUIRED_BOOL_VALUES.items():
        value = payload.get(field)
        if isinstance(value, bool) and value is not expected:
            failures.append(f"{field}_must_be_{str(expected).lower()}")

    execution_id = _safe_str(payload.get("execution_id", ""))
    task_id = _safe_str(payload.get("task_id", ""))
    run_id = _safe_str(payload.get("run_id", ""))
    policy_version = _safe_str(payload.get("policy_version", ""))
    code_version = _safe_str(payload.get("code_version", ""))

    if failures:
        descriptor_digest = "sha256:" + hashlib.sha256(
            ("rejected:" + ":".join(sorted(failures))).encode("utf-8")
        ).hexdigest()
        return ExecutionDescriptorReceipt(
            accepted=False,
            failures=tuple(failures),
            execution_id=execution_id,
            task_id=task_id,
            run_id=run_id,
            policy_version=policy_version,
            code_version=code_version,
            descriptor_digest=descriptor_digest,
        )

    # Compute deterministic digest from the sanitized input fields
    digest_seed: dict[str, str] = {
        "execution_id": execution_id,
        "task_id": task_id,
        "run_id": run_id,
        "stage": _safe_str(payload.get("stage", "")),
        "policy_version": policy_version,
        "code_version": code_version,
        "input_digest": _safe_str(payload.get("input_digest", "")),
        "task_manifest_digest": _safe_str(payload.get("task_manifest_digest", "")),
        "operator_intent_digest": _safe_str(payload.get("operator_intent_digest", "")),
    }
    descriptor_digest = _digest_payload(digest_seed)

    return ExecutionDescriptorReceipt(
        accepted=True,
        failures=(),
        execution_id=execution_id,
        task_id=task_id,
        run_id=run_id,
        policy_version=policy_version,
        code_version=code_version,
        descriptor_digest=descriptor_digest,
    )
