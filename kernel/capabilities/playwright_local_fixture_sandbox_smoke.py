"""Bounded local fixture smoke harness for the Playwright candidate.

This module creates repository-owned local fixture pages and structured smoke
artifacts only. Subprocess execution is plan-only by default and, when
explicitly requested, is limited to an owned runner script invoked through an
explicit executable path with fixed arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE",
    "PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE",
    "PLAYWRIGHT_BOUNDARY_FALSE_FIELDS",
    "PlaywrightLocalFixtureSandboxSmokeResult",
    "build_playwright_local_fixture_sandbox_smoke_plan",
    "run_playwright_local_fixture_sandbox_smoke",
    "run_playwright_local_fixture_sandbox_smoke_launcher",
]


PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE = (
    "playwright_local_fixture_sandbox_smoke_plan.json"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE = (
    "playwright_local_fixture_sandbox_smoke_manifest.json"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE = (
    "playwright_local_fixture_sandbox_smoke_summary.md"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE = (
    "playwright_local_fixture_sandbox_smoke_checklist.md"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE = (
    "playwright_local_fixture_sandbox_smoke_result.json"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE = (
    "playwright_local_fixture_sandbox_smoke_runner_output.json"
)
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE = "screenshot.png"
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE = "artifact_index.json"
PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

FIXTURE_DIR_NAME = "fixture"
FIXTURE_INDEX_FILE = "index.html"
FIXTURE_APP_JS_FILE = "app.js"
FIXTURE_STYLE_CSS_FILE = "style.css"
FIXTURE_MARKER_TEXT = "SOVEREIGN_PLAYWRIGHT_LOCAL_FIXTURE_SMOKE_MARKER"

_SMOKE_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_v1"
_RESULT_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_result_v1"
_MANIFEST_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "playwright_local_fixture_bounded_sandbox_smoke_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "playwright_local_fixture_bounded_sandbox_smoke_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_external_capability_sandbox_smoke_record"
_EXECUTION_CAPABILITY = "playwright_local_fixture_smoke_only"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_INTENDED_USE = "browser_automation"
_PLAN_READY_STATUS = "playwright_local_fixture_sandbox_smoke_plan_ready"
_COMPLETED_STATUS = "playwright_local_fixture_sandbox_smoke_completed"
_FAILED_STATUS = "playwright_local_fixture_sandbox_smoke_failed"
_PLAN_READY_DECISION = "ready_for_explicit_local_fixture_execution"
_PASSED_DECISION = "bounded_local_fixture_smoke_passed"
_FAILED_DECISION = "fix_playwright_local_fixture_smoke_and_retry"
_PLAN_NEXT_ACTION = "run_explicit_playwright_local_fixture_smoke"
_REVIEW_NEXT_ACTION = "review_playwright_local_fixture_smoke_result"
_FIX_NEXT_ACTION = "fix_playwright_local_fixture_smoke_and_retry"
_RUNNER_TYPE = "playwright_local_fixture_smoke_runner_v1"
_TIMEOUT_SECONDS = 30
_MAX_CAPTURE_CHARS = 8192

_PLAN_OUTPUT_FILES = (
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE,
)
_EXECUTION_OUTPUT_FILES = (
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE,
    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE,
)
_ALL_OUTPUT_FILES = _PLAN_OUTPUT_FILES + _EXECUTION_OUTPUT_FILES

PLAYWRIGHT_BOUNDARY_FALSE_FIELDS: dict[str, bool] = {
    "live_website_automation_performed": False,
    "account_workflow_performed": False,
    "scraping_performed": False,
    "bypass_performed": False,
    "captcha_workflow_performed": False,
    "credential_input_performed": False,
    "external_network_performed": False,
    "package_install_performed": False,
    "browser_download_performed": False,
    "npx_performed": False,
    "npm_performed": False,
    "git_clone_performed": False,
    "git_command_performed": False,
    "dependency_installation_performed": False,
    "third_party_code_execution_performed": False,
    "candidate_repo_access_performed": False,
    "candidate_code_imported": False,
    "candidate_code_execution_performed": False,
    "candidate_repo_mutation_performed": False,
    "model_api_called": False,
    "secret_access_performed": False,
    "adapter_generated": False,
    "adapter_registered": False,
    "auto_adoption_performed": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_DISABLED_CAPABILITY_FIELDS: dict[str, bool] = {
    "live_website_automation_allowed": False,
    "account_workflow_allowed": False,
    "scraping_allowed": False,
    "bypass_allowed": False,
    "captcha_workflow_allowed": False,
    "credential_input_allowed": False,
    "external_network_allowed": False,
    "package_install_allowed": False,
    "browser_download_allowed": False,
    "npx_allowed": False,
    "npm_allowed": False,
    "adapter_generation_allowed": False,
    "adapter_registration_allowed": False,
    "auto_adoption_allowed": False,
    "production_promotion_allowed": False,
    "candidate_repo_access_allowed": False,
    "candidate_code_execution_allowed": False,
    "candidate_code_import_allowed": False,
    "secret_access_allowed": False,
}

_FIXTURE_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Playwright Local Fixture Smoke</title>
  <link rel="stylesheet" href="./style.css">
  <script src="./app.js" defer></script>
</head>
<body>
  <main>
    <h1>Playwright Local Fixture Smoke</h1>
    <p id="smoke-marker">SOVEREIGN_PLAYWRIGHT_LOCAL_FIXTURE_SMOKE_MARKER</p>
    <button id="smoke-button" type="button">Run smoke</button>
    <p id="smoke-status" aria-live="polite">ready</p>
  </main>
</body>
</html>
"""

_FIXTURE_APP_JS = """(() => {
  "use strict";

  const button = document.getElementById("smoke-button");
  const status = document.getElementById("smoke-status");

  button.addEventListener("click", () => {
    status.textContent = "clicked";
  });
})();
"""

_FIXTURE_STYLE_CSS = """* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  font-family: system-ui, sans-serif;
  background: #f7faf8;
  color: #17211b;
}

main {
  width: min(36rem, calc(100vw - 2rem));
  padding: 2rem;
  border: 1px solid #c7d7ce;
  background: #ffffff;
}

button {
  min-height: 2.75rem;
  padding: 0 1rem;
  border: 1px solid #1f5b43;
  background: #1f5b43;
  color: #ffffff;
  font: inherit;
  cursor: pointer;
}

#smoke-status {
  min-height: 1.5rem;
  font-weight: 700;
}
"""


@dataclass(frozen=True)
class PlaywrightLocalFixtureSandboxSmokeResult:
    selection_matrix_path: Path
    candidate_manifest_path: Path
    output_dir: Path
    plan_path: Path | None
    smoke_manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    result_path: Path | None
    runner_output_path: Path | None
    screenshot_path: Path | None
    fixture_dir: Path | None
    fixture_index_path: Path | None
    fixture_app_js_path: Path | None
    fixture_style_css_path: Path | None
    complete: bool
    executed: bool
    success: bool
    smoke_status: str
    payload: dict[str, object]


def build_playwright_local_fixture_sandbox_smoke_plan(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    smoke_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> PlaywrightLocalFixtureSandboxSmokeResult:
    """Create plan-only smoke artifacts and a deterministic local fixture."""

    return run_playwright_local_fixture_sandbox_smoke(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        smoke_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        execute_local_fixture_smoke=False,
    )


def run_playwright_local_fixture_sandbox_smoke_launcher(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    smoke_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    execute_local_fixture_smoke: bool = False,
) -> PlaywrightLocalFixtureSandboxSmokeResult:
    """Launcher-oriented wrapper for the bounded local fixture smoke."""

    return run_playwright_local_fixture_sandbox_smoke(
        selection_matrix,
        playwright_candidate_manifest,
        output_dir,
        smoke_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        node_command=node_command,
        runner_script=runner_script,
        execute_local_fixture_smoke=execute_local_fixture_smoke,
    )


def run_playwright_local_fixture_sandbox_smoke(
    selection_matrix: Path,
    playwright_candidate_manifest: Path,
    output_dir: Path,
    smoke_id: str,
    *,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    node_command: Path | None = None,
    runner_script: Path | None = None,
    execute_local_fixture_smoke: bool = False,
    timeout_seconds: int = _TIMEOUT_SECONDS,
) -> PlaywrightLocalFixtureSandboxSmokeResult:
    """Create the smoke plan and optionally run the explicit local fixture smoke."""

    selection_path = Path(selection_matrix)
    manifest_path = Path(playwright_candidate_manifest)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    fixture_paths = _fixture_paths(output_path)

    preflight_error = _preflight_output_error(output_path, paths, fixture_paths)
    if preflight_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_output_dir",
            preflight_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    if not _non_empty_text(smoke_id):
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_smoke_id",
            "smoke_id is missing",
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    fixture_error = _fixture_content_error()
    if fixture_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_fixture_content",
            fixture_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    execution_preflight_error = _execution_preflight_error(
        execute_local_fixture_smoke=execute_local_fixture_smoke,
        node_command=node_command,
        runner_script=runner_script,
        output_dir=output_path,
    )
    if execution_preflight_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_execution",
            execution_preflight_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    selection_payload, selection_error = _read_json_object(
        selection_path,
        "selection_matrix",
    )
    if selection_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_selection_matrix",
            selection_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    selected_candidate, selection_validation_error = _validate_selection_matrix(
        selection_payload
    )
    if selection_validation_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_selection_matrix_schema",
            selection_validation_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    manifest_payload, manifest_error = _read_json_object(
        manifest_path,
        "playwright_candidate_manifest",
    )
    if manifest_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_candidate_manifest",
            manifest_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    normalized_manifest, manifest_validation_error = _validate_candidate_manifest(
        manifest_payload
    )
    if manifest_validation_error is not None:
        return _structured_failure_result(
            selection_path,
            manifest_path,
            output_path,
            "preflight_candidate_manifest_schema",
            manifest_validation_error,
            smoke_id=smoke_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            executed=False,
        )

    selection_sha256 = sha256_file(selection_path)
    candidate_sha256 = sha256_file(manifest_path)

    _write_fixture_files(fixture_paths)
    fixture_url = fixture_paths[FIXTURE_INDEX_FILE].resolve(strict=True).as_uri()

    execution_result = None
    if execute_local_fixture_smoke:
        execution_result = _execute_runner(
            node_command=Path(node_command),  # type: ignore[arg-type]
            runner_script=Path(runner_script),  # type: ignore[arg-type]
            smoke_id=smoke_id,
            fixture_url=fixture_url,
            runner_output_path=paths[
                PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE
            ],
            screenshot_path=paths[
                PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE
            ],
            timeout_seconds=max(1, min(int(timeout_seconds), _TIMEOUT_SECONDS)),
        )
        _write_json_exclusive(
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE],
            execution_result,
        )

    status, decision, next_action = _status_decision_next_action(execution_result)
    plan = _plan_payload(
        selection_path=selection_path,
        selection_sha256=selection_sha256,
        candidate_manifest_path=manifest_path,
        candidate_manifest_sha256=candidate_sha256,
        selected_candidate=selected_candidate,
        candidate_manifest=normalized_manifest,
        output_path=output_path,
        fixture_paths=fixture_paths,
        fixture_url=fixture_url,
        smoke_id=smoke_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        executed=execute_local_fixture_smoke,
        smoke_status=status,
        smoke_decision=decision,
        next_allowed_action=next_action,
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE],
        plan,
    )
    _write_text_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE],
        _summary_markdown(plan, execution_result),
    )
    _write_text_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE],
        _checklist_markdown(plan),
    )
    smoke_manifest = _smoke_manifest_payload(
        output_path=output_path,
        paths=paths,
        fixture_paths=fixture_paths,
        plan=plan,
        selection_matrix_path=selection_path,
        selection_matrix_sha256=selection_sha256,
        candidate_manifest_path=manifest_path,
        candidate_manifest_sha256=candidate_sha256,
        executed=execute_local_fixture_smoke,
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE],
        smoke_manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path,
        paths,
        fixture_paths,
        executed=execute_local_fixture_smoke,
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    success = (
        bool(execution_result["success"])
        if execution_result is not None
        else True
    )
    payload = _launcher_payload(
        plan=plan,
        paths=paths,
        fixture_paths=fixture_paths,
        execution_result=execution_result,
        complete=success,
    )
    return PlaywrightLocalFixtureSandboxSmokeResult(
        selection_matrix_path=selection_path,
        candidate_manifest_path=manifest_path,
        output_dir=output_path,
        plan_path=paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE],
        smoke_manifest_path=paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE
        ],
        summary_path=paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE],
        checklist_path=paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE],
        artifact_index_path=paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        result_path=paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE]
        if execution_result is not None
        else None,
        runner_output_path=paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE
        ]
        if execution_result is not None
        else None,
        screenshot_path=paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE]
        if execution_result is not None
        else None,
        fixture_dir=output_path / FIXTURE_DIR_NAME,
        fixture_index_path=fixture_paths[FIXTURE_INDEX_FILE],
        fixture_app_js_path=fixture_paths[FIXTURE_APP_JS_FILE],
        fixture_style_css_path=fixture_paths[FIXTURE_STYLE_CSS_FILE],
        complete=success,
        executed=execute_local_fixture_smoke,
        success=success,
        smoke_status=status,
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _ALL_OUTPUT_FILES}


def _fixture_paths(output_path: Path) -> dict[str, Path]:
    fixture_dir = output_path / FIXTURE_DIR_NAME
    return {
        FIXTURE_INDEX_FILE: fixture_dir / FIXTURE_INDEX_FILE,
        FIXTURE_APP_JS_FILE: fixture_dir / FIXTURE_APP_JS_FILE,
        FIXTURE_STYLE_CSS_FILE: fixture_dir / FIXTURE_STYLE_CSS_FILE,
    }


def _preflight_output_error(
    output_path: Path,
    paths: dict[str, Path],
    fixture_paths: dict[str, Path],
) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    fixture_dir = output_path / FIXTURE_DIR_NAME
    if os.path.lexists(fixture_dir):
        return "fixture directory already exists"
    for file_name in sorted(paths):
        if os.path.lexists(paths[file_name]):
            return "playwright local fixture smoke output already exists: " + file_name
    for fixture_file in sorted(fixture_paths):
        if os.path.lexists(fixture_paths[fixture_file]):
            return "playwright local fixture file already exists: " + fixture_file
    return None


def _execution_preflight_error(
    *,
    execute_local_fixture_smoke: bool,
    node_command: Path | None,
    runner_script: Path | None,
    output_dir: Path,
) -> str | None:
    if not execute_local_fixture_smoke:
        return None
    if node_command is None:
        return "node_command is required for explicit local fixture execution"
    if runner_script is None:
        return "runner_script is required for explicit local fixture execution"
    node_error = _regular_file_error(Path(node_command), "node_command")
    if node_error is not None:
        return node_error
    runner_error = _regular_file_error(Path(runner_script), "runner_script")
    if runner_error is not None:
        return runner_error
    if Path(node_command).name.lower() in {"npm", "npx", "npm.cmd", "npx.cmd"}:
        return "node_command must not be npm or npx"
    if not _runner_script_in_allowed_root(Path(runner_script), output_dir):
        return "runner_script must be inside the repository or output_dir"
    return None


def _regular_file_error(path: Path, label: str) -> str | None:
    if not os.path.lexists(path):
        return label + " is missing"
    if path.is_symlink():
        return label + " must not be a symlink"
    if not path.is_file():
        return label + " must be a regular file"
    return None


def _runner_script_in_allowed_root(runner_script: Path, output_dir: Path) -> bool:
    try:
        runner_resolved = runner_script.resolve(strict=True)
    except OSError:
        return False
    return _path_is_inside(runner_resolved, _repo_root()) or _path_is_inside(
        runner_resolved,
        output_dir,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _validate_selection_matrix(
    matrix: dict[str, object],
) -> tuple[dict[str, object], str | None]:
    if matrix.get("matrix_type") != "real_github_candidate_selection_matrix_v1":
        return {}, "matrix_type must be real_github_candidate_selection_matrix_v1"
    candidates = matrix.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return {}, "selection matrix candidates must be a non-empty list"
    selected = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return {}, "selection matrix candidates must be objects"
        if candidate.get("selected_for_first_sandbox_smoke") is True:
            selected.append(candidate)
    if len(selected) != 1:
        return {}, "selection matrix must contain exactly one selected candidate"
    chosen = dict(selected[0])
    if chosen.get("candidate_id") != _CANDIDATE_ID:
        return {}, "selected candidate must be " + _CANDIDATE_ID
    if chosen.get("decision") != "select_for_first_bounded_sandbox_smoke":
        return {}, "selected candidate decision is not approved for this smoke"
    if (
        chosen.get("next_allowed_action")
        != "create_playwright_local_fixture_sandbox_smoke_plan"
    ):
        return {}, "selected candidate next_allowed_action is not this smoke plan"
    return chosen, None


def _validate_candidate_manifest(
    manifest: dict[str, object],
) -> tuple[dict[str, object], str | None]:
    if manifest.get("candidate_type") != "github_capability_candidate_v1":
        return {}, "candidate_type must be github_capability_candidate_v1"
    if manifest.get("candidate_id") != _CANDIDATE_ID:
        return {}, "candidate_id must be " + _CANDIDATE_ID
    if manifest.get("repo_full_name") != _REPO_FULL_NAME:
        return {}, "repo_full_name must be " + _REPO_FULL_NAME
    if manifest.get("intended_use") != _INTENDED_USE:
        return {}, "intended_use must be " + _INTENDED_USE
    domains = manifest.get("capability_domains")
    if not isinstance(domains, list) or _INTENDED_USE not in domains:
        return {}, "candidate must include browser_automation in capability_domains"
    declared_license = manifest.get("declared_license")
    if not _non_empty_text(declared_license):
        return {}, "declared_license must be non-empty"
    return {
        "candidate_type": "github_capability_candidate_v1",
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "intended_use": _INTENDED_USE,
        "capability_domains": list(domains),
        "declared_license": str(declared_license),
        "candidate_name": manifest.get("candidate_name"),
        "repo_url": manifest.get("repo_url"),
    }, None


def _fixture_content_error() -> str | None:
    combined = "\n".join((_FIXTURE_INDEX_HTML, _FIXTURE_APP_JS, _FIXTURE_STYLE_CSS))
    if FIXTURE_MARKER_TEXT not in _FIXTURE_INDEX_HTML:
        return "fixture marker text is missing"
    if 'id="smoke-button"' not in _FIXTURE_INDEX_HTML:
        return "fixture smoke button is missing"
    if 'id="smoke-status"' not in _FIXTURE_INDEX_HTML:
        return "fixture smoke status element is missing"
    if "http://" in combined or "https://" in combined:
        return "fixture must not contain external URLs"
    if "<form" in combined.lower():
        return "fixture must not contain forms"
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource"):
        if forbidden in _FIXTURE_APP_JS:
            return "fixture JavaScript must not contain network calls"
    return None


def _write_fixture_files(fixture_paths: dict[str, Path]) -> None:
    fixture_dir = fixture_paths[FIXTURE_INDEX_FILE].parent
    fixture_dir.mkdir()
    _write_text_exclusive(fixture_paths[FIXTURE_INDEX_FILE], _FIXTURE_INDEX_HTML)
    _write_text_exclusive(fixture_paths[FIXTURE_APP_JS_FILE], _FIXTURE_APP_JS)
    _write_text_exclusive(fixture_paths[FIXTURE_STYLE_CSS_FILE], _FIXTURE_STYLE_CSS)


def _execute_runner(
    *,
    node_command: Path,
    runner_script: Path,
    smoke_id: str,
    fixture_url: str,
    runner_output_path: Path,
    screenshot_path: Path,
    timeout_seconds: int,
) -> dict[str, object]:
    args = [
        node_command.as_posix(),
        runner_script.as_posix(),
        "--fixture-url",
        fixture_url,
        "--output-json",
        runner_output_path.as_posix(),
        "--screenshot-path",
        screenshot_path.as_posix(),
    ]
    stdout = ""
    stderr = ""
    returncode = None
    timed_out = False
    runner_parse_error = None
    runner_payload: dict[str, object] | None = None
    validation_error = None

    try:
        completed = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = _coerce_subprocess_text(error.stdout)
        stderr = _coerce_subprocess_text(error.stderr)

    if not runner_output_path.exists() and not timed_out:
        _write_json_exclusive(
            runner_output_path,
            {
                "runner_type": _RUNNER_TYPE,
                "fixture_url": fixture_url,
                "marker_found": False,
                "click_completed": False,
                "status_text": "",
                "non_local_request_count": 0,
                "non_local_requests": [],
                "screenshot_path": screenshot_path.as_posix(),
                "success": False,
                "error_code": "runner_output_missing",
            },
        )

    if runner_output_path.exists() and runner_output_path.is_file():
        try:
            loaded = json.loads(runner_output_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                runner_payload = loaded
            else:
                runner_parse_error = "runner output JSON must be an object"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            runner_parse_error = "runner output JSON is malformed: " + _safe_text(error)
    elif timed_out:
        runner_parse_error = "runner output JSON missing after timeout"
    else:
        runner_parse_error = "runner output JSON missing"

    if runner_payload is not None:
        validation_error = _runner_output_validation_error(runner_payload, fixture_url)

    stdout_captured, stdout_truncated = _truncate(stdout)
    stderr_captured, stderr_truncated = _truncate(stderr)
    success = _execution_success(
        returncode=returncode,
        timed_out=timed_out,
        runner_parse_error=runner_parse_error,
        runner_validation_error=validation_error,
        runner_payload=runner_payload,
    )
    marker_found = bool(runner_payload.get("marker_found")) if runner_payload else False
    click_completed = (
        bool(runner_payload.get("click_completed")) if runner_payload else False
    )
    status_text = str(runner_payload.get("status_text", "")) if runner_payload else ""
    non_local_request_count = (
        int(runner_payload.get("non_local_request_count", 0))
        if runner_payload
        and isinstance(runner_payload.get("non_local_request_count"), int)
        and not isinstance(runner_payload.get("non_local_request_count"), bool)
        else 0
    )
    non_local_requests = (
        list(runner_payload.get("non_local_requests", []))
        if runner_payload and isinstance(runner_payload.get("non_local_requests"), list)
        else []
    )
    return {
        "result_type": _RESULT_TYPE,
        "smoke_id": smoke_id,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": True,
        "execution_mode": "explicit_local_fixture_only",
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
        "owned_local_smoke_runner_executed": True,
        "node_command_path": node_command.as_posix(),
        "runner_script_path": runner_script.as_posix(),
        "fixture_url": fixture_url,
        "fixture_url_scheme": "file",
        "subprocess_shell_used": False,
        "subprocess_args": args,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "returncode": returncode,
        "stdout_captured": stdout_captured,
        "stderr_captured": stderr_captured,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "runner_output_json_path": runner_output_path.as_posix(),
        "screenshot_path": screenshot_path.as_posix(),
        "runner_output_parse_error": runner_parse_error,
        "runner_output_validation_error": validation_error,
        "marker_found": marker_found,
        "click_completed": click_completed,
        "status_text": status_text,
        "non_local_request_count": non_local_request_count,
        "non_local_requests": non_local_requests,
        "success": success,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "production_promotion_performed": False,
        "candidate_code_import_performed": False,
        "smoke_status": _COMPLETED_STATUS if success else _FAILED_STATUS,
        "smoke_decision": _PASSED_DECISION if success else _FAILED_DECISION,
        "next_allowed_action": _REVIEW_NEXT_ACTION if success else _FIX_NEXT_ACTION,
        "required_human_review": True,
        "required_human_approval": True,
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }


def _runner_output_validation_error(
    runner_payload: dict[str, object],
    fixture_url: str,
) -> str | None:
    if runner_payload.get("runner_type") != _RUNNER_TYPE:
        return "runner_type mismatch"
    if runner_payload.get("fixture_url") != fixture_url:
        return "runner fixture_url mismatch"
    if runner_payload.get("marker_found") is not True:
        return "runner did not find fixture marker"
    if runner_payload.get("click_completed") is not True:
        return "runner did not complete fixture click"
    if runner_payload.get("status_text") != "clicked":
        return "runner status_text is not clicked"
    request_count = runner_payload.get("non_local_request_count")
    if not isinstance(request_count, int) or isinstance(request_count, bool):
        return "runner non_local_request_count is malformed"
    if request_count > 0:
        return "runner recorded non-local requests"
    requests = runner_payload.get("non_local_requests")
    if not isinstance(requests, list):
        return "runner non_local_requests is malformed"
    if runner_payload.get("success") is not True:
        return "runner did not report success"
    if not isinstance(runner_payload.get("screenshot_path"), str):
        return "runner screenshot_path is malformed"
    return None


def _execution_success(
    *,
    returncode: int | None,
    timed_out: bool,
    runner_parse_error: str | None,
    runner_validation_error: str | None,
    runner_payload: dict[str, object] | None,
) -> bool:
    if runner_payload is None:
        return False
    return all(
        (
            timed_out is False,
            returncode == 0,
            runner_parse_error is None,
            runner_validation_error is None,
            runner_payload.get("success") is True,
        )
    )


def _status_decision_next_action(
    execution_result: dict[str, object] | None,
) -> tuple[str, str, str]:
    if execution_result is None:
        return _PLAN_READY_STATUS, _PLAN_READY_DECISION, _PLAN_NEXT_ACTION
    if execution_result["success"] is True:
        return _COMPLETED_STATUS, _PASSED_DECISION, _REVIEW_NEXT_ACTION
    return _FAILED_STATUS, _FAILED_DECISION, _FIX_NEXT_ACTION


def _plan_payload(
    *,
    selection_path: Path,
    selection_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    selected_candidate: dict[str, object],
    candidate_manifest: dict[str, object],
    output_path: Path,
    fixture_paths: dict[str, Path],
    fixture_url: str,
    smoke_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
    smoke_status: str,
    smoke_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    return {
        "smoke_type": _SMOKE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
        "smoke_id": smoke_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "selection_matrix_path": selection_path.as_posix(),
        "selection_matrix_sha256": selection_sha256,
        "candidate_manifest_path": candidate_manifest_path.as_posix(),
        "candidate_manifest_sha256": candidate_manifest_sha256,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "intended_use": _INTENDED_USE,
        "capability_domains": list(candidate_manifest["capability_domains"]),
        "declared_license": candidate_manifest["declared_license"],
        "selection_decision": selected_candidate["decision"],
        "fixture_dir": (output_path / FIXTURE_DIR_NAME).as_posix(),
        "fixture_index_path": fixture_paths[FIXTURE_INDEX_FILE].as_posix(),
        "fixture_app_js_path": fixture_paths[FIXTURE_APP_JS_FILE].as_posix(),
        "fixture_style_css_path": fixture_paths[FIXTURE_STYLE_CSS_FILE].as_posix(),
        "fixture_url": fixture_url,
        "fixture_url_scheme": "file",
        "fixture_contains_external_url": False,
        "fixture_contains_form": False,
        "fixture_contains_secret": False,
        "fixture_contains_network_call": False,
        "executed": executed,
        "execution_mode": "explicit_local_fixture_only" if executed else "plan_only",
        "owned_local_smoke_runner_executed": executed,
        "required_human_review": True,
        "required_human_approval": True,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "smoke_status": smoke_status,
        "smoke_decision": smoke_decision,
        "next_allowed_action": next_allowed_action,
        **dict(_DISABLED_CAPABILITY_FIELDS),
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }


def _smoke_manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    fixture_paths: dict[str, Path],
    plan: dict[str, object],
    selection_matrix_path: Path,
    selection_matrix_sha256: str,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    executed: bool,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
        "job_dir": output_path.as_posix(),
        "smoke_id": plan["smoke_id"],
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "selection_matrix_sha256": selection_matrix_sha256,
        "candidate_manifest_path": candidate_manifest_path.as_posix(),
        "candidate_manifest_sha256": candidate_manifest_sha256,
        "plan_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE]
        ),
        "summary_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE]
        ),
        "fixture_index_path": fixture_paths[FIXTURE_INDEX_FILE].as_posix(),
        "fixture_index_sha256": sha256_file(fixture_paths[FIXTURE_INDEX_FILE]),
        "fixture_app_js_path": fixture_paths[FIXTURE_APP_JS_FILE].as_posix(),
        "fixture_app_js_sha256": sha256_file(fixture_paths[FIXTURE_APP_JS_FILE]),
        "fixture_style_css_path": fixture_paths[FIXTURE_STYLE_CSS_FILE].as_posix(),
        "fixture_style_css_sha256": sha256_file(
            fixture_paths[FIXTURE_STYLE_CSS_FILE]
        ),
        "fixture_url": plan["fixture_url"],
        "fixture_url_scheme": "file",
        "executed": executed,
        "smoke_status": plan["smoke_status"],
        "smoke_decision": plan["smoke_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "required_human_review": True,
        "required_human_approval": True,
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }
    if executed:
        result_path = paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE]
        runner_output_path = paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE
        ]
        screenshot_path = paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE]
        manifest.update(
            {
                "result_path": result_path.as_posix(),
                "result_sha256": sha256_file(result_path),
                "runner_output_json_path": runner_output_path.as_posix(),
                "runner_output_json_sha256": sha256_file(runner_output_path)
                if runner_output_path.exists() and runner_output_path.is_file()
                else None,
                "screenshot_path": screenshot_path.as_posix(),
                "screenshot_sha256": sha256_file(screenshot_path)
                if screenshot_path.exists() and screenshot_path.is_file()
                else None,
            }
        )
    return manifest


def _artifact_index_payload(
    output_path: Path,
    paths: dict[str, Path],
    fixture_paths: dict[str, Path],
    *,
    executed: bool,
) -> dict[str, object]:
    artifact_roles = [
        (
            "playwright_local_fixture_sandbox_smoke_plan",
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE],
        ),
        (
            "playwright_local_fixture_sandbox_smoke_manifest",
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE],
        ),
        (
            "playwright_local_fixture_sandbox_smoke_summary",
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE],
        ),
        (
            "playwright_local_fixture_sandbox_smoke_checklist",
            paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE],
        ),
        ("fixture_index_html", fixture_paths[FIXTURE_INDEX_FILE]),
        ("fixture_app_js", fixture_paths[FIXTURE_APP_JS_FILE]),
        ("fixture_style_css", fixture_paths[FIXTURE_STYLE_CSS_FILE]),
    ]
    if executed:
        artifact_roles.extend(
            [
                (
                    "playwright_local_fixture_sandbox_smoke_result",
                    paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE],
                ),
                (
                    "playwright_local_fixture_sandbox_smoke_runner_output",
                    paths[
                        PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE
                    ],
                ),
                (
                    "playwright_local_fixture_sandbox_smoke_screenshot",
                    paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE],
                ),
            ]
        )
    entries = [
        _generated_artifact_entry(output_path, role, path)
        for role, path in artifact_roles
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": (
            "explicit_playwright_local_fixture_smoke_and_fixture_artifacts_only"
        ),
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _REVIEW_NEXT_ACTION if executed else _PLAN_NEXT_ACTION,
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
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
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
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
    plan: dict[str, object],
    paths: dict[str, Path],
    fixture_paths: dict[str, Path],
    execution_result: dict[str, object] | None,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "playwright_local_fixture_sandbox_smoke_plan_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_PLAN_FILE
        ].as_posix(),
        "playwright_local_fixture_sandbox_smoke_manifest_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_MANIFEST_FILE
        ].as_posix(),
        "playwright_local_fixture_sandbox_smoke_summary_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SUMMARY_FILE
        ].as_posix(),
        "playwright_local_fixture_sandbox_smoke_checklist_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_CHECKLIST_FILE
        ].as_posix(),
        "playwright_local_fixture_sandbox_smoke_result_path": None,
        "playwright_local_fixture_sandbox_smoke_runner_output_path": None,
        "playwright_local_fixture_sandbox_smoke_screenshot_path": None,
        "artifact_index_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "fixture_dir": Path(plan["fixture_dir"]).as_posix(),
        "fixture_index_path": fixture_paths[FIXTURE_INDEX_FILE].as_posix(),
        "fixture_app_js_path": fixture_paths[FIXTURE_APP_JS_FILE].as_posix(),
        "fixture_style_css_path": fixture_paths[FIXTURE_STYLE_CSS_FILE].as_posix(),
        "fixture_url": plan["fixture_url"],
        "fixture_url_scheme": "file",
        "smoke_id": plan["smoke_id"],
        "project_id": plan["project_id"],
        "reviewer_id": plan["reviewer_id"],
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "intended_use": _INTENDED_USE,
        "executed": plan["executed"],
        "success": complete,
        "bounded_local_fixture_execution_only": True,
        "owned_local_smoke_runner_executed": bool(plan["executed"]),
        "smoke_status": plan["smoke_status"],
        "smoke_decision": plan["smoke_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "required_human_review": True,
        "required_human_approval": True,
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }
    if execution_result is not None:
        payload.update(
            {
                "playwright_local_fixture_sandbox_smoke_result_path": paths[
                    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RESULT_FILE
                ].as_posix(),
                "playwright_local_fixture_sandbox_smoke_runner_output_path": paths[
                    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_RUNNER_OUTPUT_FILE
                ].as_posix(),
                "playwright_local_fixture_sandbox_smoke_screenshot_path": paths[
                    PLAYWRIGHT_LOCAL_FIXTURE_SANDBOX_SMOKE_SCREENSHOT_FILE
                ].as_posix(),
                "returncode": execution_result["returncode"],
                "marker_found": execution_result["marker_found"],
                "click_completed": execution_result["click_completed"],
                "status_text": execution_result["status_text"],
                "non_local_request_count": execution_result[
                    "non_local_request_count"
                ],
                "non_local_requests": execution_result["non_local_requests"],
            }
        )
    return payload


def _structured_failure_result(
    selection_matrix_path: Path,
    candidate_manifest_path: Path,
    output_path: Path,
    failure_stage: str,
    error_message: str,
    *,
    smoke_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    executed: bool,
) -> PlaywrightLocalFixtureSandboxSmokeResult:
    payload = {
        "complete": False,
        "smoke_type": _SMOKE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_scope": "bounded_local_fixture_execution_only",
        "bounded_local_fixture_execution_only": True,
        "smoke_id": smoke_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "selection_matrix_path": selection_matrix_path.as_posix(),
        "selection_matrix_sha256": None,
        "candidate_manifest_path": candidate_manifest_path.as_posix(),
        "candidate_manifest_sha256": None,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "executed": executed,
        "success": False,
        "owned_local_smoke_runner_executed": False,
        "smoke_status": _FAILED_STATUS,
        "smoke_decision": _FAILED_DECISION,
        "next_allowed_action": _FIX_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "playwright_local_fixture_sandbox_smoke_plan_path": None,
        "playwright_local_fixture_sandbox_smoke_manifest_path": None,
        "playwright_local_fixture_sandbox_smoke_summary_path": None,
        "playwright_local_fixture_sandbox_smoke_checklist_path": None,
        "playwright_local_fixture_sandbox_smoke_result_path": None,
        "playwright_local_fixture_sandbox_smoke_runner_output_path": None,
        "playwright_local_fixture_sandbox_smoke_screenshot_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "fixture_dir": None,
        "fixture_url": None,
        "fixture_url_scheme": None,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "required_human_review": True,
        "required_human_approval": True,
        **dict(_DISABLED_CAPABILITY_FIELDS),
        **dict(PLAYWRIGHT_BOUNDARY_FALSE_FIELDS),
    }
    return PlaywrightLocalFixtureSandboxSmokeResult(
        selection_matrix_path=selection_matrix_path,
        candidate_manifest_path=candidate_manifest_path,
        output_dir=output_path,
        plan_path=None,
        smoke_manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        result_path=None,
        runner_output_path=None,
        screenshot_path=None,
        fixture_dir=None,
        fixture_index_path=None,
        fixture_app_js_path=None,
        fixture_style_css_path=None,
        complete=False,
        executed=executed,
        success=False,
        smoke_status=_FAILED_STATUS,
        payload=payload,
    )


def _summary_markdown(
    plan: dict[str, object],
    execution_result: dict[str, object] | None,
) -> str:
    lines = [
        "# Playwright Local Fixture Sandbox Smoke",
        "",
        "Status: " + str(plan["smoke_status"]),
        "Candidate: " + str(plan["repo_full_name"]),
        "Fixture URL scheme: file",
        "Plan-only default: true",
        "Explicit execution requested: " + str(plan["executed"]).lower(),
        "Live website automation performed: false",
        "Account workflow performed: false",
        "Scraping performed: false",
        "Bypass performed: false",
        "Secret access performed: false",
        "Dependency installation performed: false",
        "Adapter generated: false",
        "Production promotion granted: false",
        "Next allowed action: " + str(plan["next_allowed_action"]),
        "",
        "Boundary: generated local fixture pages only; human review remains required.",
    ]
    if execution_result is not None:
        lines.insert(5, "Runner success: " + str(execution_result["success"]).lower())
    return "\n".join(lines)


def _checklist_markdown(plan: dict[str, object]) -> str:
    lines = [
        "# Playwright Local Fixture Sandbox Smoke Checklist",
        "",
        "- [ ] Confirm the selected matrix candidate is microsoft/playwright.",
        "- [ ] Confirm the fixture URL is file:// only.",
        "- [ ] Confirm no live websites, accounts, scraping, bypass, or secrets are involved.",
        "- [ ] Confirm no package install, browser download, npm, or npx occurred.",
        "- [ ] Confirm adapter generation and production promotion remain disabled.",
        "",
        "Smoke decision: " + str(plan["smoke_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    return "\n".join(lines)


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) <= _MAX_CAPTURE_CHARS:
        return text, False
    return text[:_MAX_CAPTURE_CHARS], True


def _coerce_subprocess_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
    return text[:240] if text else "playwright local fixture smoke failed"
