"""Deterministic private operator daily loop report."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import require_text_terms
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
)

__all__ = [
    "OperatorDailyLoop",
    "build_operator_daily_loop",
    "render_operator_daily_loop_markdown",
]

_POLICY_VERSION = "operator-daily-loop-v1"
_CODE_VERSION = "0.1.0"
_STRING_FIELDS = (
    "loop_id",
    "date_label",
    "repository_url",
    "main_commit",
    "current_phase",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "today_focus",
    "completed_recently",
    "active_constraints",
    "blocked_capabilities",
    "current_risks",
    "next_actions",
    "stop_conditions",
    "verification_required",
    "rollback_notes",
)


@dataclass(frozen=True)
class OperatorDailyLoop:
    """Repository-ready daily operator loop report."""

    loop_id: str
    date_label: str
    repository_url: str
    main_commit: str
    current_phase: str
    today_focus: tuple[object, ...]
    completed_recently: tuple[object, ...]
    active_constraints: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    current_risks: tuple[object, ...]
    next_actions: tuple[object, ...]
    stop_conditions: tuple[object, ...]
    verification_required: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "active_constraints": list(self.active_constraints),
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "completed_recently": list(self.completed_recently),
            "current_phase": self.current_phase,
            "current_risks": list(self.current_risks),
            "date_label": self.date_label,
            "loop_id": self.loop_id,
            "main_commit": self.main_commit,
            "next_actions": list(self.next_actions),
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "stop_conditions": list(self.stop_conditions),
            "today_focus": list(self.today_focus),
            "verification_required": list(self.verification_required),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_daily_loop(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorDailyLoop:
    """Build a deterministic daily loop from caller-provided material."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operator_daily_loop_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "production autonomy", "trading automation", "houdini/vfx"),
        error="blocked_capabilities_missing_required_language",
    )

    loop = OperatorDailyLoop(
        loop_id=normalized["loop_id"],
        date_label=normalized["date_label"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        current_phase=normalized["current_phase"],
        today_focus=tuple(normalized["today_focus"]),
        completed_recently=tuple(normalized["completed_recently"]),
        active_constraints=tuple(normalized["active_constraints"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        current_risks=tuple(normalized["current_risks"]),
        next_actions=tuple(normalized["next_actions"]),
        stop_conditions=tuple(normalized["stop_conditions"]),
        verification_required=tuple(normalized["verification_required"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(loop, content_hash=compute_content_hash(loop.deterministic_material()))


def render_operator_daily_loop_markdown(loop: OperatorDailyLoop) -> str:
    """Render deterministic Markdown for the daily loop."""

    if not isinstance(loop, OperatorDailyLoop):
        raise ValueError("loop_must_be_operator_daily_loop")
    material = loop.deterministic_material()
    return render_markdown(
        "Operator Daily Loop Report",
        metadata_rows=(
            ("loop_id", loop.loop_id),
            ("date_label", loop.date_label),
            ("repository_url", loop.repository_url),
            ("main_commit", loop.main_commit),
            ("current_phase", loop.current_phase),
            ("policy_version", loop.policy_version),
            ("code_version", loop.code_version),
            ("content_hash", loop.content_hash),
            ("observed_at", loop.observed_at),
        ),
        sections=(
            ("Today Focus", material["today_focus"]),
            ("Completed Recently", material["completed_recently"]),
            ("Active Constraints", material["active_constraints"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Current Risks", material["current_risks"]),
            ("Next Actions", material["next_actions"]),
            ("Stop Conditions", material["stop_conditions"]),
            ("Verification Required", material["verification_required"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
