"""Deterministic private daily code audit report workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "CodeAuditDailyReport",
    "build_code_audit_daily_report",
    "render_code_audit_daily_report_markdown",
]

_POLICY_VERSION = "code-audit-daily-report-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "daily_report_id",
    "repository_url",
    "main_commit",
    "policy_version",
    "code_version",
)
_REQUIRED_DICT_FIELDS = ("branch_state", "verification_matrix")
_REQUIRED_LIST_FIELDS = (
    "changed_capabilities",
    "risk_matrix",
    "blocked_capabilities",
    "recommended_next_actions",
    "rollback_notes",
)
_REQUIRED_INPUT_FIELDS = _REQUIRED_STRING_FIELDS + _REQUIRED_DICT_FIELDS + _REQUIRED_LIST_FIELDS

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
    ("Branch State", "branch_state"),
    ("Verification Matrix", "verification_matrix"),
    ("Changed Capabilities", "changed_capabilities"),
    ("Risk Matrix", "risk_matrix"),
    ("Blocked Capabilities", "blocked_capabilities"),
    ("Recommended Next Actions", "recommended_next_actions"),
    ("Rollback Notes", "rollback_notes"),
)


@dataclass(frozen=True)
class CodeAuditDailyReport:
    """Repository-ready private daily code audit report."""

    daily_report_id: str
    repository_url: str
    main_commit: str
    branch_state: dict[str, object]
    verification_matrix: dict[str, object]
    changed_capabilities: tuple[object, ...]
    risk_matrix: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    recommended_next_actions: tuple[object, ...]
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities": list(self.blocked_capabilities),
            "branch_state": self.branch_state,
            "changed_capabilities": list(self.changed_capabilities),
            "code_version": self.code_version,
            "daily_report_id": self.daily_report_id,
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "recommended_next_actions": list(self.recommended_next_actions),
            "repository_url": self.repository_url,
            "risk_matrix": list(self.risk_matrix),
            "rollback_notes": list(self.rollback_notes),
            "verification_matrix": self.verification_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_code_audit_daily_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CodeAuditDailyReport:
    """Build a deterministic daily audit report from caller-provided material."""

    if not isinstance(material, dict):
        raise ValueError("daily_report_material_must_be_dict")
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

    report = CodeAuditDailyReport(
        daily_report_id=normalized["daily_report_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch_state=normalized["branch_state"],
        verification_matrix=normalized["verification_matrix"],
        changed_capabilities=tuple(normalized["changed_capabilities"]),
        risk_matrix=tuple(normalized["risk_matrix"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        recommended_next_actions=tuple(normalized["recommended_next_actions"]),
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_code_audit_daily_report_markdown(report: CodeAuditDailyReport) -> str:
    """Render daily audit report Markdown with deterministic section ordering."""

    if not isinstance(report, CodeAuditDailyReport):
        raise ValueError("report_must_be_code_audit_daily_report")
    lines = [
        "# Code Audit Daily Report",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| daily_report_id | {_escape_table(report.daily_report_id)} |",
        f"| repository_url | {_escape_table(report.repository_url)} |",
        f"| main_commit | {_escape_table(report.main_commit)} |",
        f"| policy_version | {_escape_table(report.policy_version)} |",
        f"| code_version | {_escape_table(report.code_version)} |",
        f"| content_hash | {_escape_table(report.content_hash)} |",
        f"| observed_at | {_escape_table(report.observed_at)} |",
        "",
    ]
    material = report.deterministic_material()
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(report: CodeAuditDailyReport) -> CodeAuditDailyReport:
    return CodeAuditDailyReport(
        daily_report_id=report.daily_report_id,
        repository_url=report.repository_url,
        main_commit=report.main_commit,
        branch_state=report.branch_state,
        verification_matrix=report.verification_matrix,
        changed_capabilities=report.changed_capabilities,
        risk_matrix=report.risk_matrix,
        blocked_capabilities=report.blocked_capabilities,
        recommended_next_actions=report.recommended_next_actions,
        rollback_notes=report.rollback_notes,
        policy_version=report.policy_version,
        code_version=report.code_version,
        content_hash=digest_payload(report.deterministic_material()),
        observed_at=report.observed_at,
    )


def _validate_required_fields(material: Mapping[str, object]) -> None:
    for field in _REQUIRED_INPUT_FIELDS:
        if field not in material:
            raise ValueError(f"{field}_missing")
    for field in _REQUIRED_STRING_FIELDS:
        if not strict_nonempty_string(material[field]):
            raise ValueError(f"{field}_must_be_nonempty_string")
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
        raise ValueError("daily_report_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("daily_report_material_must_be_dict")
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
