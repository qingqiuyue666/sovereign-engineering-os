"""Approved output package manifest for Personal AI local v1."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ApprovedOutputManifestResult",
    "build_approved_output_manifest",
]

_REQUIRED_OUTPUT_FILES = {
    "approved_output_manifest": "approved_output_manifest.json",
    "delivery_summary": "delivery_summary.json",
    "approval_receipt": "approval_receipt.json",
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


def build_approved_output_manifest(
    output_package_dir: Path,
    output_manifest_path: Path,
) -> ApprovedOutputManifestResult:
    package_path = Path(output_package_dir)
    manifest_path = Path(output_manifest_path)
    _validate_manifest_inputs(package_path, manifest_path)

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
    complete = not missing_artifacts

    write_json_atomically(
        manifest_path,
        {
            "manifest_type": "personal_ai_local_v1_approved_output_manifest",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "output_package_dir": package_path.as_posix(),
            "artifacts": artifacts,
            "artifact_presence": artifact_presence,
            "complete": complete,
            "missing_artifacts": missing_artifacts,
            "approval_verified": approval_verified,
            "boundaries": dict(_BOUNDARIES),
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "next_allowed_action": "human_review_only",
        },
    )

    return ApprovedOutputManifestResult(
        output_package_dir=package_path,
        output_manifest_path=manifest_path,
        complete=complete,
        missing_artifacts=missing_artifacts,
        approval_verified=approval_verified,
    )


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


def _artifact_is_present(package_path, manifest_path, artifact_name, artifact_file):
    expected_path = package_path / artifact_file
    if artifact_name == "approved_output_manifest":
        return manifest_path == expected_path
    return expected_path.exists()


def _approval_receipt_verified(receipt_path):
    if not receipt_path.exists():
        return False
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        return False
    return receipt.get("approval_verified") is True
