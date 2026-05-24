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
from kernel.personal_ai.local_launcher import (
    run_browser_fixture_launcher,
    run_browser_runtime_dry_run_launcher,
    run_blender_dry_run_launcher,
    run_comfyui_dry_run_launcher,
    run_creative_handoff_launcher,
    run_github_capability_intake_packet_launcher,
    run_local_asset_bounded_smoke_iteration_launcher,
    run_local_asset_bounded_smoke_cycle_contract_launcher,
    run_local_asset_bounded_smoke_cycle_human_review_launcher,
    run_local_asset_human_smoke_launcher,
    run_local_asset_iteration_promotion_gate_launcher,
    run_local_asset_next_bounded_smoke_iteration_admission_launcher,
    run_local_asset_next_bounded_smoke_iteration_execution_request_launcher,
    run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_launcher,
    run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_launcher,
    run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_launcher,
    run_local_asset_next_bounded_smoke_iteration_run_review_packet_launcher,
    run_local_asset_next_bounded_smoke_iteration_runner_admission_launcher,
    run_local_asset_next_bounded_smoke_iteration_runner_launcher,
    run_local_asset_scan_launcher,
    run_local_asset_smoke_promotion_gate_launcher,
    run_local_asset_smoke_iteration_review_packet_launcher,
    run_local_asset_smoke_readiness_launcher,
    run_local_asset_smoke_review_packet_launcher,
    run_local_office_launcher,
    run_local_only_playwright_fixture_scenario_suite_launcher,
    run_playwright_local_admission_receipt_aggregation_launcher,
    run_model_fixture_launcher,
    run_model_provider_dry_run_launcher,
    run_bounded_playwright_worker_adapter_draft_launcher,
    run_local_fixture_adapter_dry_run_invocation_plan_launcher,
    run_local_fixture_adapter_execution_gate_plan_launcher,
    run_local_fixture_human_approval_artifact_launcher,
    run_local_fixture_playwright_adapter_admission_gate_launcher,
    run_local_fixture_runner_contract_draft_launcher,
    run_local_fixture_runner_receipt_contract_draft_launcher,
    run_local_fixture_runner_receipt_metadata_artifact_launcher,
    run_local_fixture_runner_receipt_preflight_verifier_launcher,
    run_local_fixture_runner_stub_admission_gate_launcher,
    run_local_fixture_adapter_usage_receipt_launcher,
    run_operator_provided_playwright_execution_receipt_launcher,
    run_playwright_local_fixture_sandbox_smoke_launcher,
    run_product_health_check_launcher,
    run_runtime_delivery_validation_launcher,
    run_admission_gated_local_adapter_registry_promotion_launcher,
    run_task_graph_launcher,
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
from kernel.personal_ai.adapters.browser_fixture_runtime import (
    run_browser_fixture_from_actions_file,
)
from kernel.personal_ai.adapters.adapter_registry import (
    DEFAULT_ADAPTER_REGISTRY,
    validate_adapter_registry_entry,
)
from kernel.personal_ai.adapters.tool_intake_register import (
    validate_runtime_tool_admission_register_file,
)
from kernel.personal_ai.runtime_delivery_package import (
    validate_runtime_delivery_package,
)
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from kernel.personal_ai.io_utils import write_json_atomically

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
    "run-browser-fixture",
    "validate-runtime-delivery",
    "run-task-graph-fixture",
    "launch-local-asset-human-smoke-run",
    "launch-local-asset-bounded-smoke-iteration",
    "launch-local-asset-bounded-smoke-cycle-contract",
    "launch-local-asset-bounded-smoke-cycle-human-review",
    "launch-local-asset-next-bounded-smoke-iteration-admission",
    "launch-local-asset-next-bounded-smoke-iteration-execution-request",
    "launch-local-asset-next-bounded-smoke-iteration-runner-admission",
    "launch-local-asset-next-bounded-smoke-iteration-runner",
    "launch-local-asset-next-bounded-smoke-iteration-run-review-packet",
    "launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate",
    "launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate",
    "launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate",
    "launch-github-capability-intake-packet",
    "launch-playwright-local-fixture-sandbox-smoke",
    "launch-bounded-playwright-worker-adapter-draft",
    "launch-operator-provided-playwright-execution-receipt",
    "launch-local-fixture-playwright-adapter-admission-gate",
    "launch-local-only-playwright-fixture-scenario-suite",
    "launch-playwright-local-admission-receipt-aggregation",
    "launch-admission-gated-local-adapter-registry-promotion",
    "launch-local-fixture-adapter-usage-receipt",
    "launch-local-fixture-adapter-dry-run-invocation-plan",
    "launch-local-fixture-adapter-execution-gate-plan",
    "launch-local-fixture-human-approval-artifact",
    "launch-local-fixture-runner-contract-draft",
    "launch-local-fixture-runner-stub-admission-gate",
    "launch-local-fixture-runner-receipt-contract-draft",
    "launch-local-fixture-runner-receipt-preflight-verifier",
    "launch-local-fixture-runner-receipt-metadata-artifact",
    "launch-local-asset-smoke-promotion-gate",
    "launch-local-asset-iteration-promotion-gate",
    "launch-local-asset-smoke-iteration-review-packet",
    "launch-local-asset-smoke-review-packet",
    "launch-local-asset-scan",
    "launch-local-asset-smoke-readiness",
    "launch-office-workflow",
    "launch-model-fixture",
    "launch-model-provider-dry-run",
    "launch-browser-fixture",
    "launch-browser-dry-run",
    "launch-comfyui-dry-run",
    "launch-blender-dry-run",
    "launch-creative-handoff",
    "launch-task-graph",
    "launch-runtime-delivery-validation",
    "launch-product-health-check",
    "show-adapter-registry",
    "validate-tool-intake",
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
                approved=_parse_exact_true(args.approved, "--approved"),
                human_reviewed=_parse_exact_true(
                    args.human_reviewed, "--human-reviewed"
                ),
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
        if args.command == "run-browser-fixture":
            result = run_browser_fixture_from_actions_file(
                Path(args.fixture_path),
                Path(args.actions_path),
                Path(args.output_dir),
            )
            _print_command_payload(
                {
                    "complete": True,
                    "fixture_path": result.fixture_path.as_posix(),
                    "output_dir": result.output_dir.as_posix(),
                    "browser_action_log_path": result.action_log_path.as_posix(),
                    "browser_evidence_manifest_path": (
                        result.evidence_manifest_path.as_posix()
                    ),
                    "action_count": result.action_count,
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0
        if args.command == "validate-runtime-delivery":
            result = validate_runtime_delivery_package(
                Path(args.package_dir),
                Path(args.output_path),
                raw_sentinel_values=args.raw_sentinel or [],
            )
            _print_command_payload(
                {
                    "complete": result.complete,
                    "package_dir": result.package_dir.as_posix(),
                    "runtime_delivery_manifest_path": (
                        result.runtime_delivery_manifest_path.as_posix()
                    ),
                    "runtime_delivery_validation_path": (
                        result.runtime_delivery_validation_path.as_posix()
                    ),
                    "packaged_artifacts": list(result.packaged_artifacts),
                    "raw_value_leakage_detected": (
                        result.raw_value_leakage_detected
                    ),
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.complete else 1
        if args.command == "run-task-graph-fixture":
            result = run_local_task_graph_fixture(
                Path(args.graph_path),
                Path(args.output_dir),
            )
            _print_command_payload(
                {
                    "complete": result.success,
                    "graph_path": result.graph_path.as_posix(),
                    "output_dir": result.output_dir.as_posix(),
                    "task_graph_execution_manifest_path": None
                    if result.execution_manifest_path is None
                    else result.execution_manifest_path.as_posix(),
                    "task_graph_replay_manifest_path": None
                    if result.replay_manifest_path is None
                    else result.replay_manifest_path.as_posix(),
                    "task_graph_artifact_outputs_path": None
                    if result.artifact_outputs_manifest_path is None
                    else result.artifact_outputs_manifest_path.as_posix(),
                    "task_graph_failure_bundle_path": None
                    if result.failure_bundle_path is None
                    else result.failure_bundle_path.as_posix(),
                    "node_order": list(result.node_order),
                    "required_human_approval": result.required_human_approval,
                }
            )
            return 0 if result.success else 1
        if args.command == "launch-local-asset-scan":
            result = run_local_asset_scan_launcher(
                Path(args.input_dir),
                Path(args.output_dir),
                recursive=args.recursive,
                include_hidden=args.include_hidden,
                project_id=args.project_id,
                previous_scan_output_dir=_optional_path(
                    args.previous_scan_output_dir
                ),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-smoke-readiness":
            result = run_local_asset_smoke_readiness_launcher(
                Path(args.candidate_input_dir),
                Path(args.output_dir),
                recursive=args.recursive,
                include_hidden=args.include_hidden,
                project_id=args.project_id,
                max_entries=args.max_entries,
                max_depth=args.max_depth,
                max_total_bytes=args.max_total_bytes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-human-smoke-run":
            result = run_local_asset_human_smoke_launcher(
                Path(args.candidate_input_dir),
                Path(args.output_dir),
                Path(args.readiness_report),
                human_approval_id=args.human_approval_id,
                human_approval_phrase=args.human_approval_phrase,
                recursive=args.recursive,
                include_hidden=args.include_hidden,
                project_id=args.project_id,
                max_smoke_files=args.max_smoke_files,
                max_smoke_bytes=args.max_smoke_bytes,
                max_smoke_depth=args.max_smoke_depth,
                previous_scan_output_dir=_optional_path(
                    args.previous_scan_output_dir
                ),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-bounded-smoke-iteration":
            result = run_local_asset_bounded_smoke_iteration_launcher(
                Path(args.promotion_output_dir),
                Path(args.candidate_input_dir),
                Path(args.readiness_report),
                Path(args.output_dir),
                human_signoff_id=args.human_signoff_id,
                human_signoff_phrase=args.human_signoff_phrase,
                recursive=args.recursive,
                include_hidden=args.include_hidden,
                project_id=args.project_id,
                max_smoke_files=args.max_smoke_files,
                max_smoke_bytes=args.max_smoke_bytes,
                max_smoke_depth=args.max_smoke_depth,
                previous_scan_output_dir=_optional_path(
                    args.previous_scan_output_dir
                ),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-smoke-review-packet":
            result = run_local_asset_smoke_review_packet_launcher(
                Path(args.smoke_output_dir),
                Path(args.output_dir),
                project_id=args.project_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-smoke-iteration-review-packet":
            result = run_local_asset_smoke_iteration_review_packet_launcher(
                Path(args.iteration_output_dir),
                Path(args.output_dir),
                project_id=args.project_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-smoke-promotion-gate":
            result = run_local_asset_smoke_promotion_gate_launcher(
                Path(args.review_output_dir),
                Path(args.output_dir),
                project_id=args.project_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-iteration-promotion-gate":
            result = run_local_asset_iteration_promotion_gate_launcher(
                Path(args.iteration_review_output_dir),
                Path(args.output_dir),
                project_id=args.project_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-bounded-smoke-cycle-contract":
            result = run_local_asset_bounded_smoke_cycle_contract_launcher(
                Path(args.readiness_output_dir),
                Path(args.smoke_output_dir),
                Path(args.smoke_review_output_dir),
                Path(args.smoke_promotion_output_dir),
                Path(args.iteration_output_dir),
                Path(args.iteration_review_output_dir),
                Path(args.iteration_promotion_output_dir),
                Path(args.output_dir),
                project_id=args.project_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-asset-bounded-smoke-cycle-human-review":
            result = run_local_asset_bounded_smoke_cycle_human_review_launcher(
                Path(args.cycle_contract_output_dir),
                Path(args.output_dir),
                human_review_id=args.human_review_id,
                human_reviewer_id=args.human_reviewer_id,
                human_decision=args.human_decision,
                human_signoff_phrase=args.human_signoff_phrase,
                project_id=args.project_id,
                human_review_notes=args.human_review_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-admission"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_admission_launcher(
                    Path(args.cycle_human_review_output_dir),
                    Path(args.output_dir),
                    project_id=args.project_id,
                    requested_next_iteration_id=args.requested_next_iteration_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-execution-request"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_execution_request_launcher(
                    Path(args.next_admission_output_dir),
                    Path(args.output_dir),
                    requested_next_iteration_id=args.requested_next_iteration_id,
                    requested_candidate_input_dir=args.requested_candidate_input_dir,
                    requested_next_iteration_output_dir=(
                        args.requested_next_iteration_output_dir
                    ),
                    requested_max_files=args.requested_max_files,
                    requested_max_total_bytes=args.requested_max_total_bytes,
                    requested_max_depth=args.requested_max_depth,
                    project_id=args.project_id,
                    request_id=args.request_id,
                    operator_id=args.operator_id,
                    operator_notes=args.operator_notes,
                    requested_compare_previous_scan_manifest_path=(
                        args.requested_compare_previous_scan_manifest_path
                    ),
                    requested_previous_iteration_artifact_index_path=(
                        args.requested_previous_iteration_artifact_index_path
                    ),
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-runner-admission"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_runner_admission_launcher(
                    Path(args.execution_request_output_dir),
                    Path(args.output_dir),
                    runner_admission_id=args.runner_admission_id,
                    runner_operator_id=args.runner_operator_id,
                    runner_operator_acknowledgement_phrase=(
                        args.runner_operator_acknowledgement_phrase
                    ),
                    admitted_runner_id=args.admitted_runner_id,
                    admitted_runner_version=args.admitted_runner_version,
                    admitted_max_files=args.admitted_max_files,
                    admitted_max_total_bytes=args.admitted_max_total_bytes,
                    admitted_max_depth=args.admitted_max_depth,
                    project_id=args.project_id,
                    operator_notes=args.operator_notes,
                    runner_environment_label=args.runner_environment_label,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-runner"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_runner_launcher(
                    Path(args.runner_admission_output_dir),
                    Path(args.runner_output_dir),
                    Path(args.actual_next_iteration_output_dir),
                    runner_execution_id=args.runner_execution_id,
                    runner_operator_id=args.runner_operator_id,
                    runner_execution_acknowledgement_phrase=(
                        args.runner_execution_acknowledgement_phrase
                    ),
                    project_id=args.project_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-run-review-packet"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_run_review_packet_launcher(
                    Path(args.runner_output_dir),
                    Path(args.actual_next_iteration_output_dir),
                    Path(args.output_dir),
                    review_packet_id=args.review_packet_id,
                    project_id=args.project_id,
                    reviewer_id=args.reviewer_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate"
        ):
            result = (
                run_local_asset_next_bounded_smoke_iteration_run_promotion_gate_launcher(
                    Path(args.run_review_packet_output_dir),
                    Path(args.output_dir),
                    promotion_gate_id=args.promotion_gate_id,
                    project_id=args.project_id,
                    reviewer_id=args.reviewer_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate"
        ):
            result = (
                run_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_launcher(
                    Path(args.run_promotion_gate_output_dir),
                    Path(args.output_dir),
                    cycle_contract_id=args.cycle_contract_id,
                    project_id=args.project_id,
                    reviewer_id=args.reviewer_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate"
        ):
            result = (
                run_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_launcher(
                    Path(args.cycle_contract_output_dir),
                    Path(args.output_dir),
                    human_review_id=args.human_review_id,
                    human_decision=args.human_decision,
                    human_signoff_phrase=args.human_signoff_phrase,
                    project_id=args.project_id,
                    reviewer_id=args.reviewer_id,
                    operator_notes=args.operator_notes,
                )
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-github-capability-intake-packet":
            result = run_github_capability_intake_packet_launcher(
                Path(args.candidate_manifest),
                Path(args.output_dir),
                args.intake_id,
                candidate_repo_dir=_optional_path(args.candidate_repo_dir),
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-playwright-local-fixture-sandbox-smoke":
            result = run_playwright_local_fixture_sandbox_smoke_launcher(
                Path(args.selection_matrix),
                Path(args.playwright_candidate_manifest),
                Path(args.output_dir),
                args.smoke_id,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                node_command=_optional_path(args.node_command),
                runner_script=_optional_path(args.runner_script),
                execute_local_fixture_smoke=args.execute_local_fixture_smoke,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-bounded-playwright-worker-adapter-draft":
            result = run_bounded_playwright_worker_adapter_draft_launcher(
                Path(args.selection_matrix),
                Path(args.playwright_candidate_manifest),
                Path(args.output_dir),
                args.adapter_draft_id,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                node_command=_optional_path(args.node_command),
                runner_script=_optional_path(args.runner_script),
                execute_local_fixture_smoke=args.execute_local_fixture_smoke,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-operator-provided-playwright-execution-receipt":
            result = run_operator_provided_playwright_execution_receipt_launcher(
                Path(args.selection_matrix),
                Path(args.playwright_candidate_manifest),
                Path(args.output_dir),
                args.receipt_id,
                node_command=_optional_path(args.node_command),
                runner_script=_optional_path(args.runner_script),
                operator_attestation=args.operator_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                expected_node_version=args.expected_node_version,
                expected_playwright_source=args.expected_playwright_source,
                plan_only=args.plan_only,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-playwright-adapter-admission-gate":
            result = run_local_fixture_playwright_adapter_admission_gate_launcher(
                Path(args.receipt_dir),
                Path(args.output_dir),
                args.gate_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                aggregation_result=_optional_path(args.aggregation_result),
                require_aggregation_evidence=args.require_aggregation_evidence,
                require_regression_evidence=args.require_regression_evidence,
                plan_only=args.plan_only,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-only-playwright-fixture-scenario-suite":
            result = run_local_only_playwright_fixture_scenario_suite_launcher(
                Path(args.selection_matrix),
                Path(args.playwright_candidate_manifest),
                Path(args.output_dir),
                args.suite_id,
                node_command=_optional_path(args.node_command),
                runner_script=_optional_path(args.runner_script),
                operator_attestation=args.operator_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                expected_node_version=args.expected_node_version,
                expected_playwright_source=args.expected_playwright_source,
                scenario_set=args.scenario_set,
                plan_only=args.plan_only,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-playwright-local-admission-receipt-aggregation":
            result = run_playwright_local_admission_receipt_aggregation_launcher(
                Path(args.suite_run_dirs),
                Path(args.output_dir),
                args.aggregation_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                minimum_suite_runs=args.minimum_suite_runs,
                minimum_pass_rate_bps=args.minimum_pass_rate_bps,
                maximum_flaky_rate_bps=args.maximum_flaky_rate_bps,
                maximum_evidence_age_days=args.maximum_evidence_age_days,
                plan_only=args.plan_only,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-admission-gated-local-adapter-registry-promotion"
        ):
            result = run_admission_gated_local_adapter_registry_promotion_launcher(
                Path(args.admission_gate_decision),
                Path(args.output_dir),
                args.promotion_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                registry_output=_optional_path(args.registry_output),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-adapter-usage-receipt":
            result = run_local_fixture_adapter_usage_receipt_launcher(
                Path(args.promotion_result),
                Path(args.output_dir),
                args.usage_receipt_id,
                review_attestation=args.review_attestation,
                local_fixture_reference=args.local_fixture_reference,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
                registry_entry=_optional_path(args.registry_entry),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if (
            args.command
            == "launch-local-fixture-adapter-dry-run-invocation-plan"
        ):
            result = run_local_fixture_adapter_dry_run_invocation_plan_launcher(
                Path(args.usage_receipt),
                Path(args.output_dir),
                args.invocation_plan_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-adapter-execution-gate-plan":
            result = run_local_fixture_adapter_execution_gate_plan_launcher(
                Path(args.dry_run_plan),
                Path(args.output_dir),
                args.execution_gate_plan_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-human-approval-artifact":
            result = run_local_fixture_human_approval_artifact_launcher(
                Path(args.execution_gate_plan),
                Path(args.output_dir),
                args.approval_artifact_id,
                args.reviewer_id,
                args.approval_attestation,
                project_id=args.project_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-runner-contract-draft":
            result = run_local_fixture_runner_contract_draft_launcher(
                Path(args.output_dir),
                args.runner_contract_id,
                review_attestation=args.review_attestation,
                project_id=args.project_id,
                reviewer_id=args.reviewer_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-runner-stub-admission-gate":
            result = run_local_fixture_runner_stub_admission_gate_launcher(
                Path(args.human_approval_artifact_result),
                Path(args.runner_contract_draft_result),
                Path(args.output_dir),
                args.gate_id,
                args.reviewer_id,
                args.review_attestation,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-runner-receipt-contract-draft":
            result = run_local_fixture_runner_receipt_contract_draft_launcher(
                Path(args.output_dir),
                args.receipt_contract_id,
                args.reviewer_id,
                args.review_attestation,
                project_id=args.project_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-runner-receipt-preflight-verifier":
            result = run_local_fixture_runner_receipt_preflight_verifier_launcher(
                Path(args.runner_stub_admission_gate_result),
                Path(args.runner_receipt_contract_draft_result),
                Path(args.human_approval_artifact_result),
                Path(args.output_dir),
                args.preflight_id,
                args.reviewer_id,
                args.review_attestation,
                project_id=args.project_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-local-fixture-runner-receipt-metadata-artifact":
            result = run_local_fixture_runner_receipt_metadata_artifact_launcher(
                Path(args.runner_receipt_preflight_result),
                Path(args.output_dir),
                args.runner_receipt_id,
                args.reviewer_id,
                args.review_attestation,
                project_id=args.project_id,
                operator_notes=args.operator_notes,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-office-workflow":
            result = run_local_office_launcher(
                Path(args.input_workbook),
                Path(args.output_dir),
                output_workbook_name=args.output_workbook_name,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-model-fixture":
            result = run_model_fixture_launcher(
                Path(args.input_artifact_path),
                Path(args.output_dir),
                schema_name=args.schema_name,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-model-provider-dry-run":
            result = run_model_provider_dry_run_launcher(
                Path(args.input_artifact_path),
                Path(args.output_dir),
                schema_name=args.schema_name,
                provider_id=args.provider_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-browser-fixture":
            result = run_browser_fixture_launcher(
                Path(args.fixture_path),
                Path(args.actions_path),
                Path(args.output_dir),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-browser-dry-run":
            result = run_browser_runtime_dry_run_launcher(
                Path(args.actions_path),
                Path(args.output_dir),
                target_url=args.target_url,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-comfyui-dry-run":
            result = run_comfyui_dry_run_launcher(
                Path(args.workflow_path),
                Path(args.output_dir),
                input_asset_paths=tuple(Path(path) for path in args.input_asset),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-blender-dry-run":
            result = run_blender_dry_run_launcher(
                Path(args.scene_path),
                Path(args.operation_plan_path),
                Path(args.output_dir),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-creative-handoff":
            result = run_creative_handoff_launcher(
                args.family,
                tuple(Path(path) for path in args.source_asset),
                Path(args.output_dir),
                package_id=args.package_id,
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-task-graph":
            result = run_task_graph_launcher(
                Path(args.graph_path),
                Path(args.output_dir),
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-runtime-delivery-validation":
            result = run_runtime_delivery_validation_launcher(
                Path(args.package_dir),
                Path(args.output_dir),
                raw_sentinel_values=args.raw_sentinel or [],
            )
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "launch-product-health-check":
            result = run_product_health_check_launcher(Path(args.output_dir))
            _print_command_payload(result.to_cli_payload())
            return 0 if result.complete else 1
        if args.command == "show-adapter-registry":
            payload = {
                "complete": True,
                "registry_type": "personal_ai_execution_os_v2_adapter_registry",
                "entries": [
                    entry.to_dict()
                    for entry in DEFAULT_ADAPTER_REGISTRY
                ],
                "validation_failures": {
                    entry.adapter_id: list(validate_adapter_registry_entry(entry))
                    for entry in DEFAULT_ADAPTER_REGISTRY
                },
                "required_human_approval": True,
            }
            _write_optional_cli_output(payload, _optional_path(args.output_path))
            _print_command_payload(payload)
            return 0
        if args.command == "validate-tool-intake":
            result = validate_runtime_tool_admission_register_file(
                Path(args.register_path)
            )
            payload = {
                "complete": result.accepted,
                "register_path": None
                if result.register_path is None
                else result.register_path.as_posix(),
                "entry_count": result.entry_count,
                "failures": list(result.failures),
                "admitted_projects": list(result.admitted_projects),
                "deferred_projects": list(result.deferred_projects),
                "required_human_approval": True,
            }
            _write_optional_cli_output(payload, _optional_path(args.output_path))
            _print_command_payload(payload)
            return 0 if result.accepted else 1
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
    approve_xlsx_parser.add_argument("--approved", required=True)
    approve_xlsx_parser.add_argument("--human-reviewed", required=True)
    approve_xlsx_parser.add_argument("--reviewer-id", required=True)

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

    browser_fixture_parser = subparsers.add_parser("run-browser-fixture")
    browser_fixture_parser.add_argument("--fixture-path", required=True)
    browser_fixture_parser.add_argument("--actions-path", required=True)
    browser_fixture_parser.add_argument("--output-dir", required=True)

    runtime_delivery_parser = subparsers.add_parser("validate-runtime-delivery")
    runtime_delivery_parser.add_argument("--package-dir", required=True)
    runtime_delivery_parser.add_argument("--output-path", required=True)
    runtime_delivery_parser.add_argument("--raw-sentinel", action="append")

    task_graph_parser = subparsers.add_parser("run-task-graph-fixture")
    task_graph_parser.add_argument("--graph-path", required=True)
    task_graph_parser.add_argument("--output-dir", required=True)

    launch_asset_parser = subparsers.add_parser("launch-local-asset-scan")
    launch_asset_parser.add_argument("--input-dir", required=True)
    launch_asset_parser.add_argument("--output-dir", required=True)
    launch_asset_parser.add_argument("--recursive", action="store_true")
    launch_asset_parser.add_argument("--include-hidden", action="store_true")
    launch_asset_parser.add_argument("--project-id")
    launch_asset_parser.add_argument("--previous-scan-output-dir")

    launch_smoke_readiness_parser = subparsers.add_parser(
        "launch-local-asset-smoke-readiness"
    )
    launch_smoke_readiness_parser.add_argument(
        "--candidate-input-dir",
        required=True,
    )
    launch_smoke_readiness_parser.add_argument("--output-dir", required=True)
    launch_smoke_readiness_parser.add_argument("--recursive", action="store_true")
    launch_smoke_readiness_parser.add_argument(
        "--include-hidden",
        action="store_true",
    )
    launch_smoke_readiness_parser.add_argument("--project-id")
    launch_smoke_readiness_parser.add_argument(
        "--max-entries",
        type=int,
        default=50000,
    )
    launch_smoke_readiness_parser.add_argument(
        "--max-depth",
        type=int,
        default=20,
    )
    launch_smoke_readiness_parser.add_argument(
        "--max-total-bytes",
        type=int,
        default=500000000000,
    )

    launch_human_smoke_parser = subparsers.add_parser(
        "launch-local-asset-human-smoke-run"
    )
    launch_human_smoke_parser.add_argument(
        "--candidate-input-dir",
        required=True,
    )
    launch_human_smoke_parser.add_argument("--output-dir", required=True)
    launch_human_smoke_parser.add_argument("--readiness-report", required=True)
    launch_human_smoke_parser.add_argument("--human-approval-id", required=True)
    launch_human_smoke_parser.add_argument("--human-approval-phrase", required=True)
    launch_human_smoke_parser.add_argument("--recursive", action="store_true")
    launch_human_smoke_parser.add_argument(
        "--include-hidden",
        action="store_true",
    )
    launch_human_smoke_parser.add_argument("--project-id")
    launch_human_smoke_parser.add_argument(
        "--max-smoke-files",
        type=int,
        default=100,
    )
    launch_human_smoke_parser.add_argument(
        "--max-smoke-bytes",
        type=int,
        default=2000000000,
    )
    launch_human_smoke_parser.add_argument(
        "--max-smoke-depth",
        type=int,
        default=8,
    )
    launch_human_smoke_parser.add_argument("--previous-scan-output-dir")

    launch_bounded_iteration_parser = subparsers.add_parser(
        "launch-local-asset-bounded-smoke-iteration"
    )
    launch_bounded_iteration_parser.add_argument(
        "--promotion-output-dir",
        required=True,
    )
    launch_bounded_iteration_parser.add_argument(
        "--candidate-input-dir",
        required=True,
    )
    launch_bounded_iteration_parser.add_argument(
        "--readiness-report",
        required=True,
    )
    launch_bounded_iteration_parser.add_argument("--output-dir", required=True)
    launch_bounded_iteration_parser.add_argument("--human-signoff-id", required=True)
    launch_bounded_iteration_parser.add_argument(
        "--human-signoff-phrase",
        required=True,
    )
    launch_bounded_iteration_parser.add_argument("--project-id")
    launch_bounded_iteration_parser.add_argument("--previous-scan-output-dir")
    launch_bounded_iteration_parser.add_argument("--recursive", action="store_true")
    launch_bounded_iteration_parser.add_argument(
        "--include-hidden",
        action="store_true",
    )
    launch_bounded_iteration_parser.add_argument(
        "--max-smoke-files",
        type=int,
        default=100,
    )
    launch_bounded_iteration_parser.add_argument(
        "--max-smoke-bytes",
        type=int,
        default=1073741824,
    )
    launch_bounded_iteration_parser.add_argument(
        "--max-smoke-depth",
        type=int,
        default=12,
    )

    launch_smoke_review_parser = subparsers.add_parser(
        "launch-local-asset-smoke-review-packet"
    )
    launch_smoke_review_parser.add_argument("--smoke-output-dir", required=True)
    launch_smoke_review_parser.add_argument("--output-dir", required=True)
    launch_smoke_review_parser.add_argument("--project-id")

    launch_smoke_iteration_review_parser = subparsers.add_parser(
        "launch-local-asset-smoke-iteration-review-packet"
    )
    launch_smoke_iteration_review_parser.add_argument(
        "--iteration-output-dir",
        required=True,
    )
    launch_smoke_iteration_review_parser.add_argument("--output-dir", required=True)
    launch_smoke_iteration_review_parser.add_argument("--project-id")

    launch_smoke_promotion_parser = subparsers.add_parser(
        "launch-local-asset-smoke-promotion-gate"
    )
    launch_smoke_promotion_parser.add_argument("--review-output-dir", required=True)
    launch_smoke_promotion_parser.add_argument("--output-dir", required=True)
    launch_smoke_promotion_parser.add_argument("--project-id")

    launch_iteration_promotion_parser = subparsers.add_parser(
        "launch-local-asset-iteration-promotion-gate"
    )
    launch_iteration_promotion_parser.add_argument(
        "--iteration-review-output-dir",
        required=True,
    )
    launch_iteration_promotion_parser.add_argument("--output-dir", required=True)
    launch_iteration_promotion_parser.add_argument("--project-id")

    launch_cycle_contract_parser = subparsers.add_parser(
        "launch-local-asset-bounded-smoke-cycle-contract"
    )
    launch_cycle_contract_parser.add_argument(
        "--readiness-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument("--smoke-output-dir", required=True)
    launch_cycle_contract_parser.add_argument(
        "--smoke-review-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument(
        "--smoke-promotion-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument(
        "--iteration-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument(
        "--iteration-review-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument(
        "--iteration-promotion-output-dir",
        required=True,
    )
    launch_cycle_contract_parser.add_argument("--output-dir", required=True)
    launch_cycle_contract_parser.add_argument("--project-id")

    launch_cycle_human_review_parser = subparsers.add_parser(
        "launch-local-asset-bounded-smoke-cycle-human-review"
    )
    launch_cycle_human_review_parser.add_argument(
        "--cycle-contract-output-dir",
        required=True,
    )
    launch_cycle_human_review_parser.add_argument("--output-dir", required=True)
    launch_cycle_human_review_parser.add_argument(
        "--human-review-id",
        required=True,
    )
    launch_cycle_human_review_parser.add_argument(
        "--human-reviewer-id",
        required=True,
    )
    launch_cycle_human_review_parser.add_argument(
        "--human-decision",
        required=True,
    )
    launch_cycle_human_review_parser.add_argument(
        "--human-signoff-phrase",
        required=True,
    )
    launch_cycle_human_review_parser.add_argument("--project-id")
    launch_cycle_human_review_parser.add_argument("--human-review-notes")

    launch_next_iteration_admission_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-admission"
    )
    launch_next_iteration_admission_parser.add_argument(
        "--cycle-human-review-output-dir",
        required=True,
    )
    launch_next_iteration_admission_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_iteration_admission_parser.add_argument("--project-id")
    launch_next_iteration_admission_parser.add_argument(
        "--requested-next-iteration-id"
    )
    launch_next_iteration_admission_parser.add_argument("--operator-notes")

    launch_next_iteration_execution_request_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-execution-request"
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--next-admission-output-dir",
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-next-iteration-id",
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-candidate-input-dir",
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-next-iteration-output-dir",
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-max-files",
        type=int,
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-max-total-bytes",
        type=int,
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-max-depth",
        type=int,
        required=True,
    )
    launch_next_iteration_execution_request_parser.add_argument("--project-id")
    launch_next_iteration_execution_request_parser.add_argument("--request-id")
    launch_next_iteration_execution_request_parser.add_argument("--operator-id")
    launch_next_iteration_execution_request_parser.add_argument("--operator-notes")
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-compare-previous-scan-manifest-path"
    )
    launch_next_iteration_execution_request_parser.add_argument(
        "--requested-previous-iteration-artifact-index-path"
    )

    launch_next_iteration_runner_admission_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-runner-admission"
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--execution-request-output-dir",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--runner-admission-id",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--runner-operator-id",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--runner-operator-acknowledgement-phrase",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--admitted-runner-id",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--admitted-runner-version",
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--admitted-max-files",
        type=int,
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--admitted-max-total-bytes",
        type=int,
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument(
        "--admitted-max-depth",
        type=int,
        required=True,
    )
    launch_next_iteration_runner_admission_parser.add_argument("--project-id")
    launch_next_iteration_runner_admission_parser.add_argument("--operator-notes")
    launch_next_iteration_runner_admission_parser.add_argument(
        "--runner-environment-label"
    )

    launch_next_iteration_runner_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-runner"
    )
    launch_next_iteration_runner_parser.add_argument(
        "--runner-admission-output-dir",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument(
        "--runner-output-dir",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument(
        "--actual-next-iteration-output-dir",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument(
        "--runner-execution-id",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument(
        "--runner-operator-id",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument(
        "--runner-execution-acknowledgement-phrase",
        required=True,
    )
    launch_next_iteration_runner_parser.add_argument("--project-id")
    launch_next_iteration_runner_parser.add_argument("--operator-notes")

    launch_next_iteration_run_review_packet_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-run-review-packet"
    )
    launch_next_iteration_run_review_packet_parser.add_argument(
        "--runner-output-dir",
        required=True,
    )
    launch_next_iteration_run_review_packet_parser.add_argument(
        "--actual-next-iteration-output-dir",
        required=True,
    )
    launch_next_iteration_run_review_packet_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_iteration_run_review_packet_parser.add_argument(
        "--review-packet-id",
        required=True,
    )
    launch_next_iteration_run_review_packet_parser.add_argument("--project-id")
    launch_next_iteration_run_review_packet_parser.add_argument("--reviewer-id")
    launch_next_iteration_run_review_packet_parser.add_argument("--operator-notes")

    launch_next_iteration_run_promotion_gate_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-iteration-run-promotion-gate"
    )
    launch_next_iteration_run_promotion_gate_parser.add_argument(
        "--run-review-packet-output-dir",
        required=True,
    )
    launch_next_iteration_run_promotion_gate_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_iteration_run_promotion_gate_parser.add_argument(
        "--promotion-gate-id",
        required=True,
    )
    launch_next_iteration_run_promotion_gate_parser.add_argument("--project-id")
    launch_next_iteration_run_promotion_gate_parser.add_argument("--reviewer-id")
    launch_next_iteration_run_promotion_gate_parser.add_argument("--operator-notes")

    launch_next_cycle_contract_from_run_gate_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate"
    )
    launch_next_cycle_contract_from_run_gate_parser.add_argument(
        "--run-promotion-gate-output-dir",
        required=True,
    )
    launch_next_cycle_contract_from_run_gate_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_cycle_contract_from_run_gate_parser.add_argument(
        "--cycle-contract-id",
        required=True,
    )
    launch_next_cycle_contract_from_run_gate_parser.add_argument("--project-id")
    launch_next_cycle_contract_from_run_gate_parser.add_argument("--reviewer-id")
    launch_next_cycle_contract_from_run_gate_parser.add_argument("--operator-notes")

    launch_next_cycle_contract_review_from_run_gate_parser = subparsers.add_parser(
        "launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate"
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--cycle-contract-output-dir",
        required=True,
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--output-dir",
        required=True,
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--human-review-id",
        required=True,
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--human-decision",
        required=True,
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--human-signoff-phrase",
        required=True,
    )
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument("--project-id")
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument("--reviewer-id")
    launch_next_cycle_contract_review_from_run_gate_parser.add_argument(
        "--operator-notes"
    )

    github_intake_parser = subparsers.add_parser(
        "launch-github-capability-intake-packet"
    )
    github_intake_parser.add_argument("--candidate-manifest", required=True)
    github_intake_parser.add_argument("--output-dir", required=True)
    github_intake_parser.add_argument("--intake-id", required=True)
    github_intake_parser.add_argument("--candidate-repo-dir")
    github_intake_parser.add_argument("--project-id")
    github_intake_parser.add_argument("--reviewer-id")
    github_intake_parser.add_argument("--operator-notes")

    playwright_smoke_parser = subparsers.add_parser(
        "launch-playwright-local-fixture-sandbox-smoke"
    )
    playwright_smoke_parser.add_argument("--selection-matrix", required=True)
    playwright_smoke_parser.add_argument(
        "--playwright-candidate-manifest",
        required=True,
    )
    playwright_smoke_parser.add_argument("--output-dir", required=True)
    playwright_smoke_parser.add_argument("--smoke-id", required=True)
    playwright_smoke_parser.add_argument("--project-id")
    playwright_smoke_parser.add_argument("--reviewer-id")
    playwright_smoke_parser.add_argument("--operator-notes")
    playwright_smoke_parser.add_argument("--node-command")
    playwright_smoke_parser.add_argument("--runner-script")
    playwright_smoke_parser.add_argument(
        "--execute-local-fixture-smoke",
        action="store_true",
    )

    bounded_playwright_adapter_parser = subparsers.add_parser(
        "launch-bounded-playwright-worker-adapter-draft"
    )
    bounded_playwright_adapter_parser.add_argument(
        "--selection-matrix",
        required=True,
    )
    bounded_playwright_adapter_parser.add_argument(
        "--playwright-candidate-manifest",
        required=True,
    )
    bounded_playwright_adapter_parser.add_argument("--output-dir", required=True)
    bounded_playwright_adapter_parser.add_argument(
        "--adapter-draft-id",
        required=True,
    )
    bounded_playwright_adapter_parser.add_argument("--project-id")
    bounded_playwright_adapter_parser.add_argument("--reviewer-id")
    bounded_playwright_adapter_parser.add_argument("--operator-notes")
    bounded_playwright_adapter_parser.add_argument("--node-command")
    bounded_playwright_adapter_parser.add_argument("--runner-script")
    bounded_playwright_adapter_parser.add_argument(
        "--execute-local-fixture-smoke",
        action="store_true",
    )

    operator_receipt_parser = subparsers.add_parser(
        "launch-operator-provided-playwright-execution-receipt"
    )
    operator_receipt_parser.add_argument("--selection-matrix", required=True)
    operator_receipt_parser.add_argument(
        "--playwright-candidate-manifest",
        required=True,
    )
    operator_receipt_parser.add_argument("--output-dir", required=True)
    operator_receipt_parser.add_argument("--receipt-id", required=True)
    operator_receipt_parser.add_argument("--node-command", required=True)
    operator_receipt_parser.add_argument("--runner-script", required=True)
    operator_receipt_parser.add_argument("--operator-attestation", required=True)
    operator_receipt_parser.add_argument("--project-id")
    operator_receipt_parser.add_argument("--reviewer-id")
    operator_receipt_parser.add_argument("--operator-notes")
    operator_receipt_parser.add_argument("--expected-node-version")
    operator_receipt_parser.add_argument("--expected-playwright-source")
    operator_receipt_parser.add_argument(
        "--plan-only",
        action="store_true",
    )

    admission_gate_parser = subparsers.add_parser(
        "launch-local-fixture-playwright-adapter-admission-gate"
    )
    admission_gate_parser.add_argument("--receipt-dir", required=True)
    admission_gate_parser.add_argument("--output-dir", required=True)
    admission_gate_parser.add_argument("--gate-id", required=True)
    admission_gate_parser.add_argument("--review-attestation", required=True)
    admission_gate_parser.add_argument("--project-id")
    admission_gate_parser.add_argument("--reviewer-id")
    admission_gate_parser.add_argument("--operator-notes")
    admission_gate_parser.add_argument("--aggregation-result")
    admission_gate_parser.add_argument(
        "--require-aggregation-evidence",
        action="store_true",
    )
    admission_gate_parser.add_argument(
        "--require-regression-evidence",
        action="store_true",
    )
    admission_gate_parser.add_argument(
        "--plan-only",
        action="store_true",
    )

    scenario_suite_parser = subparsers.add_parser(
        "launch-local-only-playwright-fixture-scenario-suite"
    )
    scenario_suite_parser.add_argument("--selection-matrix", required=True)
    scenario_suite_parser.add_argument(
        "--playwright-candidate-manifest",
        required=True,
    )
    scenario_suite_parser.add_argument("--output-dir", required=True)
    scenario_suite_parser.add_argument("--suite-id", required=True)
    scenario_suite_parser.add_argument("--node-command", required=True)
    scenario_suite_parser.add_argument("--runner-script", required=True)
    scenario_suite_parser.add_argument("--operator-attestation", required=True)
    scenario_suite_parser.add_argument("--project-id")
    scenario_suite_parser.add_argument("--reviewer-id")
    scenario_suite_parser.add_argument("--operator-notes")
    scenario_suite_parser.add_argument("--expected-node-version")
    scenario_suite_parser.add_argument("--expected-playwright-source")
    scenario_suite_parser.add_argument(
        "--scenario-set",
        choices=("core", "extended", "regression"),
        default="core",
    )
    scenario_suite_parser.add_argument(
        "--plan-only",
        action="store_true",
    )

    aggregation_parser = subparsers.add_parser(
        "launch-playwright-local-admission-receipt-aggregation"
    )
    aggregation_parser.add_argument("--suite-run-dirs", required=True)
    aggregation_parser.add_argument("--output-dir", required=True)
    aggregation_parser.add_argument("--aggregation-id", required=True)
    aggregation_parser.add_argument("--review-attestation", required=True)
    aggregation_parser.add_argument("--project-id")
    aggregation_parser.add_argument("--reviewer-id")
    aggregation_parser.add_argument("--operator-notes")
    aggregation_parser.add_argument("--minimum-suite-runs", type=int, default=2)
    aggregation_parser.add_argument(
        "--minimum-pass-rate-bps",
        type=int,
        default=10000,
    )
    aggregation_parser.add_argument(
        "--maximum-flaky-rate-bps",
        type=int,
        default=0,
    )
    aggregation_parser.add_argument(
        "--maximum-evidence-age-days",
        type=int,
        default=30,
    )
    aggregation_parser.add_argument(
        "--plan-only",
        action="store_true",
    )

    registry_promotion_parser = subparsers.add_parser(
        "launch-admission-gated-local-adapter-registry-promotion"
    )
    registry_promotion_parser.add_argument(
        "--admission-gate-decision",
        required=True,
    )
    registry_promotion_parser.add_argument("--output-dir", required=True)
    registry_promotion_parser.add_argument("--promotion-id", required=True)
    registry_promotion_parser.add_argument("--review-attestation", required=True)
    registry_promotion_parser.add_argument("--project-id")
    registry_promotion_parser.add_argument("--reviewer-id")
    registry_promotion_parser.add_argument("--operator-notes")
    registry_promotion_parser.add_argument("--registry-output")

    usage_receipt_parser = subparsers.add_parser(
        "launch-local-fixture-adapter-usage-receipt"
    )
    usage_receipt_parser.add_argument("--promotion-result", required=True)
    usage_receipt_parser.add_argument("--output-dir", required=True)
    usage_receipt_parser.add_argument("--usage-receipt-id", required=True)
    usage_receipt_parser.add_argument("--review-attestation", required=True)
    usage_receipt_parser.add_argument("--local-fixture-reference", required=True)
    usage_receipt_parser.add_argument("--project-id")
    usage_receipt_parser.add_argument("--reviewer-id")
    usage_receipt_parser.add_argument("--operator-notes")
    usage_receipt_parser.add_argument("--registry-entry")

    invocation_plan_parser = subparsers.add_parser(
        "launch-local-fixture-adapter-dry-run-invocation-plan"
    )
    invocation_plan_parser.add_argument("--usage-receipt", required=True)
    invocation_plan_parser.add_argument("--output-dir", required=True)
    invocation_plan_parser.add_argument("--invocation-plan-id", required=True)
    invocation_plan_parser.add_argument("--review-attestation", required=True)
    invocation_plan_parser.add_argument("--project-id")
    invocation_plan_parser.add_argument("--reviewer-id")
    invocation_plan_parser.add_argument("--operator-notes")

    execution_gate_plan_parser = subparsers.add_parser(
        "launch-local-fixture-adapter-execution-gate-plan"
    )
    execution_gate_plan_parser.add_argument("--dry-run-plan", required=True)
    execution_gate_plan_parser.add_argument("--output-dir", required=True)
    execution_gate_plan_parser.add_argument("--execution-gate-plan-id", required=True)
    execution_gate_plan_parser.add_argument("--review-attestation", required=True)
    execution_gate_plan_parser.add_argument("--project-id")
    execution_gate_plan_parser.add_argument("--reviewer-id")
    execution_gate_plan_parser.add_argument("--operator-notes")

    human_approval_artifact_parser = subparsers.add_parser(
        "launch-local-fixture-human-approval-artifact"
    )
    human_approval_artifact_parser.add_argument(
        "--execution-gate-plan",
        required=True,
    )
    human_approval_artifact_parser.add_argument("--output-dir", required=True)
    human_approval_artifact_parser.add_argument(
        "--approval-artifact-id",
        required=True,
    )
    human_approval_artifact_parser.add_argument("--reviewer-id", required=True)
    human_approval_artifact_parser.add_argument(
        "--approval-attestation",
        required=True,
    )
    human_approval_artifact_parser.add_argument("--project-id")
    human_approval_artifact_parser.add_argument("--operator-notes")

    runner_contract_parser = subparsers.add_parser(
        "launch-local-fixture-runner-contract-draft"
    )
    runner_contract_parser.add_argument("--output-dir", required=True)
    runner_contract_parser.add_argument("--runner-contract-id", required=True)
    runner_contract_parser.add_argument("--review-attestation", required=True)
    runner_contract_parser.add_argument("--project-id")
    runner_contract_parser.add_argument("--reviewer-id")
    runner_contract_parser.add_argument("--operator-notes")

    runner_stub_gate_parser = subparsers.add_parser(
        "launch-local-fixture-runner-stub-admission-gate"
    )
    runner_stub_gate_parser.add_argument(
        "--human-approval-artifact-result",
        required=True,
    )
    runner_stub_gate_parser.add_argument(
        "--runner-contract-draft-result",
        required=True,
    )
    runner_stub_gate_parser.add_argument("--output-dir", required=True)
    runner_stub_gate_parser.add_argument("--gate-id", required=True)
    runner_stub_gate_parser.add_argument("--reviewer-id", required=True)
    runner_stub_gate_parser.add_argument("--review-attestation", required=True)

    runner_receipt_contract_parser = subparsers.add_parser(
        "launch-local-fixture-runner-receipt-contract-draft"
    )
    runner_receipt_contract_parser.add_argument("--output-dir", required=True)
    runner_receipt_contract_parser.add_argument(
        "--receipt-contract-id",
        required=True,
    )
    runner_receipt_contract_parser.add_argument("--reviewer-id", required=True)
    runner_receipt_contract_parser.add_argument(
        "--review-attestation",
        required=True,
    )
    runner_receipt_contract_parser.add_argument("--project-id")
    runner_receipt_contract_parser.add_argument("--operator-notes")

    runner_receipt_preflight_parser = subparsers.add_parser(
        "launch-local-fixture-runner-receipt-preflight-verifier"
    )
    runner_receipt_preflight_parser.add_argument(
        "--runner-stub-admission-gate-result",
        required=True,
    )
    runner_receipt_preflight_parser.add_argument(
        "--runner-receipt-contract-draft-result",
        required=True,
    )
    runner_receipt_preflight_parser.add_argument(
        "--human-approval-artifact-result",
        required=True,
    )
    runner_receipt_preflight_parser.add_argument("--output-dir", required=True)
    runner_receipt_preflight_parser.add_argument("--preflight-id", required=True)
    runner_receipt_preflight_parser.add_argument("--reviewer-id", required=True)
    runner_receipt_preflight_parser.add_argument(
        "--review-attestation",
        required=True,
    )
    runner_receipt_preflight_parser.add_argument("--project-id")
    runner_receipt_preflight_parser.add_argument("--operator-notes")

    runner_receipt_metadata_parser = subparsers.add_parser(
        "launch-local-fixture-runner-receipt-metadata-artifact"
    )
    runner_receipt_metadata_parser.add_argument(
        "--runner-receipt-preflight-result",
        required=True,
    )
    runner_receipt_metadata_parser.add_argument("--output-dir", required=True)
    runner_receipt_metadata_parser.add_argument(
        "--runner-receipt-id",
        required=True,
    )
    runner_receipt_metadata_parser.add_argument("--reviewer-id", required=True)
    runner_receipt_metadata_parser.add_argument(
        "--review-attestation",
        required=True,
    )
    runner_receipt_metadata_parser.add_argument("--project-id")
    runner_receipt_metadata_parser.add_argument("--operator-notes")

    launch_office_parser = subparsers.add_parser("launch-office-workflow")
    launch_office_parser.add_argument("--input-workbook", required=True)
    launch_office_parser.add_argument("--output-dir", required=True)
    launch_office_parser.add_argument(
        "--output-workbook-name",
        default="derived_xlsx_summary.xlsx",
    )

    launch_model_parser = subparsers.add_parser("launch-model-fixture")
    launch_model_parser.add_argument("--input-artifact-path", required=True)
    launch_model_parser.add_argument("--output-dir", required=True)
    launch_model_parser.add_argument("--schema-name", required=True)

    launch_model_dry_run_parser = subparsers.add_parser(
        "launch-model-provider-dry-run"
    )
    launch_model_dry_run_parser.add_argument("--input-artifact-path", required=True)
    launch_model_dry_run_parser.add_argument("--output-dir", required=True)
    launch_model_dry_run_parser.add_argument("--schema-name", required=True)
    launch_model_dry_run_parser.add_argument("--provider-id", default="openai")

    launch_browser_parser = subparsers.add_parser("launch-browser-fixture")
    launch_browser_parser.add_argument("--fixture-path", required=True)
    launch_browser_parser.add_argument("--actions-path", required=True)
    launch_browser_parser.add_argument("--output-dir", required=True)

    launch_browser_dry_run_parser = subparsers.add_parser("launch-browser-dry-run")
    launch_browser_dry_run_parser.add_argument("--actions-path", required=True)
    launch_browser_dry_run_parser.add_argument("--output-dir", required=True)
    launch_browser_dry_run_parser.add_argument(
        "--target-url",
        default="http://127.0.0.1",
    )

    launch_comfyui_parser = subparsers.add_parser("launch-comfyui-dry-run")
    launch_comfyui_parser.add_argument("--workflow-path", required=True)
    launch_comfyui_parser.add_argument("--output-dir", required=True)
    launch_comfyui_parser.add_argument("--input-asset", action="append", default=[])

    launch_blender_parser = subparsers.add_parser("launch-blender-dry-run")
    launch_blender_parser.add_argument("--scene-path", required=True)
    launch_blender_parser.add_argument("--operation-plan-path", required=True)
    launch_blender_parser.add_argument("--output-dir", required=True)

    launch_handoff_parser = subparsers.add_parser("launch-creative-handoff")
    launch_handoff_parser.add_argument("--family", required=True)
    launch_handoff_parser.add_argument("--source-asset", action="append", required=True)
    launch_handoff_parser.add_argument("--output-dir", required=True)
    launch_handoff_parser.add_argument(
        "--package-id",
        default="creative-handoff-package",
    )

    launch_task_graph_parser = subparsers.add_parser("launch-task-graph")
    launch_task_graph_parser.add_argument("--graph-path", required=True)
    launch_task_graph_parser.add_argument("--output-dir", required=True)

    launch_delivery_parser = subparsers.add_parser(
        "launch-runtime-delivery-validation"
    )
    launch_delivery_parser.add_argument("--package-dir", required=True)
    launch_delivery_parser.add_argument("--output-dir", required=True)
    launch_delivery_parser.add_argument("--raw-sentinel", action="append")

    launch_health_parser = subparsers.add_parser("launch-product-health-check")
    launch_health_parser.add_argument("--output-dir", required=True)

    adapter_registry_parser = subparsers.add_parser("show-adapter-registry")
    adapter_registry_parser.add_argument("--output-path")

    tool_intake_parser = subparsers.add_parser("validate-tool-intake")
    tool_intake_parser.add_argument("--register-path", required=True)
    tool_intake_parser.add_argument("--output-path")

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


def _parse_exact_true(value, flag_name):
    if value != "true":
        raise ValueError(f"{flag_name} must be exactly true")
    return True


def _write_optional_cli_output(payload, output_path):
    if output_path is None:
        return
    if output_path.exists():
        raise ValueError("output_path already exists")
    write_json_atomically(output_path, payload)


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
