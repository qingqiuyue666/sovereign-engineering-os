"""Deterministic final manifest for Personal AI local v1 job packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "FinalJobManifestResult",
    "build_final_job_manifest",
]

_FINAL_ARTIFACT_FILES = {
    "input_snapshot": "input_snapshot.json",
    "intake_ledger": "intake_ledger.jsonl",
    "artifact_profile": "artifact_profile.json",
    "work_order_proposal": "work_order_proposal.json",
    "review_packet": "review_packet.json",
    "pipeline_manifest": "pipeline_manifest.json",
    "task_route": "task_route.json",
    "spreadsheet_processor_plan": "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection": "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan": "spreadsheet_report_plan.json",
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
    "artifact_index": "artifact_index.json",
    "artifact_index_manifest": "artifact_index_manifest.json",
    "final_job_manifest": "final_job_manifest.json",
    "job_summary": "job_summary.json",
    "human_next_steps": "human_next_steps.md",
}

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_ai_classification": True,
    "no_semantic_classification": True,
    "no_spreadsheet_output_write": True,
    "no_spreadsheet_cleaning": True,
    "no_spreadsheet_transformation": True,
    "no_issue_severity_assignment": True,
    "no_business_semantic_interpretation": True,
    "no_input_file_mutation": True,
    "no_input_content_copy": True,
    "no_raw_cell_value_copy": True,
    "no_destructive_actions": True,
}

_FORBIDDEN_ACTIONS = [
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "write_spreadsheet_outputs",
    "clean_spreadsheets",
    "transform_spreadsheets",
    "copy_raw_cell_values",
    "infer_semantic_meaning",
    "assign_issue_severity",
    "perform_business_semantic_interpretation",
    "call_network",
    "call_api",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
]


@dataclass(frozen=True)
class FinalJobManifestResult:
    job_dir: Path
    output_manifest_path: Path
    complete: bool
    missing_artifacts: list[str]
    route_type: str
    recommended_processor_lane: str
    spreadsheet_plan_status: str
    spreadsheet_report_status: str
    spreadsheet_structural_report_status: str
    required_human_approval: bool


def build_final_job_manifest(
    job_dir: Path,
    output_manifest_path: Path,
) -> FinalJobManifestResult:
    job_path = Path(job_dir)
    manifest_path = Path(output_manifest_path)
    _validate_manifest_inputs(job_path, manifest_path)

    artifacts = {
        artifact_name: (job_path / artifact_file).as_posix()
        for artifact_name, artifact_file in _FINAL_ARTIFACT_FILES.items()
    }
    artifact_presence = {
        artifact_name: _artifact_is_present(
            job_path,
            manifest_path,
            artifact_name,
            artifact_file,
        )
        for artifact_name, artifact_file in _FINAL_ARTIFACT_FILES.items()
    }
    missing_artifacts = [
        artifact_file
        for artifact_name, artifact_file in _FINAL_ARTIFACT_FILES.items()
        if not artifact_presence[artifact_name]
    ]

    task_route = _read_generated_json(job_path / "task_route.json")
    spreadsheet_plan = _read_generated_json(
        job_path / "spreadsheet_processor_plan.json"
    )
    spreadsheet_report_plan = _read_generated_json(
        job_path / "spreadsheet_report_plan.json"
    )
    spreadsheet_structural_report = _read_generated_json(
        job_path / "spreadsheet_structural_report.json"
    )
    job_summary = _read_generated_json(job_path / "job_summary.json")

    complete = not missing_artifacts
    manifest = {
        "manifest_type": "personal_ai_local_v1_final_job_manifest",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "job_dir": job_path.as_posix(),
        "artifacts": artifacts,
        "artifact_presence": artifact_presence,
        "complete": complete,
        "missing_artifacts": missing_artifacts,
        "route_type": str(task_route.get("route_type", "missing_source_artifact")),
        "recommended_processor_lane": str(
            task_route.get("recommended_processor_lane", "missing_source_artifact")
        ),
        "spreadsheet_plan_status": str(
            spreadsheet_plan.get("plan_status", "missing_source_artifact")
        ),
        "spreadsheet_report_status": str(
            spreadsheet_report_plan.get("report_status", "missing_source_artifact")
        ),
        "spreadsheet_structural_report_status": str(
            spreadsheet_structural_report.get(
                "report_status",
                "missing_source_artifact",
            )
        ),
        "boundaries": _manifest_boundaries(job_summary),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(manifest_path, manifest)

    return FinalJobManifestResult(
        job_dir=job_path,
        output_manifest_path=manifest_path,
        complete=complete,
        missing_artifacts=missing_artifacts,
        route_type=manifest["route_type"],
        recommended_processor_lane=manifest["recommended_processor_lane"],
        spreadsheet_plan_status=manifest["spreadsheet_plan_status"],
        spreadsheet_report_status=manifest["spreadsheet_report_status"],
        spreadsheet_structural_report_status=(
            manifest["spreadsheet_structural_report_status"]
        ),
        required_human_approval=True,
    )


def _validate_manifest_inputs(job_path, manifest_path):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    if not manifest_path.parent.exists() or not manifest_path.parent.is_dir():
        raise ValueError("output_manifest_path parent is missing")
    if manifest_path.parent.resolve(strict=True) != job_path.resolve(strict=True):
        raise ValueError("output_manifest_path must be in job_dir")


def _artifact_is_present(job_path, manifest_path, artifact_name, artifact_file):
    expected_path = job_path / artifact_file
    if artifact_name == "final_job_manifest":
        return manifest_path == expected_path
    return expected_path.exists()


def _read_generated_json(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        return {}
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def _manifest_boundaries(job_summary):
    summary_boundaries = job_summary.get("boundaries")
    if isinstance(summary_boundaries, dict):
        merged_boundaries = dict(_BOUNDARIES)
        for key in sorted(summary_boundaries):
            merged_boundaries[str(key)] = bool(summary_boundaries[key])
        return merged_boundaries
    return dict(_BOUNDARIES)
