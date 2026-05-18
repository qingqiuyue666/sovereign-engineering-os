"""Deterministic branch audit report built from caller-provided material."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

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
    "BranchAuditReport",
    "build_branch_audit_report",
    "render_branch_audit_report_markdown",
]

_POLICY_VERSION = "branch-audit-report-v1"
_CODE_VERSION = "0.1.0"
_RECOMMENDED_ACTIONS = ("merge_ready", "needs_fix", "reject", "defer")

_STRING_FIELDS = (
    "report_id",
    "repository_url",
    "base_branch",
    "feature_branch",
    "base_commit",
    "head_commit",
    "recommended_action",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "changed_files",
    "added_files",
    "modified_files",
    "deleted_files",
    "risk_matrix",
    "boundary_findings",
    "forbidden_changes",
    "merge_blockers",
    "rollback_plan",
)
_DICT_FIELDS = ("test_matrix",)
_ALLOW_EMPTY_LISTS = (
    "changed_files",
    "added_files",
    "modified_files",
    "deleted_files",
    "risk_matrix",
    "boundary_findings",
    "forbidden_changes",
    "merge_blockers",
)


@dataclass(frozen=True)
class BranchAuditReport:
    """Repository-ready branch audit report."""

    report_id: str
    repository_url: str
    base_branch: str
    feature_branch: str
    base_commit: str
    head_commit: str
    changed_files: tuple[object, ...]
    added_files: tuple[object, ...]
    modified_files: tuple[object, ...]
    deleted_files: tuple[object, ...]
    test_matrix: dict[str, object]
    risk_matrix: tuple[object, ...]
    boundary_findings: tuple[object, ...]
    forbidden_changes: tuple[object, ...]
    merge_blockers: tuple[object, ...]
    recommended_action: str
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "added_files": list(self.added_files),
            "base_branch": self.base_branch,
            "base_commit": self.base_commit,
            "boundary_findings": list(self.boundary_findings),
            "changed_files": list(self.changed_files),
            "code_version": self.code_version,
            "deleted_files": list(self.deleted_files),
            "feature_branch": self.feature_branch,
            "forbidden_changes": list(self.forbidden_changes),
            "head_commit": self.head_commit,
            "merge_blockers": list(self.merge_blockers),
            "modified_files": list(self.modified_files),
            "policy_version": self.policy_version,
            "recommended_action": self.recommended_action,
            "report_id": self.report_id,
            "repository_url": self.repository_url,
            "risk_matrix": list(self.risk_matrix),
            "rollback_plan": list(self.rollback_plan),
            "test_matrix": self.test_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_branch_audit_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> BranchAuditReport:
    """Build a deterministic branch audit report without inspecting repository state."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="branch_audit_report_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_dict_fields(normalized, _DICT_FIELDS, allow_empty=_DICT_FIELDS)
    require_valid_choice(
        normalized["recommended_action"],
        field="recommended_action",
        allowed=_RECOMMENDED_ACTIONS,
    )

    report = BranchAuditReport(
        report_id=normalized["report_id"],
        repository_url=normalized["repository_url"],
        base_branch=normalized["base_branch"],
        feature_branch=normalized["feature_branch"],
        base_commit=normalized["base_commit"],
        head_commit=normalized["head_commit"],
        changed_files=tuple(normalized["changed_files"]),
        added_files=tuple(normalized["added_files"]),
        modified_files=tuple(normalized["modified_files"]),
        deleted_files=tuple(normalized["deleted_files"]),
        test_matrix=normalized["test_matrix"],
        risk_matrix=tuple(normalized["risk_matrix"]),
        boundary_findings=tuple(normalized["boundary_findings"]),
        forbidden_changes=tuple(normalized["forbidden_changes"]),
        merge_blockers=tuple(normalized["merge_blockers"]),
        recommended_action=normalized["recommended_action"],
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_branch_audit_report_markdown(report: BranchAuditReport) -> str:
    """Render branch audit report Markdown with deterministic section ordering."""

    if not isinstance(report, BranchAuditReport):
        raise ValueError("report_must_be_branch_audit_report")
    material = report.deterministic_material()
    return render_markdown(
        "Branch Audit Report",
        metadata_rows=(
            ("report_id", report.report_id),
            ("repository_url", report.repository_url),
            ("base_branch", report.base_branch),
            ("feature_branch", report.feature_branch),
            ("base_commit", report.base_commit),
            ("head_commit", report.head_commit),
            ("policy_version", report.policy_version),
            ("code_version", report.code_version),
            ("content_hash", report.content_hash),
            ("observed_at", report.observed_at),
        ),
        sections=(
            ("Executive Summary", {"recommended_action": report.recommended_action}),
            (
                "Branch State",
                {
                    "base_branch": report.base_branch,
                    "feature_branch": report.feature_branch,
                    "base_commit": report.base_commit,
                    "head_commit": report.head_commit,
                },
            ),
            (
                "Changed Files",
                {
                    "changed_files": material["changed_files"],
                    "added_files": material["added_files"],
                    "modified_files": material["modified_files"],
                    "deleted_files": material["deleted_files"],
                },
            ),
            ("Test Matrix", material["test_matrix"]),
            ("Risk Matrix", material["risk_matrix"]),
            ("Boundary Findings", material["boundary_findings"]),
            ("Forbidden Changes", material["forbidden_changes"]),
            ("Merge Blockers", material["merge_blockers"]),
            ("Recommended Action", report.recommended_action),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(report: BranchAuditReport) -> BranchAuditReport:
    return BranchAuditReport(
        report_id=report.report_id,
        repository_url=report.repository_url,
        base_branch=report.base_branch,
        feature_branch=report.feature_branch,
        base_commit=report.base_commit,
        head_commit=report.head_commit,
        changed_files=report.changed_files,
        added_files=report.added_files,
        modified_files=report.modified_files,
        deleted_files=report.deleted_files,
        test_matrix=report.test_matrix,
        risk_matrix=report.risk_matrix,
        boundary_findings=report.boundary_findings,
        forbidden_changes=report.forbidden_changes,
        merge_blockers=report.merge_blockers,
        recommended_action=report.recommended_action,
        rollback_plan=report.rollback_plan,
        policy_version=report.policy_version,
        code_version=report.code_version,
        content_hash=compute_content_hash(report.deterministic_material()),
        observed_at=report.observed_at,
    )
