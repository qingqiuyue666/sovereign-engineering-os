"""Failure taxonomy, retry execution, and convergence decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creative.common import write_json
from execution_plane.runtime.patch_repair_policy import PatchRepairPolicy
from execution_plane.runtime.retry_budget import RetryBudget

FAILURE_CONVERGENCE_SCHEMA_VERSION = "seos.failure_convergence.v1"

RETRYABLE_FAILURE_CODES = frozenset(
    {
        "TIMEOUT",
        "SERVICE_UNAVAILABLE",
        "APP_NOT_RUNNING",
        "API_ATTACH_FAILED",
        "LICENSE_BLOCKED",
        "AUTO_PROVISION_FAILED",
    }
)
PATCH_REPAIRABLE_FAILURE_CODES = frozenset(
    {
        "EXECUTION_FAILED",
        "PROCESS_EXIT_NONZERO",
        "NONZERO_EXIT",
        "SCHEMA_INVALID",
        "OUTPUT_INVALID",
    }
)
DEPENDENCY_FAILURE_CODES = frozenset(
    {
        "DEPENDENCY_FAILED",
        "DEPENDENCY_BLOCKED",
        "ENV_NOT_FOUND",
        "ADAPTER_UNAVAILABLE",
        "METHOD_NOT_ALLOWED",
    }
)
OUTPUT_TERMINAL_FAILURE_CODES = frozenset({"OUTPUT_MISSING", "PROJECT_NOT_FOUND"})


@dataclass(frozen=True)
class FailureClassification:
    failure_code: str | None
    category: str
    retryable: bool
    patch_repairable: bool
    terminal: bool
    repair_hint: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "failure_code": self.failure_code,
            "category": self.category,
            "retryable": self.retryable,
            "patch_repairable": self.patch_repairable,
            "terminal": self.terminal,
            "repair_hint": dict(self.repair_hint),
        }


RuntimeDispatch = Callable[[Mapping[str, Any], Mapping[str, Any] | None], dict[str, Any]]


def classify_failure(result: Mapping[str, Any]) -> FailureClassification:
    status = str(result.get("status") or "UNKNOWN")
    if status == "SUCCEEDED":
        return FailureClassification(
            failure_code=None,
            category="success",
            retryable=False,
            patch_repairable=False,
            terminal=True,
            repair_hint={"action": "none", "reason": "execution_succeeded"},
        )
    failure_code = _extract_failure_code(result)
    retryable = failure_code in RETRYABLE_FAILURE_CODES
    patch_repairable = failure_code in PATCH_REPAIRABLE_FAILURE_CODES
    if failure_code in DEPENDENCY_FAILURE_CODES:
        category = "dependency_or_environment"
        hint = {"action": "repair_environment_or_dependency", "retry_after_fix": True}
    elif retryable:
        category = "transient_retryable"
        hint = {"action": "retry_after_backoff", "requires_operator": False}
    elif patch_repairable:
        category = "code_or_schema_repairable"
        hint = {"action": "create_patch_repair_job", "requires_policy": "patch_repair.enabled"}
    elif failure_code in OUTPUT_TERMINAL_FAILURE_CODES:
        category = "terminal_output_or_project"
        hint = {"action": "inspect_outputs_or_project", "retry_after_fix": True}
    else:
        category = "terminal_unknown"
        hint = {"action": "inspect_failure_bundle", "retry_after_fix": True}
    return FailureClassification(
        failure_code=failure_code,
        category=category,
        retryable=retryable,
        patch_repairable=patch_repairable,
        terminal=not retryable and not patch_repairable,
        repair_hint=hint,
    )


def convergence_decision(
    *,
    result: Mapping[str, Any],
    attempt: int,
    token: Mapping[str, Any],
) -> dict[str, Any]:
    classification = classify_failure(result)
    retry_budget = RetryBudget.from_token(token)
    patch_policy = PatchRepairPolicy.from_token(token)
    next_attempt = attempt + 1
    if result.get("status") == "SUCCEEDED":
        decision = "succeeded"
        terminal_classifier = "TERMINAL_SUCCEEDED"
    elif classification.retryable and retry_budget.attempt_allowed(next_attempt):
        decision = "retry_after_backoff"
        terminal_classifier = "RETRY_PENDING"
    elif classification.patch_repairable and patch_policy.can_generate_patch():
        decision = "patch_repair_recommended"
        terminal_classifier = "PATCH_REPAIR_RECOMMENDED"
    else:
        decision = "no_retry_terminal"
        terminal_classifier = "TERMINAL_FAILED"
    return {
        "schema_version": FAILURE_CONVERGENCE_SCHEMA_VERSION,
        "attempt": attempt,
        "next_attempt": next_attempt if decision == "retry_after_backoff" else None,
        "max_attempts": retry_budget.max_attempts,
        "retry_enabled": retry_budget.enabled,
        "backoff_seconds": retry_budget.backoff_seconds,
        "decision": decision,
        "terminal_classifier": terminal_classifier,
        "classification": classification.as_dict(),
        "repair_hint": _repair_hint(classification, patch_policy),
    }


def execute_with_retry(
    *,
    permit: Mapping[str, Any],
    payload: Mapping[str, Any] | None,
    dispatch: RuntimeDispatch,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    attempt = 1
    while True:
        result = dict(dispatch(permit, payload))
        decision = convergence_decision(result=result, attempt=attempt, token=permit)
        attempts.append(
            {
                "attempt": attempt,
                "status": result.get("status"),
                "failure_code": decision["classification"]["failure_code"],
                "decision": decision["decision"],
                "terminal_classifier": decision["terminal_classifier"],
            }
        )
        if decision["decision"] != "retry_after_backoff":
            result["attempt_count"] = attempt
            result["retry_records"] = attempts
            result["failure_classification"] = decision["classification"]
            result["convergence_decision"] = decision
            _write_convergence_receipts(permit, attempts, decision)
            return result
        attempt += 1


def _extract_failure_code(result: Mapping[str, Any]) -> str:
    policy_blocks = result.get("policy_blocks")
    if isinstance(policy_blocks, list) and policy_blocks:
        return str(policy_blocks[0])
    failure_summary = str(result.get("failure_summary") or "")
    if ":" in failure_summary:
        prefix = failure_summary.split(":", 1)[0].strip()
        if prefix:
            return prefix
    status = str(result.get("status") or "")
    if status == "TIMED_OUT":
        return "TIMEOUT"
    if status == "BLOCKED":
        return "PREFLIGHT_FAILED"
    return "EXECUTION_FAILED"


def _repair_hint(classification: FailureClassification, policy: PatchRepairPolicy) -> dict[str, Any]:
    hint = dict(classification.repair_hint)
    hint["patch_repair_policy_enabled"] = policy.enabled
    hint["patch_repair_available"] = classification.patch_repairable and policy.can_generate_patch()
    hint["allowed_tools"] = list(policy.allowed_tools)
    hint["auto_apply"] = policy.auto_apply
    return hint


def _write_convergence_receipts(
    permit: Mapping[str, Any],
    attempts: list[dict[str, Any]],
    decision: Mapping[str, Any],
) -> None:
    output_root = Path(str(permit.get("allowed_output_root", "")))
    if not output_root:
        return
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(
        output_root / "retry_records.json",
        {
            "schema_version": "seos.retry_records.v1",
            "permit_id": permit.get("permit_id"),
            "attempts": attempts,
        },
    )
    write_json(output_root / "failure_convergence.json", decision)
