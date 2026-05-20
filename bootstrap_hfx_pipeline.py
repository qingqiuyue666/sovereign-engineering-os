#!/usr/bin/env python3
"""
Bootstrap the HFX Houdini pipeline contract skeleton.

This script is the only authored artifact required for the scaffold. When run
from the repository root, it creates assets/houdini/* layer directories and
populates them with JSON schemas, Markdown contracts, and Python validator
templates. It intentionally does not create pixels, shaders, Houdini scenes,
EXRs, or client deliverables.
"""

import json
import os
import pathlib


SYSTEM_STATE = "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS"
MAXIMUM_ALLOWED_STATE = SYSTEM_STATE
PIPELINE_ROOT = pathlib.Path(
    os.environ.get("HFX_PIPELINE_ROOT", pathlib.Path(__file__).resolve().parent)
).resolve()
HOUDINI_ROOT = PIPELINE_ROOT / "assets" / "houdini"
OVERWRITE = os.environ.get("HFX_BOOTSTRAP_OVERWRITE", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "force",
}


def object_schema(title, required=None, properties=None, description=""):
    required = required or []
    properties = properties or {}
    base = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:hfx:houdini:pipeline:schema:" + slugify(title),
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }
    if description:
        base["description"] = description
    return base


def array_of_strings(description):
    return {
        "type": "array",
        "description": description,
        "items": {"type": "string"},
        "default": [],
    }


def enum(values, description=""):
    data = {"type": "string", "enum": values}
    if description:
        data["description"] = description
    return data


def slugify(value):
    result = []
    previous_was_separator = False
    for char in str(value).lower():
        if char.isalnum():
            result.append(char)
            previous_was_separator = False
        elif not previous_was_separator:
            result.append("_")
            previous_was_separator = True
    return "".join(result).strip("_")


def contract(title, purpose, inputs=None, outputs=None, gates=None, fail_closed=True):
    inputs = inputs or []
    outputs = outputs or []
    gates = gates or []
    lines = [
        "# " + title,
        "",
        "## Purpose",
        purpose,
        "",
        "## Contract Boundary",
        "- This layer defines interfaces, schemas, reports, and validation gates only.",
        "- This layer does not create final pixels, production renders, shaders, plates, or client deliverables.",
        "- Maximum legal state: `" + MAXIMUM_ALLOWED_STATE + "`.",
        "",
        "## Required Inputs",
    ]
    lines.extend("- " + item for item in (inputs or ["None."]))
    lines.extend(["", "## Required Outputs"])
    lines.extend("- " + item for item in (outputs or ["None."]))
    lines.extend(["", "## Validation Gates"])
    lines.extend("- " + item for item in (gates or ["Schema exists and validator template exists."]))
    lines.extend(["", "## Failure Policy"])
    if fail_closed:
        lines.append("All unresolved, missing, ambiguous, or unimplemented checks fail closed.")
    else:
        lines.append("This layer records scaffold readiness only and cannot authorize final pixels.")
    lines.append("")
    return "\n".join(lines)


def validator_template(layer_name, validator_name, purpose, fail_closed=True, final_pixel_gate=False):
    default_status = "BLOCKED" if fail_closed else "SCAFFOLD_ONLY"
    lines = [
        '"""',
        validator_name.replace("_", " ").title(),
        "",
        "Generated validator template for " + layer_name + ".",
        "Purpose: " + purpose,
        '"""',
        "",
        "SYSTEM_STATE = " + repr(SYSTEM_STATE),
        "LAYER_NAME = " + repr(layer_name),
        "VALIDATOR_NAME = " + repr(validator_name),
        "",
        "",
        "def validate(payload=None, context=None):",
        "    \"\"\"Return a fail-closed validation envelope.",
        "",
        "    Implement production validation here. Until implementation is complete,",
        "    this scaffold does not certify final pixels or client deliverables.",
        "    \"\"\"",
        "    payload = payload or {}",
        "    context = context or {}",
    ]
    if final_pixel_gate:
        lines.extend(
            [
                "    exr_paths = payload.get(\"exr_paths\") or []",
                "    verified_real_exrs = bool(payload.get(\"verified_real_exrs\"))",
                "    if not exr_paths or not verified_real_exrs:",
                "        return {",
                "            \"ok\": False,",
                "            \"status\": \"FINAL_PIXEL_CLAIM_BLOCKED\",",
                "            \"system_state\": SYSTEM_STATE,",
                "            \"reason\": \"Fail-closed: no verified real EXR evidence was supplied.\",",
                "            \"layer\": LAYER_NAME,",
                "            \"validator\": VALIDATOR_NAME,",
                "        }",
                "    return {",
                "        \"ok\": False,",
                "        \"status\": \"FINAL_PIXEL_CLAIM_BLOCKED\",",
                "        \"system_state\": SYSTEM_STATE,",
                "        \"reason\": \"Fail-closed scaffold: EXR metadata alone cannot authorize final pixels.\",",
                "        \"layer\": LAYER_NAME,",
                "        \"validator\": VALIDATOR_NAME,",
                "    }",
            ]
        )
    else:
        lines.extend(
            [
                "    return {",
                "        \"ok\": False,",
                "        \"status\": " + repr(default_status) + ",",
                "        \"system_state\": SYSTEM_STATE,",
                "        \"reason\": \"Validator scaffold has not been implemented for production approval.\",",
                "        \"layer\": LAYER_NAME,",
                "        \"validator\": VALIDATOR_NAME,",
                "        \"payload_keys\": sorted(payload.keys()),",
                "        \"context_keys\": sorted(context.keys()),",
                "    }",
            ]
        )
    lines.extend(
        [
            "",
            "",
            "if __name__ == \"__main__\":",
            "    print(validate())",
            "",
        ]
    )
    return "\n".join(lines)


def schema_asset_publish_manifest():
    return object_schema(
        "HFX Asset Publish Manifest",
        required=[
            "asset_id",
            "asset_name",
            "asset_type",
            "department",
            "publish_version",
            "houdini_version",
            "hda_path",
            "interface_contract",
            "status",
        ],
        properties={
            "asset_id": {"type": "string", "pattern": "^hfx_[a-z0-9_]+$"},
            "asset_name": {"type": "string"},
            "asset_type": enum(["fx", "crowd", "environment", "prop", "vehicle", "creature", "utility"]),
            "department": enum(["hfx", "lookdev", "lighting", "pipeline", "layout"]),
            "publish_version": {"type": "string", "pattern": "^v[0-9]{3,}$"},
            "houdini_version": {"type": "string"},
            "hda_path": {"type": "string"},
            "source_scene_path": {"type": "string", "default": ""},
            "interface_contract": {"type": "string"},
            "dependencies": array_of_strings("Upstream contracts or package ids required by this asset."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
            "notes": {"type": "string", "default": ""},
        },
    )


def schema_parameter_interface_contract():
    return object_schema(
        "HFX Parameter Interface Contract",
        required=["asset_id", "parameter_groups", "locked_parameters", "public_controls", "status"],
        properties={
            "asset_id": {"type": "string"},
            "parameter_groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "parameters"],
                    "properties": {
                        "name": {"type": "string"},
                        "parameters": array_of_strings("Published parameter names."),
                    },
                },
                "default": [],
            },
            "locked_parameters": array_of_strings("Internal controls that cannot be modified downstream."),
            "public_controls": array_of_strings("Controls exposed to artists and automation."),
            "versioned_defaults": {"type": "object", "default": {}},
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_hda_readiness_report():
    return object_schema(
        "HFX HDA Readiness Report",
        required=["asset_id", "hda_path", "checks", "ready_for_publish", "status"],
        properties={
            "asset_id": {"type": "string"},
            "hda_path": {"type": "string"},
            "checks": {
                "type": "object",
                "additionalProperties": {"type": "boolean"},
                "default": {},
            },
            "ready_for_publish": {"type": "boolean", "default": False},
            "blocking_findings": array_of_strings("Reasons the HDA cannot be published."),
            "status": enum(["blocked", "ready_for_validation", "sealed"]),
        },
    )


def schema_twelve_asset_aov_contract():
    return object_schema(
        "HFX Twelve Asset AOV Contract",
        required=["show_id", "asset_count", "assets", "required_aovs", "status"],
        properties={
            "show_id": {"type": "string"},
            "asset_count": {"type": "integer", "const": 12},
            "assets": {
                "type": "array",
                "minItems": 12,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["asset_id", "aov_profile"],
                    "properties": {
                        "asset_id": {"type": "string"},
                        "aov_profile": {"type": "string"},
                        "required_overrides": array_of_strings("Asset-specific AOV overrides."),
                    },
                },
            },
            "required_aovs": array_of_strings("AOV names required for every asset."),
            "optional_aovs": array_of_strings("AOV names that may be emitted when approved."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_global_aov_matrix():
    return object_schema(
        "HFX Global AOV Matrix",
        required=["matrix_version", "aovs", "renderer_targets", "status"],
        properties={
            "matrix_version": {"type": "string", "pattern": "^v[0-9]{3,}$"},
            "aovs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "data_type", "required"],
                    "properties": {
                        "name": {"type": "string"},
                        "data_type": enum(["float", "vector", "color", "integer", "string"]),
                        "required": {"type": "boolean"},
                        "description": {"type": "string", "default": ""},
                    },
                },
                "default": [],
            },
            "renderer_targets": array_of_strings("Renderer integrations that must honor this matrix."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_desktop_inbox_scan():
    return object_schema(
        "HFX Desktop Inbox Scan",
        required=["scan_roots", "allowed_extensions", "quarantine_root", "status"],
        properties={
            "scan_roots": array_of_strings("Inbox paths searched for incoming production resources."),
            "allowed_extensions": array_of_strings("Extensions accepted by the intake gate."),
            "quarantine_root": {"type": "string"},
            "dedupe_strategy": enum(["sha256", "name_version", "manual_review"]),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_resource_manifest():
    return object_schema(
        "HFX Resource Manifest",
        required=["resource_id", "resource_type", "source_path", "license_id", "usage_scope", "status"],
        properties={
            "resource_id": {"type": "string"},
            "resource_type": enum(["texture", "model", "hdri", "plate", "reference", "cache", "document"]),
            "source_path": {"type": "string"},
            "checksum": {"type": "string", "default": ""},
            "license_id": {"type": "string"},
            "usage_scope": array_of_strings("Approved show, sequence, shot, or internal-use scopes."),
            "metadata": {"type": "object", "default": {}},
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_license_record():
    return object_schema(
        "HFX License Record",
        required=["license_id", "source", "permitted_uses", "expires", "status"],
        properties={
            "license_id": {"type": "string"},
            "source": {"type": "string"},
            "permitted_uses": array_of_strings("Allowed production and distribution uses."),
            "restricted_uses": array_of_strings("Uses that must remain blocked."),
            "expires": {"type": "string", "description": "ISO date or NEVER."},
            "status": enum(["draft", "valid", "expired", "blocked"]),
        },
    )


def schema_shader_slot_registry():
    return object_schema(
        "HFX Shader Slot Registry",
        required=["registry_version", "slots", "status"],
        properties={
            "registry_version": {"type": "string", "pattern": "^v[0-9]{3,}$"},
            "slots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["slot_name", "semantic", "required"],
                    "properties": {
                        "slot_name": {"type": "string"},
                        "semantic": {"type": "string"},
                        "required": {"type": "boolean"},
                        "allowed_value_types": array_of_strings("Accepted value or node types."),
                    },
                },
                "default": [],
            },
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_material_binding():
    return object_schema(
        "HFX Material Binding",
        required=["asset_id", "bindings", "status"],
        properties={
            "asset_id": {"type": "string"},
            "bindings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["geometry_path", "material_id", "shader_slot_profile"],
                    "properties": {
                        "geometry_path": {"type": "string"},
                        "material_id": {"type": "string"},
                        "shader_slot_profile": {"type": "string"},
                    },
                },
                "default": [],
            },
            "unbound_policy": enum(["block", "warn_only"]),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_plate_camera_lens_hdri_binding():
    return object_schema(
        "HFX Plate Camera Lens HDRI Binding",
        required=["shot_id", "plate", "camera", "lens", "hdri", "status"],
        properties={
            "shot_id": {"type": "string"},
            "plate": {
                "type": "object",
                "additionalProperties": False,
                "required": ["plate_id", "path", "frame_range", "colorspace"],
                "properties": {
                    "plate_id": {"type": "string"},
                    "path": {"type": "string"},
                    "frame_range": array_of_strings("Start and end frame labels."),
                    "colorspace": {"type": "string"},
                },
            },
            "camera": {
                "type": "object",
                "additionalProperties": False,
                "required": ["camera_id", "path", "unit_scale"],
                "properties": {
                    "camera_id": {"type": "string"},
                    "path": {"type": "string"},
                    "unit_scale": {"type": "number"},
                },
            },
            "lens": {
                "type": "object",
                "additionalProperties": False,
                "required": ["lens_id", "distortion_model"],
                "properties": {
                    "lens_id": {"type": "string"},
                    "distortion_model": {"type": "string"},
                    "metadata_path": {"type": "string", "default": ""},
                },
            },
            "hdri": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hdri_id", "path", "exposure_reference"],
                "properties": {
                    "hdri_id": {"type": "string"},
                    "path": {"type": "string"},
                    "exposure_reference": {"type": "string"},
                },
            },
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_tracking_validation_report():
    return object_schema(
        "HFX Tracking Validation Report",
        required=["shot_id", "track_source", "checks", "tracking_approved", "status"],
        properties={
            "shot_id": {"type": "string"},
            "track_source": {"type": "string"},
            "checks": {"type": "object", "additionalProperties": {"type": "boolean"}, "default": {}},
            "tracking_approved": {"type": "boolean", "default": False},
            "blocking_findings": array_of_strings("Reasons tracking cannot be approved."),
            "status": enum(["blocked", "ready_for_validation", "sealed"]),
        },
    )


def schema_render_job():
    return object_schema(
        "HFX Render Job",
        required=["job_id", "show_id", "shot_id", "renderer", "frame_range", "aov_contract", "status"],
        properties={
            "job_id": {"type": "string"},
            "show_id": {"type": "string"},
            "shot_id": {"type": "string"},
            "renderer": enum(["karma", "arnold", "renderman", "redshift", "other"]),
            "frame_range": array_of_strings("Start, end, and optional step."),
            "aov_contract": {"type": "string"},
            "farm_pool": {"type": "string", "default": ""},
            "priority": {"type": "integer", "minimum": 0, "maximum": 100, "default": 50},
            "status": enum(["draft", "ready_for_validation", "blocked", "submitted", "sealed"]),
        },
    )


def schema_render_validation():
    return object_schema(
        "HFX Render Validation",
        required=["job_id", "checks", "approved_for_submission", "status"],
        properties={
            "job_id": {"type": "string"},
            "checks": {"type": "object", "additionalProperties": {"type": "boolean"}, "default": {}},
            "approved_for_submission": {"type": "boolean", "default": False},
            "blocked_frames": array_of_strings("Frames that cannot be submitted or accepted."),
            "status": enum(["blocked", "ready_for_validation", "sealed"]),
        },
    )


def schema_failed_frame_retry():
    return object_schema(
        "HFX Failed Frame Retry",
        required=["job_id", "failed_frames", "retry_policy", "status"],
        properties={
            "job_id": {"type": "string"},
            "failed_frames": array_of_strings("Frame numbers or frame ranges to retry."),
            "retry_policy": enum(["single_retry", "retry_with_cleanup", "manual_review"]),
            "max_attempts": {"type": "integer", "minimum": 0, "default": 1},
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_comp_instruction(name, host):
    return object_schema(
        "HFX " + name + " Instruction",
        required=["instruction_id", "host_application", "shot_id", "inputs", "outputs", "status"],
        properties={
            "instruction_id": {"type": "string"},
            "host_application": {"type": "string", "const": host},
            "shot_id": {"type": "string"},
            "inputs": array_of_strings("Input manifests, plates, or render products."),
            "outputs": array_of_strings("Expected script, project, or review artifacts."),
            "operations": array_of_strings("Ordered high-level operations for the host app."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_color_pipeline():
    return object_schema(
        "HFX Color Pipeline",
        required=["show_id", "working_space", "display_transform", "ocio_config", "status"],
        properties={
            "show_id": {"type": "string"},
            "working_space": {"type": "string", "default": "ACEScg"},
            "display_transform": {"type": "string", "default": "sRGB"},
            "ocio_config": {"type": "string"},
            "lut_registry": array_of_strings("Approved LUT ids or paths."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_ocio_placeholder():
    return object_schema(
        "HFX ACES OCIO Placeholder",
        required=["config_id", "aces_version", "ocio_version", "placeholder_only", "status"],
        properties={
            "config_id": {"type": "string"},
            "aces_version": {"type": "string"},
            "ocio_version": {"type": "string"},
            "placeholder_only": {"type": "boolean", "const": True},
            "blocked_until_real_config": {"type": "boolean", "const": True},
            "status": enum(["blocked", "placeholder"]),
        },
    )


def schema_review_package():
    return object_schema(
        "HFX Review Package",
        required=["review_id", "shot_id", "media_items", "review_targets", "status"],
        properties={
            "review_id": {"type": "string"},
            "shot_id": {"type": "string"},
            "media_items": array_of_strings("Reviewable media paths or ids."),
            "review_targets": array_of_strings("Systems or stakeholders receiving this package."),
            "notes": {"type": "string", "default": ""},
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_contact_sheet():
    return object_schema(
        "HFX Contact Sheet",
        required=["contact_sheet_id", "source_media", "layout", "status"],
        properties={
            "contact_sheet_id": {"type": "string"},
            "source_media": array_of_strings("Media items to include in the contact sheet."),
            "layout": enum(["grid_3x4", "grid_4x4", "sequence_strip", "custom"]),
            "burnins": array_of_strings("Approved metadata burn-ins."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_dailies_report():
    return object_schema(
        "HFX Dailies Report",
        required=["report_id", "session_id", "items", "decisions", "status"],
        properties={
            "report_id": {"type": "string"},
            "session_id": {"type": "string"},
            "items": array_of_strings("Review package ids covered in the dailies session."),
            "decisions": array_of_strings("Approved notes, holds, and required follow-ups."),
            "status": enum(["draft", "ready_for_validation", "blocked", "sealed"]),
        },
    )


def schema_final_pixel_claim():
    return object_schema(
        "HFX Final Pixel Claim",
        required=["claim_id", "shot_id", "exr_paths", "verified_real_exrs", "claim_status"],
        properties={
            "claim_id": {"type": "string"},
            "shot_id": {"type": "string"},
            "exr_paths": array_of_strings("Real EXR paths offered as evidence."),
            "verified_real_exrs": {
                "type": "boolean",
                "const": False,
                "description": "Bootstrap state cannot verify real EXRs.",
            },
            "claim_status": enum(["blocked"]),
            "block_reason": {
                "type": "string",
                "default": "Fail-closed: final pixels cannot be claimed by this scaffold.",
            },
        },
        description="Fail-closed schema for final pixel claims. In this scaffold, all claims remain blocked.",
    )


def schema_blocked_claim_registry():
    return object_schema(
        "HFX Blocked Final Pixel Claim Registry",
        required=["registry_id", "claims", "all_claims_blocked", "system_state"],
        properties={
            "registry_id": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["claim_id", "shot_id", "reason"],
                    "properties": {
                        "claim_id": {"type": "string"},
                        "shot_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
                "default": [],
            },
            "all_claims_blocked": {"type": "boolean", "const": True},
            "system_state": {"type": "string", "const": SYSTEM_STATE},
        },
    )


def schema_delivery_manifest():
    return object_schema(
        "HFX Delivery Manifest",
        required=["delivery_id", "client_id", "items", "final_pixel_claim_status", "status"],
        properties={
            "delivery_id": {"type": "string"},
            "client_id": {"type": "string"},
            "items": array_of_strings("Delivery item ids or paths."),
            "final_pixel_claim_status": enum(["blocked"]),
            "color_pipeline": {"type": "string", "default": ""},
            "status": enum(["draft", "blocked"]),
        },
    )


def schema_client_delivery_blocker():
    return object_schema(
        "HFX Client Delivery Blocker",
        required=["blocker_id", "delivery_id", "blocked", "reasons", "system_state"],
        properties={
            "blocker_id": {"type": "string"},
            "delivery_id": {"type": "string"},
            "blocked": {"type": "boolean", "const": True},
            "reasons": array_of_strings("Reasons client delivery must not proceed."),
            "system_state": {"type": "string", "const": SYSTEM_STATE},
        },
    )


def schema_master_pipeline_seal():
    return object_schema(
        "HFX Master Pipeline Global Seal",
        required=["seal_id", "system_state", "maximum_allowed_state", "layers", "final_pixel_gate"],
        properties={
            "seal_id": {"type": "string"},
            "system_state": {"type": "string", "const": SYSTEM_STATE},
            "maximum_allowed_state": {"type": "string", "const": MAXIMUM_ALLOWED_STATE},
            "layers": {
                "type": "array",
                "minItems": 12,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["index", "name", "title", "status", "required_files", "final_pixels_authorized"],
                    "properties": {
                        "index": {"type": "integer"},
                        "name": {"type": "string"},
                        "title": {"type": "string"},
                        "status": enum(["CONTRACT_SCAFFOLDED", "BLOCKED_NO_FINAL_PIXELS"]),
                        "required_files": array_of_strings("Files expected inside this layer."),
                        "final_pixels_authorized": {"type": "boolean", "const": False},
                    },
                },
            },
            "pipeline_root": {"type": "string"},
            "houdini_root": {"type": "string"},
            "final_pixel_gate": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim_policy", "delivery_policy", "real_exr_required", "current_state", "reason"],
                "properties": {
                    "claim_policy": enum(["fail_closed"]),
                    "delivery_policy": enum(["blocked"]),
                    "real_exr_required": {"type": "boolean", "const": True},
                    "current_state": {"type": "string", "const": SYSTEM_STATE},
                    "reason": {"type": "string"},
                },
            },
            "delivery_policy": {
                "type": "object",
                "additionalProperties": False,
                "required": ["client_delivery_allowed", "reason"],
                "properties": {
                    "client_delivery_allowed": {"type": "boolean", "const": False},
                    "reason": {"type": "string"},
                },
            },
            "output": {"type": "string", "const": SYSTEM_STATE},
        },
    )


LAYER_SPECS = [
    {
        "index": 1,
        "name": "hfx_assetization_layer",
        "title": "HFX Assetization Layer",
        "purpose": "Define publish manifests, public HDA interfaces, readiness reports, and local asset seals.",
        "files": [
            ("asset_publish_manifest.schema.json", schema_asset_publish_manifest),
            ("parameter_interface_contract.schema.json", schema_parameter_interface_contract),
            ("hda_readiness_report.schema.json", schema_hda_readiness_report),
            (
                "GLOBAL_SEAL.json",
                lambda: build_layer_global_seal(layer_by_name("hfx_assetization_layer")),
            ),
            (
                "asset_publish_manifest.contract.md",
                lambda: contract(
                    "Asset Publish Manifest Contract",
                    "Describe the minimum data required before an HFX asset can enter the publish validation queue.",
                    ["Asset id, HDA path, publish version, dependency list."],
                    ["Validated manifest envelope for downstream gates."],
                    ["Asset id pattern is stable.", "Publish version is explicit.", "Dependencies are declared."],
                ),
            ),
            (
                "parameter_interface_contract.contract.md",
                lambda: contract(
                    "Parameter Interface Contract",
                    "Define public controls, locked internals, parameter groups, and versioned defaults for HDAs.",
                    ["HDA parameter inventory.", "Artist-facing control requirements."],
                    ["Public interface registry for automation and review."],
                    ["Public controls are named.", "Locked parameters are declared.", "Defaults are versioned."],
                ),
            ),
            (
                "hda_readiness_report.contract.md",
                lambda: contract(
                    "HDA Readiness Report Contract",
                    "Record whether an HDA satisfies structural readiness checks before any production publish.",
                    ["HDA path.", "Readiness checklist."],
                    ["Blocked or ready-for-validation report."],
                    ["Missing checks block publish.", "Unresolved findings block seal."],
                ),
            ),
            (
                "GLOBAL_SEAL.contract.md",
                lambda: contract(
                    "Assetization Global Seal Contract",
                    "Aggregate the assetization contracts into a single local seal without authorizing final pixels.",
                    ["Asset manifest schema.", "Parameter interface schema.", "HDA readiness schema."],
                    ["Layer-level scaffold seal."],
                    ["Seal remains non-final-pixel.", "All missing child contracts block production seal."],
                ),
            ),
            (
                "asset_publish_manifest_validator.py",
                lambda: validator_template(
                    "hfx_assetization_layer",
                    "asset_publish_manifest_validator",
                    "Validate asset publish manifest structure.",
                ),
            ),
            (
                "parameter_interface_validator.py",
                lambda: validator_template(
                    "hfx_assetization_layer",
                    "parameter_interface_validator",
                    "Validate HDA public parameter interface declarations.",
                ),
            ),
            (
                "hda_readiness_validator.py",
                lambda: validator_template(
                    "hfx_assetization_layer",
                    "hda_readiness_validator",
                    "Validate HDA readiness report gates.",
                ),
            ),
            (
                "global_seal_validator.py",
                lambda: validator_template(
                    "hfx_assetization_layer",
                    "global_seal_validator",
                    "Validate the assetization layer seal envelope.",
                ),
            ),
        ],
    },
    {
        "index": 2,
        "name": "hfx_aov_pass_contract_layer",
        "title": "HFX AOV Pass Contract Layer",
        "purpose": "Define AOV requirements for twelve HFX assets and a global pass matrix.",
        "files": [
            ("twelve_asset_aov_contract.schema.json", schema_twelve_asset_aov_contract),
            ("global_aov_matrix.schema.json", schema_global_aov_matrix),
            (
                "twelve_asset_aov_contract.contract.md",
                lambda: contract(
                    "Twelve Asset AOV Contract",
                    "Lock the required AOV profile for exactly twelve assets before render automation can proceed.",
                    ["Twelve asset ids.", "Required and optional AOV names."],
                    ["Per-asset AOV contract."],
                    ["Asset count must be exactly twelve.", "Required AOVs must be explicit."],
                ),
            ),
            (
                "global_aov_matrix.contract.md",
                lambda: contract(
                    "Global AOV Matrix Contract",
                    "Centralize renderer-agnostic AOV names, data types, and required flags.",
                    ["Renderer targets.", "AOV semantic definitions."],
                    ["Global matrix consumed by render and comp layers."],
                    ["Unsupported data types block validation.", "Missing required AOVs block render submission."],
                ),
            ),
            (
                "twelve_asset_aov_validator.py",
                lambda: validator_template(
                    "hfx_aov_pass_contract_layer",
                    "twelve_asset_aov_validator",
                    "Validate exactly twelve asset AOV profiles.",
                ),
            ),
            (
                "global_aov_matrix_validator.py",
                lambda: validator_template(
                    "hfx_aov_pass_contract_layer",
                    "global_aov_matrix_validator",
                    "Validate the global AOV matrix contract.",
                ),
            ),
        ],
    },
    {
        "index": 3,
        "name": "hfx_resource_library_layer",
        "title": "HFX Resource Library Layer",
        "purpose": "Define resource intake, manifesting, license validation, quarantine, and scan behavior.",
        "files": [
            ("desktop_inbox_scan.schema.json", schema_desktop_inbox_scan),
            ("resource_manifest.schema.json", schema_resource_manifest),
            ("license_record.schema.json", schema_license_record),
            (
                "desktop_inbox_scanner_logic.contract.md",
                lambda: contract(
                    "Desktop Inbox Scanner Logic Contract",
                    "Describe scanner roots, extension filters, dedupe strategy, and quarantine policy for resource intake.",
                    ["Desktop inbox paths.", "Allowed extension list."],
                    ["Scanned resource candidate envelope."],
                    ["Unknown extensions quarantine.", "Duplicates require deterministic handling."],
                ),
            ),
            (
                "resource_manifest.contract.md",
                lambda: contract(
                    "Resource Manifest Contract",
                    "Capture resource identity, type, source, checksum, license, scope, and metadata.",
                    ["Incoming resource candidate.", "License id."],
                    ["Resource manifest pending license approval."],
                    ["Missing license blocks use.", "Missing source path blocks publish."],
                ),
            ),
            (
                "license_validator.contract.md",
                lambda: contract(
                    "License Validator Contract",
                    "Gate resource use against permitted uses, restricted uses, expiry, and production scope.",
                    ["License record.", "Resource manifest usage scope."],
                    ["Valid, expired, or blocked license status."],
                    ["Expired or ambiguous license blocks downstream use."],
                ),
            ),
            (
                "desktop_inbox_scanner.py",
                lambda: validator_template(
                    "hfx_resource_library_layer",
                    "desktop_inbox_scanner",
                    "Template for scanning desktop inbox locations into resource candidates.",
                ),
            ),
            (
                "resource_manifest_validator.py",
                lambda: validator_template(
                    "hfx_resource_library_layer",
                    "resource_manifest_validator",
                    "Validate resource manifest structure and required fields.",
                ),
            ),
            (
                "license_validator.py",
                lambda: validator_template(
                    "hfx_resource_library_layer",
                    "license_validator",
                    "Validate resource license status and permitted usage.",
                ),
            ),
        ],
    },
    {
        "index": 4,
        "name": "hfx_lookdev_shader_contract_layer",
        "title": "HFX Lookdev Shader Contract Layer",
        "purpose": "Define shader slots, material bindings, and unbound material policy.",
        "files": [
            ("shader_slot_registry.schema.json", schema_shader_slot_registry),
            ("material_binding.schema.json", schema_material_binding),
            (
                "shader_slot_registry.contract.md",
                lambda: contract(
                    "Shader Slot Registry Contract",
                    "Define named shader slots, semantics, required flags, and allowed value types.",
                    ["Renderer and show lookdev requirements."],
                    ["Versioned shader slot registry."],
                    ["Missing required slots block material validation."],
                ),
            ),
            (
                "material_binding.contract.md",
                lambda: contract(
                    "Material Binding Contract",
                    "Map geometry paths to material ids and shader slot profiles.",
                    ["Asset geometry paths.", "Shader slot registry."],
                    ["Material binding manifest."],
                    ["Unbound geometry follows explicit block or warning policy."],
                ),
            ),
            (
                "shader_slot_registry_validator.py",
                lambda: validator_template(
                    "hfx_lookdev_shader_contract_layer",
                    "shader_slot_registry_validator",
                    "Validate shader slot registry structure.",
                ),
            ),
            (
                "material_binding_validator.py",
                lambda: validator_template(
                    "hfx_lookdev_shader_contract_layer",
                    "material_binding_validator",
                    "Validate material binding declarations.",
                ),
            ),
        ],
    },
    {
        "index": 5,
        "name": "hfx_plate_camera_integration_layer",
        "title": "HFX Plate Camera Integration Layer",
        "purpose": "Define plate, camera, lens, HDRI, and tracking report binding contracts.",
        "files": [
            ("plate_camera_lens_hdri_binding.schema.json", schema_plate_camera_lens_hdri_binding),
            ("tracking_validation_report.schema.json", schema_tracking_validation_report),
            (
                "plate_camera_lens_hdri_binding.contract.md",
                lambda: contract(
                    "Plate Camera Lens HDRI Binding Contract",
                    "Bind plates, cameras, lens metadata, and HDRIs into a single shot integration envelope.",
                    ["Shot id.", "Plate path.", "Camera path.", "Lens metadata.", "HDRI path."],
                    ["Shot integration binding manifest."],
                    ["Missing camera, lens, plate, or HDRI metadata blocks integration approval."],
                ),
            ),
            (
                "tracking_validation_report.contract.md",
                lambda: contract(
                    "Tracking Validation Report Contract",
                    "Record tracking source, validation checks, approval flag, and blocking findings.",
                    ["Tracking export.", "Shot integration binding."],
                    ["Blocked or ready-for-validation tracking report."],
                    ["Unapproved tracking blocks render automation."],
                ),
            ),
            (
                "plate_camera_lens_hdri_binding_validator.py",
                lambda: validator_template(
                    "hfx_plate_camera_integration_layer",
                    "plate_camera_lens_hdri_binding_validator",
                    "Validate shot plate, camera, lens, and HDRI bindings.",
                ),
            ),
            (
                "tracking_validation_report_validator.py",
                lambda: validator_template(
                    "hfx_plate_camera_integration_layer",
                    "tracking_validation_report_validator",
                    "Validate tracking approval report structure.",
                ),
            ),
        ],
    },
    {
        "index": 6,
        "name": "hfx_render_automation_layer",
        "title": "HFX Render Automation Layer",
        "purpose": "Define render jobs, pre-submit validation, and failed frame retry behavior.",
        "files": [
            ("render_job.schema.json", schema_render_job),
            ("render_validation.schema.json", schema_render_validation),
            ("failed_frame_retry.schema.json", schema_failed_frame_retry),
            (
                "render_job.contract.md",
                lambda: contract(
                    "Render Job Contract",
                    "Declare renderer, shot, frame range, AOV contract, farm pool, and priority for render automation.",
                    ["Shot id.", "Frame range.", "AOV contract."],
                    ["Render job manifest."],
                    ["Missing AOV contract blocks submission.", "Unknown renderer blocks submission."],
                ),
            ),
            (
                "render_validation.contract.md",
                lambda: contract(
                    "Render Validation Contract",
                    "Collect pre-submit render checks and frame blockers.",
                    ["Render job manifest.", "Upstream AOV and integration contracts."],
                    ["Approved or blocked submission report."],
                    ["Failed validation blocks farm submission."],
                ),
            ),
            (
                "failed_frame_retry.contract.md",
                lambda: contract(
                    "Failed Frame Retry Contract",
                    "Define failed frame retry policy, frame list, and maximum attempts.",
                    ["Failed frame identifiers.", "Render job id."],
                    ["Retry request manifest."],
                    ["Unknown failure mode requires manual review."],
                ),
            ),
            (
                "render_job_validator.py",
                lambda: validator_template(
                    "hfx_render_automation_layer",
                    "render_job_validator",
                    "Validate render job manifests.",
                ),
            ),
            (
                "render_validation_validator.py",
                lambda: validator_template(
                    "hfx_render_automation_layer",
                    "render_validation_validator",
                    "Validate render pre-submit gates.",
                ),
            ),
            (
                "failed_frame_retry_validator.py",
                lambda: validator_template(
                    "hfx_render_automation_layer",
                    "failed_frame_retry_validator",
                    "Validate failed frame retry requests.",
                ),
            ),
        ],
    },
    {
        "index": 7,
        "name": "hfx_comp_automation_layer",
        "title": "HFX Comp Automation Layer",
        "purpose": "Define instruction-generator schemas for Nuke, After Effects, and DaVinci Resolve handoff.",
        "files": [
            ("nuke_instruction.schema.json", lambda: schema_comp_instruction("Nuke", "nuke")),
            ("after_effects_instruction.schema.json", lambda: schema_comp_instruction("After Effects", "after_effects")),
            ("davinci_resolve_instruction.schema.json", lambda: schema_comp_instruction("DaVinci Resolve", "davinci_resolve")),
            (
                "nuke_instruction_generator.contract.md",
                lambda: contract(
                    "Nuke Instruction Generator Contract",
                    "Describe the manifest used to generate Nuke scripts from approved render and plate inputs.",
                    ["Render products.", "Plate bindings.", "Color pipeline contract."],
                    ["Nuke instruction manifest."],
                    ["Missing render inputs block script generation."],
                ),
            ),
            (
                "after_effects_instruction_generator.contract.md",
                lambda: contract(
                    "After Effects Instruction Generator Contract",
                    "Describe the manifest used to generate After Effects project instructions.",
                    ["Review media.", "Plate or render inputs."],
                    ["After Effects instruction manifest."],
                    ["Unsupported input media blocks generation."],
                ),
            ),
            (
                "davinci_resolve_instruction_generator.contract.md",
                lambda: contract(
                    "DaVinci Resolve Instruction Generator Contract",
                    "Describe the manifest used to generate DaVinci Resolve timeline and color handoff instructions.",
                    ["Review media.", "Color pipeline contract."],
                    ["DaVinci Resolve instruction manifest."],
                    ["Missing color pipeline blocks generation."],
                ),
            ),
            (
                "nuke_instruction_validator.py",
                lambda: validator_template(
                    "hfx_comp_automation_layer",
                    "nuke_instruction_validator",
                    "Validate Nuke instruction manifests.",
                ),
            ),
            (
                "after_effects_instruction_validator.py",
                lambda: validator_template(
                    "hfx_comp_automation_layer",
                    "after_effects_instruction_validator",
                    "Validate After Effects instruction manifests.",
                ),
            ),
            (
                "davinci_resolve_instruction_validator.py",
                lambda: validator_template(
                    "hfx_comp_automation_layer",
                    "davinci_resolve_instruction_validator",
                    "Validate DaVinci Resolve instruction manifests.",
                ),
            ),
        ],
    },
    {
        "index": 8,
        "name": "hfx_color_management_layer",
        "title": "HFX Color Management Layer",
        "purpose": "Define show color pipeline contracts and placeholder ACES/OCIO gates.",
        "files": [
            ("color_pipeline.schema.json", schema_color_pipeline),
            ("aces_ocio_placeholder.schema.json", schema_ocio_placeholder),
            (
                "color_pipeline.contract.md",
                lambda: contract(
                    "Color Pipeline Contract",
                    "Define working space, display transform, OCIO config pointer, and LUT registry.",
                    ["Show id.", "OCIO config path or placeholder id."],
                    ["Color pipeline manifest."],
                    ["Missing OCIO config blocks production color approval."],
                ),
            ),
            (
                "aces_ocio_placeholder.contract.md",
                lambda: contract(
                    "ACES OCIO Placeholder Contract",
                    "Record that ACES/OCIO exists only as a scaffold placeholder until a real config is approved.",
                    ["ACES version.", "OCIO version.", "Placeholder id."],
                    ["Blocked placeholder contract."],
                    ["Placeholder cannot authorize final pixels or client delivery."],
                ),
            ),
            (
                "color_pipeline_validator.py",
                lambda: validator_template(
                    "hfx_color_management_layer",
                    "color_pipeline_validator",
                    "Validate color pipeline manifests.",
                ),
            ),
            (
                "aces_ocio_placeholder_validator.py",
                lambda: validator_template(
                    "hfx_color_management_layer",
                    "aces_ocio_placeholder_validator",
                    "Validate ACES/OCIO placeholder gates.",
                ),
            ),
        ],
    },
    {
        "index": 9,
        "name": "hfx_review_dailies_layer",
        "title": "HFX Review Dailies Layer",
        "purpose": "Define review packages, contact sheet contracts, and dailies reports.",
        "files": [
            ("review_package.schema.json", schema_review_package),
            ("contact_sheet.schema.json", schema_contact_sheet),
            ("dailies_report.schema.json", schema_dailies_report),
            (
                "review_package.contract.md",
                lambda: contract(
                    "Review Package Contract",
                    "Package reviewable media and notes for dailies and stakeholder review.",
                    ["Reviewable media ids.", "Shot id.", "Review targets."],
                    ["Review package manifest."],
                    ["Missing media blocks review package approval."],
                ),
            ),
            (
                "contact_sheet.contract.md",
                lambda: contract(
                    "Contact Sheet Contract",
                    "Define source media, layout, and burn-ins for contact sheet generation.",
                    ["Review media.", "Layout profile.", "Burn-in metadata."],
                    ["Contact sheet manifest."],
                    ["Missing source media blocks contact sheet generation."],
                ),
            ),
            (
                "dailies_report.contract.md",
                lambda: contract(
                    "Dailies Report Contract",
                    "Record reviewed items, session id, and decisions from a dailies session.",
                    ["Review package ids.", "Session id."],
                    ["Dailies report manifest."],
                    ["Unresolved decisions remain non-delivery blockers until explicitly cleared."],
                ),
            ),
            (
                "review_package_validator.py",
                lambda: validator_template(
                    "hfx_review_dailies_layer",
                    "review_package_validator",
                    "Validate review package manifests.",
                ),
            ),
            (
                "contact_sheet_validator.py",
                lambda: validator_template(
                    "hfx_review_dailies_layer",
                    "contact_sheet_validator",
                    "Validate contact sheet manifests.",
                ),
            ),
            (
                "dailies_report_validator.py",
                lambda: validator_template(
                    "hfx_review_dailies_layer",
                    "dailies_report_validator",
                    "Validate dailies reports.",
                ),
            ),
        ],
    },
    {
        "index": 10,
        "name": "hfx_final_pixel_gate_layer",
        "title": "HFX Final Pixel Gate Layer",
        "purpose": "Fail closed on final pixel claims unless real EXR evidence and production validators exist.",
        "files": [
            ("final_pixel_claim.schema.json", schema_final_pixel_claim),
            ("blocked_claim_registry.schema.json", schema_blocked_claim_registry),
            (
                "blocked_claim_registry.json",
                lambda: {
                    "registry_id": "hfx_blocked_final_pixel_claim_registry",
                    "claims": [],
                    "all_claims_blocked": True,
                    "system_state": SYSTEM_STATE,
                    "policy": "No final pixel claim can pass in bootstrap scaffold state.",
                },
            ),
            (
                "final_pixel_gate.contract.md",
                lambda: contract(
                    "Final Pixel Gate Contract",
                    "Prevent any final-pixel claim from passing in the scaffold state.",
                    ["Final pixel claim envelope.", "Verified real EXR evidence from production validators."],
                    ["Blocked claim report.", "Blocked claim registry update."],
                    [
                        "No verified real EXRs means blocked.",
                        "Metadata alone means blocked.",
                        "Bootstrap scaffold never authorizes final pixels.",
                    ],
                ),
            ),
            (
                "blocked_claim_registry.contract.md",
                lambda: contract(
                    "Blocked Claim Registry Contract",
                    "Record attempted final-pixel claims and the reasons they remain blocked.",
                    ["Final pixel claim id.", "Shot id.", "Blocking reason."],
                    ["Blocked claim registry."],
                    ["Registry must preserve all blocked claim reasons."],
                ),
            ),
            (
                "final_pixel_claim_validator.py",
                lambda: validator_template(
                    "hfx_final_pixel_gate_layer",
                    "final_pixel_claim_validator",
                    "Fail closed unless real EXR evidence is verified by production validators.",
                    final_pixel_gate=True,
                ),
            ),
            (
                "blocked_claim_registry_validator.py",
                lambda: validator_template(
                    "hfx_final_pixel_gate_layer",
                    "blocked_claim_registry_validator",
                    "Validate blocked final pixel claim registry structure.",
                ),
            ),
        ],
    },
    {
        "index": 11,
        "name": "hfx_delivery_package_layer",
        "title": "HFX Delivery Package Layer",
        "purpose": "Define client delivery manifests and delivery blockers while final pixels are unavailable.",
        "files": [
            ("delivery_manifest.schema.json", schema_delivery_manifest),
            ("client_delivery_blocker.schema.json", schema_client_delivery_blocker),
            (
                "delivery_manifest.contract.md",
                lambda: contract(
                    "Delivery Manifest Contract",
                    "Describe delivery ids, client ids, items, color pipeline link, and final-pixel claim status.",
                    ["Client id.", "Delivery item list.", "Color pipeline contract."],
                    ["Delivery manifest."],
                    ["Final pixel claim status must remain blocked in scaffold state."],
                ),
            ),
            (
                "client_delivery_blocker.contract.md",
                lambda: contract(
                    "Client Delivery Blocker Contract",
                    "Block client delivery while final pixel gates and production content remain unavailable.",
                    ["Delivery manifest.", "Final pixel gate result."],
                    ["Client delivery blocker record."],
                    ["Blocked final pixels block client delivery.", "Missing delivery item evidence blocks delivery."],
                ),
            ),
            (
                "delivery_manifest_validator.py",
                lambda: validator_template(
                    "hfx_delivery_package_layer",
                    "delivery_manifest_validator",
                    "Validate delivery manifests.",
                ),
            ),
            (
                "client_delivery_blocker.py",
                lambda: validator_template(
                    "hfx_delivery_package_layer",
                    "client_delivery_blocker",
                    "Validate that client delivery remains blocked when final pixels are unavailable.",
                ),
            ),
        ],
    },
    {
        "index": 12,
        "name": "hfx_master_pipeline_seal",
        "title": "HFX Master Pipeline Seal",
        "purpose": "Evaluate the scaffolded contract layers and emit the only legal master system state.",
        "files": [
            ("master_pipeline_seal.schema.json", schema_master_pipeline_seal),
            (
                "HFX_MASTER_PIPELINE_GLOBAL_SEAL.json",
                lambda: build_master_seal(),
            ),
            (
                "master_pipeline_seal.contract.md",
                lambda: contract(
                    "Master Pipeline Seal Contract",
                    "Aggregate all twelve layer contracts into the global scaffold seal.",
                    ["Layer manifests.", "Final pixel gate policy.", "Delivery blocker policy."],
                    ["HFX_MASTER_PIPELINE_GLOBAL_SEAL.json."],
                    [
                        "All twelve layer directories must exist.",
                        "Final pixel gate must remain fail-closed.",
                        "Output state must be " + SYSTEM_STATE + ".",
                    ],
                ),
            ),
            (
                "master_pipeline_seal_validator.py",
                lambda: validator_template(
                    "hfx_master_pipeline_seal",
                    "master_pipeline_seal_validator",
                    "Validate the master pipeline seal envelope.",
                ),
            ),
        ],
    },
]


GLOBAL_LAYER_FILE_NAMES = (
    "GLOBAL_SEAL.json",
    "GLOBAL_SEAL.contract.md",
    "global_seal_validator.py",
)


def layer_by_name(layer_name):
    for layer in LAYER_SPECS:
        if layer["name"] == layer_name:
            return layer
    raise KeyError(layer_name)


def ordered_unique(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def declared_layer_files(layer):
    return [name for name, _ in layer["files"]]


def layer_required_files(layer):
    return ordered_unique(declared_layer_files(layer) + list(GLOBAL_LAYER_FILE_NAMES) + ["layer_manifest.json"])


def build_layer_global_seal(layer):
    return {
        "seal_id": layer["name"] + "_GLOBAL_SEAL",
        "layer_index": layer["index"],
        "layer_name": layer["name"],
        "title": layer["title"],
        "purpose": layer["purpose"],
        "system_state": SYSTEM_STATE,
        "maximum_allowed_state": MAXIMUM_ALLOWED_STATE,
        "seal_status": "CONTRACT_SCAFFOLD_SEALED",
        "validation_policy": "fail_closed",
        "final_pixels_authorized": False,
        "client_delivery_authorized": False,
        "required_files": layer_required_files(layer),
        "blocked_claim_policy": "block_all_final_pixel_claims_without_real_exr_validation",
    }


def build_layer_global_seal_contract(layer):
    return contract(
        layer["title"] + " Global Seal Contract",
        "Aggregate this layer's schemas, contracts, validators, and manifest into a fail-closed scaffold seal.",
        [
            "Layer schema files.",
            "Layer Markdown contracts.",
            "Layer Python validator templates.",
            "Layer manifest.",
        ],
        ["GLOBAL_SEAL.json", "GLOBAL_SEAL.contract.md", "global_seal_validator.py"],
        [
            "All required layer files must exist.",
            "Layer seal cannot authorize final pixels.",
            "Layer seal cannot authorize client delivery.",
        ],
    )


def layer_global_files(layer):
    return [
        ("GLOBAL_SEAL.json", lambda: build_layer_global_seal(layer)),
        ("GLOBAL_SEAL.contract.md", lambda: build_layer_global_seal_contract(layer)),
        (
            "global_seal_validator.py",
            lambda: validator_template(
                layer["name"],
                "global_seal_validator",
                "Validate the " + layer["name"] + " global scaffold seal.",
            ),
        ),
    ]


def build_layer_manifest(layer):
    return {
        "layer_index": layer["index"],
        "layer_name": layer["name"],
        "title": layer["title"],
        "purpose": layer["purpose"],
        "system_state": SYSTEM_STATE,
        "final_pixels_authorized": False,
        "maximum_allowed_state": MAXIMUM_ALLOWED_STATE,
        "required_files": layer_required_files(layer),
        "validation_policy": "fail_closed",
        "generated_by": pathlib.Path(__file__).name,
    }


def build_master_seal():
    layers = []
    for layer in LAYER_SPECS:
        layer_status = "BLOCKED_NO_FINAL_PIXELS" if layer["name"] == "hfx_final_pixel_gate_layer" else "CONTRACT_SCAFFOLDED"
        layers.append(
            {
                "index": layer["index"],
                "name": layer["name"],
                "title": layer["title"],
                "status": layer_status,
                "required_files": layer_required_files(layer),
                "final_pixels_authorized": False,
            }
        )
    return {
        "seal_id": "HFX_MASTER_PIPELINE_GLOBAL_SEAL",
        "system_state": SYSTEM_STATE,
        "maximum_allowed_state": MAXIMUM_ALLOWED_STATE,
        "pipeline_root": ".",
        "houdini_root": "assets/houdini",
        "layers": layers,
        "final_pixel_gate": {
            "claim_policy": "fail_closed",
            "delivery_policy": "blocked",
            "real_exr_required": True,
            "current_state": SYSTEM_STATE,
            "reason": "The scaffold contains contracts and validators only; no real EXRs or production pixels exist.",
        },
        "delivery_policy": {
            "client_delivery_allowed": False,
            "reason": "Client delivery is blocked until final pixel claims pass real production validation.",
        },
        "output": SYSTEM_STATE,
    }


def make_parent(path):
    os.makedirs(str(path.parent), exist_ok=True)


def write_json(path, payload):
    make_parent(path)
    if path.exists() and not OVERWRITE:
        return "skipped"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return "written"


def write_text(path, text):
    make_parent(path)
    if path.exists() and not OVERWRITE:
        return "skipped"
    path.write_text(str(text).rstrip() + "\n", encoding="utf-8")
    return "written"


def write_file(path, producer):
    payload = producer()
    if isinstance(payload, dict) or isinstance(payload, list):
        return write_json(path, payload)
    return write_text(path, payload)


def bootstrap():
    summary = {"written": 0, "skipped": 0, "layers": []}
    os.makedirs(str(HOUDINI_ROOT), exist_ok=True)
    for layer in LAYER_SPECS:
        layer_dir = HOUDINI_ROOT / layer["name"]
        os.makedirs(str(layer_dir), exist_ok=True)
        layer_written = 0
        layer_skipped = 0
        for file_name, producer in layer["files"]:
            status = write_file(layer_dir / file_name, producer)
            summary[status] += 1
            if status == "written":
                layer_written += 1
            else:
                layer_skipped += 1
        declared_files = set(declared_layer_files(layer))
        for file_name, producer in layer_global_files(layer):
            if file_name in declared_files:
                continue
            status = write_file(layer_dir / file_name, producer)
            summary[status] += 1
            if status == "written":
                layer_written += 1
            else:
                layer_skipped += 1
        manifest_status = write_json(layer_dir / "layer_manifest.json", build_layer_manifest(layer))
        summary[manifest_status] += 1
        if manifest_status == "written":
            layer_written += 1
        else:
            layer_skipped += 1
        summary["layers"].append(
            {
                "name": layer["name"],
                "path": str(layer_dir),
                "written": layer_written,
                "skipped": layer_skipped,
            }
        )
    return summary


def main():
    summary = bootstrap()
    print(json.dumps(
        {
            "system_state": SYSTEM_STATE,
            "houdini_root": str(HOUDINI_ROOT),
            "overwrite": OVERWRITE,
            "written": summary["written"],
            "skipped": summary["skipped"],
            "layers": summary["layers"],
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
