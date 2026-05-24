"""Local-fixture-only Playwright adapter admission gate.

This module is an evidence gate over an operator-provided #422 receipt tree.
It reads receipt artifacts, verifies their boundaries and hashes, and emits a
deterministic local-fixture-only admission or rejection decision. It does not
execute Playwright, Node, package managers, candidate code, or arbitrary
commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS",
    "LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS",
    "LocalFixturePlaywrightAdapterAdmissionGateResult",
    "build_local_fixture_playwright_adapter_admission_gate_plan",
    "run_local_fixture_playwright_adapter_admission_gate",
    "run_local_fixture_playwright_adapter_admission_gate_launcher",
]


LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE = (
    "local_fixture_playwright_adapter_admission_gate_plan.json"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE = (
    "local_fixture_playwright_adapter_admission_gate_manifest.json"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE = (
    "local_fixture_playwright_adapter_admission_gate_summary.md"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE = (
    "local_fixture_playwright_adapter_admission_gate_checklist.md"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE = (
    "local_fixture_playwright_adapter_admission_gate_decision.json"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION = (
    "I_REVIEWED_OPERATOR_PROVIDED_PLAYWRIGHT_RECEIPT_LOCAL_FIXTURE_ONLY_"
    "NO_LIVE_WEBSITES_NO_ACCOUNTS_NO_SCRAPING_NO_BYPASS"
)

_RECEIPT_PLAN_FILE = "operator_provided_playwright_execution_receipt_plan.json"
_RECEIPT_MANIFEST_FILE = "operator_provided_playwright_execution_receipt_manifest.json"
_RECEIPT_SUMMARY_FILE = "operator_provided_playwright_execution_receipt_summary.md"
_RECEIPT_CHECKLIST_FILE = "operator_provided_playwright_execution_receipt_checklist.md"
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

_GATE_TYPE = "local_fixture_playwright_adapter_admission_gate_v1"
_DECISION_TYPE = "local_fixture_playwright_adapter_admission_gate_decision_v1"
_MANIFEST_TYPE = "local_fixture_playwright_adapter_admission_gate_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_playwright_adapter_admission_gate_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_playwright_adapter_admission_gate_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_local_fixture_adapter_admission_gate_record"
_EXECUTION_CAPABILITY = "local_fixture_playwright_adapter_admission_gate_only"
_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_ADAPTER_CAPABILITY = "launch_bounded_playwright_worker_adapter_draft"
_GATE_ADAPTER_ID = "local_fixture_playwright_adapter_admission_gate"
_GATE_CAPABILITY = "launch_local_fixture_playwright_adapter_admission_gate"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_RECEIPT_TYPE = "operator_provided_local_playwright_execution_receipt_v1"
_RECEIPT_RESULT_TYPE = "operator_provided_local_playwright_execution_receipt_result_v1"
_ADAPTER_DRAFT_TYPE = "bounded_playwright_worker_adapter_draft_v1"
_SMOKE_TYPE = "playwright_local_fixture_bounded_sandbox_smoke_v1"

_PLAN_READY_STATUS = "local_fixture_playwright_adapter_admission_gate_plan_ready"
_ADMITTED_STATUS = "local_fixture_playwright_adapter_admission_gate_admitted"
_REJECTED_STATUS = "local_fixture_playwright_adapter_admission_gate_rejected"
_FAILED_STATUS = "local_fixture_playwright_adapter_admission_gate_failed"
_PLAN_READY_DECISION = "ready_to_evaluate_local_fixture_playwright_adapter_admission"
_ADMIT_DECISION = "admit_local_fixture_only_playwright_adapter"
_REJECT_DECISION = "reject_local_fixture_playwright_adapter"
_FIX_DECISION = "fix_receipt_or_adapter_and_retry"
_PLAN_NEXT_ACTION = "run_local_fixture_playwright_adapter_admission_gate"
_ADMITTED_NEXT_ACTION = "use_local_fixture_only_adapter_under_human_review"
_REJECTED_NEXT_ACTION = "fix_receipt_or_adapter_and_retry"
_STRONGER_SUITE_NEXT_ACTION = "run_stronger_local_fixture_scenario_suite"

_PLAN_OUTPUT_FILES = (
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
)
_RUN_OUTPUT_FILES = _PLAN_OUTPUT_FILES[:4] + (
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
)

LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS: dict[str, bool] = {
    "local_fixture_admission_granted": False,
    "production_admission_granted": False,
    "live_website_admission_granted": False,
    "general_browser_automation_admission_granted": False,
    "arbitrary_url_navigation_admission_granted": False,
    "account_workflow_admission_granted": False,
    "login_workflow_admission_granted": False,
    "registration_workflow_admission_granted": False,
    "scraping_admission_granted": False,
    "bypass_admission_granted": False,
    "captcha_workflow_admission_granted": False,
    "credential_input_admission_granted": False,
    "cookie_access_admission_granted": False,
    "external_network_admission_granted": False,
    "package_install_admission_granted": False,
    "browser_download_admission_granted": False,
    "npm_admission_granted": False,
    "npx_admission_granted": False,
    "candidate_repo_access_admission_granted": False,
    "candidate_code_import_admission_granted": False,
    "candidate_code_execution_admission_granted": False,
    "arbitrary_command_admission_granted": False,
    "production_promotion_granted": False,
    "autonomous_execution_admission_granted": False,
}

LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS: dict[str, bool] = {
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

_SOURCE_FALSE_FIELDS = tuple(
    sorted(
        set(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS)
        | {
            "adapter_generation_allowed",
            "adapter_registration_allowed",
            "arbitrary_command_allowed",
            "arbitrary_url_navigation_allowed",
            "auto_adoption_allowed",
            "autonomous_execution_allowed",
            "browser_download_allowed",
            "bypass_allowed",
            "candidate_code_execution_allowed",
            "candidate_code_import_allowed",
            "candidate_repo_access_allowed",
            "captcha_workflow_allowed",
            "cookie_access_allowed",
            "credential_input_allowed",
            "external_network_allowed",
            "live_website_automation_allowed",
            "login_workflow_allowed",
            "account_workflow_allowed",
            "npm_allowed",
            "npx_allowed",
            "package_install_allowed",
            "production_promotion_allowed",
            "registration_workflow_allowed",
            "scraping_allowed",
            "secret_access_allowed",
            "target_url_accepted",
            "user_supplied_url_accepted",
            "user_supplied_url_allowed",
            "candidate_code_import_performed",
            "production_promotion_performed",
        }
    )
)

_ROOT_RECEIPT_ARTIFACTS = {
    _RECEIPT_PLAN_FILE,
    _RECEIPT_MANIFEST_FILE,
    _RECEIPT_SUMMARY_FILE,
    _RECEIPT_CHECKLIST_FILE,
    _RECEIPT_RESULT_FILE,
    _RECEIPT_ARTIFACT_INDEX_FILE,
    _RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
}


@dataclass(frozen=True)
class LocalFixturePlaywrightAdapterAdmissionGateResult:
    receipt_dir: Path
    output_dir: Path
    gate_id: str
    plan_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    decision_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    admitted: bool
    gate_status: str
    gate_decision: str
    payload: dict[str, object]


def build_local_fixture_playwright_adapter_admission_gate_plan(
    receipt_dir: Path,
    output_dir: Path,
    gate_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixturePlaywrightAdapterAdmissionGateResult:
    """Create a non-evaluating admission gate plan."""

    return _build_or_run_gate(
        receipt_dir=receipt_dir,
        output_dir=output_dir,
        gate_id=gate_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        evaluate=False,
    )


def run_local_fixture_playwright_adapter_admission_gate_launcher(
    receipt_dir: Path,
    output_dir: Path,
    gate_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    plan_only: bool = False,
) -> LocalFixturePlaywrightAdapterAdmissionGateResult:
    """Launcher-oriented wrapper for plan or evidence-gate evaluation."""

    if plan_only:
        return build_local_fixture_playwright_adapter_admission_gate_plan(
            receipt_dir,
            output_dir,
            gate_id,
            review_attestation=review_attestation,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )
    return run_local_fixture_playwright_adapter_admission_gate(
        receipt_dir,
        output_dir,
        gate_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_playwright_adapter_admission_gate(
    receipt_dir: Path,
    output_dir: Path,
    gate_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixturePlaywrightAdapterAdmissionGateResult:
    """Evaluate #422 receipt evidence and write an admission or rejection."""

    return _build_or_run_gate(
        receipt_dir=receipt_dir,
        output_dir=output_dir,
        gate_id=gate_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        evaluate=True,
    )


def _build_or_run_gate(
    *,
    receipt_dir: Path,
    output_dir: Path,
    gate_id: str,
    review_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    evaluate: bool,
) -> LocalFixturePlaywrightAdapterAdmissionGateResult:
    receipt_path = Path(receipt_dir)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    output_files = _RUN_OUTPUT_FILES if evaluate else _PLAN_OUTPUT_FILES

    preflight_error = _preflight_error(
        receipt_path=receipt_path,
        output_path=output_path,
        gate_id=gate_id,
        review_attestation=review_attestation,
        output_files=output_files,
    )
    if preflight_error is not None:
        return _structured_failure_result(
            receipt_path,
            output_path,
            gate_id,
            preflight_error[0],
            preflight_error[1],
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )

    if not evaluate:
        plan = _plan_payload(
            receipt_dir=receipt_path,
            output_dir=output_path,
            paths=paths,
            gate_id=gate_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            review_attestation=review_attestation or "",
            gate_status=_PLAN_READY_STATUS,
            gate_decision=_PLAN_READY_DECISION,
            next_allowed_action=_PLAN_NEXT_ACTION,
            local_fixture_admission_granted=False,
        )
        _write_json_exclusive(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE],
            plan,
        )
        _write_text_exclusive(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE],
            _summary_markdown(plan, None),
        )
        _write_text_exclusive(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE],
            _checklist_markdown(plan, None),
        )
        manifest = _manifest_payload(
            output_path=output_path,
            paths=paths,
            plan=plan,
            decision=None,
            evaluated=False,
            admitted=False,
        )
        _write_json_exclusive(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE],
            manifest,
        )
        artifact_index = _artifact_index_payload(
            output_path=output_path,
            paths=paths,
            gate_id=gate_id,
            evaluated=False,
            admitted=False,
            gate_status=_PLAN_READY_STATUS,
            gate_decision=_PLAN_READY_DECISION,
            next_allowed_action=_PLAN_NEXT_ACTION,
        )
        _write_json_exclusive(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE],
            artifact_index,
        )
        index_manifest = _artifact_index_manifest_payload(output_path, paths, artifact_index)
        _write_json_exclusive(
            paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
            ],
            index_manifest,
        )
        payload = _launcher_payload(
            output_path=output_path,
            paths=paths,
            plan=plan,
            decision=None,
            evaluated=False,
            complete=True,
            admitted=False,
        )
        return LocalFixturePlaywrightAdapterAdmissionGateResult(
            receipt_dir=receipt_path,
            output_dir=output_path,
            gate_id=gate_id,
            plan_path=paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE],
            manifest_path=paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE
            ],
            summary_path=paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE
            ],
            checklist_path=paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE
            ],
            decision_path=None,
            artifact_index_path=paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE
            ],
            artifact_index_manifest_path=paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
            ],
            complete=True,
            admitted=False,
            gate_status=_PLAN_READY_STATUS,
            gate_decision=_PLAN_READY_DECISION,
            payload=payload,
        )

    evidence = _load_evidence(receipt_path)
    check_results, metrics = _evaluate_admission_checks(evidence)
    failed_checks = [check for check in check_results if not check["passed"]]
    admitted = not failed_checks
    gate_status = _ADMITTED_STATUS if admitted else _REJECTED_STATUS
    gate_decision = _ADMIT_DECISION if admitted else _REJECT_DECISION
    next_allowed_action = _ADMITTED_NEXT_ACTION if admitted else _REJECTED_NEXT_ACTION
    plan = _plan_payload(
        receipt_dir=receipt_path,
        output_dir=output_path,
        paths=paths,
        gate_id=gate_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        review_attestation=review_attestation or "",
        gate_status=gate_status,
        gate_decision=gate_decision,
        next_allowed_action=next_allowed_action,
        local_fixture_admission_granted=admitted,
    )
    decision = _decision_payload(
        gate_id=gate_id,
        plan=plan,
        evidence=evidence,
        metrics=metrics,
        check_results=check_results,
        admitted=admitted,
        gate_status=gate_status,
        gate_decision=gate_decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE],
        plan,
    )
    _write_text_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE],
        _summary_markdown(plan, decision),
    )
    _write_text_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE],
        _checklist_markdown(plan, decision),
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE],
        decision,
    )
    manifest = _manifest_payload(
        output_path=output_path,
        paths=paths,
        plan=plan,
        decision=decision,
        evaluated=True,
        admitted=admitted,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        gate_id=gate_id,
        evaluated=True,
        admitted=admitted,
        gate_status=gate_status,
        gate_decision=gate_decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    index_manifest = _artifact_index_manifest_payload(output_path, paths, artifact_index)
    _write_json_exclusive(
        paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        index_manifest,
    )
    payload = _launcher_payload(
        output_path=output_path,
        paths=paths,
        plan=plan,
        decision=decision,
        evaluated=True,
        complete=admitted,
        admitted=admitted,
    )
    return LocalFixturePlaywrightAdapterAdmissionGateResult(
        receipt_dir=receipt_path,
        output_dir=output_path,
        gate_id=gate_id,
        plan_path=paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE],
        manifest_path=paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE],
        summary_path=paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE],
        checklist_path=paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE
        ],
        decision_path=paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE
        ],
        artifact_index_path=paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=admitted,
        admitted=admitted,
        gate_status=gate_status,
        gate_decision=gate_decision,
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {
        file_name: output_path / file_name
        for file_name in (
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE,
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE,
        )
    }


def _preflight_error(
    *,
    receipt_path: Path,
    output_path: Path,
    gate_id: str,
    review_attestation: str | None,
    output_files: tuple[str, ...],
) -> tuple[str, str] | None:
    output_error = _real_existing_dir_error(output_path, "output_dir")
    if output_error is not None:
        return "preflight_output_dir", output_error
    for file_name in sorted(output_files):
        candidate = output_path / file_name
        if candidate.exists() or candidate.is_symlink():
            return "preflight_output_collision", "gate output artifact already exists"
    if not _non_empty_text(gate_id):
        return "preflight_gate_id", "gate_id is missing"
    attestation_error = _review_attestation_error(review_attestation)
    if attestation_error is not None:
        return "preflight_review_attestation", attestation_error
    receipt_error = _real_existing_dir_error(receipt_path, "receipt_dir")
    if receipt_error is not None:
        return "preflight_receipt_dir", receipt_error
    return None


def _real_existing_dir_error(path: Path, label: str) -> str | None:
    if path.is_symlink():
        return label + " must not be a symlink"
    if not path.exists():
        return label + " is missing"
    if not path.is_dir():
        return label + " must be a directory"
    return None


def _review_attestation_error(value: str | None) -> str | None:
    if not _non_empty_text(value):
        return "review_attestation is required"
    if value != LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_REVIEW_ATTESTATION:
        return "review_attestation must match required local fixture-only review phrase"
    return None


def _plan_payload(
    *,
    receipt_dir: Path,
    output_dir: Path,
    paths: dict[str, Path],
    gate_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    review_attestation: str,
    gate_status: str,
    gate_decision: str,
    next_allowed_action: str,
    local_fixture_admission_granted: bool,
) -> dict[str, object]:
    receipt_paths = _receipt_paths(receipt_dir)
    disabled_fields = _admission_false_fields(local_fixture_admission_granted)
    return {
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "gate_id": gate_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "review_attestation_present": True,
        "review_attestation_sha256": _sha256_text(review_attestation),
        "receipt_dir": receipt_dir.as_posix(),
        "receipt_plan_path": receipt_paths["receipt_plan"].as_posix(),
        "receipt_manifest_path": receipt_paths["receipt_manifest"].as_posix(),
        "receipt_result_path": receipt_paths["receipt_result"].as_posix(),
        "receipt_artifact_index_path": receipt_paths["receipt_artifact_index"].as_posix(),
        "adapter_draft_run_dir": receipt_paths["adapter_draft_run_dir"].as_posix(),
        "adapter_draft_plan_path": receipt_paths["adapter_draft_plan"].as_posix(),
        "adapter_draft_manifest_path": receipt_paths["adapter_draft_manifest"].as_posix(),
        "adapter_draft_result_path": receipt_paths["adapter_draft_result"].as_posix(),
        "embedded_smoke_dir": receipt_paths["embedded_smoke_dir"].as_posix(),
        "embedded_smoke_plan_path": receipt_paths["embedded_smoke_plan"].as_posix(),
        "embedded_smoke_manifest_path": receipt_paths[
            "embedded_smoke_manifest"
        ].as_posix(),
        "embedded_smoke_result_path": receipt_paths["embedded_smoke_result"].as_posix(),
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "receipt_type": _RECEIPT_TYPE,
        "source_adapter_draft_type": _ADAPTER_DRAFT_TYPE,
        "source_smoke_type": _SMOKE_TYPE,
        "admitted_scope": "local_fixture_only" if local_fixture_admission_granted else "none",
        "production_scope": "denied",
        "live_website_scope": "denied",
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "gate_adapter_id": _GATE_ADAPTER_ID,
        "gate_capability": _GATE_CAPABILITY,
        "gate_output_dir": output_dir.as_posix(),
        "gate_plan_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE
        ].as_posix(),
        "gate_manifest_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE
        ].as_posix(),
        "gate_decision_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE
        ].as_posix(),
        "gate_status": gate_status,
        "gate_decision": gate_decision,
        "next_allowed_action": next_allowed_action,
        "operator_runtime_metadata_evidence_only": True,
        "no_new_execution_performed": True,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **disabled_fields,
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }


def _receipt_paths(receipt_dir: Path) -> dict[str, Path]:
    adapter_dir = receipt_dir / _ADAPTER_DRAFT_RUN_DIR
    embedded_dir = adapter_dir / _EMBEDDED_SMOKE_DIR
    fixture_dir = embedded_dir / _FIXTURE_DIR
    return {
        "receipt_plan": receipt_dir / _RECEIPT_PLAN_FILE,
        "receipt_manifest": receipt_dir / _RECEIPT_MANIFEST_FILE,
        "receipt_summary": receipt_dir / _RECEIPT_SUMMARY_FILE,
        "receipt_checklist": receipt_dir / _RECEIPT_CHECKLIST_FILE,
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


def _load_evidence(receipt_dir: Path) -> dict[str, object]:
    paths = _receipt_paths(receipt_dir)
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
    return {
        "receipt_dir": receipt_dir,
        "paths": paths,
        "payloads": payloads,
        "errors": errors,
    }


def _evaluate_admission_checks(
    evidence: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    paths = evidence["paths"]  # type: ignore[assignment]
    payloads = evidence["payloads"]  # type: ignore[assignment]
    errors = evidence["errors"]  # type: ignore[assignment]
    receipt_dir = Path(evidence["receipt_dir"])  # type: ignore[arg-type]

    metrics = _evidence_metrics(receipt_dir, paths, payloads)
    checks: list[dict[str, object]] = []

    def add(check_id: str, passed: bool, message: str, path_key: str | None = None) -> None:
        evidence_path = None if path_key is None else Path(paths[path_key]).as_posix()
        checks.append(
            {
                "check_id": check_id,
                "passed": bool(passed),
                "severity": "blocker",
                "message": message,
                "evidence_path": evidence_path,
            }
        )

    add("receipt_plan_exists", _regular_file_ok(paths["receipt_plan"]), "receipt plan exists", "receipt_plan")
    add(
        "receipt_manifest_exists",
        _regular_file_ok(paths["receipt_manifest"]),
        "receipt manifest exists",
        "receipt_manifest",
    )
    add("receipt_result_exists", _regular_file_ok(paths["receipt_result"]), "receipt result exists", "receipt_result")
    add(
        "receipt_artifact_index_exists",
        _regular_file_ok(paths["receipt_artifact_index"]),
        "receipt artifact index exists",
        "receipt_artifact_index",
    )
    add(
        "adapter_draft_result_exists",
        _regular_file_ok(paths["adapter_draft_result"]),
        "adapter draft result exists",
        "adapter_draft_result",
    )
    add(
        "embedded_smoke_result_exists",
        _regular_file_ok(paths["embedded_smoke_result"]),
        "embedded smoke result exists",
        "embedded_smoke_result",
    )
    add(
        "receipt_type_expected",
        payloads["receipt_plan"].get("receipt_type") == _RECEIPT_TYPE,
        errors.get("receipt_plan") or "receipt type is expected",
        "receipt_plan",
    )
    add(
        "receipt_result_type_expected",
        payloads["receipt_result"].get("result_type") == _RECEIPT_RESULT_TYPE,
        errors.get("receipt_result") or "receipt result type is expected",
        "receipt_result",
    )
    add(
        "adapter_draft_type_expected",
        payloads["adapter_draft_plan"].get("adapter_draft_type") == _ADAPTER_DRAFT_TYPE,
        errors.get("adapter_draft_plan") or "adapter draft type is expected",
        "adapter_draft_plan",
    )
    add(
        "embedded_smoke_type_expected",
        payloads["embedded_smoke_plan"].get("smoke_type") == _SMOKE_TYPE,
        errors.get("embedded_smoke_plan") or "embedded smoke type is expected",
        "embedded_smoke_plan",
    )
    add(
        "candidate_id_expected",
        _all_present_identifiers_match(payloads, "candidate_id", _CANDIDATE_ID)
        and _all_present_identifiers_match(payloads, "selected_candidate_id", _CANDIDATE_ID),
        "candidate identifiers match expected Playwright candidate",
        "receipt_result",
    )
    add(
        "repo_full_name_expected",
        _all_present_identifiers_match(payloads, "repo_full_name", _REPO_FULL_NAME),
        "repository identifiers match expected Playwright repository",
        "receipt_result",
    )
    add(
        "receipt_success_true",
        payloads["receipt_result"].get("success") is True,
        "receipt result reports success true",
        "receipt_result",
    )
    add(
        "adapter_draft_success_true",
        payloads["adapter_draft_result"].get("success") is True,
        "adapter draft result reports success true",
        "adapter_draft_result",
    )
    add(
        "embedded_smoke_success_true",
        payloads["embedded_smoke_result"].get("success") is True,
        "embedded smoke result reports success true",
        "embedded_smoke_result",
    )
    add(
        "embedded_fixture_scheme_file",
        bool(metrics["embedded_fixture_scheme_file"]),
        "embedded fixture scheme is file",
        "embedded_smoke_result",
    )
    add(
        "embedded_non_local_request_count_zero",
        bool(metrics["embedded_non_local_request_count_zero"]),
        "embedded non-local request count is zero",
        "embedded_smoke_result",
    )
    add(
        "all_receipt_boundary_false_fields_false",
        not _true_fields(
            {
                "receipt_plan": payloads["receipt_plan"],
                "receipt_manifest": payloads["receipt_manifest"],
                "receipt_result": payloads["receipt_result"],
                "receipt_artifact_index": payloads["receipt_artifact_index"],
                "receipt_artifact_index_manifest": payloads[
                    "receipt_artifact_index_manifest"
                ],
            }
        ),
        "receipt boundary fields remain false",
        "receipt_result",
    )
    add(
        "all_adapter_boundary_false_fields_false",
        not _true_fields(
            {
                "adapter_draft_plan": payloads["adapter_draft_plan"],
                "adapter_draft_manifest": payloads["adapter_draft_manifest"],
                "adapter_draft_result": payloads["adapter_draft_result"],
                "adapter_draft_artifact_index": payloads[
                    "adapter_draft_artifact_index"
                ],
                "adapter_draft_artifact_index_manifest": payloads[
                    "adapter_draft_artifact_index_manifest"
                ],
            }
        ),
        "adapter draft boundary fields remain false",
        "adapter_draft_result",
    )
    add(
        "all_embedded_smoke_boundary_false_fields_false",
        not _true_fields(
            {
                "embedded_smoke_plan": payloads["embedded_smoke_plan"],
                "embedded_smoke_manifest": payloads["embedded_smoke_manifest"],
                "embedded_smoke_result": payloads["embedded_smoke_result"],
                "embedded_smoke_runner_output": payloads["embedded_smoke_runner_output"],
                "embedded_smoke_artifact_index": payloads[
                    "embedded_smoke_artifact_index"
                ],
                "embedded_smoke_artifact_index_manifest": payloads[
                    "embedded_smoke_artifact_index_manifest"
                ],
            }
        ),
        "embedded smoke boundary fields remain false where available",
        "embedded_smoke_result",
    )
    add(
        "target_url_not_accepted",
        not _any_true(payloads, ("target_url_accepted",)),
        "target URL is not accepted",
        "receipt_plan",
    )
    add(
        "user_supplied_url_not_used",
        not _any_true(payloads, ("user_supplied_url_accepted", "user_supplied_url_used")),
        "user-supplied URL is not used",
        "receipt_plan",
    )
    add(
        "live_website_not_allowed_or_performed",
        not _any_true(payloads, ("live_website_automation_allowed", "live_website_automation_performed")),
        "live website automation is neither allowed nor performed",
        "receipt_plan",
    )
    add(
        "account_scraping_bypass_captcha_not_allowed_or_performed",
        not _any_true(
            payloads,
            (
                "account_workflow_allowed",
                "account_workflow_performed",
                "login_workflow_allowed",
                "login_workflow_performed",
                "registration_workflow_allowed",
                "registration_workflow_performed",
                "scraping_allowed",
                "scraping_performed",
                "bypass_allowed",
                "bypass_performed",
                "captcha_workflow_allowed",
                "captcha_workflow_performed",
            ),
        ),
        "accounts, scraping, bypass, and captcha workflow remain blocked",
        "receipt_plan",
    )
    add(
        "secrets_cookies_not_allowed_or_performed",
        not _any_true(
            payloads,
            (
                "secret_access_allowed",
                "secret_access_performed",
                "credential_input_allowed",
                "credential_input_performed",
                "cookie_access_allowed",
                "cookie_access_performed",
            ),
        ),
        "secrets, credentials, and cookies remain blocked",
        "receipt_plan",
    )
    add(
        "external_network_not_allowed_or_performed",
        not _any_true(payloads, ("external_network_allowed", "external_network_performed")),
        "external network remains blocked",
        "receipt_plan",
    )
    add(
        "install_download_npm_npx_not_allowed_or_performed",
        not _any_true(
            payloads,
            (
                "package_install_allowed",
                "package_install_performed",
                "browser_download_allowed",
                "browser_download_performed",
                "npm_allowed",
                "npm_performed",
                "npx_allowed",
                "npx_performed",
                "dependency_installation_performed",
            ),
        ),
        "package installation, browser download, and package runners remain blocked",
        "receipt_plan",
    )
    add(
        "candidate_repo_code_not_accessed_or_executed",
        not _any_true(
            payloads,
            (
                "candidate_repo_access_allowed",
                "candidate_repo_access_performed",
                "candidate_code_import_allowed",
                "candidate_code_imported",
                "candidate_code_import_performed",
                "candidate_code_execution_allowed",
                "candidate_code_execution_performed",
                "candidate_repo_mutation_performed",
            ),
        ),
        "candidate repository code is neither accessed nor executed",
        "receipt_plan",
    )
    add(
        "arbitrary_command_not_allowed_or_performed",
        not _any_true(payloads, ("arbitrary_command_allowed", "arbitrary_command_execution_performed")),
        "arbitrary command execution remains blocked",
        "receipt_plan",
    )
    add(
        "production_promotion_not_granted",
        not _any_true(
            payloads,
            (
                "production_promotion_allowed",
                "production_promotion_granted",
                "production_promotion_performed",
            ),
        ),
        "production promotion is not granted",
        "receipt_plan",
    )
    add(
        "autonomy_not_granted_or_performed",
        not _any_true(
            payloads,
            (
                "autonomous_execution_allowed",
                "autonomous_execution_performed",
                "automatic_approval_performed",
                "auto_adoption_allowed",
                "auto_adoption_performed",
            ),
        ),
        "autonomy is not granted or performed",
        "receipt_plan",
    )
    add(
        "receipt_artifact_index_paths_under_receipt_dir",
        bool(metrics["receipt_artifact_index_paths_under_receipt_dir"]),
        "receipt artifact index paths resolve under receipt_dir",
        "receipt_artifact_index",
    )
    add(
        "receipt_artifact_index_no_symlink_paths",
        bool(metrics["receipt_artifact_index_no_symlink_paths"]),
        "receipt artifact index paths are not symlinks",
        "receipt_artifact_index",
    )
    add(
        "adapter_draft_run_dir_not_symlink",
        bool(metrics["adapter_draft_run_dir_not_symlink"]),
        "adapter_draft_run directory is present and not a symlink",
        "adapter_draft_result",
    )
    add(
        "embedded_smoke_dir_not_symlink",
        bool(metrics["embedded_smoke_dir_not_symlink"]),
        "embedded smoke directory is present and not a symlink",
        "embedded_smoke_result",
    )
    add(
        "candidate_repo_files_not_indexed",
        not bool(metrics["candidate_repo_files_indexed"]),
        "candidate repository files are not indexed",
        "receipt_artifact_index",
    )
    add(
        "external_candidate_artifacts_not_indexed",
        not bool(metrics["external_candidate_artifacts_indexed"]),
        "external candidate artifacts are not indexed",
        "receipt_artifact_index",
    )
    add(
        "receipt_artifact_hashes_match_existing_files",
        bool(metrics["receipt_artifact_hashes_match_existing_files"]),
        "receipt artifact hashes match existing files",
        "receipt_artifact_index",
    )
    add(
        "adapter_draft_artifact_hashes_match_existing_files",
        bool(metrics["adapter_draft_artifact_hashes_match_existing_files"]),
        "adapter draft artifact hashes match existing files",
        "adapter_draft_artifact_index",
    )
    add(
        "embedded_smoke_artifact_hashes_match_existing_files",
        bool(metrics["embedded_smoke_artifact_hashes_match_existing_files"]),
        "embedded smoke artifact hashes match existing files",
        "embedded_smoke_artifact_index",
    )
    add(
        "receipt_manifest_hashes_match_existing_files",
        bool(metrics["receipt_manifest_hashes_match_existing_files"]),
        "receipt manifest hashes match existing files",
        "receipt_manifest",
    )
    add(
        "adapter_manifest_hashes_match_existing_files",
        bool(metrics["adapter_manifest_hashes_match_existing_files"]),
        "adapter manifest hashes match existing files",
        "adapter_draft_manifest",
    )
    add(
        "embedded_smoke_manifest_hashes_match_existing_files",
        bool(metrics["embedded_smoke_manifest_hashes_match_existing_files"]),
        "embedded smoke manifest hashes match existing files",
        "embedded_smoke_manifest",
    )
    add(
        "receipt_plan_manifest_result_index_identifiers_agree",
        bool(metrics["key_identifiers_agree"]),
        "receipt plan, manifest, result, and indexes agree on key identifiers",
        "receipt_result",
    )
    add(
        "operator_runtime_metadata_present",
        bool(metrics["operator_runtime_metadata_present"]),
        "operator-provided runtime metadata is present as evidence only",
        "receipt_result",
    )
    return checks, metrics


def _evidence_metrics(
    receipt_dir: Path,
    paths: dict[str, Path],
    payloads: dict[str, dict[str, object]],
) -> dict[str, object]:
    fixture_url = _first_text(
        payloads["receipt_result"].get("embedded_fixture_url"),
        payloads["adapter_draft_result"].get("embedded_fixture_url"),
        payloads["embedded_smoke_result"].get("fixture_url"),
        payloads["embedded_smoke_runner_output"].get("fixture_url"),
        payloads["embedded_smoke_plan"].get("fixture_url"),
    )
    scheme_values = [
        str(value)
        for value in (
            payloads["receipt_result"].get("embedded_fixture_url_scheme"),
            payloads["adapter_draft_result"].get("embedded_fixture_url_scheme"),
            payloads["adapter_draft_plan"].get("embedded_fixture_url_scheme"),
            payloads["embedded_smoke_result"].get("fixture_url_scheme"),
            payloads["embedded_smoke_plan"].get("fixture_url_scheme"),
        )
        if isinstance(value, str) and value
    ]
    if fixture_url:
        scheme_values.append(_scheme_from_reference(fixture_url))
    embedded_fixture_scheme = scheme_values[0] if scheme_values else None
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
    embedded_non_local_request_count = present_counts[0] if present_counts else None

    receipt_index_verification = _verify_index_payload(
        payloads["receipt_artifact_index"],
        receipt_dir,
        allowed_root_only=True,
    )
    adapter_index_verification = _verify_index_payload(
        payloads["adapter_draft_artifact_index"],
        receipt_dir,
        allowed_root_only=False,
    )
    smoke_index_verification = _verify_index_payload(
        payloads["embedded_smoke_artifact_index"],
        receipt_dir,
        allowed_root_only=False,
    )
    receipt_manifest_hashes = _verify_manifest_hashes(
        payloads["receipt_manifest"],
        receipt_dir,
    )
    adapter_manifest_hashes = _verify_manifest_hashes(
        payloads["adapter_draft_manifest"],
        receipt_dir,
    )
    smoke_manifest_hashes = _verify_manifest_hashes(
        payloads["embedded_smoke_manifest"],
        receipt_dir,
    )
    return {
        "receipt_id": _first_text(
            payloads["receipt_plan"].get("receipt_id"),
            payloads["receipt_manifest"].get("receipt_id"),
            payloads["receipt_result"].get("receipt_id"),
        ),
        "adapter_draft_id": _first_text(
            payloads["receipt_plan"].get("adapter_draft_id"),
            payloads["receipt_manifest"].get("adapter_draft_id"),
            payloads["receipt_result"].get("adapter_draft_id"),
            payloads["adapter_draft_plan"].get("adapter_draft_id"),
            payloads["adapter_draft_manifest"].get("adapter_draft_id"),
            payloads["adapter_draft_result"].get("adapter_draft_id"),
        ),
        "receipt_success": payloads["receipt_result"].get("success") is True,
        "adapter_draft_success": payloads["adapter_draft_result"].get("success")
        is True,
        "embedded_smoke_success": payloads["embedded_smoke_result"].get("success")
        is True,
        "embedded_fixture_url": fixture_url,
        "embedded_fixture_url_scheme": embedded_fixture_scheme,
        "embedded_fixture_scheme_file": bool(scheme_values)
        and all(value == "file" for value in scheme_values),
        "embedded_non_local_request_count": embedded_non_local_request_count,
        "embedded_non_local_request_count_zero": bool(present_counts)
        and all(value == 0 for value in present_counts),
        "receipt_artifact_index_paths_under_receipt_dir": receipt_index_verification[
            "paths_under_receipt_dir"
        ],
        "receipt_artifact_index_no_symlink_paths": receipt_index_verification[
            "no_symlink_paths"
        ],
        "receipt_artifact_hashes_match_existing_files": receipt_index_verification[
            "receipt_hashes_match"
        ],
        "adapter_draft_artifact_hashes_match_existing_files": adapter_index_verification[
            "all_hashes_match"
        ],
        "embedded_smoke_artifact_hashes_match_existing_files": smoke_index_verification[
            "all_hashes_match"
        ],
        "receipt_manifest_hashes_match_existing_files": receipt_manifest_hashes,
        "adapter_manifest_hashes_match_existing_files": adapter_manifest_hashes,
        "embedded_smoke_manifest_hashes_match_existing_files": smoke_manifest_hashes,
        "artifact_hashes_verified": all(
            (
                receipt_index_verification["receipt_hashes_match"],
                adapter_index_verification["all_hashes_match"],
                smoke_index_verification["all_hashes_match"],
                receipt_manifest_hashes,
                adapter_manifest_hashes,
                smoke_manifest_hashes,
            )
        ),
        "candidate_repo_files_indexed": any(
            (
                receipt_index_verification["candidate_repo_files_indexed"],
                adapter_index_verification["candidate_repo_files_indexed"],
                smoke_index_verification["candidate_repo_files_indexed"],
            )
        ),
        "external_candidate_artifacts_indexed": any(
            (
                receipt_index_verification["external_candidate_artifacts_indexed"],
                adapter_index_verification["external_candidate_artifacts_indexed"],
                smoke_index_verification["external_candidate_artifacts_indexed"],
            )
        ),
        "key_identifiers_agree": _key_identifiers_agree(payloads),
        "operator_runtime_metadata_present": _operator_runtime_metadata_present(payloads),
        "artifact_index_under_receipt_dir": _path_is_inside(
            paths["receipt_artifact_index"],
            receipt_dir,
        ),
        "adapter_draft_run_dir_not_symlink": _directory_ok(
            paths["adapter_draft_run_dir"]
        ),
        "embedded_smoke_dir_not_symlink": _directory_ok(paths["embedded_smoke_dir"]),
    }


def _verify_index_payload(
    index_payload: dict[str, object],
    receipt_dir: Path,
    *,
    allowed_root_only: bool,
) -> dict[str, bool]:
    entries = index_payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return {
            "paths_under_receipt_dir": False,
            "no_symlink_paths": False,
            "all_hashes_match": False,
            "receipt_hashes_match": False,
            "candidate_repo_files_indexed": bool(
                index_payload.get("candidate_repo_files_indexed") is True
            ),
            "external_candidate_artifacts_indexed": bool(
                index_payload.get("external_candidate_artifacts_indexed") is True
            ),
        }
    paths_under = True
    no_symlinks = True
    all_hashes = True
    receipt_hashes = True
    saw_receipt_entry = False
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
        if path.is_symlink() or _path_has_symlink_component(path, receipt_dir):
            no_symlinks = False
            all_hashes = False
        if not _path_is_inside(path, receipt_dir):
            paths_under = False
            external_candidate_artifacts_indexed = True
            all_hashes = False
        if allowed_root_only and not _receipt_index_path_allowed(path, receipt_dir):
            paths_under = False
            all_hashes = False
        if not path.exists() or not path.is_file() or path.is_symlink():
            all_hashes = False
            if _receipt_index_path_allowed(path, receipt_dir):
                receipt_hashes = False
            continue
        recorded_hash = entry.get("sha256")
        if isinstance(recorded_hash, str) and recorded_hash:
            actual_hash = sha256_file(path)
            if actual_hash != recorded_hash:
                all_hashes = False
                if _is_root_receipt_artifact(path, receipt_dir):
                    receipt_hashes = False
        if _is_root_receipt_artifact(path, receipt_dir):
            saw_receipt_entry = True
    if not saw_receipt_entry and allowed_root_only:
        receipt_hashes = False
    return {
        "paths_under_receipt_dir": paths_under,
        "no_symlink_paths": no_symlinks,
        "all_hashes_match": all_hashes,
        "receipt_hashes_match": receipt_hashes,
        "candidate_repo_files_indexed": candidate_repo_files_indexed,
        "external_candidate_artifacts_indexed": external_candidate_artifacts_indexed,
    }


def _verify_manifest_hashes(manifest: dict[str, object], receipt_dir: Path) -> bool:
    if not manifest:
        return False
    checked = 0
    ok = True
    for key, path_value in manifest.items():
        if not key.endswith("_path") or not isinstance(path_value, str):
            continue
        prefix = key[:-5]
        sha_key = prefix + "_sha256"
        recorded_hash = manifest.get(sha_key)
        if not isinstance(recorded_hash, str) or not recorded_hash:
            continue
        path = Path(path_value)
        if not _path_is_inside(path, receipt_dir):
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
            if not _path_is_inside(path, receipt_dir):
                continue
            checked += 1
            if path.is_symlink() or not path.exists() or not path.is_file():
                ok = False
                continue
            if sha256_file(path) != recorded_hash:
                ok = False
    return checked > 0 and ok


def _decision_payload(
    *,
    gate_id: str,
    plan: dict[str, object],
    evidence: dict[str, object],
    metrics: dict[str, object],
    check_results: list[dict[str, object]],
    admitted: bool,
    gate_status: str,
    gate_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    failed = [check for check in check_results if not check["passed"]]
    disabled_fields = _admission_false_fields(admitted)
    return {
        "decision_type": _DECISION_TYPE,
        "gate_id": gate_id,
        "receipt_id": metrics.get("receipt_id"),
        "adapter_draft_id": metrics.get("adapter_draft_id"),
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "admitted_scope": "local_fixture_only" if admitted else "none",
        "production_scope": "denied",
        "live_website_scope": "denied",
        "gate_status": gate_status,
        "gate_decision": gate_decision,
        "next_allowed_action": next_allowed_action,
        "admission_checks_total": len(check_results),
        "admission_checks_passed": len(check_results) - len(failed),
        "admission_checks_failed": len(failed),
        "admission_check_results": check_results,
        "failed_check_ids": [str(check["check_id"]) for check in failed],
        "receipt_success": bool(metrics["receipt_success"]),
        "adapter_draft_success": bool(metrics["adapter_draft_success"]),
        "embedded_smoke_success": bool(metrics["embedded_smoke_success"]),
        "embedded_fixture_url": metrics.get("embedded_fixture_url"),
        "embedded_fixture_url_scheme": metrics.get("embedded_fixture_url_scheme"),
        "embedded_non_local_request_count": metrics.get(
            "embedded_non_local_request_count"
        ),
        "artifact_index_under_receipt_dir": bool(
            metrics["artifact_index_under_receipt_dir"]
        ),
        "artifact_hashes_verified": bool(metrics["artifact_hashes_verified"]),
        "candidate_repo_files_indexed": bool(metrics["candidate_repo_files_indexed"]),
        "external_candidate_artifacts_indexed": bool(
            metrics["external_candidate_artifacts_indexed"]
        ),
        "receipt_dir": Path(evidence["receipt_dir"]).as_posix(),
        "gate_plan_path": plan["gate_plan_path"],
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **disabled_fields,
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    plan: dict[str, object],
    decision: dict[str, object] | None,
    evaluated: bool,
    admitted: bool,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "gate_id": plan["gate_id"],
        "gate_adapter_id": _GATE_ADAPTER_ID,
        "gate_capability": _GATE_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "plan_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE]
        ),
        "receipt_dir": plan["receipt_dir"],
        "receipt_plan_path": plan["receipt_plan_path"],
        "receipt_manifest_path": plan["receipt_manifest_path"],
        "receipt_result_path": plan["receipt_result_path"],
        "receipt_artifact_index_path": plan["receipt_artifact_index_path"],
        "adapter_draft_run_dir": plan["adapter_draft_run_dir"],
        "adapter_draft_plan_path": plan["adapter_draft_plan_path"],
        "adapter_draft_manifest_path": plan["adapter_draft_manifest_path"],
        "adapter_draft_result_path": plan["adapter_draft_result_path"],
        "embedded_smoke_dir": plan["embedded_smoke_dir"],
        "embedded_smoke_plan_path": plan["embedded_smoke_plan_path"],
        "embedded_smoke_manifest_path": plan["embedded_smoke_manifest_path"],
        "embedded_smoke_result_path": plan["embedded_smoke_result_path"],
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "adapter_id": _ADAPTER_ID,
        "adapter_capability": _ADAPTER_CAPABILITY,
        "gate_status": plan["gate_status"],
        "gate_decision": plan["gate_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "evaluated": evaluated,
        "admitted": admitted,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **_admission_false_fields(admitted),
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }
    if decision is not None:
        decision_path = paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE]
        manifest.update(
            {
                "decision_path": decision_path.as_posix(),
                "decision_sha256": sha256_file(decision_path),
                "admission_checks_total": decision["admission_checks_total"],
                "admission_checks_failed": decision["admission_checks_failed"],
                "artifact_hashes_verified": decision["artifact_hashes_verified"],
            }
        )
    return manifest


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    gate_id: str,
    evaluated: bool,
    admitted: bool,
    gate_status: str,
    gate_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = [
        (
            "local_fixture_playwright_adapter_admission_gate_plan",
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE],
        ),
        (
            "local_fixture_playwright_adapter_admission_gate_manifest",
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE],
        ),
        (
            "local_fixture_playwright_adapter_admission_gate_summary",
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE],
        ),
        (
            "local_fixture_playwright_adapter_admission_gate_checklist",
            paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE],
        ),
    ]
    if evaluated:
        roles.append(
            (
                "local_fixture_playwright_adapter_admission_gate_decision",
                paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE],
            )
        )
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "gate_id": gate_id,
        "gate_adapter_id": _GATE_ADAPTER_ID,
        "gate_capability": _GATE_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "gate_output_artifacts_only",
        "gate_status": gate_status,
        "gate_decision": gate_decision,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        **_admission_false_fields(admitted),
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    admitted = bool(artifact_index["local_fixture_admission_granted"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "gate_adapter_id": _GATE_ADAPTER_ID,
        "gate_capability": _GATE_CAPABILITY,
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
        "gate_status": artifact_index["gate_status"],
        "gate_decision": artifact_index["gate_decision"],
        "next_allowed_action": artifact_index["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_admission_false_fields(admitted),
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
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
    paths: dict[str, Path],
    plan: dict[str, object],
    decision: dict[str, object] | None,
    evaluated: bool,
    complete: bool,
    admitted: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "admitted": admitted,
        "evaluated": evaluated,
        "gate_id": plan["gate_id"],
        "adapter_id": _GATE_ADAPTER_ID,
        "capability": _GATE_CAPABILITY,
        "output_dir": output_path.as_posix(),
        "local_fixture_playwright_adapter_admission_gate_plan_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_PLAN_FILE
        ].as_posix(),
        "local_fixture_playwright_adapter_admission_gate_manifest_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_playwright_adapter_admission_gate_summary_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_playwright_adapter_admission_gate_checklist_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "local_fixture_playwright_adapter_admission_gate_decision_path": (
            paths[
                LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_DECISION_FILE
            ].as_posix()
            if evaluated
            else None
        ),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_GATE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "receipt_dir": plan["receipt_dir"],
        "receipt_plan_path": plan["receipt_plan_path"],
        "receipt_manifest_path": plan["receipt_manifest_path"],
        "receipt_result_path": plan["receipt_result_path"],
        "receipt_artifact_index_path": plan["receipt_artifact_index_path"],
        "adapter_draft_run_dir": plan["adapter_draft_run_dir"],
        "adapter_draft_plan_path": plan["adapter_draft_plan_path"],
        "adapter_draft_manifest_path": plan["adapter_draft_manifest_path"],
        "adapter_draft_result_path": plan["adapter_draft_result_path"],
        "embedded_smoke_dir": plan["embedded_smoke_dir"],
        "embedded_smoke_plan_path": plan["embedded_smoke_plan_path"],
        "embedded_smoke_manifest_path": plan["embedded_smoke_manifest_path"],
        "embedded_smoke_result_path": plan["embedded_smoke_result_path"],
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_adapter_id": _ADAPTER_ID,
        "source_adapter_capability": _ADAPTER_CAPABILITY,
        "gate_status": plan["gate_status"],
        "gate_decision": plan["gate_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **_admission_false_fields(admitted),
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }
    if decision is not None:
        payload.update(
            {
                "receipt_id": decision["receipt_id"],
                "adapter_draft_id": decision["adapter_draft_id"],
                "admission_checks_total": decision["admission_checks_total"],
                "admission_checks_passed": decision["admission_checks_passed"],
                "admission_checks_failed": decision["admission_checks_failed"],
                "failed_check_ids": list(decision["failed_check_ids"]),
                "receipt_success": decision["receipt_success"],
                "adapter_draft_success": decision["adapter_draft_success"],
                "embedded_smoke_success": decision["embedded_smoke_success"],
                "embedded_fixture_url": decision["embedded_fixture_url"],
                "embedded_fixture_url_scheme": decision["embedded_fixture_url_scheme"],
                "embedded_non_local_request_count": decision[
                    "embedded_non_local_request_count"
                ],
                "artifact_hashes_verified": decision["artifact_hashes_verified"],
            }
        )
    return payload


def _structured_failure_result(
    receipt_dir: Path,
    output_dir: Path,
    gate_id: str,
    failure_stage: str,
    error_message: str,
    *,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
) -> LocalFixturePlaywrightAdapterAdmissionGateResult:
    safe_error = _safe_text(error_message)
    payload = {
        "complete": False,
        "admitted": False,
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "gate_id": gate_id,
        "adapter_id": _GATE_ADAPTER_ID,
        "capability": _GATE_CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "receipt_dir": receipt_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "gate_status": _FAILED_STATUS,
        "gate_decision": _FIX_DECISION,
        "next_allowed_action": _REJECTED_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": safe_error,
        "artifacts_written": False,
        "local_fixture_playwright_adapter_admission_gate_plan_path": None,
        "local_fixture_playwright_adapter_admission_gate_manifest_path": None,
        "local_fixture_playwright_adapter_admission_gate_summary_path": None,
        "local_fixture_playwright_adapter_admission_gate_checklist_path": None,
        "local_fixture_playwright_adapter_admission_gate_decision_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **_admission_false_fields(False),
        **dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS),
    }
    return LocalFixturePlaywrightAdapterAdmissionGateResult(
        receipt_dir=receipt_dir,
        output_dir=output_dir,
        gate_id=gate_id,
        plan_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        decision_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        admitted=False,
        gate_status=_FAILED_STATUS,
        gate_decision=_FIX_DECISION,
        payload=payload,
    )


def _summary_markdown(
    plan: dict[str, object],
    decision: dict[str, object] | None,
) -> str:
    lines = [
        "# Local-Fixture Playwright Adapter Admission Gate",
        "",
        "Status: " + str(plan["gate_status"]),
        "Gate id: " + str(plan["gate_id"]),
        "Candidate: microsoft/playwright",
        "Admitted scope: " + str(plan["admitted_scope"]),
        "Production scope: denied",
        "Live website scope: denied",
        "No new execution performed: true",
        "Next allowed action: " + str(plan["next_allowed_action"]),
        "",
        "Boundary: receipt evidence gate for local fixture only.",
    ]
    if decision is not None:
        lines.insert(
            6,
            "Admission checks failed: " + str(decision["admission_checks_failed"]),
        )
        lines.insert(
            7,
            "Local fixture admission granted: "
            + str(decision["local_fixture_admission_granted"]).lower(),
        )
    return "\n".join(lines)


def _checklist_markdown(
    plan: dict[str, object],
    decision: dict[str, object] | None,
) -> str:
    lines = [
        "# Local-Fixture Playwright Adapter Admission Gate Checklist",
        "",
        "- [ ] Confirm #422 receipt plan, manifest, result, and indexes are present.",
        "- [ ] Confirm receipt, adapter draft, and embedded smoke all report success.",
        "- [ ] Confirm embedded fixture scheme is file and non-local request count is zero.",
        "- [ ] Confirm no live websites, arbitrary navigation, accounts, scraping, bypass, captcha, secrets, cookies, external network, installs, package runners, candidate code, arbitrary commands, production promotion, or autonomy occurred.",
        "- [ ] Confirm indexed paths stay under receipt_dir and are not symlinks.",
        "- [ ] Confirm receipt, adapter draft, and embedded smoke hashes match existing files.",
        "- [ ] Confirm local-fixture-only admission is not production or live website admission.",
        "",
        "Gate decision: " + str(plan["gate_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    if decision is not None:
        lines.append(
            "Failed check ids: " + ", ".join(str(item) for item in decision["failed_check_ids"])
        )
    return "\n".join(lines)


def _read_json_object(path: Path, label: str) -> tuple[dict[str, object], str | None]:
    if path.is_symlink():
        return {}, label + " must not be a symlink"
    if not path.exists():
        return {}, label + " is missing"
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


def _regular_file_ok(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _directory_ok(path: Path) -> bool:
    return path.exists() and path.is_dir() and not path.is_symlink()


def _admission_false_fields(local_fixture_admission_granted: bool) -> dict[str, bool]:
    fields = dict(LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS)
    fields["local_fixture_admission_granted"] = local_fixture_admission_granted
    return fields


def _all_present_identifiers_match(
    payloads: dict[str, dict[str, object]],
    field_name: str,
    expected: str,
) -> bool:
    values = [
        payload[field_name]
        for payload in payloads.values()
        if field_name in payload and payload[field_name] is not None
    ]
    return bool(values) and all(value == expected for value in values)


def _key_identifiers_agree(payloads: dict[str, dict[str, object]]) -> bool:
    receipt_ids = {
        payload["receipt_id"]
        for key, payload in payloads.items()
        if key.startswith("receipt_")
        and "receipt_id" in payload
        and isinstance(payload["receipt_id"], str)
    }
    adapter_ids = {
        payload["adapter_draft_id"]
        for payload in payloads.values()
        if "adapter_draft_id" in payload and isinstance(payload["adapter_draft_id"], str)
    }
    candidate_ok = _all_present_identifiers_match(payloads, "candidate_id", _CANDIDATE_ID)
    repo_ok = _all_present_identifiers_match(payloads, "repo_full_name", _REPO_FULL_NAME)
    return len(receipt_ids) == 1 and len(adapter_ids) == 1 and candidate_ok and repo_ok


def _operator_runtime_metadata_present(payloads: dict[str, dict[str, object]]) -> bool:
    receipt_plan = payloads["receipt_plan"]
    receipt_result = payloads["receipt_result"]
    for payload in (receipt_plan, receipt_result):
        for field_name in (
            "node_command_path",
            "node_command_sha256",
            "runner_script_path",
            "runner_script_sha256",
        ):
            if not _non_empty_text(payload.get(field_name)):
                return False
    return True


def _true_fields(payloads: dict[str, dict[str, object]]) -> list[str]:
    fields = []
    for label, payload in payloads.items():
        for field_name in _SOURCE_FALSE_FIELDS:
            if payload.get(field_name) is True:
                fields.append(label + "." + field_name)
    return fields


def _any_true(
    payloads: dict[str, dict[str, object]],
    field_names: tuple[str, ...],
) -> bool:
    for payload in payloads.values():
        for field_name in field_names:
            if payload.get(field_name) is True:
                return True
    return False


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _scheme_from_reference(value: str) -> str:
    if ":" not in value:
        return ""
    return value.split(":", 1)[0]


def _receipt_index_path_allowed(path: Path, receipt_dir: Path) -> bool:
    relative = _relative_path(path, receipt_dir)
    if relative is None:
        return False
    parts = Path(relative).parts
    if not parts:
        return False
    if parts[0] == _ADAPTER_DRAFT_RUN_DIR:
        return True
    return relative in _ROOT_RECEIPT_ARTIFACTS


def _is_root_receipt_artifact(path: Path, receipt_dir: Path) -> bool:
    relative = _relative_path(path, receipt_dir)
    return relative in _ROOT_RECEIPT_ARTIFACTS


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
    return text[:240] if text else "local fixture admission gate failed"
