"""Deterministic public-safe asset manifest reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import json

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "PublicAssetItem",
    "PublicAssetManifest",
    "build_public_asset_manifest",
    "render_public_asset_manifest_markdown",
]

_POLICY_VERSION = "public-asset-manifest-v1"
_CODE_VERSION = "0.1.0"
_OBSERVED_AT_NOT_PROVIDED = "not_provided"

_REQUIRED_STRING_FIELDS = (
    "manifest_id",
    "repository_url",
    "main_commit",
    "policy_version",
    "code_version",
)
_REQUIRED_DICT_FIELDS = ("verification_matrix",)
_REQUIRED_LIST_FIELDS = (
    "asset_items",
    "blocked_capabilities",
    "safety_boundaries",
    "public_release_notes",
)
_REQUIRED_INPUT_FIELDS = _REQUIRED_STRING_FIELDS + _REQUIRED_DICT_FIELDS + _REQUIRED_LIST_FIELDS

_REQUIRED_ASSET_STRING_FIELDS = (
    "asset_id",
    "path",
    "asset_type",
    "purpose",
    "verification_status",
)
_OPTIONAL_ASSET_DIGEST_FIELDS = ("content_hash", "declared_hash")

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
class PublicAssetItem:
    """One public-safe repository asset included in a manifest."""

    asset_id: str
    path: str
    asset_type: str
    public_safe: bool
    purpose: str
    verification_status: str
    content_hash: str | None = None
    declared_hash: str | None = None

    def deterministic_material(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "path": self.path,
            "public_safe": self.public_safe,
            "purpose": self.purpose,
            "verification_status": self.verification_status,
        }
        if self.content_hash is not None:
            payload["content_hash"] = self.content_hash
        if self.declared_hash is not None:
            payload["declared_hash"] = self.declared_hash
        return payload

    def as_dict(self) -> dict[str, object]:
        return self.deterministic_material()


@dataclass(frozen=True)
class PublicAssetManifest:
    """Repository-ready deterministic public asset manifest."""

    manifest_id: str
    repository_url: str
    main_commit: str
    asset_items: tuple[PublicAssetItem, ...]
    verification_matrix: dict[str, object]
    blocked_capabilities: tuple[object, ...]
    safety_boundaries: tuple[object, ...]
    public_release_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = _OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_items": [item.deterministic_material() for item in self.asset_items],
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "main_commit": self.main_commit,
            "manifest_id": self.manifest_id,
            "policy_version": self.policy_version,
            "public_release_notes": list(self.public_release_notes),
            "repository_url": self.repository_url,
            "safety_boundaries": list(self.safety_boundaries),
            "verification_matrix": self.verification_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_public_asset_manifest(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> PublicAssetManifest:
    """Build a deterministic public asset manifest from caller-provided material."""

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
    asset_items = tuple(_build_asset_item(item, index) for index, item in enumerate(normalized["asset_items"]))

    manifest = PublicAssetManifest(
        manifest_id=normalized["manifest_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        asset_items=asset_items,
        verification_matrix=normalized["verification_matrix"],
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        safety_boundaries=tuple(normalized["safety_boundaries"]),
        public_release_notes=tuple(normalized["public_release_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(manifest)


def render_public_asset_manifest_markdown(manifest: PublicAssetManifest) -> str:
    """Render manifest Markdown with deterministic section ordering."""

    if not isinstance(manifest, PublicAssetManifest):
        raise ValueError("manifest_must_be_public_asset_manifest")
    lines = [
        "# Sovereign Production OS Public Asset Manifest",
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
        "## Asset Items",
    ]
    for item in manifest.asset_items:
        lines.extend(_render_asset_item(item))
    lines.extend(
        [
            "",
            "## Verification Matrix",
            *_render_value(manifest.verification_matrix),
            "",
            "## Blocked Capabilities",
            *_render_value(list(manifest.blocked_capabilities)),
            "",
            "## Safety Boundaries",
            *_render_value(list(manifest.safety_boundaries)),
            "",
            "## Public Release Notes",
            *_render_value(list(manifest.public_release_notes)),
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _with_hash(manifest: PublicAssetManifest) -> PublicAssetManifest:
    return PublicAssetManifest(
        manifest_id=manifest.manifest_id,
        repository_url=manifest.repository_url,
        main_commit=manifest.main_commit,
        asset_items=manifest.asset_items,
        verification_matrix=manifest.verification_matrix,
        blocked_capabilities=manifest.blocked_capabilities,
        safety_boundaries=manifest.safety_boundaries,
        public_release_notes=manifest.public_release_notes,
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
    for field in _REQUIRED_DICT_FIELDS:
        if not isinstance(material[field], dict):
            raise ValueError(f"{field}_must_be_dict")
    for field in _REQUIRED_LIST_FIELDS:
        if not isinstance(material[field], list):
            raise ValueError(f"{field}_must_be_list")
    if not material["asset_items"]:
        raise ValueError("asset_items_must_not_be_empty")


def _build_asset_item(value: object, index: int) -> PublicAssetItem:
    if not isinstance(value, dict):
        raise ValueError(f"asset_items[{index}]_must_be_dict")
    for field in _REQUIRED_ASSET_STRING_FIELDS:
        if not strict_nonempty_string(value.get(field)):
            raise ValueError(f"asset_items[{index}].{field}_must_be_nonempty_string")
    if not strict_bool(value.get("public_safe")):
        raise ValueError(f"asset_items[{index}].public_safe_must_be_bool")
    if value["public_safe"] is not True:
        raise ValueError(f"asset_items[{index}].public_safe_must_be_true")
    for field in _OPTIONAL_ASSET_DIGEST_FIELDS:
        if field in value and value[field] is not None and not strict_digest(value[field]):
            raise ValueError(f"asset_items[{index}].{field}_must_be_valid_digest")
    return PublicAssetItem(
        asset_id=value["asset_id"],
        path=value["path"],
        asset_type=value["asset_type"],
        public_safe=value["public_safe"],
        purpose=value["purpose"],
        verification_status=value["verification_status"],
        content_hash=value.get("content_hash"),
        declared_hash=value.get("declared_hash"),
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


def _render_asset_item(item: PublicAssetItem) -> list[str]:
    lines = [
        f"### {item.asset_id}",
        f"- path: {item.path}",
        f"- asset_type: {item.asset_type}",
        f"- public_safe: {'true' if item.public_safe else 'false'}",
        f"- purpose: {item.purpose}",
        f"- verification_status: {item.verification_status}",
    ]
    if item.content_hash is not None:
        lines.append(f"- content_hash: {item.content_hash}")
    if item.declared_hash is not None:
        lines.append(f"- declared_hash: {item.declared_hash}")
    return lines


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
