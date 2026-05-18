"""Deterministic Houdini asset specification for the private creative sample."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    contains_required_terms,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_required_members,
    require_string_fields,
)

__all__ = [
    "HOUDINI_REQUIRED_ASSET_CLASSES",
    "HoudiniAssetSpec",
    "build_houdini_asset_spec",
    "render_houdini_asset_spec_markdown",
]

_POLICY_VERSION = "houdini-asset-spec-v1"
_CODE_VERSION = "0.1.0"

HOUDINI_REQUIRED_ASSET_CLASSES = (
    "particle_field",
    "vdb_smoke_or_energy",
    "velocity_pass",
    "depth_pass",
    "normal_pass",
    "emission_pass",
    "camera_metadata",
)

_STRING_FIELDS = ("spec_id", "project_name", "policy_version", "code_version")
_LIST_FIELDS = (
    "asset_classes",
    "particle_requirements",
    "vdb_requirements",
    "field_requirements",
    "pass_exports",
    "blocked_execution",
    "quality_gates",
    "rollback_plan",
)
_DICT_FIELDS = ("camera_metadata", "naming_contract", "directory_contract")


@dataclass(frozen=True)
class HoudiniAssetSpec:
    """Repository-ready Houdini asset specification."""

    spec_id: str
    project_name: str
    asset_classes: tuple[object, ...]
    particle_requirements: tuple[object, ...]
    vdb_requirements: tuple[object, ...]
    field_requirements: tuple[object, ...]
    pass_exports: tuple[object, ...]
    camera_metadata: dict[str, object]
    naming_contract: dict[str, object]
    directory_contract: dict[str, object]
    blocked_execution: tuple[object, ...]
    quality_gates: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "asset_classes": list(self.asset_classes),
            "blocked_execution": list(self.blocked_execution),
            "camera_metadata": self.camera_metadata,
            "code_version": self.code_version,
            "directory_contract": self.directory_contract,
            "field_requirements": list(self.field_requirements),
            "naming_contract": self.naming_contract,
            "particle_requirements": list(self.particle_requirements),
            "pass_exports": list(self.pass_exports),
            "policy_version": self.policy_version,
            "project_name": self.project_name,
            "quality_gates": list(self.quality_gates),
            "rollback_plan": list(self.rollback_plan),
            "spec_id": self.spec_id,
            "vdb_requirements": list(self.vdb_requirements),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_houdini_asset_spec(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HoudiniAssetSpec:
    """Build a deterministic Houdini asset spec without launching creative tools."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="houdini_asset_spec_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_required_members(normalized["asset_classes"], HOUDINI_REQUIRED_ASSET_CLASSES, field="asset_classes")
    if not contains_required_terms(normalized["blocked_execution"], ("houdini", "hython", "execution")):
        raise ValueError("blocked_execution_must_block_houdini_hython_execution")

    spec = HoudiniAssetSpec(
        spec_id=normalized["spec_id"],
        project_name=normalized["project_name"],
        asset_classes=tuple(normalized["asset_classes"]),
        particle_requirements=tuple(normalized["particle_requirements"]),
        vdb_requirements=tuple(normalized["vdb_requirements"]),
        field_requirements=tuple(normalized["field_requirements"]),
        pass_exports=tuple(normalized["pass_exports"]),
        camera_metadata=normalized["camera_metadata"],
        naming_contract=normalized["naming_contract"],
        directory_contract=normalized["directory_contract"],
        blocked_execution=tuple(normalized["blocked_execution"]),
        quality_gates=tuple(normalized["quality_gates"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(spec)


def render_houdini_asset_spec_markdown(spec: HoudiniAssetSpec) -> str:
    """Render Houdini asset spec Markdown deterministically."""

    if not isinstance(spec, HoudiniAssetSpec):
        raise ValueError("spec_must_be_houdini_asset_spec")
    material = spec.deterministic_material()
    return render_markdown(
        "Houdini Asset Specification v1",
        metadata_rows=(
            ("spec_id", spec.spec_id),
            ("project_name", spec.project_name),
            ("policy_version", spec.policy_version),
            ("code_version", spec.code_version),
            ("content_hash", spec.content_hash),
            ("observed_at", spec.observed_at),
        ),
        sections=(
            ("Asset Classes", material["asset_classes"]),
            ("Particle Requirements", material["particle_requirements"]),
            ("VDB Requirements", material["vdb_requirements"]),
            ("Field Requirements", material["field_requirements"]),
            ("Pass Exports", material["pass_exports"]),
            ("Camera Metadata", material["camera_metadata"]),
            ("Naming Contract", material["naming_contract"]),
            ("Directory Contract", material["directory_contract"]),
            ("Blocked Execution", material["blocked_execution"]),
            ("Quality Gates", material["quality_gates"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(spec: HoudiniAssetSpec) -> HoudiniAssetSpec:
    return HoudiniAssetSpec(
        spec_id=spec.spec_id,
        project_name=spec.project_name,
        asset_classes=spec.asset_classes,
        particle_requirements=spec.particle_requirements,
        vdb_requirements=spec.vdb_requirements,
        field_requirements=spec.field_requirements,
        pass_exports=spec.pass_exports,
        camera_metadata=spec.camera_metadata,
        naming_contract=spec.naming_contract,
        directory_contract=spec.directory_contract,
        blocked_execution=spec.blocked_execution,
        quality_gates=spec.quality_gates,
        rollback_plan=spec.rollback_plan,
        policy_version=spec.policy_version,
        code_version=spec.code_version,
        content_hash=compute_content_hash(spec.deterministic_material()),
        observed_at=spec.observed_at,
    )
