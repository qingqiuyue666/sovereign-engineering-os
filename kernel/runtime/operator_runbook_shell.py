"""Non-executing symbolic runbook shell for operator queue items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_nonempty_string
from kernel.runtime.operator_work_queue import OperatorWorkQueueItem

__all__ = ["OperatorRunbookShellPlan", "build_operator_runbook_shell"]

_POLICY_VERSION = "operator-runbook-shell-v1"
_CODE_VERSION = "0.1.0"
_STEP_MAP = {
    "pending_review": (
        "operator.review.open_packet",
        "operator.review.compare_promotion_gate",
        "operator.review.record_decision",
    ),
    "approved": (
        "operator.approval.verify_receipt",
        "operator.approval.prepare_next_manual_stage",
    ),
    "rejected": (
        "operator.rejection.verify_receipt",
        "operator.rollback.review_symbolic_plan",
    ),
    "blocked": (
        "operator.blocked.inspect_gate",
        "operator.blocked.keep_execution_disabled",
    ),
}
_COMMAND_MARKERS = (
    " ",
    "\t",
    "\n",
    ";",
    "|",
    "&",
    "$",
    "`",
    ">",
    "<",
    "/",
    "\\",
    "(",
    ")",
)
_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)


@dataclass(frozen=True)
class OperatorRunbookShellPlan:
    runbook_id: str
    step_ids: tuple[str, ...]
    queue_item_count: int
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "policy_version": self.policy_version,
            "queue_item_count": self.queue_item_count,
            "runbook_id": self.runbook_id,
            "step_ids": list(self.step_ids),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_runbook_shell(
    *,
    runbook_id: str,
    queue_items: tuple[OperatorWorkQueueItem, ...],
    extra_symbolic_step_ids: tuple[str, ...] = (),
    operator_metadata: dict[str, object] | None = None,
    observed_at: str | None = None,
) -> OperatorRunbookShellPlan:
    """Map queue items to symbolic manual runbook step IDs only."""

    if not strict_nonempty_string(runbook_id):
        raise ValueError("runbook_id_must_be_nonempty_string")
    if not isinstance(queue_items, tuple):
        raise ValueError("queue_items_must_be_tuple")
    if not isinstance(extra_symbolic_step_ids, tuple):
        raise ValueError("extra_symbolic_step_ids_must_be_tuple")
    _reject_forbidden_fields(operator_metadata or {})
    observed = _observed_at(observed_at)

    steps: list[str] = []
    for item in queue_items:
        if not isinstance(item, OperatorWorkQueueItem):
            raise ValueError("queue_item_must_be_operator_work_queue_item")
        status_steps = _STEP_MAP.get(item.queue_status)
        if status_steps is None:
            raise ValueError("unsupported_queue_status")
        steps.extend(status_steps)
    steps.extend(extra_symbolic_step_ids)
    for step_id in steps:
        _validate_symbolic_step_id(step_id)

    plan = OperatorRunbookShellPlan(
        runbook_id=runbook_id,
        step_ids=tuple(steps),
        queue_item_count=len(queue_items),
        content_hash="",
        observed_at=observed,
    )
    return OperatorRunbookShellPlan(
        runbook_id=plan.runbook_id,
        step_ids=plan.step_ids,
        queue_item_count=plan.queue_item_count,
        policy_version=plan.policy_version,
        code_version=plan.code_version,
        content_hash=digest_payload(plan.deterministic_material()),
        observed_at=plan.observed_at,
    )


def _validate_symbolic_step_id(step_id: str) -> None:
    if not strict_nonempty_string(step_id):
        raise ValueError("step_id_must_be_nonempty_string")
    lowered = step_id.lower()
    if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
        raise ValueError("forbidden_step_id")
    if any(marker in step_id for marker in _COMMAND_MARKERS):
        raise ValueError("step_id_must_be_symbolic")
    if not all(char.islower() or char.isdigit() or char in {"_", "."} for char in step_id):
        raise ValueError("step_id_must_be_lowercase_symbolic")


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError("forbidden_field_present")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _reject_forbidden_fields(nested)


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
