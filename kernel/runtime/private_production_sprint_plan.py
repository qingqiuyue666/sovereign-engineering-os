"""Deterministic 7-day private production sprint plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_exact_number,
    require_list_fields,
    require_string_fields,
)

__all__ = [
    "PrivateProductionSprintPlan",
    "build_private_production_sprint_plan",
    "render_private_production_sprint_plan_markdown",
]

_POLICY_VERSION = "private-production-sprint-plan-v1"
_CODE_VERSION = "0.1.0"

_STRING_FIELDS = ("sprint_id", "sprint_name", "policy_version", "code_version")
_LIST_FIELDS = (
    "daily_plan",
    "deliverables",
    "verification_plan",
    "stop_conditions",
    "blocked_actions",
    "review_cadence",
    "rollback_plan",
)


@dataclass(frozen=True)
class PrivateProductionSprintPlan:
    """Repository-ready 7-day private production sprint plan."""

    sprint_id: str
    sprint_name: str
    duration_days: int
    daily_plan: tuple[object, ...]
    deliverables: tuple[object, ...]
    verification_plan: tuple[object, ...]
    stop_conditions: tuple[object, ...]
    blocked_actions: tuple[object, ...]
    review_cadence: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_actions": list(self.blocked_actions),
            "code_version": self.code_version,
            "daily_plan": list(self.daily_plan),
            "deliverables": list(self.deliverables),
            "duration_days": self.duration_days,
            "policy_version": self.policy_version,
            "review_cadence": list(self.review_cadence),
            "rollback_plan": list(self.rollback_plan),
            "sprint_id": self.sprint_id,
            "sprint_name": self.sprint_name,
            "stop_conditions": list(self.stop_conditions),
            "verification_plan": list(self.verification_plan),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_private_production_sprint_plan(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> PrivateProductionSprintPlan:
    """Build a deterministic 7-day private production sprint plan."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="private_production_sprint_plan_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    if "duration_days" not in normalized:
        raise ValueError("duration_days_missing")
    require_exact_number(normalized["duration_days"], field="duration_days", expected=7)
    require_list_fields(normalized, _LIST_FIELDS)
    if len(normalized["daily_plan"]) != 7:
        raise ValueError("daily_plan_must_have_7_days")

    sprint = PrivateProductionSprintPlan(
        sprint_id=normalized["sprint_id"],
        sprint_name=normalized["sprint_name"],
        duration_days=normalized["duration_days"],
        daily_plan=tuple(normalized["daily_plan"]),
        deliverables=tuple(normalized["deliverables"]),
        verification_plan=tuple(normalized["verification_plan"]),
        stop_conditions=tuple(normalized["stop_conditions"]),
        blocked_actions=tuple(normalized["blocked_actions"]),
        review_cadence=tuple(normalized["review_cadence"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(sprint)


def render_private_production_sprint_plan_markdown(plan: PrivateProductionSprintPlan) -> str:
    """Render private production sprint plan Markdown deterministically."""

    if not isinstance(plan, PrivateProductionSprintPlan):
        raise ValueError("plan_must_be_private_production_sprint_plan")
    material = plan.deterministic_material()
    return render_markdown(
        "Private Production Sprint Plan v1",
        metadata_rows=(
            ("sprint_id", plan.sprint_id),
            ("sprint_name", plan.sprint_name),
            ("duration_days", plan.duration_days),
            ("policy_version", plan.policy_version),
            ("code_version", plan.code_version),
            ("content_hash", plan.content_hash),
            ("observed_at", plan.observed_at),
        ),
        sections=(
            ("Daily Plan", material["daily_plan"]),
            ("Deliverables", material["deliverables"]),
            ("Verification Plan", material["verification_plan"]),
            ("Stop Conditions", material["stop_conditions"]),
            ("Blocked Actions", material["blocked_actions"]),
            ("Review Cadence", material["review_cadence"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(plan: PrivateProductionSprintPlan) -> PrivateProductionSprintPlan:
    return PrivateProductionSprintPlan(
        sprint_id=plan.sprint_id,
        sprint_name=plan.sprint_name,
        duration_days=plan.duration_days,
        daily_plan=plan.daily_plan,
        deliverables=plan.deliverables,
        verification_plan=plan.verification_plan,
        stop_conditions=plan.stop_conditions,
        blocked_actions=plan.blocked_actions,
        review_cadence=plan.review_cadence,
        rollback_plan=plan.rollback_plan,
        policy_version=plan.policy_version,
        code_version=plan.code_version,
        content_hash=compute_content_hash(plan.deterministic_material()),
        observed_at=plan.observed_at,
    )
