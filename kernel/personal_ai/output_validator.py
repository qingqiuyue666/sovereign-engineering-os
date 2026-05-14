"""Validation reports for Personal AI approved output packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ApprovedOutputValidationResult",
    "build_approved_output_validation",
]

_VALIDATION_TYPE = "personal_ai_local_v1_approved_output_validation"

_REQUIRED_OUTPUT_FILES = {
    "approved_output_manifest": "approved_output_manifest.json",
    "delivery_summary": "delivery_summary.json",
    "approval_receipt": "approval_receipt.json",
    "provenance_chain": "provenance_chain.json",
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
    "final_job_manifest": "final_job_manifest.json",
}

_REQUIRED_BOUNDARIES = {
    "no_runtime_authority",
    "no_arbitrary_execution_capability",
    "no_external_tool_control",
    "no_network",
    "no_api_calls",
    "no_subprocess",
    "no_adapter_implementation",
    "no_input_file_mutation",
    "no_raw_cell_value_copy",
    "no_spreadsheet_output_write",
    "no_destructive_actions",
}

_SPREADSHEET_OUTPUT_SUFFIXES = {
    ".xls",
    ".xlsm",
    ".xlsx",
}

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_arbitrary_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_input_file_mutation": True,
    "no_raw_cell_value_copy": True,
    "no_spreadsheet_output_write": True,
    "no_destructive_actions": True,
}


@dataclass(frozen=True)
class ApprovedOutputValidationResult:
    output_package_dir: Path
    output_validation_path: Path
    complete: bool
    missing_artifacts: list[str]
    malformed_artifacts: list[str]
    artifact_hashes: dict[str, str]
    manifest_hashes_verified: bool
    approval_verified: bool
    provenance_verified: bool
    boundaries_verified: bool
    raw_sentinel_leakage_detected: bool
    spreadsheet_output_files: list[str]


def build_approved_output_validation(
    output_package_dir: Path,
    output_validation_path: Path | None = None,
    *,
    raw_sentinel_values: list[str] | None = None,
) -> ApprovedOutputValidationResult:
    package_path = Path(output_package_dir)
    validation_path = (
        package_path / "approved_output_validation.json"
        if output_validation_path is None
        else Path(output_validation_path)
    )
    _validate_inputs(package_path, validation_path)

    missing_artifacts = _missing_required_artifacts(package_path)
    malformed_artifacts = _malformed_json_artifacts(package_path)
    artifact_hashes = _artifact_hashes(package_path)
    manifest = _read_json_object(package_path / "approved_output_manifest.json")
    delivery_summary = _read_json_object(package_path / "delivery_summary.json")
    approval_receipt = _read_json_object(package_path / "approval_receipt.json")
    provenance_chain = _read_json_object(package_path / "provenance_chain.json")
    manifest_hashes_verified = _manifest_hashes_verified(
        manifest,
        artifact_hashes,
    )
    approval_verified = _approval_verified(manifest, approval_receipt)
    provenance_verified = _provenance_verified(provenance_chain)
    boundary_failures = _boundary_failures(
        manifest,
        delivery_summary,
        provenance_chain,
    )
    boundaries_verified = not boundary_failures
    spreadsheet_output_files = _spreadsheet_output_files(package_path)
    raw_sentinel_leakage_detected = _raw_sentinel_leakage_detected(
        package_path,
        raw_sentinel_values or [],
        validation_path.name,
    )
    complete = (
        not missing_artifacts
        and not malformed_artifacts
        and _manifest_complete(manifest)
        and manifest_hashes_verified
        and approval_verified
        and provenance_verified
        and boundaries_verified
        and not spreadsheet_output_files
        and not raw_sentinel_leakage_detected
    )

    payload = {
        "validation_type": _VALIDATION_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "output_package_dir": package_path.as_posix(),
        "complete": complete,
        "required_artifacts": list(_REQUIRED_OUTPUT_FILES.values()),
        "missing_artifacts": missing_artifacts,
        "malformed_artifacts": malformed_artifacts,
        "artifact_hashes": artifact_hashes,
        "manifest_complete": _manifest_complete(manifest),
        "manifest_hashes_verified": manifest_hashes_verified,
        "approval_verified": approval_verified,
        "provenance_verified": provenance_verified,
        "boundaries_verified": boundaries_verified,
        "boundary_failures": boundary_failures,
        "raw_sentinel_leakage_detected": raw_sentinel_leakage_detected,
        "raw_cell_values_copied": False,
        "input_mutation_performed": False,
        "spreadsheet_output_files": spreadsheet_output_files,
        "spreadsheet_output_written": bool(spreadsheet_output_files),
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(validation_path, payload)

    return ApprovedOutputValidationResult(
        output_package_dir=package_path,
        output_validation_path=validation_path,
        complete=complete,
        missing_artifacts=missing_artifacts,
        malformed_artifacts=malformed_artifacts,
        artifact_hashes=artifact_hashes,
        manifest_hashes_verified=manifest_hashes_verified,
        approval_verified=approval_verified,
        provenance_verified=provenance_verified,
        boundaries_verified=boundaries_verified,
        raw_sentinel_leakage_detected=raw_sentinel_leakage_detected,
        spreadsheet_output_files=spreadsheet_output_files,
    )


def _validate_inputs(package_path, validation_path):
    if not package_path.exists():
        raise ValueError("output_package_dir is missing")
    if not package_path.is_dir():
        raise ValueError("output_package_dir is not a directory")
    parent = Path(validation_path).parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("output_validation_path parent is missing")


def _missing_required_artifacts(package_path):
    missing = [
        artifact_file
        for artifact_file in _REQUIRED_OUTPUT_FILES.values()
        if not (package_path / artifact_file).exists()
    ]
    missing.sort()
    return missing


def _malformed_json_artifacts(package_path):
    malformed = []
    for artifact_file in _REQUIRED_OUTPUT_FILES.values():
        if not artifact_file.endswith(".json"):
            continue
        artifact_path = package_path / artifact_file
        if artifact_path.exists() and _read_json_object(artifact_path) is None:
            malformed.append(artifact_file)
    malformed.sort()
    return malformed


def _artifact_hashes(package_path):
    hashes = {
        artifact_name: sha256_file(package_path / artifact_file)
        for artifact_name, artifact_file in _REQUIRED_OUTPUT_FILES.items()
        if (package_path / artifact_file).exists()
        and (package_path / artifact_file).is_file()
    }
    return {
        artifact_name: hashes[artifact_name]
        for artifact_name in sorted(hashes)
    }


def _read_json_object(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _manifest_complete(manifest):
    return (
        isinstance(manifest, dict)
        and manifest.get("complete") is True
        and manifest.get("missing_artifacts") == []
        and manifest.get("approval_verified") is True
    )


def _manifest_hashes_verified(manifest, artifact_hashes):
    if not isinstance(manifest, dict):
        return False
    manifest_hashes = manifest.get("artifact_hashes")
    if not isinstance(manifest_hashes, dict):
        return False
    for artifact_name, digest in artifact_hashes.items():
        if artifact_name == "approved_output_manifest":
            continue
        if manifest_hashes.get(artifact_name) != digest:
            return False
    return True


def _approval_verified(manifest, approval_receipt):
    return (
        _manifest_complete(manifest)
        and isinstance(approval_receipt, dict)
        and approval_receipt.get("approval_verified") is True
        and approval_receipt.get("hash_binding_verified") is True
    )


def _provenance_verified(provenance_chain):
    return (
        isinstance(provenance_chain, dict)
        and provenance_chain.get("chain_complete") is True
        and provenance_chain.get("hash_binding_verified") is True
    )


def _boundary_failures(manifest, delivery_summary, provenance_chain):
    failures = []
    for source_name, payload in (
        ("approved_output_manifest", manifest),
        ("delivery_summary", delivery_summary),
        ("provenance_chain", provenance_chain),
    ):
        boundaries = payload.get("boundaries") if isinstance(payload, dict) else None
        if not isinstance(boundaries, dict):
            failures.append(f"{source_name}:boundaries_missing")
            continue
        for boundary_name in sorted(_REQUIRED_BOUNDARIES):
            if boundaries.get(boundary_name) is not True:
                failures.append(f"{source_name}:{boundary_name}")
    return failures


def _spreadsheet_output_files(package_path):
    output_files = [
        path.name
        for path in package_path.iterdir()
        if path.is_file() and path.suffix.lower() in _SPREADSHEET_OUTPUT_SUFFIXES
    ]
    output_files.sort()
    return output_files


def _raw_sentinel_leakage_detected(package_path, raw_sentinel_values, validation_name):
    sentinels = [
        value
        for value in raw_sentinel_values
        if isinstance(value, str) and value
    ]
    if not sentinels:
        return False
    for path in sorted(package_path.iterdir(), key=lambda candidate: candidate.name):
        if not path.is_file() or path.name == validation_name:
            continue
        if _file_contains_any(path, sentinels):
            return True
    return False


def _file_contains_any(path, sentinels):
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(sentinel in content for sentinel in sentinels)
