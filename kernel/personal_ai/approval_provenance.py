"""Approval provenance chain for Personal AI local v1 output packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.approval_gate import (
    approval_request_sha256_excluding_self,
    validate_output_approval_decision,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.output_package_manifest import (
    approved_output_manifest_sha256_for_provenance,
)

__all__ = [
    "ApprovalProvenanceChainResult",
    "build_approval_provenance_chain",
]

_PROVENANCE_TYPE = "personal_ai_local_v1_approval_provenance_chain"

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

_SOURCE_ARTIFACT_FILES = {
    "final_job_manifest": "final_job_manifest.json",
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
}

_OUTPUT_ARTIFACT_FILES = {
    "approval_receipt": "approval_receipt.json",
    "approved_output_manifest": "approved_output_manifest.json",
    "delivery_summary": "delivery_summary.json",
    "output_final_job_manifest": "final_job_manifest.json",
    "output_spreadsheet_structural_report_json": (
        "spreadsheet_structural_report.json"
    ),
    "output_spreadsheet_structural_report_markdown": (
        "spreadsheet_structural_report.md"
    ),
}


@dataclass(frozen=True)
class ApprovalProvenanceChainResult:
    output_provenance_path: Path
    chain_complete: bool
    missing_artifacts: list[str]
    hash_binding_verified: bool
    artifact_hashes: dict[str, str]


def build_approval_provenance_chain(
    job_dir: Path,
    approval_request_path: Path,
    approval_decision_path: Path,
    output_package_dir: Path,
    output_provenance_path: Path,
) -> ApprovalProvenanceChainResult:
    package_path = Path(output_package_dir)
    manifest_path = package_path / "approved_output_manifest.json"
    manifest_sha256 = approved_output_manifest_sha256_for_provenance(
        package_path,
        manifest_path,
    )
    return _build_approval_provenance_chain_with_manifest_sha256(
        job_dir,
        approval_request_path,
        approval_decision_path,
        package_path,
        output_provenance_path,
        approved_output_manifest_sha256=manifest_sha256,
        assume_approved_output_manifest_present=True,
    )


def _build_approval_provenance_chain_with_manifest_sha256(
    job_dir: Path,
    approval_request_path: Path,
    approval_decision_path: Path,
    output_package_dir: Path,
    output_provenance_path: Path,
    *,
    approved_output_manifest_sha256: str,
    assume_approved_output_manifest_present: bool = False,
) -> ApprovalProvenanceChainResult:
    job_path = Path(job_dir)
    request_path = Path(approval_request_path)
    decision_path = Path(approval_decision_path)
    package_path = Path(output_package_dir)
    provenance_path = Path(output_provenance_path)
    _validate_provenance_inputs(
        job_path,
        request_path,
        decision_path,
        package_path,
        provenance_path,
    )

    artifact_paths = _required_artifact_paths(
        job_path,
        request_path,
        decision_path,
        package_path,
    )
    missing_artifacts = _missing_artifacts(
        artifact_paths,
        assume_approved_output_manifest_present=(
            assume_approved_output_manifest_present
        ),
    )
    artifact_hashes = _artifact_hashes(
        artifact_paths,
        approved_output_manifest_sha256=approved_output_manifest_sha256,
        assume_approved_output_manifest_present=(
            assume_approved_output_manifest_present
        ),
    )
    chain_complete = not missing_artifacts
    hash_binding_verified = _hash_binding_verified(
        job_path,
        request_path,
        decision_path,
        package_path,
        artifact_hashes,
        chain_complete=chain_complete,
    )

    payload = {
        "provenance_type": _PROVENANCE_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "job_dir": job_path.as_posix(),
        "output_package_dir": package_path.as_posix(),
        "approval_request_sha256": artifact_hashes.get("approval_request"),
        "approval_decision_sha256": artifact_hashes.get("approval_decision"),
        "approval_receipt_sha256": artifact_hashes.get("approval_receipt"),
        "approved_output_manifest_sha256": artifact_hashes.get(
            "approved_output_manifest"
        ),
        "delivery_summary_sha256": artifact_hashes.get("delivery_summary"),
        "final_job_manifest_sha256": artifact_hashes.get("final_job_manifest"),
        "spreadsheet_structural_report_json_sha256": artifact_hashes.get(
            "spreadsheet_structural_report_json"
        ),
        "spreadsheet_structural_report_md_sha256": artifact_hashes.get(
            "spreadsheet_structural_report_markdown"
        ),
        "artifact_hashes": artifact_hashes,
        "chain_complete": chain_complete,
        "missing_artifacts": missing_artifacts,
        "hash_binding_verified": hash_binding_verified,
        "boundaries": dict(_BOUNDARIES),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(provenance_path, payload)

    return ApprovalProvenanceChainResult(
        output_provenance_path=provenance_path,
        chain_complete=chain_complete,
        missing_artifacts=missing_artifacts,
        hash_binding_verified=hash_binding_verified,
        artifact_hashes=artifact_hashes,
    )


def _validate_provenance_inputs(
    job_path,
    request_path,
    decision_path,
    package_path,
    provenance_path,
):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    if not request_path.exists():
        raise ValueError("approval_request_path is missing")
    if not request_path.is_file():
        raise ValueError("approval_request_path is not a file")
    if not decision_path.exists():
        raise ValueError("approval_decision_path is missing")
    if not decision_path.is_file():
        raise ValueError("approval_decision_path is not a file")
    if not package_path.exists():
        raise ValueError("output_package_dir is missing")
    if not package_path.is_dir():
        raise ValueError("output_package_dir is not a directory")
    if not provenance_path.parent.exists() or not provenance_path.parent.is_dir():
        raise ValueError("output_provenance_path parent is missing")


def _required_artifact_paths(job_path, request_path, decision_path, package_path):
    artifact_paths = {
        "approval_request": request_path,
        "approval_decision": decision_path,
    }
    artifact_paths.update(
        {
            artifact_name: job_path / artifact_file
            for artifact_name, artifact_file in _SOURCE_ARTIFACT_FILES.items()
        }
    )
    artifact_paths.update(
        {
            artifact_name: package_path / artifact_file
            for artifact_name, artifact_file in _OUTPUT_ARTIFACT_FILES.items()
        }
    )
    return artifact_paths


def _missing_artifacts(
    artifact_paths,
    *,
    assume_approved_output_manifest_present,
):
    missing = []
    for artifact_name in sorted(artifact_paths):
        if (
            artifact_name == "approved_output_manifest"
            and assume_approved_output_manifest_present
        ):
            continue
        artifact_path = artifact_paths[artifact_name]
        if not artifact_path.exists() or not artifact_path.is_file():
            missing.append(artifact_name)
    return missing


def _artifact_hashes(
    artifact_paths,
    *,
    approved_output_manifest_sha256,
    assume_approved_output_manifest_present,
):
    hashes = {}
    for artifact_name in sorted(artifact_paths):
        artifact_path = artifact_paths[artifact_name]
        if artifact_name == "approval_request":
            hashes[artifact_name] = approval_request_sha256_excluding_self(
                artifact_path
            )
            continue
        if artifact_name == "approved_output_manifest":
            if artifact_path.exists() or assume_approved_output_manifest_present:
                hashes[artifact_name] = approved_output_manifest_sha256
            continue
        if artifact_path.exists() and artifact_path.is_file():
            hashes[artifact_name] = sha256_file(artifact_path)
    return hashes


def _hash_binding_verified(
    job_path,
    request_path,
    decision_path,
    package_path,
    artifact_hashes,
    *,
    chain_complete,
):
    if not chain_complete:
        return False
    try:
        validate_output_approval_decision(
            decision_path,
            expected_job_id=_job_id_from_summary(job_path),
            approval_request_path=request_path,
            final_job_manifest_path=job_path / "final_job_manifest.json",
            spreadsheet_structural_report_json_path=(
                job_path / "spreadsheet_structural_report.json"
            ),
            spreadsheet_structural_report_markdown_path=(
                job_path / "spreadsheet_structural_report.md"
            ),
        )
        receipt = _read_json(package_path / "approval_receipt.json")
    except ValueError:
        return False

    expected_receipt_hashes = {
        "approval_request_sha256": artifact_hashes.get("approval_request"),
        "approval_decision_sha256": artifact_hashes.get("approval_decision"),
        "final_job_manifest_sha256": artifact_hashes.get("final_job_manifest"),
        "spreadsheet_structural_report_json_sha256": artifact_hashes.get(
            "spreadsheet_structural_report_json"
        ),
        "spreadsheet_structural_report_md_sha256": artifact_hashes.get(
            "spreadsheet_structural_report_markdown"
        ),
    }
    if receipt.get("hash_binding_verified") is not True:
        return False
    for field_name, expected_hash in expected_receipt_hashes.items():
        if receipt.get(field_name) != expected_hash:
            return False

    output_source_pairs = (
        ("output_final_job_manifest", "final_job_manifest"),
        (
            "output_spreadsheet_structural_report_json",
            "spreadsheet_structural_report_json",
        ),
        (
            "output_spreadsheet_structural_report_markdown",
            "spreadsheet_structural_report_markdown",
        ),
    )
    return all(
        artifact_hashes.get(output_name) == artifact_hashes.get(source_name)
        for output_name, source_name in output_source_pairs
    )


def _job_id_from_summary(job_path):
    summary = _read_json(job_path / "job_summary.json")
    job_id = summary.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("job_id is missing from job_summary")
    return job_id


def _read_json(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise ValueError(f"{artifact_path.name} is missing")
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{artifact_path.name} is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_path.name} must be a JSON object")
    return payload
