"""Deterministic local-only non-authority Personal AI job package builder."""

from dataclasses import dataclass
from pathlib import Path
import json
import re

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_pipeline import build_local_review_pipeline
from kernel.personal_ai.task_router import build_task_route

__all__ = [
    "LocalJobPackageResult",
    "build_local_job_package",
]

_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_ARTIFACT_FILES = {
    "input_snapshot": "input_snapshot.json",
    "intake_ledger": "intake_ledger.jsonl",
    "artifact_profile": "artifact_profile.json",
    "work_order_proposal": "work_order_proposal.json",
    "review_packet": "review_packet.json",
    "pipeline_manifest": "pipeline_manifest.json",
    "task_route": "task_route.json",
    "job_summary": "job_summary.json",
    "human_next_steps": "human_next_steps.md",
}

_BOUNDARIES = {
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_ai_classification": True,
    "no_semantic_classification": True,
    "no_input_file_mutation": True,
    "no_input_content_copy": True,
    "no_destructive_actions": True,
}

_FORBIDDEN_ACTIONS = (
    "modify input files",
    "delete input files",
    "move input files",
    "rename input files",
    "execute files",
    "call network",
    "call AI APIs",
    "run subprocess",
    "control external tools",
)


@dataclass(frozen=True)
class LocalJobPackageResult:
    job_id: str
    input_dir: Path
    output_root_dir: Path
    job_dir: Path
    input_snapshot_path: Path
    intake_ledger_path: Path
    artifact_profile_path: Path
    work_order_proposal_path: Path
    review_packet_path: Path
    pipeline_manifest_path: Path
    task_route_path: Path
    job_summary_path: Path
    human_next_steps_path: Path
    files_recorded: int
    candidate_tasks: list[str]
    route_type: str
    recommended_processor_lane: str
    required_human_approval: bool


def build_local_job_package(
    input_dir: Path,
    output_root_dir: Path,
    *,
    job_id: str,
    recursive: bool = False,
    include_hidden: bool = False,
) -> LocalJobPackageResult:
    input_path = Path(input_dir)
    output_root_path = Path(output_root_dir)
    _validate_job_package_inputs(input_path, output_root_path, job_id)

    job_dir = output_root_path / job_id
    if job_dir.exists():
        raise ValueError("job_dir already exists")

    job_dir.mkdir()

    input_snapshot_path = job_dir / _ARTIFACT_FILES["input_snapshot"]
    intake_ledger_path = job_dir / _ARTIFACT_FILES["intake_ledger"]
    artifact_profile_path = job_dir / _ARTIFACT_FILES["artifact_profile"]
    work_order_proposal_path = job_dir / _ARTIFACT_FILES["work_order_proposal"]
    review_packet_path = job_dir / _ARTIFACT_FILES["review_packet"]
    pipeline_manifest_path = job_dir / _ARTIFACT_FILES["pipeline_manifest"]
    task_route_path = job_dir / _ARTIFACT_FILES["task_route"]
    job_summary_path = job_dir / _ARTIFACT_FILES["job_summary"]
    human_next_steps_path = job_dir / _ARTIFACT_FILES["human_next_steps"]

    write_json_atomically(
        input_snapshot_path,
        {
            "snapshot_type": "personal_ai_local_input_snapshot",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "input_dir": input_path.as_posix(),
            "recursive": recursive,
            "include_hidden": include_hidden,
            "captured_by": "metadata_hash_only",
            "input_file_contents_copied": False,
            "input_mutation_performed": False,
        },
    )

    pipeline_result = build_local_review_pipeline(
        input_path,
        job_dir,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    candidate_tasks = list(pipeline_result.candidate_tasks)
    pipeline_manifest = _read_generated_json(pipeline_result.pipeline_manifest_path)
    task_route_result = build_task_route(
        artifact_profile_path,
        work_order_proposal_path,
        task_route_path,
    )

    artifacts = {
        "input_snapshot": input_snapshot_path.as_posix(),
        "intake_ledger": intake_ledger_path.as_posix(),
        "artifact_profile": artifact_profile_path.as_posix(),
        "work_order_proposal": work_order_proposal_path.as_posix(),
        "review_packet": review_packet_path.as_posix(),
        "pipeline_manifest": pipeline_manifest_path.as_posix(),
        "task_route": task_route_path.as_posix(),
        "job_summary": job_summary_path.as_posix(),
        "human_next_steps": human_next_steps_path.as_posix(),
    }
    counts = dict(pipeline_manifest.get("counts", {}))
    counts["job_artifacts"] = len(artifacts)

    write_json_atomically(
        job_summary_path,
        {
            "summary_type": "personal_ai_local_job_summary",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "job_id": job_id,
            "job_dir": job_dir.as_posix(),
            "input_dir": input_path.as_posix(),
            "artifacts": artifacts,
            "counts": counts,
            "candidate_tasks": candidate_tasks,
            "route_type": task_route_result.route_type,
            "recommended_processor_lane": (
                task_route_result.recommended_processor_lane
            ),
            "required_human_approval": True,
            "boundaries": dict(_BOUNDARIES),
            "next_allowed_action": "human_review_only",
        },
    )
    human_next_steps_path.write_text(
        _render_human_next_steps(
            job_id,
            artifacts,
            candidate_tasks,
            task_route_result.route_type,
            task_route_result.recommended_processor_lane,
        ),
        encoding="utf-8",
    )

    return LocalJobPackageResult(
        job_id=job_id,
        input_dir=input_path,
        output_root_dir=output_root_path,
        job_dir=job_dir,
        input_snapshot_path=input_snapshot_path,
        intake_ledger_path=intake_ledger_path,
        artifact_profile_path=artifact_profile_path,
        work_order_proposal_path=work_order_proposal_path,
        review_packet_path=review_packet_path,
        pipeline_manifest_path=pipeline_manifest_path,
        task_route_path=task_route_path,
        job_summary_path=job_summary_path,
        human_next_steps_path=human_next_steps_path,
        files_recorded=pipeline_result.files_recorded,
        candidate_tasks=candidate_tasks,
        route_type=task_route_result.route_type,
        recommended_processor_lane=task_route_result.recommended_processor_lane,
        required_human_approval=True,
    )


def _validate_job_package_inputs(input_path, output_root_path, job_id):
    if not input_path.exists():
        raise ValueError("input_dir is missing")
    if not input_path.is_dir():
        raise ValueError("input_dir is not a directory")
    if not output_root_path.exists():
        raise ValueError("output_root_dir is missing")
    if not output_root_path.is_dir():
        raise ValueError("output_root_dir is not a directory")
    if _path_is_inside(output_root_path, input_path):
        raise ValueError("output_root_dir must be outside input_dir")
    if not _valid_job_id(job_id):
        raise ValueError("job_id is invalid")


def _valid_job_id(job_id):
    if not isinstance(job_id, str):
        return False
    if not job_id:
        return False
    if job_id.startswith("."):
        return False
    if "/" in job_id or "\\" in job_id:
        return False
    if ".." in job_id:
        return False
    return bool(_JOB_ID_PATTERN.fullmatch(job_id))


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = candidate_path.resolve(strict=True)
    resolved_root = root_path.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def _read_generated_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _render_human_next_steps(
    job_id,
    artifacts,
    candidate_tasks,
    route_type,
    recommended_processor_lane,
):
    lines = [
        "# Personal AI Local Job Package Review",
        "",
        f"- job id: {job_id}",
        "- authority: non_authority",
        "- execution capability: not_introduced",
        "- required human approval: true",
        "- next allowed action: human_review_only",
        f"- route type: {route_type}",
        f"- recommended processor lane: {recommended_processor_lane}",
        "",
        "## Generated artifacts",
    ]
    for artifact_name in _ARTIFACT_FILES:
        lines.append(f"- {artifact_name}: {Path(artifacts[artifact_name]).name}")

    lines.extend(["", "## Candidate tasks"])
    if candidate_tasks:
        for task in candidate_tasks:
            lines.append(f"- {task}")
    else:
        lines.append("- none")

    lines.extend(["", "## Explicit forbidden actions"])
    for action in _FORBIDDEN_ACTIONS:
        lines.append(f"- {action}")

    lines.extend(["", "## Next allowed action", "", "human_review_only", ""])
    return "\n".join(lines)
