"""Tool manifest normalizer v1.

Normalizes external and local tool candidate metadata into a deterministic
internal manifest for dry-run ingestion. References are metadata only: this
module does not execute tools, resolve commands, launch processes, call
networks, call providers, load workflows, start browsers, or launch DCC apps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

__all__ = [
    "FORBIDDEN_MANIFEST_FIELDS",
    "SUPPORTED_SOURCE_TYPES",
    "NormalizedToolManifest",
    "RawToolManifestCandidate",
    "normalize_tool_manifest_candidate",
]

SUPPORTED_SOURCE_TYPES = (
    "MCP_SERVER",
    "MCP_TOOL",
    "CLI_TOOL",
    "LOCAL_SCRIPT",
    "API_ADAPTER",
    "DCC_APP",
    "DCC_PLUGIN",
    "COMFYUI_WORKFLOW",
    "GITHUB_REPO",
    "WASM_PLUGIN",
    "BROWSER_AUTOMATION_TOOL",
    "MODEL_RUNTIME",
    "RENDER_TOOL",
    "UNKNOWN",
)

FORBIDDEN_MANIFEST_FIELDS = frozenset(
    (
        "command",
        "raw_command",
        "command_line",
        "argv",
        "args",
        "shell",
        "script",
        "bash",
        "python_code",
        "executable",
        "executable_path",
        "workdir",
        "cwd",
        "env",
        "environment",
        "path",
        "path_override",
        "credential",
        "credentials",
        "secret",
        "token_value",
        "api_key",
        "password",
        "private_key",
        "timeout",
    )
)

_REQUIRED_FIELDS = (
    "source_type",
    "tool_name",
    "declared_capabilities",
    "declared_inputs",
    "declared_outputs",
    "filesystem_scope",
    "network_scope",
    "process_scope",
    "credential_scope",
    "provider_scope",
    "dcc_scope",
    "model_scope",
    "browser_scope",
    "plugin_scope",
)


@dataclass(frozen=True)
class RawToolManifestCandidate:
    source_type: str
    tool_name: str
    declared_capabilities: tuple[str, ...]
    declared_inputs: Mapping[str, object]
    declared_outputs: Mapping[str, object]
    filesystem_scope: str
    network_scope: str
    process_scope: str
    credential_scope: str
    provider_scope: str
    dcc_scope: str
    model_scope: str
    browser_scope: str
    plugin_scope: str
    version: str | None = None
    source_ref: str | None = None
    notes: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "RawToolManifestCandidate":
        failures = _forbidden_fields(payload)
        if failures:
            raise ValueError("forbidden_manifest_fields:" + ",".join(failures))
        missing = [field for field in _REQUIRED_FIELDS if field not in payload]
        if missing:
            raise ValueError("required_manifest_fields_missing:" + ",".join(missing))
        return cls(
            source_type=_required_string(payload, "source_type"),
            tool_name=_required_string(payload, "tool_name"),
            declared_capabilities=_string_tuple(payload["declared_capabilities"]),
            declared_inputs=_required_mapping(payload, "declared_inputs"),
            declared_outputs=_required_mapping(payload, "declared_outputs"),
            filesystem_scope=_required_string(payload, "filesystem_scope"),
            network_scope=_required_string(payload, "network_scope"),
            process_scope=_required_string(payload, "process_scope"),
            credential_scope=_required_string(payload, "credential_scope"),
            provider_scope=_required_string(payload, "provider_scope"),
            dcc_scope=_required_string(payload, "dcc_scope"),
            model_scope=_required_string(payload, "model_scope"),
            browser_scope=_required_string(payload, "browser_scope"),
            plugin_scope=_required_string(payload, "plugin_scope"),
            version=_optional_string(payload.get("version")),
            source_ref=_optional_string(payload.get("source_ref")),
            notes=_optional_string(payload.get("notes")),
        )

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["declared_capabilities"] = list(self.declared_capabilities)
        data["declared_inputs"] = _json_ready(self.declared_inputs)
        data["declared_outputs"] = _json_ready(self.declared_outputs)
        return data


@dataclass(frozen=True)
class NormalizedToolManifest:
    manifest_id: str
    source_type: str
    tool_id: str
    display_name: str
    declared_capabilities: tuple[str, ...]
    input_contract: Mapping[str, object]
    output_contract: Mapping[str, object]
    filesystem_scope: str
    network_scope: str
    process_scope: str
    credential_scope: str
    provider_scope: str
    dcc_scope: str
    model_scope: str
    browser_scope: str
    plugin_scope: str
    normalized_at: str
    content_hash: str
    direct_execution_allowed: bool
    runtime_integration_allowed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "source_type": self.source_type,
            "tool_id": self.tool_id,
            "display_name": self.display_name,
            "declared_capabilities": list(self.declared_capabilities),
            "input_contract": _json_ready(self.input_contract),
            "output_contract": _json_ready(self.output_contract),
            "filesystem_scope": self.filesystem_scope,
            "network_scope": self.network_scope,
            "process_scope": self.process_scope,
            "credential_scope": self.credential_scope,
            "provider_scope": self.provider_scope,
            "dcc_scope": self.dcc_scope,
            "model_scope": self.model_scope,
            "browser_scope": self.browser_scope,
            "plugin_scope": self.plugin_scope,
            "normalized_at": self.normalized_at,
            "content_hash": self.content_hash,
            "direct_execution_allowed": self.direct_execution_allowed,
            "runtime_integration_allowed": self.runtime_integration_allowed,
        }


def normalize_tool_manifest_candidate(
    candidate: RawToolManifestCandidate | Mapping[str, object],
    *,
    normalized_at: str | None = None,
) -> NormalizedToolManifest:
    """Normalize one tool candidate without admitting it to runtime execution."""

    if isinstance(candidate, Mapping):
        raw = RawToolManifestCandidate.from_mapping(candidate)
    else:
        raw = candidate
        failures = _forbidden_fields(raw.as_dict())
        if failures:
            raise ValueError("forbidden_manifest_fields:" + ",".join(failures))

    source_type = _normalize_source_type(raw.source_type)
    display_name = _clean_display_name(raw.tool_name)
    declared_capabilities = tuple(
        sorted({_normalize_token(capability) for capability in raw.declared_capabilities})
    )
    base_material = {
        "source_type": source_type,
        "tool_name": display_name,
        "declared_capabilities": declared_capabilities,
        "input_contract": _contract(raw.declared_inputs),
        "output_contract": _contract(raw.declared_outputs),
        "filesystem_scope": _scope(raw.filesystem_scope),
        "network_scope": _scope(raw.network_scope),
        "process_scope": _scope(raw.process_scope),
        "credential_scope": _scope(raw.credential_scope),
        "provider_scope": _scope(raw.provider_scope),
        "dcc_scope": _scope(raw.dcc_scope),
        "model_scope": _scope(raw.model_scope),
        "browser_scope": _scope(raw.browser_scope),
        "plugin_scope": _scope(raw.plugin_scope),
        "version": raw.version,
        "source_ref": raw.source_ref,
        "notes": raw.notes,
        "direct_execution_allowed": False,
        "runtime_integration_allowed": False,
    }
    manifest_id = "manifest_" + _sha256(_canonical_json(base_material)).removeprefix(
        "sha256:"
    )[:32]
    fields = {
        "manifest_id": manifest_id,
        "source_type": source_type,
        "tool_id": f"tool.{source_type.lower()}.{_slug(display_name)}",
        "display_name": display_name,
        "declared_capabilities": declared_capabilities,
        "input_contract": base_material["input_contract"],
        "output_contract": base_material["output_contract"],
        "filesystem_scope": base_material["filesystem_scope"],
        "network_scope": base_material["network_scope"],
        "process_scope": base_material["process_scope"],
        "credential_scope": base_material["credential_scope"],
        "provider_scope": base_material["provider_scope"],
        "dcc_scope": base_material["dcc_scope"],
        "model_scope": base_material["model_scope"],
        "browser_scope": base_material["browser_scope"],
        "plugin_scope": base_material["plugin_scope"],
        "direct_execution_allowed": False,
        "runtime_integration_allowed": False,
    }
    return NormalizedToolManifest(
        **fields,
        normalized_at=normalized_at or _now(),
        content_hash=_sha256(_canonical_json(fields)),
    )


def _normalize_source_type(source_type: str) -> str:
    normalized = _normalize_token(source_type).upper()
    return normalized if normalized in SUPPORTED_SOURCE_TYPES else "UNKNOWN"


def _clean_display_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("tool_name_required")
    return cleaned


def _normalize_token(value: object) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip()).strip("_")
    return normalized.lower() or "unknown"


def _slug(value: str) -> str:
    return _normalize_token(value).replace("_", "-")


def _scope(value: str) -> str:
    return " ".join(value.strip().split()).lower() or "none"


def _contract(value: Mapping[str, object]) -> dict[str, object]:
    failures = _forbidden_fields(value)
    if failures:
        raise ValueError("forbidden_manifest_fields:" + ",".join(failures))
    return _json_ready(value)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("optional_manifest_string_invalid")
    return value.strip()


def _required_mapping(payload: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    return dict(value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("declared_capabilities_must_be_nonempty_sequence")
    values = tuple(str(entry).strip() for entry in value if str(entry).strip())
    if not values:
        raise ValueError("declared_capabilities_must_be_nonempty_sequence")
    return values


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = _normalize_token(key)
        if normalized in FORBIDDEN_MANIFEST_FIELDS:
            found.add(normalized)
        if isinstance(value, Mapping):
            found.update(_forbidden_fields(value))
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    found.update(_forbidden_fields(item))
    return tuple(sorted(found))


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
