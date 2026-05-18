"""Deterministic review rubric for the private creative sample."""

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
    require_required_members,
    require_string_fields,
    require_valid_choices,
)

__all__ = [
    "CREATIVE_RUBRIC_REQUIRED_SCORING_CATEGORIES",
    "CreativeAssetReviewRubric",
    "build_creative_asset_review_rubric",
    "render_creative_asset_review_rubric_markdown",
]

_POLICY_VERSION = "creative-asset-review-rubric-v1"
_CODE_VERSION = "0.1.0"
_REVIEW_DECISIONS = ("pass", "needs_rework", "reject")

CREATIVE_RUBRIC_REQUIRED_SCORING_CATEGORIES = (
    "cinematic_quality",
    "motion_coherence",
    "lighting_consistency",
    "compositing_believability",
    "artifact_control",
    "ai_overuse_control",
    "commercial_usability",
)

_STRING_FIELDS = ("rubric_id", "project_name", "policy_version", "code_version")
_LIST_FIELDS = (
    "scoring_categories",
    "rejection_rules",
    "artifact_checks",
    "motion_checks",
    "lighting_checks",
    "compositing_checks",
    "ai_overuse_checks",
    "commercial_usability_checks",
    "review_decision_options",
    "rollback_plan",
)
_DICT_FIELDS = ("pass_thresholds",)


@dataclass(frozen=True)
class CreativeAssetReviewRubric:
    """Repository-ready creative asset review rubric."""

    rubric_id: str
    project_name: str
    scoring_categories: tuple[object, ...]
    rejection_rules: tuple[object, ...]
    pass_thresholds: dict[str, object]
    artifact_checks: tuple[object, ...]
    motion_checks: tuple[object, ...]
    lighting_checks: tuple[object, ...]
    compositing_checks: tuple[object, ...]
    ai_overuse_checks: tuple[object, ...]
    commercial_usability_checks: tuple[object, ...]
    review_decision_options: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "ai_overuse_checks": list(self.ai_overuse_checks),
            "artifact_checks": list(self.artifact_checks),
            "code_version": self.code_version,
            "commercial_usability_checks": list(self.commercial_usability_checks),
            "compositing_checks": list(self.compositing_checks),
            "lighting_checks": list(self.lighting_checks),
            "motion_checks": list(self.motion_checks),
            "pass_thresholds": self.pass_thresholds,
            "policy_version": self.policy_version,
            "project_name": self.project_name,
            "rejection_rules": list(self.rejection_rules),
            "review_decision_options": list(self.review_decision_options),
            "rollback_plan": list(self.rollback_plan),
            "rubric_id": self.rubric_id,
            "scoring_categories": list(self.scoring_categories),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_creative_asset_review_rubric(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CreativeAssetReviewRubric:
    """Build a deterministic creative asset review rubric."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="creative_asset_review_rubric_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_required_members(
        normalized["scoring_categories"],
        CREATIVE_RUBRIC_REQUIRED_SCORING_CATEGORIES,
        field="scoring_categories",
    )
    require_valid_choices(
        normalized["review_decision_options"],
        field="review_decision_options",
        allowed=_REVIEW_DECISIONS,
    )

    rubric = CreativeAssetReviewRubric(
        rubric_id=normalized["rubric_id"],
        project_name=normalized["project_name"],
        scoring_categories=tuple(normalized["scoring_categories"]),
        rejection_rules=tuple(normalized["rejection_rules"]),
        pass_thresholds=normalized["pass_thresholds"],
        artifact_checks=tuple(normalized["artifact_checks"]),
        motion_checks=tuple(normalized["motion_checks"]),
        lighting_checks=tuple(normalized["lighting_checks"]),
        compositing_checks=tuple(normalized["compositing_checks"]),
        ai_overuse_checks=tuple(normalized["ai_overuse_checks"]),
        commercial_usability_checks=tuple(normalized["commercial_usability_checks"]),
        review_decision_options=tuple(normalized["review_decision_options"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(rubric)


def render_creative_asset_review_rubric_markdown(rubric: CreativeAssetReviewRubric) -> str:
    """Render creative asset review rubric Markdown deterministically."""

    if not isinstance(rubric, CreativeAssetReviewRubric):
        raise ValueError("rubric_must_be_creative_asset_review_rubric")
    material = rubric.deterministic_material()
    return render_markdown(
        "Creative Asset Review Rubric v1",
        metadata_rows=(
            ("rubric_id", rubric.rubric_id),
            ("project_name", rubric.project_name),
            ("policy_version", rubric.policy_version),
            ("code_version", rubric.code_version),
            ("content_hash", rubric.content_hash),
            ("observed_at", rubric.observed_at),
        ),
        sections=(
            ("Scoring Categories", material["scoring_categories"]),
            ("Rejection Rules", material["rejection_rules"]),
            ("Pass Thresholds", material["pass_thresholds"]),
            ("Artifact Checks", material["artifact_checks"]),
            ("Motion Checks", material["motion_checks"]),
            ("Lighting Checks", material["lighting_checks"]),
            ("Compositing Checks", material["compositing_checks"]),
            ("AI Overuse Checks", material["ai_overuse_checks"]),
            ("Commercial Usability Checks", material["commercial_usability_checks"]),
            ("Review Decision Options", material["review_decision_options"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(rubric: CreativeAssetReviewRubric) -> CreativeAssetReviewRubric:
    return CreativeAssetReviewRubric(
        rubric_id=rubric.rubric_id,
        project_name=rubric.project_name,
        scoring_categories=rubric.scoring_categories,
        rejection_rules=rubric.rejection_rules,
        pass_thresholds=rubric.pass_thresholds,
        artifact_checks=rubric.artifact_checks,
        motion_checks=rubric.motion_checks,
        lighting_checks=rubric.lighting_checks,
        compositing_checks=rubric.compositing_checks,
        ai_overuse_checks=rubric.ai_overuse_checks,
        commercial_usability_checks=rubric.commercial_usability_checks,
        review_decision_options=rubric.review_decision_options,
        rollback_plan=rubric.rollback_plan,
        policy_version=rubric.policy_version,
        code_version=rubric.code_version,
        content_hash=compute_content_hash(rubric.deterministic_material()),
        observed_at=rubric.observed_at,
    )
