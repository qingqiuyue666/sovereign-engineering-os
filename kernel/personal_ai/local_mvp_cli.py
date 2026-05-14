"""Safe CLI for the Personal AI local-only MVP runner."""

import argparse
import json
from pathlib import Path

from kernel.personal_ai.failure_quarantine import write_failure_quarantine
from kernel.personal_ai.local_mvp_runner import (
    PersonalAILocalMVPResult,
    run_personal_ai_local_mvp,
)
from kernel.personal_ai.output_package import build_approved_output_package

__all__ = [
    "main",
]

_REQUIRED_JOB_ARTIFACTS = [
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


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_dir = Path(args.input_dir)
    output_root_dir = Path(args.output_root_dir)
    approval_mode = _approval_output_mode_requested(args)

    if approval_mode and not _approval_output_flags_complete(args):
        failure_path = _write_failure_if_possible(
            output_root_dir,
            job_id=args.job_id,
            error_type="ApprovalOutputPackageFlags",
            error_message="approval output package mode requires all approval flags",
        )
        _print_result(
            job_dir=None,
            complete=False,
            missing_artifacts=[],
            required_human_approval=True,
            approval_verified=False,
            output_package_complete=False,
            failure_quarantine_path=failure_path,
        )
        return 1

    try:
        result = _run_or_verify_local_mvp(
            input_dir,
            output_root_dir,
            job_id=args.job_id,
            recursive=args.recursive,
            include_hidden=args.include_hidden,
            verify_existing=approval_mode,
        )
    except ValueError as error:
        failure_path = _write_failure_if_possible(
            output_root_dir,
            job_id=args.job_id,
            error_type=error.__class__.__name__,
            error_message=str(error),
        )
        _print_result(
            job_dir=None,
            complete=False,
            missing_artifacts=[],
            required_human_approval=True,
            approval_verified=False if approval_mode else None,
            output_package_complete=False if approval_mode else None,
            failure_quarantine_path=failure_path,
        )
        return 1

    if not result.complete:
        failure_path = _write_failure_if_possible(
            output_root_dir,
            job_id=args.job_id,
            error_type="IncompletePackage",
            error_message="local MVP package is missing required artifacts",
        )
        _print_result(
            job_dir=result.job_dir,
            complete=False,
            missing_artifacts=result.missing_artifacts,
            required_human_approval=result.required_human_approval,
            approval_verified=False if approval_mode else None,
            output_package_complete=False if approval_mode else None,
            failure_quarantine_path=failure_path,
        )
        return 1

    if approval_mode:
        try:
            output_package_result = build_approved_output_package(
                result.job_dir,
                Path(args.output_package_root_dir),
                Path(args.approval_decision),
                output_package_id=args.output_package_id,
            )
        except ValueError as error:
            failure_path = _write_failure_if_possible(
                output_root_dir,
                job_id=args.job_id,
                error_type=error.__class__.__name__,
                error_message=str(error),
            )
            _print_result(
                job_dir=result.job_dir,
                complete=True,
                missing_artifacts=result.missing_artifacts,
                required_human_approval=result.required_human_approval,
                approval_verified=False,
                output_package_complete=False,
                failure_quarantine_path=failure_path,
            )
            return 1

        _print_result(
            job_dir=result.job_dir,
            complete=True,
            missing_artifacts=result.missing_artifacts,
            required_human_approval=result.required_human_approval,
            approved_output_package_dir=output_package_result.output_package_dir,
            approval_verified=output_package_result.approval_verified,
            output_package_complete=output_package_result.complete,
            output_package_missing_artifacts=(
                output_package_result.missing_artifacts
            ),
        )
        return 0 if output_package_result.complete else 1

    _print_result(
        job_dir=result.job_dir,
        complete=True,
        missing_artifacts=result.missing_artifacts,
        required_human_approval=result.required_human_approval,
    )
    return 0


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Run the Personal AI local-only MVP safely.",
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-root-dir", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument("--approval-decision")
    parser.add_argument("--output-package-root-dir")
    parser.add_argument("--output-package-id")
    return parser


def _approval_output_mode_requested(args):
    return any(
        value is not None
        for value in (
            args.approval_decision,
            args.output_package_root_dir,
            args.output_package_id,
        )
    )


def _approval_output_flags_complete(args):
    return all(
        value is not None
        for value in (
            args.approval_decision,
            args.output_package_root_dir,
            args.output_package_id,
        )
    )


def _run_or_verify_local_mvp(
    input_dir,
    output_root_dir,
    *,
    job_id,
    recursive,
    include_hidden,
    verify_existing,
):
    try:
        return run_personal_ai_local_mvp(
            input_dir,
            output_root_dir,
            job_id=job_id,
            recursive=recursive,
            include_hidden=include_hidden,
        )
    except ValueError as error:
        if not verify_existing or str(error) != "job_dir already exists":
            raise
    return _verify_existing_local_mvp_job(output_root_dir, job_id=job_id)


def _verify_existing_local_mvp_job(output_root_dir, *, job_id):
    output_root_path = Path(output_root_dir)
    job_dir = output_root_path / job_id
    if not job_dir.exists():
        raise ValueError("job_dir is missing")
    if not job_dir.is_dir():
        raise ValueError("job_dir is not a directory")

    missing_artifacts = [
        artifact_name
        for artifact_name in _REQUIRED_JOB_ARTIFACTS
        if not (job_dir / artifact_name).exists()
    ]
    missing_artifacts.sort()

    return PersonalAILocalMVPResult(
        job_id=job_id,
        job_dir=job_dir,
        required_artifacts=list(_REQUIRED_JOB_ARTIFACTS),
        missing_artifacts=missing_artifacts,
        complete=not missing_artifacts,
        required_human_approval=True,
    )


def _write_failure_if_possible(
    output_root_dir,
    *,
    job_id,
    error_type,
    error_message,
):
    output_root_path = Path(output_root_dir)
    if not output_root_path.exists() or not output_root_path.is_dir():
        return None
    try:
        result = write_failure_quarantine(
            output_root_path,
            job_id=job_id,
            error_type=error_type,
            error_message=error_message,
        )
    except ValueError:
        return None
    return result.quarantine_dir.as_posix()


def _print_result(
    *,
    job_dir,
    complete,
    missing_artifacts,
    required_human_approval,
    approved_output_package_dir=None,
    approval_verified=None,
    output_package_complete=None,
    output_package_missing_artifacts=None,
    failure_quarantine_path=None,
):
    payload = {
        "job_dir": None if job_dir is None else Path(job_dir).as_posix(),
        "complete": bool(complete),
        "missing_artifacts": list(missing_artifacts),
        "required_human_approval": bool(required_human_approval),
    }
    if approved_output_package_dir is not None:
        payload["approved_output_package_dir"] = (
            Path(approved_output_package_dir).as_posix()
        )
    if approval_verified is not None:
        payload["approval_verified"] = bool(approval_verified)
    if output_package_complete is not None:
        payload["output_package_complete"] = bool(output_package_complete)
    if output_package_missing_artifacts is not None:
        payload["output_package_missing_artifacts"] = list(
            output_package_missing_artifacts
        )
    if failure_quarantine_path is not None:
        payload["failure_quarantine_path"] = failure_quarantine_path
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
