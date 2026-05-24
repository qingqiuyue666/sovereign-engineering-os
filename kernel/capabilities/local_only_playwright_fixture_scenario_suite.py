"""Local-only Playwright fixture scenario suite.

This module creates deterministic scenario declarations and evaluates each
scenario through the existing operator-provided local fixture receipt path. It
does not introduce a browser execution path; execution delegation is limited to
``run_operator_provided_playwright_execution_receipt``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os

from kernel.capabilities.operator_provided_playwright_execution_receipt import (
    OPERATOR_PLAYWRIGHT_LOCAL_FIXTURE_ATTESTATION,
    run_operator_provided_playwright_execution_receipt,
)
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS",
    "LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS",
    "LocalOnlyPlaywrightFixtureScenarioSuiteResult",
    "build_local_only_playwright_fixture_scenario_suite_plan",
    "run_local_only_playwright_fixture_scenario_suite",
    "run_local_only_playwright_fixture_scenario_suite_launcher",
]


LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE = (
    "local_only_playwright_fixture_scenario_suite_plan.json"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE = (
    "local_only_playwright_fixture_scenario_suite_manifest.json"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE = (
    "local_only_playwright_fixture_scenario_suite_summary.md"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE = (
    "local_only_playwright_fixture_scenario_suite_checklist.md"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE = (
    "local_only_playwright_fixture_scenario_suite_result.json"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME = "scenarios"
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_OPERATOR_RECEIPT_DIR_NAME = (
    "operator_receipt"
)
LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE = (
    "scenario_result.json"
)

_SUITE_TYPE = "local_only_playwright_fixture_scenario_suite_v1"
_RESULT_TYPE = "local_only_playwright_fixture_scenario_suite_result_v1"
_MANIFEST_TYPE = "local_only_playwright_fixture_scenario_suite_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "local_only_playwright_fixture_scenario_suite_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_only_playwright_fixture_scenario_suite_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_local_only_playwright_fixture_scenario_suite_record"
_EXECUTION_CAPABILITY = "local_only_playwright_fixture_scenario_suite_only"
_ADAPTER_ID = "local_only_playwright_fixture_scenario_suite"
_CAPABILITY = "launch_local_only_playwright_fixture_scenario_suite"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_SOURCE_RECEIPT_TYPE = "operator_provided_local_playwright_execution_receipt_v1"
_SOURCE_ADAPTER_DRAFT_TYPE = "bounded_playwright_worker_adapter_draft_v1"
_SOURCE_SMOKE_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_v1"
_INTENDED_USE = "browser_automation"
_LOCAL_EXECUTION_SCOPE = "file_fixture_only"
_FIXTURE_SCHEME = "file"

_PLAN_READY_STATUS = "local_only_playwright_fixture_scenario_suite_plan_ready"
_COMPLETED_STATUS = "local_only_playwright_fixture_scenario_suite_completed"
_FAILED_STATUS = "local_only_playwright_fixture_scenario_suite_failed"
_PLAN_READY_DECISION = "ready_to_run_local_only_playwright_fixture_scenario_suite"
_PASSED_DECISION = "local_only_playwright_fixture_scenario_suite_passed"
_FAILED_DECISION = "fix_local_only_playwright_fixture_scenario_suite_and_retry"
_PLAN_NEXT_ACTION = "run_local_only_playwright_fixture_scenario_suite"
_REVIEW_NEXT_ACTION = "review_local_only_playwright_fixture_scenario_suite"
_FIX_NEXT_ACTION = "fix_local_only_playwright_fixture_scenario_suite_and_retry"

_PLAN_OUTPUT_FILES = (
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE,
)
_ALL_OUTPUT_FILES = _PLAN_OUTPUT_FILES + (
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE,
)

_RECEIPT_PLAN_FILE = "operator_provided_playwright_execution_receipt_plan.json"
_RECEIPT_MANIFEST_FILE = "operator_provided_playwright_execution_receipt_manifest.json"
_RECEIPT_RESULT_FILE = "operator_provided_playwright_execution_receipt_result.json"
_RECEIPT_ARTIFACT_INDEX_FILE = "artifact_index.json"
_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_ADAPTER_DRAFT_RUN_DIR = "adapter_draft_run"
_ADAPTER_PLAN_FILE = "bounded_playwright_worker_adapter_draft_plan.json"
_ADAPTER_MANIFEST_FILE = "bounded_playwright_worker_adapter_draft_manifest.json"
_ADAPTER_RESULT_FILE = "bounded_playwright_worker_adapter_draft_result.json"
_ADAPTER_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ADAPTER_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_EMBEDDED_SMOKE_DIR = "embedded_smoke"
_SMOKE_PLAN_FILE = "playwright_local_fixture_sandbox_smoke_plan.json"
_SMOKE_MANIFEST_FILE = "playwright_local_fixture_sandbox_smoke_manifest.json"
_SMOKE_RESULT_FILE = "playwright_local_fixture_sandbox_smoke_result.json"
_SMOKE_RUNNER_OUTPUT_FILE = "playwright_local_fixture_sandbox_smoke_runner_output.json"
_SMOKE_ARTIFACT_INDEX_FILE = "artifact_index.json"
_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_FIXTURE_DIR = "fixture"
_FIXTURE_INDEX_FILE = "index.html"
_FIXTURE_APP_FILE = "app.js"
_FIXTURE_STYLE_FILE = "style.css"

LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS: dict[str, bool] = {
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
    "production_admission_granted": False,
    "live_website_admission_granted": False,
    "general_browser_automation_admission_granted": False,
}

LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS: dict[str, bool] = {
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

_FALSE_FIELD_NAMES = frozenset(
    tuple(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS)
    + tuple(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS)
    + (
        "target_url_accepted",
        "user_supplied_url_accepted",
        "adapter_generation_allowed",
        "adapter_generated",
        "auto_adoption_allowed",
        "production_promotion_performed",
        "candidate_code_import_performed",
        "secret_access_allowed",
        "cookie_access_admission_granted",
        "arbitrary_url_navigation_admission_granted",
    )
)


@dataclass(frozen=True)
class LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    selection_matrix_path: Path
    playwright_candidate_manifest_path: Path
    output_dir: Path
    suite_id: str
    scenario_set: str
    plan_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    result_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    scenarios_dir: Path | None
    complete: bool
    executed: bool
    success: bool
    suite_status: str
    payload: dict[str, object]


def build_local_only_playwright_fixture_scenario_suite_plan(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    suite_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
    scenario_set: str = "core",
) -> LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    """Create suite plan artifacts without running operator receipt scenarios."""

    return _build_or_run_suite(
        selection_matrix=selection_matrix,
        playwright_candidate_manifest=playwright_candidate_manifest,
        output_dir=output_dir,
        suite_id=suite_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        scenario_set=scenario_set,
        execute_suite=False,
    )


def run_local_only_playwright_fixture_scenario_suite_launcher(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    suite_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
    scenario_set: str = "core",
    plan_only: bool = False,
) -> LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    """Launcher-oriented wrapper for suite plan or execution."""

    if plan_only:
        return build_local_only_playwright_fixture_scenario_suite_plan(
            selection_matrix,
            playwright_candidate_manifest,
            output_dir,
            suite_id,
            node_command=node_command,
            runner_script=runner_script,
            operator_attestation=operator_attestation,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            expected_node_version=expected_node_version,
            expected_playwright_source=expected_playwright_source,
            scenario_set=scenario_set,
        )
    return run_local_only_playwright_fixture_scenario_suite(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        suite_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        scenario_set=scenario_set,
    )


def run_local_only_playwright_fixture_scenario_suite(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    suite_id: str,
    *,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    operator_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    expected_node_version: str | None = None,
    expected_playwright_source: str | None = None,
    scenario_set: str = "core",
) -> LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    """Run all planned local-only scenarios through #422 receipt delegation."""

    return _build_or_run_suite(
        selection_matrix=selection_matrix,
        playwright_candidate_manifest=playwright_candidate_manifest,
        output_dir=output_dir,
        suite_id=suite_id,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        scenario_set=scenario_set,
        execute_suite=True,
    )


def _build_or_run_suite(
    *,
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    suite_id: str,
    node_command: Path | None,
    runner_script: Path | None,
    operator_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    expected_node_version: str | None,
    expected_playwright_source: str | None,
    scenario_set: str,
    execute_suite: bool,
) -> LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    selection_path = Path(selection_matrix)
    manifest_input_path = Path(playwright_candidate_manifest)
    output_path = Path(output_dir)
    normalized_scenario_set = scenario_set if scenario_set in {"core", "extended"} else scenario_set
    suite_paths = _suite_paths(output_path)
    scenarios_dir = output_path / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME
    planned_scenarios = (
        _planned_scenarios(scenario_set)
        if scenario_set in {"core", "extended"}
        else ()
    )

    preflight_error = _preflight_error(
        selection_path=selection_path,
        candidate_manifest_path=manifest_input_path,
        output_path=output_path,
        suite_paths=suite_paths,
        scenarios_dir=scenarios_dir,
        suite_id=suite_id,
        scenario_set=scenario_set,
        node_command=node_command,
        runner_script=runner_script,
        operator_attestation=operator_attestation,
    )
    if preflight_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_input_path,
            output_path,
            suite_id,
            normalized_scenario_set,
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

    scenario_results: list[dict[str, object]] = []
    receipt_failures: dict[str, str] = {}
    if execute_suite:
        scenarios_dir.mkdir()
        for scenario in planned_scenarios:
            scenario_dir = scenarios_dir / str(scenario["scenario_id"])
            receipt_dir = scenario_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_OPERATOR_RECEIPT_DIR_NAME
            scenario_dir.mkdir()
            receipt_dir.mkdir()
            try:
                run_operator_provided_playwright_execution_receipt(
                    selection_path,
                    manifest_input_path,
                    receipt_dir,
                    _receipt_id(suite_id, str(scenario["scenario_id"])),
                    node_command=node_path,
                    runner_script=runner_path,
                    operator_attestation=operator_attestation,
                    project_id=project_id,
                    reviewer_id=reviewer_id,
                    operator_notes=operator_notes,
                    expected_node_version=expected_node_version,
                    expected_playwright_source=expected_playwright_source,
                )
            except Exception as error:  # pragma: no cover - defensive evidence.
                receipt_failures[str(scenario["scenario_id"])] = _safe_text(error)

        for scenario in planned_scenarios:
            scenario_id = str(scenario["scenario_id"])
            scenario_dir = scenarios_dir / scenario_id
            receipt_dir = (
                scenario_dir
                / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_OPERATOR_RECEIPT_DIR_NAME
            )
            result_payload = _scenario_result_payload(
                scenario,
                scenario_dir=scenario_dir,
                receipt_dir=receipt_dir,
            )
            if scenario_id in receipt_failures:
                result_payload["success"] = False
                result_payload["failure_reasons"] = list(
                    result_payload["failure_reasons"]
                ) + ["operator_receipt_exception:" + receipt_failures[scenario_id]]
            scenario_results.append(result_payload)

        _apply_repeated_equivalence(scenario_results)
        for result_payload in scenario_results:
            _write_json_exclusive(
                Path(str(result_payload["scenario_dir"]))
                / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE,
                result_payload,
            )

    scenario_count_executed = len(scenario_results)
    scenario_count_passed = sum(1 for item in scenario_results if item["success"] is True)
    scenario_count_failed = scenario_count_executed - scenario_count_passed
    suite_success = bool(
        execute_suite
        and scenario_count_executed == len(planned_scenarios)
        and scenario_count_failed == 0
    )
    status, decision, next_action = _status_decision_next_action(
        executed=execute_suite,
        success=suite_success,
    )
    plan = _plan_payload(
        selection_path=selection_path,
        selection_sha256=selection_sha256,
        candidate_manifest_path=manifest_input_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        output_path=output_path,
        suite_paths=suite_paths,
        scenarios_dir=scenarios_dir if execute_suite else None,
        suite_id=suite_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        operator_attestation=operator_attestation or "",
        node_path=node_path,
        node_sha256=node_sha256,
        runner_path=runner_path,
        runner_sha256=runner_sha256,
        expected_node_version=expected_node_version,
        expected_playwright_source=expected_playwright_source,
        scenario_set=scenario_set,
        planned_scenarios=planned_scenarios,
        executed=execute_suite,
        status=status,
        decision=decision,
        next_action=next_action,
    )
    _write_json_exclusive(
        suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE],
        plan,
    )

    result_payload = None
    if execute_suite:
        result_payload = _result_payload(
            suite_id=suite_id,
            scenario_set=scenario_set,
            planned_count=len(planned_scenarios),
            scenario_results=scenario_results,
            suite_success=suite_success,
            status=status,
            decision=decision,
            next_action=next_action,
        )
        _write_json_exclusive(
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE],
            result_payload,
        )

    _write_text_exclusive(
        suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE],
        _summary_markdown(plan, result_payload),
    )
    _write_text_exclusive(
        suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE],
        _checklist_markdown(plan, result_payload),
    )
    manifest = _manifest_payload(
        output_path=output_path,
        suite_paths=suite_paths,
        plan=plan,
        result=result_payload,
        executed=execute_suite,
        success=suite_success,
    )
    _write_json_exclusive(
        suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        suite_paths=suite_paths,
        executed=execute_suite,
        status=status,
        next_action=next_action,
    )
    _write_json_exclusive(
        suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE
        ],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        suite_paths,
        artifact_index,
    )
    _write_json_exclusive(
        suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(
        output_path=output_path,
        suite_paths=suite_paths,
        plan=plan,
        result=result_payload,
        artifact_index=artifact_index,
        executed=execute_suite,
        complete=suite_success if execute_suite else True,
    )
    return LocalOnlyPlaywrightFixtureScenarioSuiteResult(
        selection_matrix_path=selection_path,
        playwright_candidate_manifest_path=manifest_input_path,
        output_dir=output_path,
        suite_id=suite_id,
        scenario_set=scenario_set,
        plan_path=suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE],
        manifest_path=suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE
        ],
        summary_path=suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE
        ],
        checklist_path=suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE
        ],
        result_path=suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE]
        if execute_suite
        else None,
        artifact_index_path=suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        scenarios_dir=scenarios_dir if execute_suite else None,
        complete=suite_success if execute_suite else True,
        executed=execute_suite,
        success=suite_success,
        suite_status=status,
        payload=payload,
    )


def _suite_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _ALL_OUTPUT_FILES}


def _preflight_error(
    *,
    selection_path: Path,
    candidate_manifest_path: Path,
    output_path: Path,
    suite_paths: dict[str, Path],
    scenarios_dir: Path,
    suite_id: str,
    scenario_set: str,
    node_command: Path | None,
    runner_script: Path | None,
    operator_attestation: str | None,
) -> tuple[str, str] | None:
    output_error = _output_error(output_path, suite_paths, scenarios_dir)
    if output_error is not None:
        return "preflight_output_dir", output_error
    if not _non_empty_text(suite_id):
        return "preflight_suite_id", "suite_id is missing"
    if scenario_set not in {"core", "extended"}:
        return "preflight_scenario_set", "scenario_set must be core or extended"
    attestation_error = _operator_attestation_error(operator_attestation)
    if attestation_error is not None:
        return "preflight_operator_attestation", attestation_error
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
    if node_command is None:
        return "preflight_node_command", "node_command is required"
    if runner_script is None:
        return "preflight_runner_script", "runner_script is required"
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
    suite_paths: dict[str, Path],
    scenarios_dir: Path,
) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    if os.path.lexists(scenarios_dir):
        return "scenarios directory already exists"
    for file_name in sorted(suite_paths):
        if os.path.lexists(suite_paths[file_name]):
            return "local-only Playwright fixture scenario suite output already exists: " + file_name
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
        return "selected candidate decision is not approved for this suite"
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


def _planned_scenarios(scenario_set: str) -> tuple[dict[str, object], ...]:
    scenarios: list[dict[str, object]] = [
        {
            "scenario_id": "static_click_marker",
            "scenario_type": "static_click_marker",
            "purpose": "baseline click marker on local file fixture",
            "requires_marker": True,
            "requires_click": True,
            "requires_status_text": True,
        },
        {
            "scenario_id": "repeated_local_fixture_execution_a",
            "scenario_type": "repeated_local_fixture_execution",
            "purpose": "deterministic rerun proof first independent receipt",
            "requires_marker": True,
            "requires_click": True,
            "requires_status_text": True,
        },
        {
            "scenario_id": "repeated_local_fixture_execution_b",
            "scenario_type": "repeated_local_fixture_execution",
            "purpose": "deterministic rerun proof second independent receipt",
            "requires_marker": True,
            "requires_click": True,
            "requires_status_text": True,
        },
    ]
    if scenario_set == "extended":
        scenarios.extend(
            [
                {
                    "scenario_id": "output_integrity_scenario",
                    "scenario_type": "output_integrity_scenario",
                    "purpose": "verify required receipt files and artifact indexes exist",
                    "requires_marker": True,
                    "requires_click": True,
                    "requires_status_text": True,
                },
                {
                    "scenario_id": "boundary_false_scenario",
                    "scenario_type": "boundary_false_scenario",
                    "purpose": "verify false boundaries remain false across artifacts",
                    "requires_marker": True,
                    "requires_click": True,
                    "requires_status_text": True,
                },
            ]
        )
    return tuple(scenarios)


def _plan_payload(
    *,
    selection_path: Path,
    selection_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    output_path: Path,
    suite_paths: dict[str, Path],
    scenarios_dir: Path | None,
    suite_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    operator_attestation: str,
    node_path: Path,
    node_sha256: str,
    runner_path: Path,
    runner_sha256: str,
    expected_node_version: str | None,
    expected_playwright_source: str | None,
    scenario_set: str,
    planned_scenarios: tuple[dict[str, object], ...],
    executed: bool,
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "suite_type": _SUITE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "suite_id": suite_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "operator_attestation_present": True,
        "operator_attestation_sha256": _sha256_text(operator_attestation),
        "scenario_set": scenario_set,
        "scenario_count_planned": len(planned_scenarios),
        "planned_scenarios": [dict(scenario) for scenario in planned_scenarios],
        "selection_matrix_path": selection_path.as_posix(),
        "selection_matrix_sha256": selection_sha256,
        "playwright_candidate_manifest_path": candidate_manifest_path.as_posix(),
        "playwright_candidate_manifest_sha256": candidate_manifest_sha256,
        "node_command_path": node_path.as_posix(),
        "node_command_sha256": node_sha256,
        "node_command_size_bytes": node_path.stat().st_size,
        "runner_script_path": runner_path.as_posix(),
        "runner_script_sha256": runner_sha256,
        "runner_script_size_bytes": runner_path.stat().st_size,
        "runner_script_allowed_root": _runner_allowed_root_label(runner_path, output_path),
        "expected_node_version": expected_node_version,
        "expected_playwright_source": expected_playwright_source,
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_receipt_type": _SOURCE_RECEIPT_TYPE,
        "source_adapter_draft_type": _SOURCE_ADAPTER_DRAFT_TYPE,
        "source_smoke_type": _SOURCE_SMOKE_TYPE,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "fixture_scheme": _FIXTURE_SCHEME,
        "suite_status": status,
        "suite_decision": decision,
        "next_allowed_action": next_action,
        "executed": executed,
        "execution_mode": "operator_provided_receipt_scenario_suite" if executed else "plan_only",
        "scenarios_dir": None if scenarios_dir is None else scenarios_dir.as_posix(),
        "suite_plan_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE
        ].as_posix(),
        "suite_manifest_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE
        ].as_posix(),
        "suite_result_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE
        ].as_posix()
        if executed
        else None,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }


def _result_payload(
    *,
    suite_id: str,
    scenario_set: str,
    planned_count: int,
    scenario_results: list[dict[str, object]],
    suite_success: bool,
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "result_type": _RESULT_TYPE,
        "suite_id": suite_id,
        "scenario_set": scenario_set,
        "scenario_count_planned": planned_count,
        "scenario_count_executed": len(scenario_results),
        "scenario_count_passed": sum(
            1 for scenario in scenario_results if scenario["success"] is True
        ),
        "scenario_count_failed": sum(
            1 for scenario in scenario_results if scenario["success"] is not True
        ),
        "scenario_results": scenario_results,
        "suite_success": suite_success,
        "suite_status": status,
        "suite_decision": decision,
        "next_allowed_action": next_action,
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }


def _manifest_payload(
    *,
    output_path: Path,
    suite_paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object] | None,
    executed: bool,
    success: bool,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "suite_id": plan["suite_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "scenario_set": plan["scenario_set"],
        "scenario_count_planned": plan["scenario_count_planned"],
        "plan_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE]
        ),
        "summary_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE]
        ),
        "checklist_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE]
        ),
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
        "node_command_size_bytes": plan["node_command_size_bytes"],
        "runner_script_path": plan["runner_script_path"],
        "runner_script_sha256": plan["runner_script_sha256"],
        "runner_script_size_bytes": plan["runner_script_size_bytes"],
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_receipt_type": _SOURCE_RECEIPT_TYPE,
        "source_adapter_draft_type": _SOURCE_ADAPTER_DRAFT_TYPE,
        "source_smoke_type": _SOURCE_SMOKE_TYPE,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "executed": executed,
        "success": success,
        "suite_status": plan["suite_status"],
        "suite_decision": plan["suite_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }
    if result is not None:
        result_path = suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE]
        manifest.update(
            {
                "result_path": result_path.as_posix(),
                "result_sha256": sha256_file(result_path),
                "scenario_count_executed": result["scenario_count_executed"],
                "scenario_count_passed": result["scenario_count_passed"],
                "scenario_count_failed": result["scenario_count_failed"],
                "suite_success": result["suite_success"],
            }
        )
    return manifest


def _artifact_index_payload(
    *,
    output_path: Path,
    suite_paths: dict[str, Path],
    executed: bool,
    status: str,
    next_action: str,
) -> dict[str, object]:
    entries = [
        _generated_artifact_entry(output_path, role, path)
        for role, path in _suite_artifact_roles(output_path, suite_paths, executed)
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "suite_and_scenario_receipt_artifacts_under_output_dir_only",
        "suite_status": status,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": next_action,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    suite_paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = suite_paths[
        LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE
    ]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
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
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }


def _suite_artifact_roles(
    output_path: Path,
    suite_paths: dict[str, Path],
    executed: bool,
) -> list[tuple[str, Path]]:
    roles = [
        (
            "local_only_playwright_fixture_scenario_suite_plan",
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE],
        ),
        (
            "local_only_playwright_fixture_scenario_suite_manifest",
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE],
        ),
        (
            "local_only_playwright_fixture_scenario_suite_summary",
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE],
        ),
        (
            "local_only_playwright_fixture_scenario_suite_checklist",
            suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE],
        ),
    ]
    result_path = suite_paths[LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE]
    if executed and result_path.exists():
        roles.append(
            (
                "local_only_playwright_fixture_scenario_suite_result",
                result_path,
            )
        )
    scenarios_dir = output_path / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIOS_DIR_NAME
    if executed and scenarios_dir.exists() and scenarios_dir.is_dir():
        for path in sorted(scenarios_dir.rglob("*")):
            if path.is_file() and not path.is_symlink():
                roles.append(("scenario_suite_" + _role_slug(_relative_path(path, output_path) or path.name), path))
    return roles


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


def _scenario_result_payload(
    scenario: dict[str, object],
    *,
    scenario_dir: Path,
    receipt_dir: Path,
) -> dict[str, object]:
    paths = _receipt_paths(receipt_dir)
    payloads, errors = _load_receipt_payloads(paths)
    metrics = _scenario_metrics(paths, payloads, receipt_dir, scenario_dir)
    failure_reasons = _scenario_failure_reasons(scenario, metrics, errors, paths)
    success = not failure_reasons
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_type": scenario["scenario_type"],
        "scenario_dir": scenario_dir.as_posix(),
        "operator_receipt_dir": receipt_dir.as_posix(),
        "operator_receipt_result_path": paths["receipt_result"].as_posix(),
        "adapter_draft_result_path": paths["adapter_draft_result"].as_posix(),
        "embedded_smoke_result_path": paths["embedded_smoke_result"].as_posix(),
        "success": success,
        "receipt_success": bool(metrics["receipt_success"]),
        "adapter_draft_success": bool(metrics["adapter_draft_success"]),
        "embedded_smoke_success": bool(metrics["embedded_smoke_success"]),
        "embedded_fixture_url": metrics["embedded_fixture_url"],
        "embedded_fixture_url_scheme": metrics["embedded_fixture_url_scheme"],
        "embedded_marker_found": bool(metrics["embedded_marker_found"]),
        "embedded_click_completed": bool(metrics["embedded_click_completed"]),
        "embedded_status_text": metrics["embedded_status_text"],
        "embedded_non_local_request_count": metrics[
            "embedded_non_local_request_count"
        ],
        "artifact_index_under_scenario_dir": bool(
            metrics["artifact_index_under_scenario_dir"]
        ),
        "candidate_repo_files_indexed": bool(metrics["candidate_repo_files_indexed"]),
        "external_candidate_artifacts_indexed": bool(
            metrics["external_candidate_artifacts_indexed"]
        ),
        "all_boundaries_false": bool(metrics["all_boundaries_false"]),
        "artifact_hashes_verified": bool(metrics["artifact_hashes_verified"]),
        "fixture_files_exist": bool(metrics["fixture_files_exist"]),
        "required_receipt_files_exist": bool(metrics["required_receipt_files_exist"]),
        "artifact_index_paths_have_no_symlink": bool(
            metrics["artifact_index_paths_have_no_symlink"]
        ),
        "candidate_repo_files_indexed_expected_false": False,
        "external_candidate_artifacts_indexed_expected_false": False,
        "failure_reasons": failure_reasons,
    }


def _receipt_paths(receipt_dir: Path) -> dict[str, Path]:
    adapter_dir = receipt_dir / _ADAPTER_DRAFT_RUN_DIR
    embedded_dir = adapter_dir / _EMBEDDED_SMOKE_DIR
    fixture_dir = embedded_dir / _FIXTURE_DIR
    return {
        "receipt_plan": receipt_dir / _RECEIPT_PLAN_FILE,
        "receipt_manifest": receipt_dir / _RECEIPT_MANIFEST_FILE,
        "receipt_result": receipt_dir / _RECEIPT_RESULT_FILE,
        "receipt_artifact_index": receipt_dir / _RECEIPT_ARTIFACT_INDEX_FILE,
        "receipt_artifact_index_manifest": receipt_dir
        / _RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
        "adapter_draft_run_dir": adapter_dir,
        "adapter_draft_plan": adapter_dir / _ADAPTER_PLAN_FILE,
        "adapter_draft_manifest": adapter_dir / _ADAPTER_MANIFEST_FILE,
        "adapter_draft_result": adapter_dir / _ADAPTER_RESULT_FILE,
        "adapter_draft_artifact_index": adapter_dir / _ADAPTER_ARTIFACT_INDEX_FILE,
        "adapter_draft_artifact_index_manifest": adapter_dir
        / _ADAPTER_ARTIFACT_INDEX_MANIFEST_FILE,
        "embedded_smoke_dir": embedded_dir,
        "embedded_smoke_plan": embedded_dir / _SMOKE_PLAN_FILE,
        "embedded_smoke_manifest": embedded_dir / _SMOKE_MANIFEST_FILE,
        "embedded_smoke_result": embedded_dir / _SMOKE_RESULT_FILE,
        "embedded_smoke_runner_output": embedded_dir / _SMOKE_RUNNER_OUTPUT_FILE,
        "embedded_smoke_artifact_index": embedded_dir / _SMOKE_ARTIFACT_INDEX_FILE,
        "embedded_smoke_artifact_index_manifest": embedded_dir
        / _SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
        "fixture_index": fixture_dir / _FIXTURE_INDEX_FILE,
        "fixture_app": fixture_dir / _FIXTURE_APP_FILE,
        "fixture_style": fixture_dir / _FIXTURE_STYLE_FILE,
    }


def _load_receipt_payloads(
    paths: dict[str, Path],
) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    labels = {
        "receipt_plan": "receipt plan",
        "receipt_manifest": "receipt manifest",
        "receipt_result": "receipt result",
        "receipt_artifact_index": "receipt artifact index",
        "receipt_artifact_index_manifest": "receipt artifact index manifest",
        "adapter_draft_plan": "adapter draft plan",
        "adapter_draft_manifest": "adapter draft manifest",
        "adapter_draft_result": "adapter draft result",
        "adapter_draft_artifact_index": "adapter draft artifact index",
        "adapter_draft_artifact_index_manifest": "adapter draft artifact index manifest",
        "embedded_smoke_plan": "embedded smoke plan",
        "embedded_smoke_manifest": "embedded smoke manifest",
        "embedded_smoke_result": "embedded smoke result",
        "embedded_smoke_runner_output": "embedded smoke runner output",
        "embedded_smoke_artifact_index": "embedded smoke artifact index",
        "embedded_smoke_artifact_index_manifest": "embedded smoke artifact index manifest",
    }
    payloads: dict[str, dict[str, object]] = {}
    errors: dict[str, str] = {}
    for key, label in labels.items():
        payload, error = _read_json_object(paths[key], label)
        payloads[key] = payload
        if error is not None:
            errors[key] = error
    return payloads, errors


def _scenario_metrics(
    paths: dict[str, Path],
    payloads: dict[str, dict[str, object]],
    receipt_dir: Path,
    scenario_dir: Path,
) -> dict[str, object]:
    fixture_reference = _first_text(
        payloads["receipt_result"].get("embedded_fixture_url"),
        payloads["adapter_draft_result"].get("embedded_fixture_url"),
        payloads["embedded_smoke_result"].get("fixture_url"),
        payloads["embedded_smoke_runner_output"].get("fixture_url"),
        payloads["embedded_smoke_plan"].get("fixture_url"),
    )
    scheme_values = [
        value
        for value in (
            _text_or_none(payloads["receipt_result"].get("embedded_fixture_url_scheme")),
            _text_or_none(payloads["adapter_draft_result"].get("embedded_fixture_url_scheme")),
            _text_or_none(payloads["adapter_draft_plan"].get("embedded_fixture_url_scheme")),
            _text_or_none(payloads["embedded_smoke_result"].get("fixture_url_scheme")),
            _text_or_none(payloads["embedded_smoke_runner_output"].get("fixture_url_scheme")),
            _text_or_none(payloads["embedded_smoke_plan"].get("fixture_url_scheme")),
        )
        if value
    ]
    if fixture_reference:
        scheme_values.append(_scheme_from_reference(fixture_reference))
    fixture_scheme_file = bool(scheme_values) and all(
        value == _FIXTURE_SCHEME for value in scheme_values
    )
    marker_values = _present_bool_values(
        payloads["receipt_result"].get("embedded_marker_found"),
        payloads["adapter_draft_result"].get("embedded_marker_found"),
        payloads["embedded_smoke_result"].get("marker_found"),
        payloads["embedded_smoke_runner_output"].get("marker_found"),
    )
    click_values = _present_bool_values(
        payloads["receipt_result"].get("embedded_click_completed"),
        payloads["adapter_draft_result"].get("embedded_click_completed"),
        payloads["embedded_smoke_result"].get("click_completed"),
        payloads["embedded_smoke_runner_output"].get("click_completed"),
    )
    status_values = [
        value
        for value in (
            _text_or_none(payloads["receipt_result"].get("embedded_status_text")),
            _text_or_none(payloads["adapter_draft_result"].get("embedded_status_text")),
            _text_or_none(payloads["embedded_smoke_result"].get("status_text")),
            _text_or_none(payloads["embedded_smoke_runner_output"].get("status_text")),
        )
        if value is not None
    ]
    non_local_counts = [
        _int_or_none(payload.get(field_name))
        for payload in (
            payloads["receipt_result"],
            payloads["adapter_draft_result"],
            payloads["embedded_smoke_result"],
            payloads["embedded_smoke_runner_output"],
        )
        for field_name in ("embedded_non_local_request_count", "non_local_request_count")
    ]
    present_counts = [value for value in non_local_counts if value is not None]
    index_verifications = [
        _verify_index_payload(payloads[key], scenario_dir)
        for key in (
            "receipt_artifact_index",
            "adapter_draft_artifact_index",
            "embedded_smoke_artifact_index",
        )
    ]
    manifest_hashes = [
        _verify_manifest_hashes(payloads[key], scenario_dir)
        for key in (
            "receipt_manifest",
            "adapter_draft_manifest",
            "embedded_smoke_manifest",
        )
    ]
    required_receipt_files = (
        "receipt_plan",
        "receipt_manifest",
        "receipt_result",
        "receipt_artifact_index",
        "receipt_artifact_index_manifest",
        "adapter_draft_result",
        "embedded_smoke_result",
    )
    fixture_files = ("fixture_index", "fixture_app", "fixture_style")
    return {
        "receipt_success": payloads["receipt_result"].get("success") is True,
        "adapter_draft_success": payloads["adapter_draft_result"].get("success") is True,
        "embedded_smoke_success": payloads["embedded_smoke_result"].get("success") is True,
        "embedded_fixture_url": fixture_reference,
        "embedded_fixture_url_scheme": scheme_values[0] if scheme_values else None,
        "embedded_fixture_scheme_file": fixture_scheme_file,
        "embedded_marker_found": bool(marker_values) and all(marker_values),
        "embedded_click_completed": bool(click_values) and all(click_values),
        "embedded_status_text": status_values[0] if status_values else "",
        "embedded_status_text_nonempty": bool(status_values)
        and all(bool(value.strip()) for value in status_values),
        "embedded_non_local_request_count": present_counts[0] if present_counts else None,
        "embedded_non_local_request_count_zero": bool(present_counts)
        and all(value == 0 for value in present_counts),
        "required_receipt_files_exist": all(_regular_file_ok(paths[key]) for key in required_receipt_files),
        "fixture_files_exist": all(_regular_file_ok(paths[key]) for key in fixture_files),
        "artifact_index_under_scenario_dir": all(
            verification["paths_under_scenario_dir"] for verification in index_verifications
        )
        and _path_is_inside(paths["receipt_artifact_index"], scenario_dir),
        "artifact_index_paths_have_no_symlink": all(
            verification["no_symlink_paths"] for verification in index_verifications
        ),
        "candidate_repo_files_indexed": any(
            verification["candidate_repo_files_indexed"] for verification in index_verifications
        ),
        "external_candidate_artifacts_indexed": any(
            verification["external_candidate_artifacts_indexed"] for verification in index_verifications
        ),
        "artifact_hashes_verified": all(
            verification["all_hashes_match"] for verification in index_verifications
        )
        and all(manifest_hashes),
        "all_boundaries_false": not _true_fields(payloads),
        "receipt_dir_under_scenario_dir": _path_is_inside(receipt_dir, scenario_dir),
    }


def _scenario_failure_reasons(
    scenario: dict[str, object],
    metrics: dict[str, object],
    errors: dict[str, str],
    paths: dict[str, Path],
) -> list[str]:
    reasons = []
    for key in sorted(errors):
        reasons.append(key + ":" + errors[key])
    checks = (
        ("receipt_success", "receipt_success_false"),
        ("adapter_draft_success", "adapter_draft_success_false"),
        ("embedded_smoke_success", "embedded_smoke_success_false"),
        ("embedded_fixture_scheme_file", "embedded_fixture_scheme_not_file"),
        (
            "embedded_non_local_request_count_zero",
            "embedded_non_local_request_count_not_zero",
        ),
        ("required_receipt_files_exist", "required_receipt_files_missing"),
        ("fixture_files_exist", "fixture_files_missing"),
        ("artifact_index_under_scenario_dir", "artifact_index_path_outside_scenario_dir"),
        ("artifact_index_paths_have_no_symlink", "artifact_index_symlink_path"),
        ("all_boundaries_false", "boundary_false_field_true"),
        ("artifact_hashes_verified", "artifact_hash_mismatch"),
        ("receipt_dir_under_scenario_dir", "operator_receipt_dir_outside_scenario_dir"),
    )
    for metric_name, failure_reason in checks:
        if not metrics[metric_name]:
            reasons.append(failure_reason)
    if scenario.get("requires_marker") is True and not metrics["embedded_marker_found"]:
        reasons.append("embedded_marker_not_found")
    if scenario.get("requires_click") is True and not metrics["embedded_click_completed"]:
        reasons.append("embedded_click_not_completed")
    if (
        scenario.get("requires_status_text") is True
        and not metrics["embedded_status_text_nonempty"]
    ):
        reasons.append("embedded_status_text_empty")
    if metrics["candidate_repo_files_indexed"]:
        reasons.append("candidate_repo_files_indexed")
    if metrics["external_candidate_artifacts_indexed"]:
        reasons.append("external_candidate_artifacts_indexed")
    for directory_key in ("adapter_draft_run_dir", "embedded_smoke_dir"):
        if paths[directory_key].is_symlink():
            reasons.append(directory_key + "_is_symlink")
    return reasons


def _apply_repeated_equivalence(scenario_results: list[dict[str, object]]) -> None:
    repeated = [
        result
        for result in scenario_results
        if result["scenario_type"] == "repeated_local_fixture_execution"
    ]
    if len(repeated) != 2:
        return
    equivalent = _normalized_repeated_result(repeated[0]) == _normalized_repeated_result(
        repeated[1]
    )
    equivalent = equivalent and all(result["success"] is True for result in repeated)
    for result in repeated:
        result.update(
            {
                "deterministic_equivalence_group": "repeated_local_fixture_execution",
                "deterministic_equivalence_confirmed": equivalent,
                "deterministic_equivalence_mode": (
                    "behavioral_result_equivalence_not_byte_identical"
                ),
                "byte_identical_required": False,
                "exact_hashing_stable": False,
            }
        )
        if not equivalent:
            result["success"] = False
            result["failure_reasons"] = list(result["failure_reasons"]) + [
                "repeated_local_fixture_execution_not_deterministically_equivalent"
            ]


def _normalized_repeated_result(result: dict[str, object]) -> dict[str, object]:
    return {
        "receipt_success": result["receipt_success"],
        "adapter_draft_success": result["adapter_draft_success"],
        "embedded_smoke_success": result["embedded_smoke_success"],
        "embedded_fixture_url_scheme": result["embedded_fixture_url_scheme"],
        "embedded_marker_found": result["embedded_marker_found"],
        "embedded_click_completed": result["embedded_click_completed"],
        "embedded_status_text": result["embedded_status_text"],
        "embedded_non_local_request_count": result["embedded_non_local_request_count"],
        "artifact_index_under_scenario_dir": result["artifact_index_under_scenario_dir"],
        "candidate_repo_files_indexed": result["candidate_repo_files_indexed"],
        "external_candidate_artifacts_indexed": result[
            "external_candidate_artifacts_indexed"
        ],
        "all_boundaries_false": result["all_boundaries_false"],
        "artifact_hashes_verified": result["artifact_hashes_verified"],
        "fixture_files_exist": result["fixture_files_exist"],
        "required_receipt_files_exist": result["required_receipt_files_exist"],
    }


def _verify_index_payload(
    index_payload: dict[str, object],
    scenario_dir: Path,
) -> dict[str, bool]:
    entries = index_payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return {
            "paths_under_scenario_dir": False,
            "no_symlink_paths": False,
            "all_hashes_match": False,
            "candidate_repo_files_indexed": index_payload.get(
                "candidate_repo_files_indexed"
            )
            is True,
            "external_candidate_artifacts_indexed": index_payload.get(
                "external_candidate_artifacts_indexed"
            )
            is True,
        }
    paths_under = True
    no_symlinks = True
    all_hashes = True
    candidate_repo_files_indexed = index_payload.get("candidate_repo_files_indexed") is True
    external_candidate_artifacts_indexed = (
        index_payload.get("external_candidate_artifacts_indexed") is True
    )
    for entry in entries:
        if not isinstance(entry, dict):
            paths_under = False
            all_hashes = False
            continue
        candidate_repo_files_indexed = candidate_repo_files_indexed or (
            entry.get("candidate_repo_file") is True
        )
        external_candidate_artifacts_indexed = external_candidate_artifacts_indexed or (
            entry.get("external_candidate_artifact") is True
        )
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            paths_under = False
            all_hashes = False
            continue
        path = Path(path_value)
        if _candidate_repo_marker_in_path(path):
            candidate_repo_files_indexed = True
        if path.is_symlink() or _path_has_symlink_component(path, scenario_dir):
            no_symlinks = False
            all_hashes = False
        if not _path_is_inside(path, scenario_dir):
            paths_under = False
            external_candidate_artifacts_indexed = True
            all_hashes = False
        if not path.exists() or not path.is_file() or path.is_symlink():
            all_hashes = False
            continue
        recorded_hash = entry.get("sha256")
        if isinstance(recorded_hash, str) and recorded_hash:
            if sha256_file(path) != recorded_hash:
                all_hashes = False
    return {
        "paths_under_scenario_dir": paths_under,
        "no_symlink_paths": no_symlinks,
        "all_hashes_match": all_hashes,
        "candidate_repo_files_indexed": candidate_repo_files_indexed,
        "external_candidate_artifacts_indexed": external_candidate_artifacts_indexed,
    }


def _verify_manifest_hashes(manifest: dict[str, object], scenario_dir: Path) -> bool:
    if not manifest:
        return False
    checked = 0
    ok = True
    for key, path_value in manifest.items():
        if not key.endswith("_path") or not isinstance(path_value, str):
            continue
        prefix = key[:-5]
        recorded_hash = manifest.get(prefix + "_sha256")
        if not isinstance(recorded_hash, str) or not recorded_hash:
            continue
        path = Path(path_value)
        if not _path_is_inside(path, scenario_dir):
            continue
        checked += 1
        if path.is_symlink() or not path.exists() or not path.is_file():
            ok = False
            continue
        if sha256_file(path) != recorded_hash:
            ok = False
    for value in manifest.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            path_value = item.get("path")
            recorded_hash = item.get("sha256")
            if not isinstance(path_value, str) or not isinstance(recorded_hash, str):
                continue
            path = Path(path_value)
            if not _path_is_inside(path, scenario_dir):
                continue
            checked += 1
            if path.is_symlink() or not path.exists() or not path.is_file():
                ok = False
                continue
            if sha256_file(path) != recorded_hash:
                ok = False
    return checked > 0 and ok


def _true_fields(payloads: dict[str, dict[str, object]]) -> dict[str, list[str]]:
    true_fields: dict[str, list[str]] = {}
    for label, payload in payloads.items():
        matches = [
            key
            for key, value in payload.items()
            if key in _FALSE_FIELD_NAMES and value is True
        ]
        if matches:
            true_fields[label] = sorted(matches)
    return true_fields


def _launcher_payload(
    *,
    output_path: Path,
    suite_paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object] | None,
    artifact_index: dict[str, object],
    executed: bool,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "suite_id": plan["suite_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "output_dir": output_path.as_posix(),
        "local_only_playwright_fixture_scenario_suite_plan_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE
        ].as_posix(),
        "local_only_playwright_fixture_scenario_suite_manifest_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE
        ].as_posix(),
        "local_only_playwright_fixture_scenario_suite_summary_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SUMMARY_FILE
        ].as_posix(),
        "local_only_playwright_fixture_scenario_suite_checklist_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_CHECKLIST_FILE
        ].as_posix(),
        "local_only_playwright_fixture_scenario_suite_result_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE
        ].as_posix()
        if executed
        else None,
        "artifact_index_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": suite_paths[
            LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "scenarios_dir": plan["scenarios_dir"],
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
        "scenario_set": plan["scenario_set"],
        "scenario_count_planned": plan["scenario_count_planned"],
        "scenario_count_executed": 0
        if result is None
        else result["scenario_count_executed"],
        "scenario_count_passed": 0 if result is None else result["scenario_count_passed"],
        "scenario_count_failed": 0 if result is None else result["scenario_count_failed"],
        "scenario_result_paths": []
        if result is None
        else [
            str(scenario["scenario_dir"]) + "/" + LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_SCENARIO_RESULT_FILE
            for scenario in result["scenario_results"]
        ],
        "suite_success": False if result is None else result["suite_success"],
        "suite_status": plan["suite_status"],
        "suite_decision": plan["suite_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "indexed_artifacts": artifact_index["indexed_artifacts"],
        "executed": executed,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }
    return payload


def _structured_failure_result(
    selection_matrix_path: Path,
    playwright_candidate_manifest_path: Path,
    output_path: Path,
    suite_id: str,
    scenario_set: str,
    failure_stage: str,
    error_message: str,
    *,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
) -> LocalOnlyPlaywrightFixtureScenarioSuiteResult:
    payload = {
        "complete": False,
        "suite_type": _SUITE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "suite_id": suite_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "playwright_candidate_manifest_path": (
            playwright_candidate_manifest_path.as_posix()
        ),
        "scenario_set": scenario_set,
        "executed": executed,
        "success": False,
        "suite_status": _FAILED_STATUS,
        "suite_decision": _FAILED_DECISION,
        "next_allowed_action": _FIX_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "local_only_playwright_fixture_scenario_suite_plan_path": None,
        "local_only_playwright_fixture_scenario_suite_manifest_path": None,
        "local_only_playwright_fixture_scenario_suite_summary_path": None,
        "local_only_playwright_fixture_scenario_suite_checklist_path": None,
        "local_only_playwright_fixture_scenario_suite_result_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "scenarios_dir": None,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS),
        **dict(LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS),
    }
    return LocalOnlyPlaywrightFixtureScenarioSuiteResult(
        selection_matrix_path=selection_matrix_path,
        playwright_candidate_manifest_path=playwright_candidate_manifest_path,
        output_dir=output_path,
        suite_id=suite_id,
        scenario_set=scenario_set,
        plan_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        result_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        scenarios_dir=None,
        complete=False,
        executed=executed,
        success=False,
        suite_status=_FAILED_STATUS,
        payload=payload,
    )


def _summary_markdown(
    plan: dict[str, object],
    result: dict[str, object] | None,
) -> str:
    lines = [
        "# Local-Only Playwright Fixture Scenario Suite",
        "",
        "Status: " + str(plan["suite_status"]),
        "Suite id: " + str(plan["suite_id"]),
        "Scenario set: " + str(plan["scenario_set"]),
        "Planned scenarios: " + str(plan["scenario_count_planned"]),
        "Candidate: microsoft/playwright",
        "Scope: local file fixtures through operator-provided receipts only",
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
        "Boundary: scenario declarations and #422 receipt evidence only.",
    ]
    if result is not None:
        lines.insert(6, "Executed scenarios: " + str(result["scenario_count_executed"]))
        lines.insert(7, "Passed scenarios: " + str(result["scenario_count_passed"]))
        lines.insert(8, "Suite success: " + str(result["suite_success"]).lower())
    return "\n".join(lines)


def _checklist_markdown(
    plan: dict[str, object],
    result: dict[str, object] | None,
) -> str:
    lines = [
        "# Local-Only Playwright Fixture Scenario Suite Checklist",
        "",
        "- [ ] Confirm every scenario executed only through the #422 receipt path.",
        "- [ ] Confirm embedded fixture schemes are file only.",
        "- [ ] Confirm no user-supplied target, live website, account, login, registration, scraping, bypass, or captcha workflow is involved.",
        "- [ ] Confirm no secrets, cookies, external network, package install, browser download, npm, or npx.",
        "- [ ] Confirm no candidate repository access or candidate code execution occurred.",
        "- [ ] Confirm adapter registration, production promotion, and autonomous execution remain disabled.",
        "- [ ] Confirm suite success is not production admission.",
        "",
        "Suite decision: " + str(plan["suite_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    if result is not None:
        lines.append("Suite success: " + str(result["suite_success"]).lower())
    return "\n".join(lines)


def _status_decision_next_action(*, executed: bool, success: bool) -> tuple[str, str, str]:
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


def _receipt_id(suite_id: str, scenario_id: str) -> str:
    return _role_slug(suite_id) + "__" + _role_slug(scenario_id)


def _read_json_object(path: Path, label: str) -> tuple[dict[str, object], str | None]:
    if not os.path.lexists(path):
        return {}, label + " is missing"
    if path.is_symlink():
        return {}, label + " must not be a symlink"
    if not path.is_file():
        return {}, label + " must be a regular file"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return {}, label + " must be a valid JSON object: " + _safe_text(error)
    if not isinstance(payload, dict):
        return {}, label + " must be a valid JSON object"
    return payload, None


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _first_text(*values: object) -> str | None:
    for value in values:
        text = _text_or_none(value)
        if text is not None:
            return text
    return None


def _present_bool_values(*values: object) -> list[bool]:
    return [value for value in values if isinstance(value, bool)]


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _regular_file_ok(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _scheme_from_reference(value: object) -> str | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    return value.split(":", 1)[0].lower()


def _candidate_repo_marker_in_path(path: Path) -> bool:
    lowered = tuple(part.lower() for part in Path(path).parts)
    if "capability_candidates" in lowered:
        return True
    for index in range(len(lowered) - 1):
        if lowered[index] == "microsoft" and lowered[index + 1] == "playwright":
            return True
    return False


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


def _path_has_symlink_component(candidate_path: Path, root_path: Path) -> bool:
    relative = _relative_path(candidate_path, root_path)
    if relative is None:
        return False
    cursor = Path(root_path)
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return True
    return False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _role_slug(value: str) -> str:
    slug = []
    for char in str(value):
        if char.isalnum():
            slug.append(char.lower())
        else:
            slug.append("_")
    return "_".join("".join(slug).split("_")) or "scenario"


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
    return text[:240] if text else "local-only Playwright fixture scenario suite failed"
