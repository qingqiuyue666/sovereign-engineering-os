#!/usr/bin/env python3
"""Deterministic local-first shot binding for the HFX Factory Core 12 assets."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


class HFXShotBindingError(RuntimeError):
    """Raised when a shot-binding operation must fail closed."""


LAYER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAYER_ROOT.parents[2]
CORE12_ROOT = REPO_ROOT / "assets" / "houdini" / "hfx_factory_core12"
REGISTRY_PATH = CORE12_ROOT / "00_INDEX_资产索引" / "HFX_LONG_TERM_ASSET_REGISTRY.json"
GLOBAL_SEAL_PATH = (
    CORE12_ROOT
    / "500_HFX_FACTORY"
    / "HFX_FACTORY_FINAL_GLOBAL_SEAL"
    / "02_validation"
    / "HFX_FACTORY_FINAL_GLOBAL_SEAL_VALIDATION.json"
)
PRODUCTION_UPGRADE_ROOT = CORE12_ROOT / "300_PRODUCTION_UPGRADE"
FACTORY_ROOT = CORE12_ROOT / "500_HFX_FACTORY"
PROFILE_PATH = LAYER_ROOT / "templates" / "HFX_SHOT_ASSET_CONTRACT_PROFILES.json"

REQUEST_REQUIRED_FIELDS = [
    "project_id",
    "sequence_id",
    "shot_id",
    "take_id",
    "frame_start",
    "frame_end",
    "fps",
    "plate_path",
    "camera_path",
    "hdri_path",
    "lens_profile_path",
    "output_root",
    "requested_assets",
    "render_target",
    "comp_target",
    "notes",
]
REQUEST_ASSET_REQUIRED_FIELDS = [
    "asset_id",
    "enabled",
    "parameter_overrides",
    "dependency_policy",
]
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
FORBIDDEN_PACKAGE_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".flv",
    ".rar",
    ".zip",
    ".7z",
}
GLOBAL_LAYER_OUTPUTS = {
    "manifests/HFX_SHOT_BINDING_LAYER_MANIFEST.json",
    "manifests/HFX_SHOT_BINDING_LAYER_SHA256SUMS.txt",
    "manifests/HFX_SHOT_BINDING_LAYER_FILE_TREE.txt",
    "validation/HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.json",
    "validation/HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.md",
}
REQUIRED_ASSETS = {
    "HFX_008": "Energy Shockwave",
    "HFX_015": "Portal Ring",
    "HFX_016": "Heat Distortion",
    "HFX_021": "Advanced Pyro Explosion",
    "HFX_025": "Character Energy Field",
    "HFX_028": "Space Rift Tear",
    "HFX_033": "Glow Emission Pass",
    "HFX_036": "Alpha Holdout Matte",
    "HFX_037": "LightWrap Rim Interaction",
    "HFX_038": "ContactShadow Ground Integration",
    "HFX_027": "Summoning Portal Gate",
    "HFX_029": "Black Hole Accretion Disk",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HFXShotBindingError(f"Required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HFXShotBindingError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def relpath(path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def ensure_identifier(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise HFXShotBindingError(
            f"{field_name} must be a non-empty deterministic identifier using letters, "
            "numbers, dot, underscore, or hyphen"
        )


def resolve_core12_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve(strict=False)
    return (CORE12_ROOT / path).resolve(strict=False)


def assert_path_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise HFXShotBindingError(f"{description} does not exist: {path}")


def assert_output_path_allowed(path: Path) -> None:
    resolved = path.resolve(strict=False)
    forbidden_roots = [PRODUCTION_UPGRADE_ROOT, FACTORY_ROOT]
    for forbidden in forbidden_roots:
        if is_relative_to(resolved, forbidden):
            raise HFXShotBindingError(
                f"Output path is inside a forbidden Core 12 authority tree: {resolved}"
            )


def validate_factory_core12() -> dict[str, Any]:
    registry = load_json(REGISTRY_PATH)
    seal = load_json(GLOBAL_SEAL_PATH)

    checks: list[dict[str, Any]] = []

    def require(condition: bool, check_id: str, detail: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(condition), "detail": detail})
        if not condition:
            raise HFXShotBindingError(f"Factory Core 12 validation failed: {check_id}: {detail}")

    require(
        seal.get("status") == "HFX_FACTORY_FINAL_GLOBAL_SEAL_PASS",
        "global_seal_status",
        "global seal status is HFX_FACTORY_FINAL_GLOBAL_SEAL_PASS",
    )
    require(seal.get("validated") is True, "global_seal_validated", "validated is true")
    require(seal.get("asset_count_required") == 12, "asset_count_required", "required count is 12")
    require(seal.get("asset_count_passed") == 12, "asset_count_passed", "passed count is 12")
    require(seal.get("pollution") == [], "pollution_empty", "pollution list is empty")
    require(isinstance(registry.get("assets"), list), "registry_assets_array", "assets is a list")

    registry_assets = registry["assets"]
    require(len(registry_assets) >= 12, "registry_asset_count", "registry has at least 12 assets")
    by_id: dict[str, dict[str, Any]] = {}
    for entry in registry_assets:
        asset_id = entry.get("asset_id")
        if asset_id:
            by_id[asset_id] = entry

    discovered: dict[str, dict[str, Any]] = {}
    for asset_id, expected_name in REQUIRED_ASSETS.items():
        require(asset_id in by_id, f"{asset_id}_registry_entry", f"{asset_id} exists in registry")
        entry = by_id[asset_id]
        require(
            entry.get("asset_name") == expected_name,
            f"{asset_id}_asset_name",
            f"{asset_id} asset name is {expected_name}",
        )
        release_paths = entry.get("release_paths")
        require(
            isinstance(release_paths, dict),
            f"{asset_id}_release_paths",
            f"{asset_id} has release_paths",
        )
        release_root_value = release_paths.get("release_root")
        release_hip_value = release_paths.get("release_hip")
        final_asset_seal_value = release_paths.get("final_asset_seal")
        require(bool(release_root_value), f"{asset_id}_release_root_declared", "release_root exists")
        require(bool(release_hip_value), f"{asset_id}_release_hip_declared", "release_hip exists")
        require(
            bool(final_asset_seal_value),
            f"{asset_id}_final_asset_seal_declared",
            "final_asset_seal exists",
        )

        release_root = resolve_core12_path(str(release_root_value))
        release_hip = resolve_core12_path(str(release_hip_value))
        final_asset_seal = resolve_core12_path(str(final_asset_seal_value))
        require(release_root.exists(), f"{asset_id}_release_root_on_disk", str(release_root))
        require(release_hip.exists(), f"{asset_id}_release_hip_on_disk", str(release_hip))
        require(final_asset_seal.exists(), f"{asset_id}_final_seal_on_disk", str(final_asset_seal))
        require(
            is_relative_to(release_hip, release_root),
            f"{asset_id}_release_hip_inside_release_root",
            "release HIP is inside release_root",
        )
        require(
            is_relative_to(final_asset_seal, release_root),
            f"{asset_id}_final_seal_inside_release_root",
            "final seal is inside release_root",
        )

        discovered[asset_id] = {
            "asset_id": asset_id,
            "asset_name": expected_name,
            "release_root": release_root,
            "release_hip": release_hip,
            "final_asset_seal": final_asset_seal,
            "registry_entry": copy.deepcopy(entry),
        }

    return {
        "status": "PASS",
        "registry_path": REGISTRY_PATH,
        "global_seal_path": GLOBAL_SEAL_PATH,
        "registry": registry,
        "global_seal": seal,
        "assets": discovered,
        "checks": checks,
    }


def load_asset_profiles() -> dict[str, dict[str, Any]]:
    profiles_document = load_json(PROFILE_PATH)
    profiles = profiles_document.get("asset_profiles")
    if not isinstance(profiles, dict):
        raise HFXShotBindingError(f"asset_profiles is missing from {PROFILE_PATH}")
    missing = sorted(set(REQUIRED_ASSETS) - set(profiles))
    if missing:
        raise HFXShotBindingError(f"Asset contract profiles are missing: {', '.join(missing)}")
    return profiles


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise HFXShotBindingError("ShotBindingRequest must be a JSON object")
    expected = set(REQUEST_REQUIRED_FIELDS)
    actual = set(request)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise HFXShotBindingError(f"ShotBindingRequest is missing fields: {', '.join(missing)}")
    if extra:
        raise HFXShotBindingError(f"ShotBindingRequest has unsupported fields: {', '.join(extra)}")

    for field in ["project_id", "sequence_id", "shot_id", "take_id"]:
        ensure_identifier(request[field], field)

    if type(request["frame_start"]) is not int or type(request["frame_end"]) is not int:
        raise HFXShotBindingError("frame_start and frame_end must be integers")
    if request["frame_end"] < request["frame_start"]:
        raise HFXShotBindingError("frame_end must be greater than or equal to frame_start")
    if not isinstance(request["fps"], (int, float)) or isinstance(request["fps"], bool) or request["fps"] <= 0:
        raise HFXShotBindingError("fps must be a positive number")

    for field in [
        "plate_path",
        "camera_path",
        "hdri_path",
        "lens_profile_path",
        "output_root",
        "render_target",
        "comp_target",
        "notes",
    ]:
        if not isinstance(request[field], str):
            raise HFXShotBindingError(f"{field} must be a string")

    requested_assets = request["requested_assets"]
    if not isinstance(requested_assets, list) or not requested_assets:
        raise HFXShotBindingError("requested_assets must be a non-empty list")

    asset_ids: list[str] = []
    for index, item in enumerate(requested_assets):
        if not isinstance(item, dict):
            raise HFXShotBindingError(f"requested_assets[{index}] must be an object")
        expected_asset_fields = set(REQUEST_ASSET_REQUIRED_FIELDS)
        item_fields = set(item)
        missing = sorted(expected_asset_fields - item_fields)
        extra = sorted(item_fields - expected_asset_fields)
        if missing:
            raise HFXShotBindingError(
                f"requested_assets[{index}] is missing fields: {', '.join(missing)}"
            )
        if extra:
            raise HFXShotBindingError(
                f"requested_assets[{index}] has unsupported fields: {', '.join(extra)}"
            )
        if not isinstance(item["asset_id"], str) or not item["asset_id"]:
            raise HFXShotBindingError(f"requested_assets[{index}].asset_id must be a string")
        if type(item["enabled"]) is not bool:
            raise HFXShotBindingError(f"requested_assets[{index}].enabled must be a boolean")
        if not isinstance(item["parameter_overrides"], dict):
            raise HFXShotBindingError(
                f"requested_assets[{index}].parameter_overrides must be an object"
            )
        if not isinstance(item["dependency_policy"], str) or not item["dependency_policy"]:
            raise HFXShotBindingError(
                f"requested_assets[{index}].dependency_policy must be a non-empty string"
            )
        asset_ids.append(item["asset_id"])

    duplicates = sorted({asset_id for asset_id in asset_ids if asset_ids.count(asset_id) > 1})
    if duplicates:
        raise HFXShotBindingError(f"duplicate asset IDs exist in one shot request: {', '.join(duplicates)}")

    enabled_assets = [item for item in requested_assets if item["enabled"]]
    if not enabled_assets:
        raise HFXShotBindingError("requested_assets must contain at least one enabled asset")

    output_root = Path(request["output_root"]).expanduser().resolve(strict=False)
    assert_output_path_allowed(output_root)

    validated = copy.deepcopy(request)
    validated["output_root"] = output_root.as_posix()
    return validated


def package_root_for_request(request: dict[str, Any]) -> Path:
    return (
        Path(request["output_root"]).expanduser().resolve(strict=False)
        / request["project_id"]
        / request["sequence_id"]
        / request["shot_id"]
        / request["take_id"]
    )


def package_directories(package_root: Path) -> dict[str, Path]:
    return {
        "request": package_root / "00_request",
        "source_assets": package_root / "01_source_assets",
        "shot_hip": package_root / "02_shot_hip",
        "parameters": package_root / "03_parameters",
        "render_contract": package_root / "04_render_contract",
        "comp_contract": package_root / "05_comp_contract",
        "validation": package_root / "06_validation",
        "manifests": package_root / "07_manifests",
        "docs": package_root / "08_docs",
    }


def assert_package_path_allowed(package_root: Path) -> None:
    assert_output_path_allowed(package_root)
    if package_root.resolve(strict=False) == Path("/").resolve(strict=False):
        raise HFXShotBindingError("Refusing to bind into filesystem root")
    if len(package_root.resolve(strict=False).parts) < 5:
        raise HFXShotBindingError(f"Refusing unsafe short package path: {package_root}")


def guard_write_path(path: Path, release_roots: list[Path]) -> None:
    resolved = path.resolve(strict=False)
    assert_output_path_allowed(resolved)
    for release_root in release_roots:
        if is_relative_to(resolved, release_root):
            raise HFXShotBindingError(
                f"Shot binding attempted to write inside a release package directory: {resolved}"
            )


def merge_parameters(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        merged[key] = value
    return merged


def per_asset_filename(asset_id: str, shot_id: str, take_id: str, suffix: str) -> str:
    return f"{asset_id}_{shot_id}_{take_id}_{suffix}"


def build_render_contract(
    request: dict[str, Any],
    asset_bindings: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    per_asset = []
    required_outputs: list[str] = []
    for binding in asset_bindings:
        asset_id = binding["asset_id"]
        passes = list(profiles[asset_id]["expected_passes"])
        per_asset.append(
            {
                "asset_id": asset_id,
                "asset_name": binding["asset_name"],
                "expected_passes": passes,
            }
        )
        for pass_name in passes:
            output_id = f"{asset_id}:{pass_name}"
            if output_id not in required_outputs:
                required_outputs.append(output_id)

    return {
        "schema_type": "RenderCompChecklist",
        "contract_type": "render",
        "status": "HFX_RENDER_CONTRACT_READY_NO_PIXELS_RENDERED",
        "shot_id": request["shot_id"],
        "take_id": request["take_id"],
        "frame_start": request["frame_start"],
        "frame_end": request["frame_end"],
        "fps": request["fps"],
        "render_target": request["render_target"],
        "required_outputs": sorted(required_outputs),
        "per_asset_expected_pass_list": per_asset,
        "explicit_blocked_claims": [
            "no OpenEXR rendered yet",
            "no final comp rendered yet",
            "no client delivery yet",
        ],
    }


def build_comp_contract(
    request: dict[str, Any],
    asset_bindings: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required_inputs = [
        "plate",
        "camera",
        "hdri",
        "lens profile",
        "rendered FX passes",
    ]
    asset_ids = {binding["asset_id"] for binding in asset_bindings}
    if "HFX_036" in asset_ids:
        required_inputs.append("alpha/holdout where required")
    if "HFX_037" in asset_ids:
        required_inputs.append("lightwrap/contact shadow where required")
    if "HFX_038" in asset_ids and "lightwrap/contact shadow where required" not in required_inputs:
        required_inputs.append("lightwrap/contact shadow where required")

    per_asset_notes = []
    for binding in asset_bindings:
        asset_id = binding["asset_id"]
        per_asset_notes.append(
            {
                "asset_id": asset_id,
                "asset_name": binding["asset_name"],
                "comp_notes": list(profiles[asset_id]["comp_notes"]),
            }
        )

    return {
        "schema_type": "RenderCompChecklist",
        "contract_type": "comp",
        "status": "HFX_COMP_CONTRACT_READY_NO_FINAL_COMP_RENDERED",
        "shot_id": request["shot_id"],
        "take_id": request["take_id"],
        "comp_target": request["comp_target"],
        "expected_comp_app_options": [
            "Nuke",
            "After Effects",
            "DaVinci Resolve",
        ],
        "required_inputs": required_inputs,
        "input_paths": {
            "plate": request["plate_path"],
            "camera": request["camera_path"],
            "hdri": request["hdri_path"],
            "lens_profile": request["lens_profile_path"],
        },
        "per_asset_comp_notes": per_asset_notes,
        "explicit_final_pixel_blocking_conditions": [
            "No OpenEXR render sequence is generated by this binding layer.",
            "No final composited image or movie is generated by this binding layer.",
            "No client delivery, review movie, or final-pixel claim is authorized by this package.",
        ],
    }


def build_operator_guide(
    request: dict[str, Any],
    asset_bindings: list[dict[str, Any]],
    render_contract_path: Path,
    comp_contract_path: Path,
) -> str:
    asset_lines = "\n".join(
        f"- `{binding['asset_id']}` {binding['asset_name']}: use copied HIP `{Path(binding['shot_hip']).name}`"
        for binding in asset_bindings
    )
    return f"""# HFX Shot Operator Guide: {request['shot_id']} {request['take_id']}

This package binds sealed HFX Factory Core 12 release assets into a per-shot working area.
It does not create Hollywood final-pixel shots, OpenEXR render sequences, final comps, review movies, or client delivery.

## Bound Assets
{asset_lines}

## How To Work
- Open only the copied HIP files in `02_shot_hip/`.
- Apply shot-specific parameter changes from `03_parameters/`.
- Treat source release HIP files and final asset seals as read-only authority.
- Use `{relpath(render_contract_path)}` as the render automation contract.
- Use `{relpath(comp_contract_path)}` as the comp handoff contract.

## Do Not Edit
- Do not edit any file under `assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/**/10_release/release_package/`.
- Do not move, overwrite, or re-save Core 12 release HIP files.
- Do not claim OpenEXR render completion until actual EXR files are rendered and validated.
- Do not claim final comp completion until actual comp outputs are generated and validated.

## Next Layer
The next production layer is Houdini batch render automation followed by comp automation and render/comp validation.
"""


def build_mutation_guard_report(
    request: dict[str, Any],
    package_root: Path,
    source_hash_records: list[dict[str, Any]],
    release_roots: list[Path],
) -> dict[str, Any]:
    return {
        "schema_type": "MutationGuardReport",
        "status": "PASS",
        "project_id": request["project_id"],
        "sequence_id": request["sequence_id"],
        "shot_id": request["shot_id"],
        "take_id": request["take_id"],
        "package_root": package_root.as_posix(),
        "forbidden_output_roots": [
            PRODUCTION_UPGRADE_ROOT.as_posix(),
            FACTORY_ROOT.as_posix(),
        ],
        "release_roots_guarded": [path.as_posix() for path in sorted(release_roots)],
        "source_release_hip_hash_checks": source_hash_records,
        "checks": [
            {
                "check_id": "output_not_in_production_upgrade",
                "passed": not is_relative_to(package_root, PRODUCTION_UPGRADE_ROOT),
            },
            {
                "check_id": "output_not_in_factory_root",
                "passed": not is_relative_to(package_root, FACTORY_ROOT),
            },
            {
                "check_id": "source_release_hips_unchanged_during_binding",
                "passed": all(
                    item["sha256_before"] == item["sha256_after"] for item in source_hash_records
                ),
            },
            {
                "check_id": "shot_package_writes_outside_release_package_directories",
                "passed": True,
            },
        ],
        "blocked_claims": [
            "Hollywood final-pixel shot complete",
            "actual OpenEXR pixels rendered",
            "actual final comp rendered",
            "client/public delivery ready",
        ],
    }


def bind_shot(request_path: Path) -> dict[str, Any]:
    request_path = request_path.resolve(strict=False)
    request = validate_request(load_json(request_path))
    factory = validate_factory_core12()
    profiles = load_asset_profiles()

    package_root = package_root_for_request(request)
    assert_package_path_allowed(package_root)

    requested_asset_ids = [item["asset_id"] for item in request["requested_assets"]]
    unknown_assets = sorted(set(requested_asset_ids) - set(factory["assets"]))
    if unknown_assets:
        raise HFXShotBindingError(f"requested asset is not in registry: {', '.join(unknown_assets)}")

    enabled_requests = [item for item in request["requested_assets"] if item["enabled"]]
    release_roots = [factory["assets"][item["asset_id"]]["release_root"] for item in enabled_requests]
    for release_root in release_roots:
        if is_relative_to(package_root, release_root):
            raise HFXShotBindingError(
                f"shot package writes inside release package directories are blocked: {package_root}"
            )

    if package_root.exists():
        assert_package_path_allowed(package_root)
        shutil.rmtree(package_root)

    dirs = package_directories(package_root)
    for directory in dirs.values():
        guard_write_path(directory, release_roots)
        directory.mkdir(parents=True, exist_ok=True)

    request_snapshot_path = dirs["request"] / f"HFX_SHOT_BINDING_REQUEST_{request['shot_id']}_{request['take_id']}.json"
    request_snapshot = {
        "schema_type": "ShotBindingRequest",
        "source_request_path": request_path.as_posix(),
        "request": copy.deepcopy(request),
    }
    guard_write_path(request_snapshot_path, release_roots)
    write_json(request_snapshot_path, request_snapshot)

    asset_bindings: list[dict[str, Any]] = []
    source_hash_records: list[dict[str, Any]] = []
    for asset_request in enabled_requests:
        asset_id = asset_request["asset_id"]
        asset = factory["assets"][asset_id]
        profile = profiles[asset_id]

        release_hip: Path = asset["release_hip"]
        final_asset_seal: Path = asset["final_asset_seal"]
        if not release_hip.exists():
            raise HFXShotBindingError(f"requested asset lacks release HIP: {asset_id}")
        if not final_asset_seal.exists():
            raise HFXShotBindingError(f"requested asset lacks final seal: {asset_id}")

        source_sha_before = sha256_file(release_hip)
        shot_hip_path = dirs["shot_hip"] / f"{asset_id}__{release_hip.name}"
        guard_write_path(shot_hip_path, release_roots)
        shutil.copyfile(release_hip, shot_hip_path)
        source_sha_after = sha256_file(release_hip)
        if source_sha_before != source_sha_after:
            raise HFXShotBindingError(f"source release HIP sha256 changed during binding: {release_hip}")
        copied_sha = sha256_file(shot_hip_path)

        hash_record = {
            "asset_id": asset_id,
            "source_release_hip": release_hip.as_posix(),
            "sha256_before": source_sha_before,
            "sha256_after": source_sha_after,
        }
        source_hash_records.append(hash_record)

        parameter_path = dirs["parameters"] / per_asset_filename(
            asset_id, request["shot_id"], request["take_id"], "PARAMETERS.json"
        )
        parameter_payload = {
            "schema_type": "ShotParameterSet",
            "asset_id": asset_id,
            "asset_name": asset["asset_name"],
            "shot_id": request["shot_id"],
            "take_id": request["take_id"],
            "enabled": True,
            "dependency_policy": asset_request["dependency_policy"],
            "parameter_defaults": copy.deepcopy(profile["parameter_defaults"]),
            "parameter_overrides": copy.deepcopy(asset_request["parameter_overrides"]),
            "resolved_parameters": merge_parameters(
                profile["parameter_defaults"],
                asset_request["parameter_overrides"],
            ),
            "source_release_hip": release_hip.as_posix(),
            "copied_shot_hip": shot_hip_path.as_posix(),
            "direct_release_mutation_forbidden": True,
        }
        guard_write_path(parameter_path, release_roots)
        write_json(parameter_path, parameter_payload)

        source_reference_path = dirs["source_assets"] / per_asset_filename(
            asset_id, request["shot_id"], request["take_id"], "SOURCE_RELEASE_REFERENCE.json"
        )
        source_reference = {
            "asset_id": asset_id,
            "asset_name": asset["asset_name"],
            "release_root": asset["release_root"].as_posix(),
            "release_hip": release_hip.as_posix(),
            "final_asset_seal": final_asset_seal.as_posix(),
            "source_release_hip_sha256": source_sha_before,
            "registry_entry_snapshot": copy.deepcopy(asset["registry_entry"]),
        }
        guard_write_path(source_reference_path, release_roots)
        write_json(source_reference_path, source_reference)

        binding_record = {
            "schema_type": "ShotAssetBinding",
            "asset_id": asset_id,
            "asset_name": asset["asset_name"],
            "enabled": True,
            "shot_id": request["shot_id"],
            "take_id": request["take_id"],
            "release_root": asset["release_root"].as_posix(),
            "release_hip": release_hip.as_posix(),
            "shot_hip": shot_hip_path.as_posix(),
            "final_asset_seal": final_asset_seal.as_posix(),
            "source_release_hip_sha256": source_sha_before,
            "copied_shot_hip_sha256": copied_sha,
            "parameter_file": parameter_path.as_posix(),
            "source_reference_file": source_reference_path.as_posix(),
            "dependency_policy": asset_request["dependency_policy"],
            "registry_entry_snapshot": copy.deepcopy(asset["registry_entry"]),
        }
        binding_path = dirs["manifests"] / per_asset_filename(
            asset_id, request["shot_id"], request["take_id"], "BINDING_RECORD.json"
        )
        guard_write_path(binding_path, release_roots)
        write_json(binding_path, binding_record)
        binding_record["binding_record_path"] = binding_path.as_posix()
        asset_bindings.append(binding_record)

    render_contract_path = (
        dirs["render_contract"] / f"HFX_RENDER_CONTRACT_{request['shot_id']}_{request['take_id']}.json"
    )
    comp_contract_path = (
        dirs["comp_contract"] / f"HFX_COMP_CONTRACT_{request['shot_id']}_{request['take_id']}.json"
    )
    operator_guide_path = (
        dirs["docs"] / f"HFX_SHOT_OPERATOR_GUIDE_{request['shot_id']}_{request['take_id']}.md"
    )
    mutation_guard_path = (
        dirs["validation"] / f"HFX_MUTATION_GUARD_REPORT_{request['shot_id']}_{request['take_id']}.json"
    )
    validation_report_path = (
        dirs["validation"] / f"HFX_SHOT_VALIDATION_REPORT_{request['shot_id']}_{request['take_id']}.json"
    )
    manifest_path = (
        dirs["manifests"] / f"HFX_SHOT_BINDING_MANIFEST_{request['shot_id']}_{request['take_id']}.json"
    )

    render_contract = build_render_contract(request, asset_bindings, profiles)
    comp_contract = build_comp_contract(request, asset_bindings, profiles)
    mutation_guard = build_mutation_guard_report(
        request,
        package_root,
        source_hash_records,
        release_roots,
    )
    manifest = {
        "schema_type": "ShotBindingManifest",
        "status": "HFX_SHOT_BINDING_MANIFEST_READY",
        "project_id": request["project_id"],
        "sequence_id": request["sequence_id"],
        "shot_id": request["shot_id"],
        "take_id": request["take_id"],
        "package_root": package_root.as_posix(),
        "source_authority": {
            "core12_root": CORE12_ROOT.as_posix(),
            "registry_path": REGISTRY_PATH.as_posix(),
            "registry_sha256": sha256_file(REGISTRY_PATH),
            "global_seal_path": GLOBAL_SEAL_PATH.as_posix(),
            "global_seal_sha256": sha256_file(GLOBAL_SEAL_PATH),
            "global_seal_status": factory["global_seal"]["status"],
        },
        "request_snapshot": request_snapshot_path.as_posix(),
        "asset_bindings": asset_bindings,
        "render_contract": render_contract_path.as_posix(),
        "comp_contract": comp_contract_path.as_posix(),
        "operator_guide": operator_guide_path.as_posix(),
        "mutation_guard_report": mutation_guard_path.as_posix(),
        "validation_report": validation_report_path.as_posix(),
        "explicit_blocked_claims": [
            "Hollywood final-pixel shot complete",
            "OpenEXR render completion",
            "final comp completion",
            "client/public delivery ready",
        ],
    }

    for output_path, payload in [
        (render_contract_path, render_contract),
        (comp_contract_path, comp_contract),
        (mutation_guard_path, mutation_guard),
        (manifest_path, manifest),
    ]:
        guard_write_path(output_path, release_roots)
        write_json(output_path, payload)

    write_text(
        operator_guide_path,
        build_operator_guide(request, asset_bindings, render_contract_path, comp_contract_path),
    )

    validation_report = validate_shot_package(package_root, require_validation_report=False)
    guard_write_path(validation_report_path, release_roots)
    write_json(validation_report_path, validation_report)

    return {
        "status": "HFX_SHOT_BINDING_PACKAGE_READY",
        "package_root": package_root.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "validation_report_path": validation_report_path.as_posix(),
        "asset_count": len(asset_bindings),
    }


def find_manifest(package_root: Path) -> Path:
    manifest_dir = package_root / "07_manifests"
    manifests = sorted(manifest_dir.glob("HFX_SHOT_BINDING_MANIFEST_*.json"))
    if not manifests:
        raise HFXShotBindingError(f"manifest does not exist under {manifest_dir}")
    if len(manifests) > 1:
        raise HFXShotBindingError(f"multiple shot binding manifests found under {manifest_dir}")
    return manifests[0]


def validate_no_forbidden_package_files(package_root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for file_path in sorted(path for path in package_root.rglob("*") if path.is_file()):
        name = file_path.name
        suffix = file_path.suffix.lower()
        forbidden = suffix in FORBIDDEN_PACKAGE_SUFFIXES or name == ".DS_Store" or name.startswith("._")
        checks.append(
            {
                "check_id": "forbidden_file_type",
                "path": file_path.as_posix(),
                "passed": not forbidden,
            }
        )
    return checks


def validate_shot_package(package_root: Path, require_validation_report: bool = True) -> dict[str, Any]:
    package_root = package_root.resolve(strict=False)
    if not package_root.exists() or not package_root.is_dir():
        raise HFXShotBindingError(f"shot package path does not exist: {package_root}")

    checks: list[dict[str, Any]] = []

    def check(condition: bool, check_id: str, detail: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(condition), "detail": detail})

    manifest_path = find_manifest(package_root)
    manifest = load_json(manifest_path)
    check(True, "manifest_exists", manifest_path.as_posix())

    request_snapshot = Path(manifest.get("request_snapshot", ""))
    render_contract = Path(manifest.get("render_contract", ""))
    comp_contract = Path(manifest.get("comp_contract", ""))
    operator_guide = Path(manifest.get("operator_guide", ""))
    mutation_guard_report = Path(manifest.get("mutation_guard_report", ""))
    validation_report = Path(manifest.get("validation_report", ""))

    for check_id, path in [
        ("request_snapshot_exists", request_snapshot),
        ("render_contract_exists", render_contract),
        ("comp_contract_exists", comp_contract),
        ("operator_guide_exists", operator_guide),
        ("mutation_guard_report_exists", mutation_guard_report),
    ]:
        check(path.exists(), check_id, path.as_posix())
    if require_validation_report:
        check(validation_report.exists(), "validation_report_exists", validation_report.as_posix())

    asset_bindings = manifest.get("asset_bindings", [])
    check(isinstance(asset_bindings, list) and bool(asset_bindings), "asset_bindings_non_empty", "manifest asset_bindings")
    for binding in asset_bindings:
        asset_id = binding.get("asset_id", "UNKNOWN")
        source_release_hip = Path(binding.get("release_hip", ""))
        copied_shot_hip = Path(binding.get("shot_hip", ""))
        source_expected_sha = binding.get("source_release_hip_sha256")
        copied_expected_sha = binding.get("copied_shot_hip_sha256")

        check(source_release_hip.exists(), f"{asset_id}_source_release_hip_exists", source_release_hip.as_posix())
        check(copied_shot_hip.exists(), f"{asset_id}_copied_shot_hip_exists", copied_shot_hip.as_posix())
        if source_release_hip.exists():
            check(
                sha256_file(source_release_hip) == source_expected_sha,
                f"{asset_id}_source_sha256_matches_manifest",
                source_release_hip.as_posix(),
            )
        else:
            check(False, f"{asset_id}_source_sha256_matches_manifest", source_release_hip.as_posix())
        if copied_shot_hip.exists():
            check(
                sha256_file(copied_shot_hip) == copied_expected_sha,
                f"{asset_id}_copied_sha256_matches_manifest",
                copied_shot_hip.as_posix(),
            )
        else:
            check(False, f"{asset_id}_copied_sha256_matches_manifest", copied_shot_hip.as_posix())

    checks.extend(validate_no_forbidden_package_files(package_root))
    passed = all(item["passed"] for item in checks)
    report = {
        "schema_type": "ShotValidationReport",
        "status": "PASS" if passed else "FAIL",
        "shot_id": manifest.get("shot_id"),
        "take_id": manifest.get("take_id"),
        "package_root": package_root.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "checks": checks,
        "blocked_claims": [
            "Hollywood final-pixel shot complete",
            "OpenEXR render completion",
            "final comp completion",
            "client/public delivery ready",
        ],
    }
    if not passed:
        failed = [item["check_id"] for item in checks if not item["passed"]]
        raise HFXShotBindingError(f"shot package validation failed: {', '.join(failed)}")
    return report


def schema_paths() -> list[Path]:
    return sorted((LAYER_ROOT / "schemas").glob("*.schema.json"))


def validate_layer_schemas() -> dict[str, Any]:
    required_titles = {
        "ShotBindingRequest",
        "ShotBindingManifest",
        "ShotAssetBinding",
        "ShotParameterSet",
        "ShotValidationReport",
        "RenderCompChecklist",
        "MutationGuardReport",
    }
    checks: list[dict[str, Any]] = []
    found_titles: set[str] = set()
    for path in schema_paths():
        schema = load_json(path)
        title = schema.get("title")
        found_titles.add(title)
        checks.append(
            {
                "check_id": f"schema_{path.name}_is_strict_object",
                "passed": schema.get("type") == "object" and schema.get("additionalProperties") is False,
                "detail": path.as_posix(),
            }
        )
        if title == "ShotBindingRequest":
            checks.append(
                {
                    "check_id": "shot_binding_request_required_fields",
                    "passed": schema.get("required") == REQUEST_REQUIRED_FIELDS,
                    "detail": path.as_posix(),
                }
            )
    missing = sorted(required_titles - found_titles)
    checks.append(
        {
            "check_id": "all_required_schema_titles_present",
            "passed": not missing,
            "detail": ",".join(missing),
        }
    )
    passed = all(item["passed"] for item in checks)
    if not passed:
        failed = [item["check_id"] for item in checks if not item["passed"]]
        raise HFXShotBindingError(f"schema validation failed: {', '.join(failed)}")
    return {"status": "PASS", "schema_count": len(schema_paths()), "checks": checks}


def example_request_paths() -> list[Path]:
    return [
        LAYER_ROOT / "examples" / "shot_request_energy_impact.json",
        LAYER_ROOT / "examples" / "shot_request_portal_arrival.json",
        LAYER_ROOT / "examples" / "shot_request_black_hole.json",
    ]


def iter_layer_manifest_files() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(LAYER_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(LAYER_ROOT).as_posix()
        if rel in GLOBAL_LAYER_OUTPUTS:
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        paths.append(path)
    return paths


def write_layer_manifests() -> dict[str, Any]:
    files = []
    lines = []
    tree = []
    for path in iter_layer_manifest_files():
        relative = path.relative_to(LAYER_ROOT).as_posix()
        digest = sha256_file(path)
        files.append(
            {
                "path": relative,
                "sha256": digest,
                "size_bytes": path.stat().st_size,
            }
        )
        lines.append(f"{digest}  {relative}")
        tree.append(relative)

    sha_path = LAYER_ROOT / "manifests" / "HFX_SHOT_BINDING_LAYER_SHA256SUMS.txt"
    tree_path = LAYER_ROOT / "manifests" / "HFX_SHOT_BINDING_LAYER_FILE_TREE.txt"
    manifest_path = LAYER_ROOT / "manifests" / "HFX_SHOT_BINDING_LAYER_MANIFEST.json"

    write_text(sha_path, "\n".join(lines))
    write_text(tree_path, "\n".join(tree))
    manifest = {
        "status": "HFX_SHOT_BINDING_LAYER_MANIFEST_READY",
        "layer_root": relpath(LAYER_ROOT),
        "file_count": len(files),
        "files": files,
        "excluded_self_referential_outputs": sorted(GLOBAL_LAYER_OUTPUTS),
    }
    write_json(manifest_path, manifest)
    return {
        "manifest_path": manifest_path.as_posix(),
        "sha256sums_path": sha_path.as_posix(),
        "file_tree_path": tree_path.as_posix(),
        "file_count": len(files),
    }


def run_global_shot_binding_seal() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    factory = validate_factory_core12()
    checks.append(
        {
            "check_id": "factory_core12_global_seal",
            "passed": factory["status"] == "PASS",
            "detail": GLOBAL_SEAL_PATH.as_posix(),
        }
    )

    schema_report = validate_layer_schemas()
    checks.append(
        {
            "check_id": "shot_binding_schemas",
            "passed": schema_report["status"] == "PASS",
            "detail": f"{schema_report['schema_count']} schemas",
        }
    )

    for example_path in example_request_paths():
        bind_result = bind_shot(example_path)
        validation_result = validate_shot_package(Path(bind_result["package_root"]))
        example_record = {
            "request": example_path.as_posix(),
            "package_root": bind_result["package_root"],
            "bind_status": bind_result["status"],
            "validation_status": validation_result["status"],
            "asset_count": bind_result["asset_count"],
        }
        examples.append(example_record)
        checks.append(
            {
                "check_id": f"example_{example_path.stem}_binds_and_validates",
                "passed": bind_result["status"] == "HFX_SHOT_BINDING_PACKAGE_READY"
                and validation_result["status"] == "PASS",
                "detail": bind_result["package_root"],
            }
        )

    layer_manifest = write_layer_manifests()
    checks.append(
        {
            "check_id": "layer_manifest_outputs",
            "passed": layer_manifest["file_count"] > 0,
            "detail": layer_manifest["manifest_path"],
        }
    )

    passed = all(item["passed"] for item in checks)
    status = "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL_PASS" if passed else "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL_FAIL"
    seal = {
        "status": status,
        "validated": passed,
        "layer_id": "HFX_FACTORY_SHOT_BINDING_LAYER",
        "source_authority": {
            "factory_core12_global_seal_status": factory["global_seal"]["status"],
            "asset_count_required": factory["global_seal"]["asset_count_required"],
            "asset_count_passed": factory["global_seal"]["asset_count_passed"],
            "registry_path": REGISTRY_PATH.as_posix(),
            "global_seal_path": GLOBAL_SEAL_PATH.as_posix(),
        },
        "schema_validation": schema_report,
        "example_packages": examples,
        "layer_manifest": layer_manifest,
        "checks": checks,
        "allowed_claims": [
            "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL_PASS",
            "deterministic auditable per-shot binding packages generated",
            "Core 12 release HIP files copied into shot working packages without source mutation",
        ],
        "blocked_claims": [
            "Hollywood final-pixel shot complete",
            "actual OpenEXR pixels rendered",
            "actual final comp rendered",
            "client/public delivery ready",
        ],
        "next_layer_recommendation": "Houdini batch render automation, EXR validation, comp automation, and final-pixel review gates.",
    }
    seal_json_path = LAYER_ROOT / "validation" / "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.json"
    seal_md_path = LAYER_ROOT / "validation" / "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.md"
    write_json(seal_json_path, seal)
    write_text(
        seal_md_path,
        f"""# HFX Shot Binding Layer Global Seal

Status: `{status}`

Validated: `{str(passed).lower()}`

This seal confirms deterministic per-shot binding package generation from the sealed HFX Factory Core 12 release packages.
It does not claim Hollywood final-pixel completion, OpenEXR render completion, final comp completion, or client delivery readiness.

Generated example packages:
{chr(10).join(f"- `{item['request']}` -> `{item['package_root']}`" for item in examples)}

Next layer recommendation: Houdini batch render automation, EXR validation, comp automation, and final-pixel review gates.
""",
    )
    if not passed:
        failed = [item["check_id"] for item in checks if not item["passed"]]
        raise HFXShotBindingError(f"global shot binding seal failed: {', '.join(failed)}")
    return seal
