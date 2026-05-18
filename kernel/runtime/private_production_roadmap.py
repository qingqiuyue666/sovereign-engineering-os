"""Deterministic private production roadmap contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "PrivateProductionRoadmap",
    "build_private_production_roadmap",
    "render_private_production_roadmap_markdown",
]

_POLICY_VERSION = "private-production-roadmap-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "roadmap_id",
    "current_phase",
    "policy_version",
    "code_version",
)
_REQUIRED_LIST_FIELDS = (
    "completed_layers",
    "frozen_layers",
    "next_workbenches",
    "forbidden_directions",
    "decision_rules",
    "success_metrics",
    "stop_conditions",
)
_REQUIRED_INPUT_FIELDS = _REQUIRED_STRING_FIELDS + _REQUIRED_LIST_FIELDS

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
    ("Current Phase", "current_phase"),
    ("Completed Layers", "completed_layers"),
    ("Frozen Layers", "frozen_layers"),
    ("Next Workbenches", "next_workbenches"),
    ("Forbidden Directions", "forbidden_directions"),
    ("Decision Rules", "decision_rules"),
    ("Success Metrics", "success_metrics"),
    ("Stop Conditions", "stop_conditions"),
)


@dataclass(frozen=True)
class PrivateProductionRoadmap:
    """Repository-ready private production roadmap."""

    roadmap_id: str
    current_phase: str
    completed_layers: tuple[object, ...]
    frozen_layers: tuple[object, ...]
    next_workbenches: tuple[object, ...]
    forbidden_directions: tuple[object, ...]
    decision_rules: tuple[object, ...]
    success_metrics: tuple[object, ...]
    stop_conditions: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "completed_layers": list(self.completed_layers),
            "current_phase": self.current_phase,
            "decision_rules": list(self.decision_rules),
            "forbidden_directions": list(self.forbidden_directions),
            "frozen_layers": list(self.frozen_layers),
            "next_workbenches": list(self.next_workbenches),
            "policy_version": self.policy_version,
            "roadmap_id": self.roadmap_id,
            "stop_conditions": list(self.stop_conditions),
            "success_metrics": list(self.success_metrics),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_private_production_roadmap(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> PrivateProductionRoadmap:
    """Build a deterministic private production roadmap from caller-provided material."""

    if not isinstance(material, dict):
        raise ValueError("roadmap_material_must_be_dict")
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

    roadmap = PrivateProductionRoadmap(
        roadmap_id=normalized["roadmap_id"],
        current_phase=normalized["current_phase"],
        completed_layers=tuple(normalized["completed_layers"]),
        frozen_layers=tuple(normalized["frozen_layers"]),
        next_workbenches=tuple(normalized["next_workbenches"]),
        forbidden_directions=tuple(normalized["forbidden_directions"]),
        decision_rules=tuple(normalized["decision_rules"]),
        success_metrics=tuple(normalized["success_metrics"]),
        stop_conditions=tuple(normalized["stop_conditions"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(roadmap)


def render_private_production_roadmap_markdown(roadmap: PrivateProductionRoadmap) -> str:
    """Render private production roadmap Markdown deterministically."""

    if not isinstance(roadmap, PrivateProductionRoadmap):
        raise ValueError("roadmap_must_be_private_production_roadmap")
    lines = [
        "# Private Production Roadmap",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| roadmap_id | {_escape_table(roadmap.roadmap_id)} |",
        f"| policy_version | {_escape_table(roadmap.policy_version)} |",
        f"| code_version | {_escape_table(roadmap.code_version)} |",
        f"| content_hash | {_escape_table(roadmap.content_hash)} |",
        f"| observed_at | {_escape_table(roadmap.observed_at)} |",
        "",
    ]
    material = roadmap.deterministic_material()
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(roadmap: PrivateProductionRoadmap) -> PrivateProductionRoadmap:
    return PrivateProductionRoadmap(
        roadmap_id=roadmap.roadmap_id,
        current_phase=roadmap.current_phase,
        completed_layers=roadmap.completed_layers,
        frozen_layers=roadmap.frozen_layers,
        next_workbenches=roadmap.next_workbenches,
        forbidden_directions=roadmap.forbidden_directions,
        decision_rules=roadmap.decision_rules,
        success_metrics=roadmap.success_metrics,
        stop_conditions=roadmap.stop_conditions,
        policy_version=roadmap.policy_version,
        code_version=roadmap.code_version,
        content_hash=digest_payload(roadmap.deterministic_material()),
        observed_at=roadmap.observed_at,
    )


def _validate_required_fields(material: Mapping[str, object]) -> None:
    for field in _REQUIRED_INPUT_FIELDS:
        if field not in material:
            raise ValueError(f"{field}_missing")
    for field in _REQUIRED_STRING_FIELDS:
        if not strict_nonempty_string(material[field]):
            raise ValueError(f"{field}_must_be_nonempty_string")
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
        raise ValueError("roadmap_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("roadmap_material_must_be_dict")
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
