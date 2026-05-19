"""Deterministic non-Houdini engineering foundation closure report."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    require_bool_gate_map,
    require_complete_has_no_status_violation,
    require_complete_has_required_gates,
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
    "EngineeringFoundationClosure",
    "build_engineering_foundation_closure",
    "render_engineering_foundation_closure_markdown",
]

_POLICY_VERSION = "engineering-foundation-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_FOUNDATION_GATES = (
    "tracer_bullet_green",
    "schemas_green",
    "acceptance_green",
    "make_ci_green",
    "git_diff_check_clean",
    "git_status_clean",
    "root_integrity_preserved",
    "makefile_unchanged_unless_authorized",
    "root_readme_unchanged_unless_authorized",
    "health_gate_wiring_unchanged_unless_authorized",
    "blocked_capabilities_preserved",
    "no_provider_execution",
    "no_production_autonomy",
    "no_financial_execution",
    "no_trading_automation",
    "no_houdini_vfx_execution_in_this_slice",
)
_STRING_FIELDS = (
    "closure_id",
    "repository_url",
    "main_commit",
    "branch",
    "completion_decision",
    "policy_version",
    "code_version",
)
_DICT_FIELDS = (
    "foundation_gates",
    "verification_matrix",
    "protected_file_status",
    "root_integrity_status",
    "ci_status",
    "blocked_capability_status",
)
_LIST_FIELDS = ("remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class EngineeringFoundationClosure:
    """Repository-ready closure contract for the engineering foundation."""

    closure_id: str
    repository_url: str
    main_commit: str
    branch: str
    foundation_gates: dict[str, object]
    verification_matrix: dict[str, object]
    protected_file_status: dict[str, object]
    root_integrity_status: dict[str, object]
    ci_status: dict[str, object]
    blocked_capability_status: dict[str, object]
    completion_decision: str
    remaining_gaps: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capability_status": self.blocked_capability_status,
            "branch": self.branch,
            "ci_status": self.ci_status,
            "closure_id": self.closure_id,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "foundation_gates": self.foundation_gates,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "protected_file_status": self.protected_file_status,
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "root_integrity_status": self.root_integrity_status,
            "verification_matrix": self.verification_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_engineering_foundation_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> EngineeringFoundationClosure:
    """Build a deterministic closure object from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="engineering_foundation_closure_material",
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
        normalized["foundation_gates"],
        field="foundation_gates",
        required_gates=_REQUIRED_FOUNDATION_GATES,
    )
    require_complete_has_required_gates(
        normalized["completion_decision"],
        gates=gates,
        required_gates=_REQUIRED_FOUNDATION_GATES,
    )
    require_complete_has_no_status_violation(
        normalized["completion_decision"],
        status=normalized["blocked_capability_status"],
        error="blocked_capability_violation_blocks_complete",
    )

    closure = EngineeringFoundationClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch=normalized["branch"],
        foundation_gates=gates,
        verification_matrix=normalized["verification_matrix"],
        protected_file_status=normalized["protected_file_status"],
        root_integrity_status=normalized["root_integrity_status"],
        ci_status=normalized["ci_status"],
        blocked_capability_status=normalized["blocked_capability_status"],
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_engineering_foundation_closure_markdown(closure: EngineeringFoundationClosure) -> str:
    """Render deterministic Markdown for the closure report."""

    if not isinstance(closure, EngineeringFoundationClosure):
        raise ValueError("closure_must_be_engineering_foundation_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Engineering Foundation Closure",
        metadata_rows=(
            ("closure_id", closure.closure_id),
            ("repository_url", closure.repository_url),
            ("main_commit", closure.main_commit),
            ("branch", closure.branch),
            ("completion_decision", closure.completion_decision),
            ("policy_version", closure.policy_version),
            ("code_version", closure.code_version),
            ("content_hash", closure.content_hash),
            ("observed_at", closure.observed_at),
        ),
        sections=(
            ("Foundation Gates", material["foundation_gates"]),
            ("Verification Matrix", material["verification_matrix"]),
            ("Protected File Status", material["protected_file_status"]),
            ("Root Integrity Status", material["root_integrity_status"]),
            ("CI Status", material["ci_status"]),
            ("Blocked Capability Status", material["blocked_capability_status"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
