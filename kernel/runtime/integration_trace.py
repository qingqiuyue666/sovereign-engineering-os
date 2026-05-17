"""Deterministic runtime integration trace descriptor.

Produces a trace descriptor for the full dry-run path that contains only
digest refs. No raw content, no inline payloads, no live provider responses,
no network results.

The trace is a deterministic digest chain that links all foundation module
receipts into a verifiable integration spine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.runtime._strict_validation import (
    strict_digest,
)

__all__ = [
    "IntegrationTraceReceipt",
    "IntegrationTraceRejection",
    "validate_integration_trace",
]

_REQUIRED_DIGEST_FIELDS: tuple[str, ...] = (
    "execution_descriptor_digest",
    "runner_receipt_digest",
    "state_transition_digest",
    "idempotency_digest",
    "event_journal_digest",
    "provider_boundary_digest",
    "evidence_boundary_digest",
)

_OPTIONAL_DIGEST_FIELDS: tuple[str, ...] = (
    "failure_bundle_digest",
    "replay_plan_digest",
    "replay_diff_digest",
)

_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "inline_payload",
    "live_provider_response",
    "network_result",
)

_ALL_DIGEST_FIELDS: tuple[str, ...] = _REQUIRED_DIGEST_FIELDS + _OPTIONAL_DIGEST_FIELDS


class IntegrationTraceRejection(ValueError):
    """Raised when an integration trace violates a policy boundary."""


@dataclass(frozen=True)
class IntegrationTraceReceipt:
    """Deterministic receipt from integration trace validation."""

    accepted: bool
    failures: tuple[str, ...]
    trace_digest: str
    policy_version: str
    code_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "trace_digest": self.trace_digest,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
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


def validate_integration_trace(payload: Mapping[str, object]) -> IntegrationTraceReceipt:
    """Validate a runtime integration trace descriptor against policy.

    The trace must contain digest refs only — no raw content, no inline
    payloads, no live provider responses, no network results.

    Returns an IntegrationTraceReceipt with accepted=True and a deterministic
    trace_digest if valid, or accepted=False with failures if not.
    """
    if not isinstance(payload, Mapping):
        raise IntegrationTraceRejection("integration_trace_must_be_a_mapping")

    failures: list[str] = []

    # Gate 1: forbidden fields must be absent
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    # Gate 2: required digest fields must be present and valid
    for field in _REQUIRED_DIGEST_FIELDS:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not strict_digest(value):
            if isinstance(value, str):
                failures.append(f"{field}_must_be_valid_digest")
            else:
                failures.append(f"{field}_must_be_string")

    # Gate 3: optional digest fields must be valid if present
    for field in _OPTIONAL_DIGEST_FIELDS:
        if field in payload:
            value = payload[field]
            if not strict_digest(value):
                if isinstance(value, str):
                    failures.append(f"{field}_must_be_valid_digest")
                else:
                    failures.append(f"{field}_must_be_string")

    policy_version = _safe_str(payload.get("policy_version", ""))
    code_version = _safe_str(payload.get("code_version", ""))

    if failures:
        trace_digest = "sha256:" + hashlib.sha256(
            ("rejected:" + ":".join(sorted(failures))).encode("utf-8")
        ).hexdigest()
        return IntegrationTraceReceipt(
            accepted=False,
            failures=tuple(failures),
            trace_digest=trace_digest,
            policy_version=policy_version,
            code_version=code_version,
        )

    # Build deterministic trace digest from all digest fields
    trace_seed: dict[str, str] = {}
    for field in _REQUIRED_DIGEST_FIELDS:
        trace_seed[field] = _safe_str(payload.get(field, ""))
    for field in _OPTIONAL_DIGEST_FIELDS:
        if field in payload:
            trace_seed[field] = _safe_str(payload[field])
    trace_digest = _digest_payload(trace_seed)

    return IntegrationTraceReceipt(
        accepted=True,
        failures=(),
        trace_digest=trace_digest,
        policy_version=policy_version,
        code_version=code_version,
    )
