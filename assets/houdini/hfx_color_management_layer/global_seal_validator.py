#!/usr/bin/env python3
"""
Fail-closed global seal validator for hfx_color_management_layer.
"""

import json
import pathlib
import sys


SYSTEM_STATE = 'HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS'
LAYER_NAME = 'hfx_color_management_layer'
VALIDATION_FILE = "GLOBAL_SEAL_VALIDATION.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_authorization_violations(value, path="$"):
    violations = []
    forbidden_true_keys = {
        "final_pixels_authorized",
        "final_pixel_authorized",
        "final_pixel_ready",
        "final_pixel_render_complete",
        "actual_openexr_rendered",
        "actual_exr_rendered",
        "client_delivery_authorized",
        "client_delivery_allowed",
        "delivery_ready",
        "public_delivery_ready",
    }
    forbidden_string_tokens = {
        "HFX_MASTER_PIPELINE_FINAL_PIXEL_READY",
        "FINAL_PIXEL_RENDER_COMPLETE",
        "CLIENT_DELIVERY_READY",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in forbidden_true_keys and child is True:
                violations.append(f"{child_path} is true")
            violations.extend(collect_authorization_violations(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(collect_authorization_violations(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for token in forbidden_string_tokens:
            if token in value:
                violations.append(f"{path} contains {token}")
    return violations


def validate():
    layer_dir = pathlib.Path(__file__).resolve().parent
    checks = []
    failures = []

    manifest_path = layer_dir / "layer_manifest.json"
    seal_path = layer_dir / "GLOBAL_SEAL.json"

    def check(name, condition, detail):
        checks.append({"name": name, "pass": bool(condition), "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("layer_manifest_exists", manifest_path.exists(), str(manifest_path))
    check("global_seal_exists", seal_path.exists(), str(seal_path))

    manifest = {}
    seal = {}
    if manifest_path.exists():
        manifest = read_json(manifest_path)
    if seal_path.exists():
        seal = read_json(seal_path)

    for file_name in manifest.get("required_files", []):
        required_path = layer_dir / file_name
        check("required_file_exists", required_path.exists(), file_name)

    check("manifest_system_state", manifest.get("system_state") == SYSTEM_STATE, manifest.get("system_state"))
    check("seal_system_state", seal.get("system_state") == SYSTEM_STATE, seal.get("system_state"))
    check(
        "manifest_maximum_allowed_state",
        manifest.get("maximum_allowed_state") == SYSTEM_STATE,
        manifest.get("maximum_allowed_state"),
    )
    check(
        "seal_maximum_allowed_state",
        seal.get("maximum_allowed_state") == SYSTEM_STATE,
        seal.get("maximum_allowed_state"),
    )
    check("manifest_validation_policy", manifest.get("validation_policy") == "fail_closed", manifest.get("validation_policy"))
    check("seal_validation_policy", seal.get("validation_policy") == "fail_closed", seal.get("validation_policy"))
    check("manifest_final_pixels_false", manifest.get("final_pixels_authorized") is False, manifest.get("final_pixels_authorized"))
    check("seal_final_pixels_false", seal.get("final_pixels_authorized") is False, seal.get("final_pixels_authorized"))
    check(
        "seal_client_delivery_false",
        seal.get("client_delivery_authorized") is False,
        seal.get("client_delivery_authorized"),
    )

    authorization_violations = collect_authorization_violations({"manifest": manifest, "seal": seal})
    check(
        "forbidden_authorization_absent",
        not authorization_violations,
        authorization_violations,
    )

    report = {
        "layer_name": LAYER_NAME,
        "status": "PASS" if not failures else "FAIL",
        "system_state": SYSTEM_STATE,
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "validation_policy": "fail_closed",
        "checks": checks,
        "failures": failures,
    }
    (layer_dir / VALIDATION_FILE).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    report = validate()
    print(report["status"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
