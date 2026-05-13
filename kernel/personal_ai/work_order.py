"""Non-executing work-order proposal generation for Personal AI planning."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "WorkOrderProposalResult",
    "build_work_order_proposal",
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


@dataclass(frozen=True)
class WorkOrderProposalResult:
    profile_path: Path
    output_work_order_path: Path
    candidate_tasks: list[str]
    required_human_approval: bool


def build_work_order_proposal(
    profile_path: Path,
    output_work_order_path: Path,
) -> WorkOrderProposalResult:
    profile_file = Path(profile_path)
    output_path = Path(output_work_order_path)

    if not profile_file.exists():
        raise ValueError("profile_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_work_order_path parent is missing")

    profile = json.loads(profile_file.read_text(encoding="utf-8"))
    categories = profile.get("categories", {})
    candidate_tasks = _candidate_tasks(categories)

    proposal = {
        "proposal_type": "personal_ai_local_work_order_proposal",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "input_profile": {
            "path": profile_file.as_posix(),
            "total_files": profile.get("total_files", 0),
            "total_bytes": profile.get("total_bytes", 0),
            "categories": {
                category: int(categories.get(category, 0))
                for category in _CATEGORY_ORDER
            },
        },
        "candidate_tasks": candidate_tasks,
        "required_human_approval": True,
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "summary": {
            "advisory_only": True,
            "proposal_executes_tasks": False,
            "proposal_modifies_files": False,
            "proposal_calls_apis": False,
        },
    }

    write_json_atomically(output_path, proposal)

    return WorkOrderProposalResult(
        profile_path=profile_file,
        output_work_order_path=output_path,
        candidate_tasks=candidate_tasks,
        required_human_approval=True,
    )


def _candidate_tasks(categories):
    tasks = []
    category_count = {
        category: int(categories.get(category, 0))
        for category in _CATEGORY_ORDER
    }

    if category_count["spreadsheet"] > 0:
        tasks.append("spreadsheet_review")
    if category_count["document"] > 0:
        tasks.append("document_review")
    if (
        category_count["image"] > 0
        or category_count["video"] > 0
        or category_count["audio"] > 0
    ):
        tasks.append("media_inventory")
    if category_count["code"] > 0:
        tasks.append("code_inventory")
    if category_count["archive"] > 0:
        tasks.append("archive_inventory")

    nonzero_categories = [
        category
        for category, count in category_count.items()
        if count > 0
    ]
    if len(nonzero_categories) > 1:
        tasks.append("mixed_file_inventory")
    if nonzero_categories == ["unknown"]:
        tasks.append("unknown_inventory")

    return tasks
