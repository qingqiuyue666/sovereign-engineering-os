"""Deterministic non-executing task routing for local Personal AI packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "TaskRouteResult",
    "build_task_route",
]

_CATEGORY_ORDER = (
    "spreadsheet",
    "document",
    "image",
    "video",
    "audio",
    "archive",
    "code",
    "unknown",
)

_ROUTE_PRIORITY = (
    ("mixed_file_inventory", "mixed_inventory_route"),
    ("spreadsheet_review", "spreadsheet_route"),
    ("document_review", "document_route"),
    ("media_inventory", "media_inventory_route"),
    ("code_inventory", "code_inventory_route"),
    ("archive_inventory", "archive_inventory_route"),
)

_PROCESSOR_LANES = {
    "spreadsheet_route": "spreadsheet_processor_planning_only",
    "document_route": "document_processor_planning_only",
    "media_inventory_route": "media_inventory_planning_only",
    "code_inventory_route": "code_inventory_planning_only",
    "archive_inventory_route": "archive_inventory_planning_only",
    "mixed_inventory_route": "mixed_file_inventory_planning_only",
    "unknown_inventory_route": "unknown_inventory_planning_only",
}

_ACTION_PLANS = {
    "spreadsheet_route": [
        "inspect spreadsheet-like artifacts",
        "prepare spreadsheet processor planning packet",
        "require human approval before any processing",
    ],
    "document_route": [
        "inspect document-like artifacts",
        "prepare document processor planning packet",
        "require human approval before any processing",
    ],
    "media_inventory_route": [
        "inspect media inventory artifacts",
        "prepare media inventory planning packet",
        "require human approval before any processing",
    ],
    "code_inventory_route": [
        "inspect code inventory artifacts",
        "prepare code inventory planning packet",
        "require human approval before any processing",
    ],
    "archive_inventory_route": [
        "inspect archive inventory artifacts",
        "prepare archive inventory planning packet",
        "require human approval before any processing",
    ],
    "mixed_inventory_route": [
        "inspect mixed artifact categories",
        "prepare mixed file inventory planning packet",
        "require human approval before any processing",
    ],
    "unknown_inventory_route": [
        "inspect unknown artifact categories",
        "prepare unknown inventory planning packet",
        "require human approval before any processing",
    ],
}

_FORBIDDEN_ACTIONS = [
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
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
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_destructive_actions",
]


@dataclass(frozen=True)
class TaskRouteResult:
    artifact_profile_path: Path
    work_order_path: Path
    output_task_route_path: Path
    route_type: str
    recommended_processor_lane: str
    candidate_tasks: list[str]
    required_human_approval: bool


def build_task_route(
    artifact_profile_path: Path,
    work_order_path: Path,
    output_task_route_path: Path,
) -> TaskRouteResult:
    profile_path = Path(artifact_profile_path)
    work_order_file = Path(work_order_path)
    output_path = Path(output_task_route_path)

    if not profile_path.exists():
        raise ValueError("artifact_profile_path is missing")
    if not work_order_file.exists():
        raise ValueError("work_order_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_task_route_path parent is missing")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    work_order = json.loads(work_order_file.read_text(encoding="utf-8"))

    if "categories" not in profile:
        raise ValueError("artifact_profile is missing categories")
    if "candidate_tasks" not in work_order:
        raise ValueError("work_order is missing candidate_tasks")

    category_counts = _category_counts(profile["categories"])
    candidate_tasks = [str(task) for task in work_order["candidate_tasks"]]
    route_type, route_reason = _select_route(candidate_tasks)
    recommended_processor_lane = _PROCESSOR_LANES[route_type]

    task_route = {
        "route_type": route_type,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "recommended_processor_lane": recommended_processor_lane,
        "source_artifacts": {
            "artifact_profile": profile_path.as_posix(),
            "work_order_proposal": work_order_file.as_posix(),
        },
        "candidate_tasks": candidate_tasks,
        "category_counts": category_counts,
        "route_reason": route_reason,
        "non_executing_action_plan": list(_ACTION_PLANS[route_type]),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "boundaries": list(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(output_path, task_route)

    return TaskRouteResult(
        artifact_profile_path=profile_path,
        work_order_path=work_order_file,
        output_task_route_path=output_path,
        route_type=route_type,
        recommended_processor_lane=recommended_processor_lane,
        candidate_tasks=candidate_tasks,
        required_human_approval=True,
    )


def _category_counts(categories):
    return {
        category: int(categories.get(category, 0))
        for category in _CATEGORY_ORDER
    }


def _select_route(candidate_tasks):
    task_set = set(candidate_tasks)
    for candidate_task, route_type in _ROUTE_PRIORITY:
        if candidate_task in task_set:
            return route_type, f"candidate_tasks contains {candidate_task}"
    return "unknown_inventory_route", "no known candidate task found"
