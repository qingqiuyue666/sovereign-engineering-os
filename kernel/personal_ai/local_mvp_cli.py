"""Safe CLI for the Personal AI local-only MVP runner."""

import argparse
import json
import sys
from pathlib import Path

from kernel.personal_ai.artifact_index import build_artifact_index
from kernel.personal_ai.failure_quarantine import write_failure_quarantine
from kernel.personal_ai.approval_gate import build_output_approval_request
from kernel.personal_ai.local_mvp_runner import (
    PersonalAILocalMVPResult,
    run_personal_ai_local_mvp,
)
from kernel.personal_ai.output_package import build_approved_output_package
from kernel.personal_ai.output_validator import build_approved_output_validation
from kernel.personal_ai.package_validator import build_job_package_validation
from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.adapters.xlsx_output_writer import (
    approve_xlsx_output,
    create_approved_xlsx_output,
    plan_xlsx_output,
    validate_xlsx_output,
)
from kernel.personal_ai.adapters.model_typed_schema_runtime import run_model_fixture

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
    "artifact_index.json",
    "artifact_index_manifest.json",
    "final_job_manifest.json",
    "job_summary.json",
    "human_next_steps.md",
    "job_package_validation.json",
]

_SUBCOMMANDS = {
    "run-local",
    "write-approval-request",
    "create-approved-output",
    "validate-job",
    "validate-output",
    "index-artifacts",
    "inspect-xlsx",
    "plan-xlsx-output",
    "approve-xlsx-output",
    "create-approved-xlsx-output",
    "validate-xlsx-output",
    "run-model-fixture",
}


def main(argv=None) -> int:
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv and effective_argv[0] in _SUBCOMMANDS:
        return _main_subcommand(effective_argv)
    return _main_run_local(effective_argv)


def _main_run_local(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_dir = Path(args.input_dir)
    output_root_dir = Path(args.output_root_dir)
    approval_mode = _approval_output_mode_requested(args)
    approval_request_mode = args.write_approval_request is not None

    if approval_mode and approval_request_mode:
        failure_path = _write_failure_if_possible(
            output_root_dir,
            job_id=args.job_id,
            error_type="ApprovalOutputPackageFlags",
            error_message="approval request mode cannot be combined with approval output package mode",
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
            verify_existing=approval_mode or approval_request_mode,
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

    if approval_request_mode:
        try:
            approval_request_result = build_output_approval_request(
                result.job_dir,
                Path(args.write_approval_request),
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
            approval_request_path=approval_request_result.output_request_path,
            approval_request_sha256=(
                approval_request_result.approval_request_sha256
            ),
        )
        return 0

    if approval_mode:
        try:
            output_package_result = build_approved_output_package(
                result.job_dir,
                Path(args.output_package_root_dir),
                Path(args.approval_decision),
                output_package_id=args.output_package_id,
                approval_request_path=Path(args.approval_request),
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


def _main_subcommand(argv) -> int:
    command = argv[0]
    if command == "run-local":
        return _main_run_local(argv[1:])

    parser = _build_subcommand_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "write-approval-request":
            result = build_output_approval_request(
                Path(args.job_dir),
                Path(args.output_path),
            )
            _print_command_payload(
                {
                    "complete": True,
                    "job_dir": Path(args.job_dir).as_posix(),
                    "approval_request_path": result.output_request_path.as_posix(),
                    "approval_request_sha256": result.approval_request_sha256,
                    "required_human_approval": True,
                }
            )
            return 0
        if args.command == "create-approved-output":
            result = build_approved_output_package(
                Path(args.job_dir),
                Path(args.output_package_root_dir),
                Path(args.approval_decision),
                output_package_id=args.output_package_id,
                approval_request_path=Path(args.approval_request),
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "job_dir": Path(args.job_dir).as_posix(),
                    "approved_output_package_dir": (
                        result.output_package_dir.as_posix()
                    ),
                    "approval_verified": result.approval_verified,
                    "output_package_missing_artifacts": (
                        result.missing_artifacts
                    ),
                    "approved_output_validation_path": (
                        result.approved_output_validation_path.as_posix()
                    ),
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.complete else 1
        if args.command == "validate-job":
            result = build_job_package_validation(
                Path(args.job_dir),
                _optional_path(args.output_path),
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "job_dir": result.job_dir.as_posix(),
                    "job_package_validation_path": (
                        result.output_validation_path.as_posix()
                    ),
                    "missing_artifacts": result.missing_artifacts,
                    "malformed_artifacts": result.malformed_artifacts,
                    "boundaries_verified": result.boundaries_verified,
                    "raw_sentinel_leakage_detected": (
                        result.raw_sentinel_leakage_detected
                    ),
                    "spreadsheet_output_files": result.spreadsheet_output_files,
                }
            )
            return 0 if result.complete else 1
        if args.command == "validate-output":
            result = build_approved_output_validation(
                Path(args.output_package_dir),
                _optional_path(args.output_path),
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "output_package_dir": result.output_package_dir.as_posix(),
                    "approved_output_validation_path": (
                        result.output_validation_path.as_posix()
                    ),
                    "missing_artifacts": result.missing_artifacts,
                    "malformed_artifacts": result.malformed_artifacts,
                    "manifest_hashes_verified": result.manifest_hashes_verified,
                    "approval_verified": result.approval_verified,
                    "provenance_verified": result.provenance_verified,
                    "boundaries_verified": result.boundaries_verified,
                    "raw_sentinel_leakage_detected": (
                        result.raw_sentinel_leakage_detected
                    ),
                    "spreadsheet_output_files": result.spreadsheet_output_files,
                }
            )
            return 0 if result.complete else 1
        if args.command == "index-artifacts":
            result = build_artifact_index(
                Path(args.job_dir),
                _optional_path(args.output_path),
                _optional_path(args.manifest_output_path),
            )
            _print_command_payload(
                {
                    "complete": True,
                    "job_dir": result.job_dir.as_posix(),
                    "artifact_index_path": result.artifact_index_path.as_posix(),
                    "artifact_index_manifest_path": (
                        result.artifact_index_manifest_path.as_posix()
                    ),
                    "indexed_artifacts": result.indexed_artifacts,
                    "required_human_approval": True,
                }
            )
            return 0
        if args.command == "inspect-xlsx":
            result = inspect_xlsx_readonly(
                Path(args.input_workbook),
                Path(args.output_dir),
            )
            _print_command_payload(
                {
                    "complete": True,
                    "input_workbook_path": result.input_workbook_path.as_posix(),
                    "output_dir": result.output_dir.as_posix(),
                    "xlsx_inspection_path": (
                        result.xlsx_inspection_path.as_posix()
                    ),
                    "xlsx_inspection_summary_path": (
                        result.xlsx_inspection_summary_path.as_posix()
                    ),
                    "input_sha256": result.input_sha256,
                    "sheet_count": result.sheet_count,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0
        if args.command == "plan-xlsx-output":
            result = plan_xlsx_output(
                Path(args.input_workbook),
                Path(args.xlsx_inspection),
                Path(args.output_dir),
                output_workbook_name=args.output_workbook_name,
            )
            _print_command_payload(
                {
                    "complete": True,
                    "xlsx_output_plan_path": result.plan_path.as_posix(),
                    "input_sha256": result.input_sha256,
                    "xlsx_inspection_sha256": result.xlsx_inspection_sha256,
                    "plan_sha256": result.plan_sha256,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0
        if args.command == "approve-xlsx-output":
            result = approve_xlsx_output(
                Path(args.plan_path),
                Path(args.output_path),
                approved=_parse_bool(args.approved),
                human_reviewed=_parse_bool(args.human_reviewed),
                reviewer_id=args.reviewer_id,
            )
            _print_command_payload(
                {
                    "complete": result.approved,
                    "xlsx_output_approval_path": result.approval_path.as_posix(),
                    "approved": result.approved,
                    "plan_sha256": result.plan_sha256,
                    "approval_sha256": result.approval_sha256,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.approved else 1
        if args.command == "create-approved-xlsx-output":
            result = create_approved_xlsx_output(
                Path(args.input_workbook),
                Path(args.plan_path),
                Path(args.approval_path),
                Path(args.output_dir),
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "output_workbook_path": result.output_workbook_path.as_posix(),
                    "xlsx_output_manifest_path": (
                        result.output_manifest_path.as_posix()
                    ),
                    "xlsx_output_delivery_summary_path": (
                        result.delivery_summary_path.as_posix()
                    ),
                    "xlsx_output_validation_path": (
                        result.validation_report_path.as_posix()
                    ),
                    "output_sha256": result.output_sha256,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.complete else 1
        if args.command == "validate-xlsx-output":
            result = validate_xlsx_output(
                Path(args.output_dir),
                _optional_path(args.output_path),
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "output_dir": result.output_dir.as_posix(),
                    "xlsx_output_validation_path": (
                        result.validation_report_path.as_posix()
                    ),
                    "manifest_hash_verified": result.manifest_hash_verified,
                    "output_workbook_exists": result.output_workbook_exists,
                    "raw_value_leakage_detected": (
                        result.raw_value_leakage_detected
                    ),
                    "required_human_approval": True,
                }
            )
            return 0 if result.complete else 1
        if args.command == "run-model-fixture":
            result = run_model_fixture(
                Path(args.request_path),
                Path(args.output_dir),
            )
            _print_command_payload(
                {
                    "complete": result.success,
                    "request_path": result.request_path.as_posix(),
                    "output_dir": result.output_dir.as_posix(),
                    "model_inference_artifact_path": None
                    if result.inference_artifact_path is None
                    else result.inference_artifact_path.as_posix(),
                    "model_failure_bundle_path": None
                    if result.failure_bundle_path is None
                    else result.failure_bundle_path.as_posix(),
                    "schema_name": result.schema_name,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.success else 1
    except ValueError as error:
        _print_command_payload(
            {
                "complete": False,
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "required_human_approval": True,
            }
        )
        return 1

    _print_command_payload(
        {
            "complete": False,
            "error_type": "UnsupportedCommand",
            "error_message": command,
            "required_human_approval": True,
        }
    )
    return 1


def _build_subcommand_parser():
    parser = argparse.ArgumentParser(
        description="Run safe Personal AI local v1 helper commands.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    approval_request_parser = subparsers.add_parser("write-approval-request")
    approval_request_parser.add_argument("--job-dir", required=True)
    approval_request_parser.add_argument("--output-path", required=True)

    approved_output_parser = subparsers.add_parser("create-approved-output")
    approved_output_parser.add_argument("--job-dir", required=True)
    approved_output_parser.add_argument("--approval-decision", required=True)
    approved_output_parser.add_argument("--approval-request", required=True)
    approved_output_parser.add_argument("--output-package-root-dir", required=True)
    approved_output_parser.add_argument("--output-package-id", required=True)

    validate_job_parser = subparsers.add_parser("validate-job")
    validate_job_parser.add_argument("--job-dir", required=True)
    validate_job_parser.add_argument("--output-path")

    validate_output_parser = subparsers.add_parser("validate-output")
    validate_output_parser.add_argument("--output-package-dir", required=True)
    validate_output_parser.add_argument("--output-path")

    index_parser = subparsers.add_parser("index-artifacts")
    index_parser.add_argument("--job-dir", required=True)
    index_parser.add_argument("--output-path")
    index_parser.add_argument("--manifest-output-path")

    inspect_xlsx_parser = subparsers.add_parser("inspect-xlsx")
    inspect_xlsx_parser.add_argument("--input-workbook", required=True)
    inspect_xlsx_parser.add_argument("--output-dir", required=True)

    plan_xlsx_parser = subparsers.add_parser("plan-xlsx-output")
    plan_xlsx_parser.add_argument("--input-workbook", required=True)
    plan_xlsx_parser.add_argument("--xlsx-inspection", required=True)
    plan_xlsx_parser.add_argument("--output-dir", required=True)
    plan_xlsx_parser.add_argument(
        "--output-workbook-name",
        default="derived_xlsx_summary.xlsx",
    )

    approve_xlsx_parser = subparsers.add_parser("approve-xlsx-output")
    approve_xlsx_parser.add_argument("--plan-path", required=True)
    approve_xlsx_parser.add_argument("--output-path", required=True)
    approve_xlsx_parser.add_argument("--approved", default="true")
    approve_xlsx_parser.add_argument("--human-reviewed", default="true")
    approve_xlsx_parser.add_argument(
        "--reviewer-id",
        default="local_human_review",
    )

    create_xlsx_parser = subparsers.add_parser("create-approved-xlsx-output")
    create_xlsx_parser.add_argument("--input-workbook", required=True)
    create_xlsx_parser.add_argument("--plan-path", required=True)
    create_xlsx_parser.add_argument("--approval-path", required=True)
    create_xlsx_parser.add_argument("--output-dir", required=True)

    validate_xlsx_parser = subparsers.add_parser("validate-xlsx-output")
    validate_xlsx_parser.add_argument("--output-dir", required=True)
    validate_xlsx_parser.add_argument("--output-path")

    model_fixture_parser = subparsers.add_parser("run-model-fixture")
    model_fixture_parser.add_argument("--request-path", required=True)
    model_fixture_parser.add_argument("--output-dir", required=True)

    return parser


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
    parser.add_argument("--approval-request")
    parser.add_argument("--output-package-root-dir")
    parser.add_argument("--output-package-id")
    parser.add_argument("--write-approval-request")
    return parser


def _approval_output_mode_requested(args):
    return any(
        value is not None
        for value in (
            args.approval_decision,
            args.approval_request,
            args.output_package_root_dir,
            args.output_package_id,
        )
    )


def _approval_output_flags_complete(args):
    return all(
        value is not None
        for value in (
            args.approval_decision,
            args.approval_request,
            args.output_package_root_dir,
            args.output_package_id,
        )
    )


def _optional_path(value):
    if value is None:
        return None
    return Path(value)


def _parse_bool(value):
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("boolean argument must be true or false")


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


def _print_command_payload(payload):
    print(json.dumps(payload, sort_keys=True))


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
    approval_request_path=None,
    approval_request_sha256=None,
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
        approved_output_validation_path = (
            Path(approved_output_package_dir) / "approved_output_validation.json"
        )
        if approved_output_validation_path.exists():
            payload["approved_output_validation_path"] = (
                approved_output_validation_path.as_posix()
            )
    if approval_verified is not None:
        payload["approval_verified"] = bool(approval_verified)
    if output_package_complete is not None:
        payload["output_package_complete"] = bool(output_package_complete)
    if output_package_missing_artifacts is not None:
        payload["output_package_missing_artifacts"] = list(
            output_package_missing_artifacts
        )
    if approval_request_path is not None:
        payload["approval_request_path"] = Path(approval_request_path).as_posix()
    if approval_request_sha256 is not None:
        payload["approval_request_sha256"] = approval_request_sha256
    if failure_quarantine_path is not None:
        payload["failure_quarantine_path"] = failure_quarantine_path
    if job_dir is not None:
        supplemental_paths = {
            "artifact_index_path": "artifact_index.json",
            "artifact_index_manifest_path": "artifact_index_manifest.json",
            "job_package_validation_path": "job_package_validation.json",
        }
        for payload_key, artifact_file in supplemental_paths.items():
            supplemental_path = Path(job_dir) / artifact_file
            if supplemental_path.exists():
                payload[payload_key] = supplemental_path.as_posix()
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
