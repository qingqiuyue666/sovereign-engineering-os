"""Operator-provided local Playwright execution receipt.

This module is an evidence layer over the bounded Playwright worker adapter
draft. It records an operator-supplied local executable and local runner script,
then delegates execution to the existing adapter draft with the embedded local
fixture smoke enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os

from kernel.capabilities import bounded_playwright_worker_adapter_draft
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS",
    "OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS",
    "OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION",
    "ADAPTER_DRAFT_RUN_DIR_NAME",
    "OperatorProvidedPlaywrightExecutionReceiptResult",
    "build_operator_provided_playwright_execution_receipt_plan",
    "run_operator_provided_playwright_execution_receipt",
    "run_operator_provided_playwright_execution_receipt_launcher",
]


OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE = (
    "operator_provided_playwright_execution_receipt_plan.json"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE = (
    "operator_provided_playwright_execution_receipt_manifest.json"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE = (
    "operator_provided_playwright_execution_receipt_summary.md"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE = (
    "operator_provided_playwright_execution_receipt_checklist.md"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE = (
    "operator_provided_playwright_execution_receipt_result.json"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

ADAPTER_DRAFT_RUN_DIR_NAME = "adapter_draft_run"
OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION = (
    "I_UNDERSTAND_THIS_RUN_IS_LOCAL_FIXTURE_ONLY_NO_LIVE_WEBSITES_NO_ACCOUNTS_"
    "NO_SCRAPING_NO_BYPASS"
)

_RECEIPT_TYPE = "operator_provided_local_playwright_execution_receipt_v1"
_RESULT_TYPE = "operator_provided_local_playwright_execution_receipt_result_v1"
_MANIFEST_TYPE = "operator_provided_local_playwright_execution_receipt_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "operator_provided_local_playwright_execution_receipt_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "operator_provided_local_playwright_execution_receipt_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_operator_provided_local_execution_receipt"
_EXECUTION_CAPABILITY = "operator_provided_local_playwright_execution_receipt_only"
_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_SOURCE_ADAPTER_DRAFT_TYPE = "bounded_playwright_worker_adapter_draft_v1"
_SOURCE_SMOKE_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_v1"
_ADAPTER_CAPABILITY = "launch_bounded_playwright_worker_adapter_draft"
_RECEIPT_ADAPTER_ID = "operator_provided_playwright_execution_receipt"
_RECEIPT_CAPABILITY = "launch_operator_provided_playwright_execution_receipt"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_INTENDED_USE = "browser_automation"

_PLAN_READY_STATUS = "operator_provided_playwright_execution_receipt_plan_ready"
_COMPLETED_STATUS = "operator_provided_playwright_execution_receipt_completed"
_FAILED_STATUS = "operator_provided_playwright_execution_receipt_failed"
_PLAN_READY_DECISION = "ready_for_operator_provided_local_fixture_execution"
_PASSED_DECISION = "operator_provided_local_fixture_execution_passed"
_FAILED_DECISION = "fix_operator_provided_local_fixture_execution_and_retry"
_PLAN_NEXT_ACTION = "run_operator_provided_local_fixture_execution"
_REVIEW_NEXT_ACTION = "review_operator_provided_playwright_execution_receipt"
_FIX_NEXT_ACTION = "fix_operator_provided_local_fixture_execution_and_retry"

_PLAN_OUTPUT_FILES = (
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE,
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
)
_ALL_OUTPUT_FILES = _PLAN_OUTPUT_FILES + (
    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE,
)

OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS: dict[str, bool] = {
    "target_url_accepted": False,
    "user_supplied_url_accepted": False,
    "live_website_automation_allowed": False,
    "arbitrary_url_navigation_allowed": False,
    "user_supplied_url_allowed": False,
    "account_workflow_allowed": False,
    "login_workflow_allowed": False,
    "registration_workflow_allowed": False,
    "scraping_allowed": False,
    "bypass_allowed": False,
    "captcha_workflow_allowed": False,
    "credential_input_allowed": False,
    "cookie_access_allowed": False,
    "external_network_allowed": False,
    "package_install_allowed": False,
    "browser_download_allowed": False,
    "npm_allowed": False,
    "npx_allowed": False,
    "candidate_repo_access_allowed": False,
    "candidate_code_import_allowed": False,
    "candidate_code_execution_allowed": False,
    "arbitrary_command_allowed": False,
    "adapter_registration_allowed": False,
    "production_promotion_allowed": False,
    "autonomous_execution_allowed": False,
}

OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS: dict[str, bool] = {
    "live_website_automation_performed": False,
    "arbitrary_url_navigation_performed": False,
    "user_supplied_url_used": False,
    "account_workflow_performed": False,
    "login_workflow_performed": False,
    "registration_workflow_performed": False,
    "scraping_performed": False,
    "bypass_performed": False,
    "captcha_workflow_performed": False,
    "credential_input_performed": False,
    "cookie_access_performed": False,
    "external_network_performed": False,
    "package_install_performed": False,
    "browser_download_performed": False,
    "npm_performed": False,
    "npx_performed": False,
    "git_clone_performed": False,
    "git_command_performed": False,
    "dependency_installation_performed": False,
    "third_party_code_execution_performed": False,
    "candidate_repo_access_performed": False,
    "candidate_code_imported": False,
    "candidate_code_execution_performed": False,
    "candidate_repo_mutation_performed": False,
    "arbitrary_command_execution_performed": False,
    "model_api_called": False,
    "secret_access_performed": False,
    "adapter_registered": False,
    "auto_adoption_performed": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}


@dataclass(frozen=True)
class OperatorProvidedPlaywrightExecutionReceiptResult:
    selection_matrix_path: Path
    playwright_candidate_manifest_path: Path
    output_dir: Path
    receipt_id: str
    adapter_draft_id: str
    plan_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    result_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    adapter_draft_run_dir: Path | None
    complete: bool
    executed: bool
    success: bool
    receipt_status: str
    payload: dict[str, object]


def build_operator_provided_playwright_execution_receipt_plan(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    receipt_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
) -> OperatorProvidedPlaywrightExecutionReceiptResult:
    """Create preflight receipt artifacts without invoking the adapter draft."""

    return _build_or_run_receipt(
        selection_matrix=selection_matrix,
        playwright_candidate_manifest=playwright_candidate_manifest,
        output_dir=output_dir,
        receipt_id=receipt_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        execute_receipt=False,
    )


def run_operator_provided_playwright_execution_receipt_launcher(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    receipt_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
    plan_only: bool = False,
) -> OperatorProvidedPlaywrightExecutionReceiptResult:
    """Launcher-oriented wrapper for plan or execution receipt creation."""

    if plan_only:
        return build_operator_provided_playwright_execution_receipt_plan(
            selection_matrix,
            playwright_candidate_manifest,
            output_dir,
            receipt_id,
            node_command=node_command,
            runner_script=runner_script,
            operator_attestation=operator_attestation,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            expected_node_version=expected_node_version,
            expected_playwright_source=expected_playwright_source,
        )
    return run_operator_provided_playwright_execution_receipt(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        receipt_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
    )


def run_operator_provided_playwright_execution_receipt(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    receipt_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
) -> OperatorProvidedPlaywrightExecutionReceiptResult:
    """Run the #421 bounded adapter draft against its embedded local fixture."""

    return _build_or_run_receipt(
        selection_matrix=selection_matrix,
        playwright_candidate_manifest=playwright_candidate_manifest,
        output_dir=output_dir,
        receipt_id=receipt_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        execute_receipt=True,
    )


def _build_or_run_receipt(
    *,
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    receipt_id: str,
    node_command: Path | None,
    runner_script: Path | None,
    operator_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    expected_node_version: str | None,
    expected_playwright_source: str | None,
    execute_receipt: bool,
) -> OperatorProvidedPlaywrightExecutionReceiptResult:
    selection_path = Path(selection_matrix)
    manifest_input_path = Path(playwright_candidate_manifest)
    output_path = Path(output_dir)
    receipt_paths = _receipt_paths(output_path)
    adapter_draft_run_dir = output_path / ADAPTER_DRAFT_RUN_DIR_NAME
    adapter_draft_id = _adapter_draft_id(receipt_id)

    preflight_error = _preflight_error(
        selection_path=selection_path,
        candidate_manifest_path=manifest_input_path,
        output_path=output_path,
        receipt_paths=receipt_paths,
        adapter_draft_run_dir=adapter_draft_run_dir,
        receipt_id=receipt_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
    )
    if preflight_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_input_path,
            output_path,
            receipt_id,
            adapter_draft_id,
            preflight_error[0],
            preflight_error[1],
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    node_path = Path(node_command)  # type: ignore[arg-type]
    runner_path = Path(runner_script)  # type: ignore[arg-type]
    selection_sha256 = sha256_file(selection_path)
    candidate_manifest_sha256 = sha256_file(manifest_input_path)
    node_sha256 = sha256_file(node_path)
    runner_sha256 = sha256_file(runner_path)
    node_size = node_path.stat().st_size
    runner_size = runner_path.stat().st_size
    runner_root = _runner_allowed_root_label(runner_path, output_path)

    status, decision, next_action = _status_decision_next_action(
        executed=execute_receipt,
        success=False,
    )
    plan = _plan_payload(
        selection_path=selection_path,
        selection_sha256=selection_sha256,
        candidate_manifest_path=manifest_input_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        output_path=output_path,
        receipt_paths=receipt_paths,
        adapter_draft_run_dir=adapter_draft_run_dir,
        receipt_id=receipt_id,
        adapter_draft_id=adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        operator_attestation=operator_attestation or "",
        node_command_path=node_path,
        node_command_sha256=node_sha256,
        node_command_size=node_size,
        runner_script_path=runner_path,
        runner_script_sha256=runner_sha256,
        runner_script_size=runner_size,
        runner_script_allowed_root=runner_root,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        executed=execute_receipt,
        success=False,
        status=status,
        decision=decision,
        next_action=next_action,
    )
    if not execute_receipt:
        _write_json_exclusive(
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE],
            plan,
        )
        _write_text_exclusive(
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE
            ],
            _summary_markdown(plan, None),
        )
        _write_text_exclusive(
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
            ],
            _checklist_markdown(plan),
        )

    adapter_result = None
    adapter_payload: dict[str, object] = {}
    adapter_error_message = None
    adapter_exception = None
    if execute_receipt:
        adapter_draft_run_dir.mkdir()
        try:
            adapter_result = (
                bounded_playwright_worker_adapter_draft.run_bounded_playwright_worker_adapter_draft(
                    selection_path,
                    manifest_input_path,
                    adapter_draft_run_dir,
                    adapter_draft_id,
                    project_id=project_id,
                    reviewer_id=reviewer_id,
                    operator_notes=operator_notes,
                    node_command=node_path,
                    runner_script=runner_path,
                    execute_local_fixture_smoke=True,
                )
            )
            adapter_payload = dict(adapter_result.payload)
        except Exception as error:  # pragma: no cover - defensive receipt evidence.
            adapter_exception = error
            adapter_error_message = _safe_text(error)
            adapter_payload = {
                "success": False,
                "failure_stage": "bounded_adapter_draft_exception",
                "error_message": adapter_error_message,
            }

        adapter_result_json = _read_json_object_if_present(
            None if adapter_result is None else adapter_result.result_path
        )
        adapter_success = bool(
            adapter_result.success if adapter_result is not None else False
        )
        status, decision, next_action = _status_decision_next_action(
            executed=True,
            success=adapter_success,
        )
        plan.update(
            {
                "receipt_status": status,
                "receipt_decision": decision,
                "next_allowed_action": next_action,
                "operator_provided_local_executable_supplied": True,
                "operator_provided_local_runner_supplied": True,
                "owned_local_smoke_runner_executed": True,
                "embedded_playwright_local_fixture_smoke_executed": True,
                "bounded_adapter_draft_wrapper_executed": True,
                "operator_provided_receipt_generated": True,
            }
        )
        _write_json_exclusive(
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE],
            plan,
        )
        result_payload = _result_payload(
            receipt_id=receipt_id,
            adapter_draft_id=adapter_draft_id,
            adapter_draft_run_dir=adapter_draft_run_dir,
            adapter_result=adapter_result,
            adapter_payload=adapter_payload,
            adapter_result_json=adapter_result_json,
            node_command_path=node_path,
            node_command_sha256=node_sha256,
            runner_script_path=runner_path,
            runner_script_sha256=runner_sha256,
            status=status,
            decision=decision,
            next_action=next_action,
            success=adapter_success,
            adapter_exception=adapter_exception,
            adapter_error_message=adapter_error_message,
        )
        _write_text_exclusive(
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE
            ],
            _summary_markdown(plan, result_payload),
        )
        _write_text_exclusive(
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
            ],
            _checklist_markdown(plan),
        )
        _write_json_exclusive(
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE],
            result_payload,
        )

    manifest = _manifest_payload(
        output_path=output_path,
        receipt_paths=receipt_paths,
        plan=plan,
        selection_matrix_path=selection_path,
        selection_matrix_sha256=selection_sha256,
        candidate_manifest_path=manifest_input_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        executed=execute_receipt,
        success=execute_receipt and bool(adapter_result and adapter_result.success),
        adapter_draft_run_dir=adapter_draft_run_dir,
    )
    _write_json_exclusive(
        receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        receipt_paths=receipt_paths,
        adapter_draft_run_dir=adapter_draft_run_dir,
        executed=execute_receipt,
        status=status,
        next_action=next_action,
    )
    _write_json_exclusive(
        receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE
        ],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        receipt_paths,
        artifact_index,
    )
    _write_json_exclusive(
        receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    success = execute_receipt and bool(adapter_result and adapter_result.success)
    complete = success if execute_receipt else True
    payload = _launcher_payload(
        output_path=output_path,
        receipt_paths=receipt_paths,
        plan=plan,
        artifact_index=artifact_index,
        executed=execute_receipt,
        success=success if execute_receipt else True,
    )
    return OperatorProvidedPlaywrightExecutionReceiptResult(
        selection_matrix_path=selection_path,
        playwright_candidate_manifest_path=manifest_input_path,
        output_dir=output_path,
        receipt_id=receipt_id,
        adapter_draft_id=adapter_draft_id,
        plan_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE
        ],
        manifest_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE
        ],
        summary_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE
        ],
        checklist_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
        ],
        result_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE
        ]
        if execute_receipt
        else None,
        artifact_index_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        adapter_draft_run_dir=adapter_draft_run_dir if execute_receipt else None,
        complete=complete,
        executed=execute_receipt,
        success=success,
        receipt_status=status,
        payload=payload,
    )


def _receipt_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _ALL_OUTPUT_FILES}


def _preflight_error(
    *,
    selection_path: Path,
    candidate_manifest_path: Path,
    output_path: Path,
    receipt_paths: dict[str, Path],
    adapter_draft_run_dir: Path,
    receipt_id: str,
    node_command: Path | None,
    runner_script: Path | None,
    operator_attestation: str | None,
) -> tuple[str, str] | None:
    output_error = _output_error(output_path, receipt_paths, adapter_draft_run_dir)
    if output_error is not None:
        return "preflight_output_dir", output_error
    if not _non_empty_text(receipt_id):
        return "preflight_receipt_id", "receipt_id is missing"
    attestation_error = _operator_attestation_error(operator_attestation)
    if attestation_error is not None:
        return "preflight_operator_attestation", attestation_error
    if node_command is None:
        return "preflight_node_command", "node_command is required"
    if runner_script is None:
        return "preflight_runner_script", "runner_script is required"
    selection_error = _json_file_error(selection_path, "selection_matrix")
    if selection_error is not None:
        return "preflight_selection_matrix", selection_error
    manifest_error = _json_file_error(
        candidate_manifest_path,
        "playwright_candidate_manifest",
    )
    if manifest_error is not None:
        return "preflight_candidate_manifest", manifest_error
    selection_payload, selection_read_error = _read_json_object(
        selection_path,
        "selection_matrix",
    )
    if selection_read_error is not None:
        return "preflight_selection_matrix", selection_read_error
    selection_validation_error = _selection_matrix_error(selection_payload)
    if selection_validation_error is not None:
        return "preflight_selection_matrix_schema", selection_validation_error
    manifest_payload, manifest_read_error = _read_json_object(
        candidate_manifest_path,
        "playwright_candidate_manifest",
    )
    if manifest_read_error is not None:
        return "preflight_candidate_manifest", manifest_read_error
    candidate_validation_error = _candidate_manifest_error(manifest_payload)
    if candidate_validation_error is not None:
        return "preflight_candidate_manifest_schema", candidate_validation_error
    node_error = _regular_file_error(Path(node_command), "node_command")
    if node_error is not None:
        return "preflight_node_command", node_error
    if Path(node_command).name.lower() in {"npm", "npx", "npm.cmd", "npx.cmd"}:
        return "preflight_node_command", "node_command must not be package runner"
    runner_error = _regular_file_error(Path(runner_script), "runner_script")
    if runner_error is not None:
        return "preflight_runner_script", runner_error
    if _runner_allowed_root_label(Path(runner_script), output_path) is None:
        return (
            "preflight_runner_script",
            "runner_script must be inside repository root or output_dir",
        )
    candidate_repo_error = _candidate_repo_runner_error(Path(runner_script))
    if candidate_repo_error is not None:
        return "preflight_runner_script", candidate_repo_error
    return None


def _output_error(
    output_path: Path,
    receipt_paths: dict[str, Path],
    adapter_draft_run_dir: Path,
) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    if os.path.lexists(adapter_draft_run_dir):
        return "adapter_draft_run directory already exists"
    for file_name in sorted(receipt_paths):
        if os.path.lexists(receipt_paths[file_name]):
            return "operator-provided Playwright receipt output already exists: " + file_name
    return None


def _operator_attestation_error(value: str | None) -> str | None:
    if not _non_empty_text(value):
        return "operator_attestation is required"
    if value != OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION:
        return "operator_attestation must match required local fixture-only phrase"
    return None


def _json_file_error(path: Path, label: str) -> str | None:
    regular_error = _regular_file_error(path, label)
    if regular_error is not None:
        return regular_error
    _payload, read_error = _read_json_object(path, label)
    return read_error


def _regular_file_error(path: Path, label: str) -> str | None:
    if not os.path.lexists(path):
        return label + " is missing"
    if path.is_symlink():
        return label + " must not be a symlink"
    if not path.is_file():
        return label + " must be a regular file"
    return None


def _selection_matrix_error(matrix: dict[str, object]) -> str | None:
    if matrix.get("matrix_type") != "real_github_candidate_selection_matrix_v1":
        return "matrix_type must be real_github_candidate_selection_matrix_v1"
    candidates = matrix.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "selection matrix candidates must be a non-empty list"
    selected = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("selected_for_first_sandbox_smoke") is True
    ]
    if len(selected) != 1:
        return "selection matrix must contain exactly one selected candidate"
    chosen = selected[0]
    if chosen.get("candidate_id") != _CANDIDATE_ID:
        return "selected candidate must be " + _CANDIDATE_ID
    if chosen.get("repo_full_name") != _REPO_FULL_NAME:
        return "selected candidate repo_full_name must be " + _REPO_FULL_NAME
    if chosen.get("decision") != "select_for_first_bounded_sandbox_smoke":
        return "selected candidate decision is not approved for this receipt"
    return None


def _candidate_manifest_error(manifest: dict[str, object]) -> str | None:
    if manifest.get("candidate_type") != "github_capability_candidate_v1":
        return "candidate_type must be github_capability_candidate_v1"
    if manifest.get("candidate_id") != _CANDIDATE_ID:
        return "candidate_id must be " + _CANDIDATE_ID
    if manifest.get("repo_full_name") != _REPO_FULL_NAME:
        return "repo_full_name must be " + _REPO_FULL_NAME
    if manifest.get("intended_use") != _INTENDED_USE:
        return "intended_use must be " + _INTENDED_USE
    domains = manifest.get("capability_domains")
    if not isinstance(domains, list) or _INTENDED_USE not in domains:
        return "candidate must include browser_automation in capability_domains"
    if not _non_empty_text(manifest.get("declared_license")):
        return "declared_license must be non-empty"
    return None


def _plan_payload(
    *,
    selection_path: Path,
    selection_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    output_path: Path,
    receipt_paths: dict[str, Path],
    adapter_draft_run_dir: Path,
    receipt_id: str,
    adapter_draft_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    operator_attestation: str,
    node_command_path: Path,
    node_command_sha256: str,
    node_command_size: int,
    runner_script_path: Path,
    runner_script_sha256: str,
    runner_script_size: int,
    runner_script_allowed_root: str | None,
    expected_node_version: str | None,
    expected_playwright_source: str | None,
    executed: bool,
    success: bool,
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_id": receipt_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "operator_attestation_present": True,
        "operator_attestation_sha256": _sha256_text(operator_attestation),
        "selection_matrix_path": selection_path.as_posix(),
        "selection_matrix_sha256": selection_sha256,
        "playwright_candidate_manifest_path": candidate_manifest_path.as_posix(),
        "playwright_candidate_manifest_sha256": candidate_manifest_sha256,
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "source_adapter_draft_type": _SOURCE_ADAPTER_DRAFT_TYPE,
        "source_smoke_type": _SOURCE_SMOKE_TYPE,
        "adapter_draft_run_dir": adapter_draft_run_dir.as_posix(),
        "node_command_path": node_command_path.as_posix(),
        "node_command_sha256": node_command_sha256,
        "node_command_size_bytes": node_command_size,
        "runner_script_path": runner_script_path.as_posix(),
        "runner_script_sha256": runner_script_sha256,
        "runner_script_size_bytes": runner_script_size,
        "runner_script_allowed_root": runner_script_allowed_root,
        "expected_node_version": expected_node_version,
        "expected_playwright_source": expected_playwright_source,
        "local_execution_scope": "file_fixture_only",
        "fixture_url_source": "generated_by_embedded_smoke",
        "fixture_url_scheme": "file",
        "executed": executed,
        "success": success,
        "execution_mode": "operator_provided_local_fixture_only"
        if executed
        else "preflight_plan_only",
        "operator_provided_local_executable_supplied": bool(executed),
        "operator_provided_local_runner_supplied": bool(executed),
        "owned_local_smoke_runner_executed": bool(executed),
        "embedded_playwright_local_fixture_smoke_executed": bool(executed),
        "bounded_adapter_draft_wrapper_executed": bool(executed),
        "operator_provided_receipt_generated": bool(executed),
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "receipt_status": status,
        "receipt_decision": decision,
        "next_allowed_action": next_action,
        "receipt_plan_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE
        ].as_posix(),
        "receipt_manifest_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE
        ].as_posix(),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }


def _result_payload(
    *,
    receipt_id: str,
    adapter_draft_id: str,
    adapter_draft_run_dir: Path,
    adapter_result,
    adapter_payload: dict[str, object],
    adapter_result_json: dict[str, object],
    node_command_path: Path,
    node_command_sha256: str,
    runner_script_path: Path,
    runner_script_sha256: str,
    status: str,
    decision: str,
    next_action: str,
    success: bool,
    adapter_exception: Exception | None,
    adapter_error_message: str | None,
) -> dict[str, object]:
    adapter_plan_path = _adapter_path(adapter_result, "plan_path")
    adapter_manifest_path = _adapter_path(adapter_result, "manifest_path")
    adapter_summary_path = _adapter_path(adapter_result, "summary_path")
    adapter_checklist_path = _adapter_path(adapter_result, "checklist_path")
    adapter_result_path = _adapter_path(adapter_result, "result_path")
    payload = {
        "result_type": _RESULT_TYPE,
        "receipt_id": receipt_id,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": True,
        "execution_mode": "operator_provided_local_fixture_only",
        "adapter_draft_run_dir": adapter_draft_run_dir.as_posix(),
        "adapter_draft_plan_path": adapter_plan_path,
        "adapter_draft_manifest_path": adapter_manifest_path,
        "adapter_draft_summary_path": adapter_summary_path,
        "adapter_draft_checklist_path": adapter_checklist_path,
        "adapter_draft_result_path": adapter_result_path,
        "embedded_smoke_plan_path": adapter_payload.get("embedded_smoke_plan_path"),
        "embedded_smoke_manifest_path": adapter_payload.get(
            "embedded_smoke_manifest_path"
        ),
        "embedded_smoke_summary_path": adapter_payload.get(
            "embedded_smoke_summary_path"
        ),
        "embedded_smoke_checklist_path": adapter_payload.get(
            "embedded_smoke_checklist_path"
        ),
        "embedded_smoke_result_path": adapter_payload.get("embedded_smoke_result_path"),
        "embedded_smoke_runner_output_path": adapter_payload.get(
            "embedded_smoke_runner_output_path"
        ),
        "embedded_smoke_screenshot_path": adapter_payload.get(
            "embedded_smoke_screenshot_path"
        ),
        "embedded_fixture_url": adapter_payload.get("embedded_fixture_url")
        or adapter_result_json.get("embedded_fixture_url"),
        "embedded_fixture_index_path": adapter_payload.get(
            "embedded_fixture_index_path"
        ),
        "embedded_fixture_app_js_path": adapter_payload.get(
            "embedded_fixture_app_js_path"
        ),
        "embedded_fixture_style_css_path": adapter_payload.get(
            "embedded_fixture_style_css_path"
        ),
        "embedded_fixture_url_scheme": "file",
        "embedded_marker_found": bool(
            adapter_result_json.get(
                "embedded_marker_found",
                adapter_payload.get("embedded_marker_found", False),
            )
        ),
        "embedded_click_completed": bool(
            adapter_result_json.get(
                "embedded_click_completed",
                adapter_payload.get("embedded_click_completed", False),
            )
        ),
        "embedded_status_text": str(
            adapter_result_json.get(
                "embedded_status_text",
                adapter_payload.get("embedded_status_text", ""),
            )
        ),
        "embedded_non_local_request_count": _int_value(
            adapter_result_json.get(
                "embedded_non_local_request_count",
                adapter_payload.get("embedded_non_local_request_count", 0),
            )
        ),
        "embedded_success": bool(
            adapter_result_json.get(
                "embedded_success",
                adapter_payload.get("embedded_success", False),
            )
        ),
        "adapter_draft_success": bool(
            adapter_result_json.get("success", adapter_payload.get("success", False))
        ),
        "success": success,
        "node_command_path": node_command_path.as_posix(),
        "node_command_sha256": node_command_sha256,
        "runner_script_path": runner_script_path.as_posix(),
        "runner_script_sha256": runner_script_sha256,
        "receipt_status": status,
        "receipt_decision": decision,
        "next_allowed_action": next_action,
        "operator_provided_local_executable_supplied": True,
        "operator_provided_local_runner_supplied": True,
        "owned_local_smoke_runner_executed": True,
        "embedded_playwright_local_fixture_smoke_executed": True,
        "bounded_adapter_draft_wrapper_executed": True,
        "operator_provided_receipt_generated": True,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }
    if adapter_exception is not None:
        payload.update(
            {
                "adapter_exception_type": adapter_exception.__class__.__name__,
                "adapter_error_message": adapter_error_message,
            }
        )
    if not success:
        payload.update(
            {
                "adapter_failure_stage": adapter_payload.get("failure_stage"),
                "adapter_error_message": adapter_payload.get("error_message")
                or adapter_error_message,
            }
        )
    return payload


def _manifest_payload(
    *,
    output_path: Path,
    receipt_paths: dict[str, Path],
    plan: dict[str, object],
    selection_matrix_path: Path,
    selection_matrix_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    executed: bool,
    success: bool,
    adapter_draft_run_dir: Path,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_id": plan["receipt_id"],
        "adapter_draft_id": plan["adapter_draft_id"],
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "selection_matrix_sha256": selection_matrix_sha256,
        "playwright_candidate_manifest_path": candidate_manifest_path.as_posix(),
        "playwright_candidate_manifest_sha256": candidate_manifest_sha256,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "node_command_path": plan["node_command_path"],
        "node_command_sha256": plan["node_command_sha256"],
        "node_command_size_bytes": plan["node_command_size_bytes"],
        "runner_script_path": plan["runner_script_path"],
        "runner_script_sha256": plan["runner_script_sha256"],
        "runner_script_size_bytes": plan["runner_script_size_bytes"],
        "adapter_draft_run_dir": adapter_draft_run_dir.as_posix(),
        "plan_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE]
        ),
        "summary_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE]
        ),
        "checklist_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
            ]
        ),
        "executed": executed,
        "success": success,
        "receipt_status": plan["receipt_status"],
        "receipt_decision": plan["receipt_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "operator_provided_local_executable_supplied": bool(executed),
        "operator_provided_local_runner_supplied": bool(executed),
        "owned_local_smoke_runner_executed": bool(executed),
        "embedded_playwright_local_fixture_smoke_executed": bool(executed),
        "bounded_adapter_draft_wrapper_executed": bool(executed),
        "operator_provided_receipt_generated": bool(executed),
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }
    if executed:
        result_path = receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE
        ]
        manifest.update(
            {
                "result_path": result_path.as_posix(),
                "result_sha256": sha256_file(result_path),
                "adapter_draft_artifacts": _artifact_hashes_under(
                    adapter_draft_run_dir,
                    output_path,
                ),
            }
        )
    return manifest


def _artifact_index_payload(
    *,
    output_path: Path,
    receipt_paths: dict[str, Path],
    adapter_draft_run_dir: Path,
    executed: bool,
    status: str,
    next_action: str,
) -> dict[str, object]:
    roles: list[tuple[str, Path]] = [
        (
            "operator_provided_playwright_execution_receipt_plan",
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE],
        ),
        (
            "operator_provided_playwright_execution_receipt_manifest",
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE
            ],
        ),
        (
            "operator_provided_playwright_execution_receipt_summary",
            receipt_paths[OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE],
        ),
        (
            "operator_provided_playwright_execution_receipt_checklist",
            receipt_paths[
                OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
            ],
        ),
    ]
    if executed:
        roles.append(
            (
                "operator_provided_playwright_execution_receipt_result",
                receipt_paths[
                    OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE
                ],
            )
        )
        roles.extend(_adapter_artifact_roles(adapter_draft_run_dir))
    entries = [
        _generated_artifact_entry(output_path, role, path)
        for role, path in roles
        if _path_is_inside_lenient(path, output_path)
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": (
            "operator_receipt_and_bounded_adapter_draft_run_artifacts_under_output_dir_only"
        ),
        "receipt_status": status,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "operator_provided_local_executable_supplied": bool(executed),
        "operator_provided_local_runner_supplied": bool(executed),
        "owned_local_smoke_runner_executed": bool(executed),
        "embedded_playwright_local_fixture_smoke_executed": bool(executed),
        "bounded_adapter_draft_wrapper_executed": bool(executed),
        "operator_provided_receipt_generated": bool(executed),
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": next_action,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    receipt_paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = receipt_paths[
        OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE
    ]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "operator_provided_local_executable_supplied": artifact_index[
            "operator_provided_local_executable_supplied"
        ],
        "operator_provided_local_runner_supplied": artifact_index[
            "operator_provided_local_runner_supplied"
        ],
        "owned_local_smoke_runner_executed": artifact_index[
            "owned_local_smoke_runner_executed"
        ],
        "embedded_playwright_local_fixture_smoke_executed": artifact_index[
            "embedded_playwright_local_fixture_smoke_executed"
        ],
        "bounded_adapter_draft_wrapper_executed": artifact_index[
            "bounded_adapter_draft_wrapper_executed"
        ],
        "operator_provided_receipt_generated": artifact_index[
            "operator_provided_receipt_generated"
        ],
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }


def _launcher_payload(
    *,
    output_path: Path,
    receipt_paths: dict[str, Path],
    plan: dict[str, object],
    artifact_index: dict[str, object],
    executed: bool,
    success: bool,
) -> dict[str, object]:
    result_path = receipt_paths[
        OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_RESULT_FILE
    ]
    payload = {
        "complete": success,
        "receipt_id": plan["receipt_id"],
        "adapter_draft_id": plan["adapter_draft_id"],
        "adapter_id": _RECEIPT_ADAPTER_ID,
        "capability": _RECEIPT_CAPABILITY,
        "output_dir": output_path.as_posix(),
        "operator_provided_playwright_execution_receipt_plan_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_PLAN_FILE
        ].as_posix(),
        "operator_provided_playwright_execution_receipt_manifest_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_MANIFEST_FILE
        ].as_posix(),
        "operator_provided_playwright_execution_receipt_summary_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "operator_provided_playwright_execution_receipt_checklist_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_CHECKLIST_FILE
        ].as_posix(),
        "operator_provided_playwright_execution_receipt_result_path": result_path.as_posix()
        if executed
        else None,
        "artifact_index_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": receipt_paths[
            OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "adapter_draft_run_dir": plan["adapter_draft_run_dir"],
        "selection_matrix_path": plan["selection_matrix_path"],
        "selection_matrix_sha256": plan["selection_matrix_sha256"],
        "playwright_candidate_manifest_path": plan[
            "playwright_candidate_manifest_path"
        ],
        "playwright_candidate_manifest_sha256": plan[
            "playwright_candidate_manifest_sha256"
        ],
        "node_command_path": plan["node_command_path"],
        "node_command_sha256": plan["node_command_sha256"],
        "runner_script_path": plan["runner_script_path"],
        "runner_script_sha256": plan["runner_script_sha256"],
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": executed,
        "success": success,
        "receipt_status": plan["receipt_status"],
        "receipt_decision": plan["receipt_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "indexed_artifacts": artifact_index["indexed_artifacts"],
        "operator_provided_local_executable_supplied": bool(executed),
        "operator_provided_local_runner_supplied": bool(executed),
        "owned_local_smoke_runner_executed": bool(executed),
        "embedded_playwright_local_fixture_smoke_executed": bool(executed),
        "bounded_adapter_draft_wrapper_executed": bool(executed),
        "operator_provided_receipt_generated": bool(executed),
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }
    if executed and result_path.exists():
        result_payload = _read_json_object_if_present(result_path)
        payload.update(
            {
                "adapter_draft_plan_path": result_payload.get(
                    "adapter_draft_plan_path"
                ),
                "adapter_draft_manifest_path": result_payload.get(
                    "adapter_draft_manifest_path"
                ),
                "adapter_draft_result_path": result_payload.get(
                    "adapter_draft_result_path"
                ),
                "adapter_draft_summary_path": result_payload.get(
                    "adapter_draft_summary_path"
                ),
                "adapter_draft_checklist_path": result_payload.get(
                    "adapter_draft_checklist_path"
                ),
                "embedded_smoke_plan_path": result_payload.get(
                    "embedded_smoke_plan_path"
                ),
                "embedded_smoke_manifest_path": result_payload.get(
                    "embedded_smoke_manifest_path"
                ),
                "embedded_smoke_summary_path": result_payload.get(
                    "embedded_smoke_summary_path"
                ),
                "embedded_smoke_checklist_path": result_payload.get(
                    "embedded_smoke_checklist_path"
                ),
                "embedded_smoke_result_path": result_payload.get(
                    "embedded_smoke_result_path"
                ),
                "embedded_smoke_runner_output_path": result_payload.get(
                    "embedded_smoke_runner_output_path"
                ),
                "embedded_smoke_screenshot_path": result_payload.get(
                    "embedded_smoke_screenshot_path"
                ),
                "embedded_fixture_url": result_payload.get("embedded_fixture_url"),
                "embedded_fixture_index_path": result_payload.get(
                    "embedded_fixture_index_path"
                ),
                "embedded_fixture_app_js_path": result_payload.get(
                    "embedded_fixture_app_js_path"
                ),
                "embedded_fixture_style_css_path": result_payload.get(
                    "embedded_fixture_style_css_path"
                ),
                "embedded_fixture_url_scheme": result_payload.get(
                    "embedded_fixture_url_scheme"
                ),
                "embedded_marker_found": result_payload.get("embedded_marker_found"),
                "embedded_click_completed": result_payload.get(
                    "embedded_click_completed"
                ),
                "embedded_status_text": result_payload.get("embedded_status_text"),
                "embedded_non_local_request_count": result_payload.get(
                    "embedded_non_local_request_count"
                ),
                "embedded_success": result_payload.get("embedded_success"),
                "adapter_draft_success": result_payload.get(
                    "adapter_draft_success"
                ),
            }
        )
    return payload


def _structured_failure_result(
    selection_matrix_path: Path,
    playwright_candidate_manifest_path: Path,
    output_path: Path,
    receipt_id: str,
    adapter_draft_id: str,
    failure_stage: str,
    error_message: str,
    *,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
) -> OperatorProvidedPlaywrightExecutionReceiptResult:
    payload = {
        "complete": False,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_id": receipt_id,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _RECEIPT_ADAPTER_ID,
        "capability": _RECEIPT_CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "playwright_candidate_manifest_path": (
            playwright_candidate_manifest_path.as_posix()
        ),
        "executed": executed,
        "success": False,
        "receipt_status": _FAILED_STATUS,
        "receipt_decision": _FAILED_DECISION,
        "next_allowed_action": _FIX_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "operator_provided_playwright_execution_receipt_plan_path": None,
        "operator_provided_playwright_execution_receipt_manifest_path": None,
        "operator_provided_playwright_execution_receipt_summary_path": None,
        "operator_provided_playwright_execution_receipt_checklist_path": None,
        "operator_provided_playwright_execution_receipt_result_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "adapter_draft_run_dir": None,
        "operator_provided_local_executable_supplied": False,
        "operator_provided_local_runner_supplied": False,
        "owned_local_smoke_runner_executed": False,
        "embedded_playwright_local_fixture_smoke_executed": False,
        "bounded_adapter_draft_wrapper_executed": False,
        "operator_provided_receipt_generated": False,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_DISABLED_FIELDS),
        **dict(OPERATOR_PROVIDED_PLAYWRIGHT_EXECUTION_RECEIPT_BOUNDARY_FALSE_FIELDS),
    }
    return OperatorProvidedPlaywrightExecutionReceiptResult(
        selection_matrix_path=selection_matrix_path,
        playwright_candidate_manifest_path=playwright_candidate_manifest_path,
        output_dir=output_path,
        receipt_id=receipt_id,
        adapter_draft_id=adapter_draft_id,
        plan_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        result_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        adapter_draft_run_dir=None,
        complete=False,
        executed=executed,
        success=False,
        receipt_status=_FAILED_STATUS,
        payload=payload,
    )


def _adapter_artifact_roles(adapter_draft_run_dir: Path) -> list[tuple[str, Path]]:
    if not adapter_draft_run_dir.exists() or not adapter_draft_run_dir.is_dir():
        return []
    roles = []
    for path in sorted(adapter_draft_run_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(adapter_draft_run_dir).as_posix()
        role = "adapter_draft_run_" + _role_slug(relative)
        roles.append((role, path))
    return roles


def _artifact_hashes_under(root_path: Path, output_path: Path) -> list[dict[str, object]]:
    entries = []
    if not root_path.exists() or not root_path.is_dir():
        return entries
    for path in sorted(root_path.rglob("*")):
        if path.is_file() and not path.is_symlink() and _path_is_inside_lenient(
            path,
            output_path,
        ):
            entries.append(
                {
                    "path": path.as_posix(),
                    "relative_path": _relative_path(path, output_path),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return entries


def _generated_artifact_entry(
    root_path: Path,
    role: str,
    path: Path,
) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": _relative_path(path, root_path),
        "extension": path.suffix,
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_repo_file": False,
        "external_candidate_artifact": False,
        "required_human_approval": True,
        "required_human_review": True,
    }


def _summary_markdown(
    plan: dict[str, object],
    result: dict[str, object] | None,
) -> str:
    lines = [
        "# Operator-Provided Playwright Execution Receipt",
        "",
        "Status: " + str(plan["receipt_status"]),
        "Receipt id: " + str(plan["receipt_id"]),
        "Candidate: microsoft/playwright",
        "Scope: local file fixture only",
        "Fixture scheme: file",
        "Execution requested: " + str(plan["executed"]).lower(),
        "Live website automation performed: false",
        "Arbitrary navigation performed: false",
        "Account workflow performed: false",
        "Scraping performed: false",
        "Bypass performed: false",
        "Captcha workflow performed: false",
        "Secret access performed: false",
        "Package installation performed: false",
        "Candidate repository access performed: false",
        "Adapter registered: false",
        "Production promotion granted: false",
        "Next allowed action: " + str(plan["next_allowed_action"]),
        "",
        "Boundary: receipt layer around the existing bounded adapter draft only.",
    ]
    if result is not None:
        lines.insert(7, "Embedded smoke success: " + str(result["embedded_success"]).lower())
        lines.insert(8, "Receipt success: " + str(result["success"]).lower())
    return "\n".join(lines)


def _checklist_markdown(plan: dict[str, object]) -> str:
    lines = [
        "# Operator-Provided Playwright Execution Receipt Checklist",
        "",
        "- [ ] Confirm the supplied executable path and hash match the operator environment.",
        "- [ ] Confirm the supplied runner path and hash match the reviewed local fixture runner.",
        "- [ ] Confirm the embedded fixture scheme is file only.",
        "- [ ] Confirm no user-supplied target is accepted.",
        "- [ ] Confirm no live websites, accounts, scraping, bypass, or captcha workflow occurred.",
        "- [ ] Confirm no secrets, cookies, package install, browser download, or package runner command occurred.",
        "- [ ] Confirm no candidate repository access or candidate code execution occurred.",
        "- [ ] Confirm adapter registration and production promotion remain disabled.",
        "",
        "Receipt decision: " + str(plan["receipt_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    return "\n".join(lines)


def _status_decision_next_action(
    *,
    executed: bool,
    success: bool,
) -> tuple[str, str, str]:
    if not executed:
        return _PLAN_READY_STATUS, _PLAN_READY_DECISION, _PLAN_NEXT_ACTION
    if success:
        return _COMPLETED_STATUS, _PASSED_DECISION, _REVIEW_NEXT_ACTION
    return _FAILED_STATUS, _FAILED_DECISION, _FIX_NEXT_ACTION


def _runner_allowed_root_label(runner_script: Path, output_dir: Path) -> str | None:
    try:
        runner_resolved = runner_script.resolve(strict=True)
    except OSError:
        return None
    if _path_is_inside(runner_resolved, output_dir):
        return "output_dir"
    if _path_is_inside(runner_resolved, _repo_root()):
        return "repo_root"
    return None


def _candidate_repo_runner_error(runner_script: Path) -> str | None:
    try:
        resolved = runner_script.resolve(strict=True)
    except OSError:
        return "runner_script is missing"
    try:
        relative_parts = resolved.relative_to(_repo_root().resolve(strict=True)).parts
    except ValueError:
        relative_parts = resolved.parts
    lowered = tuple(part.lower() for part in relative_parts)
    for index in range(len(lowered) - 1):
        if lowered[index] == "microsoft" and lowered[index + 1] == "playwright":
            return "runner_script must not be from candidate repository code"
    if "capability_candidates" in lowered:
        return "runner_script must not be from candidate repository evidence"
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _adapter_draft_id(receipt_id: str) -> str:
    if _non_empty_text(receipt_id):
        return receipt_id + "-adapter-draft"
    return "missing-receipt-id-adapter-draft"


def _adapter_path(adapter_result, attr_name: str) -> str | None:
    if adapter_result is None:
        return None
    path = getattr(adapter_result, attr_name)
    return _path_or_none(path)


def _read_json_object(path: Path, label: str) -> tuple[dict[str, object], str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return {}, label + " must be a valid JSON object: " + _safe_text(error)
    if not isinstance(payload, dict):
        return {}, label + " must be a valid JSON object"
    return payload, None


def _read_json_object_if_present(path: Path | str | None) -> dict[str, object]:
    if path is None:
        return {}
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        return {}
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else Path(path).as_posix()


def _int_value(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=True).relative_to(
            Path(root_path).resolve(strict=True)
        )
    except (OSError, ValueError):
        return False
    return True


def _path_is_inside_lenient(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _role_slug(value: str) -> str:
    chars = []
    for char in value:
        if char.isalnum():
            chars.append(char.lower())
        else:
            chars.append("_")
    return "_".join("".join(chars).split("_"))


def _safe_text(value: object) -> str:
    text = " ".join(str(value).split())
    if "Traceback (most recent call last)" in text:
        text = text.split("Traceback (most recent call last)", 1)[0].strip()
    for marker in (
        "SECRET",
        "SENTINEL",
        "TOKEN",
        "PASSWORD",
        "CREDENTIAL",
        "API_KEY",
        "BEARER",
        "COOKIE",
    ):
        if marker in text.upper():
            return "[redacted-sensitive-token]"
    return text[:240] if text else "operator-provided Playwright receipt failed"
