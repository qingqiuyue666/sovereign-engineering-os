"""Deterministic merge readiness report built from caller-provided evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    has_nonempty_violation,
    has_unsafe_status,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)

__all__ = [
    "MergeReadinessReport",
    "build_merge_readiness_report",
    "render_merge_readiness_report_markdown",
]

_POLICY_VERSION = "merge-readiness-report-v1"
_CODE_VERSION = "0.1.0"
_MERGE_DECISIONS = ("approved_for_merge", "blocked", "needs_human_review", "rejected")
_PROTECTED_STATUS_KEYS = (
    "Makefile",
    "root_README",
    "root_integrity_manifests",
    "health_gate_wiring",
    "governance_files",
    "schema_files",
)

_STRING_FIELDS = (
    "report_id",
    "repository_url",
    "source_branch",
    "target_branch",
    "source_commit",
    "target_commit",
    "merge_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("changed_files", "merge_blockers", "rollback_plan")
_DICT_FIELDS = (
    "protected_files_status",
    "test_matrix",
    "clean_tree_status",
    "diff_check_status",
    "root_integrity_status",
    "blocked_capability_status",
)
_ALLOW_EMPTY_LISTS = ("changed_files", "merge_blockers")


@dataclass(frozen=True)
class MergeReadinessReport:
    """Repository-ready merge gate report."""

    report_id: str
    repository_url: str
    source_branch: str
    target_branch: str
    source_commit: str
    target_commit: str
    changed_files: tuple[object, ...]
    protected_files_status: dict[str, object]
    test_matrix: dict[str, object]
    clean_tree_status: dict[str, object]
    diff_check_status: dict[str, object]
    root_integrity_status: dict[str, object]
    blocked_capability_status: dict[str, object]
    merge_decision: str
    merge_blockers: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capability_status": self.blocked_capability_status,
            "changed_files": list(self.changed_files),
            "clean_tree_status": self.clean_tree_status,
            "code_version": self.code_version,
            "diff_check_status": self.diff_check_status,
            "merge_blockers": list(self.merge_blockers),
            "merge_decision": self.merge_decision,
            "policy_version": self.policy_version,
            "protected_files_status": self.protected_files_status,
            "report_id": self.report_id,
            "repository_url": self.repository_url,
            "rollback_plan": list(self.rollback_plan),
            "root_integrity_status": self.root_integrity_status,
            "source_branch": self.source_branch,
            "source_commit": self.source_commit,
            "target_branch": self.target_branch,
            "target_commit": self.target_commit,
            "test_matrix": self.test_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_merge_readiness_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> MergeReadinessReport:
    """Build a deterministic merge readiness report without performing a merge."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="merge_readiness_report_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_dict_fields(normalized, _DICT_FIELDS, allow_empty=_DICT_FIELDS)
    require_valid_choice(normalized["merge_decision"], field="merge_decision", allowed=_MERGE_DECISIONS)
    _validate_protected_files_status(normalized["protected_files_status"])
    if normalized["merge_decision"] == "approved_for_merge":
        if has_unsafe_status(normalized["protected_files_status"]):
            raise ValueError("unsafe_protected_file_status_blocks_approved_merge")
        if has_nonempty_violation(normalized["blocked_capability_status"]):
            raise ValueError("blocked_capability_violation_blocks_approved_merge")

    report = MergeReadinessReport(
        report_id=normalized["report_id"],
        repository_url=normalized["repository_url"],
        source_branch=normalized["source_branch"],
        target_branch=normalized["target_branch"],
        source_commit=normalized["source_commit"],
        target_commit=normalized["target_commit"],
        changed_files=tuple(normalized["changed_files"]),
        protected_files_status=normalized["protected_files_status"],
        test_matrix=normalized["test_matrix"],
        clean_tree_status=normalized["clean_tree_status"],
        diff_check_status=normalized["diff_check_status"],
        root_integrity_status=normalized["root_integrity_status"],
        blocked_capability_status=normalized["blocked_capability_status"],
        merge_decision=normalized["merge_decision"],
        merge_blockers=tuple(normalized["merge_blockers"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_merge_readiness_report_markdown(report: MergeReadinessReport) -> str:
    """Render merge readiness report Markdown deterministically."""

    if not isinstance(report, MergeReadinessReport):
        raise ValueError("report_must_be_merge_readiness_report")
    material = report.deterministic_material()
    return render_markdown(
        "Merge Readiness Report",
        metadata_rows=(
            ("report_id", report.report_id),
            ("repository_url", report.repository_url),
            ("source_branch", report.source_branch),
            ("target_branch", report.target_branch),
            ("source_commit", report.source_commit),
            ("target_commit", report.target_commit),
            ("policy_version", report.policy_version),
            ("code_version", report.code_version),
            ("content_hash", report.content_hash),
            ("observed_at", report.observed_at),
        ),
        sections=(
            ("Merge Readiness Summary", {"merge_decision": report.merge_decision}),
            ("Branch Pair", {"source_branch": report.source_branch, "target_branch": report.target_branch}),
            ("Changed Files", material["changed_files"]),
            ("Protected Files Status", material["protected_files_status"]),
            ("Verification Matrix", material["test_matrix"]),
            (
                "Clean Tree / Diff Check",
                {
                    "clean_tree_status": material["clean_tree_status"],
                    "diff_check_status": material["diff_check_status"],
                },
            ),
            ("Root Integrity Status", material["root_integrity_status"]),
            ("Blocked Capability Status", material["blocked_capability_status"]),
            ("Merge Decision", report.merge_decision),
            ("Merge Blockers", material["merge_blockers"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _validate_protected_files_status(status: object) -> None:
    if not isinstance(status, dict):
        raise ValueError("protected_files_status_must_be_dict")
    for key in _PROTECTED_STATUS_KEYS:
        if key not in status:
            raise ValueError(f"protected_files_status_missing:{key}")


def _with_hash(report: MergeReadinessReport) -> MergeReadinessReport:
    return MergeReadinessReport(
        report_id=report.report_id,
        repository_url=report.repository_url,
        source_branch=report.source_branch,
        target_branch=report.target_branch,
        source_commit=report.source_commit,
        target_commit=report.target_commit,
        changed_files=report.changed_files,
        protected_files_status=report.protected_files_status,
        test_matrix=report.test_matrix,
        clean_tree_status=report.clean_tree_status,
        diff_check_status=report.diff_check_status,
        root_integrity_status=report.root_integrity_status,
        blocked_capability_status=report.blocked_capability_status,
        merge_decision=report.merge_decision,
        merge_blockers=report.merge_blockers,
        rollback_plan=report.rollback_plan,
        policy_version=report.policy_version,
        code_version=report.code_version,
        content_hash=compute_content_hash(report.deterministic_material()),
        observed_at=report.observed_at,
    )
