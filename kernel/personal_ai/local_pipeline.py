"""End-to-end local-only non-authority Personal AI review pipeline."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.artifact_profiler import build_artifact_profile
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_file_intake import build_local_file_intake_ledger
from kernel.personal_ai.review_packet import build_review_packet
from kernel.personal_ai.work_order import build_work_order_proposal

__all__ = [
    "LocalReviewPipelineResult",
    "build_local_review_pipeline",
]


@dataclass(frozen=True)
class LocalReviewPipelineResult:
    input_dir: Path
    output_dir: Path
    intake_ledger_path: Path
    artifact_profile_path: Path
    work_order_proposal_path: Path
    review_packet_path: Path
    pipeline_manifest_path: Path
    files_recorded: int
    candidate_tasks: list[str]
    required_human_approval: bool


def build_local_review_pipeline(
    input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = False,
    include_hidden: bool = False,
) -> LocalReviewPipelineResult:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    _validate_pipeline_directories(input_path, output_path)

    intake_ledger_path = output_path / "intake_ledger.jsonl"
    artifact_profile_path = output_path / "artifact_profile.json"
    work_order_proposal_path = output_path / "work_order_proposal.json"
    review_packet_path = output_path / "review_packet.json"
    pipeline_manifest_path = output_path / "pipeline_manifest.json"

    intake_result = build_local_file_intake_ledger(
        input_path,
        intake_ledger_path,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    build_artifact_profile(
        intake_ledger_path,
        artifact_profile_path,
    )
    work_order_result = build_work_order_proposal(
        artifact_profile_path,
        work_order_proposal_path,
    )
    review_packet_result = build_review_packet(
        intake_ledger_path,
        artifact_profile_path,
        work_order_proposal_path,
        review_packet_path,
    )

    candidate_tasks = list(work_order_result.candidate_tasks)
    manifest = {
        "manifest_type": "personal_ai_local_review_pipeline_manifest",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "input_dir": input_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "artifacts": {
            "intake_ledger": intake_ledger_path.as_posix(),
            "artifact_profile": artifact_profile_path.as_posix(),
            "work_order_proposal": work_order_proposal_path.as_posix(),
            "review_packet": review_packet_path.as_posix(),
        },
        "candidate_tasks": candidate_tasks,
        "counts": {
            "files_seen": intake_result.files_seen,
            "files_recorded": intake_result.files_recorded,
            "bytes_recorded": intake_result.bytes_recorded,
            "candidate_tasks": len(candidate_tasks),
        },
        "boundaries": {
            "no_runtime_authority": True,
            "no_execution_capability": True,
            "no_external_tool_control": True,
            "no_network": True,
            "no_api_calls": True,
            "no_subprocess": True,
            "no_adapter_implementation": True,
            "no_input_file_mutation": True,
            "no_destructive_actions": True,
        },
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(pipeline_manifest_path, manifest)

    return LocalReviewPipelineResult(
        input_dir=input_path,
        output_dir=output_path,
        intake_ledger_path=intake_ledger_path,
        artifact_profile_path=artifact_profile_path,
        work_order_proposal_path=work_order_proposal_path,
        review_packet_path=review_packet_path,
        pipeline_manifest_path=pipeline_manifest_path,
        files_recorded=review_packet_result.files_recorded,
        candidate_tasks=candidate_tasks,
        required_human_approval=review_packet_result.required_human_approval,
    )


def _validate_pipeline_directories(input_path, output_path):
    if not input_path.exists():
        raise ValueError("input_dir is missing")
    if not input_path.is_dir():
        raise ValueError("input_dir is not a directory")
    if not output_path.exists():
        raise ValueError("output_dir is missing")
    if not output_path.is_dir():
        raise ValueError("output_dir is not a directory")
    if _path_is_inside(output_path, input_path):
        raise ValueError("output_dir must be outside input_dir")


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = candidate_path.resolve(strict=True)
    resolved_root = root_path.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True
