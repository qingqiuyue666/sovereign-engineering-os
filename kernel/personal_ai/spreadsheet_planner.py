"""Deterministic non-executing spreadsheet processor planning artifacts."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "SpreadsheetProcessorPlanResult",
    "build_spreadsheet_processor_plan",
]

_COMPATIBLE_ROUTE_TYPES = (
    "spreadsheet_route",
    "mixed_inventory_route",
)

_SPREADSHEET_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xlsm",
    ".xls",
}

_NON_EXECUTING_PLAN = [
    "review selected spreadsheet-like artifact inventory",
    "verify human approval before any spreadsheet content inspection",
    "choose future spreadsheet inspection processor only after approval",
    "preserve original input files unchanged",
    "produce future results only outside input directory",
]

_FORBIDDEN_ACTIONS = [
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "read_spreadsheet_cell_contents",
    "write_spreadsheet_outputs",
    "call_network",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
]

_BOUNDARIES = [
    "no_runtime_authority",
    "no_execution_capability",
    "no_external_tool_control",
    "no_network",
    "no_api_calls",
    "no_subprocess",
    "no_adapter_implementation",
    "no_ai_classification",
    "no_semantic_classification",
    "no_spreadsheet_content_read",
    "no_spreadsheet_output_write",
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_destructive_actions",
]


@dataclass(frozen=True)
class SpreadsheetProcessorPlanResult:
    artifact_profile_path: Path
    task_route_path: Path
    output_plan_path: Path
    plan_status: str
    observed_route_type: str
    artifact_count: int
    total_bytes: int
    required_human_approval: bool


def build_spreadsheet_processor_plan(
    artifact_profile_path: Path,
    task_route_path: Path,
    output_plan_path: Path,
) -> SpreadsheetProcessorPlanResult:
    profile_path = Path(artifact_profile_path)
    route_path = Path(task_route_path)
    output_path = Path(output_plan_path)

    if not profile_path.exists():
        raise ValueError("artifact_profile_path is missing")
    if not route_path.exists():
        raise ValueError("task_route_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_plan_path parent is missing")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    task_route = json.loads(route_path.read_text(encoding="utf-8"))

    if "entries" not in profile:
        raise ValueError("artifact_profile is missing entries")
    if "route_type" not in task_route:
        raise ValueError("task_route is missing route_type")

    observed_route_type = str(task_route["route_type"])
    recommended_processor_lane = str(
        task_route.get("recommended_processor_lane", "")
    )
    compatible_route = observed_route_type in _COMPATIBLE_ROUTE_TYPES
    selected_artifacts = (
        _selected_spreadsheet_artifacts(profile["entries"])
        if compatible_route
        else []
    )

    if not compatible_route:
        plan_status = "not_applicable"
        non_executing_plan = []
    elif not selected_artifacts:
        plan_status = "no_spreadsheet_artifacts"
        non_executing_plan = []
    else:
        plan_status = "planning_ready"
        non_executing_plan = list(_NON_EXECUTING_PLAN)

    artifact_count = len(selected_artifacts)
    total_bytes = sum(artifact["size_bytes"] for artifact in selected_artifacts)

    plan = {
        "plan_type": "personal_ai_local_spreadsheet_processor_plan",
        "plan_status": plan_status,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "source_artifacts": {
            "artifact_profile": profile_path.as_posix(),
            "task_route": route_path.as_posix(),
        },
        "compatible_route_types": list(_COMPATIBLE_ROUTE_TYPES),
        "observed_route_type": observed_route_type,
        "recommended_processor_lane": recommended_processor_lane,
        "selected_spreadsheet_artifacts": selected_artifacts,
        "artifact_count": artifact_count,
        "total_bytes": total_bytes,
        "non_executing_plan": non_executing_plan,
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "boundaries": list(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(output_path, plan)

    return SpreadsheetProcessorPlanResult(
        artifact_profile_path=profile_path,
        task_route_path=route_path,
        output_plan_path=output_path,
        plan_status=plan_status,
        observed_route_type=observed_route_type,
        artifact_count=artifact_count,
        total_bytes=total_bytes,
        required_human_approval=True,
    )


def _selected_spreadsheet_artifacts(entries):
    selected = [
        _selected_artifact_entry(entry)
        for entry in entries
        if _is_spreadsheet_like(entry)
    ]
    selected.sort(key=lambda entry: entry["relative_path"])
    return selected


def _is_spreadsheet_like(entry):
    extension = str(entry.get("extension", "")).lower()
    category = str(entry.get("category", ""))
    return extension in _SPREADSHEET_EXTENSIONS or category == "spreadsheet"


def _selected_artifact_entry(entry):
    return {
        "relative_path": str(entry["relative_path"]),
        "extension": str(entry["extension"]).lower(),
        "size_bytes": int(entry["size_bytes"]),
        "sha256": str(entry["sha256"]),
        "modified_time_ns": int(entry["modified_time_ns"]),
        "category": str(entry["category"]),
    }
