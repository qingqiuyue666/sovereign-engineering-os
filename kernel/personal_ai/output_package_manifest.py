"""Approved output package manifest for Personal AI local v1."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import (
    hash_artifact_set,
    sha256_canonical_json,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ApprovedOutputManifestResult",
    "approved_output_manifest_sha256_for_provenance",
    "build_approved_output_manifest",
    "planned_approved_output_manifest_sha256",
]

_REQUIRED_OUTPUT_FILES = {
    "approved_output_manifest": "approved_output_manifest.json",
    "delivery_summary": "delivery_summary.json",
    "approval_receipt": "approval_receipt.json",
    "provenance_chain": "provenance_chain.json",
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
    "final_job_manifest": "final_job_manifest.json",
}

_BOUNDARIES = {
    "no_runtime_authority": True,
    "no_arbitrary_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_ai_classification": True,
    "no_semantic_classification": True,
    "no_input_file_mutation": True,
    "no_raw_cell_value_copy": True,
    "no_spreadsheet_output_write": True,
    "no_destructive_actions": True,
}

_FORBIDDEN_ACTIONS = [
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "write_spreadsheet_outputs",
    "copy_raw_cell_values",
    "call_network",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
]


@dataclass(frozen=True)
class ApprovedOutputManifestResult:
    output_package_dir: Path
    output_manifest_path: Path
    complete: bool
    missing_artifacts: list[str]
    approval_verified: bool
    artifact_hashes: dict[str, str]


def build_approved_output_manifest(
    output_package_dir: Path,
    output_manifest_path: Path,
) -> ApprovedOutputManifestResult:
    package_path = Path(output_package_dir)
    manifest_path = Path(output_manifest_path)
    _validate_manifest_inputs(package_path, manifest_path)

    manifest = _build_manifest_payload(package_path, manifest_path)
    manifest["approved_output_manifest_sha256_excluding_self"] = (
        _manifest_sha256_for_provenance(manifest)
    )

    write_json_atomically(manifest_path, manifest)

    return ApprovedOutputManifestResult(
        output_package_dir=package_path,
        output_manifest_path=manifest_path,
        complete=manifest["complete"],
        missing_artifacts=manifest["missing_artifacts"],
        approval_verified=manifest["approval_verified"],
        artifact_hashes=manifest["artifact_hashes"],
    )


def planned_approved_output_manifest_sha256(
    output_package_dir: Path,
    output_manifest_path: Path,
) -> str:
    package_path = Path(output_package_dir)
    manifest_path = Path(output_manifest_path)
    _validate_manifest_inputs(package_path, manifest_path)
    manifest = _build_manifest_payload(
        package_path,
        manifest_path,
        assume_provenance_chain_present=True,
    )
    return _manifest_sha256_for_provenance(manifest)


def approved_output_manifest_sha256_for_provenance(
    output_package_dir: Path,
    output_manifest_path: Path,
) -> str:
    package_path = Path(output_package_dir)
    manifest_path = Path(output_manifest_path)
    _validate_manifest_inputs(package_path, manifest_path)
    if not manifest_path.exists():
        raise ValueError("approved_output_manifest.json is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("approved_output_manifest.json is malformed") from error
    if not isinstance(manifest, dict):
        raise ValueError("approved_output_manifest.json must be an object")
    return _manifest_sha256_for_provenance(manifest)


def _validate_manifest_inputs(package_path, manifest_path):
    if not package_path.exists():
        raise ValueError("output_package_dir is missing")
    if not package_path.is_dir():
        raise ValueError("output_package_dir is not a directory")
    if not manifest_path.parent.exists() or not manifest_path.parent.is_dir():
        raise ValueError("output_manifest_path parent is missing")
    if manifest_path.parent.resolve(strict=True) != package_path.resolve(strict=True):
        raise ValueError("output_manifest_path must be in output_package_dir")
    if manifest_path.name != "approved_output_manifest.json":
        raise ValueError("output_manifest_path must be approved_output_manifest.json")


def _build_manifest_payload(
    package_path,
    manifest_path,
    *,
    assume_provenance_chain_present=False,
):
    artifacts = {
        artifact_name: (package_path / artifact_file).as_posix()
        for artifact_name, artifact_file in _REQUIRED_OUTPUT_FILES.items()
    }
    artifact_presence = {
        artifact_name: _artifact_is_present(
            package_path,
            manifest_path,
            artifact_name,
            artifact_file,
            assume_provenance_chain_present=assume_provenance_chain_present,
        )
        for artifact_name, artifact_file in _REQUIRED_OUTPUT_FILES.items()
    }
    missing_artifacts = [
        artifact_file
        for artifact_name, artifact_file in _REQUIRED_OUTPUT_FILES.items()
        if not artifact_presence[artifact_name]
    ]
    approval_verified = _approval_receipt_verified(
        package_path / "approval_receipt.json"
    )
    return {
        "manifest_type": "personal_ai_local_v1_approved_output_manifest",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "output_package_dir": package_path.as_posix(),
        "artifacts": artifacts,
        "artifact_presence": artifact_presence,
        "artifact_hashes": _artifact_hashes(package_path, artifact_presence),
        "complete": not missing_artifacts,
        "missing_artifacts": missing_artifacts,
        "approval_verified": approval_verified,
        "boundaries": dict(_BOUNDARIES),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "next_allowed_action": "human_review_only",
    }


def _artifact_is_present(
    package_path,
    manifest_path,
    artifact_name,
    artifact_file,
    *,
    assume_provenance_chain_present=False,
):
    expected_path = package_path / artifact_file
    if artifact_name == "approved_output_manifest":
        return manifest_path == expected_path
    if artifact_name == "provenance_chain" and assume_provenance_chain_present:
        return True
    return expected_path.exists()


def _artifact_hashes(package_path, artifact_presence):
    hashable_artifact_paths = {
        artifact_name: package_path / artifact_file
        for artifact_name, artifact_file in _REQUIRED_OUTPUT_FILES.items()
        if artifact_name != "approved_output_manifest"
        and artifact_presence.get(artifact_name) is True
        and (package_path / artifact_file).exists()
        and (package_path / artifact_file).is_file()
    }
    return hash_artifact_set(hashable_artifact_paths)


def _manifest_sha256_for_provenance(manifest):
    hash_payload = dict(manifest)
    hash_payload.pop("approved_output_manifest_sha256_excluding_self", None)
    artifact_hashes = dict(hash_payload.get("artifact_hashes", {}))
    artifact_hashes.pop("provenance_chain", None)
    hash_payload["artifact_hashes"] = artifact_hashes
    return sha256_canonical_json(hash_payload)


def _approval_receipt_verified(receipt_path):
    if not receipt_path.exists():
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(receipt, dict):
        return False
    return (
        receipt.get("approval_verified") is True
        and receipt.get("hash_binding_verified") is True
    )
