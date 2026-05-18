"""Deterministic private Creative Asset Factory planning contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "CreativeAssetFactoryPlan",
    "build_creative_asset_factory_plan",
    "render_creative_asset_factory_plan_markdown",
]

_POLICY_VERSION = "creative-asset-factory-plan-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "plan_id",
    "project_name",
    "target_output",
    "visual_style",
    "policy_version",
    "code_version",
)
_REQUIRED_LIST_FIELDS = (
    "shot_plan",
    "asset_requirements",
    "production_steps",
    "blocked_execution",
    "quality_gates",
    "rollback_notes",
)
_REQUIRED_DICT_FIELDS = ("tool_roles",)
_REQUIRED_INPUT_FIELDS = _REQUIRED_STRING_FIELDS + ("duration_seconds",) + _REQUIRED_LIST_FIELDS + _REQUIRED_DICT_FIELDS

_FORBIDDEN_FIELD_MARKERS = (
    "raw_prompt",
    "raw_response",
    "raw_provider_response",
    "raw_exception",
    "raw_traceback",
    "env",
    "secret",
    "credential",
    "token",
    "api_key",
    "password",
    "private_key",
    "authorization",
)
_DIGEST_FIELD_NAMES = frozenset({"hash", "digest", "content_hash", "declared_hash"})
_DIGEST_FIELD_SUFFIXES = ("_hash", "_digest", "_chain_head")

_SECTION_ORDER = (
    ("Target Output", "target_output"),
    ("Visual Style", "visual_style"),
    ("Shot Plan", "shot_plan"),
    ("Tool Roles", "tool_roles"),
    ("Asset Requirements", "asset_requirements"),
    ("Production Steps", "production_steps"),
    ("Blocked Execution", "blocked_execution"),
    ("Quality Gates", "quality_gates"),
    ("Rollback Notes", "rollback_notes"),
)


@dataclass(frozen=True)
class CreativeAssetFactoryPlan:
    """Repository-ready private creative production plan."""

    plan_id: str
    project_name: str
    target_output: str
    duration_seconds: int | float
    visual_style: str
    shot_plan: tuple[object, ...]
    tool_roles: dict[str, object]
    asset_requirements: tuple[object, ...]
    production_steps: tuple[object, ...]
    blocked_execution: tuple[object, ...]
    quality_gates: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_requirements": list(self.asset_requirements),
            "blocked_execution": list(self.blocked_execution),
            "code_version": self.code_version,
            "duration_seconds": self.duration_seconds,
            "plan_id": self.plan_id,
            "policy_version": self.policy_version,
            "production_steps": list(self.production_steps),
            "project_name": self.project_name,
            "quality_gates": list(self.quality_gates),
            "rollback_notes": list(self.rollback_notes),
            "shot_plan": list(self.shot_plan),
            "target_output": self.target_output,
            "tool_roles": self.tool_roles,
            "visual_style": self.visual_style,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_creative_asset_factory_plan(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CreativeAssetFactoryPlan:
    """Build a deterministic planning-only creative asset factory plan."""

    if not isinstance(material, dict):
        raise ValueError("plan_material_must_be_dict")
    if "content_hash" in material:
        raise ValueError("content_hash_is_computed")

    material_observed_at = material.get("observed_at")
    if observed_at is not None and material_observed_at is not None:
        raise ValueError("observed_at_must_have_single_source")
    observed = observed_at if observed_at is not None else material_observed_at
    if observed is None:
        observed = _OBSERVED_AT_NOT_PROVIDED
    if not strict_nonempty_string(observed):
        raise ValueError("observed_at_must_be_nonempty_string")

    deterministic_input = {key: value for key, value in material.items() if key != "observed_at"}
    _reject_forbidden_fields(deterministic_input)
    _validate_required_fields(deterministic_input)
    _validate_digest_fields(deterministic_input)
    normalized = _normalize_json_material(deterministic_input)

    plan = CreativeAssetFactoryPlan(
        plan_id=normalized["plan_id"],
        project_name=normalized["project_name"],
        target_output=normalized["target_output"],
        duration_seconds=normalized["duration_seconds"],
        visual_style=normalized["visual_style"],
        shot_plan=tuple(normalized["shot_plan"]),
        tool_roles=normalized["tool_roles"],
        asset_requirements=tuple(normalized["asset_requirements"]),
        production_steps=tuple(normalized["production_steps"]),
        blocked_execution=tuple(normalized["blocked_execution"]),
        quality_gates=tuple(normalized["quality_gates"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(plan)


def render_creative_asset_factory_plan_markdown(plan: CreativeAssetFactoryPlan) -> str:
    """Render creative asset factory plan Markdown deterministically."""

    if not isinstance(plan, CreativeAssetFactoryPlan):
        raise ValueError("plan_must_be_creative_asset_factory_plan")
    lines = [
        "# Creative Asset Factory Plan",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| plan_id | {_escape_table(plan.plan_id)} |",
        f"| project_name | {_escape_table(plan.project_name)} |",
        f"| duration_seconds | {plan.duration_seconds} |",
        f"| policy_version | {_escape_table(plan.policy_version)} |",
        f"| code_version | {_escape_table(plan.code_version)} |",
        f"| content_hash | {_escape_table(plan.content_hash)} |",
        f"| observed_at | {_escape_table(plan.observed_at)} |",
        "",
    ]
    material = plan.deterministic_material()
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(plan: CreativeAssetFactoryPlan) -> CreativeAssetFactoryPlan:
    return CreativeAssetFactoryPlan(
        plan_id=plan.plan_id,
        project_name=plan.project_name,
        target_output=plan.target_output,
        duration_seconds=plan.duration_seconds,
        visual_style=plan.visual_style,
        shot_plan=plan.shot_plan,
        tool_roles=plan.tool_roles,
        asset_requirements=plan.asset_requirements,
        production_steps=plan.production_steps,
        blocked_execution=plan.blocked_execution,
        quality_gates=plan.quality_gates,
        rollback_notes=plan.rollback_notes,
        policy_version=plan.policy_version,
        code_version=plan.code_version,
        content_hash=digest_payload(plan.deterministic_material()),
        observed_at=plan.observed_at,
    )


def _validate_required_fields(material: Mapping[str, object]) -> None:
    for field in _REQUIRED_INPUT_FIELDS:
        if field not in material:
            raise ValueError(f"{field}_missing")
    for field in _REQUIRED_STRING_FIELDS:
        if not strict_nonempty_string(material[field]):
            raise ValueError(f"{field}_must_be_nonempty_string")
    duration = material["duration_seconds"]
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("duration_seconds_must_be_positive_number")
    for field in _REQUIRED_DICT_FIELDS:
        if not isinstance(material[field], dict):
            raise ValueError(f"{field}_must_be_dict")
    for field in _REQUIRED_LIST_FIELDS:
        if not isinstance(material[field], list):
            raise ValueError(f"{field}_must_be_list")
        if not material[field]:
            raise ValueError(f"{field}_must_not_be_empty")


def _reject_forbidden_fields(value: object, path: str = "material") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_field_name_must_be_string")
            normalized = key.lower()
            if any(marker in normalized for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError(f"forbidden_field:{path}.{key}")
            _reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def _validate_digest_fields(value: object, path: str = "material") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_digest_field(key) and child is not None and not strict_digest(child):
                raise ValueError(f"{path}.{key}_must_be_valid_digest")
            _validate_digest_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_digest_fields(child, f"{path}[{index}]")


def _is_digest_field(key: str) -> bool:
    normalized = key.lower()
    return normalized in _DIGEST_FIELD_NAMES or normalized.endswith(_DIGEST_FIELD_SUFFIXES)


def _normalize_json_material(material: Mapping[str, object]) -> dict[str, object]:
    try:
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        normalized = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError("plan_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("plan_material_must_be_dict")
    return normalized


def _render_value(value: object, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    if isinstance(value, str):
        return [prefix + value]
    if isinstance(value, bool):
        return [prefix + ("true" if value else "false")]
    if value is None:
        return [prefix + "null"]
    if isinstance(value, (int, float)):
        return [prefix + str(value)]
    if isinstance(value, list):
        if not value:
            return [prefix + "- none"]
        return _render_list(value, indent)
    if isinstance(value, dict):
        if not value:
            return [prefix + "- none"]
        lines: list[str] = []
        for key in sorted(value):
            child = value[key]
            if _is_scalar(child):
                lines.append(prefix + f"- {key}: {_format_scalar(child)}")
            else:
                lines.append(prefix + f"- {key}:")
                lines.extend(_render_value(child, indent + 1))
        return lines
    return [prefix + str(value)]


def _render_list(value: list[object], indent: int) -> list[str]:
    prefix = "  " * indent
    lines: list[str] = []
    for item in value:
        if _is_scalar(item):
            lines.append(prefix + f"- {_format_scalar(item)}")
        elif isinstance(item, dict):
            lines.append(prefix + "-")
            for key in sorted(item):
                child = item[key]
                if _is_scalar(child):
                    lines.append(prefix + f"  - {key}: {_format_scalar(child)}")
                else:
                    lines.append(prefix + f"  - {key}:")
                    lines.extend(_render_value(child, indent + 2))
        else:
            lines.append(prefix + "-")
            lines.extend(_render_value(item, indent + 1))
    return lines


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")
