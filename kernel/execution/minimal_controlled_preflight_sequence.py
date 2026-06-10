"""Fixed minimal controlled preflight sequence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping

from kernel.execution.minimal_controlled_execution_contract import (
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
    POLICY_VERSION,
)
from kernel.execution.minimal_controlled_git_diff_check_runner import (
    MinimalControlledExecutionRunResult as GitDiffCheckResult,
    run_minimal_controlled_git_diff_check,
)
from kernel.execution.minimal_controlled_git_status_runner import (
    MinimalControlledExecutionRunResult as GitStatusResult,
    run_minimal_controlled_git_status,
)

__all__ = [
    "PREFLIGHT_ALLOWED_STATUSES",
    "PREFLIGHT_ORDER",
    "MINIMAL_CONTROLLED_PREFLIGHT_RESULT_FIELDS",
    "MinimalControlledPreflightResult",
    "minimal_controlled_preflight_result_hash",
    "run_minimal_controlled_preflight_sequence",
]

PREFLIGHT_ORDER = ("git_status_short", "git_diff_check")
PREFLIGHT_ALLOWED_STATUSES = frozenset(
    {
        "PREFLIGHT_PASSED",
        "PREFLIGHT_FAILED",
        "PREFLIGHT_NOT_ATTEMPTED",
        "PREFLIGHT_PARTIAL_FAILURE",
    }
)
MINIMAL_CONTROLLED_PREFLIGHT_RESULT_FIELDS = (
    "preflight_id",
    "task_id",
    "run_id",
    "ordered_command_ids",
    "child_request_hashes",
    "child_decision_hashes",
    "child_admission_hashes",
    "child_receipt_hashes",
    "child_failure_bundle_hashes",
    "child_verifier_input_hashes",
    "child_verifier_binding_hashes",
    "pre_snapshot_hashes",
    "post_snapshot_hashes",
    "overall_status",
    "failure_reasons",
    "execution_performed",
    "preflight_result_hash",
)
_ALLOWED_PAYLOAD_FIELDS = frozenset(
    {
        "preflight_id",
        "task_id",
        "run_id",
        "requested_at",
        "requester",
        "use_case_ids",
        "snapshot_ref",
        "caller_intent",
        "approval_token_id",
    }
)
_FORBIDDEN_PREFLIGHT_FIELDS = frozenset(
    {
        "command_id",
        "command_ids",
        "commands",
        "steps",
        "sequence",
        "tasks",
        "graph",
        "retry",
        "retries",
        "parallel",
        "background",
    }
)


@dataclass(frozen=True)
class MinimalControlledPreflightResult:
    preflight_id: str
    task_id: str
    run_id: str
    ordered_command_ids: tuple[str, ...]
    child_request_hashes: tuple[str, ...]
    child_decision_hashes: tuple[str, ...]
    child_admission_hashes: tuple[str, ...]
    child_receipt_hashes: tuple[str, ...]
    child_failure_bundle_hashes: tuple[str, ...]
    child_verifier_input_hashes: tuple[str, ...]
    child_verifier_binding_hashes: tuple[str, ...]
    pre_snapshot_hashes: tuple[str, ...]
    post_snapshot_hashes: tuple[str, ...]
    overall_status: str
    failure_reasons: tuple[str, ...]
    execution_performed: bool
    preflight_result_hash: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "ordered_command_ids",
            "child_request_hashes",
            "child_decision_hashes",
            "child_admission_hashes",
            "child_receipt_hashes",
            "child_failure_bundle_hashes",
            "child_verifier_input_hashes",
            "child_verifier_binding_hashes",
            "pre_snapshot_hashes",
            "post_snapshot_hashes",
            "failure_reasons",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if self.ordered_command_ids != PREFLIGHT_ORDER:
            raise ValueError("preflight_order_mismatch")
        if self.overall_status not in PREFLIGHT_ALLOWED_STATUSES:
            raise ValueError("preflight_status_invalid")
        if not isinstance(self.execution_performed, bool):
            raise ValueError("execution_performed_must_be_bool")
        expected = minimal_controlled_preflight_result_hash(self)
        if self.preflight_result_hash and self.preflight_result_hash != expected:
            raise ValueError("preflight_result_hash_mismatch")
        object.__setattr__(self, "preflight_result_hash", expected)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_minimal_controlled_preflight_sequence(
    payload: Mapping[str, object],
) -> MinimalControlledPreflightResult:
    data = _validated_preflight_payload(payload)
    child_results: list[GitStatusResult | GitDiffCheckResult] = []
    for command_id in PREFLIGHT_ORDER:
        request = _child_request(data, command_id)
        if command_id == "git_status_short":
            child_results.append(run_minimal_controlled_git_status(request))
        else:
            child_results.append(run_minimal_controlled_git_diff_check(request))
    return _preflight_result(data, child_results)


def minimal_controlled_preflight_result_hash(
    result: MinimalControlledPreflightResult | Mapping[str, object],
) -> str:
    data = result.as_dict() if isinstance(result, MinimalControlledPreflightResult) else dict(result)
    data.pop("preflight_result_hash", None)
    return "sha256:" + _sha256_text(_canonical_json(_json_ready(data)))


def _validated_preflight_payload(payload: Mapping[str, object]) -> dict[str, object]:
    data = dict(payload)
    forbidden = sorted(
        (EXECUTION_REQUEST_FORBIDDEN_FIELDS | _FORBIDDEN_PREFLIGHT_FIELDS).intersection(data)
    )
    if forbidden:
        raise ValueError("preflight_field_forbidden:" + ",".join(forbidden))
    extra = sorted(set(data) - _ALLOWED_PAYLOAD_FIELDS)
    if extra:
        raise ValueError("preflight_field_not_allowed:" + ",".join(extra))
    for field_name in ("preflight_id", "task_id", "run_id", "requested_at", "requester"):
        if not isinstance(data.get(field_name), str) or not data[field_name]:
            raise ValueError(field_name + "_required")
    if "use_case_ids" in data:
        use_case_ids = data["use_case_ids"]
        if not isinstance(use_case_ids, (list, tuple)) or isinstance(use_case_ids, (str, bytes)):
            raise ValueError("use_case_ids_must_be_sequence")
        if not all(isinstance(item, str) and item for item in use_case_ids):
            raise ValueError("use_case_ids_must_be_non_empty_strings")
    if "approval_token_id" in data and not isinstance(data["approval_token_id"], str):
        raise ValueError("approval_token_id_must_be_string")
    for optional_string in ("snapshot_ref", "caller_intent"):
        if optional_string in data and (
            not isinstance(data[optional_string], str) or not data[optional_string]
        ):
            raise ValueError(optional_string + "_must_be_non_empty_string")
    return data


def _child_request(data: Mapping[str, object], command_id: str) -> dict[str, object]:
    preflight_id = str(data["preflight_id"])
    requested_at = str(data["requested_at"])
    return {
        "approval_token_id": str(data.get("approval_token_id", "")),
        "caller_intent": str(data.get("caller_intent", "run fixed minimal controlled preflight")),
        "command_id": command_id,
        "policy_version": POLICY_VERSION,
        "request_id": preflight_id + "-" + command_id.replace("_", "-"),
        "requested_at": requested_at,
        "requester": str(data["requester"]),
        "run_id": str(data["run_id"]),
        "snapshot_ref": str(data.get("snapshot_ref", "preflight:" + preflight_id)),
        "task_id": str(data["task_id"]),
        "use_case_ids": tuple(data.get("use_case_ids", ("uc_001_codex_pr_preflight",))),
    }


def _preflight_result(
    data: Mapping[str, object],
    child_results: tuple[GitStatusResult | GitDiffCheckResult, ...] | list[GitStatusResult | GitDiffCheckResult],
) -> MinimalControlledPreflightResult:
    children = tuple(child_results)
    failures = _failure_reasons(children)
    execution_count = sum(1 for child in children if child.execution_performed)
    if not children:
        overall_status = "PREFLIGHT_NOT_ATTEMPTED"
    elif failures and execution_count != len(children):
        overall_status = "PREFLIGHT_PARTIAL_FAILURE"
    elif failures:
        overall_status = "PREFLIGHT_FAILED"
    else:
        overall_status = "PREFLIGHT_PASSED"
    return MinimalControlledPreflightResult(
        preflight_id=str(data["preflight_id"]),
        task_id=str(data["task_id"]),
        run_id=str(data["run_id"]),
        ordered_command_ids=PREFLIGHT_ORDER,
        child_request_hashes=tuple(child.request.request_hash for child in children),
        child_decision_hashes=tuple(child.policy_decision.decision_hash for child in children),
        child_admission_hashes=tuple(
            child.admission_record.admission_record_hash for child in children
        ),
        child_receipt_hashes=tuple(
            child.receipt.receipt_hash if child.receipt is not None else "" for child in children
        ),
        child_failure_bundle_hashes=tuple(
            child.failure_bundle.failure_bundle_hash if child.failure_bundle is not None else ""
            for child in children
        ),
        child_verifier_input_hashes=tuple(
            child.verifier_input.verifier_input_hash if child.verifier_input is not None else ""
            for child in children
        ),
        child_verifier_binding_hashes=tuple(
            child.verifier_binding.verifier_binding_hash if child.verifier_binding is not None else ""
            for child in children
        ),
        pre_snapshot_hashes=tuple(child.pre_snapshot.snapshot_hash for child in children),
        post_snapshot_hashes=tuple(child.post_snapshot.snapshot_hash for child in children),
        overall_status=overall_status,
        failure_reasons=failures,
        execution_performed=execution_count > 0,
    )


def _failure_reasons(
    children: tuple[GitStatusResult | GitDiffCheckResult, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    for child in children:
        if child.failure_bundle is not None:
            reasons.extend(child.failure_bundle.failure_reasons)
        if not child.execution_performed:
            reasons.append(child.request.command_id + ":EXECUTION_NOT_PERFORMED")
    return tuple(reasons)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
