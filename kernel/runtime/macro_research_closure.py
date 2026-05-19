"""Deterministic closure report for safe macro research workflows."""

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
    "MacroResearchClosure",
    "build_macro_research_closure",
    "render_macro_research_closure_markdown",
]

_POLICY_VERSION = "macro-research-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_CLOSURE_GATES = (
    "research_note_contract_exists",
    "readme_exists",
    "evidence_pack_template_exists",
    "contradiction_pack_template_exists",
    "no_trade_reason_template_exists",
    "manual_decision_checklist_exists",
    "forbidden_outputs_include_required_boundaries",
    "final_decision_remains_manual",
)
_REQUIRED_FORBIDDEN_OUTPUTS = (
    "auto order execution",
    "broker/api execution",
    "leverage",
    "full-position instruction",
    "autonomous trading",
)
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = ("closure_gates",)
_LIST_FIELDS = ("workflow_docs", "forbidden_outputs", "blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class MacroResearchClosure:
    """Repository-ready safe macro research closure."""

    closure_id: str
    repository_url: str
    main_commit: str
    closure_gates: dict[str, object]
    workflow_docs: tuple[object, ...]
    forbidden_outputs: tuple[object, ...]
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
            "forbidden_outputs": list(self.forbidden_outputs),
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "workflow_docs": list(self.workflow_docs),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_macro_research_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> MacroResearchClosure:
    """Build a deterministic macro research closure from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="macro_research_closure_material",
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
        normalized["forbidden_outputs"],
        _REQUIRED_FORBIDDEN_OUTPUTS,
        error="forbidden_outputs_missing_required_boundary",
    )
    require_text_terms(
        normalized["workflow_docs"],
        ("final decision remains manual", "not a trading system"),
        error="workflow_docs_missing_manual_boundary",
    )

    closure = MacroResearchClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        closure_gates=gates,
        workflow_docs=tuple(normalized["workflow_docs"]),
        forbidden_outputs=tuple(normalized["forbidden_outputs"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_macro_research_closure_markdown(closure: MacroResearchClosure) -> str:
    """Render deterministic Markdown for macro research closure."""

    if not isinstance(closure, MacroResearchClosure):
        raise ValueError("closure_must_be_macro_research_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Macro Research Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Closure Gates", material["closure_gates"]),
            ("Workflow Docs", material["workflow_docs"]),
            ("Forbidden Outputs", material["forbidden_outputs"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
