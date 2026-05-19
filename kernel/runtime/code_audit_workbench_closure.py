"""Deterministic closure report for the non-Houdini Code Audit Workbench."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import (
    reject_text_markers,
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
    "CodeAuditWorkbenchClosure",
    "build_code_audit_workbench_closure",
    "render_code_audit_workbench_closure_markdown",
]

_POLICY_VERSION = "code-audit-workbench-closure-v1"
_CODE_VERSION = "0.1.0"
_COMPLETION_DECISIONS = ("complete", "incomplete", "blocked", "needs_human_review")
_REQUIRED_CLOSURE_GATES = (
    "branch_audit_report_contract_exists",
    "merge_readiness_report_contract_exists",
    "ai_worker_result_review_packet_exists",
    "post_merge_retrospective_exists",
    "daily_report_workflow_exists",
    "operational_loop_exists",
    "sample_pack_exists",
    "real_run_001_generated",
    "next_action_queue_generated",
    "blocked_capabilities_preserved",
    "no_fake_verification_claims",
)
_REQUIRED_REAL_RUN_TERMS = (
    "mainline branch audit",
    "mainline merge readiness",
    "ai worker result review summary",
    "post merge retrospective",
    "daily report",
    "next action queue",
)
_FAKE_CLAIM_MARKERS = (
    "fake green",
    "assumed green",
    "claimed without running",
    "verification fabricated",
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
_DICT_FIELDS = ("closure_gates", "verification_matrix")
_LIST_FIELDS = ("real_run_artifacts", "blocked_capabilities", "remaining_gaps", "rollback_notes")
_ALLOW_EMPTY_LISTS = ("remaining_gaps",)


@dataclass(frozen=True)
class CodeAuditWorkbenchClosure:
    """Repository-ready closure contract for the Code Audit Workbench."""

    closure_id: str
    repository_url: str
    main_commit: str
    branch: str
    closure_gates: dict[str, object]
    verification_matrix: dict[str, object]
    real_run_artifacts: tuple[object, ...]
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
            "branch": self.branch,
            "closure_gates": self.closure_gates,
            "closure_id": self.closure_id,
            "code_version": self.code_version,
            "completion_decision": self.completion_decision,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "real_run_artifacts": list(self.real_run_artifacts),
            "remaining_gaps": list(self.remaining_gaps),
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "verification_matrix": self.verification_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_code_audit_workbench_closure(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CodeAuditWorkbenchClosure:
    """Build a deterministic workbench closure from caller-provided evidence."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="code_audit_workbench_closure_material",
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
    if normalized["completion_decision"] == "complete":
        require_text_terms(
            normalized["real_run_artifacts"],
            _REQUIRED_REAL_RUN_TERMS,
            error="real_run_artifacts_missing_required_report",
        )
    reject_text_markers(normalized, _FAKE_CLAIM_MARKERS, error="fake_verification_claim_blocks_complete")

    closure = CodeAuditWorkbenchClosure(
        closure_id=normalized["closure_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch=normalized["branch"],
        closure_gates=gates,
        verification_matrix=normalized["verification_matrix"],
        real_run_artifacts=tuple(normalized["real_run_artifacts"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        completion_decision=normalized["completion_decision"],
        remaining_gaps=tuple(normalized["remaining_gaps"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(closure, content_hash=compute_content_hash(closure.deterministic_material()))


def render_code_audit_workbench_closure_markdown(closure: CodeAuditWorkbenchClosure) -> str:
    """Render deterministic Markdown for the Code Audit Workbench closure."""

    if not isinstance(closure, CodeAuditWorkbenchClosure):
        raise ValueError("closure_must_be_code_audit_workbench_closure")
    material = closure.deterministic_material()
    return render_markdown(
        "Code Audit Workbench Closure",
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
            ("Closure Gates", material["closure_gates"]),
            ("Verification Matrix", material["verification_matrix"]),
            ("Real Run Artifacts", material["real_run_artifacts"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Completion Decision", closure.completion_decision),
            ("Remaining Gaps", material["remaining_gaps"]),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )
