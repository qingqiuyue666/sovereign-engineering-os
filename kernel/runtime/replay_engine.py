"""Standalone replay verification contract.

Replay Engine V1 compares caller-supplied receipt and replay descriptors. It
does not execute commands, rerun jobs, open browsers, call networks/providers,
or mutate artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping

from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "ReplayVerificationReport",
    "verify_replay_descriptor",
]

_POLICY_VERSION = "replay-engine-v1"
_CODE_VERSION = "0.1.0"

_REQUIRED_STRING_FIELDS = (
    "replay_id",
    "source_receipt_id",
    "candidate_receipt_id",
    "expected_command_id",
    "actual_command_id",
)

_REQUIRED_DIGEST_FIELDS = (
    "source_receipt_digest",
    "candidate_receipt_digest",
    "expected_environment_digest",
    "actual_environment_digest",
    "expected_argv_hash",
    "actual_argv_hash",
    "expected_output_digest",
    "actual_output_digest",
)

_FORBIDDEN_FIELDS = (
    "raw_stdout",
    "raw_stderr",
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "command_line",
    "argv_override",
)


@dataclass(frozen=True)
class ReplayVerificationReport:
    replay_id: str
    accepted: bool
    replay_match: bool
    failure_classification: str
    failures: tuple[str, ...]
    receipt_comparison_hash: str
    content_hash: str
    observed_at: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "code_version": self.code_version,
            "failure_classification": self.failure_classification,
            "failures": list(self.failures),
            "policy_version": self.policy_version,
            "receipt_comparison_hash": self.receipt_comparison_hash,
            "replay_id": self.replay_id,
            "replay_match": self.replay_match,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def verify_replay_descriptor(
    descriptor: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> ReplayVerificationReport:
    """Compare replay evidence without re-executing the command."""

    if not isinstance(descriptor, Mapping):
        return _report(
            replay_id="",
            accepted=False,
            replay_match=False,
            failures=("descriptor_must_be_mapping",),
            descriptor={},
            observed_at=observed_at,
        )
    payload = dict(descriptor)
    failures = _validate_descriptor(payload)
    replay_id = str(payload.get("replay_id", ""))
    if not failures:
        _compare_fields(
            payload,
            failures,
            expected="source_receipt_digest",
            actual="candidate_receipt_digest",
            failure="receipt_digest_mismatch",
        )
        _compare_fields(
            payload,
            failures,
            expected="expected_environment_digest",
            actual="actual_environment_digest",
            failure="environment_digest_mismatch",
        )
        _compare_fields(
            payload,
            failures,
            expected="expected_command_id",
            actual="actual_command_id",
            failure="command_id_mismatch",
        )
        _compare_fields(
            payload,
            failures,
            expected="expected_argv_hash",
            actual="actual_argv_hash",
            failure="argv_hash_mismatch",
        )
        _compare_fields(
            payload,
            failures,
            expected="expected_output_digest",
            actual="actual_output_digest",
            failure="output_digest_mismatch",
        )
        if payload.get("expected_exit_code") != payload.get("actual_exit_code"):
            failures.append("exit_code_mismatch")

    accepted = not any(_is_validation_failure(failure) for failure in failures)
    replay_match = accepted and not failures
    return _report(
        replay_id=replay_id,
        accepted=accepted,
        replay_match=replay_match,
        failures=failures,
        descriptor=payload,
        observed_at=observed_at,
    )


def _validate_descriptor(payload: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")
    for field in _REQUIRED_STRING_FIELDS:
        if not strict_nonempty_string(payload.get(field)):
            failures.append(f"{field}_required")
    for field in _REQUIRED_DIGEST_FIELDS:
        if not strict_digest(payload.get(field)):
            failures.append(f"{field}_required")
    for field in ("expected_exit_code", "actual_exit_code"):
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{field}_must_be_int")
    reexecution = payload.get("automatic_reexecution_requested")
    if reexecution is not False:
        failures.append("automatic_reexecution_forbidden")
    return failures


def _compare_fields(
    payload: Mapping[str, object],
    failures: list[str],
    *,
    expected: str,
    actual: str,
    failure: str,
) -> None:
    if payload.get(expected) != payload.get(actual):
        failures.append(failure)


def _report(
    *,
    replay_id: str,
    accepted: bool,
    replay_match: bool,
    failures: list[str] | tuple[str, ...],
    descriptor: Mapping[str, object],
    observed_at: str | None,
) -> ReplayVerificationReport:
    normalized_failures = tuple(sorted(set(failures)))
    receipt_material = {
        "actual_argv_hash": descriptor.get("actual_argv_hash"),
        "actual_command_id": descriptor.get("actual_command_id"),
        "actual_environment_digest": descriptor.get("actual_environment_digest"),
        "actual_exit_code": descriptor.get("actual_exit_code"),
        "actual_output_digest": descriptor.get("actual_output_digest"),
        "candidate_receipt_digest": descriptor.get("candidate_receipt_digest"),
        "expected_argv_hash": descriptor.get("expected_argv_hash"),
        "expected_command_id": descriptor.get("expected_command_id"),
        "expected_environment_digest": descriptor.get("expected_environment_digest"),
        "expected_exit_code": descriptor.get("expected_exit_code"),
        "expected_output_digest": descriptor.get("expected_output_digest"),
        "source_receipt_digest": descriptor.get("source_receipt_digest"),
    }
    receipt_comparison_hash = _digest_payload(receipt_material)
    classification = _classify(normalized_failures, accepted, replay_match)
    material = {
        "accepted": accepted,
        "code_version": _CODE_VERSION,
        "failure_classification": classification,
        "failures": list(normalized_failures),
        "policy_version": _POLICY_VERSION,
        "receipt_comparison_hash": receipt_comparison_hash,
        "replay_id": replay_id,
        "replay_match": replay_match,
    }
    return ReplayVerificationReport(
        replay_id=replay_id,
        accepted=accepted,
        replay_match=replay_match,
        failure_classification=classification,
        failures=normalized_failures,
        receipt_comparison_hash=receipt_comparison_hash,
        content_hash=_digest_payload(material),
        observed_at=_timestamp(observed_at),
    )


def _classify(failures: tuple[str, ...], accepted: bool, replay_match: bool) -> str:
    if replay_match:
        return "REPLAY_MATCH"
    if not accepted:
        return "INVALID_DESCRIPTOR"
    mismatch_classes = {
        "receipt_digest_mismatch": "RECEIPT_MISMATCH",
        "environment_digest_mismatch": "ENVIRONMENT_MISMATCH",
        "command_id_mismatch": "COMMAND_MISMATCH",
        "argv_hash_mismatch": "ARGV_MISMATCH",
        "output_digest_mismatch": "OUTPUT_MISMATCH",
        "exit_code_mismatch": "EXIT_CODE_MISMATCH",
    }
    present = [mismatch_classes[failure] for failure in failures if failure in mismatch_classes]
    if len(present) == 1:
        return present[0]
    if present:
        return "MULTIPLE_MISMATCHES"
    return "REPLAY_REJECTED"


def _is_validation_failure(failure: str) -> bool:
    return (
        failure.endswith("_required")
        or failure.endswith("_must_be_int")
        or failure.endswith("_forbidden")
        or failure == "automatic_reexecution_forbidden"
        or failure == "descriptor_must_be_mapping"
    )


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
