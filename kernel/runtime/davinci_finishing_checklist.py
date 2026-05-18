"""Deterministic DaVinci finishing checklist for the private creative sample."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    contains_required_terms,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
)

__all__ = [
    "DaVinciFinishingChecklist",
    "build_davinci_finishing_checklist",
    "render_davinci_finishing_checklist_markdown",
]

_POLICY_VERSION = "davinci-finishing-checklist-v1"
_CODE_VERSION = "0.1.0"

_STRING_FIELDS = ("checklist_id", "project_name", "policy_version", "code_version")
_LIST_FIELDS = (
    "color_pipeline",
    "contrast_targets",
    "highlight_policy",
    "subject_separation",
    "grain_halation_bloom_policy",
    "artifact_review",
    "export_formats",
    "platform_deliverables",
    "rejection_rules",
    "blocked_execution",
    "rollback_plan",
)


@dataclass(frozen=True)
class DaVinciFinishingChecklist:
    """Repository-ready DaVinci finishing checklist."""

    checklist_id: str
    project_name: str
    color_pipeline: tuple[object, ...]
    contrast_targets: tuple[object, ...]
    highlight_policy: tuple[object, ...]
    subject_separation: tuple[object, ...]
    grain_halation_bloom_policy: tuple[object, ...]
    artifact_review: tuple[object, ...]
    export_formats: tuple[object, ...]
    platform_deliverables: tuple[object, ...]
    rejection_rules: tuple[object, ...]
    blocked_execution: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "artifact_review": list(self.artifact_review),
            "blocked_execution": list(self.blocked_execution),
            "checklist_id": self.checklist_id,
            "code_version": self.code_version,
            "color_pipeline": list(self.color_pipeline),
            "contrast_targets": list(self.contrast_targets),
            "export_formats": list(self.export_formats),
            "grain_halation_bloom_policy": list(self.grain_halation_bloom_policy),
            "highlight_policy": list(self.highlight_policy),
            "platform_deliverables": list(self.platform_deliverables),
            "policy_version": self.policy_version,
            "project_name": self.project_name,
            "rejection_rules": list(self.rejection_rules),
            "rollback_plan": list(self.rollback_plan),
            "subject_separation": list(self.subject_separation),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_davinci_finishing_checklist(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> DaVinciFinishingChecklist:
    """Build a deterministic finishing checklist without launching editing tools."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="davinci_finishing_checklist_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    if not contains_required_terms(normalized["blocked_execution"], ("davinci", "execution")):
        raise ValueError("blocked_execution_must_block_davinci_execution")

    checklist = DaVinciFinishingChecklist(
        checklist_id=normalized["checklist_id"],
        project_name=normalized["project_name"],
        color_pipeline=tuple(normalized["color_pipeline"]),
        contrast_targets=tuple(normalized["contrast_targets"]),
        highlight_policy=tuple(normalized["highlight_policy"]),
        subject_separation=tuple(normalized["subject_separation"]),
        grain_halation_bloom_policy=tuple(normalized["grain_halation_bloom_policy"]),
        artifact_review=tuple(normalized["artifact_review"]),
        export_formats=tuple(normalized["export_formats"]),
        platform_deliverables=tuple(normalized["platform_deliverables"]),
        rejection_rules=tuple(normalized["rejection_rules"]),
        blocked_execution=tuple(normalized["blocked_execution"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(checklist)


def render_davinci_finishing_checklist_markdown(checklist: DaVinciFinishingChecklist) -> str:
    """Render DaVinci finishing checklist Markdown deterministically."""

    if not isinstance(checklist, DaVinciFinishingChecklist):
        raise ValueError("checklist_must_be_davinci_finishing_checklist")
    material = checklist.deterministic_material()
    return render_markdown(
        "DaVinci Finishing Checklist v1",
        metadata_rows=(
            ("checklist_id", checklist.checklist_id),
            ("project_name", checklist.project_name),
            ("policy_version", checklist.policy_version),
            ("code_version", checklist.code_version),
            ("content_hash", checklist.content_hash),
            ("observed_at", checklist.observed_at),
        ),
        sections=(
            ("Color Pipeline", material["color_pipeline"]),
            ("Contrast Targets", material["contrast_targets"]),
            ("Highlight Policy", material["highlight_policy"]),
            ("Subject Separation", material["subject_separation"]),
            ("Grain / Halation / Bloom Policy", material["grain_halation_bloom_policy"]),
            ("Artifact Review", material["artifact_review"]),
            ("Export Formats", material["export_formats"]),
            ("Platform Deliverables", material["platform_deliverables"]),
            ("Rejection Rules", material["rejection_rules"]),
            ("Blocked Execution", material["blocked_execution"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(checklist: DaVinciFinishingChecklist) -> DaVinciFinishingChecklist:
    return DaVinciFinishingChecklist(
        checklist_id=checklist.checklist_id,
        project_name=checklist.project_name,
        color_pipeline=checklist.color_pipeline,
        contrast_targets=checklist.contrast_targets,
        highlight_policy=checklist.highlight_policy,
        subject_separation=checklist.subject_separation,
        grain_halation_bloom_policy=checklist.grain_halation_bloom_policy,
        artifact_review=checklist.artifact_review,
        export_formats=checklist.export_formats,
        platform_deliverables=checklist.platform_deliverables,
        rejection_rules=checklist.rejection_rules,
        blocked_execution=checklist.blocked_execution,
        rollback_plan=checklist.rollback_plan,
        policy_version=checklist.policy_version,
        code_version=checklist.code_version,
        content_hash=compute_content_hash(checklist.deterministic_material()),
        observed_at=checklist.observed_at,
    )
