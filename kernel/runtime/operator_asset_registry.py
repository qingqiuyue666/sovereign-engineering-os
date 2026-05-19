"""Deterministic read-only operator asset registry contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from kernel.runtime._nonhoudini_completion_common import contains_text, require_text_terms
from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)

__all__ = [
    "OperatorAssetRegistry",
    "build_operator_asset_registry",
    "render_operator_asset_registry_markdown",
]

_POLICY_VERSION = "operator-asset-registry-v1"
_CODE_VERSION = "0.1.0"
_REGISTRY_TYPES = (
    "code_report_registry",
    "ai_worker_output_registry",
    "decision_log_registry",
    "rollback_registry",
    "evidence_registry",
    "production_asset_registry",
)
_STRING_FIELDS = (
    "registry_id",
    "registry_type",
    "repository_url",
    "main_commit",
    "update_policy",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("entries", "blocked_capabilities", "rollback_notes")
_ENTRY_STRING_FIELDS = ("entry_id", "path", "title", "status")


@dataclass(frozen=True)
class OperatorAssetRegistry:
    """Repository-ready operator registry."""

    registry_id: str
    registry_type: str
    repository_url: str
    main_commit: str
    entries: tuple[object, ...]
    blocked_capabilities: tuple[object, ...]
    update_policy: str
    rollback_notes: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_capabilities": list(self.blocked_capabilities),
            "code_version": self.code_version,
            "entries": list(self.entries),
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "registry_id": self.registry_id,
            "registry_type": self.registry_type,
            "repository_url": self.repository_url,
            "rollback_notes": list(self.rollback_notes),
            "update_policy": self.update_policy,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_operator_asset_registry(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> OperatorAssetRegistry:
    """Build a deterministic read-only registry from caller-provided entries."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="operator_asset_registry_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_valid_choice(normalized["registry_type"], field="registry_type", allowed=_REGISTRY_TYPES)
    _validate_entries(normalized["entries"])
    require_text_terms(
        normalized["blocked_capabilities"],
        ("provider execution", "trading automation", "houdini/vfx"),
        error="blocked_capabilities_missing_required_language",
    )

    registry = OperatorAssetRegistry(
        registry_id=normalized["registry_id"],
        registry_type=normalized["registry_type"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        entries=tuple(normalized["entries"]),
        blocked_capabilities=tuple(normalized["blocked_capabilities"]),
        update_policy=normalized["update_policy"],
        rollback_notes=tuple(normalized["rollback_notes"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(registry, content_hash=compute_content_hash(registry.deterministic_material()))


def render_operator_asset_registry_markdown(registry: OperatorAssetRegistry) -> str:
    """Render deterministic Markdown for an operator registry."""

    if not isinstance(registry, OperatorAssetRegistry):
        raise ValueError("registry_must_be_operator_asset_registry")
    material = registry.deterministic_material()
    return render_markdown(
        "Operator Asset Registry",
        metadata_rows=(
            ("registry_id", registry.registry_id),
            ("registry_type", registry.registry_type),
            ("repository_url", registry.repository_url),
            ("main_commit", registry.main_commit),
            ("policy_version", registry.policy_version),
            ("code_version", registry.code_version),
            ("content_hash", registry.content_hash),
            ("observed_at", registry.observed_at),
        ),
        sections=(
            ("Entries", material["entries"]),
            ("Blocked Capabilities", material["blocked_capabilities"]),
            ("Update Policy", registry.update_policy),
            ("Rollback Notes", material["rollback_notes"]),
        ),
    )


def _validate_entries(entries: object) -> None:
    if not isinstance(entries, list):
        raise ValueError("entries_must_be_list")
    if not entries:
        raise ValueError("entries_must_not_be_empty")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entries_{index}_must_be_dict")
        for field in _ENTRY_STRING_FIELDS:
            if field not in entry or not isinstance(entry[field], str) or not entry[field]:
                raise ValueError(f"entries_{index}_{field}_must_be_nonempty_string")
        if _is_vfx_execution_asset(entry) and entry.get("external_line_reference_only") is not True:
            raise ValueError("houdini_vfx_execution_asset_requires_external_line_reference_only")


def _is_vfx_execution_asset(entry: Mapping[str, object]) -> bool:
    return (contains_text(entry, "houdini") or contains_text(entry, "vfx")) and contains_text(entry, "execution")
