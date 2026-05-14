"""Approved output package builder for Personal AI local v1."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.approval_gate import (
    build_output_approval_request,
    validate_output_approval_decision,
)
from kernel.personal_ai.approval_provenance import (
    _build_approval_provenance_chain_with_manifest_sha256,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.job_package import validate_job_id
from kernel.personal_ai.markdown_utils import write_markdown_atomically
from kernel.personal_ai.output_package_manifest import (
    build_approved_output_manifest,
    planned_approved_output_manifest_sha256,
)

__all__ = [
    "ApprovedOutputPackageResult",
    "build_approved_output_package",
]

_APPROVED_SOURCE_FILES = {
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
    "final_job_manifest": "final_job_manifest.json",
}

_APPROVED_OUTPUT_FILES = [
    "approved_output_manifest.json",
    "delivery_summary.json",
    "approval_receipt.json",
    "provenance_chain.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
]

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
class ApprovedOutputPackageResult:
    output_package_id: str
    output_package_dir: Path
    approved_output_manifest_path: Path
    delivery_summary_path: Path
    approval_receipt_path: Path
    provenance_chain_path: Path
    required_human_approval: bool
    approval_verified: bool
    complete: bool
    missing_artifacts: list[str]


def build_approved_output_package(
    job_dir: Path,
    output_root_dir: Path,
    approval_decision_path: Path,
    *,
    output_package_id: str,
    approval_request_path: Path,
) -> ApprovedOutputPackageResult:
    job_path = Path(job_dir)
    output_root_path = Path(output_root_dir)
    _validate_package_inputs(job_path, output_root_path, output_package_id)

    job_id = _job_id_from_generated_artifacts(job_path)
    input_dir = _input_dir_from_generated_artifacts(job_path)
    if input_dir is not None and _path_is_inside(output_root_path, input_dir):
        raise ValueError("output_root_dir must be outside input_dir")

    _validate_source_artifacts(job_path)
    request_path = Path(approval_request_path)
    if not request_path.exists():
        build_output_approval_request(job_path, request_path)

    decision = validate_output_approval_decision(
        approval_decision_path,
        expected_job_id=job_id,
        approval_request_path=request_path,
        final_job_manifest_path=job_path / "final_job_manifest.json",
        spreadsheet_structural_report_json_path=(
            job_path / "spreadsheet_structural_report.json"
        ),
        spreadsheet_structural_report_markdown_path=(
            job_path / "spreadsheet_structural_report.md"
        ),
    )

    output_package_dir = output_root_path / output_package_id
    if output_package_dir.exists():
        raise ValueError("output_package_dir already exists")
    if input_dir is not None and _path_is_inside(output_package_dir, input_dir):
        raise ValueError("output_package_dir must be outside input_dir")

    output_package_dir.mkdir()

    _copy_json_artifact(
        job_path / "spreadsheet_structural_report.json",
        output_package_dir / "spreadsheet_structural_report.json",
    )
    _copy_markdown_artifact(
        job_path / "spreadsheet_structural_report.md",
        output_package_dir / "spreadsheet_structural_report.md",
    )
    _copy_json_artifact(
        job_path / "final_job_manifest.json",
        output_package_dir / "final_job_manifest.json",
    )

    delivery_summary_path = output_package_dir / "delivery_summary.json"
    approval_receipt_path = output_package_dir / "approval_receipt.json"
    provenance_chain_path = output_package_dir / "provenance_chain.json"
    approved_output_manifest_path = (
        output_package_dir / "approved_output_manifest.json"
    )
    decision_sha256 = sha256_file(approval_decision_path)

    write_json_atomically(
        delivery_summary_path,
        {
            "summary_type": "personal_ai_local_v1_delivery_summary",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "output_package_id": output_package_id,
            "source_job_dir": job_path.as_posix(),
            "delivered_artifacts": list(_APPROVED_OUTPUT_FILES),
            "required_human_approval": True,
            "approval_verified": True,
            "approval_request_sha256": decision.approval_request_sha256,
            "approval_decision_sha256": decision_sha256,
            "hash_binding_verified": True,
            "boundaries": dict(_BOUNDARIES),
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "next_allowed_action": "human_review_only",
        },
    )
    write_json_atomically(
        approval_receipt_path,
        {
            "receipt_type": "personal_ai_local_v1_output_approval_receipt",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "job_id": job_id,
            "output_package_id": output_package_id,
            "approved_action": decision.approved_action,
            "human_reviewed": decision.human_reviewed,
            "approval_verified": True,
            "approval_request_sha256": decision.approval_request_sha256,
            "approval_decision_sha256": decision_sha256,
            "final_job_manifest_sha256": decision.final_job_manifest_sha256,
            "spreadsheet_structural_report_json_sha256": (
                decision.spreadsheet_structural_report_json_sha256
            ),
            "spreadsheet_structural_report_md_sha256": (
                decision.spreadsheet_structural_report_md_sha256
            ),
            "hash_binding_verified": True,
            "next_allowed_action": "human_review_only",
        },
    )

    planned_manifest_sha256 = planned_approved_output_manifest_sha256(
        output_package_dir,
        approved_output_manifest_path,
    )
    _build_approval_provenance_chain_with_manifest_sha256(
        job_path,
        request_path,
        approval_decision_path,
        output_package_dir,
        provenance_chain_path,
        approved_output_manifest_sha256=planned_manifest_sha256,
        assume_approved_output_manifest_present=True,
    )
    manifest_result = build_approved_output_manifest(
        output_package_dir,
        approved_output_manifest_path,
    )

    return ApprovedOutputPackageResult(
        output_package_id=output_package_id,
        output_package_dir=output_package_dir,
        approved_output_manifest_path=approved_output_manifest_path,
        delivery_summary_path=delivery_summary_path,
        approval_receipt_path=approval_receipt_path,
        provenance_chain_path=provenance_chain_path,
        required_human_approval=True,
        approval_verified=manifest_result.approval_verified,
        complete=manifest_result.complete,
        missing_artifacts=manifest_result.missing_artifacts,
    )


def _validate_package_inputs(job_path, output_root_path, output_package_id):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    if not output_root_path.exists():
        raise ValueError("output_root_dir is missing")
    if not output_root_path.is_dir():
        raise ValueError("output_root_dir is not a directory")
    _validate_output_package_id(output_package_id)


def _validate_output_package_id(output_package_id):
    try:
        validate_job_id(output_package_id)
    except ValueError as error:
        raise ValueError("output_package_id is invalid") from error


def _job_id_from_generated_artifacts(job_path):
    job_summary = _read_generated_json(job_path / "job_summary.json")
    job_id = job_summary.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("job_id is missing from job_summary")
    return job_id


def _input_dir_from_generated_artifacts(job_path):
    input_snapshot_path = job_path / "input_snapshot.json"
    if not input_snapshot_path.exists():
        return None
    input_snapshot = _read_generated_json(input_snapshot_path)
    input_dir = input_snapshot.get("input_dir")
    if isinstance(input_dir, str) and input_dir:
        return Path(input_dir)
    return None


def _validate_source_artifacts(job_path):
    missing = [
        artifact_file
        for artifact_file in _APPROVED_SOURCE_FILES.values()
        if not (job_path / artifact_file).exists()
    ]
    if missing:
        raise ValueError("approved source artifacts are missing: " + ", ".join(missing))


def _copy_json_artifact(source_path, output_path):
    payload = _read_generated_json(source_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{Path(source_path).name} must be a JSON object")
    write_json_atomically(output_path, payload)


def _copy_markdown_artifact(source_path, output_path):
    source_file = Path(source_path)
    if not source_file.exists():
        raise ValueError(f"{source_file.name} is missing")
    write_markdown_atomically(
        output_path,
        source_file.read_text(encoding="utf-8"),
    )


def _read_generated_json(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise ValueError(f"{artifact_path.name} is missing")
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{artifact_path.name} is malformed") from error


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = Path(candidate_path).resolve(strict=False)
    resolved_root = Path(root_path).resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True
