"""Deterministic private AI worker handoff packet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "AIWorkerHandoffPacket",
    "build_ai_worker_handoff_packet",
    "render_ai_worker_handoff_packet_markdown",
]

_POLICY_VERSION = "ai-worker-handoff-packet-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "packet_id",
    "repository_url",
    "main_commit",
    "current_state_summary",
    "policy_version",
    "code_version",
)
_REQUIRED_LIST_FIELDS = (
    "required_reading",
    "allowed_work",
    "forbidden_work",
    "required_verification",
    "merge_rules",
    "rollback_rules",
    "blocked_capabilities",
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
    ("Required Reading", "required_reading"),
    ("Current State Summary", "current_state_summary"),
    ("Allowed Work", "allowed_work"),
    ("Forbidden Work", "forbidden_work"),
    ("Required Verification", "required_verification"),
    ("Merge Rules", "merge_rules"),
    ("Rollback Rules", "rollback_rules"),
    ("Blocked Capabilities", "blocked_capabilities"),
)


@dataclass(frozen=True)
class AIWorkerHandoffPacket:
    """Repository-ready context packet for future AI workers."""

    packet_id: str
    repository_url: str
    main_commit: str
    required_reading: tuple[object, ...]
    current_state_summary: str
    allowed_work: tuple[object, ...]
    forbidden_work: tuple[object, ...]
    required_verification: tuple[object, ...]
    merge_rules: tuple[object, ...]
    rollback_rules: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "allowed_work": list(self.allowed_work),
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "current_state_summary": self.current_state_summary,
            "forbidden_work": list(self.forbidden_work),
            "main_commit": self.main_commit,
            "merge_rules": list(self.merge_rules),
            "packet_id": self.packet_id,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "required_reading": list(self.required_reading),
            "required_verification": list(self.required_verification),
            "rollback_rules": list(self.rollback_rules),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_ai_worker_handoff_packet(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> AIWorkerHandoffPacket:
    """Build a deterministic AI worker handoff packet from caller-provided material."""

    if not isinstance(material, dict):
        raise ValueError("packet_material_must_be_dict")
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

    packet = AIWorkerHandoffPacket(
        packet_id=normalized["packet_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        required_reading=tuple(normalized["required_reading"]),
        current_state_summary=normalized["current_state_summary"],
        allowed_work=tuple(normalized["allowed_work"]),
        forbidden_work=tuple(normalized["forbidden_work"]),
        required_verification=tuple(normalized["required_verification"]),
        merge_rules=tuple(normalized["merge_rules"]),
        rollback_rules=tuple(normalized["rollback_rules"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(packet)


def render_ai_worker_handoff_packet_markdown(packet: AIWorkerHandoffPacket) -> str:
    """Render AI worker handoff packet Markdown deterministically."""

    if not isinstance(packet, AIWorkerHandoffPacket):
        raise ValueError("packet_must_be_ai_worker_handoff_packet")
    lines = [
        "# AI Worker Handoff Packet",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| packet_id | {_escape_table(packet.packet_id)} |",
        f"| repository_url | {_escape_table(packet.repository_url)} |",
        f"| main_commit | {_escape_table(packet.main_commit)} |",
        f"| policy_version | {_escape_table(packet.policy_version)} |",
        f"| code_version | {_escape_table(packet.code_version)} |",
        f"| content_hash | {_escape_table(packet.content_hash)} |",
        f"| observed_at | {_escape_table(packet.observed_at)} |",
        "",
    ]
    material = packet.deterministic_material()
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(packet: AIWorkerHandoffPacket) -> AIWorkerHandoffPacket:
    return AIWorkerHandoffPacket(
        packet_id=packet.packet_id,
        repository_url=packet.repository_url,
        main_commit=packet.main_commit,
        required_reading=packet.required_reading,
        current_state_summary=packet.current_state_summary,
        allowed_work=packet.allowed_work,
        forbidden_work=packet.forbidden_work,
        required_verification=packet.required_verification,
        merge_rules=packet.merge_rules,
        rollback_rules=packet.rollback_rules,
        blocked_capabilities=packet.blocked_capabilities,
        policy_version=packet.policy_version,
        code_version=packet.code_version,
        content_hash=digest_payload(packet.deterministic_material()),
        observed_at=packet.observed_at,
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
        raise ValueError("packet_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("packet_material_must_be_dict")
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
