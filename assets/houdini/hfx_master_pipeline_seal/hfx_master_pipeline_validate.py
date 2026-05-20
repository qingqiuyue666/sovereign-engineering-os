#!/usr/bin/env python3
"""
Runtime validator for the HFX master pipeline no-final-pixels scaffold.
"""

import hashlib
import json
import pathlib
import subprocess
import sys


SYSTEM_STATE = 'HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS'
PASS_STATE = 'HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS_PASS'
LAYER_NAMES = ['hfx_assetization_layer', 'hfx_aov_pass_contract_layer', 'hfx_resource_library_layer', 'hfx_lookdev_shader_contract_layer', 'hfx_plate_camera_integration_layer', 'hfx_render_automation_layer', 'hfx_comp_automation_layer', 'hfx_color_management_layer', 'hfx_review_dailies_layer', 'hfx_final_pixel_gate_layer', 'hfx_delivery_package_layer', 'hfx_master_pipeline_seal']
OUTPUT_NAMES = {
    "HFX_MASTER_PIPELINE_VALIDATION_REPORT.json",
    "HFX_MASTER_PIPELINE_VALIDATION_REPORT.md",
    "HFX_MASTER_PIPELINE_MANIFEST.json",
    "HFX_MASTER_PIPELINE_SHA256SUMS.txt",
    "HFX_MASTER_PIPELINE_FILE_TREE.txt",
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[3]


def rel(path):
    return str(path.relative_to(repo_root()))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def status_pass(data):
    status = str(data.get("status", ""))
    return data.get("validated") is True or status.endswith("_PASS") or status == "PASS"


def run_layer_validator(layer_dir):
    validator = layer_dir / "global_seal_validator.py"
    result = subprocess.run(
        [sys.executable, str(validator)],
        cwd=str(repo_root()),
        text=True,
        capture_output=True,
    )
    report_path = layer_dir / "GLOBAL_SEAL_VALIDATION.json"
    report = read_json(report_path) if report_path.exists() else {}
    return {
        "validator": rel(validator),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "report_path": rel(report_path),
        "status": report.get("status", "MISSING"),
        "pass": result.returncode == 0 and report.get("status") == "PASS",
    }


def validate_reference(path, label):
    if not path.exists():
        return {
            "label": label,
            "path": rel(path),
            "present": False,
            "authoritative": False,
            "status": "REFERENCE_MISSING_NON_AUTHORITATIVE",
            "pass": True,
            "final_pixels_authorized": False,
        }
    data = read_json(path)
    passed = status_pass(data)
    return {
        "label": label,
        "path": rel(path),
        "present": True,
        "authoritative": passed,
        "status": data.get("status", "UNKNOWN"),
        "validated": data.get("validated"),
        "pass": passed,
        "final_pixels_authorized": False,
    }


def collect_files(root):
    paths = []
    for layer_name in LAYER_NAMES:
        layer_dir = root / "assets" / "houdini" / layer_name
        if layer_dir.exists():
            paths.extend(path for path in layer_dir.rglob("*") if path.is_file())
    return sorted(paths, key=lambda path: rel(path))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_markdown(report):
    lines = [
        "# HFX Master Pipeline Validation Report",
        "",
        "- Status: `" + report["status"] + "`",
        "- System state: `" + report["system_state"] + "`",
        "- Final pixels authorized: `false`",
        "- Client delivery allowed: `false`",
        "- Claim policy: `fail_closed`",
        "",
        "## Layer Validators",
    ]
    for layer in report["layers"]:
        lines.append("- `" + layer["name"] + "`: `" + layer["validation"]["status"] + "`")
    lines.extend(["", "## References"])
    for reference in report["references"]:
        lines.append("- `" + reference["label"] + "`: `" + reference["status"] + "`")
    lines.append("")
    return "\n".join(lines)


def validate():
    root = repo_root()
    houdini_root = root / "assets" / "houdini"
    output_dir = houdini_root / "hfx_master_pipeline_seal"
    failures = []
    layers = []

    for index, layer_name in enumerate(LAYER_NAMES, start=1):
        layer_dir = houdini_root / layer_name
        layer = {
            "index": index,
            "name": layer_name,
            "path": rel(layer_dir),
            "exists": layer_dir.is_dir(),
            "manifest_exists": (layer_dir / "layer_manifest.json").is_file(),
            "global_seal_exists": (layer_dir / "GLOBAL_SEAL.json").is_file(),
            "global_validator_exists": (layer_dir / "global_seal_validator.py").is_file(),
            "final_pixels_authorized": False,
        }
        for key in ("exists", "manifest_exists", "global_seal_exists", "global_validator_exists"):
            if not layer[key]:
                failures.append(layer_name + ":" + key)
        if layer["global_validator_exists"]:
            layer["validation"] = run_layer_validator(layer_dir)
            if not layer["validation"]["pass"]:
                failures.append(layer_name + ":global_validator")
        else:
            layer["validation"] = {"status": "MISSING", "pass": False}
        layers.append(layer)

    master_seal_path = output_dir / "HFX_MASTER_PIPELINE_GLOBAL_SEAL.json"
    master_seal = read_json(master_seal_path)
    master_checks = {
        "system_state": master_seal.get("system_state") == SYSTEM_STATE,
        "output": master_seal.get("output") == SYSTEM_STATE,
        "maximum_allowed_state": master_seal.get("maximum_allowed_state") == SYSTEM_STATE,
        "final_pixels_authorized": master_seal.get("final_pixels_authorized") is False,
        "client_delivery_allowed": master_seal.get("client_delivery_allowed") is False
        and master_seal.get("delivery_policy", {}).get("client_delivery_allowed") is False,
        "final_pixel_gate_claim_policy": master_seal.get("final_pixel_gate", {}).get("claim_policy") == "fail_closed",
        "real_exr_required": master_seal.get("final_pixel_gate", {}).get("real_exr_required") is True,
    }
    for key, passed in master_checks.items():
        if not passed:
            failures.append("master_seal:" + key)

    references = [
        validate_reference(
            houdini_root
            / "hfx_factory_core12"
            / "500_HFX_FACTORY"
            / "HFX_FACTORY_FINAL_GLOBAL_SEAL"
            / "02_validation"
            / "HFX_FACTORY_FINAL_GLOBAL_SEAL_VALIDATION.json",
            "Core 12 factory global seal",
        ),
        validate_reference(
            houdini_root / "hfx_shot_binding_layer" / "validation" / "HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.json",
            "Shot Binding Layer global seal",
        ),
    ]
    for reference in references:
        if reference["present"] and not reference["pass"]:
            failures.append(reference["label"] + ":reference_status")

    report = {
        "status": PASS_STATE if not failures else "HFX_MASTER_PIPELINE_SYSTEM_READY_NO_FINAL_PIXELS_BLOCKED",
        "system_state": SYSTEM_STATE,
        "output": SYSTEM_STATE,
        "maximum_allowed_state": SYSTEM_STATE,
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
        "final_pixel_gate": {
            "claim_policy": "fail_closed",
            "real_exr_required": True,
            "final_pixel_claim_status": "FINAL_PIXEL_CLAIM_BLOCKED",
        },
        "layers": layers,
        "references": references,
        "master_checks": master_checks,
        "failures": failures,
    }

    report_json = output_dir / "HFX_MASTER_PIPELINE_VALIDATION_REPORT.json"
    report_md = output_dir / "HFX_MASTER_PIPELINE_VALIDATION_REPORT.md"
    manifest_path = output_dir / "HFX_MASTER_PIPELINE_MANIFEST.json"
    file_tree_path = output_dir / "HFX_MASTER_PIPELINE_FILE_TREE.txt"
    sha_path = output_dir / "HFX_MASTER_PIPELINE_SHA256SUMS.txt"

    write_json(report_json, report)
    report_md.write_text(build_markdown(report), encoding="utf-8")

    files = collect_files(root)
    file_tree_lines = [rel(path) for path in files]
    file_tree_path.write_text("\n".join(file_tree_lines) + "\n", encoding="utf-8")

    manifest = {
        "manifest_id": "HFX_MASTER_PIPELINE_MANIFEST",
        "status": report["status"],
        "system_state": SYSTEM_STATE,
        "layer_count": len(LAYER_NAMES),
        "layers": LAYER_NAMES,
        "outputs": sorted(OUTPUT_NAMES),
        "file_count": len(files),
        "final_pixels_authorized": False,
        "client_delivery_allowed": False,
    }
    write_json(manifest_path, manifest)

    checksum_files = [path for path in collect_files(root) if path != sha_path]
    sha_lines = [sha256(path) + "  " + rel(path) for path in checksum_files]
    sha_path.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    return report


def main():
    report = validate()
    print(report["status"])
    return 0 if report["status"] == PASS_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
