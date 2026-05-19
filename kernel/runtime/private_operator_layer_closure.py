"""Deterministic private operator layer closure report."""

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
    require_valid_choice,
)

__all__ = [
    "PrivateOperatorLayerClosure",
    "build_private_operator_layer_closure",
    "render_private_operator_layer_closure_markdown",
]

_POLICY_VERSION = "private-operator-layer-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "daily_usage_path",
    "completion_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "operator_docs",
    "operator_rules",
    "handoff_packets",
    "review_forms",
    "task_intake_templates",
    "knowledge_indexes",
    "sprint_artifacts",
    "blocked_capabilities",
    "remaining_gaps",
    "rollback_notes",
)
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)
_REQUIRED_DOC_TERMS = (
    "operator command center",
    "current state",
    "operating rules",
    "blocked capabilities",
    "report gallery",
    "knowledge base index",
    "workspace hygiene",
    "current operator control pack",
)


@dataclass(frozen=True)
class PrivateOperatorLayerClosure:
    """Repository-ready current private operator control pack closure."""

    closure_id: str
    repository_url: str
    main_commit: str
    operator_docs: tuple[object, ...]
    operator_rules: tuple[object, ...]
    handoff_packets: tuple[object, ...]
    review_forms: tuple[object, ...]
    task_intake_templates: tuple[object, ...]
    knowledge_indexes: tuple[object, ...]
    sprint_artifacts: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    daily_usage_path: str
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
            "closure_id": self.closure_id,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "daily_usage_path": self.daily_usage_path,
            "handoff_packets": list(self.handoff_packets),
            "knowledge_indexes": list(self.knowledge_indexes),
            "main_commit": self.main_commit,
            "operator_docs": list(self.operator_docs),
            "operator_rules": list(self.operator_rules),
            "policy_version": self.policy_version,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "review_forms": list(self.review_forms),
            "rollback_notes": list(self.rollback_notes),
            "sprint_artifacts": list(self.sprint_artifacts),
            "task_intake_templates": list(self.task_intake_templates),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_private_operator_layer_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> PrivateOperatorLayerClosure:
    """Build a deterministic private operator layer closure object."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="private_operator_layer_closure_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(
        normalized["completion_decision"],
        field="completion_decision",
        allowed=_COMPLETION_DECISIONS,
    )
    require_text_terms(normalized, _REQUIRED_DOC_TERMS, error="operator_control_pack_missing_required_surface")
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "production autonomy", "trading automation", "houdini"),
        error="blocked_capabilities_missing_required_language",
    )

    closure = PrivateOperatorLayerClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        operator_docs=tuple(normalized["operator_docs"]),
        operator_rules=tuple(normalized["operator_rules"]),
        handoff_packets=tuple(normalized["handoff_packets"]),
        review_forms=tuple(normalized["review_forms"]),
        task_intake_templates=tuple(normalized["task_intake_templates"]),
        knowledge_indexes=tuple(normalized["knowledge_indexes"]),
        sprint_artifacts=tuple(normalized["sprint_artifacts"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        daily_usage_path=normalized["daily_usage_path"],
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_private_operator_layer_closure_markdown(closure: PrivateOperatorLayerClosure) -> str:
    """Render deterministic Markdown for the private operator layer closure."""

    if not isinstance(closure, PrivateOperatorLayerClosure):
        raise ValueError("closure_must_be_private_operator_layer_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Private Operator Layer Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("daily_usage_path", closure.daily_usage_path),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Operator Docs", material["operator_docs"]),
            ("Operator Rules", material["operator_rules"]),
            ("Handoff Packets", material["handoff_packets"]),
            ("Review Forms", material["review_forms"]),
            ("Task Intake Templates", material["task_intake_templates"]),
            ("Knowledge Indexes", material["knowledge_indexes"]),
            ("Sprint Artifacts", material["sprint_artifacts"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
