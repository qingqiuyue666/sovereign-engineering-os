"""Tool manifest risk binding v1.

Binds normalized dry-run tool manifests to the existing tool risk classifier.
This module never executes tools, calls networks, calls providers, contacts MCP
servers, launches browsers, launches DCC apps, or loads ComfyUI workflows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json

from kernel.runtime.tool_manifest_normalizer import NormalizedToolManifest
from kernel.runtime.tool_risk_classifier import (
    ToolRiskAssessment,
    ToolRiskDescriptor,
    classify_tool_risk,
)

__all__ = [
    "ToolManifestRiskBindingReport",
    "bind_tool_manifest_risk",
]

_SOURCE_TYPE_MAP = {
    "MCP_SERVER": "mcp_server",
    "MCP_TOOL": "mcp_server",
    "CLI_TOOL": "read_only_tool",
    "LOCAL_SCRIPT": "local_script",
    "API_ADAPTER": "provider_api",
    "DCC_APP": "dcc_app",
    "DCC_PLUGIN": "plugin",
    "COMFYUI_WORKFLOW": "comfyui_workflow",
    "GITHUB_REPO": "read_only_tool",
    "WASM_PLUGIN": "plugin",
    "BROWSER_AUTOMATION_TOOL": "browser_automation",
    "MODEL_RUNTIME": "model_runtime",
    "RENDER_TOOL": "render_tool",
    "UNKNOWN": "unknown_manifest_source",
}

_SOURCE_CAPABILITY_HINTS = {
    "MCP_SERVER": ("mcp_tool",),
    "MCP_TOOL": ("mcp_tool",),
    "DCC_APP": ("dcc_control",),
    "DCC_PLUGIN": ("dcc_control", "plugin_execution"),
    "COMFYUI_WORKFLOW": ("comfyui_execution",),
    "BROWSER_AUTOMATION_TOOL": ("browser_control",),
    "MODEL_RUNTIME": ("model_execution",),
    "RENDER_TOOL": ("render_execution",),
    "WASM_PLUGIN": ("plugin_execution",),
    "UNKNOWN": ("high_risk",),
}


@dataclass(frozen=True)
class ToolManifestRiskBindingReport:
    manifest_id: str
    tool_id: str
    source_type: str
    risk_classes: tuple[str, ...]
    highest_risk: str
    approval_required: bool
    token_required: bool
    production_admission_allowed: bool
    reasons: tuple[str, ...]
    manifest_content_hash: str
    risk_content_hash: str
    binding_hash: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["risk_classes"] = list(self.risk_classes)
        data["reasons"] = list(self.reasons)
        return data


def bind_tool_manifest_risk(
    manifest: NormalizedToolManifest | Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> ToolManifestRiskBindingReport:
    """Classify a normalized manifest with the existing risk classifier."""

    normalized = _manifest(manifest)
    descriptor = _descriptor_from_manifest(normalized)
    assessment = classify_tool_risk(descriptor)
    reasons = tuple(
        sorted(
            set(assessment.reasons)
            | {
                f"manifest_source_type:{normalized.source_type}",
                f"manifest_content_hash:{normalized.content_hash}",
            }
        )
    )
    production_admission_allowed = (
        assessment.production_admission_allowed
        and normalized.runtime_integration_allowed
        and normalized.direct_execution_allowed
        and assessment.highest_risk != "HIGH_RISK"
    )
    fields = {
        "manifest_id": normalized.manifest_id,
        "tool_id": normalized.tool_id,
        "source_type": normalized.source_type,
        "risk_classes": assessment.risk_classes,
        "highest_risk": assessment.highest_risk,
        "approval_required": assessment.approval_required,
        "token_required": assessment.token_required,
        "production_admission_allowed": production_admission_allowed,
        "reasons": reasons,
        "manifest_content_hash": normalized.content_hash,
        "risk_content_hash": assessment.content_hash,
    }
    return ToolManifestRiskBindingReport(
        **fields,
        binding_hash=_sha256(_canonical_json(fields)),
        observed_at=observed_at or _now(),
    )


def _descriptor_from_manifest(manifest: NormalizedToolManifest) -> ToolRiskDescriptor:
    capabilities = set(manifest.declared_capabilities)
    capabilities.update(_SOURCE_CAPABILITY_HINTS.get(manifest.source_type, ()))
    if _scope_enabled(manifest.provider_scope):
        capabilities.add("provider_api")
    if _scope_enabled(manifest.credential_scope):
        capabilities.add("credential_touching")
    if manifest.source_type == "COMFYUI_WORKFLOW" and _scope_enabled(manifest.model_scope):
        capabilities.add("model_execution")
    if manifest.source_type == "CLI_TOOL" and _scope_enabled(manifest.process_scope):
        capabilities.add("process_launch")
    if not capabilities:
        capabilities.add("read_only")

    return ToolRiskDescriptor(
        tool_id=manifest.tool_id,
        source_type=_SOURCE_TYPE_MAP.get(manifest.source_type, "unknown_manifest_source"),
        declared_capabilities=tuple(sorted(capabilities)),
        filesystem_scope=manifest.filesystem_scope,
        network_scope=manifest.network_scope,
        process_scope=manifest.process_scope,
        credential_scope=manifest.credential_scope,
        provider_scope=manifest.provider_scope,
        dcc_scope=manifest.dcc_scope,
        model_scope=manifest.model_scope,
        browser_scope=manifest.browser_scope,
        plugin_scope=manifest.plugin_scope,
    )


def _manifest(value: NormalizedToolManifest | Mapping[str, object]) -> NormalizedToolManifest:
    if isinstance(value, NormalizedToolManifest):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("manifest_must_be_normalized_manifest_or_mapping")
    return NormalizedToolManifest(
        manifest_id=_required_string(value, "manifest_id"),
        source_type=_required_string(value, "source_type"),
        tool_id=_required_string(value, "tool_id"),
        display_name=_required_string(value, "display_name"),
        declared_capabilities=tuple(str(item) for item in value.get("declared_capabilities", ())),
        input_contract=_required_mapping(value, "input_contract"),
        output_contract=_required_mapping(value, "output_contract"),
        filesystem_scope=_required_string(value, "filesystem_scope"),
        network_scope=_required_string(value, "network_scope"),
        process_scope=_required_string(value, "process_scope"),
        credential_scope=_required_string(value, "credential_scope"),
        provider_scope=_required_string(value, "provider_scope"),
        dcc_scope=_required_string(value, "dcc_scope"),
        model_scope=_required_string(value, "model_scope"),
        browser_scope=_required_string(value, "browser_scope"),
        plugin_scope=_required_string(value, "plugin_scope"),
        normalized_at=_required_string(value, "normalized_at"),
        content_hash=_required_string(value, "content_hash"),
        direct_execution_allowed=bool(value.get("direct_execution_allowed")),
        runtime_integration_allowed=bool(value.get("runtime_integration_allowed")),
    )


def _scope_enabled(value: str) -> bool:
    return value.lower().strip() not in {"", "none", "no", "false", "read_only"}


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _required_mapping(payload: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    return dict(value)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
