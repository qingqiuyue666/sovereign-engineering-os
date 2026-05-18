"""Deterministic post-merge retrospective report for operator memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
)

__all__ = [
    "PostMergeRetrospectiveReport",
    "build_post_merge_retrospective_report",
    "render_post_merge_retrospective_report_markdown",
]

_POLICY_VERSION = "post-merge-retrospective-report-v1"
_CODE_VERSION = "0.1.0"

_STRING_FIELDS = (
    "report_id",
    "repository_url",
    "merge_commit",
    "merged_branch",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "merged_capabilities",
    "files_added",
    "files_modified",
    "files_deleted",
    "tests_after_merge",
    "risks_retained",
    "blocked_capabilities_preserved",
    "lessons_learned",
    "next_actions",
    "rollback_route",
)
_ALLOW_EMPTY_LISTS = ("files_added", "files_modified", "files_deleted", "risks_retained")


@dataclass(frozen=True)
class PostMergeRetrospectiveReport:
    """Repository-ready post-merge retrospective."""

    report_id: str
    repository_url: str
    merge_commit: str
    merged_branch: str
    merged_capabilities: tuple[object, ...]
    files_added: tuple[object, ...]
    files_modified: tuple[object, ...]
    files_deleted: tuple[object, ...]
    tests_after_merge: tuple[object, ...]
    risks_retained: tuple[object, ...]
    blocked_capabilities_preserved: tuple[object, ...]
    lessons_learned: tuple[object, ...]
    next_actions: tuple[object, ...]
    rollback_route: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities_preserved": list(self.blocked_capabilities_preserved),
            "code_version": self.code_version,
            "files_added": list(self.files_added),
            "files_deleted": list(self.files_deleted),
            "files_modified": list(self.files_modified),
            "lessons_learned": list(self.lessons_learned),
            "merge_commit": self.merge_commit,
            "merged_branch": self.merged_branch,
            "merged_capabilities": list(self.merged_capabilities),
            "next_actions": list(self.next_actions),
            "policy_version": self.policy_version,
            "report_id": self.report_id,
            "repository_url": self.repository_url,
            "risks_retained": list(self.risks_retained),
            "rollback_route": list(self.rollback_route),
            "tests_after_merge": list(self.tests_after_merge),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_post_merge_retrospective_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> PostMergeRetrospectiveReport:
    """Build a deterministic post-merge retrospective without inspecting repository state."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="post_merge_retrospective_report_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)

    report = PostMergeRetrospectiveReport(
        report_id=normalized["report_id"],
        repository_url=normalized["repository_url"],
        merge_commit=normalized["merge_commit"],
        merged_branch=normalized["merged_branch"],
        merged_capabilities=tuple(normalized["merged_capabilities"]),
        files_added=tuple(normalized["files_added"]),
        files_modified=tuple(normalized["files_modified"]),
        files_deleted=tuple(normalized["files_deleted"]),
        tests_after_merge=tuple(normalized["tests_after_merge"]),
        risks_retained=tuple(normalized["risks_retained"]),
        blocked_capabilities_preserved=tuple(normalized["blocked_capabilities_preserved"]),
        lessons_learned=tuple(normalized["lessons_learned"]),
        next_actions=tuple(normalized["next_actions"]),
        rollback_route=tuple(normalized["rollback_route"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_post_merge_retrospective_report_markdown(report: PostMergeRetrospectiveReport) -> str:
    """Render post-merge retrospective Markdown deterministically."""

    if not isinstance(report, PostMergeRetrospectiveReport):
        raise ValueError("report_must_be_post_merge_retrospective_report")
    material = report.deterministic_material()
    return render_markdown(
        "Post-Merge Retrospective Report",
        metadata_rows=(
            ("report_id", report.report_id),
            ("repository_url", report.repository_url),
            ("merge_commit", report.merge_commit),
            ("merged_branch", report.merged_branch),
            ("policy_version", report.policy_version),
            ("code_version", report.code_version),
            ("content_hash", report.content_hash),
            ("observed_at", report.observed_at),
        ),
        sections=(
            ("Merge Summary", {"merge_commit": report.merge_commit, "merged_branch": report.merged_branch}),
            ("Merged Capabilities", material["merged_capabilities"]),
            (
                "Files Changed",
                {
                    "files_added": material["files_added"],
                    "files_modified": material["files_modified"],
                    "files_deleted": material["files_deleted"],
                },
            ),
            ("Tests After Merge", material["tests_after_merge"]),
            ("Risks Retained", material["risks_retained"]),
            ("Blocked Capabilities Preserved", material["blocked_capabilities_preserved"]),
            ("Lessons Learned", material["lessons_learned"]),
            ("Next Actions", material["next_actions"]),
            ("Rollback Route", material["rollback_route"]),
        ),
    )


def _with_hash(report: PostMergeRetrospectiveReport) -> PostMergeRetrospectiveReport:
    return PostMergeRetrospectiveReport(
        report_id=report.report_id,
        repository_url=report.repository_url,
        merge_commit=report.merge_commit,
        merged_branch=report.merged_branch,
        merged_capabilities=report.merged_capabilities,
        files_added=report.files_added,
        files_modified=report.files_modified,
        files_deleted=report.files_deleted,
        tests_after_merge=report.tests_after_merge,
        risks_retained=report.risks_retained,
        blocked_capabilities_preserved=report.blocked_capabilities_preserved,
        lessons_learned=report.lessons_learned,
        next_actions=report.next_actions,
        rollback_route=report.rollback_route,
        policy_version=report.policy_version,
        code_version=report.code_version,
        content_hash=compute_content_hash(report.deterministic_material()),
        observed_at=report.observed_at,
    )
