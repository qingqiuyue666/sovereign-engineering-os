"""Deterministic manifest for the non-core production asset kit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_required_members,
    require_string_fields,
)

__all__ = [
    "NONCORE_REQUIRED_ASSET_GROUPS",
    "NoncoreAssetKitManifest",
    "build_noncore_asset_kit_manifest",
    "render_noncore_asset_kit_manifest_markdown",
]

_POLICY_VERSION = "noncore-asset-kit-manifest-v1"
_CODE_VERSION = "0.1.0"

NONCORE_REQUIRED_ASSET_GROUPS = (
    "documents",
    "templates",
    "examples",
    "forms",
    "sprint_artifacts",
)

_STRING_FIELDS = (
    "manifest_id",
    "repository_url",
    "main_commit",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "asset_groups",
    "documents",
    "templates",
    "examples",
    "forms",
    "sprint_artifacts",
    "blocked_capabilities",
)
_DICT_FIELDS = ("verification_matrix",)
_FORBIDDEN_EXTRA_FIELDS = frozenset(
    {
        "raw_prompt",
        "raw_response",
        "raw_provider_response",
        "raw_exception",
        "raw_traceback",
        "env",
        "environment",
        "environment_variables",
        "secret",
        "credentials",
        "credential",
        "token",
        "api_key",
        "password",
        "private_key",
        "authorization",
        "content_hash",
    }
)


@dataclass(frozen=True)
class NoncoreAssetKitManifest:
    """Repository-ready deterministic manifest for non-core production assets."""

    manifest_id: str
    repository_url: str
    main_commit: str
    asset_groups: tuple[object, ...]
    documents: tuple[object, ...]
    templates: tuple[object, ...]
    examples: tuple[object, ...]
    forms: tuple[object, ...]
    sprint_artifacts: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    verification_matrix: dict[str, object]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_groups": list(self.asset_groups),
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "documents": list(self.documents),
            "examples": list(self.examples),
            "forms": list(self.forms),
            "main_commit": self.main_commit,
            "manifest_id": self.manifest_id,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "sprint_artifacts": list(self.sprint_artifacts),
            "templates": list(self.templates),
            "verification_matrix": self.verification_matrix,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_noncore_asset_kit_manifest(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> NoncoreAssetKitManifest:
    """Build a deterministic manifest for the non-core production asset kit."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="noncore_asset_kit_manifest_material",
    )
    _reject_forbidden_top_level_fields(normalized)
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_required_members(
        normalized["asset_groups"],
        NONCORE_REQUIRED_ASSET_GROUPS,
        field="asset_groups",
    )
    _validate_group_paths(normalized)

    manifest = NoncoreAssetKitManifest(
        manifest_id=normalized["manifest_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        asset_groups=tuple(normalized["asset_groups"]),
        documents=tuple(normalized["documents"]),
        templates=tuple(normalized["templates"]),
        examples=tuple(normalized["examples"]),
        forms=tuple(normalized["forms"]),
        sprint_artifacts=tuple(normalized["sprint_artifacts"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        verification_matrix=normalized["verification_matrix"],
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(manifest)


def render_noncore_asset_kit_manifest_markdown(manifest: NoncoreAssetKitManifest) -> str:
    """Render non-core asset kit manifest Markdown deterministically."""

    if not isinstance(manifest, NoncoreAssetKitManifest):
        raise ValueError("manifest_must_be_noncore_asset_kit_manifest")
    material = manifest.deterministic_material()
    return render_markdown(
        "Non-Core Production Asset Kit Manifest",
        metadata_rows=(
            ("manifest_id", manifest.manifest_id),
            ("repository_url", manifest.repository_url),
            ("main_commit", manifest.main_commit),
            ("policy_version", manifest.policy_version),
            ("code_version", manifest.code_version),
            ("content_hash", manifest.content_hash),
            ("observed_at", manifest.observed_at),
        ),
        sections=(
            ("Asset Groups", material["asset_groups"]),
            ("Documents", material["documents"]),
            ("Templates", material["templates"]),
            ("Examples", material["examples"]),
            ("Forms", material["forms"]),
            ("Sprint Artifacts", material["sprint_artifacts"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Verification Matrix", material["verification_matrix"]),
        ),
    )


def _validate_group_paths(material: Mapping[str, object]) -> None:
    for field in ("documents", "templates", "examples", "forms", "sprint_artifacts"):
        for index, value in enumerate(material[field]):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field}[{index}]_must_be_nonempty_string")
            if value.startswith("/") or ".." in value.split("/"):
                raise ValueError(f"{field}[{index}]_must_be_relative_repository_path")


def _reject_forbidden_top_level_fields(material: Mapping[str, object]) -> None:
    for key in material:
        if key in _FORBIDDEN_EXTRA_FIELDS:
            if key == "content_hash":
                raise ValueError("content_hash_is_computed")
            raise ValueError(f"forbidden_field:material.{key}")


def _with_hash(manifest: NoncoreAssetKitManifest) -> NoncoreAssetKitManifest:
    return NoncoreAssetKitManifest(
        manifest_id=manifest.manifest_id,
        repository_url=manifest.repository_url,
        main_commit=manifest.main_commit,
        asset_groups=manifest.asset_groups,
        documents=manifest.documents,
        templates=manifest.templates,
        examples=manifest.examples,
        forms=manifest.forms,
        sprint_artifacts=manifest.sprint_artifacts,
        blocked_capabilities=manifest.blocked_capabilities,
        verification_matrix=manifest.verification_matrix,
        policy_version=manifest.policy_version,
        code_version=manifest.code_version,
        content_hash=compute_content_hash(manifest.deterministic_material()),
        observed_at=manifest.observed_at,
    )
