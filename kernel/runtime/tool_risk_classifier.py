"""Tool risk classifier v1.

Deterministically classifies tool descriptors for dry-run planning. This module
does not execute tools, resolve commands, launch processes, call networks, call
providers, store credentials, or integrate plugins.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping
import hashlib
import json

__all__ = [
    "RISK_CLASSES",
    "ToolRiskAssessment",
    "ToolRiskDescriptor",
    "classify_tool_risk",
]

READ_ONLY = "READ_ONLY"
LOCAL_FILE_READ = "LOCAL_FILE_READ"
LOCAL_FILE_WRITE = "LOCAL_FILE_WRITE"
PROCESS_LAUNCH = "PROCESS_LAUNCH"
NETWORK_ACCESS = "NETWORK_ACCESS"
BROWSER_CONTROL = "BROWSER_CONTROL"
PROVIDER_API = "PROVIDER_API"
CREDENTIAL_TOUCHING = "CREDENTIAL_TOUCHING"
MCP_TOOL = "MCP_TOOL"
DCC_CONTROL = "DCC_CONTROL"
COMFYUI_EXECUTION = "COMFYUI_EXECUTION"
RENDER_EXECUTION = "RENDER_EXECUTION"
MODEL_EXECUTION = "MODEL_EXECUTION"
PLUGIN_EXECUTION = "PLUGIN_EXECUTION"
HIGH_RISK = "HIGH_RISK"

RISK_CLASSES = (
    READ_ONLY,
    LOCAL_FILE_READ,
    LOCAL_FILE_WRITE,
    PROCESS_LAUNCH,
    NETWORK_ACCESS,
    BROWSER_CONTROL,
    PROVIDER_API,
    CREDENTIAL_TOUCHING,
    MCP_TOOL,
    DCC_CONTROL,
    COMFYUI_EXECUTION,
    RENDER_EXECUTION,
    MODEL_EXECUTION,
    PLUGIN_EXECUTION,
    HIGH_RISK,
)

_RISK_RANK = {risk_class: index for index, risk_class in enumerate(RISK_CLASSES)}
_KNOWN_SOURCE_TYPES = frozenset(
    (
        "asset_inventory",
        "browser_automation",
        "comfyui_workflow",
        "dcc_app",
        "local_script",
        "mcp_server",
        "model_runtime",
        "plugin",
        "provider_api",
        "read_only_tool",
        "render_tool",
    )
)
_CAPABILITY_RISK = {
    "read_only": READ_ONLY,
    "local_file_read": LOCAL_FILE_READ,
    "local_file_write": LOCAL_FILE_WRITE,
    "process_launch": PROCESS_LAUNCH,
    "network_access": NETWORK_ACCESS,
    "browser_control": BROWSER_CONTROL,
    "provider_api": PROVIDER_API,
    "credential_touching": CREDENTIAL_TOUCHING,
    "mcp_tool": MCP_TOOL,
    "dcc_control": DCC_CONTROL,
    "comfyui_execution": COMFYUI_EXECUTION,
    "render_execution": RENDER_EXECUTION,
    "model_execution": MODEL_EXECUTION,
    "plugin_execution": PLUGIN_EXECUTION,
    "high_risk": HIGH_RISK,
}
_APPROVAL_RISKS = frozenset(
    (
        LOCAL_FILE_WRITE,
        PROCESS_LAUNCH,
        NETWORK_ACCESS,
        BROWSER_CONTROL,
        PROVIDER_API,
        DCC_CONTROL,
        COMFYUI_EXECUTION,
        RENDER_EXECUTION,
        MODEL_EXECUTION,
        PLUGIN_EXECUTION,
        HIGH_RISK,
    )
)


@dataclass(frozen=True)
class ToolRiskDescriptor:
    tool_id: str
    source_type: str
    declared_capabilities: tuple[str, ...]
    filesystem_scope: str
    network_scope: str
    process_scope: str
    credential_scope: str
    provider_scope: str
    dcc_scope: str
    model_scope: str
    browser_scope: str
    plugin_scope: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["declared_capabilities"] = list(self.declared_capabilities)
        return data


@dataclass(frozen=True)
class ToolRiskAssessment:
    tool_id: str
    risk_classes: tuple[str, ...]
    highest_risk: str
    approval_required: bool
    token_required: bool
    production_admission_allowed: bool
    reasons: tuple[str, ...]
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["risk_classes"] = list(self.risk_classes)
        data["reasons"] = list(self.reasons)
        return data


def classify_tool_risk(descriptor: ToolRiskDescriptor) -> ToolRiskAssessment:
    reasons: list[str] = []
    risk_classes: set[str] = set()

    if not isinstance(descriptor.tool_id, str) or not descriptor.tool_id.strip():
        risk_classes.add(HIGH_RISK)
        reasons.append("tool_id_required")

    if not isinstance(descriptor.source_type, str) or not descriptor.source_type.strip():
        risk_classes.add(HIGH_RISK)
        reasons.append("source_type_required")
    elif descriptor.source_type not in _KNOWN_SOURCE_TYPES:
        risk_classes.add(HIGH_RISK)
        reasons.append(f"source_type_unknown:{descriptor.source_type}")

    if not descriptor.declared_capabilities:
        risk_classes.add(HIGH_RISK)
        reasons.append("declared_capability_required")
    for capability in descriptor.declared_capabilities:
        risk_class = _CAPABILITY_RISK.get(capability)
        if risk_class is None:
            risk_classes.add(HIGH_RISK)
            reasons.append(f"declared_capability_unknown:{capability}")
        else:
            risk_classes.add(risk_class)
            reasons.append(f"declared_capability:{capability}")

    _add_scope_risks(descriptor, risk_classes, reasons)

    if not risk_classes:
        risk_classes.add(READ_ONLY)
        reasons.append("default_read_only")

    if CREDENTIAL_TOUCHING in risk_classes:
        risk_classes.add(HIGH_RISK)
        reasons.append("credential_touching_high_risk")

    if PLUGIN_EXECUTION in risk_classes and not _has_plugin_sandbox_strategy(
        descriptor.plugin_scope
    ):
        risk_classes.add(HIGH_RISK)
        reasons.append("plugin_sandbox_strategy_required")

    ordered_risks = tuple(sorted(risk_classes, key=lambda item: _RISK_RANK[item]))
    highest_risk = max(ordered_risks, key=lambda item: _RISK_RANK[item])
    approval_required = bool(_APPROVAL_RISKS.intersection(ordered_risks))
    token_required = approval_required
    production_admission_allowed = (
        highest_risk in {READ_ONLY, LOCAL_FILE_READ}
        and not approval_required
        and HIGH_RISK not in ordered_risks
    )

    fields = {
        "tool_id": descriptor.tool_id,
        "risk_classes": ordered_risks,
        "highest_risk": highest_risk,
        "approval_required": approval_required,
        "token_required": token_required,
        "production_admission_allowed": production_admission_allowed,
        "reasons": tuple(sorted(reasons)),
    }
    return ToolRiskAssessment(
        **fields,
        content_hash=_sha256(_canonical_json(fields)),
    )


def _add_scope_risks(
    descriptor: ToolRiskDescriptor,
    risk_classes: set[str],
    reasons: list[str],
) -> None:
    filesystem_scope = descriptor.filesystem_scope.lower()
    if "write" in filesystem_scope or "mutate" in filesystem_scope:
        risk_classes.add(LOCAL_FILE_WRITE)
        reasons.append("filesystem_scope_write")
    elif "read" in filesystem_scope:
        risk_classes.add(LOCAL_FILE_READ)
        reasons.append("filesystem_scope_read")

    if _scope_enabled(descriptor.network_scope):
        risk_classes.add(NETWORK_ACCESS)
        reasons.append("network_scope_enabled")
    if _scope_enabled(descriptor.process_scope):
        risk_classes.add(PROCESS_LAUNCH)
        reasons.append("process_scope_enabled")
    if _scope_enabled(descriptor.credential_scope):
        risk_classes.add(CREDENTIAL_TOUCHING)
        reasons.append("credential_scope_enabled")
    if _scope_enabled(descriptor.provider_scope):
        risk_classes.add(PROVIDER_API)
        reasons.append("provider_scope_enabled")
    if _scope_enabled(descriptor.dcc_scope):
        risk_classes.add(DCC_CONTROL)
        reasons.append("dcc_scope_enabled")
    if _scope_enabled(descriptor.model_scope):
        risk_classes.add(MODEL_EXECUTION)
        reasons.append("model_scope_enabled")
    if _scope_enabled(descriptor.browser_scope):
        risk_classes.add(BROWSER_CONTROL)
        reasons.append("browser_scope_enabled")
    if _scope_enabled(descriptor.plugin_scope):
        risk_classes.add(PLUGIN_EXECUTION)
        reasons.append("plugin_scope_enabled")


def _scope_enabled(value: str) -> bool:
    return value.lower() not in {"", "none", "no", "false", "read_only"}


def _has_plugin_sandbox_strategy(value: str) -> bool:
    normalized = value.lower().strip()
    return normalized in {
        "sandbox",
        "sandboxed",
        "sandbox_strategy",
        "sandbox_strategy_defined",
    }


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
