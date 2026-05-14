"""Approval gate for Personal AI local v1 output packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "OutputApprovalDecisionResult",
    "OutputApprovalRequestResult",
    "build_output_approval_request",
    "validate_output_approval_decision",
]

_APPROVAL_REQUEST_TYPE = "personal_ai_local_output_approval_request"
_APPROVAL_DECISION_TYPE = "personal_ai_local_output_approval_decision"
_APPROVED_ACTION = "create_approved_output_package"

_APPROVED_OUTPUT_FILES = [
    "approved_output_manifest.json",
    "delivery_summary.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
    "approval_receipt.json",
]

_APPROVED_SOURCE_ARTIFACTS = {
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

_DECISION_KEYS = {
    "decision_type",
    "job_id",
    "approved",
    "approved_action",
    "human_reviewed",
}


@dataclass(frozen=True)
class OutputApprovalRequestResult:
    job_dir: Path
    output_request_path: Path
    required_human_approval: bool


@dataclass(frozen=True)
class OutputApprovalDecisionResult:
    approval_decision_path: Path
    job_id: str
    approved: bool
    approved_action: str
    human_reviewed: bool


def build_output_approval_request(
    job_dir: Path,
    output_request_path: Path,
) -> OutputApprovalRequestResult:
    job_path = Path(job_dir)
    request_path = Path(output_request_path)
    _validate_request_inputs(job_path, request_path)

    job_summary = _read_generated_json(job_path / "job_summary.json")
    final_job_manifest = _read_generated_json(job_path / "final_job_manifest.json")
    job_id = _job_id_from_summary(job_summary, job_path)
    manifest_artifacts = final_job_manifest.get("artifacts", {})

    source_artifacts = {
        artifact_name: str(
            manifest_artifacts.get(
                artifact_name,
                (job_path / artifact_file).as_posix(),
            )
        )
        for artifact_name, artifact_file in _APPROVED_SOURCE_ARTIFACTS.items()
    }

    write_json_atomically(
        request_path,
        {
            "request_type": _APPROVAL_REQUEST_TYPE,
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "job_id": job_id,
            "job_dir": job_path.as_posix(),
            "requested_action": _APPROVED_ACTION,
            "source_artifacts": source_artifacts,
            "output_package_contents": list(_APPROVED_OUTPUT_FILES),
            "required_human_approval": True,
            "approval_required_before_output_package": True,
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "boundaries": dict(_BOUNDARIES),
            "next_allowed_action": "human_approval_required",
        },
    )

    return OutputApprovalRequestResult(
        job_dir=job_path,
        output_request_path=request_path,
        required_human_approval=True,
    )


def validate_output_approval_decision(
    approval_decision_path: Path,
    *,
    expected_job_id: str,
) -> OutputApprovalDecisionResult:
    decision_path = Path(approval_decision_path)
    if not decision_path.exists():
        raise ValueError("approval_decision_path is missing")
    if not decision_path.is_file():
        raise ValueError("approval_decision_path is not a file")

    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("approval_decision_json is malformed") from error

    if not isinstance(decision, dict):
        raise ValueError("approval_decision_json must be an object")
    if set(decision) != _DECISION_KEYS:
        raise ValueError("approval_decision_json has unsupported keys")
    if decision["decision_type"] != _APPROVAL_DECISION_TYPE:
        raise ValueError("approval_decision decision_type mismatch")
    if not isinstance(decision["job_id"], str):
        raise ValueError("approval_decision job_id is invalid")
    if decision["job_id"] != expected_job_id:
        raise ValueError("approval_decision job_id mismatch")
    if decision["approved"] is not True:
        raise ValueError("approval_decision approved must be true")
    if decision["approved_action"] != _APPROVED_ACTION:
        raise ValueError("approval_decision approved_action mismatch")
    if decision["human_reviewed"] is not True:
        raise ValueError("approval_decision human_reviewed must be true")

    return OutputApprovalDecisionResult(
        approval_decision_path=decision_path,
        job_id=decision["job_id"],
        approved=True,
        approved_action=decision["approved_action"],
        human_reviewed=True,
    )


def _validate_request_inputs(job_path, request_path):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    if not request_path.parent.exists() or not request_path.parent.is_dir():
        raise ValueError("output_request_path parent is missing")


def _read_generated_json(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise ValueError(f"{artifact_path.name} is missing")
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{artifact_path.name} is malformed") from error


def _job_id_from_summary(job_summary, job_path):
    job_id = job_summary.get("job_id")
    if isinstance(job_id, str) and job_id:
        return job_id
    return job_path.name
