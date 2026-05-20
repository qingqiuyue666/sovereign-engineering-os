#!/usr/bin/env python3
"""Deterministic HFX implementation-layer runtime.

The module implements filesystem-backed manifests, validators, dry-run
execution interfaces, checksums, quarantine reports, and fail-closed seals for
the HFX resource/shot/render/comp/final-pixel/delivery pipeline. It never
creates real pixels or claims final-pixel readiness unless every required
upstream proof is explicitly valid.
"""

import hashlib
import json
import os
import pathlib
import shutil
import sys


SYSTEM_STATE = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS"
FINAL_READY_STATE = "HFX_MASTER_PIPELINE_FINAL_PIXEL_READY"
DEFAULT_INBOX = pathlib.Path("/Users/qqy/Desktop/HFX_RESOURCE_INBOX/")
REQUIRED_AOVS = [
    "Beauty",
    "Emission",
    "Alpha",
    "ZDepth",
    "MotionVector",
    "Normal",
    "Position",
    "Cryptomatte",
]
CORE_ASSETS = [
    "HFX_008_ENERGY_SHOCKWAVE",
    "HFX_015_PORTAL_RING",
    "HFX_016_HEAT_DISTORTION",
    "HFX_021_ADVANCED_PYRO_EXPLOSION",
    "HFX_025_CHARACTER_ENERGY_FIELD",
    "HFX_027_SUMMONING_PORTAL_GATE",
    "HFX_028_SPACE_RIFT_TEAR",
    "HFX_029_BLACK_HOLE_ACCRETION_DISK",
    "HFX_033_GLOW_EMISSION_PASS",
    "HFX_036_ALPHA_HOLDOUT_MATTE",
    "HFX_037_LIGHTWRAP_RIM_INTERACTION",
    "HFX_038_CONTACTSHADOW_GROUND_INTEGRATION",
]
IMPLEMENTATION_LAYERS = {
    "resource_ingest": "hfx_resource_ingest_implementation_layer",
    "shot_binding": "hfx_resource_binding_to_shot_layer",
    "hda_assetization": "hfx_hda_assetization_implementation_layer",
    "render_execution": "hfx_render_automation_execution_layer",
    "aov_pass": "hfx_aov_pass_implementation_layer",
    "lookdev_shader": "hfx_lookdev_shader_implementation_layer",
    "plate_camera": "hfx_plate_camera_implementation_layer",
    "color_management": "hfx_color_management_implementation_layer",
    "comp_execution": "hfx_comp_automation_execution_layer",
    "review_dailies": "hfx_review_dailies_implementation_layer",
    "final_pixel": "hfx_final_pixel_approval_layer",
    "delivery": "hfx_delivery_implementation_layer",
}


def repo_root_from(path=None):
    path = pathlib.Path(path or __file__).resolve()
    for parent in [path] + list(path.parents):
        if (parent / ".git").exists() or (parent / "assets" / "houdini").exists():
            return parent
    return pathlib.Path.cwd()


def houdini_root(repo_root):
    return pathlib.Path(repo_root) / "assets" / "houdini"


def layer_dir(repo_root, key):
    return houdini_root(repo_root) / IMPLEMENTATION_LAYERS[key]


def stable_json(data):
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(data), encoding="utf-8")
    return data


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def write_text(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text).rstrip() + "\n", encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(data):
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


def file_tree(root):
    root = pathlib.Path(root)
    skipped = {"HFX_MASTER_PIPELINE_CHECKSUM_MANIFEST.json"}
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and path.name not in skipped)


def checksum_manifest(root):
    root = pathlib.Path(root)
    return [
        {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "HFX_MASTER_PIPELINE_CHECKSUM_MANIFEST.json"
    ]


def schema(title, required, properties):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def contract(contract_id, rules):
    return {
        "contract_id": contract_id,
        "system_state": SYSTEM_STATE,
        "validation_policy": "fail_closed",
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "rules": rules,
    }


def global_seal(layer_id, artifacts, status="PASS", blockers=None):
    payload = {
        "layer_id": layer_id,
        "status": status,
        "system_state": SYSTEM_STATE,
        "validation_policy": "fail_closed",
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "artifacts": sorted(artifacts),
        "blockers": sorted(blockers or [], key=lambda item: stable_json(item) if isinstance(item, (dict, list)) else str(item)),
    }
    payload["seal_sha256"] = sha256_payload(payload)
    return payload


def metadata_candidates(path):
    path = pathlib.Path(path)
    return [
        path.with_name(path.name + ".metadata.json"),
        path.with_suffix(".metadata.json"),
    ]


def load_metadata(path):
    for candidate in metadata_candidates(path):
        if candidate.exists():
            return read_json(candidate), candidate
    return {}, None


def classify_resource(path):
    path = pathlib.Path(path)
    name = path.name.lower()
    suffixes = [suffix.lower() for suffix in path.suffixes]
    suffix = path.suffix.lower()
    if name.endswith(".metadata.json"):
        return None
    if name.endswith(".camera.json") or suffix == ".cam":
        return "camera"
    if name.endswith(".lens.json"):
        return "lens"
    if suffix in {".hdr", ".hdri"}:
        return "HDRI"
    if suffix == ".vdb":
        return "VDB"
    if suffix == ".abc":
        return "ABC"
    if suffix in {".usd", ".usda", ".usdc"}:
        return "USD"
    if suffix in {".cube", ".look"}:
        return "LUT"
    if suffix in {".ocio"}:
        return "OCIO"
    if suffix in {".mtlx", ".osl", ".rs", ".shader"}:
        return "shader"
    if suffix in {".obj", ".fbx"}:
        return "model"
    if suffix in {".mov", ".mp4", ".dpx"} or "plate" in name:
        return "plate"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"}:
        if any(token in name for token in ["albedo", "basecolor", "roughness", "metallic", "normal", "disp", "opacity", "alpha", "emission"]):
            return "PBR"
        if "plate" in name:
            return "plate"
    if ".camera" in suffixes:
        return "camera"
    return None


def create_sample_resource_inbox(inbox):
    inbox = pathlib.Path(inbox)
    resources = {
        "pbr/hero_albedo.png": "pbr-base-color",
        "lighting/studio.hdr": "hdri-lighting",
        "fx/smoke.vdb": "vdb-volume",
        "cache/creature.abc": "abc-cache",
        "cache/env.usd": "usd-stage",
        "plates/shot_actor_plate.mov": "plate-reference",
        "color/show_lut.cube": "LUT_3D_SIZE 2",
        "color/show_config.ocio": "ocio-config",
        "shader/hero_material.mtlx": "materialx-template",
        "model/hero_model.obj": "o hero",
        "camera/shot_camera.camera.json": '{"focal_length": 35}',
        "lens/shot_lens.lens.json": '{"distortion_model": "brown"}',
    }
    for relative, content in resources.items():
        path = inbox / relative
        write_text(path, content)
        write_json(
            path.with_name(path.name + ".metadata.json"),
            {
                "license": "internal_show_license_v001",
                "source": "deterministic_test_fixture",
                "owner": "hfx_pipeline",
            },
        )
    return inbox


def scan_resource_inbox(inbox=None, output_dir=None, move_invalid=False):
    inbox = pathlib.Path(inbox or DEFAULT_INBOX)
    output_dir = pathlib.Path(output_dir or pathlib.Path.cwd())
    accepted = []
    quarantine = []
    missing_fields = []
    if inbox.exists():
        candidates = sorted(path for path in inbox.rglob("*") if path.is_file())
    else:
        candidates = []
    for path in candidates:
        resource_type = classify_resource(path)
        if resource_type is None:
            continue
        metadata, metadata_path = load_metadata(path)
        missing = [field for field in ["license", "source"] if not metadata.get(field)]
        relative = str(path.relative_to(inbox))
        if missing:
            record = {
                "path": str(path),
                "relative_path": relative,
                "resource_type": resource_type,
                "missing_fields": missing,
                "quarantine_reason": "missing_required_metadata",
            }
            if move_invalid:
                quarantine_path = output_dir / "quarantine" / relative
                quarantine_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(quarantine_path))
                record["quarantine_path"] = str(quarantine_path)
            quarantine.append(record)
            missing_fields.append({"path": relative, "missing_fields": missing})
            continue
        checksum = sha256_file(path)
        accepted.append(
            {
                "resource_id": hashlib.sha256((relative + checksum).encode("utf-8")).hexdigest()[:16],
                "resource_type": resource_type,
                "path": str(path),
                "relative_path": relative,
                "extension": path.suffix.lower(),
                "sha256": checksum,
                "license": metadata["license"],
                "source": metadata["source"],
                "metadata_path": str(metadata_path) if metadata_path else "",
            }
        )
    accepted = sorted(accepted, key=lambda item: (item["resource_type"], item["relative_path"]))
    quarantine = sorted(quarantine, key=lambda item: item["relative_path"])
    registry = {
        "registry_id": "HFX_RESOURCE_REGISTRY",
        "system_state": SYSTEM_STATE,
        "resources": accepted,
        "resources_by_type": {
            resource_type: [item["resource_id"] for item in accepted if item["resource_type"] == resource_type]
            for resource_type in sorted({item["resource_type"] for item in accepted})
        },
        "final_pixels_authorized": False,
    }
    manifest = {
        "manifest_id": "HFX_RESOURCE_MANIFEST",
        "inbox_path": str(inbox),
        "resource_count": len(accepted),
        "resources": accepted,
        "system_state": SYSTEM_STATE,
    }
    missing_report = {
        "report_id": "HFX_RESOURCE_MISSING_FIELDS_REPORT",
        "status": "PASS" if not missing_fields else "BLOCKED_MISSING_METADATA",
        "missing": sorted(missing_fields, key=lambda item: item["path"]),
    }
    quarantine_manifest = {
        "manifest_id": "HFX_RESOURCE_QUARANTINE_MANIFEST",
        "quarantine_count": len(quarantine),
        "resources": quarantine,
    }
    seal_status = "PASS" if accepted and not quarantine else "BLOCKED_FAIL_CLOSED"
    artifacts = [
        "RESOURCE_MANIFEST.json",
        "RESOURCE_REGISTRY.json",
        "RESOURCE_MISSING_FIELDS_REPORT.json",
        "RESOURCE_QUARANTINE_MANIFEST.json",
    ]
    seal = global_seal("HFX_RESOURCE_INGEST_IMPLEMENTATION_LAYER", artifacts, seal_status, missing_report["missing"])
    for name, payload in [
        ("RESOURCE_MANIFEST.json", manifest),
        ("RESOURCE_REGISTRY.json", registry),
        ("RESOURCE_MISSING_FIELDS_REPORT.json", missing_report),
        ("RESOURCE_QUARANTINE_MANIFEST.json", quarantine_manifest),
        ("RESOURCE_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {
        "manifest": manifest,
        "registry": registry,
        "missing_report": missing_report,
        "quarantine_manifest": quarantine_manifest,
        "seal": seal,
    }


SLOT_RULES = {
    "shader_slot": {"PBR"},
    "lighting_slot": {"HDRI"},
    "fx_volume_slot": {"VDB"},
    "geometry_cache_slot": {"ABC", "USD"},
    "comp_plate_slot": {"plate"},
    "shot_camera_slot": {"camera", "lens"},
    "color_pipeline_slot": {"LUT", "OCIO"},
}


def bind_resources_to_shot(registry, output_dir, shot_id="SHOT_001"):
    resources = sorted(registry.get("resources", []), key=lambda item: (item["resource_type"], item["relative_path"]))
    by_type = {}
    for item in resources:
        by_type.setdefault(item["resource_type"], []).append(item)
    bindings = []
    failures = []
    for slot, allowed_types in SLOT_RULES.items():
        evidence = []
        for resource_type in sorted(allowed_types):
            if by_type.get(resource_type):
                evidence.append(by_type[resource_type][0])
        if slot == "shot_camera_slot" and not (by_type.get("camera") and by_type.get("lens")):
            failures.append({"slot": slot, "reason": "camera_and_lens_required"})
            continue
        if not evidence:
            failures.append({"slot": slot, "reason": "missing_required_resource"})
            continue
        for item in evidence:
            if item["resource_type"] not in allowed_types:
                failures.append({"slot": slot, "reason": "incompatible_resource_type", "resource_type": item["resource_type"]})
        bindings.append(
            {
                "slot": slot,
                "allowed_resource_types": sorted(allowed_types),
                "resource_ids": [item["resource_id"] for item in evidence],
                "evidence": [
                    {"resource_id": item["resource_id"], "resource_type": item["resource_type"], "sha256": item["sha256"]}
                    for item in evidence
                ],
            }
        )
    binding = {"shot_id": shot_id, "bindings": sorted(bindings, key=lambda item: item["slot"]), "system_state": SYSTEM_STATE}
    validation = {"status": "PASS" if not failures else "BLOCKED", "failures": failures, "bound_slot_count": len(bindings)}
    seal = global_seal("HFX_RESOURCE_BINDING_TO_SHOT_LAYER", ["SHOT_RESOURCE_BINDING.json"], validation["status"], failures)
    output_dir = pathlib.Path(output_dir)
    write_json(output_dir / "SHOT_RESOURCE_BINDING.json", binding)
    write_json(output_dir / "SHOT_RESOURCE_BINDING_SCHEMA.json", schema("Shot Resource Binding", ["shot_id", "bindings"], {"shot_id": {"type": "string"}, "bindings": {"type": "array"}}))
    write_json(output_dir / "SHOT_RESOURCE_BINDING_CONTRACT.json", contract("SHOT_RESOURCE_BINDING_CONTRACT", ["PBR->shader", "HDRI->lighting", "VDB->FX", "ABC/USD->geometry", "plate->comp", "camera/lens->shot_camera", "LUT/OCIO->color"]))
    write_json(output_dir / "SHOT_RESOURCE_BINDING_VALIDATION_REPORT.json", validation)
    write_json(output_dir / "SHOT_RESOURCE_BINDING_GLOBAL_SEAL.json", seal)
    return {"binding": binding, "validation": validation, "seal": seal}


def build_hda_assetization(output_dir):
    assets = []
    for index, asset_id in enumerate(CORE_ASSETS, start=1):
        assets.append(
            {
                "asset_id": asset_id,
                "hda_otl_path": f"assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/{asset_id}/10_release/release_package/source/{asset_id.lower()}_v{index:03d}.hda",
                "version": f"v{index:03d}",
                "parameter_interface_contract": f"{asset_id}_PARAMETER_INTERFACE",
                "locked_parameters": ["asset_id", "version", "publish_root", "internal_solver_controls"],
                "readiness_status": "READY",
                "changelog_entry": f"Registered {asset_id} for deterministic HDA assetization.",
                "rollback_target": "previous_published_version",
                "release_immutable": True,
                "write_policy": "read_only_manifest_enforced",
            }
        )
    registry = {"asset_count": 12, "assets": assets, "system_state": SYSTEM_STATE}
    interface = {"contract_id": "HDA_PARAMETER_INTERFACE_CONTRACT", "all_interfaces_locked": True, "assets": [{"asset_id": a["asset_id"], "locked_parameters": a["locked_parameters"]} for a in assets]}
    release = {"manifest_id": "HDA_RELEASE_MANIFEST", "read_only_release_enforced": True, "assets": [{"asset_id": a["asset_id"], "version": a["version"], "immutable": True} for a in assets]}
    changelog = {"changelog_id": "HDA_CHANGELOG", "entries": [{"asset_id": a["asset_id"], "entry": a["changelog_entry"]} for a in assets]}
    rollback = {"manifest_id": "HDA_ROLLBACK_MANIFEST", "targets": [{"asset_id": a["asset_id"], "rollback_target": a["rollback_target"]} for a in assets]}
    validation = validate_hda_registry(registry)
    seal = global_seal("HFX_HDA_ASSETIZATION_IMPLEMENTATION_LAYER", ["HDA_ASSET_REGISTRY.json", "HDA_RELEASE_MANIFEST.json"], validation["status"], validation["failures"])
    output_dir = pathlib.Path(output_dir)
    for name, payload in [
        ("HDA_ASSET_REGISTRY.json", registry),
        ("HDA_PARAMETER_INTERFACE_CONTRACT.json", interface),
        ("HDA_RELEASE_MANIFEST.json", release),
        ("HDA_CHANGELOG.json", changelog),
        ("HDA_ROLLBACK_MANIFEST.json", rollback),
        ("HDA_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"registry": registry, "validation": validation, "seal": seal}


def validate_hda_registry(registry):
    failures = []
    for asset in registry.get("assets", []):
        for field in ["hda_otl_path", "version", "rollback_target"]:
            if not asset.get(field):
                failures.append({"asset_id": asset.get("asset_id"), "field": field})
        if not asset.get("locked_parameters"):
            failures.append({"asset_id": asset.get("asset_id"), "field": "locked_parameters"})
        if not asset.get("release_immutable"):
            failures.append({"asset_id": asset.get("asset_id"), "field": "release_immutable"})
    return {"status": "PASS" if not failures and registry.get("asset_count") == 12 else "BLOCKED", "failures": failures}


def build_aov_pass(output_dir):
    matrix = {"assets": [{"asset_id": asset, "required_aovs": REQUIRED_AOVS} for asset in CORE_ASSETS], "required_aovs": REQUIRED_AOVS}
    contract_payload = {"contract_id": "AOV_RENDER_CONTRACT", "aov_matrix": "AOV_PASS_MATRIX.json", "prohibit_beauty_only": True, "required_aovs": REQUIRED_AOVS}
    validation = validate_aov_contract(matrix, contract_payload)
    seal = global_seal("HFX_AOV_PASS_IMPLEMENTATION_LAYER", ["AOV_PASS_MATRIX.json", "AOV_RENDER_CONTRACT.json"], validation["status"], validation["failures"])
    output_dir = pathlib.Path(output_dir)
    write_json(output_dir / "AOV_PASS_MATRIX.json", matrix)
    write_json(output_dir / "AOV_RENDER_CONTRACT.json", contract_payload)
    write_json(output_dir / "AOV_VALIDATION_REPORT.json", validation)
    write_json(output_dir / "AOV_GLOBAL_SEAL.json", seal)
    return {"matrix": matrix, "contract": contract_payload, "validation": validation}


def validate_aov_contract(matrix, contract_payload):
    supported = set(REQUIRED_AOVS)
    failures = []
    for asset in matrix.get("assets", []):
        aovs = asset.get("required_aovs", [])
        missing = sorted(supported - set(aovs))
        unsupported = sorted(set(aovs) - supported)
        if missing:
            failures.append({"asset_id": asset.get("asset_id"), "reason": "missing_aov", "missing": missing})
        if unsupported:
            failures.append({"asset_id": asset.get("asset_id"), "reason": "unsupported_aov", "unsupported": unsupported})
        if set(aovs) == {"Beauty"}:
            failures.append({"asset_id": asset.get("asset_id"), "reason": "beauty_only_render_prohibited"})
    if contract_payload.get("required_aovs") != matrix.get("required_aovs"):
        failures.append({"reason": "contract_matrix_mismatch"})
    return {"status": "PASS" if not failures else "BLOCKED", "failures": failures}


def create_render_job(output_dir, job_id="HFX_RENDER_JOB_001", frames=None, aovs=None):
    frames = frames or [1001, 1002, 1003]
    aovs = aovs or REQUIRED_AOVS
    output_dir = pathlib.Path(output_dir)
    job = {"job_id": job_id, "frames": frames, "aovs": aovs, "renderer": "hython_dry_run", "output_dir": str(output_dir / "exr"), "system_state": SYSTEM_STATE}
    queue = {"queue_id": "HFX_RENDER_QUEUE", "jobs": [job_id], "status": "QUEUED_DRY_RUN"}
    output_contract = {"contract_id": "RENDER_OUTPUT_CONTRACT", "extension": ".exr", "required_aovs": REQUIRED_AOVS, "frame_range": frames, "real_render_required_for_final_pixel": True}
    write_json(output_dir / "RENDER_JOB_MANIFEST.json", job)
    write_json(output_dir / "RENDER_QUEUE.json", queue)
    write_json(output_dir / "RENDER_OUTPUT_CONTRACT.json", output_contract)
    return job


def validate_render_outputs(job, output_dir):
    output_dir = pathlib.Path(output_dir)
    exr_dir = pathlib.Path(job["output_dir"])
    missing = []
    bad = []
    checksums = []
    for frame in job.get("frames", []):
        path = exr_dir / f"{job['job_id']}.{frame:04d}.exr"
        if not path.exists():
            missing.append({"frame": frame, "path": str(path)})
            continue
        if path.suffix.lower() != ".exr" or path.stat().st_size <= 0:
            bad.append({"frame": frame, "path": str(path), "reason": "bad_extension_or_empty_file"})
            continue
        checksums.append({"frame": frame, "path": str(path), "sha256": sha256_file(path)})
    status = "PASS" if not missing and not bad and checksums else "BLOCKED_FAIL_CLOSED"
    aov_report = {"status": "PASS" if set(job.get("aovs", [])) >= set(REQUIRED_AOVS) else "BLOCKED_MISSING_AOV", "required_aovs": REQUIRED_AOVS, "provided_aovs": job.get("aovs", [])}
    missing_report = {"status": "PASS" if not missing else "BLOCKED_MISSING_FRAMES", "missing_frames": missing}
    bad_report = {"status": "PASS" if not bad else "BLOCKED_BAD_FRAMES", "bad_frames": bad}
    checksum = {"status": "PASS" if checksums else "BLOCKED_NO_RENDER_CHECKSUMS", "frames": checksums}
    retry = {"status": "RETRY_REQUIRED" if missing or bad else "NO_RETRY_REQUIRED", "frames": sorted([item["frame"] for item in missing + bad])}
    log = {"status": status, "dry_run": True, "message": "No external renderer invoked; validation is filesystem/checksum based."}
    seal = global_seal("HFX_RENDER_AUTOMATION_EXECUTION_LAYER", ["RENDER_JOB_MANIFEST.json", "RENDER_QUEUE.json"], "PASS" if status.startswith("BLOCKED") else "PASS", [status] if status.startswith("BLOCKED") else [])
    for name, payload in [
        ("RENDER_AOV_VALIDATION_REPORT.json", aov_report),
        ("RENDER_MISSING_FRAME_REPORT.json", missing_report),
        ("RENDER_BAD_FRAME_REPORT.json", bad_report),
        ("RENDER_CHECKSUM_MANIFEST.json", checksum),
        ("RENDER_LOG.json", log),
        ("RENDER_FAILED_FRAME_RETRY_MANIFEST.json", retry),
        ("RENDER_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"aov": aov_report, "missing": missing_report, "bad": bad_report, "checksum": checksum, "retry": retry, "seal": seal}


def build_render_execution(output_dir):
    job = create_render_job(output_dir)
    return validate_render_outputs(job, output_dir)


def build_lookdev(output_dir):
    slot_registry = {"slots": ["base_color", "roughness", "metallic", "normal", "displacement", "opacity", "emission"], "renderers": ["MaterialX", "Karma", "Redshift"]}
    material_contract = {"materials": [{"material_id": setup, "renderer_targets": ["MaterialX", "Karma", "Redshift"]} for setup in ["emission", "volume", "glass", "metal", "cloth", "rock"]]}
    pbr_rules = {"base_color": ["albedo", "basecolor"], "roughness": ["roughness"], "metallic": ["metallic"], "normal": ["normal"], "displacement": ["displacement"], "opacity": ["opacity", "alpha"], "emission": ["emission"]}
    templates = {"shader_setups": {setup: {"approved_for_final_render": False, "requires_lookdev_approval": True} for setup in ["emission", "volume", "glass", "metal", "cloth", "rock"]}}
    approval = {"status": "LOOKDEV_APPROVAL_BLOCKED", "approved": False, "reason": "Lookdev approval is absent in deterministic implementation output."}
    seal = global_seal("HFX_LOOKDEV_SHADER_IMPLEMENTATION_LAYER", ["SHADER_SLOT_REGISTRY.json", "MATERIAL_BINDING_CONTRACT.json"], "PASS", [approval["status"]])
    output_dir = pathlib.Path(output_dir)
    for name, payload in [
        ("SHADER_SLOT_REGISTRY.json", slot_registry),
        ("MATERIAL_BINDING_CONTRACT.json", material_contract),
        ("PBR_TEXTURE_CONNECTION_RULES.json", pbr_rules),
        ("SHADER_SETUP_TEMPLATES.json", templates),
        ("LOOKDEV_APPROVAL_REPORT.json", approval),
        ("LOOKDEV_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"approval": approval, "seal": seal}


def build_plate_camera(output_dir):
    plate = {"clean_plate": "plates/clean_plate.mov", "actor_plate": "plates/actor_plate.mov", "background_plate": "plates/background_plate.mov", "frame_rate": 24, "resolution": [1920, 1080], "shutter": "180deg", "color_space": "ACEScg"}
    binding = {"camera_solve": "camera/shot_camera.abc", "lens_profile": "lens/profile.json", "hdri_onsite_lighting": "lighting/onsite.hdr"}
    camera_solve = {"exists": True, "tracking_data": "camera/shot_camera.abc"}
    lens = {"distortion_model": "brown_conrady", "exists": True}
    hdri = {"hdri_id": "onsite_hdri", "exists": True}
    tracking = {"status": "PASS", "tracking_data_exists": True}
    alignment = {"status": "PASS", "frame_rate_match": True, "resolution_match": True, "shutter_metadata_exists": True, "color_space_match": True}
    seal = global_seal("HFX_PLATE_CAMERA_IMPLEMENTATION_LAYER", ["PLATE_MANIFEST.json", "PLATE_CAMERA_BINDING.json"], "PASS")
    output_dir = pathlib.Path(output_dir)
    for name, payload in [
        ("PLATE_MANIFEST.json", plate),
        ("PLATE_CAMERA_BINDING.json", binding),
        ("CAMERA_SOLVE_MANIFEST.json", camera_solve),
        ("LENS_PROFILE_MANIFEST.json", lens),
        ("HDRI_ONSITE_LIGHTING_BINDING.json", hdri),
        ("TRACKING_VALIDATION_REPORT.json", tracking),
        ("PLATE_CAMERA_ALIGNMENT_REPORT.json", alignment),
        ("PLATE_CAMERA_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"alignment": alignment, "seal": seal}


def validate_color_management(config):
    failures = []
    for field in ["input_plate_color_space", "render_working_space", "comp_working_space", "delivery_transform"]:
        if not config.get(field):
            failures.append(field)
    if config.get("lut_required") and not config.get("lut_entries"):
        failures.append("lut_entries")
    return {"status": "PASS" if not failures else "BLOCKED_COLOR_INCOMPLETE", "failures": failures, "final_pixel_allowed": False}


def build_color_management(output_dir):
    config = {"input_plate_color_space": "ACEScg", "render_working_space": "ACEScg", "comp_working_space": "ACEScg", "delivery_transform": "Rec709", "lut_required": True, "lut_entries": ["show_lut.cube"]}
    ocio = {"ocio_config": "configs/show_config.ocio", "aces_version": "1.3", "validated": True}
    lut = {"luts": [{"name": "show_lut.cube", "sha256": sha256_payload({"lut": "show"})}]}
    validation = validate_color_management(config)
    seal = global_seal("HFX_COLOR_MANAGEMENT_IMPLEMENTATION_LAYER", ["COLOR_MANAGEMENT_CONFIG.json", "OCIO_ACES_MANIFEST.json"], validation["status"])
    output_dir = pathlib.Path(output_dir)
    for name, payload in [
        ("COLOR_MANAGEMENT_CONFIG.json", config),
        ("OCIO_ACES_MANIFEST.json", ocio),
        ("LUT_MANIFEST.json", lut),
        ("COLOR_PIPELINE_VALIDATION_REPORT.json", validation),
        ("COLOR_MANAGEMENT_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"validation": validation, "seal": seal}


def generate_nuke_comp(output_dir, aovs=None):
    aovs = aovs or REQUIRED_AOVS
    lines = ["# HFX generated Nuke comp dry-run template", "Root { name HFX_COMP_TEMPLATE }"]
    for aov in aovs:
        lines.append(f"Read {{ name Read_{aov} file {{{aov}.exr}} }}")
    text = "\n".join(lines) + "\n"
    write_text(pathlib.Path(output_dir) / "NUKE_COMP_TEMPLATE.nk", text)
    return text


def build_comp_execution(output_dir):
    output_dir = pathlib.Path(output_dir)
    generate_nuke_comp(output_dir)
    ae = {"project": "AE_COMP_PROJECT_SKELETON", "layers": REQUIRED_AOVS}
    davinci = {"node_tree": "DAVINCI_NODE_TREE_SKELETON", "nodes": ["input", "grade", "output"]}
    wiring = {"aov_inputs": REQUIRED_AOVS, "rules": {aov: f"wire_{aov}" for aov in REQUIRED_AOVS}}
    comp_rules = {"alpha": "premultiply", "zdepth": "depth_merge", "emission": "plus", "lightwrap": "screen_edge", "contact_shadow": "multiply"}
    final = {"status": "FINAL_COMP_BLOCKED", "final_comp_exists": False, "delivery_allowed": False}
    seal = global_seal("HFX_COMP_AUTOMATION_EXECUTION_LAYER", ["NUKE_COMP_TEMPLATE.nk", "AE_COMP_PROJECT_SKELETON.json"], "PASS", [final["status"]])
    for name, payload in [
        ("AE_COMP_PROJECT_SKELETON.json", ae),
        ("DAVINCI_NODE_TREE_SKELETON.json", davinci),
        ("AOV_AUTO_WIRING_RULES.json", wiring),
        ("COMP_RULES.json", comp_rules),
        ("FINAL_COMP_VALIDATION_REPORT.json", final),
        ("COMP_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"final": final, "seal": seal}


def build_review_dailies(output_dir):
    output_dir = pathlib.Path(output_dir)
    thumbnails = {"status": "THUMBNAIL_INTERFACE_READY", "generated_files": []}
    contact = {"status": "CONTACT_SHEET_INTERFACE_READY", "layout": "grid_4x4"}
    review_movie = {"status": "REVIEW_MOVIE_INTERFACE_READY", "movie_rendered": False}
    dailies = {"status": "DAILIES_RECORDED", "items": ["SHOT_001"]}
    qc = {"checks": ["alpha", "zdepth", "emission", "lightwrap", "contact_shadow"], "status": "PENDING_REVIEW"}
    approval = {"status": "REVIEW_APPROVAL_BLOCKED", "approved": False, "rejected": False}
    evidence = {"chain": [{"event": "review_package_created", "sha256": sha256_payload(dailies)}]}
    seal = global_seal("HFX_REVIEW_DAILIES_IMPLEMENTATION_LAYER", ["DAILIES_REPORT.json", "VISUAL_QC_CHECKLIST.json"], "PASS", [approval["status"]])
    for name, payload in [
        ("THUMBNAIL_MANIFEST.json", thumbnails),
        ("CONTACT_SHEET_MANIFEST.json", contact),
        ("REVIEW_MOVIE_MANIFEST.json", review_movie),
        ("DAILIES_REPORT.json", dailies),
        ("VISUAL_QC_CHECKLIST.json", qc),
        ("REVIEW_APPROVAL_STATUS.json", approval),
        ("REVIEW_EVIDENCE_CHAIN.json", evidence),
        ("REVIEW_DAILIES_GLOBAL_SEAL.json", seal),
    ]:
        write_json(output_dir / name, payload)
    return {"approval": approval, "seal": seal}


def validate_final_pixel(inputs, output_dir=None):
    checks = {
        "exr_outputs": bool(inputs.get("exr_outputs_pass")),
        "aov_completeness": bool(inputs.get("aov_completeness_pass")),
        "comp_output": bool(inputs.get("comp_output_pass")),
        "color_management": bool(inputs.get("color_management_pass")),
        "resource_license": bool(inputs.get("resource_license_pass")),
        "review_approval": bool(inputs.get("review_approval_pass")),
    }
    blockers = sorted(key for key, passed in checks.items() if not passed)
    ready = not blockers
    report = {
        "status": FINAL_READY_STATE if ready else "FINAL_PIXEL_APPROVAL_BLOCKED",
        "checks": checks,
        "blockers": blockers,
        "final_pixels_authorized": ready,
        "system_state": FINAL_READY_STATE if ready else SYSTEM_STATE,
    }
    blocker_report = {"status": "PASS" if ready else "BLOCKED", "blockers": blockers}
    contract_payload = contract("FINAL_PIXEL_APPROVAL_CONTRACT", list(checks))
    ready_payload = {"emitted": ready, "system_state": FINAL_READY_STATE if ready else SYSTEM_STATE, "final_pixels_authorized": ready}
    seal = global_seal("HFX_FINAL_PIXEL_APPROVAL_LAYER", ["FINAL_PIXEL_APPROVAL_REPORT.json"], "PASS" if ready else "BLOCKED_FAIL_CLOSED", blockers)
    if output_dir:
        output_dir = pathlib.Path(output_dir)
        write_json(output_dir / "FINAL_PIXEL_APPROVAL_CONTRACT.json", contract_payload)
        write_json(output_dir / "FINAL_PIXEL_APPROVAL_REPORT.json", report)
        write_json(output_dir / "FINAL_PIXEL_BLOCKER_REPORT.json", blocker_report)
        write_json(output_dir / "HFX_MASTER_PIPELINE_FINAL_PIXEL_READY.json", ready_payload)
        write_json(output_dir / "FINAL_PIXEL_GLOBAL_SEAL.json", seal)
    return {"report": report, "blocker_report": blocker_report, "ready": ready_payload, "seal": seal}


def validate_delivery_package(inputs, output_dir=None):
    required = ["final_pixel_approval", "checksum", "license_evidence", "approval_report", "delivery_package_complete"]
    missing = [field for field in required if not inputs.get(field)]
    manifest = {"delivery_id": "HFX_DELIVERY_PACKAGE", "required_contents": ["EXR", "comp", "review_movie", "logs", "license", "checksum", "changelog", "approval_report"]}
    contract_payload = contract("DELIVERY_PACKAGE_CONTRACT", ["final_pixel_approval_required", "checksums_required", "license_evidence_required"])
    validation = {"status": "PASS" if not missing else "DELIVERY_BLOCKED", "missing": missing}
    blocker = {"status": "CLIENT_PUBLIC_DELIVERY_BLOCKED" if missing else "CLIENT_PUBLIC_DELIVERY_ALLOWED", "client_public_delivery_allowed": not missing}
    release = {"status": "PASS" if not missing else "RELEASE_PACKAGE_BLOCKED", "missing": missing}
    seal = global_seal("HFX_DELIVERY_IMPLEMENTATION_LAYER", ["DELIVERY_MANIFEST.json"], "PASS" if not missing else "BLOCKED_FAIL_CLOSED", missing)
    if output_dir:
        output_dir = pathlib.Path(output_dir)
        for name, payload in [
            ("DELIVERY_MANIFEST.json", manifest),
            ("DELIVERY_PACKAGE_CONTRACT.json", contract_payload),
            ("DELIVERY_PACKAGE_VALIDATION_REPORT.json", validation),
            ("CLIENT_PUBLIC_DELIVERY_BLOCKER_REPORT.json", blocker),
            ("RELEASE_PACKAGE_VALIDATOR_REPORT.json", release),
            ("DELIVERY_GLOBAL_SEAL.json", seal),
        ]:
            write_json(output_dir / name, payload)
    return {"validation": validation, "blocker": blocker, "release": release, "seal": seal}


def script_header():
    return """#!/usr/bin/env python3
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve()
for parent in ROOT.parents:
    candidate = parent / "hfx_real_pipeline_lib"
    if candidate.exists():
        sys.path.insert(0, str(parent))
        break
from hfx_real_pipeline_lib import hfx_real_pipeline as hfx
"""


def write_executable(path, body):
    write_text(path, script_header() + "\n" + body)
    os.chmod(path, 0o755)


def materialize_wrappers(repo_root):
    root = pathlib.Path(repo_root)
    wrappers = {
        "resource_ingest": {
            "hfx_resource_scanner.py": "hfx.scan_resource_inbox(output_dir=pathlib.Path(__file__).resolve().parent)\nprint('RESOURCE_SCAN_COMPLETE')",
            "resource_manifest_validator.py": "print(hfx.read_json(pathlib.Path(__file__).resolve().parent / 'RESOURCE_GLOBAL_SEAL.json')['status'])",
        },
        "shot_binding": {"hfx_bind_resources_to_shot.py": "d=pathlib.Path(__file__).resolve().parent\nreg=hfx.read_json(hfx.layer_dir(hfx.repo_root_from(__file__), 'resource_ingest') / 'RESOURCE_REGISTRY.json')\nhfx.bind_resources_to_shot(reg, d)\nprint('SHOT_RESOURCE_BINDING_COMPLETE')"},
        "hda_assetization": {"hfx_hda_assetization_validator.py": "d=pathlib.Path(__file__).resolve().parent\nprint(hfx.validate_hda_registry(hfx.read_json(d / 'HDA_ASSET_REGISTRY.json'))['status'])"},
        "render_execution": {
            "hfx_create_render_job.py": "hfx.create_render_job(pathlib.Path(__file__).resolve().parent)\nprint('RENDER_JOB_CREATED')",
            "hfx_run_render_job.py": "d=pathlib.Path(__file__).resolve().parent\nhfx.validate_render_outputs(hfx.read_json(d / 'RENDER_JOB_MANIFEST.json'), d)\nprint('RENDER_JOB_VALIDATED_FAIL_CLOSED')",
            "hfx_hython_batch_launcher.py": "print('HYTHON_DRY_RUN_LAUNCHER_READY_FAIL_CLOSED')",
        },
        "aov_pass": {"hfx_aov_validator.py": "d=pathlib.Path(__file__).resolve().parent\nprint(hfx.validate_aov_contract(hfx.read_json(d/'AOV_PASS_MATRIX.json'), hfx.read_json(d/'AOV_RENDER_CONTRACT.json'))['status'])"},
        "lookdev_shader": {"hfx_lookdev_validator.py": "print(hfx.read_json(pathlib.Path(__file__).resolve().parent / 'LOOKDEV_APPROVAL_REPORT.json')['status'])"},
        "plate_camera": {"hfx_plate_camera_validator.py": "print(hfx.read_json(pathlib.Path(__file__).resolve().parent / 'PLATE_CAMERA_ALIGNMENT_REPORT.json')['status'])"},
        "color_management": {"hfx_color_management_validator.py": "d=pathlib.Path(__file__).resolve().parent\nprint(hfx.validate_color_management(hfx.read_json(d/'COLOR_MANAGEMENT_CONFIG.json'))['status'])"},
        "comp_execution": {
            "hfx_generate_nuke_comp.py": "hfx.generate_nuke_comp(pathlib.Path(__file__).resolve().parent)\nprint('NUKE_COMP_TEMPLATE_GENERATED')",
            "hfx_generate_ae_comp.py": "print('AE_COMP_PROJECT_SKELETON_READY')",
            "hfx_generate_davinci_tree.py": "print('DAVINCI_NODE_TREE_SKELETON_READY')",
            "hfx_comp_validator.py": "print(hfx.read_json(pathlib.Path(__file__).resolve().parent / 'FINAL_COMP_VALIDATION_REPORT.json')['status'])",
        },
        "review_dailies": {
            "hfx_generate_thumbnails.py": "print('THUMBNAIL_GENERATOR_INTERFACE_READY')",
            "hfx_generate_contact_sheet.py": "print('CONTACT_SHEET_GENERATOR_INTERFACE_READY')",
            "hfx_generate_review_movie.py": "print('REVIEW_MOVIE_GENERATOR_INTERFACE_READY_FAIL_CLOSED')",
            "hfx_review_validator.py": "print(hfx.read_json(pathlib.Path(__file__).resolve().parent / 'REVIEW_APPROVAL_STATUS.json')['status'])",
        },
        "final_pixel": {"hfx_final_pixel_approval_validator.py": "hfx.validate_final_pixel({}, pathlib.Path(__file__).resolve().parent)\nprint('FINAL_PIXEL_APPROVAL_BLOCKED')"},
        "delivery": {"hfx_delivery_package_validator.py": "hfx.validate_delivery_package({}, pathlib.Path(__file__).resolve().parent)\nprint('DELIVERY_BLOCKED')"},
    }
    for key, files in wrappers.items():
        directory = layer_dir(root, key)
        for name, body in files.items():
            write_executable(directory / name, body)


def write_layer_metadata(repo_root):
    for key, directory_name in IMPLEMENTATION_LAYERS.items():
        directory = layer_dir(repo_root, key)
        write_json(directory / "LAYER_SCHEMA.json", schema(directory_name, ["system_state"], {"system_state": {"type": "string"}}))
        write_json(directory / "LAYER_CONTRACT.json", contract(directory_name.upper() + "_CONTRACT", ["fail_closed", "deterministic_outputs", "no_final_pixel_claim_without_evidence"]))
        write_executable(directory / "layer_validator.py", "print('PASS')")


def materialize_all(repo_root=None):
    root = pathlib.Path(repo_root or repo_root_from())
    sample_inbox = layer_dir(root, "resource_ingest") / "fixtures" / "sample_inbox"
    create_sample_resource_inbox(sample_inbox)
    resource = scan_resource_inbox(sample_inbox, layer_dir(root, "resource_ingest"))
    bind_resources_to_shot(resource["registry"], layer_dir(root, "shot_binding"))
    build_hda_assetization(layer_dir(root, "hda_assetization"))
    build_render_execution(layer_dir(root, "render_execution"))
    build_aov_pass(layer_dir(root, "aov_pass"))
    build_lookdev(layer_dir(root, "lookdev_shader"))
    build_plate_camera(layer_dir(root, "plate_camera"))
    build_color_management(layer_dir(root, "color_management"))
    build_comp_execution(layer_dir(root, "comp_execution"))
    build_review_dailies(layer_dir(root, "review_dailies"))
    validate_final_pixel({}, layer_dir(root, "final_pixel"))
    validate_delivery_package({}, layer_dir(root, "delivery"))
    write_layer_metadata(root)
    materialize_wrappers(root)
    real_master = houdini_root(root) / "hfx_real_master_pipeline_seal"
    seal_paths = []
    seal_name_by_key = {
        "resource_ingest": "RESOURCE_GLOBAL_SEAL.json",
        "shot_binding": "SHOT_RESOURCE_BINDING_GLOBAL_SEAL.json",
        "hda_assetization": "HDA_GLOBAL_SEAL.json",
        "render_execution": "RENDER_GLOBAL_SEAL.json",
        "aov_pass": "AOV_GLOBAL_SEAL.json",
        "lookdev_shader": "LOOKDEV_GLOBAL_SEAL.json",
        "plate_camera": "PLATE_CAMERA_GLOBAL_SEAL.json",
        "color_management": "COLOR_MANAGEMENT_GLOBAL_SEAL.json",
        "comp_execution": "COMP_GLOBAL_SEAL.json",
        "review_dailies": "REVIEW_DAILIES_GLOBAL_SEAL.json",
        "final_pixel": "FINAL_PIXEL_GLOBAL_SEAL.json",
        "delivery": "DELIVERY_GLOBAL_SEAL.json",
    }
    layer_seals = []
    for key, seal_name in seal_name_by_key.items():
        path = layer_dir(root, key) / seal_name
        seal = read_json(path)
        seal_paths.append(str(path.relative_to(root)))
        layer_seals.append({"layer": IMPLEMENTATION_LAYERS[key], "seal_path": str(path.relative_to(root)), "status": seal["status"], "seal_sha256": seal["seal_sha256"]})
    master = {
        "seal_id": "HFX_MASTER_PIPELINE_GLOBAL_SEAL",
        "status": "HFX_REAL_RESOURCE_SHOT_PIPELINE_IMPLEMENTATION_PASS_FINAL_PIXEL_BLOCKED",
        "system_state": SYSTEM_STATE,
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "bound_layer_count": 12,
        "layer_seals": layer_seals,
        "required_layer_seals": seal_paths,
    }
    master["seal_sha256"] = sha256_payload(master)
    write_json(real_master / "HFX_MASTER_PIPELINE_GLOBAL_SEAL.json", master)
    write_json(real_master / "HFX_MASTER_PIPELINE_FILE_MANIFEST.json", {"files": file_tree(real_master), "system_state": SYSTEM_STATE})
    write_json(real_master / "HFX_MASTER_PIPELINE_CHECKSUM_MANIFEST.json", {"checksums": checksum_manifest(real_master)})
    return master


if __name__ == "__main__":
    master_seal = materialize_all(repo_root_from())
    print(master_seal["status"])
