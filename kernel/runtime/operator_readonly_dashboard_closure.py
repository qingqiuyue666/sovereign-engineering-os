"""Deterministic closure report for the read-only operator dashboard."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    require_bool_gate_map,
    require_complete_has_required_gates,
    require_text_terms,
)
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)

__all__ = [
    "OperatorReadonlyDashboardClosure",
    "build_operator_readonly_dashboard_closure",
    "render_operator_readonly_dashboard_closure_markdown",
]

_POLICY_VERSION = "operator-readonly-dashboard-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_CLOSURE_GATES = (
    "dashboard_contract_exists",
    "generated_dashboard_exists",
    "usage_doc_exists",
    "latest_reports_listed",
    "registries_listed",
    "blocked_capabilities_listed",
    "verification_commands_listed",
    "no_execution_runner_behavior",
    "no_server_behavior",
    "no_gui_behavior",
    "no_houdini_vfx_execution_in_this_slice",
)
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "dashboard_path",
    "usage_doc_path",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("closure_gates",)
_LIST_FIELDS = ("blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class OperatorReadonlyDashboardClosure:
    """Repository-ready read-only dashboard closure."""

    closure_id: str
    repository_url: str
    main_commit: str
    dashboard_path: str
    usage_doc_path: str
    closure_gates: dict[str, object]
    blocked_capabilities: tuple[object, ...]
    completion_decision: str
    remaining_gaps: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities": list(self.blocked_capabilities),
            "closure_gates": self.closure_gates,
            "closure_id": self.closure_id,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "dashboard_path": self.dashboard_path,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "usage_doc_path": self.usage_doc_path,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_readonly_dashboard_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorReadonlyDashboardClosure:
    """Build a deterministic dashboard closure from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operator_readonly_dashboard_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(
        normalized["completion_decision"],
        field="completion_decision",
        allowed=_COMPLETION_DECISIONS,
    )
    gates = require_bool_gate_map(
        normalized["closure_gates"],
        field="closure_gates",
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    require_complete_has_required_gates(
        normalized["completion_decision"],
        gates=gates,
        required_gates=_REQUIRED_CLOSURE_GATES,
    )
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "production autonomy", "trading automation", "houdini/vfx"),
        error="blocked_capabilities_missing_required_language",
    )

    closure = OperatorReadonlyDashboardClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        dashboard_path=normalized["dashboard_path"],
        usage_doc_path=normalized["usage_doc_path"],
        closure_gates=gates,
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_operator_readonly_dashboard_closure_markdown(closure: OperatorReadonlyDashboardClosure) -> str:
    """Render deterministic Markdown for read-only dashboard closure."""

    if not isinstance(closure, OperatorReadonlyDashboardClosure):
        raise ValueError("closure_must_be_operator_readonly_dashboard_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Operator Read-Only Dashboard Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("dashboard_path", closure.dashboard_path),
            ("usage_doc_path", closure.usage_doc_path),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Closure Gates", material["closure_gates"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
