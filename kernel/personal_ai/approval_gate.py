"""Approval gate for Personal AI local v1 output packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import (
    hash_artifact_set,
    sha256_canonical_json,
    sha256_file,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "OutputApprovalDecisionResult",
    "OutputApprovalRequestResult",
    "approval_request_sha256_excluding_self",
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
    "provenance_chain.json",
    "approved_output_validation.json",
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
    "decision_version",
    "job_id",
    "approved",
    "approved_action",
    "human_reviewed",
    "approval_request_sha256",
    "final_job_manifest_sha256",
    "spreadsheet_structural_report_json_sha256",
    "spreadsheet_structural_report_md_sha256",
}


@dataclass(frozen=True)
class OutputApprovalRequestResult:
    job_dir: Path
    output_request_path: Path
    required_human_approval: bool
    approval_request_sha256: str
    source_artifact_hashes: dict[str, str]


@dataclass(frozen=True)
class OutputApprovalDecisionResult:
    approval_decision_path: Path
    job_id: str
    approved: bool
    approved_action: str
    human_reviewed: bool
    approval_request_sha256: str
    final_job_manifest_sha256: str
    spreadsheet_structural_report_json_sha256: str
    spreadsheet_structural_report_md_sha256: str
    hash_binding_verified: bool


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

    source_artifact_paths = _source_artifact_paths(job_path, manifest_artifacts)
    source_artifacts = {
        artifact_name: source_artifact_paths[artifact_name].as_posix()
        for artifact_name in sorted(source_artifact_paths)
    }
    source_artifact_hashes = hash_artifact_set(source_artifact_paths)

    payload = {
            "request_type": _APPROVAL_REQUEST_TYPE,
            "approval_request_version": 1,
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "job_id": job_id,
            "job_dir": job_path.as_posix(),
            "requested_action": _APPROVED_ACTION,
            "source_artifacts": source_artifacts,
            "source_artifact_hashes": source_artifact_hashes,
            "final_job_manifest_sha256": source_artifact_hashes[
                "final_job_manifest"
            ],
            "spreadsheet_structural_report_json_sha256": source_artifact_hashes[
                "spreadsheet_structural_report_json"
            ],
            "spreadsheet_structural_report_md_sha256": source_artifact_hashes[
                "spreadsheet_structural_report_markdown"
            ],
            "output_package_contents": list(_APPROVED_OUTPUT_FILES),
            "required_human_approval": True,
            "approval_required_before_output_package": True,
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "boundaries": dict(_BOUNDARIES),
            "next_allowed_action": "human_approval_required",
    }
    approval_request_sha256 = sha256_canonical_json(payload)
    payload["approval_request_sha256_excluding_self"] = approval_request_sha256
    write_json_atomically(request_path, payload)

    return OutputApprovalRequestResult(
        job_dir=job_path,
        output_request_path=request_path,
        required_human_approval=True,
        approval_request_sha256=approval_request_sha256,
        source_artifact_hashes=source_artifact_hashes,
    )


def validate_output_approval_decision(
    approval_decision_path: Path,
    *,
    expected_job_id: str,
    approval_request_path: Path,
    final_job_manifest_path: Path,
    spreadsheet_structural_report_json_path: Path,
    spreadsheet_structural_report_markdown_path: Path,
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
    _validate_decision_keys(decision)
    if decision["decision_type"] != _APPROVAL_DECISION_TYPE:
        raise ValueError("approval_decision decision_type mismatch")
    if type(decision["decision_version"]) is not int:
        raise ValueError("approval_decision decision_version is invalid")
    if decision["decision_version"] != 1:
        raise ValueError("approval_decision decision_version mismatch")
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

    approval_request_hash, request_artifact_hashes = (
        approval_request_hash_binding(approval_request_path)
    )
    expected_hashes = {
        "approval_request_sha256": approval_request_hash,
        "final_job_manifest_sha256": sha256_file(final_job_manifest_path),
        "spreadsheet_structural_report_json_sha256": sha256_file(
            spreadsheet_structural_report_json_path
        ),
        "spreadsheet_structural_report_md_sha256": sha256_file(
            spreadsheet_structural_report_markdown_path
        ),
    }
    _validate_hash_field(
        decision,
        "approval_request_sha256",
        expected_hashes["approval_request_sha256"],
    )
    _validate_hash_field(
        decision,
        "final_job_manifest_sha256",
        expected_hashes["final_job_manifest_sha256"],
    )
    _validate_hash_field(
        decision,
        "spreadsheet_structural_report_json_sha256",
        expected_hashes["spreadsheet_structural_report_json_sha256"],
    )
    _validate_hash_field(
        decision,
        "spreadsheet_structural_report_md_sha256",
        expected_hashes["spreadsheet_structural_report_md_sha256"],
    )
    _validate_request_artifact_hashes(
        request_artifact_hashes,
        expected_hashes,
    )

    return OutputApprovalDecisionResult(
        approval_decision_path=decision_path,
        job_id=decision["job_id"],
        approved=True,
        approved_action=decision["approved_action"],
        human_reviewed=True,
        approval_request_sha256=expected_hashes["approval_request_sha256"],
        final_job_manifest_sha256=expected_hashes["final_job_manifest_sha256"],
        spreadsheet_structural_report_json_sha256=expected_hashes[
            "spreadsheet_structural_report_json_sha256"
        ],
        spreadsheet_structural_report_md_sha256=expected_hashes[
            "spreadsheet_structural_report_md_sha256"
        ],
        hash_binding_verified=True,
    )


def approval_request_sha256_excluding_self(approval_request_path: Path) -> str:
    approval_request_hash, _ = approval_request_hash_binding(
        approval_request_path
    )
    return approval_request_hash


def approval_request_hash_binding(approval_request_path: Path):
    request_path = Path(approval_request_path)
    if not request_path.exists():
        raise ValueError("approval_request_path is missing")
    if not request_path.is_file():
        raise ValueError("approval_request_path is not a file")
    request = _read_generated_json(request_path)
    if not isinstance(request, dict):
        raise ValueError("approval_request_json must be an object")
    stored_hash = request.get("approval_request_sha256_excluding_self")
    if not isinstance(stored_hash, str) or not stored_hash:
        raise ValueError("approval_request self hash is missing")
    request_without_self = dict(request)
    request_without_self.pop("approval_request_sha256_excluding_self", None)
    computed_hash = sha256_canonical_json(request_without_self)
    if stored_hash != computed_hash:
        raise ValueError("approval_request self hash mismatch")
    source_artifact_hashes = request.get("source_artifact_hashes")
    if not isinstance(source_artifact_hashes, dict):
        raise ValueError("approval_request source_artifact_hashes missing")
    return computed_hash, dict(source_artifact_hashes)


def _validate_request_inputs(job_path, request_path):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    if not request_path.parent.exists() or not request_path.parent.is_dir():
        raise ValueError("output_request_path parent is missing")


def _source_artifact_paths(job_path, manifest_artifacts):
    source_artifact_paths = {}
    if not isinstance(manifest_artifacts, dict):
        manifest_artifacts = {}
    for artifact_name, artifact_file in _APPROVED_SOURCE_ARTIFACTS.items():
        artifact_value = manifest_artifacts.get(
            artifact_name,
            (job_path / artifact_file).as_posix(),
        )
        source_artifact_paths[artifact_name] = Path(str(artifact_value))
    return source_artifact_paths


def _validate_decision_keys(decision):
    present_keys = set(decision)
    missing_keys = sorted(_DECISION_KEYS - present_keys)
    if missing_keys:
        raise ValueError(
            "approval_decision_json missing required keys: "
            + ", ".join(missing_keys)
        )
    extra_keys = sorted(present_keys - _DECISION_KEYS)
    if extra_keys:
        raise ValueError(
            "approval_decision_json has unsupported keys: "
            + ", ".join(extra_keys)
        )


def _validate_hash_field(decision, field_name, expected_hash):
    actual_hash = decision[field_name]
    if not isinstance(actual_hash, str) or not actual_hash:
        raise ValueError(f"approval_decision {field_name} is invalid")
    if actual_hash != expected_hash:
        raise ValueError(f"approval_decision {field_name} mismatch")


def _validate_request_artifact_hashes(request_artifact_hashes, expected_hashes):
    expected_request_hashes = {
        "final_job_manifest": expected_hashes["final_job_manifest_sha256"],
        "spreadsheet_structural_report_json": expected_hashes[
            "spreadsheet_structural_report_json_sha256"
        ],
        "spreadsheet_structural_report_markdown": expected_hashes[
            "spreadsheet_structural_report_md_sha256"
        ],
    }
    for artifact_name, expected_hash in expected_request_hashes.items():
        actual_hash = request_artifact_hashes.get(artifact_name)
        if actual_hash != expected_hash:
            raise ValueError(
                f"approval_request {artifact_name} hash mismatch"
            )


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
