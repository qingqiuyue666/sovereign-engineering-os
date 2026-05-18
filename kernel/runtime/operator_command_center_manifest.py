"""Deterministic private operator command-center manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "OperatorCommandCenterDocument",
    "OperatorCommandCenterManifest",
    "build_operator_command_center_manifest",
    "render_operator_command_center_manifest_markdown",
]

_POLICY_VERSION = "operator-command-center-manifest-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "manifest_id",
    "repository_url",
    "main_commit",
    "policy_version",
    "code_version",
)
_REQUIRED_LIST_FIELDS = (
    "documents",
    "linked_reports",
    "current_priorities",
    "blocked_capabilities",
    "mandatory_verification",
)
_REQUIRED_INPUT_FIELDS = _REQUIRED_STRING_FIELDS + _REQUIRED_LIST_FIELDS
_REQUIRED_DOCUMENT_STRING_FIELDS = ("document_id", "path", "title", "purpose")

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


@dataclass(frozen=True)
class OperatorCommandCenterDocument:
    """One private operator document tracked by the command center."""

    document_id: str
    path: str
    title: str
    purpose: str
    private_operator_only: bool
    required_sections: tuple[object, ...]

    def deterministic_material(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "path": self.path,
            "private_operator_only": self.private_operator_only,
            "purpose": self.purpose,
            "required_sections": list(self.required_sections),
            "title": self.title,
        }

    def as_dict(self) -> dict[str, object]:
        return self.deterministic_material()


@dataclass(frozen=True)
class OperatorCommandCenterManifest:
    """Repository-ready manifest for the private operator command center."""

    manifest_id: str
    repository_url: str
    main_commit: str
    documents: tuple[OperatorCommandCenterDocument, ...]
    linked_reports: tuple[object, ...]
    current_priorities: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    mandatory_verification: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "current_priorities": list(self.current_priorities),
            "documents": [document.deterministic_material() for document in self.documents],
            "linked_reports": list(self.linked_reports),
            "main_commit": self.main_commit,
            "mandatory_verification": list(self.mandatory_verification),
            "manifest_id": self.manifest_id,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_command_center_manifest(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorCommandCenterManifest:
    """Build a deterministic manifest from caller-provided material."""

    if not isinstance(material, dict):
        raise ValueError("manifest_material_must_be_dict")
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
    documents = tuple(_build_document(item, index) for index, item in enumerate(normalized["documents"]))

    manifest = OperatorCommandCenterManifest(
        manifest_id=normalized["manifest_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        documents=documents,
        linked_reports=tuple(normalized["linked_reports"]),
        current_priorities=tuple(normalized["current_priorities"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        mandatory_verification=tuple(normalized["mandatory_verification"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(manifest)


def render_operator_command_center_manifest_markdown(manifest: OperatorCommandCenterManifest) -> str:
    """Render manifest Markdown with deterministic section ordering."""

    if not isinstance(manifest, OperatorCommandCenterManifest):
        raise ValueError("manifest_must_be_operator_command_center_manifest")
    lines = [
        "# Private Operator Command Center Manifest",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| manifest_id | {_escape_table(manifest.manifest_id)} |",
        f"| repository_url | {_escape_table(manifest.repository_url)} |",
        f"| main_commit | {_escape_table(manifest.main_commit)} |",
        f"| policy_version | {_escape_table(manifest.policy_version)} |",
        f"| code_version | {_escape_table(manifest.code_version)} |",
        f"| content_hash | {_escape_table(manifest.content_hash)} |",
        f"| observed_at | {_escape_table(manifest.observed_at)} |",
        "",
        "## Documents",
    ]
    for document in manifest.documents:
        lines.extend(_render_document(document))
    lines.extend(
        [
            "",
            "## Linked Reports",
            *_render_value(list(manifest.linked_reports)),
            "",
            "## Current Priorities",
            *_render_value(list(manifest.current_priorities)),
            "",
            "## Blocked Capabilities",
            *_render_value(list(manifest.blocked_capabilities)),
            "",
            "## Mandatory Verification",
            *_render_value(list(manifest.mandatory_verification)),
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(manifest: OperatorCommandCenterManifest) -> OperatorCommandCenterManifest:
    return OperatorCommandCenterManifest(
        manifest_id=manifest.manifest_id,
        repository_url=manifest.repository_url,
        main_commit=manifest.main_commit,
        documents=manifest.documents,
        linked_reports=manifest.linked_reports,
        current_priorities=manifest.current_priorities,
        blocked_capabilities=manifest.blocked_capabilities,
        mandatory_verification=manifest.mandatory_verification,
        policy_version=manifest.policy_version,
        code_version=manifest.code_version,
        content_hash=digest_payload(manifest.deterministic_material()),
        observed_at=manifest.observed_at,
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


def _build_document(value: object, index: int) -> OperatorCommandCenterDocument:
    if not isinstance(value, dict):
        raise ValueError(f"documents[{index}]_must_be_dict")
    for field in _REQUIRED_DOCUMENT_STRING_FIELDS:
        if not strict_nonempty_string(value.get(field)):
            raise ValueError(f"documents[{index}].{field}_must_be_nonempty_string")
    if not strict_bool(value.get("private_operator_only")):
        raise ValueError(f"documents[{index}].private_operator_only_must_be_bool")
    if value["private_operator_only"] is not True:
        raise ValueError(f"documents[{index}].private_operator_only_must_be_true")
    if not isinstance(value.get("required_sections"), list):
        raise ValueError(f"documents[{index}].required_sections_must_be_list")
    if not value["required_sections"]:
        raise ValueError(f"documents[{index}].required_sections_must_not_be_empty")
    return OperatorCommandCenterDocument(
        document_id=value["document_id"],
        path=value["path"],
        title=value["title"],
        purpose=value["purpose"],
        private_operator_only=value["private_operator_only"],
        required_sections=tuple(value["required_sections"]),
    )


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
        raise ValueError("manifest_material_must_be_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("manifest_material_must_be_dict")
    return normalized


def _render_document(document: OperatorCommandCenterDocument) -> list[str]:
    return [
        f"### {document.document_id}",
        f"- path: {document.path}",
        f"- title: {document.title}",
        f"- purpose: {document.purpose}",
        f"- private_operator_only: {'true' if document.private_operator_only else 'false'}",
        "- required_sections:",
        *_render_value(list(document.required_sections), 1),
    ]


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
