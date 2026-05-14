"""Function-level local-only Personal AI MVP runner."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.job_package import build_local_job_package, validate_job_id

__all__ = [
    "PersonalAILocalMVPResult",
    "run_personal_ai_local_mvp",
]

_REQUIRED_ARTIFACTS = [
    "input_snapshot.json",
    "intake_ledger.jsonl",
    "artifact_profile.json",
    "work_order_proposal.json",
    "review_packet.json",
    "pipeline_manifest.json",
    "task_route.json",
    "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "final_job_manifest.json",
    "job_summary.json",
    "human_next_steps.md",
]


@dataclass(frozen=True)
class PersonalAILocalMVPResult:
    job_id: str
    job_dir: Path
    required_artifacts: list[str]
    missing_artifacts: list[str]
    complete: bool
    required_human_approval: bool


def run_personal_ai_local_mvp(
    input_dir: Path,
    output_root_dir: Path,
    *,
    job_id: str,
    recursive: bool = False,
    include_hidden: bool = False,
) -> PersonalAILocalMVPResult:
    input_path = Path(input_dir)
    output_root_path = Path(output_root_dir)

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
    validate_job_id(job_id)

    job_package_result = build_local_job_package(
        input_path,
        output_root_path,
        job_id=job_id,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    missing_artifacts = [
        artifact_name
        for artifact_name in _REQUIRED_ARTIFACTS
        if not (job_package_result.job_dir / artifact_name).exists()
    ]
    missing_artifacts.sort()

    return PersonalAILocalMVPResult(
        job_id=job_id,
        job_dir=job_package_result.job_dir,
        required_artifacts=list(_REQUIRED_ARTIFACTS),
        missing_artifacts=missing_artifacts,
        complete=not missing_artifacts,
        required_human_approval=job_package_result.required_human_approval,
    )


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = candidate_path.resolve(strict=True)
    resolved_root = root_path.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True
