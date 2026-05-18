"""Deterministic private operator state report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "OperatorStateReport",
    "build_operator_state_report",
    "render_operator_state_report_markdown",
]

_POLICY_VERSION = "operator-state-report-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "report_id",
    "repository_url",
    "main_commit",
    "policy_version",
    "code_version",
)
_REQUIRED_DICT_FIELDS = ("branch_state", "test_matrix")
_REQUIRED_LIST_FIELDS = (
    "completed_capabilities",
    "active_assets",
    "frozen_kernel_rules",
    "allowed_next_work",
    "forbidden_work",
    "risk_register",
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
_DIGEST_FIELD_NAMES = frozenset({"hash", "digest", "content_hash", "declared_hash"})
_DIGEST_FIELD_SUFFIXES = ("_hash", "_digest", "_chain_head")

_SECTION_ORDER = (
    ("Branch State", "branch_state"),
    ("Completed Capabilities", "completed_capabilities"),
    ("Active Assets", "active_assets"),
    ("Frozen Kernel Rules", "frozen_kernel_rules"),
    ("Allowed Next Work", "allowed_next_work"),
    ("Forbidden Work", "forbidden_work"),
    ("Test Matrix", "test_matrix"),
    ("Risk Register", "risk_register"),
    ("Next Actions", "next_actions"),
    ("Rollback Plan", "rollback_plan"),
)


@dataclass(frozen=True)
class OperatorStateReport:
    """Repository-ready private state report for the operator."""

    report_id: str
    repository_url: str
    main_commit: str
    branch_state: dict[str, object]
    completed_capabilities: tuple[object, ...]
    active_assets: tuple[object, ...]
    frozen_kernel_rules: tuple[object, ...]
    allowed_next_work: tuple[object, ...]
    forbidden_work: tuple[object, ...]
    test_matrix: dict[str, object]
    risk_register: tuple[object, ...]
    next_actions: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "active_assets": list(self.active_assets),
            "allowed_next_work": list(self.allowed_next_work),
            "branch_state": self.branch_state,
            "code_version": self.code_version,
            "completed_capabilities": list(self.completed_capabilities),
            "forbidden_work": list(self.forbidden_work),
            "frozen_kernel_rules": list(self.frozen_kernel_rules),
            "main_commit": self.main_commit,
            "next_actions": list(self.next_actions),
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "report_id": self.report_id,
            "risk_register": list(self.risk_register),
            "rollback_plan": list(self.rollback_plan),
            "test_matrix": self.test_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_state_report(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorStateReport:
    """Build a deterministic private operator state report from caller-provided material."""

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

    report = OperatorStateReport(
        report_id=normalized["report_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        branch_state=normalized["branch_state"],
        completed_capabilities=tuple(normalized["completed_capabilities"]),
        active_assets=tuple(normalized["active_assets"]),
        frozen_kernel_rules=tuple(normalized["frozen_kernel_rules"]),
        allowed_next_work=tuple(normalized["allowed_next_work"]),
        forbidden_work=tuple(normalized["forbidden_work"]),
        test_matrix=normalized["test_matrix"],
        risk_register=tuple(normalized["risk_register"]),
        next_actions=tuple(normalized["next_actions"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(report)


def render_operator_state_report_markdown(report: OperatorStateReport) -> str:
    """Render private operator state report Markdown deterministically."""

    if not isinstance(report, OperatorStateReport):
        raise ValueError("report_must_be_operator_state_report")
    lines = [
        "# Private Operator State Report",
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
    for title, field_name in _SECTION_ORDER:
        lines.append(f"## {title}")
        lines.extend(_render_value(material[field_name]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(report: OperatorStateReport) -> OperatorStateReport:
    return OperatorStateReport(
        report_id=report.report_id,
        repository_url=report.repository_url,
        main_commit=report.main_commit,
        branch_state=report.branch_state,
        completed_capabilities=report.completed_capabilities,
        active_assets=report.active_assets,
        frozen_kernel_rules=report.frozen_kernel_rules,
        allowed_next_work=report.allowed_next_work,
        forbidden_work=report.forbidden_work,
        test_matrix=report.test_matrix,
        risk_register=report.risk_register,
        next_actions=report.next_actions,
        rollback_plan=report.rollback_plan,
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
        raise ValueError("report_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("report_material_must_be_dict")
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
