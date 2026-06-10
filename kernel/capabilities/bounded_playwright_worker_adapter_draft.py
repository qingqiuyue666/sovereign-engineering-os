"""Bounded Playwright worker adapter draft wrapper.

This module is intentionally only an adapter-shaped envelope around the
repository-owned Playwright local fixture sandbox smoke. It does not accept
URLs, install packages, download browsers, access candidate repositories, or
register a production adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.capabilities.playwright_local_fixture_sandbox_smoke import (
    FIXTURE_APP_JS_FILE,
    FIXTURE_DIR_NAME,
    FIXTURE_INDEX_FILE,
    FIXTURE_STYLE_CSS_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    run_playwright_local_fixture_sandbox_smoke,
)
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS",
    "BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS",
    "BoundedPlaywrightWorkerAdapterDraftResult",
    "build_bounded_playwright_worker_adapter_draft_plan",
    "run_bounded_playwright_worker_adapter_draft",
    "run_bounded_playwright_worker_adapter_draft_launcher",
]


BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE = (
    "bounded_playwright_worker_adapter_draft_plan.json"
)
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE = (
    "bounded_playwright_worker_adapter_draft_manifest.json"
)
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE = (
    "bounded_playwright_worker_adapter_draft_summary.md"
)
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE = (
    "bounded_playwright_worker_adapter_draft_checklist.md"
)
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE = (
    "bounded_playwright_worker_adapter_draft_result.json"
)
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE = "artifact_index.json"
BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

EMBEDDED_SMOKE_DIR_NAME = "embedded_smoke"

_ADAPTER_DRAFT_TYPE = "bounded_playwright_worker_adapter_draft_v1"
_RESULT_TYPE = "bounded_playwright_worker_adapter_draft_result_v1"
_MANIFEST_TYPE = "bounded_playwright_worker_adapter_draft_manifest_v1"
_ARTIFACT_INDEX_TYPE = "bounded_playwright_worker_adapter_draft_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "bounded_playwright_worker_adapter_draft_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_external_worker_adapter_draft_record"
_EXECUTION_CAPABILITY = "bounded_playwright_local_fixture_worker_adapter_draft_only"
_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_CAPABILITY = "launch_bounded_playwright_worker_adapter_draft"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_SOURCE_SMOKE_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_v1"
_SCOPE = "local_fixture_pages_only"

_PLAN_READY_STATUS = "bounded_playwright_worker_adapter_draft_plan_ready"
_COMPLETED_STATUS = "bounded_playwright_worker_adapter_draft_smoke_completed"
_FAILED_STATUS = "bounded_playwright_worker_adapter_draft_smoke_failed"
_PLAN_READY_DECISION = "ready_for_explicit_local_fixture_worker_adapter_smoke"
_PASSED_DECISION = "bounded_local_fixture_worker_adapter_smoke_passed"
_FAILED_DECISION = "fix_bounded_playwright_worker_adapter_draft_and_retry"
_PLAN_NEXT_ACTION = "run_explicit_local_fixture_worker_adapter_smoke"
_REVIEW_NEXT_ACTION = "review_bounded_playwright_worker_adapter_draft_smoke_result"
_FIX_NEXT_ACTION = "fix_bounded_playwright_worker_adapter_draft_and_retry"

_PLAN_OUTPUT_FILES = (
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE,
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE,
)
_ALL_WRAPPER_OUTPUT_FILES = _PLAN_OUTPUT_FILES + (
    BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE,
)

BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS: dict[str, bool] = {
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
    "secret_access_allowed": False,
}

BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS: dict[str, bool] = {
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
class BoundedPlaywrightWorkerAdapterDraftResult:
    selection_matrix_path: Path
    playwright_candidate_manifest_path: Path
    output_dir: Path
    adapter_draft_id: str
    plan_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    result_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    embedded_smoke_dir: Path | None
    complete: bool
    executed: bool
    success: bool
    worker_adapter_status: str
    payload: dict[str, object]


def build_bounded_playwright_worker_adapter_draft_plan(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    adapter_draft_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> BoundedPlaywrightWorkerAdapterDraftResult:
    """Create plan-only adapter-draft artifacts around the embedded smoke."""

    return run_bounded_playwright_worker_adapter_draft(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        execute_local_fixture_smoke=False,
    )


def run_bounded_playwright_worker_adapter_draft_launcher(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    adapter_draft_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    execute_local_fixture_smoke: bool = False,
) -> BoundedPlaywrightWorkerAdapterDraftResult:
    """Launcher-oriented wrapper for the bounded worker adapter draft."""

    return run_bounded_playwright_worker_adapter_draft(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        node_command=node_command,
        runner_script=runner_script,
        execute_local_fixture_smoke=execute_local_fixture_smoke,
    )


def run_bounded_playwright_worker_adapter_draft(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    adapter_draft_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    execute_local_fixture_smoke: bool = False,
) -> BoundedPlaywrightWorkerAdapterDraftResult:
    """Build the adapter draft and optionally run the embedded local smoke."""

    selection_path = Path(selection_matrix)
    manifest_input_path = Path(playwright_candidate_manifest)
    output_path = Path(output_dir)
    wrapper_paths = _wrapper_paths(output_path)
    embedded_smoke_dir = output_path / EMBEDDED_SMOKE_DIR_NAME

    preflight_error = _preflight_output_error(output_path, wrapper_paths)
    if preflight_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_input_path,
            output_path,
            adapter_draft_id,
            "preflight_output_dir",
            preflight_error,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )
    if not _non_empty_text(adapter_draft_id):
        return _structured_failure_result(
            selection_path,
            manifest_input_path,
            output_path,
            adapter_draft_id,
            "preflight_adapter_draft_id",
            "adapter_draft_id is missing",
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    embedded_smoke_dir.mkdir()
    embedded = run_playwright_local_fixture_sandbox_smoke(
        selection_path,
        manifest_input_path,
        embedded_smoke_dir,
        adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        node_command=None if node_command is None else Path(node_command),
        runner_script=None if runner_script is None else Path(runner_script),
        execute_local_fixture_smoke=execute_local_fixture_smoke,
    )
    if embedded.plan_path is None:
        _remove_empty_dir(embedded_smoke_dir)
        return _structured_failure_result(
            selection_path,
            manifest_input_path,
            output_path,
            adapter_draft_id,
            str(embedded.payload.get("failure_stage", "embedded_smoke_preflight")),
            str(embedded.payload.get("error_message", "embedded smoke failed")),
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    embedded_plan = _read_json_object(embedded.plan_path)
    embedded_result = (
        _read_json_object(embedded.result_path)
        if embedded.result_path is not None
        else None
    )
    fixture_url = str(embedded_plan["fixture_url"])
    fixture_url_scheme = str(embedded_plan["fixture_url_scheme"])
    status, decision, next_action = _status_decision_next_action(
        execution_requested=execute_local_fixture_smoke,
        embedded_success=bool(embedded.success),
    )
    complete = bool(not execute_local_fixture_smoke or embedded.success)
    selection_sha256 = sha256_file(selection_path)
    candidate_manifest_sha256 = sha256_file(manifest_input_path)

    plan = _plan_payload(
        selection_path=selection_path,
        selection_sha256=selection_sha256,
        candidate_manifest_path=manifest_input_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        output_path=output_path,
        wrapper_paths=wrapper_paths,
        embedded=embedded,
        embedded_plan=embedded_plan,
        adapter_draft_id=adapter_draft_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        executed=execute_local_fixture_smoke,
        fixture_url=fixture_url,
        fixture_url_scheme=fixture_url_scheme,
        status=status,
        decision=decision,
        next_action=next_action,
    )
    _write_json_exclusive(
        wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE],
        plan,
    )
    _write_text_exclusive(
        wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE],
        _summary_markdown(plan, embedded_result),
    )
    _write_text_exclusive(
        wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE],
        _checklist_markdown(plan),
    )

    result_payload = None
    if execute_local_fixture_smoke:
        result_payload = _result_payload(
            adapter_draft_id=adapter_draft_id,
            embedded=embedded,
            embedded_result=embedded_result or {},
            fixture_url=fixture_url,
            fixture_url_scheme=fixture_url_scheme,
            success=complete,
            status=status,
            decision=decision,
            next_action=next_action,
        )
        _write_json_exclusive(
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE],
            result_payload,
        )

    manifest = _manifest_payload(
        output_path=output_path,
        wrapper_paths=wrapper_paths,
        plan=plan,
        selection_matrix_path=selection_path,
        selection_matrix_sha256=selection_sha256,
        candidate_manifest_path=manifest_input_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        embedded=embedded,
        executed=execute_local_fixture_smoke,
        success=complete,
    )
    _write_json_exclusive(
        wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path,
        wrapper_paths,
        embedded,
        executed=execute_local_fixture_smoke,
        status=status,
        next_action=next_action,
    )
    _write_json_exclusive(
        wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        wrapper_paths,
        artifact_index,
    )
    _write_json_exclusive(
        wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(
        output_path=output_path,
        wrapper_paths=wrapper_paths,
        plan=plan,
        embedded=embedded,
        executed=execute_local_fixture_smoke,
        success=complete,
        embedded_result=embedded_result,
    )
    return BoundedPlaywrightWorkerAdapterDraftResult(
        selection_matrix_path=selection_path,
        playwright_candidate_manifest_path=manifest_input_path,
        output_dir=output_path,
        adapter_draft_id=adapter_draft_id,
        plan_path=wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE],
        manifest_path=wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE
        ],
        summary_path=wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE],
        checklist_path=wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE
        ],
        result_path=wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE]
        if execute_local_fixture_smoke
        else None,
        artifact_index_path=wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        embedded_smoke_dir=embedded_smoke_dir,
        complete=complete,
        executed=execute_local_fixture_smoke,
        success=complete,
        worker_adapter_status=status,
        payload=payload,
    )


def _wrapper_paths(output_path: Path) -> dict[str, Path]:
    return {
        file_name: output_path / file_name for file_name in _ALL_WRAPPER_OUTPUT_FILES
    }


def _preflight_output_error(
    output_path: Path,
    wrapper_paths: dict[str, Path],
) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    embedded_smoke_dir = output_path / EMBEDDED_SMOKE_DIR_NAME
    if os.path.lexists(embedded_smoke_dir):
        return "embedded_smoke directory already exists"
    for file_name in sorted(wrapper_paths):
        if os.path.lexists(wrapper_paths[file_name]):
            return "bounded Playwright worker adapter draft output already exists: " + file_name
    return None


def _status_decision_next_action(
    *,
    execution_requested: bool,
    embedded_success: bool,
) -> tuple[str, str, str]:
    if not execution_requested:
        return _PLAN_READY_STATUS, _PLAN_READY_DECISION, _PLAN_NEXT_ACTION
    if embedded_success:
        return _COMPLETED_STATUS, _PASSED_DECISION, _REVIEW_NEXT_ACTION
    return _FAILED_STATUS, _FAILED_DECISION, _FIX_NEXT_ACTION


def _plan_payload(
    *,
    selection_path: Path,
    selection_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    output_path: Path,
    wrapper_paths: dict[str, Path],
    embedded,
    embedded_plan: dict[str, object],
    adapter_draft_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
    fixture_url: str,
    fixture_url_scheme: str,
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "adapter_draft_type": _ADAPTER_DRAFT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "selection_matrix_path": selection_path.as_posix(),
        "selection_matrix_sha256": selection_sha256,
        "playwright_candidate_manifest_path": candidate_manifest_path.as_posix(),
        "playwright_candidate_manifest_sha256": candidate_manifest_sha256,
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_smoke_type": _SOURCE_SMOKE_TYPE,
        "embedded_smoke_dir": Path(embedded.output_dir).as_posix(),
        "embedded_smoke_plan_path": _path_or_none(embedded.plan_path),
        "embedded_smoke_manifest_path": _path_or_none(embedded.smoke_manifest_path),
        "embedded_smoke_summary_path": _path_or_none(embedded.summary_path),
        "embedded_smoke_checklist_path": _path_or_none(embedded.checklist_path),
        "embedded_smoke_artifact_index_path": _path_or_none(
            embedded.artifact_index_path
        ),
        "embedded_smoke_artifact_index_manifest_path": _path_or_none(
            embedded.artifact_index_manifest_path
        ),
        "embedded_fixture_dir": _path_or_none(embedded.fixture_dir),
        "embedded_fixture_index_path": _path_or_none(embedded.fixture_index_path),
        "embedded_fixture_app_js_path": _path_or_none(embedded.fixture_app_js_path),
        "embedded_fixture_style_css_path": _path_or_none(
            embedded.fixture_style_css_path
        ),
        "embedded_fixture_url": fixture_url,
        "embedded_fixture_url_scheme": fixture_url_scheme,
        "adapter_draft_scope": _SCOPE,
        "executed": executed,
        "execution_mode": "explicit_local_fixture_worker_adapter_smoke_only"
        if executed
        else "plan_only",
        "owned_local_smoke_runner_executed": executed,
        "embedded_playwright_local_fixture_smoke_executed": executed,
        "worker_adapter_status": status,
        "adapter_draft_decision": decision,
        "next_allowed_action": next_action,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "wrapper_plan_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE
        ].as_posix(),
        "wrapper_manifest_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE
        ].as_posix(),
        "embedded_smoke_status": embedded_plan.get("smoke_status"),
        "embedded_smoke_decision": embedded_plan.get("smoke_decision"),
        "embedded_smoke_next_allowed_action": embedded_plan.get(
            "next_allowed_action"
        ),
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS),
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }


def _result_payload(
    *,
    adapter_draft_id: str,
    embedded,
    embedded_result: dict[str, object],
    fixture_url: str,
    fixture_url_scheme: str,
    success: bool,
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "result_type": _RESULT_TYPE,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": True,
        "execution_mode": "explicit_local_fixture_worker_adapter_smoke_only",
        "embedded_smoke_result_path": _path_or_none(embedded.result_path),
        "embedded_smoke_runner_output_path": _path_or_none(
            embedded.runner_output_path
        ),
        "embedded_smoke_screenshot_path": _path_or_none(embedded.screenshot_path),
        "embedded_fixture_url": fixture_url,
        "embedded_fixture_url_scheme": fixture_url_scheme,
        "embedded_marker_found": bool(embedded_result.get("marker_found")),
        "embedded_click_completed": bool(embedded_result.get("click_completed")),
        "embedded_status_text": str(embedded_result.get("status_text", "")),
        "embedded_non_local_request_count": _int_value(
            embedded_result.get("non_local_request_count")
        ),
        "embedded_success": bool(embedded_result.get("success")),
        "success": success,
        "worker_adapter_status": status,
        "adapter_draft_decision": decision,
        "next_allowed_action": next_action,
        "owned_local_smoke_runner_executed": True,
        "embedded_playwright_local_fixture_smoke_executed": True,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }


def _manifest_payload(
    *,
    output_path: Path,
    wrapper_paths: dict[str, Path],
    plan: dict[str, object],
    selection_matrix_path: Path,
    selection_matrix_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    embedded,
    executed: bool,
    success: bool,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_draft_id": plan["adapter_draft_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "selection_matrix_sha256": selection_matrix_sha256,
        "playwright_candidate_manifest_path": candidate_manifest_path.as_posix(),
        "playwright_candidate_manifest_sha256": candidate_manifest_sha256,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "plan_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE]
        ),
        "summary_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE]
        ),
        "checklist_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE]
        ),
        "embedded_smoke_dir": plan["embedded_smoke_dir"],
        "embedded_smoke_plan_path": plan["embedded_smoke_plan_path"],
        "embedded_smoke_plan_sha256": sha256_file(Path(embedded.plan_path)),
        "embedded_smoke_manifest_path": plan["embedded_smoke_manifest_path"],
        "embedded_smoke_manifest_sha256": sha256_file(Path(embedded.smoke_manifest_path)),
        "embedded_smoke_summary_path": plan["embedded_smoke_summary_path"],
        "embedded_smoke_summary_sha256": sha256_file(Path(embedded.summary_path)),
        "embedded_smoke_checklist_path": plan["embedded_smoke_checklist_path"],
        "embedded_smoke_checklist_sha256": sha256_file(Path(embedded.checklist_path)),
        "embedded_fixture_dir": plan["embedded_fixture_dir"],
        "embedded_fixture_index_path": plan["embedded_fixture_index_path"],
        "embedded_fixture_index_sha256": sha256_file(Path(embedded.fixture_index_path)),
        "embedded_fixture_app_js_path": plan["embedded_fixture_app_js_path"],
        "embedded_fixture_app_js_sha256": sha256_file(Path(embedded.fixture_app_js_path)),
        "embedded_fixture_style_css_path": plan["embedded_fixture_style_css_path"],
        "embedded_fixture_style_css_sha256": sha256_file(
            Path(embedded.fixture_style_css_path)
        ),
        "embedded_fixture_url": plan["embedded_fixture_url"],
        "embedded_fixture_url_scheme": "file",
        "executed": executed,
        "success": success,
        "worker_adapter_status": plan["worker_adapter_status"],
        "adapter_draft_decision": plan["adapter_draft_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "owned_local_smoke_runner_executed": executed,
        "embedded_playwright_local_fixture_smoke_executed": executed,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }
    if executed:
        result_path = wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE]
        manifest.update(
            {
                "result_path": result_path.as_posix(),
                "result_sha256": sha256_file(result_path),
                "embedded_smoke_result_path": _path_or_none(embedded.result_path),
                "embedded_smoke_result_sha256": sha256_file(Path(embedded.result_path)),
                "embedded_smoke_runner_output_path": _path_or_none(
                    embedded.runner_output_path
                ),
                "embedded_smoke_runner_output_sha256": _sha256_file_if_present(
                    embedded.runner_output_path
                ),
                "embedded_smoke_screenshot_path": _path_or_none(
                    embedded.screenshot_path
                ),
                "embedded_smoke_screenshot_sha256": _sha256_file_if_present(
                    embedded.screenshot_path
                ),
            }
        )
    return manifest


def _artifact_index_payload(
    output_path: Path,
    wrapper_paths: dict[str, Path],
    embedded,
    *,
    executed: bool,
    status: str,
    next_action: str,
) -> dict[str, object]:
    artifact_roles = [
        (
            "bounded_playwright_worker_adapter_draft_plan",
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE],
        ),
        (
            "bounded_playwright_worker_adapter_draft_manifest",
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE],
        ),
        (
            "bounded_playwright_worker_adapter_draft_summary",
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE],
        ),
        (
            "bounded_playwright_worker_adapter_draft_checklist",
            wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE],
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_plan",
            embedded.plan_path,
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_manifest",
            embedded.smoke_manifest_path,
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_summary",
            embedded.summary_path,
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_checklist",
            embedded.checklist_path,
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_artifact_index",
            embedded.artifact_index_path,
        ),
        (
            "embedded_playwright_local_fixture_sandbox_smoke_artifact_index_manifest",
            embedded.artifact_index_manifest_path,
        ),
        ("embedded_fixture_index_html", embedded.fixture_index_path),
        ("embedded_fixture_app_js", embedded.fixture_app_js_path),
        ("embedded_fixture_style_css", embedded.fixture_style_css_path),
    ]
    if executed:
        artifact_roles.extend(
            [
                (
                    "bounded_playwright_worker_adapter_draft_result",
                    wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE],
                ),
                (
                    "embedded_playwright_local_fixture_sandbox_smoke_result",
                    embedded.result_path,
                ),
                (
                    "embedded_playwright_local_fixture_sandbox_smoke_runner_output",
                    embedded.runner_output_path,
                ),
                (
                    "embedded_playwright_local_fixture_sandbox_smoke_screenshot",
                    embedded.screenshot_path,
                ),
            ]
        )
    entries = [
        _generated_artifact_entry(output_path, role, Path(path))
        for role, path in artifact_roles
        if path is not None
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_draft_id": embedded.payload.get("smoke_id"),
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": (
            "wrapper_and_embedded_local_fixture_smoke_artifacts_under_output_dir_only"
        ),
        "worker_adapter_status": status,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "owned_local_smoke_runner_executed": executed,
        "embedded_playwright_local_fixture_smoke_executed": executed,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": next_action,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    wrapper_paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = wrapper_paths[BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_draft_id": artifact_index["adapter_draft_id"],
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
        "owned_local_smoke_runner_executed": artifact_index[
            "owned_local_smoke_runner_executed"
        ],
        "embedded_playwright_local_fixture_smoke_executed": artifact_index[
            "embedded_playwright_local_fixture_smoke_executed"
        ],
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }


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


def _launcher_payload(
    *,
    output_path: Path,
    wrapper_paths: dict[str, Path],
    plan: dict[str, object],
    embedded,
    executed: bool,
    success: bool,
    embedded_result: dict[str, object] | None,
) -> dict[str, object]:
    payload = {
        "complete": success,
        "adapter_draft_id": plan["adapter_draft_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "output_dir": output_path.as_posix(),
        "bounded_playwright_worker_adapter_draft_plan_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_PLAN_FILE
        ].as_posix(),
        "bounded_playwright_worker_adapter_draft_manifest_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_MANIFEST_FILE
        ].as_posix(),
        "bounded_playwright_worker_adapter_draft_summary_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_SUMMARY_FILE
        ].as_posix(),
        "bounded_playwright_worker_adapter_draft_checklist_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_CHECKLIST_FILE
        ].as_posix(),
        "bounded_playwright_worker_adapter_draft_result_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_RESULT_FILE
        ].as_posix()
        if executed
        else None,
        "artifact_index_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": wrapper_paths[
            BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "embedded_smoke_dir": plan["embedded_smoke_dir"],
        "embedded_smoke_plan_path": plan["embedded_smoke_plan_path"],
        "embedded_smoke_manifest_path": plan["embedded_smoke_manifest_path"],
        "embedded_smoke_summary_path": plan["embedded_smoke_summary_path"],
        "embedded_smoke_checklist_path": plan["embedded_smoke_checklist_path"],
        "embedded_smoke_result_path": _path_or_none(embedded.result_path),
        "embedded_smoke_runner_output_path": _path_or_none(
            embedded.runner_output_path
        ),
        "embedded_smoke_screenshot_path": _path_or_none(embedded.screenshot_path),
        "embedded_fixture_dir": plan["embedded_fixture_dir"],
        "embedded_fixture_index_path": plan["embedded_fixture_index_path"],
        "embedded_fixture_app_js_path": plan["embedded_fixture_app_js_path"],
        "embedded_fixture_style_css_path": plan["embedded_fixture_style_css_path"],
        "embedded_fixture_url": plan["embedded_fixture_url"],
        "embedded_fixture_url_scheme": "file",
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": executed,
        "success": success,
        "worker_adapter_status": plan["worker_adapter_status"],
        "adapter_draft_decision": plan["adapter_draft_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "owned_local_smoke_runner_executed": executed,
        "embedded_playwright_local_fixture_smoke_executed": executed,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }
    if embedded_result is not None:
        payload.update(
            {
                "embedded_marker_found": bool(embedded_result.get("marker_found")),
                "embedded_click_completed": bool(
                    embedded_result.get("click_completed")
                ),
                "embedded_status_text": str(
                    embedded_result.get("status_text", "")
                ),
                "embedded_non_local_request_count": _int_value(
                    embedded_result.get("non_local_request_count")
                ),
                "embedded_success": bool(embedded_result.get("success")),
            }
        )
    return payload


def _structured_failure_result(
    selection_matrix_path: Path,
    playwright_candidate_manifest_path: Path,
    output_path: Path,
    adapter_draft_id: str,
    failure_stage: str,
    error_message: str,
    *,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
) -> BoundedPlaywrightWorkerAdapterDraftResult:
    payload = {
        "complete": False,
        "adapter_draft_type": _ADAPTER_DRAFT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_draft_id": adapter_draft_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "playwright_candidate_manifest_path": (
            playwright_candidate_manifest_path.as_posix()
        ),
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": executed,
        "success": False,
        "owned_local_smoke_runner_executed": False,
        "embedded_playwright_local_fixture_smoke_executed": False,
        "worker_adapter_status": _FAILED_STATUS,
        "adapter_draft_decision": _FAILED_DECISION,
        "next_allowed_action": _FIX_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "bounded_playwright_worker_adapter_draft_plan_path": None,
        "bounded_playwright_worker_adapter_draft_manifest_path": None,
        "bounded_playwright_worker_adapter_draft_summary_path": None,
        "bounded_playwright_worker_adapter_draft_checklist_path": None,
        "bounded_playwright_worker_adapter_draft_result_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "embedded_smoke_dir": None,
        "embedded_fixture_url": None,
        "embedded_fixture_url_scheme": None,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_DISABLED_FIELDS),
        **dict(BOUNDED_PLAYWRIGHT_WORKER_ADAPTER_DRAFT_BOUNDARY_FALSE_FIELDS),
    }
    return BoundedPlaywrightWorkerAdapterDraftResult(
        selection_matrix_path=selection_matrix_path,
        playwright_candidate_manifest_path=playwright_candidate_manifest_path,
        output_dir=output_path,
        adapter_draft_id=adapter_draft_id,
        plan_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        result_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        embedded_smoke_dir=None,
        complete=False,
        executed=executed,
        success=False,
        worker_adapter_status=_FAILED_STATUS,
        payload=payload,
    )


def _summary_markdown(
    plan: dict[str, object],
    embedded_result: dict[str, object] | None,
) -> str:
    lines = [
        "# Bounded Playwright Worker Adapter Draft",
        "",
        "Status: " + str(plan["worker_adapter_status"]),
        "Adapter draft id: " + str(plan["adapter_draft_id"]),
        "Candidate: microsoft/playwright",
        "Scope: local fixture pages only",
        "Embedded fixture URL scheme: file",
        "Plan-only default: " + str(not plan["executed"]).lower(),
        "Explicit execution requested: " + str(plan["executed"]).lower(),
        "Live website automation performed: false",
        "Arbitrary URL navigation performed: false",
        "Account workflow performed: false",
        "Scraping performed: false",
        "Bypass performed: false",
        "Captcha workflow performed: false",
        "Secret access performed: false",
        "Dependency installation performed: false",
        "Candidate repository access performed: false",
        "Adapter registered: false",
        "Production promotion granted: false",
        "Next allowed action: " + str(plan["next_allowed_action"]),
        "",
        "Boundary: adapter-draft wrapper around the existing local fixture smoke only.",
    ]
    if embedded_result is not None:
        lines.insert(6, "Embedded smoke success: " + str(embedded_result.get("success")).lower())
    return "\n".join(lines)


def _checklist_markdown(plan: dict[str, object]) -> str:
    lines = [
        "# Bounded Playwright Worker Adapter Draft Checklist",
        "",
        "- [ ] Confirm this is a draft wrapper around the local fixture smoke only.",
        "- [ ] Confirm the embedded fixture URL is file:// only.",
        "- [ ] Confirm no user-supplied URL or live website navigation is accepted.",
        "- [ ] Confirm no account, login, registration, scraping, bypass, or captcha workflow is involved.",
        "- [ ] Confirm no secrets, cookies, package install, browser download, or npm/npx.",
        "- [ ] Confirm no candidate repository access or candidate code execution occurred.",
        "- [ ] Confirm adapter registration and production promotion remain disabled.",
        "",
        "Adapter draft decision: " + str(plan["adapter_draft_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    return "\n".join(lines)


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()


def _read_json_object(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")
    return payload


def _remove_empty_dir(path: Path) -> None:
    try:
        Path(path).rmdir()
    except OSError:
        pass


def _sha256_file_if_present(path: Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file() or candidate.is_symlink():
        return None
    return sha256_file(candidate)


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
    return text[:240] if text else "bounded Playwright worker adapter draft failed"
