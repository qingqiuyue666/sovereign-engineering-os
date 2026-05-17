"""Deterministic dry-run runtime runner foundation.

This module provides a deterministic, side-effect-free dry-run runner that
produces a verifiable runner receipt. It enforces a strict boundary:
- dry_run=true is required
- provider execution is rejected
- network execution is rejected
- production autonomy is rejected
- raw_prompt, raw_provider_response, secret_value are forbidden
- task_id, run_id, stage, policy_version, code_version, input_digest are validated
- the receipt is deterministic given the same inputs
- no provider calls, network, SQLite, or file mutation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "RunnerRejection",
    "RunnerReceipt",
    "run_dry_run",
    "validate_runner_input",
    "compute_output_digest",
    "produce_runner_receipt",
]

_DRY_RUN_REQUIRED_MESSAGE = "dry_run_must_be_true"
_PROVIDER_EXECUTION_REJECTED_MESSAGE = "provider_execution_rejected"
_NETWORK_EXECUTION_REJECTED_MESSAGE = "network_execution_rejected"
_PRODUCTION_AUTONOMY_REJECTED_MESSAGE = "production_autonomy_rejected"

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
)

_REQUIRED_FIELDS = (
    "task_id",
    "run_id",
    "stage",
    "policy_version",
    "code_version",
    "input_digest",
)

_RECEIPT_FIELDS = _REQUIRED_FIELDS + ("status", "output_digest")

_ALLOWED_STATUSES = ("accepted", "rejected")


class RunnerRejection(ValueError):
    """Raised when the runner input violates a policy boundary.

    The caller must treat this as a fail-closed governance event.
    """


@dataclass(frozen=True)
class RunnerReceipt:
    """Deterministic receipt produced by the dry-run runtime runner.

    The receipt is side-effect free and reproducible: given identical inputs,
    the same receipt is produced every time.
    """

    task_id: str
    run_id: str
    stage: str
    status: str
    policy_version: str
    code_version: str
    input_digest: str
    output_digest: str
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "status": self.status,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "failures": list(self.failures),
        }

    def accepted(self) -> bool:
        return self.status == "accepted"


def _canonical_json(payload: Any) -> str:
    """Deterministic JSON serialization for digest computation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    """Deterministic sha256 digest of a JSON-serializable payload."""
    return "sha256:" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_runner_input(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Validate runner input against policy boundaries.

    Returns a tuple of failure messages. An empty tuple means the input is valid.

    Checks (in order):
    1. dry_run must be True (required gate)
    2. provider flag must not be set
    3. network flag must not be set
    4. production_autonomy flag must not be set
    5. forbidden fields (raw_prompt, raw_provider_response, secret_value) must be absent
    6. required fields (task_id, run_id, stage, policy_version, code_version, input_digest)
       must be present and non-empty strings
    """
    failures: list[str] = []

    # Gate 1: dry_run must be True
    if payload.get("dry_run") is not True:
        failures.append(_DRY_RUN_REQUIRED_MESSAGE)

    # Gate 2: no provider execution
    if payload.get("provider"):
        failures.append(_PROVIDER_EXECUTION_REJECTED_MESSAGE)

    # Gate 3: no network execution
    if payload.get("network"):
        failures.append(_NETWORK_EXECUTION_REJECTED_MESSAGE)

    # Gate 4: no production autonomy
    if payload.get("production_autonomy"):
        failures.append(_PRODUCTION_AUTONOMY_REJECTED_MESSAGE)

    # Gate 5: forbidden fields
    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    # Gate 6: required fields validation
    for field in _REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None or not isinstance(value, str) or not value.strip():
            failures.append(f"{field}_required_nonempty_string")

    return tuple(failures)


def compute_output_digest(
    *,
    task_id: str,
    run_id: str,
    stage: str,
    policy_version: str,
    code_version: str,
    input_digest: str,
) -> str:
    """Compute a deterministic output digest from runner inputs.

    The digest is derived from the canonical JSON serialization of all input
    fields. This ensures that any change to inputs produces a different digest.
    """
    seed: dict[str, str] = {
        "code_version": code_version,
        "input_digest": input_digest,
        "policy_version": policy_version,
        "run_id": run_id,
        "stage": stage,
        "task_id": task_id,
    }
    return _digest_payload(seed)


def produce_runner_receipt(payload: Mapping[str, object]) -> RunnerReceipt:
    """Produce a deterministic runner receipt from a validated payload.

    If validation fails, the receipt has status="rejected" and output_digest is
    set to a deterministic rejection marker (not derived from invalid inputs).

    If validation passes, the receipt has status="accepted" and output_digest
    is computed deterministically from the input fields.
    """
    failures = validate_runner_input(payload)

    # Extract fields with safe defaults for the receipt even on rejection.
    task_id = str(payload.get("task_id", ""))
    run_id = str(payload.get("run_id", ""))
    stage = str(payload.get("stage", ""))
    policy_version = str(payload.get("policy_version", ""))
    code_version = str(payload.get("code_version", ""))
    input_digest = str(payload.get("input_digest", ""))

    if failures:
        output_digest = "sha256:" + hashlib.sha256(
            ("rejected:" + ":".join(sorted(failures))).encode("utf-8")
        ).hexdigest()
        return RunnerReceipt(
            task_id=task_id,
            run_id=run_id,
            stage=stage,
            status="rejected",
            policy_version=policy_version,
            code_version=code_version,
            input_digest=input_digest,
            output_digest=output_digest,
            failures=failures,
        )

    output_digest = compute_output_digest(
        task_id=task_id,
        run_id=run_id,
        stage=stage,
        policy_version=policy_version,
        code_version=code_version,
        input_digest=input_digest,
    )
    return RunnerReceipt(
        task_id=task_id,
        run_id=run_id,
        stage=stage,
        status="accepted",
        policy_version=policy_version,
        code_version=code_version,
        input_digest=input_digest,
        output_digest=output_digest,
        failures=(),
    )


def run_dry_run(payload: Mapping[str, object]) -> RunnerReceipt:
    """Entry point: run the deterministic dry-run runtime runner.

    This is the primary public API. It validates the input, computes the
    output digest, and returns a RunnerReceipt.

    Raises RunnerRejection if the payload is not a Mapping.
    All other validation failures are captured in the receipt with
    status="rejected".
    """
    if not isinstance(payload, Mapping):
        raise RunnerRejection("runner_input_must_be_a_mapping")
    return produce_runner_receipt(payload)
