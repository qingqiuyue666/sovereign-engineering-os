"""Tool approval requirement binding v1.

Turns tool risk assessments into approval requirement records for dry-run
planning. Requirement records are not approval tokens and do not execute tools.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json

from kernel.runtime.human_approval_token import SUPPORTED_ACTION_TYPES
from kernel.runtime.tool_manifest_risk_binding import ToolManifestRiskBindingReport
from kernel.runtime.tool_risk_classifier import (
    BROWSER_CONTROL,
    COMFYUI_EXECUTION,
    CREDENTIAL_TOUCHING,
    DCC_CONTROL,
    HIGH_RISK,
    LOCAL_FILE_READ,
    LOCAL_FILE_WRITE,
    MCP_TOOL,
    MODEL_EXECUTION,
    NETWORK_ACCESS,
    PLUGIN_EXECUTION,
    PROCESS_LAUNCH,
    PROVIDER_API,
    READ_ONLY,
    RENDER_EXECUTION,
    ToolRiskAssessment,
)

__all__ = [
    "ApprovalRequirement",
    "generate_approval_requirement",
    "generate_approval_requirements",
]

_APPROVAL_RISK_CLASSES = frozenset(
    (
        LOCAL_FILE_WRITE,
        PROCESS_LAUNCH,
        NETWORK_ACCESS,
        BROWSER_CONTROL,
        PROVIDER_API,
        CREDENTIAL_TOUCHING,
        DCC_CONTROL,
        COMFYUI_EXECUTION,
        RENDER_EXECUTION,
        MODEL_EXECUTION,
        PLUGIN_EXECUTION,
        HIGH_RISK,
    )
)

_PRODUCTION_BLOCKING_RISK_CLASSES = frozenset(
    (
        HIGH_RISK,
        DCC_CONTROL,
        COMFYUI_EXECUTION,
    )
)

_ACTION_PRIORITY = (
    (CREDENTIAL_TOUCHING, "CALL_PROVIDER"),
    (COMFYUI_EXECUTION, "RUN_COMFYUI"),
    (DCC_CONTROL, "RUN_DCC_APP"),
    (PLUGIN_EXECUTION, "RUN_PLUGIN"),
    (BROWSER_CONTROL, "BROWSER_CONTROL"),
    (PROVIDER_API, "CALL_PROVIDER"),
    (NETWORK_ACCESS, "ACCESS_NETWORK"),
    (PROCESS_LAUNCH, "LAUNCH_PROCESS"),
    (LOCAL_FILE_WRITE, "WRITE_PATH"),
    (MCP_TOOL, "CALL_MCP_TOOL"),
    (MODEL_EXECUTION, "RUN_MODEL"),
    (RENDER_EXECUTION, "RUN_DCC_APP"),
    (LOCAL_FILE_READ, "READ_PATH"),
    (READ_ONLY, "READ_PATH"),
    (HIGH_RISK, "DRY_RUN_COMMAND_ID"),
)


@dataclass(frozen=True)
class ApprovalRequirement:
    requirement_id: str
    tool_id: str
    manifest_id: str | None
    source_type: str
    required_action_type: str
    required_scope_id: str
    target_id: str
    risk_class: str
    approval_required: bool
    token_required: bool
    reason: str
    expires_required: bool
    revocation_required: bool
    production_admission_allowed: bool
    content_hash: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def generate_approval_requirement(
    risk_report: ToolRiskAssessment | ToolManifestRiskBindingReport | Mapping[str, object],
    *,
    manifest_id: str | None = None,
    source_type: str | None = None,
    required_scope_id: str | None = None,
    target_id: str | None = None,
    observed_at: str | None = None,
) -> ApprovalRequirement:
    """Generate one requirement record without creating an approval decision."""

    report = _report_dict(risk_report)
    risk_classes = _risk_classes(report)
    risk_class = _risk_class(report, risk_classes)
    tool_id = _required_string(report, "tool_id")
    resolved_manifest_id = manifest_id or _optional_string(report.get("manifest_id"))
    resolved_source_type = source_type or _optional_string(report.get("source_type")) or "unknown"
    resolved_scope_id = required_scope_id or _default_scope_id(
        tool_id=tool_id,
        risk_classes=risk_classes,
        source_type=resolved_source_type,
    )
    resolved_target_id = target_id or resolved_manifest_id or tool_id
    action_type = _action_type(risk_classes)
    approval_required = _approval_required(risk_classes, resolved_scope_id)
    token_required = _token_required(risk_classes, approval_required)
    production_admission_allowed = _production_admission_allowed(
        report=report,
        risk_classes=risk_classes,
        approval_required=approval_required,
    )
    reasons = _reasons(
        report=report,
        risk_classes=risk_classes,
        approval_required=approval_required,
        token_required=token_required,
        production_admission_allowed=production_admission_allowed,
    )
    fields = {
        "tool_id": tool_id,
        "manifest_id": resolved_manifest_id,
        "source_type": resolved_source_type,
        "required_action_type": action_type,
        "required_scope_id": resolved_scope_id,
        "target_id": resolved_target_id,
        "risk_class": risk_class,
        "approval_required": approval_required,
        "token_required": token_required,
        "reason": ";".join(reasons),
        "expires_required": token_required,
        "revocation_required": token_required,
        "production_admission_allowed": production_admission_allowed,
    }
    content_hash = _sha256(_canonical_json(fields))
    return ApprovalRequirement(
        requirement_id="approval_requirement_" + content_hash.removeprefix("sha256:")[:32],
        **fields,
        content_hash=content_hash,
        observed_at=observed_at or _now(),
    )


def generate_approval_requirements(
    risk_reports: tuple[
        ToolRiskAssessment | ToolManifestRiskBindingReport | Mapping[str, object], ...
    ]
    | list[ToolRiskAssessment | ToolManifestRiskBindingReport | Mapping[str, object]],
    *,
    observed_at: str | None = None,
) -> tuple[ApprovalRequirement, ...]:
    return tuple(
        generate_approval_requirement(report, observed_at=observed_at)
        for report in risk_reports
    )


def _report_dict(
    value: ToolRiskAssessment | ToolManifestRiskBindingReport | Mapping[str, object],
) -> Mapping[str, object]:
    if isinstance(value, (ToolRiskAssessment, ToolManifestRiskBindingReport)):
        return value.as_dict()
    if not isinstance(value, Mapping):
        raise ValueError("risk_report_must_be_assessment_binding_or_mapping")
    return dict(value)


def _risk_classes(report: Mapping[str, object]) -> tuple[str, ...]:
    value = report.get("risk_classes")
    if isinstance(value, (tuple, list)) and value:
        return tuple(str(item) for item in value if str(item).strip())
    risk_class = report.get("risk_class") or report.get("highest_risk")
    if isinstance(risk_class, str) and risk_class.strip():
        return (risk_class.strip(),)
    raise ValueError("risk_classes_required")


def _risk_class(report: Mapping[str, object], risk_classes: tuple[str, ...]) -> str:
    highest = report.get("highest_risk") or report.get("risk_class")
    if isinstance(highest, str) and highest.strip():
        return highest.strip()
    if HIGH_RISK in risk_classes:
        return HIGH_RISK
    return risk_classes[-1]


def _action_type(risk_classes: tuple[str, ...]) -> str:
    risk_set = set(risk_classes)
    for risk_class, action_type in _ACTION_PRIORITY:
        if risk_class in risk_set:
            if action_type not in SUPPORTED_ACTION_TYPES:
                raise ValueError("approval_action_type_not_supported:" + action_type)
            return action_type
    raise ValueError("approval_action_type_not_supported_for_risk")


def _approval_required(risk_classes: tuple[str, ...], scope_id: str) -> bool:
    risk_set = set(risk_classes)
    if MCP_TOOL in risk_set and _read_only_and_bounded(risk_set, scope_id):
        return False
    if _APPROVAL_RISK_CLASSES.intersection(risk_set):
        return True
    if MCP_TOOL in risk_set:
        return True
    return False


def _token_required(risk_classes: tuple[str, ...], approval_required: bool) -> bool:
    risk_set = set(risk_classes)
    return approval_required or LOCAL_FILE_READ in risk_set or MCP_TOOL in risk_set


def _production_admission_allowed(
    *,
    report: Mapping[str, object],
    risk_classes: tuple[str, ...],
    approval_required: bool,
) -> bool:
    risk_set = set(risk_classes)
    if _PRODUCTION_BLOCKING_RISK_CLASSES.intersection(risk_set):
        return False
    if approval_required:
        return False
    if "production_admission_allowed" in report:
        return bool(report["production_admission_allowed"])
    return risk_set.issubset({READ_ONLY, LOCAL_FILE_READ, MCP_TOOL})


def _reasons(
    *,
    report: Mapping[str, object],
    risk_classes: tuple[str, ...],
    approval_required: bool,
    token_required: bool,
    production_admission_allowed: bool,
) -> tuple[str, ...]:
    reasons = set(_string_items(report.get("reasons")))
    risk_set = set(risk_classes)
    if not approval_required:
        reasons.add("explicit_approval_not_required_by_policy")
    else:
        reasons.add("human_approval_required_by_policy")
    if token_required:
        reasons.add("scoped_approval_token_required")
        reasons.add("token_expiry_and_revocation_required")
    else:
        reasons.add("approval_token_not_required_by_policy")
    if CREDENTIAL_TOUCHING in risk_set or HIGH_RISK in risk_set:
        reasons.add("implicit_approval_forbidden")
    if PLUGIN_EXECUTION in risk_set:
        reasons.add("plugin_sandbox_strategy_required")
    if DCC_CONTROL in risk_set:
        reasons.add("dcc_control_not_production_admitted_by_default")
    if COMFYUI_EXECUTION in risk_set:
        reasons.add("comfyui_execution_not_production_admitted_by_default")
    if not production_admission_allowed:
        reasons.add("production_admission_blocked_or_deferred")
    reasons.add("approval_requirement_only")
    reasons.add("accepted_decision_not_created")
    reasons.add("tool_execution_not_allowed")
    return tuple(sorted(reasons))


def _default_scope_id(
    *,
    tool_id: str,
    risk_classes: tuple[str, ...],
    source_type: str,
) -> str:
    risk_set = set(risk_classes)
    if LOCAL_FILE_READ in risk_set or LOCAL_FILE_WRITE in risk_set:
        return "scope:filesystem:unbounded"
    if MCP_TOOL in risk_set:
        return "scope:mcp:unbounded"
    return "scope:tool:" + source_type + ":" + tool_id


def _read_only_and_bounded(risk_set: set[str], scope_id: str) -> bool:
    return risk_set.issubset({READ_ONLY, LOCAL_FILE_READ, MCP_TOOL}) and _bounded_scope(
        scope_id
    )


def _bounded_scope(scope_id: str) -> bool:
    normalized = scope_id.strip().lower()
    if not normalized:
        return False
    blocked_markers = ("*", "unbounded", "global", "all")
    return not any(marker in normalized for marker in blocked_markers)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
