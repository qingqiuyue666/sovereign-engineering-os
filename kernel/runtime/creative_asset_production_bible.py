"""Deterministic production bible for the private creative sample."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    contains_required_terms,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_number_range,
    require_string_fields,
)

__all__ = [
    "CreativeAssetProductionBible",
    "build_creative_asset_production_bible",
    "render_creative_asset_production_bible_markdown",
]

_POLICY_VERSION = "creative-asset-production-bible-v1"
_CODE_VERSION = "0.1.0"

_STRING_FIELDS = ("bible_id", "project_name", "story_beat", "policy_version", "code_version")
_LIST_FIELDS = (
    "target_platforms",
    "visual_reference_language",
    "shot_list",
    "asset_requirements",
    "pass_requirements",
    "quality_gates",
    "rejection_rules",
    "delivery_outputs",
    "blocked_execution",
    "rollback_plan",
)
_DICT_FIELDS = ("tool_roles",)


@dataclass(frozen=True)
class CreativeAssetProductionBible:
    """Repository-ready creative production bible."""

    bible_id: str
    project_name: str
    target_duration_seconds: int | float
    target_platforms: tuple[object, ...]
    visual_reference_language: tuple[object, ...]
    story_beat: str
    shot_list: tuple[object, ...]
    tool_roles: dict[str, object]
    asset_requirements: tuple[object, ...]
    pass_requirements: tuple[object, ...]
    quality_gates: tuple[object, ...]
    rejection_rules: tuple[object, ...]
    delivery_outputs: tuple[object, ...]
    blocked_execution: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_requirements": list(self.asset_requirements),
            "bible_id": self.bible_id,
            "blocked_execution": list(self.blocked_execution),
            "code_version": self.code_version,
            "delivery_outputs": list(self.delivery_outputs),
            "pass_requirements": list(self.pass_requirements),
            "policy_version": self.policy_version,
            "project_name": self.project_name,
            "quality_gates": list(self.quality_gates),
            "rejection_rules": list(self.rejection_rules),
            "rollback_plan": list(self.rollback_plan),
            "shot_list": list(self.shot_list),
            "story_beat": self.story_beat,
            "target_duration_seconds": self.target_duration_seconds,
            "target_platforms": list(self.target_platforms),
            "tool_roles": self.tool_roles,
            "visual_reference_language": list(self.visual_reference_language),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_creative_asset_production_bible(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CreativeAssetProductionBible:
    """Build a deterministic planning-only production bible for the first sample."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="creative_asset_production_bible_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    if "target_duration_seconds" not in normalized:
        raise ValueError("target_duration_seconds_missing")
    require_number_range(
        normalized["target_duration_seconds"],
        field="target_duration_seconds",
        minimum=8,
        maximum=12,
    )
    require_list_fields(normalized, _LIST_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    if not contains_required_terms(normalized["blocked_execution"], ("external", "tool", "execution")):
        raise ValueError("blocked_execution_must_block_external_tool_execution")

    bible = CreativeAssetProductionBible(
        bible_id=normalized["bible_id"],
        project_name=normalized["project_name"],
        target_duration_seconds=normalized["target_duration_seconds"],
        target_platforms=tuple(normalized["target_platforms"]),
        visual_reference_language=tuple(normalized["visual_reference_language"]),
        story_beat=normalized["story_beat"],
        shot_list=tuple(normalized["shot_list"]),
        tool_roles=normalized["tool_roles"],
        asset_requirements=tuple(normalized["asset_requirements"]),
        pass_requirements=tuple(normalized["pass_requirements"]),
        quality_gates=tuple(normalized["quality_gates"]),
        rejection_rules=tuple(normalized["rejection_rules"]),
        delivery_outputs=tuple(normalized["delivery_outputs"]),
        blocked_execution=tuple(normalized["blocked_execution"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(bible)


def render_creative_asset_production_bible_markdown(bible: CreativeAssetProductionBible) -> str:
    """Render creative production bible Markdown deterministically."""

    if not isinstance(bible, CreativeAssetProductionBible):
        raise ValueError("bible_must_be_creative_asset_production_bible")
    material = bible.deterministic_material()
    return render_markdown(
        "Creative Asset Factory Production Bible v1",
        metadata_rows=(
            ("bible_id", bible.bible_id),
            ("project_name", bible.project_name),
            ("target_duration_seconds", bible.target_duration_seconds),
            ("policy_version", bible.policy_version),
            ("code_version", bible.code_version),
            ("content_hash", bible.content_hash),
            ("observed_at", bible.observed_at),
        ),
        sections=(
            ("Story Beat", bible.story_beat),
            ("Target Platforms", material["target_platforms"]),
            ("Visual Reference Language", material["visual_reference_language"]),
            ("Shot List", material["shot_list"]),
            ("Tool Roles", material["tool_roles"]),
            ("Asset Requirements", material["asset_requirements"]),
            ("Pass Requirements", material["pass_requirements"]),
            ("Quality Gates", material["quality_gates"]),
            ("Rejection Rules", material["rejection_rules"]),
            ("Delivery Outputs", material["delivery_outputs"]),
            ("Blocked Execution", material["blocked_execution"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(bible: CreativeAssetProductionBible) -> CreativeAssetProductionBible:
    return CreativeAssetProductionBible(
        bible_id=bible.bible_id,
        project_name=bible.project_name,
        target_duration_seconds=bible.target_duration_seconds,
        target_platforms=bible.target_platforms,
        visual_reference_language=bible.visual_reference_language,
        story_beat=bible.story_beat,
        shot_list=bible.shot_list,
        tool_roles=bible.tool_roles,
        asset_requirements=bible.asset_requirements,
        pass_requirements=bible.pass_requirements,
        quality_gates=bible.quality_gates,
        rejection_rules=bible.rejection_rules,
        delivery_outputs=bible.delivery_outputs,
        blocked_execution=bible.blocked_execution,
        rollback_plan=bible.rollback_plan,
        policy_version=bible.policy_version,
        code_version=bible.code_version,
        content_hash=compute_content_hash(bible.deterministic_material()),
        observed_at=bible.observed_at,
    )
