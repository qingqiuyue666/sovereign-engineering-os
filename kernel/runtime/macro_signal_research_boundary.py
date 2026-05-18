"""Deterministic macro signal research boundary contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "MacroSignalResearchBoundary",
    "build_macro_signal_research_boundary",
    "render_macro_signal_research_boundary_markdown",
]

_POLICY_VERSION = "macro-signal-research-boundary-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "boundary_id",
    "research_domain",
    "manual_decision_boundary",
    "policy_version",
    "code_version",
)
_REQUIRED_LIST_FIELDS = (
    "allowed_outputs",
    "forbidden_outputs",
    "evidence_requirements",
    "no_trade_conditions",
    "blocked_execution",
    "risk_controls",
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
    ("Research Domain", "research_domain"),
    ("Allowed Outputs", "allowed_outputs"),
    ("Forbidden Outputs", "forbidden_outputs"),
    ("Evidence Requirements", "evidence_requirements"),
    ("Manual Decision Boundary", "manual_decision_boundary"),
    ("No-Trade Conditions", "no_trade_conditions"),
    ("Blocked Execution", "blocked_execution"),
    ("Risk Controls", "risk_controls"),
)


@dataclass(frozen=True)
class MacroSignalResearchBoundary:
    """Repository-ready research-only boundary for macro signal work."""

    boundary_id: str
    research_domain: str
    allowed_outputs: tuple[object, ...]
    forbidden_outputs: tuple[object, ...]
    evidence_requirements: tuple[object, ...]
    manual_decision_boundary: str
    no_trade_conditions: tuple[object, ...]
    blocked_execution: tuple[object, ...]
    risk_controls: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "allowed_outputs": list(self.allowed_outputs),
            "blocked_execution": list(self.blocked_execution),
            "boundary_id": self.boundary_id,
            "code_version": self.code_version,
            "evidence_requirements": list(self.evidence_requirements),
            "forbidden_outputs": list(self.forbidden_outputs),
            "manual_decision_boundary": self.manual_decision_boundary,
            "no_trade_conditions": list(self.no_trade_conditions),
            "policy_version": self.policy_version,
            "research_domain": self.research_domain,
            "risk_controls": list(self.risk_controls),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_macro_signal_research_boundary(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> MacroSignalResearchBoundary:
    """Build a deterministic research-only macro signal boundary."""

    if not isinstance(material, dict):
        raise ValueError("boundary_material_must_be_dict")
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

    boundary = MacroSignalResearchBoundary(
        boundary_id=normalized["boundary_id"],
        research_domain=normalized["research_domain"],
        allowed_outputs=tuple(normalized["allowed_outputs"]),
        forbidden_outputs=tuple(normalized["forbidden_outputs"]),
        evidence_requirements=tuple(normalized["evidence_requirements"]),
        manual_decision_boundary=normalized["manual_decision_boundary"],
        no_trade_conditions=tuple(normalized["no_trade_conditions"]),
        blocked_execution=tuple(normalized["blocked_execution"]),
        risk_controls=tuple(normalized["risk_controls"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(boundary)


def render_macro_signal_research_boundary_markdown(boundary: MacroSignalResearchBoundary) -> str:
    """Render macro signal research boundary Markdown deterministically."""

    if not isinstance(boundary, MacroSignalResearchBoundary):
        raise ValueError("boundary_must_be_macro_signal_research_boundary")
    lines = [
        "# Macro Signal Research Boundary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| boundary_id | {_escape_table(boundary.boundary_id)} |",
        f"| policy_version | {_escape_table(boundary.policy_version)} |",
        f"| code_version | {_escape_table(boundary.code_version)} |",
        f"| content_hash | {_escape_table(boundary.content_hash)} |",
        f"| observed_at | {_escape_table(boundary.observed_at)} |",
        "",
    ]
    material = boundary.deterministic_material()
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(boundary: MacroSignalResearchBoundary) -> MacroSignalResearchBoundary:
    return MacroSignalResearchBoundary(
        boundary_id=boundary.boundary_id,
        research_domain=boundary.research_domain,
        allowed_outputs=boundary.allowed_outputs,
        forbidden_outputs=boundary.forbidden_outputs,
        evidence_requirements=boundary.evidence_requirements,
        manual_decision_boundary=boundary.manual_decision_boundary,
        no_trade_conditions=boundary.no_trade_conditions,
        blocked_execution=boundary.blocked_execution,
        risk_controls=boundary.risk_controls,
        policy_version=boundary.policy_version,
        code_version=boundary.code_version,
        content_hash=digest_payload(boundary.deterministic_material()),
        observed_at=boundary.observed_at,
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
        raise ValueError("boundary_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("boundary_material_must_be_dict")
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
