"""Deterministic HFX Core12 repository reality audit."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

from kernel.runtime._nonhoudini_completion_common import all_required_gates_true
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
    "HFXCore12RealityAudit",
    "HFX_CORE12_ASSETS",
    "build_hfx_core12_reality_audit",
    "collect_hfx_core12_audit_material",
    "render_hfx_core12_reality_audit_markdown",
]

_POLICY_VERSION = "hfx-core12-reality-audit-v1"
_CODE_VERSION = "0.1.0"
_ALLOWED_STATUS = (
    "gold_candidate",
    "production_candidate",
    "partial_candidate",
    "shell_only",
    "blocked",
)
_STRING_FIELDS = (
    "audit_id",
    "repository_url",
    "main_commit",
    "source_root",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = ("core12_assets",)
_ASSET_STRING_FIELDS = ("asset_id", "asset_name", "status")
_ASSET_BOOL_FIELDS = (
    "source_files_present",
    "hip_files_present",
    "hda_files_present",
    "preview_docs_present",
    "preview_manifests_present",
    "mid_tier_present",
    "final_tier_present",
    "validation_reports_present",
    "sha256_manifest_present",
    "shot_binding_present",
    "render_or_comp_report_present",
)
_ASSET_COUNT_FIELDS = ("empty_file_count", "large_file_count_over_50mb")
_GOLD_CANDIDATE_GATES = (
    "reusable_source_present",
    "preview_proof_present",
    "validation_report_present",
    "no_empty_files",
    "shot_binding_present",
    "render_or_comp_report_present",
)
_HIP_SUFFIXES = (".hip", ".hiplc", ".hipnc")
_HDA_SUFFIXES = (".hda", ".otl")
_LARGE_FILE_LIMIT_BYTES = 50 * 1024 * 1024

HFX_CORE12_ASSETS: tuple[dict[str, str], ...] = (
    {
        "asset_id": "HFX_008",
        "asset_name": "Energy Shockwave",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_008_ENERGY_SHOCKWAVE",
        "factory_dir": "",
    },
    {
        "asset_id": "HFX_015",
        "asset_name": "Portal Ring",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_015_PORTAL_RING",
        "factory_dir": "500_HFX_FACTORY/HFX_015_BATCH_FINALIZE_V007_TO_V014",
    },
    {
        "asset_id": "HFX_016",
        "asset_name": "Heat Distortion",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_016_HEAT_DISTORTION",
        "factory_dir": "500_HFX_FACTORY/HFX_016_BATCH_FINALIZE_V015_TO_V022",
    },
    {
        "asset_id": "HFX_021",
        "asset_name": "Pyro Explosion",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_021_ADVANCED_PYRO_EXPLOSION",
        "factory_dir": "500_HFX_FACTORY/HFX_021_BATCH_FINALIZE_V023_TO_V030",
    },
    {
        "asset_id": "HFX_025",
        "asset_name": "Character Energy Field",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_025_CHARACTER_ENERGY_FIELD",
        "factory_dir": "500_HFX_FACTORY/HFX_025_BATCH_FINALIZE_V031_TO_V038",
    },
    {
        "asset_id": "HFX_027",
        "asset_name": "Summoning Portal Gate",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_027_SUMMONING_PORTAL_GATE",
        "factory_dir": "500_HFX_FACTORY/HFX_027_BATCH_FINALIZE_V079_TO_V086",
    },
    {
        "asset_id": "HFX_028",
        "asset_name": "Space Rift Tear",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_028_SPACE_RIFT_TEAR",
        "factory_dir": "500_HFX_FACTORY/HFX_028_BATCH_FINALIZE_V039_TO_V046",
    },
    {
        "asset_id": "HFX_029",
        "asset_name": "Black Hole Accretion Disk",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_029_BLACK_HOLE_ACCRETION_DISK",
        "factory_dir": "500_HFX_FACTORY/HFX_029_BATCH_FINALIZE_V087_TO_V094",
    },
    {
        "asset_id": "HFX_033",
        "asset_name": "Glow Emission Pass",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_033_GLOW_EMISSION_PASS",
        "factory_dir": "500_HFX_FACTORY/HFX_033_BATCH_FINALIZE_V047_TO_V054",
    },
    {
        "asset_id": "HFX_036",
        "asset_name": "Alpha Holdout Matte",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_036_ALPHA_HOLDOUT_MATTE",
        "factory_dir": "500_HFX_FACTORY/HFX_036_BATCH_FINALIZE_V055_TO_V062",
    },
    {
        "asset_id": "HFX_037",
        "asset_name": "Lightwrap Rim Interaction",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_037_LIGHTWRAP_RIM_INTERACTION",
        "factory_dir": "500_HFX_FACTORY/HFX_037_BATCH_FINALIZE_V063_TO_V070",
    },
    {
        "asset_id": "HFX_038",
        "asset_name": "Contact Shadow Ground Integration",
        "asset_dir": "300_PRODUCTION_UPGRADE/HFX_038_CONTACTSHADOW_GROUND_INTEGRATION",
        "factory_dir": "500_HFX_FACTORY/HFX_038_BATCH_FINALIZE_V071_TO_V078",
    },
)


@dataclass(frozen=True)
class HFXCore12RealityAudit:
    """Repository-ready deterministic Core12 audit result."""

    audit_id: str
    repository_url: str
    main_commit: str
    source_root: str
    core12_assets: tuple[dict[str, object], ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "audit_id": self.audit_id,
            "code_version": self.code_version,
            "core12_assets": [dict(asset) for asset in self.core12_assets],
            "main_commit": self.main_commit,
            "policy_version": self.policy_version,
            "repository_url": self.repository_url,
            "source_root": self.source_root,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def collect_hfx_core12_audit_material(
    source_root: Path | str,
    *,
    audit_id: str,
    repository_url: str,
    main_commit: str,
) -> dict[str, object]:
    """Inspect local Core12 files and return deterministic audit material."""

    root = Path(source_root)
    if not root.is_dir():
        raise ValueError("source_root_must_exist")
    assets = [_audit_asset(root, asset_spec) for asset_spec in HFX_CORE12_ASSETS]
    return {
        "audit_id": audit_id,
        "repository_url": repository_url,
        "main_commit": main_commit,
        "source_root": root.as_posix(),
        "core12_assets": assets,
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    }


def build_hfx_core12_reality_audit(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> HFXCore12RealityAudit:
    """Build a deterministic audit object, rejecting missing evidence or over-claims."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="hfx_core12_reality_audit_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    assets = _normalize_assets(normalized["core12_assets"])
    audit = HFXCore12RealityAudit(
        audit_id=normalized["audit_id"],
        repository_url=normalized["repository_url"],
        main_commit=normalized["main_commit"],
        source_root=normalized["source_root"],
        core12_assets=tuple(assets),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        observed_at=observed,
    )
    return replace(audit, content_hash=compute_content_hash(audit.deterministic_material()))


def render_hfx_core12_reality_audit_markdown(audit: HFXCore12RealityAudit) -> str:
    """Render deterministic Markdown for the HFX Core12 reality audit."""

    if not isinstance(audit, HFXCore12RealityAudit):
        raise ValueError("audit_must_be_hfx_core12_reality_audit")
    lines = [
        "# HFX Core12 Reality Audit",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| audit_id | {audit.audit_id} |",
        f"| repository_url | {audit.repository_url} |",
        f"| main_commit | {audit.main_commit} |",
        f"| source_root | {audit.source_root} |",
        f"| policy_version | {audit.policy_version} |",
        f"| code_version | {audit.code_version} |",
        f"| content_hash | {audit.content_hash} |",
        f"| observed_at | {audit.observed_at} |",
        "",
        "## Asset Reality Table",
        "| asset_id | asset_name | source_files_present | hip_files_present | hda_files_present | preview_docs_present | preview_manifests_present | mid_tier_present | final_tier_present | validation_reports_present | sha256_manifest_present | shot_binding_present | render_or_comp_report_present | empty_file_count | large_file_count_over_50mb | status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for asset in audit.core12_assets:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(asset["asset_id"]),
                    str(asset["asset_name"]),
                    _markdown_bool(asset["source_files_present"]),
                    _markdown_bool(asset["hip_files_present"]),
                    _markdown_bool(asset["hda_files_present"]),
                    _markdown_bool(asset["preview_docs_present"]),
                    _markdown_bool(asset["preview_manifests_present"]),
                    _markdown_bool(asset["mid_tier_present"]),
                    _markdown_bool(asset["final_tier_present"]),
                    _markdown_bool(asset["validation_reports_present"]),
                    _markdown_bool(asset["sha256_manifest_present"]),
                    _markdown_bool(asset["shot_binding_present"]),
                    _markdown_bool(asset["render_or_comp_report_present"]),
                    str(asset["empty_file_count"]),
                    str(asset["large_file_count_over_50mb"]),
                    str(asset["status"]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Status Rules")
    lines.extend(
        render_markdown(
            "Status Rules",
            metadata_rows=(),
            sections=(
                (
                    "Rules",
                    [
                        "gold_candidate requires reusable HIP/HDA evidence, preview proof, validation, non-empty files, shot binding, and render/comp report evidence.",
                        "production_candidate requires real HIP/HDA evidence plus validation.",
                        "partial_candidate requires local real asset files while final proof remains incomplete.",
                        "shell_only is reserved for reports/manifests without real asset files.",
                        "blocked is used for missing critical files, empty critical files, or unsafe evidence conditions.",
                    ],
                ),
            ),
        ).splitlines()[4:]
    )
    return "\n".join(lines).rstrip() + "\n"


def _normalize_assets(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("core12_assets_must_be_nonempty_list")
    required_order = [asset["asset_id"] for asset in HFX_CORE12_ASSETS]
    required_names = {asset["asset_id"]: asset["asset_name"] for asset in HFX_CORE12_ASSETS}
    by_id: dict[str, dict[str, object]] = {}
    for row in value:
        asset = _normalize_asset(row)
        asset_id = str(asset["asset_id"])
        if asset_id in by_id:
            raise ValueError(f"duplicate_asset:{asset_id}")
        by_id[asset_id] = asset
    if list(sorted(by_id)) != list(sorted(required_order)):
        raise ValueError("core12_assets_must_list_all_12_assets")
    normalized: list[dict[str, object]] = []
    for asset_id in required_order:
        asset = by_id[asset_id]
        if asset["asset_name"] != required_names[asset_id]:
            raise ValueError(f"asset_name_mismatch:{asset_id}")
        _validate_status_evidence(asset)
        normalized.append(asset)
    return normalized


def _normalize_asset(row: object) -> dict[str, object]:
    if not isinstance(row, dict):
        raise ValueError("core12_asset_must_be_dict")
    for field in _ASSET_STRING_FIELDS:
        if field not in row or not isinstance(row[field], str) or not row[field]:
            raise ValueError(f"{field}_missing")
    require_valid_choice(row["status"], field="asset_status", allowed=_ALLOWED_STATUS)
    normalized: dict[str, object] = {
        "asset_id": row["asset_id"],
        "asset_name": row["asset_name"],
        "status": row["status"],
    }
    for field in _ASSET_BOOL_FIELDS:
        if field not in row or not isinstance(row[field], bool):
            raise ValueError(f"{field}_must_be_bool")
        normalized[field] = row[field]
    for field in _ASSET_COUNT_FIELDS:
        if field not in row or not isinstance(row[field], int) or isinstance(row[field], bool) or row[field] < 0:
            raise ValueError(f"{field}_must_be_nonnegative_int")
        normalized[field] = row[field]
    return {
        "asset_id": normalized["asset_id"],
        "asset_name": normalized["asset_name"],
        "source_files_present": normalized["source_files_present"],
        "hip_files_present": normalized["hip_files_present"],
        "hda_files_present": normalized["hda_files_present"],
        "preview_docs_present": normalized["preview_docs_present"],
        "preview_manifests_present": normalized["preview_manifests_present"],
        "mid_tier_present": normalized["mid_tier_present"],
        "final_tier_present": normalized["final_tier_present"],
        "validation_reports_present": normalized["validation_reports_present"],
        "sha256_manifest_present": normalized["sha256_manifest_present"],
        "shot_binding_present": normalized["shot_binding_present"],
        "render_or_comp_report_present": normalized["render_or_comp_report_present"],
        "empty_file_count": normalized["empty_file_count"],
        "large_file_count_over_50mb": normalized["large_file_count_over_50mb"],
        "status": normalized["status"],
    }


def _validate_status_evidence(asset: Mapping[str, object]) -> None:
    if asset["empty_file_count"] and asset["status"] != "blocked":
        raise ValueError("empty_file_count_blocks_nonblocked_status")
    if asset["status"] == "gold_candidate":
        gates = {
            "reusable_source_present": bool(
                asset["hda_files_present"] or (asset["hip_files_present"] and asset["final_tier_present"])
            ),
            "preview_proof_present": bool(asset["preview_docs_present"] and asset["preview_manifests_present"]),
            "validation_report_present": bool(asset["validation_reports_present"]),
            "no_empty_files": asset["empty_file_count"] == 0,
            "shot_binding_present": bool(asset["shot_binding_present"]),
            "render_or_comp_report_present": bool(asset["render_or_comp_report_present"]),
        }
        if not all_required_gates_true(gates, _GOLD_CANDIDATE_GATES):
            raise ValueError("gold_candidate_missing_required_evidence")
    if asset["status"] == "production_candidate":
        if not (asset["hip_files_present"] or asset["hda_files_present"]):
            raise ValueError("production_candidate_missing_real_hip_or_hda")
        if not asset["validation_reports_present"]:
            raise ValueError("production_candidate_missing_validation")
    if asset["status"] == "partial_candidate" and not (
        asset["source_files_present"] or asset["hip_files_present"] or asset["hda_files_present"]
    ):
        raise ValueError("partial_candidate_missing_real_asset_files")
    if asset["status"] == "shell_only" and (asset["hip_files_present"] or asset["hda_files_present"]):
        raise ValueError("shell_only_cannot_have_real_hip_or_hda")


def _audit_asset(root: Path, asset_spec: Mapping[str, str]) -> dict[str, object]:
    asset_root = root / asset_spec["asset_dir"]
    related_files = _collect_related_files(root, asset_root, asset_spec)
    if not related_files:
        return _asset_row(asset_spec, False, False, False, False, False, False, False, False, False, False, False, 0, 0)
    names = [path.name.lower() for path in related_files]
    path_texts = [path.relative_to(root).as_posix().lower() for path in related_files]
    hip_present = any(path.suffix.lower() in _HIP_SUFFIXES for path in related_files)
    hda_present = any(path.suffix.lower() in _HDA_SUFFIXES for path in related_files)
    source_present = any(_is_source_path(text, name) for text, name in zip(path_texts, names)) or hda_present
    preview_docs_present = any("preview" in text and path.suffix.lower() == ".md" for text, path in zip(path_texts, related_files))
    preview_manifests_present = any(
        "preview" in text and (("manifest" in text) or path.suffix.lower() == ".json" or path.suffix.lower() == ".txt")
        for text, path in zip(path_texts, related_files)
    )
    mid_present = any("02_mid" in text or "_mid_" in text or "mid_tier" in text for text in path_texts)
    final_present = any("03_final" in text or "final_tier" in text or "final_candidate" in text for text in path_texts)
    validation_present = any("validation" in text and path.suffix.lower() in {".md", ".json"} for text, path in zip(path_texts, related_files))
    sha_present = any("sha256" in text or "checksums" in text for text in path_texts)
    shot_present = any("shot_bound" in text or "shot_binding" in text or "shot_template" in text for text in path_texts)
    render_or_comp_present = any("render_comp" in text or "comp_handoff" in text or "render" in text for text in path_texts)
    empty_count = sum(1 for path in related_files if path.stat().st_size == 0)
    large_count = sum(1 for path in related_files if path.stat().st_size > _LARGE_FILE_LIMIT_BYTES)
    return _asset_row(
        asset_spec,
        source_present,
        hip_present,
        hda_present,
        preview_docs_present,
        preview_manifests_present,
        mid_present,
        final_present,
        validation_present,
        sha_present,
        shot_present,
        render_or_comp_present,
        empty_count,
        large_count,
    )


def _collect_related_files(root: Path, asset_root: Path, asset_spec: Mapping[str, str]) -> list[Path]:
    related: set[Path] = set()
    if asset_root.is_dir():
        related.update(path for path in asset_root.rglob("*") if path.is_file())
    factory_dir = asset_spec.get("factory_dir", "")
    if factory_dir:
        factory_root = root / factory_dir
        if factory_root.is_dir():
            related.update(path for path in factory_root.rglob("*") if path.is_file())
    asset_id = asset_spec["asset_id"].lower()
    compact_id = asset_id.replace("_", "")
    index_root = root / "00_INDEX_资产索引"
    if index_root.is_dir():
        for path in index_root.iterdir():
            if path.is_file():
                text = path.name.lower()
                if asset_id in text or compact_id in text:
                    related.add(path)
    return sorted(related, key=lambda path: path.relative_to(root).as_posix())


def _asset_row(
    asset_spec: Mapping[str, str],
    source_files_present: bool,
    hip_files_present: bool,
    hda_files_present: bool,
    preview_docs_present: bool,
    preview_manifests_present: bool,
    mid_tier_present: bool,
    final_tier_present: bool,
    validation_reports_present: bool,
    sha256_manifest_present: bool,
    shot_binding_present: bool,
    render_or_comp_report_present: bool,
    empty_file_count: int,
    large_file_count_over_50mb: int,
) -> dict[str, object]:
    status = _classify_status(
        source_files_present=source_files_present,
        hip_files_present=hip_files_present,
        hda_files_present=hda_files_present,
        preview_docs_present=preview_docs_present,
        preview_manifests_present=preview_manifests_present,
        final_tier_present=final_tier_present,
        validation_reports_present=validation_reports_present,
        shot_binding_present=shot_binding_present,
        render_or_comp_report_present=render_or_comp_report_present,
        empty_file_count=empty_file_count,
    )
    return {
        "asset_id": asset_spec["asset_id"],
        "asset_name": asset_spec["asset_name"],
        "source_files_present": source_files_present,
        "hip_files_present": hip_files_present,
        "hda_files_present": hda_files_present,
        "preview_docs_present": preview_docs_present,
        "preview_manifests_present": preview_manifests_present,
        "mid_tier_present": mid_tier_present,
        "final_tier_present": final_tier_present,
        "validation_reports_present": validation_reports_present,
        "sha256_manifest_present": sha256_manifest_present,
        "shot_binding_present": shot_binding_present,
        "render_or_comp_report_present": render_or_comp_report_present,
        "empty_file_count": empty_file_count,
        "large_file_count_over_50mb": large_file_count_over_50mb,
        "status": status,
    }


def _classify_status(
    *,
    source_files_present: bool,
    hip_files_present: bool,
    hda_files_present: bool,
    preview_docs_present: bool,
    preview_manifests_present: bool,
    final_tier_present: bool,
    validation_reports_present: bool,
    shot_binding_present: bool,
    render_or_comp_report_present: bool,
    empty_file_count: int,
) -> str:
    if empty_file_count:
        return "blocked"
    has_real_asset = source_files_present or hip_files_present or hda_files_present
    if not has_real_asset:
        return "shell_only"
    gold_gates = {
        "reusable_source_present": hda_files_present or (hip_files_present and final_tier_present),
        "preview_proof_present": preview_docs_present and preview_manifests_present,
        "validation_report_present": validation_reports_present,
        "no_empty_files": empty_file_count == 0,
        "shot_binding_present": shot_binding_present,
        "render_or_comp_report_present": render_or_comp_report_present,
    }
    if all_required_gates_true(gold_gates, _GOLD_CANDIDATE_GATES):
        return "gold_candidate"
    if (hip_files_present or hda_files_present) and validation_reports_present:
        return "production_candidate"
    return "partial_candidate"


def _is_source_path(path_text: str, name: str) -> bool:
    return (
        "/source/" in path_text
        or "/00_source/" in path_text
        or "source_contract" in name
        or "source_resolution" in name
    )


def _markdown_bool(value: object) -> str:
    return "yes" if value is True else "no"
