"""Deterministic read-only code audit workbench reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "CodeAuditReport",
    "build_code_audit_report",
    "render_code_audit_markdown",
]

_POLICY_VERSION = "code-audit-workbench-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "report_id",
    "repository_url",
    "main_commit",
    "public_safe_summary",
    "policy_version",
    "code_version",
)
_REQUIRED_DICT_FIELDS = (
    "branch_state",
    "test_matrix",
    "root_integrity_state",
    "durable_decision_store_state",
    "durable_review_store_state",
    "recovery_state",
    "audit_export_state",
    "status_surface_state",
    "work_queue_state",
    "runbook_shell_state",
    "provider_preflight_state",
    "readiness_matrix_state",
)
_REQUIRED_LIST_FIELDS = (
    "merged_slices",
    "blocked_capabilities",
    "risk_matrix",
    "next_actions",
    "rollback_plan",
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
_DIGEST_FIELD_NAMES = frozenset({"hash", "digest", "content_hash", "previous_hash", "current_hash"})
_DIGEST_FIELD_SUFFIXES = ("_hash", "_digest", "_chain_head")

_SECTION_ORDER = (
    ("Executive Summary", "public_safe_summary"),
    ("Repository State", "branch_state"),
    ("Recently Integrated Capabilities", "merged_slices"),
    ("Verification Matrix", "test_matrix"),
    ("Root Integrity / Governance Status", "root_integrity_state"),
    ("Durable Store Status", ("durable_decision_store_state", "durable_review_store_state")),
    (
        "Operator Review / Decision Chain Status",
        ("status_surface_state", "work_queue_state", "runbook_shell_state", "provider_preflight_state"),
    ),
    ("Recovery / Audit Export Status", ("recovery_state", "audit_export_state", "readiness_matrix_state")),
    ("Blocked Capabilities", "blocked_capabilities"),
    ("Risk Matrix", "risk_matrix"),
    ("Next Actions", "next_actions"),
    ("Rollback Plan", "rollback_plan"),
    ("Public-Safe Summary", "public_safe_summary"),
)


@dataclass(frozen=True)
class CodeAuditReport:
    """Repository-ready deterministic engineering audit report."""

    report_id: str
    repository_url: str
    main_commit: str
    branch_state: dict[str, object]
    merged_slices: tuple[object, ...]
    test_matrix: dict[str, object]
    root_integrity_state: dict[str, object]
    durable_decision_store_state: dict[str, object]
    durable_review_store_state: dict[str, object]
    recovery_state: dict[str, object]
    audit_export_state: dict[str, object]
    status_surface_state: dict[str, object]
    work_queue_state: dict[str, object]
    runbook_shell_state: dict[str, object]
    provider_preflight_state: dict[str, object]
    readiness_matrix_state: dict[str, object]
    blocked_capabilities: tuple[object, ...]
    risk_matrix: tuple[object, ...]
    next_actions: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    public_safe_summary: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "audit_export_state": self.audit_export_state,
            "blocked_capabilities": list(self.blocked_capabilities),
            "branch_state": self.branch_state,
            "code_version": self.code_version,
            "durable_decision_store_state": self.durable_decision_store_state,
            "durable_review_store_state": self.durable_review_store_state,
            "main_commit": self.main_commit,
            "merged_slices": list(self.merged_slices),
            "next_actions": list(self.next_actions),
            "policy_version": self.policy_version,
            "provider_preflight_state": self.provider_preflight_state,
            "public_safe_summary": self.public_safe_summary,
            "readiness_matrix_state": self.readiness_matrix_state,
            "recovery_state": self.recovery_state,
            "report_id": self.report_id,
            "repository_url": self.repository_url,
            "risk_matrix": list(self.risk_matrix),
            "rollback_plan": list(self.rollback_plan),
            "root_integrity_state": self.root_integrity_state,
            "runbook_shell_state": self.runbook_shell_state,
            "status_surface_state": self.status_surface_state,
            "test_matrix": self.test_matrix,
            "work_queue_state": self.work_queue_state,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_code_audit_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> CodeAuditReport:
    """Build a deterministic code audit report from caller-provided material."""

    if not isinstance(material, dict):
        raise ValueError("report_material_must_be_dict")
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

    report = CodeAuditReport(
        report_id=normalized["report_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch_state=normalized["branch_state"],
        merged_slices=tuple(normalized["merged_slices"]),
        test_matrix=normalized["test_matrix"],
        root_integrity_state=normalized["root_integrity_state"],
        durable_decision_store_state=normalized["durable_decision_store_state"],
        durable_review_store_state=normalized["durable_review_store_state"],
        recovery_state=normalized["recovery_state"],
        audit_export_state=normalized["audit_export_state"],
        status_surface_state=normalized["status_surface_state"],
        work_queue_state=normalized["work_queue_state"],
        runbook_shell_state=normalized["runbook_shell_state"],
        provider_preflight_state=normalized["provider_preflight_state"],
        readiness_matrix_state=normalized["readiness_matrix_state"],
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        risk_matrix=tuple(normalized["risk_matrix"]),
        next_actions=tuple(normalized["next_actions"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        public_safe_summary=normalized["public_safe_summary"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_code_audit_markdown(report: CodeAuditReport) -> str:
    """Render report Markdown with fixed section order."""

    if not isinstance(report, CodeAuditReport):
        raise ValueError("report_must_be_code_audit_report")
    lines = [
        "# Sovereign Engineering OS Mainline Audit Report",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| report_id | {_escape_table(report.report_id)} |",
        f"| repository_url | {_escape_table(report.repository_url)} |",
        f"| main_commit | {_escape_table(report.main_commit)} |",
        f"| policy_version | {_escape_table(report.policy_version)} |",
        f"| code_version | {_escape_table(report.code_version)} |",
        f"| content_hash | {_escape_table(report.content_hash)} |",
        f"| observed_at | {_escape_table(report.observed_at)} |",
        "",
    ]
    material = report.deterministic_material()
    for title, field_names in _SECTION_ORDER:
        lines.append(f"## {title}")
        if isinstance(field_names, tuple):
            for field_name in field_names:
                lines.extend(_render_named_block(field_name, material[field_name]))
        else:
            lines.extend(_render_value(material[field_names]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(report: CodeAuditReport) -> CodeAuditReport:
    return CodeAuditReport(
        report_id=report.report_id,
        repository_url=report.repository_url,
        main_commit=report.main_commit,
        branch_state=report.branch_state,
        merged_slices=report.merged_slices,
        test_matrix=report.test_matrix,
        root_integrity_state=report.root_integrity_state,
        durable_decision_store_state=report.durable_decision_store_state,
        durable_review_store_state=report.durable_review_store_state,
        recovery_state=report.recovery_state,
        audit_export_state=report.audit_export_state,
        status_surface_state=report.status_surface_state,
        work_queue_state=report.work_queue_state,
        runbook_shell_state=report.runbook_shell_state,
        provider_preflight_state=report.provider_preflight_state,
        readiness_matrix_state=report.readiness_matrix_state,
        blocked_capabilities=report.blocked_capabilities,
        risk_matrix=report.risk_matrix,
        next_actions=report.next_actions,
        rollback_plan=report.rollback_plan,
        public_safe_summary=report.public_safe_summary,
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
            if _is_digest_field(key) and not strict_digest(child):
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
        raise ValueError("report_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("report_material_must_be_dict")
    return normalized


def _render_named_block(field_name: str, value: object) -> list[str]:
    title = field_name.replace("_", " ")
    return [f"### {title}"] + _render_value(value)


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
