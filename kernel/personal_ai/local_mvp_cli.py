"""Safe CLI for the Personal AI local-only MVP runner."""

import argparse
import json
from pathlib import Path

from kernel.personal_ai.failure_quarantine import write_failure_quarantine
from kernel.personal_ai.local_mvp_runner import run_personal_ai_local_mvp

__all__ = [
    "main",
]


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_dir = Path(args.input_dir)
    output_root_dir = Path(args.output_root_dir)

    try:
        result = run_personal_ai_local_mvp(
            input_dir,
            output_root_dir,
            job_id=args.job_id,
            recursive=args.recursive,
            include_hidden=args.include_hidden,
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
            failure_quarantine_path=failure_path,
        )
        return 1

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
    return parser


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
    failure_quarantine_path=None,
):
    payload = {
        "job_dir": None if job_dir is None else Path(job_dir).as_posix(),
        "complete": bool(complete),
        "missing_artifacts": list(missing_artifacts),
        "required_human_approval": bool(required_human_approval),
    }
    if failure_quarantine_path is not None:
        payload["failure_quarantine_path"] = failure_quarantine_path
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
