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
import re
from typing import Mapping

from kernel.runtime._strict_validation import strict_nonempty_string

__all__ = [
    "ReplayVerificationReport",
    "verify_replay_descriptor",
]

_POLICY_VERSION = "replay-engine-v1"
_CODE_VERSION = "0.2.0"

_SHA256_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")

_REQUIRED_STRING_FIELDS = (
    "replay_id",
    "source_receipt_id",
    "candidate_receipt_id",
    "expected_command_id",
    "actual_command_id",
    "expected_executable_path",
    "actual_executable_path",
    "expected_executable_realpath",
    "actual_executable_realpath",
    "expected_environment_path_policy_id",
    "actual_environment_path_policy_id",
    "expected_executable_resolution_policy_id",
    "actual_executable_resolution_policy_id",
)

_REQUIRED_SHA256_FIELDS = (
    "expected_environment_digest",
    "actual_environment_digest",
    "expected_argv_hash",
    "actual_argv_hash",
    "expected_resolved_argv_hash",
    "actual_resolved_argv_hash",
    "expected_resolution_policy_digest",
    "actual_resolution_policy_digest",
    "expected_stdout_sha256",
    "actual_stdout_sha256",
    "expected_stderr_sha256",
    "actual_stderr_sha256",
    "expected_receipt_sha256",
    "actual_receipt_sha256",
)

_RUNNER_COMPARISON_FIELDS = (
    "command_id",
    "argv_hash",
    "resolved_argv_hash",
    "executable_path",
    "executable_realpath",
    "environment_digest",
    "environment_path_policy_id",
    "executable_resolution_policy_id",
    "resolution_policy_digest",
    "stdout_sha256",
    "stderr_sha256",
    "receipt_sha256",
)

_TOKEN_REQUIRED_STRING_SUFFIXES = (
    "token_command_id",
    "token_scope",
    "token_repo_revision",
    "token_approval_artifact_id",
    "token_state",
)
_TOKEN_REQUIRED_SHA256_SUFFIXES = ("token_approval_artifact_digest",)
_TOKEN_OPTIONAL_STRING_SUFFIXES = (
    "token_id",
    "token_ref",
    "token_receipt_ref",
)

_QUEUE_REQUIRED_STRING_SUFFIXES = (
    "queue_job_id",
    "queue_job_state",
    "queue_append_only_event_ref",
    "queue_runner_receipt_ref",
)
_QUEUE_OPTIONAL_STRING_SUFFIXES = (
    "queue_id",
    "queue_job_ref",
    "queue_token_id",
    "queue_token_receipt_ref",
)

_FORBIDDEN_FIELDS = (
    "argv",
    "args",
    "actual_argv",
    "expected_argv",
    "resolved_argv",
    "raw_stdout",
    "raw_stderr",
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "command",
    "command_line",
    "command_text",
    "shell",
    "shell_command",
    "argv_override",
    "browser",
    "url",
    "network",
    "provider_api",
    "credentials",
    "production_autonomy",
    "consume_token",
    "revoke_token",
    "issue_token",
    "enqueue_job",
    "run_job",
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
    """Compare replay evidence without re-executing commands or mutating state."""

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
        _compare_runner_evidence(payload, failures)
        _compare_executable_sha256(payload, failures)
        _compare_metadata_group(
            payload,
            failures,
            required_string_suffixes=_TOKEN_REQUIRED_STRING_SUFFIXES,
            required_sha256_suffixes=_TOKEN_REQUIRED_SHA256_SUFFIXES,
            optional_string_suffixes=_TOKEN_OPTIONAL_STRING_SUFFIXES,
        )
        _compare_metadata_group(
            payload,
            failures,
            required_string_suffixes=_QUEUE_REQUIRED_STRING_SUFFIXES,
            required_sha256_suffixes=(),
            optional_string_suffixes=_QUEUE_OPTIONAL_STRING_SUFFIXES,
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
    for field in _REQUIRED_SHA256_FIELDS:
        if not _strict_sha256(payload.get(field)):
            failures.append(f"{field}_required")
    for field in ("expected_exit_code", "actual_exit_code"):
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{field}_must_be_int")
    _validate_executable_sha256(payload, failures)
    _validate_metadata_group(
        payload,
        failures,
        prefix="token",
        required_string_suffixes=_TOKEN_REQUIRED_STRING_SUFFIXES,
        required_sha256_suffixes=_TOKEN_REQUIRED_SHA256_SUFFIXES,
        optional_string_suffixes=_TOKEN_OPTIONAL_STRING_SUFFIXES,
    )
    _validate_metadata_group(
        payload,
        failures,
        prefix="queue",
        required_string_suffixes=_QUEUE_REQUIRED_STRING_SUFFIXES,
        required_sha256_suffixes=(),
        optional_string_suffixes=_QUEUE_OPTIONAL_STRING_SUFFIXES,
    )
    reexecution = payload.get("automatic_reexecution_allowed")
    if reexecution is not False:
        failures.append("automatic_reexecution_allowed_must_be_false")
    return failures


def _compare_runner_evidence(
    payload: Mapping[str, object],
    failures: list[str],
) -> None:
    for field in _RUNNER_COMPARISON_FIELDS:
        failure = f"{field}_mismatch"
        _compare_fields(
            payload,
            failures,
            expected=f"expected_{field}",
            actual=f"actual_{field}",
            failure=failure,
        )


def _validate_executable_sha256(
    payload: Mapping[str, object],
    failures: list[str],
) -> None:
    for side in ("expected", "actual"):
        sha_key = f"{side}_executable_sha256"
        reason_key = f"{side}_executable_sha256_unavailable_reason"
        sha_value = payload.get(sha_key)
        reason_value = payload.get(reason_key)
        has_sha = _strict_sha256(sha_value)
        has_reason = strict_nonempty_string(reason_value)
        if not has_sha and not has_reason:
            failures.append(f"{side}_executable_sha256_evidence_required")
        if sha_key in payload and sha_value is not None and not has_sha:
            failures.append(f"{sha_key}_required")
        if reason_key in payload and reason_value is not None and not has_reason:
            failures.append(f"{reason_key}_required")


def _compare_executable_sha256(
    payload: Mapping[str, object],
    failures: list[str],
) -> None:
    if (
        payload.get("expected_executable_sha256")
        != payload.get("actual_executable_sha256")
        or payload.get("expected_executable_sha256_unavailable_reason")
        != payload.get("actual_executable_sha256_unavailable_reason")
    ):
        failures.append("executable_sha256_mismatch")


def _validate_metadata_group(
    payload: Mapping[str, object],
    failures: list[str],
    *,
    prefix: str,
    required_string_suffixes: tuple[str, ...],
    required_sha256_suffixes: tuple[str, ...],
    optional_string_suffixes: tuple[str, ...],
) -> None:
    suffixes = (
        required_string_suffixes
        + required_sha256_suffixes
        + optional_string_suffixes
    )
    if not any(
        f"{side}_{suffix}" in payload
        for side in ("expected", "actual")
        for suffix in suffixes
    ):
        return
    for suffix in required_string_suffixes:
        _validate_paired_string(payload, failures, suffix=suffix)
    for suffix in required_sha256_suffixes:
        _validate_paired_sha256(payload, failures, suffix=suffix)
    for suffix in optional_string_suffixes:
        expected_key = f"expected_{suffix}"
        actual_key = f"actual_{suffix}"
        if expected_key in payload or actual_key in payload:
            _validate_paired_string(payload, failures, suffix=suffix)
    if prefix == "token" and not any(
        f"{side}_{suffix}" in payload
        for side in ("expected", "actual")
        for suffix in _TOKEN_OPTIONAL_STRING_SUFFIXES
    ):
        failures.append("token_reference_required")


def _validate_paired_string(
    payload: Mapping[str, object],
    failures: list[str],
    *,
    suffix: str,
) -> None:
    for side in ("expected", "actual"):
        key = f"{side}_{suffix}"
        if not strict_nonempty_string(payload.get(key)):
            failures.append(f"{key}_required")


def _validate_paired_sha256(
    payload: Mapping[str, object],
    failures: list[str],
    *,
    suffix: str,
) -> None:
    for side in ("expected", "actual"):
        key = f"{side}_{suffix}"
        if not _strict_sha256(payload.get(key)):
            failures.append(f"{key}_required")


def _compare_metadata_group(
    payload: Mapping[str, object],
    failures: list[str],
    *,
    required_string_suffixes: tuple[str, ...],
    required_sha256_suffixes: tuple[str, ...],
    optional_string_suffixes: tuple[str, ...],
) -> None:
    for suffix in required_string_suffixes + required_sha256_suffixes:
        _compare_fields(
            payload,
            failures,
            expected=f"expected_{suffix}",
            actual=f"actual_{suffix}",
            failure=f"{suffix}_mismatch",
        )
    for suffix in optional_string_suffixes:
        expected_key = f"expected_{suffix}"
        actual_key = f"actual_{suffix}"
        if expected_key in payload or actual_key in payload:
            _compare_fields(
                payload,
                failures,
                expected=expected_key,
                actual=actual_key,
                failure=f"{suffix}_mismatch",
            )


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
    receipt_material = _comparison_material(descriptor)
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
        "receipt_sha256_mismatch": "RECEIPT_MISMATCH",
        "environment_digest_mismatch": "ENVIRONMENT_MISMATCH",
        "environment_path_policy_id_mismatch": "ENVIRONMENT_MISMATCH",
        "command_id_mismatch": "COMMAND_MISMATCH",
        "argv_hash_mismatch": "ARGV_MISMATCH",
        "resolved_argv_hash_mismatch": "RESOLVED_ARGV_MISMATCH",
        "executable_path_mismatch": "EXECUTABLE_PATH_MISMATCH",
        "executable_realpath_mismatch": "EXECUTABLE_PATH_MISMATCH",
        "executable_sha256_mismatch": "EXECUTABLE_SHA256_MISMATCH",
        "executable_resolution_policy_id_mismatch": "RESOLUTION_POLICY_MISMATCH",
        "resolution_policy_digest_mismatch": "RESOLUTION_POLICY_MISMATCH",
        "stdout_sha256_mismatch": "OUTPUT_MISMATCH",
        "stderr_sha256_mismatch": "OUTPUT_MISMATCH",
        "output_digest_mismatch": "OUTPUT_MISMATCH",
        "exit_code_mismatch": "EXIT_CODE_MISMATCH",
    }
    present = [
        mismatch_classes[failure] for failure in failures if failure in mismatch_classes
    ]
    if any(failure.startswith("token_") for failure in failures):
        present.append("TOKEN_METADATA_MISMATCH")
    if any(failure.startswith("queue_") for failure in failures):
        present.append("QUEUE_METADATA_MISMATCH")
    if len(present) == 1:
        return present[0]
    if present:
        return "MULTIPLE_MISMATCHES"
    return "REPLAY_REJECTED"


def _is_validation_failure(failure: str) -> bool:
    return (
        failure.endswith("_required")
        or failure.endswith("_must_be_int")
        or failure.endswith("_must_be_false")
        or failure.endswith("_forbidden")
        or failure == "token_reference_required"
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


def _strict_sha256(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_SHA256_RE.match(value))


def _comparison_material(descriptor: Mapping[str, object]) -> dict[str, object]:
    keys = {
        "automatic_reexecution_allowed",
        "actual_exit_code",
        "candidate_receipt_id",
        "expected_exit_code",
        "replay_id",
        "source_receipt_id",
    }
    for field in _RUNNER_COMPARISON_FIELDS:
        keys.add(f"expected_{field}")
        keys.add(f"actual_{field}")
    for side in ("expected", "actual"):
        keys.add(f"{side}_executable_sha256")
        keys.add(f"{side}_executable_sha256_unavailable_reason")
        for suffix in (
            _TOKEN_REQUIRED_STRING_SUFFIXES
            + _TOKEN_REQUIRED_SHA256_SUFFIXES
            + _TOKEN_OPTIONAL_STRING_SUFFIXES
            + _QUEUE_REQUIRED_STRING_SUFFIXES
            + _QUEUE_OPTIONAL_STRING_SUFFIXES
        ):
            keys.add(f"{side}_{suffix}")
    return {key: descriptor.get(key) for key in sorted(keys) if key in descriptor}
