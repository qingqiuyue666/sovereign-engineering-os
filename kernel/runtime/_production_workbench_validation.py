"""Shared pure helpers for private production workbench reports."""

from __future__ import annotations

from typing import Mapping, Sequence
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "OBSERVED_AT_NOT_PROVIDED",
    "compute_content_hash",
    "contains_required_terms",
    "has_nonempty_violation",
    "has_unsafe_status",
    "prepare_material",
    "render_markdown",
    "require_dict_fields",
    "require_exact_number",
    "require_list_fields",
    "require_number_range",
    "require_required_members",
    "require_string_fields",
    "require_valid_choice",
    "require_valid_choices",
]

OBSERVED_AT_NOT_PROVIDED = "not_provided"

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


def prepare_material(
    material: Mapping[str, object],
    *,
    observed_at: str | None,
    material_name: str,
) -> tuple[dict[str, object], str]:
    """Normalize caller-provided material and return deterministic input plus observation metadata."""

    if not isinstance(material, dict):
        raise ValueError(f"{material_name}_must_be_dict")
    if "content_hash" in material:
        raise ValueError("content_hash_is_computed")

    material_observed_at = material.get("observed_at")
    if observed_at is not None and material_observed_at is not None:
        raise ValueError("observed_at_must_have_single_source")
    observed = observed_at if observed_at is not None else material_observed_at
    if observed is None:
        observed = OBSERVED_AT_NOT_PROVIDED
    if not strict_nonempty_string(observed):
        raise ValueError("observed_at_must_be_nonempty_string")

    deterministic_input = {key: value for key, value in material.items() if key != "observed_at"}
    reject_forbidden_fields(deterministic_input)
    validate_digest_fields(deterministic_input)
    return normalize_json_material(deterministic_input, material_name=material_name), observed


def require_string_fields(material: Mapping[str, object], fields: Sequence[str]) -> None:
    for field in fields:
        if field not in material:
            raise ValueError(f"{field}_missing")
        if not strict_nonempty_string(material[field]):
            raise ValueError(f"{field}_must_be_nonempty_string")


def require_list_fields(
    material: Mapping[str, object],
    fields: Sequence[str],
    *,
    allow_empty: Sequence[str] = (),
) -> None:
    allow_empty_set = set(allow_empty)
    for field in fields:
        if field not in material:
            raise ValueError(f"{field}_missing")
        if not isinstance(material[field], list):
            raise ValueError(f"{field}_must_be_list")
        if field not in allow_empty_set and not material[field]:
            raise ValueError(f"{field}_must_not_be_empty")


def require_dict_fields(
    material: Mapping[str, object],
    fields: Sequence[str],
    *,
    allow_empty: Sequence[str] = (),
) -> None:
    allow_empty_set = set(allow_empty)
    for field in fields:
        if field not in material:
            raise ValueError(f"{field}_missing")
        if not isinstance(material[field], dict):
            raise ValueError(f"{field}_must_be_dict")
        if field not in allow_empty_set and not material[field]:
            raise ValueError(f"{field}_must_not_be_empty")


def require_valid_choice(value: object, *, field: str, allowed: Sequence[str]) -> None:
    if value not in set(allowed):
        raise ValueError(f"{field}_invalid")


def require_valid_choices(values: object, *, field: str, allowed: Sequence[str]) -> None:
    if not isinstance(values, list):
        raise ValueError(f"{field}_must_be_list")
    allowed_set = set(allowed)
    for value in values:
        if value not in allowed_set:
            raise ValueError(f"{field}_invalid")


def require_required_members(values: object, required: Sequence[str], *, field: str) -> None:
    if not isinstance(values, list):
        raise ValueError(f"{field}_must_be_list")
    present = {str(value) for value in values}
    for member in required:
        if member not in present:
            raise ValueError(f"{field}_missing_required_member:{member}")


def require_number_range(value: object, *, field: str, minimum: float, maximum: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field}_must_be_number")
    if value < minimum or value > maximum:
        raise ValueError(f"{field}_outside_allowed_range")


def require_exact_number(value: object, *, field: str, expected: int | float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field}_must_be_number")
    if value != expected:
        raise ValueError(f"{field}_must_equal_{expected}")


def contains_required_terms(value: object, required_terms: Sequence[str]) -> bool:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).lower()
    return all(term.lower() in text for term in required_terms)


def has_unsafe_status(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {"safe", "is_safe"} and child is False:
                return True
            if normalized_key == "status" and isinstance(child, str) and child.lower() in {"unsafe", "blocked"}:
                return True
            if has_unsafe_status(child):
                return True
    elif isinstance(value, list):
        return any(has_unsafe_status(child) for child in value)
    return False


def has_nonempty_violation(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if "violation" in normalized_key and _is_nonempty_signal(child):
                return True
            if normalized_key == "status" and isinstance(child, str) and child.lower() in {
                "failed",
                "violated",
                "violation",
            }:
                return True
            if has_nonempty_violation(child):
                return True
    elif isinstance(value, list):
        return any(has_nonempty_violation(child) for child in value)
    return False


def compute_content_hash(material: object) -> str:
    return digest_payload(material)


def render_markdown(
    title: str,
    *,
    metadata_rows: Sequence[tuple[str, object]],
    sections: Sequence[tuple[str, object]],
) -> str:
    lines = [
        f"# {title}",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for field, value in metadata_rows:
        lines.append(f"| {field} | {_escape_table(str(value))} |")
    lines.append("")
    for section_title, value in sections:
        lines.append(f"## {section_title}")
        lines.extend(render_value(value))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def reject_forbidden_fields(value: object, path: str = "material") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_field_name_must_be_string")
            normalized = key.lower()
            if any(marker in normalized for marker in _FORBIDDEN_FIELD_MARKERS):
                raise ValueError(f"forbidden_field:{path}.{key}")
            reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_fields(child, f"{path}[{index}]")


def validate_digest_fields(value: object, path: str = "material") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_digest_field(key) and child is not None and not strict_digest(child):
                raise ValueError(f"{path}.{key}_must_be_valid_digest")
            validate_digest_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_digest_fields(child, f"{path}[{index}]")


def normalize_json_material(material: Mapping[str, object], *, material_name: str) -> dict[str, object]:
    try:
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        normalized = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{material_name}_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError(f"{material_name}_must_be_dict")
    return normalized


def render_value(value: object, indent: int = 0) -> list[str]:
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
                lines.extend(render_value(child, indent + 1))
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
                    lines.extend(render_value(child, indent + 2))
        else:
            lines.append(prefix + "-")
            lines.extend(render_value(item, indent + 1))
    return lines


def _is_digest_field(key: str) -> bool:
    normalized = key.lower()
    return normalized in _DIGEST_FIELD_NAMES or normalized.endswith(_DIGEST_FIELD_SUFFIXES)


def _is_nonempty_signal(value: object) -> bool:
    if value in (None, False, "", [], {}):
        return False
    return True


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
