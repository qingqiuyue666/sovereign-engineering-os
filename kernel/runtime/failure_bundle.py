"""Sanitized deterministic failure bundle foundation.

Produces sanitized failure descriptors that contain only digest references.
Never stores raw prompts, raw provider responses, secret values, or env values.
All functions are deterministic and side-effect free.
Strict field typing enforced for all validations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.runtime._strict_validation import (
    strict_digest,
    strict_nonempty_string,
    validate_required_digest_fields,
    validate_required_string_fields,
)

__all__ = [
    "FailureBundleRejection",
    "FailureBundleValidationResult",
    "build_failure_bundle",
    "validate_failure_bundle",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_STRING_FIELDS = (
    "failure_id",
    "task_id",
    "run_id",
    "stage",
    "error_class",
    "sanitized_message",
    "policy_version",
    "code_version",
    "retry_decision",
    "quarantine_ref",
    "rollback_ref",
)

_REQUIRED_DIGEST_FIELDS = (
    "state_snapshot_digest",
    "input_snapshot_digest",
)


class FailureBundleRejection(ValueError):
    """Raised when a failure bundle violates policy boundaries."""


@dataclass(frozen=True)
class FailureBundleValidationResult:
    accepted: bool
    failures: tuple[str, ...]
    bundle_digest: str


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_failure_bundle(bundle: Mapping[str, object]) -> FailureBundleValidationResult:
    """Validate a failure bundle against policy boundaries with strict typing.

    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    No forbidden fields allowed.
    """
    payload_dict = dict(bundle)
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return FailureBundleValidationResult(False, tuple(failures), "")

    digest = _digest_payload(payload_dict)
    return FailureBundleValidationResult(True, (), digest)


def build_failure_bundle(
    *,
    task_id: str,
    run_id: str,
    stage: str,
    error_class: str,
    message: str,
    state_snapshot: Mapping[str, object],
    input_snapshot: Mapping[str, object],
    policy_version: str,
    code_version: str,
    retry_decision: str,
    quarantine_ref: str,
    rollback_ref: str,
) -> dict[str, object]:
    """Build a sanitized failure bundle descriptor."""
    state_digest = _digest_payload(dict(state_snapshot))
    input_digest = _digest_payload(dict(input_snapshot))

    seed = {
        "task_id": task_id,
        "run_id": run_id,
        "stage": stage,
        "error_class": error_class,
        "state_snapshot_digest": state_digest,
        "input_snapshot_digest": input_digest,
    }
    failure_id = "failure_" + _digest_payload(seed).split(":", 1)[1][:24]

    bundle = {
        "failure_id": failure_id,
        "task_id": task_id,
        "run_id": run_id,
        "stage": stage,
        "error_class": error_class,
        "sanitized_message": _sanitize_message(message),
        "state_snapshot_digest": state_digest,
        "input_snapshot_digest": input_digest,
        "policy_version": policy_version,
        "code_version": code_version,
        "retry_decision": retry_decision,
        "quarantine_ref": quarantine_ref,
        "rollback_ref": rollback_ref,
    }
    return bundle


def _sanitize_message(message: str) -> str:
    """Remove any potential raw secrets or provider content from messages."""
    sanitized = message
    for marker in ("sk-", "api_key=", "Bearer ", "secret=", "token=", "password=", "private_key"):
        if marker.lower() in sanitized.lower():
            sanitized = "[sanitized]"
            break
    return sanitized
