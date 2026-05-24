"""Local-fixture adapter execution-gate plan evidence.

This module reads an existing #430 local-fixture adapter dry-run invocation
plan result and writes a non-executable execution-gate plan plus a human
approval request. It records metadata only: no adapter execution, Playwright
execution, browser opening, network access, package installation, candidate
repository access, executable command materialization, approval token issuance,
runner creation, or autonomous action is performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.capabilities.local_fixture_adapter_usage_receipt import (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_REVIEW_ATTESTATION",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS",
    "LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS",
    "LocalFixtureAdapterExecutionGatePlanResult",
    "run_local_fixture_adapter_execution_gate_plan",
    "run_local_fixture_adapter_execution_gate_plan_launcher",
]


LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE = (
    "local_fixture_adapter_execution_gate_plan_plan.json"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE = (
    "local_fixture_adapter_execution_gate_plan_result.json"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE = (
    "local_fixture_adapter_execution_gate_plan_manifest.json"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE = (
    "local_fixture_adapter_execution_gate_plan_human_approval_request.md"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE = (
    "local_fixture_adapter_execution_gate_plan_summary.md"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE = (
    "local_fixture_adapter_execution_gate_plan_checklist.md"
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE = "artifact_index.json"
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_REVIEW_ATTESTATION = (
    "I_REVIEWED_DRY_RUN_INVOCATION_PLAN_FOR_EXECUTION_GATE_PLANNING_ONLY_"
    "NO_EXECUTION_NO_PRODUCTION_NO_LIVE_WEBSITES_NO_AUTONOMY"
)

LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS = (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS = (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
)
LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS = (
    "executable_command_materialized",
    "command_line_materialized",
    "argv_materialized",
    "shell_command_materialized",
    "node_command_materialized",
    "npm_command_materialized",
    "npx_command_materialized",
    "browser_command_materialized",
    "playwright_command_materialized",
)

_GATE_PLAN_TYPE = "local_fixture_adapter_execution_gate_plan_v1"
_MANIFEST_TYPE = "local_fixture_adapter_execution_gate_plan_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_adapter_execution_gate_plan_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_adapter_execution_gate_plan_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_local_fixture_execution_gate_plan_record"
_EXECUTION_CAPABILITY = "local_fixture_adapter_execution_gate_plan_only"
_PLAN_ADAPTER_ID = "local_fixture_adapter_execution_gate_plan"
_PLAN_CAPABILITY = "launch_local_fixture_adapter_execution_gate_plan"
_DRY_RUN_PLAN_TYPE = "local_fixture_adapter_dry_run_invocation_plan_v1"
_DRY_RUN_COMPLETED_STATUS = "local_fixture_adapter_dry_run_invocation_plan_completed"
_DRY_RUN_COMPLETED_DECISION = "record_dry_run_invocation_plan_only"
_USAGE_RECEIPT_TYPE = "local_fixture_adapter_usage_receipt_v1"
_PROMOTION_TYPE = "admission_gated_local_adapter_registry_promotion_v1"
_SOURCE_DECISION_TYPE = "local_fixture_playwright_adapter_admission_gate_decision_v1"
_PROMOTED_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_COMPLETED_STATUS = "local_fixture_adapter_execution_gate_plan_completed"
_REJECTED_STATUS = "local_fixture_adapter_execution_gate_plan_rejected"
_COMPLETED_DECISION = "record_execution_gate_plan_only"
_REJECTED_DECISION = "reject_execution_gate_plan"
_NEXT_ALLOWED_ACTION = (
    "human_review_execution_gate_plan_before_any_runner_implementation"
)
_FIX_DRY_RUN_PLAN_NEXT_ACTION = (
    "fix_dry_run_invocation_plan_and_retry_execution_gate_plan"
)
_DRY_RUN_MANIFEST_FILE = "local_fixture_adapter_dry_run_invocation_plan_manifest.json"
_DRY_RUN_ARTIFACT_INDEX_FILE = "artifact_index.json"
_DRY_RUN_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_ALLOWED_REFERENCE_SCHEMES = frozenset(("file", "relative_path"))
_OPTIONAL_APPROVAL_MATERIAL_FALSE_FIELDS = (
    "approval_token_issued",
    "auto_approval_performed",
)
_OPTIONAL_RUNNABLE_JOB_FALSE_FIELDS = ("runnable_job_created",)
_CANDIDATE_PATH_MARKERS = (
    "candidate-repo",
    "candidate-repository",
    "candidate-code",
    "candidate_repo",
    "candidate_repository",
    "candidate_code",
    "microsoft-playwright",
    "playwright-repo",
)
_OUTPUT_FILES = (
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE,
)


@dataclass(frozen=True)
class LocalFixtureAdapterExecutionGatePlanResult:
    dry_run_plan_path: Path
    output_dir: Path
    execution_gate_plan_id: str
    plan_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    human_approval_request_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    execution_gate_plan_granted: bool
    execution_gate_plan_status: str
    execution_gate_plan_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_adapter_execution_gate_plan_launcher(
    dry_run_plan: Path,
    output_dir: Path,
    execution_gate_plan_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureAdapterExecutionGatePlanResult:
    """Launcher-oriented wrapper for the metadata-only execution-gate plan."""

    return run_local_fixture_adapter_execution_gate_plan(
        dry_run_plan,
        output_dir,
        execution_gate_plan_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_adapter_execution_gate_plan(
    dry_run_plan: Path,
    output_dir: Path,
    execution_gate_plan_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureAdapterExecutionGatePlanResult:
    """Validate a #430 dry-run plan and write a non-executable gate plan."""

    source_path = Path(dry_run_plan)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(
        output_path,
        execution_gate_plan_id,
        paths,
    )
    if preflight_reasons:
        return _unwritten_result(
            source_path=source_path,
            output_path=output_path,
            execution_gate_plan_id=execution_gate_plan_id,
            rejection_reasons=preflight_reasons,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )

    dry_run_payload, dry_run_read_reasons = _read_dry_run_plan_result(source_path)
    dry_run_validation_reasons: list[str] = list(dry_run_read_reasons)
    if not dry_run_validation_reasons:
        dry_run_validation_reasons.extend(
            _dry_run_plan_rejection_reasons(source_path, dry_run_payload)
        )
    fixture_metadata, fixture_reasons = _local_fixture_revalidation_metadata(
        source_path,
        dry_run_payload,
    )
    review_reasons = _review_attestation_rejection_reasons(review_attestation)
    rejection_reasons = _dedupe_strings(
        dry_run_validation_reasons + fixture_reasons + review_reasons
    )

    dry_run_plan_sha256 = _source_sha256(source_path)
    dry_run_plan_validated = (
        not dry_run_validation_reasons and not fixture_reasons
    )
    execution_gate_plan_granted = not rejection_reasons
    execution_gate_plan_status = (
        _COMPLETED_STATUS if execution_gate_plan_granted else _REJECTED_STATUS
    )
    execution_gate_plan_decision = (
        _COMPLETED_DECISION
        if execution_gate_plan_granted
        else _REJECTED_DECISION
    )
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION
        if execution_gate_plan_granted
        else _FIX_DRY_RUN_PLAN_NEXT_ACTION
    )

    plan = _plan_payload(
        source_path=source_path,
        dry_run_plan_sha256=dry_run_plan_sha256,
        dry_run_payload=dry_run_payload,
        output_path=output_path,
        paths=paths,
        execution_gate_plan_id=execution_gate_plan_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        fixture_metadata=fixture_metadata,
    )
    result = _result_payload(
        source_path=source_path,
        dry_run_plan_sha256=dry_run_plan_sha256,
        dry_run_payload=dry_run_payload,
        output_path=output_path,
        execution_gate_plan_id=execution_gate_plan_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        fixture_metadata=fixture_metadata,
        dry_run_plan_validated=dry_run_plan_validated,
        execution_gate_plan_granted=execution_gate_plan_granted,
        execution_gate_plan_status=execution_gate_plan_status,
        execution_gate_plan_decision=execution_gate_plan_decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE],
        plan,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE],
        result,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE],
        _human_approval_request_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        execution_gate_plan_id=execution_gate_plan_id,
        execution_gate_plan_granted=execution_gate_plan_granted,
        execution_gate_plan_status=execution_gate_plan_status,
        execution_gate_plan_decision=execution_gate_plan_decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureAdapterExecutionGatePlanResult(
        dry_run_plan_path=source_path,
        output_dir=output_path,
        execution_gate_plan_id=execution_gate_plan_id,
        plan_path=paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE],
        result_path=paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE],
        manifest_path=paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE],
        human_approval_request_path=paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE
        ],
        summary_path=paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE],
        checklist_path=paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE],
        artifact_index_path=paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=execution_gate_plan_granted,
        execution_gate_plan_granted=execution_gate_plan_granted,
        execution_gate_plan_status=execution_gate_plan_status,
        execution_gate_plan_decision=execution_gate_plan_decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
    output_path: Path,
    execution_gate_plan_id: str,
    paths: dict[str, Path],
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink() or not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    if not _non_empty_text(execution_gate_plan_id):
        reasons.append("execution_gate_plan_id_missing")
    for candidate in paths.values():
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return _dedupe_strings(reasons)


def _read_dry_run_plan_result(
    source_path: Path,
) -> tuple[dict[str, object], list[str]]:
    reasons: list[str] = []
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    if not source_path.exists():
        reasons.append("dry_run_plan_path_missing")
        return {}, _dedupe_strings(reasons)
    if source_path.is_symlink():
        reasons.append("dry_run_plan_path_is_symlink")
        return {}, _dedupe_strings(reasons)
    if not source_path.is_file():
        reasons.append("dry_run_plan_path_missing")
        return {}, _dedupe_strings(reasons)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("dry_run_plan_not_json_object")
        return {}, _dedupe_strings(reasons)
    if not isinstance(payload, dict):
        reasons.append("dry_run_plan_not_json_object")
        return {}, _dedupe_strings(reasons)
    reasons.extend(_discoverable_dry_run_hash_rejection_reasons(source_path))
    return payload, _dedupe_strings(reasons)


def _dry_run_plan_rejection_reasons(
    source_path: Path,
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(_dry_run_plan_output_dir_rejection_reasons(source_path, payload))
    if payload.get("plan_type") != _DRY_RUN_PLAN_TYPE:
        reasons.append("dry_run_plan_type_mismatch")
    if payload.get("invocation_plan_status") != _DRY_RUN_COMPLETED_STATUS:
        reasons.append("dry_run_plan_status_not_completed")
    if payload.get("invocation_plan_decision") != _DRY_RUN_COMPLETED_DECISION:
        reasons.append("dry_run_plan_decision_mismatch")
    if payload.get("invocation_plan_granted") is not True:
        reasons.append("invocation_plan_not_granted")
    if payload.get("usage_receipt_validated") is not True:
        reasons.append("dry_run_plan_not_validated")
    if payload.get("usage_receipt_granted") is not True:
        reasons.append("usage_receipt_not_granted")
    if payload.get("registry_promotion_granted") is not True:
        reasons.append("registry_promotion_not_granted")
    if payload.get("production_promotion_granted") is not False:
        reasons.append("production_promotion_claimed")
    if payload.get("source_gate_passed") is not True:
        reasons.append("source_gate_not_passed")
    if payload.get("source_gate_decision_type") != _SOURCE_DECISION_TYPE:
        reasons.append("source_gate_decision_type_mismatch")
    if not _non_empty_text(payload.get("source_gate_decision_sha256")):
        reasons.append("source_gate_decision_sha_missing")
    if payload.get("promotion_type") != _PROMOTION_TYPE:
        reasons.append("promotion_type_mismatch")
    if not _non_empty_text(payload.get("promotion_result_sha256")):
        reasons.append("promotion_result_sha_missing")
    if payload.get("usage_receipt_type") != _USAGE_RECEIPT_TYPE:
        reasons.append("usage_receipt_type_mismatch")
    if not _non_empty_text(payload.get("usage_receipt_sha256")):
        reasons.append("usage_receipt_sha_missing")
    if payload.get("adapter_id") != _PROMOTED_ADAPTER_ID:
        reasons.append("source_adapter_id_mismatch")
    if payload.get("candidate_id") != _CANDIDATE_ID:
        reasons.append("source_candidate_id_mismatch")
    if payload.get("repo_full_name") != _REPO_FULL_NAME:
        reasons.append("source_repo_full_name_mismatch")
    if payload.get("aggregation_bound") is not True:
        reasons.append("aggregation_not_bound")
    if payload.get("regression_bound") is not True:
        reasons.append("regression_not_bound")
    if payload.get("local_fixture_only") is not True:
        reasons.append("local_fixture_only_not_true")
    if payload.get("one_usage_receipt_bound") is not True:
        reasons.append("one_usage_receipt_bound_not_true")
    if payload.get("dry_run_plan_only") is not True:
        reasons.append("dry_run_plan_only_not_true")
    if payload.get("future_invocation_requires_separate_execution_gate") is not True:
        reasons.append("future_execution_gate_not_required")
    if payload.get("future_execution_requires_human_approval") is not True:
        reasons.append("future_human_approval_not_required")
    if payload.get("human_review_required") is not True:
        reasons.append("human_review_not_required")
    if payload.get("required_human_approval") is not True:
        reasons.append("human_approval_not_required")
    if payload.get("non_production") is not True:
        reasons.append("non_production_not_true")
    if payload.get("production_adapter") is not False:
        reasons.append("production_adapter_claimed")
    if any(
        payload.get(field_name) is not False
        for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
    ):
        reasons.append("forbidden_admission_claimed")
    if any(
        payload.get(field_name) is not False
        for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
    ):
        reasons.append("performed_forbidden_action")
    if any(
        payload.get(field_name) is not False
        for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
    ):
        reasons.append("executable_material_claimed")
    if any(
        field_name in payload and payload.get(field_name) is not False
        for field_name in _OPTIONAL_APPROVAL_MATERIAL_FALSE_FIELDS
    ):
        reasons.append("approval_material_claimed")
    if any(
        field_name in payload and payload.get(field_name) is not False
        for field_name in _OPTIONAL_RUNNABLE_JOB_FALSE_FIELDS
    ):
        reasons.append("runnable_job_claimed")
    if not _non_empty_text(payload.get("local_fixture_reference")):
        reasons.append("local_fixture_reference_missing")
    if payload.get("local_fixture_reference_scheme") not in _ALLOWED_REFERENCE_SCHEMES:
        reasons.append("local_fixture_reference_forbidden_scheme")
    if not _non_empty_text(payload.get("local_fixture_path")):
        reasons.append("local_fixture_path_missing")
    if not _non_empty_text(payload.get("local_fixture_sha256")):
        reasons.append("local_fixture_sha_missing")
    if payload.get("local_fixture_revalidated") is not True:
        reasons.append("local_fixture_sha_mismatch")
    if payload.get("local_fixture_exists") is not True:
        reasons.append("local_fixture_path_missing")
    if payload.get("local_fixture_regular_file") is not True:
        reasons.append("local_fixture_path_not_regular_file")
    if payload.get("local_fixture_symlink_detected") is not False:
        reasons.append("local_fixture_path_is_symlink")
    if payload.get("local_fixture_under_allowed_root") is not True:
        reasons.append("local_fixture_path_outside_allowed_root")
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    return _dedupe_strings(reasons)


def _dry_run_plan_output_dir_rejection_reasons(
    source_path: Path,
    payload: dict[str, object],
) -> list[str]:
    if "output_dir" not in payload:
        return []
    output_dir = payload.get("output_dir")
    if not _non_empty_text(output_dir):
        return ["dry_run_plan_output_dir_mismatch"]
    if Path(str(output_dir)).resolve(strict=False) != source_path.parent.resolve(
        strict=False
    ):
        return ["dry_run_plan_output_dir_mismatch"]
    return []


def _local_fixture_revalidation_metadata(
    source_path: Path,
    payload: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    metadata = _empty_fixture_metadata(payload)
    reasons: list[str] = []
    path_value = payload.get("local_fixture_path")
    expected_sha = payload.get("local_fixture_sha256")
    allowed_root, allowed_root_reasons = _allowed_fixture_root(source_path, payload)
    reasons.extend(allowed_root_reasons)
    metadata["local_fixture_allowed_root"] = allowed_root.as_posix()
    if not _non_empty_text(path_value):
        reasons.append("local_fixture_path_missing")
        metadata["local_fixture_revalidated"] = False
        return metadata, _dedupe_strings(reasons)

    fixture_path = _path_from_value(str(path_value), allowed_root)
    metadata["local_fixture_path"] = fixture_path.as_posix()
    if not _path_is_inside(fixture_path, allowed_root):
        reasons.append("local_fixture_path_outside_allowed_root")
    if fixture_path.is_symlink():
        metadata["local_fixture_symlink_detected"] = True
        reasons.append("local_fixture_path_is_symlink")
    if _path_has_symlink_component(fixture_path, allowed_root):
        metadata["local_fixture_symlink_detected"] = True
        reasons.append("local_fixture_path_has_symlink_component")
    if not fixture_path.exists():
        reasons.append("local_fixture_path_missing")
    elif not fixture_path.is_file():
        reasons.append("local_fixture_path_not_regular_file")

    exists = fixture_path.exists()
    regular = exists and fixture_path.is_file() and not fixture_path.is_symlink()
    under_root = _path_is_inside(fixture_path, allowed_root)
    symlink_detected = bool(metadata["local_fixture_symlink_detected"])
    metadata["local_fixture_exists"] = exists
    metadata["local_fixture_regular_file"] = regular
    metadata["local_fixture_under_allowed_root"] = under_root
    metadata["local_fixture_symlink_detected"] = symlink_detected
    if not _non_empty_text(expected_sha):
        reasons.append("local_fixture_sha_missing")
    elif regular and under_root and not symlink_detected:
        actual_sha = sha256_file(fixture_path)
        metadata["local_fixture_sha256"] = actual_sha
        if actual_sha != expected_sha:
            reasons.append("local_fixture_sha_mismatch")
    metadata["local_fixture_revalidated"] = not reasons
    return metadata, _dedupe_strings(reasons)


def _empty_fixture_metadata(payload: dict[str, object]) -> dict[str, object]:
    return {
        "local_fixture_reference": payload.get("local_fixture_reference"),
        "local_fixture_reference_scheme": payload.get(
            "local_fixture_reference_scheme"
        ),
        "local_fixture_path": payload.get("local_fixture_path"),
        "local_fixture_allowed_root": None,
        "local_fixture_sha256": None,
        "local_fixture_revalidated": False,
        "local_fixture_exists": False,
        "local_fixture_regular_file": False,
        "local_fixture_symlink_detected": False,
        "local_fixture_under_allowed_root": False,
    }


def _allowed_fixture_root(
    source_path: Path,
    payload: dict[str, object],
) -> tuple[Path, list[str]]:
    canonical_root = source_path.parent
    reasons: list[str] = []
    if "usage_receipt_path" in payload:
        usage_receipt_path = payload.get("usage_receipt_path")
        if not _non_empty_text(usage_receipt_path) or not _path_is_inside(
            _path_from_value(str(usage_receipt_path), canonical_root),
            canonical_root,
        ):
            reasons.append("dry_run_plan_usage_receipt_path_mismatch")
    if "local_fixture_allowed_root" in payload:
        allowed_root_value = payload.get("local_fixture_allowed_root")
        if not _non_empty_text(allowed_root_value) or Path(
            str(allowed_root_value)
        ).resolve(strict=False) != canonical_root.resolve(strict=False):
            reasons.append("dry_run_plan_local_fixture_allowed_root_mismatch")
    return canonical_root, reasons


def _review_attestation_rejection_reasons(value: str | None) -> list[str]:
    if not _non_empty_text(value):
        return ["review_attestation_missing"]
    if value != LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_REVIEW_ATTESTATION:
        return ["review_attestation_mismatch"]
    return []


def _discoverable_dry_run_hash_rejection_reasons(source_path: Path) -> list[str]:
    reasons: list[str] = []
    root = source_path.parent
    manifest_path = root / _DRY_RUN_MANIFEST_FILE
    if manifest_path.exists() or manifest_path.is_symlink():
        manifest, ok = _read_json_object_if_regular(manifest_path)
        if not ok or not _dry_run_manifest_hashes_verified(
            manifest,
            source_path,
            root,
        ):
            reasons.append("dry_run_manifest_hash_mismatch")
    artifact_index_path = root / _DRY_RUN_ARTIFACT_INDEX_FILE
    if artifact_index_path.exists() or artifact_index_path.is_symlink():
        artifact_index, ok = _read_json_object_if_regular(artifact_index_path)
        if not ok or not _dry_run_artifact_index_hashes_verified(
            artifact_index,
            root,
        ):
            reasons.append("dry_run_artifact_index_hash_mismatch")
    index_manifest_path = root / _DRY_RUN_ARTIFACT_INDEX_MANIFEST_FILE
    if index_manifest_path.exists() or index_manifest_path.is_symlink():
        index_manifest, ok = _read_json_object_if_regular(index_manifest_path)
        if not ok or not _dry_run_artifact_index_manifest_verified(
            index_manifest,
            artifact_index_path,
            root,
        ):
            reasons.append("dry_run_artifact_index_hash_mismatch")
    return _dedupe_strings(reasons)


def _dry_run_manifest_hashes_verified(
    manifest: dict[str, object],
    source_path: Path,
    root: Path,
) -> bool:
    result_path_value = manifest.get("result_path")
    result_sha256 = manifest.get("result_sha256")
    if not isinstance(result_path_value, str) or not isinstance(result_sha256, str):
        return False
    result_path = _path_from_value(result_path_value, root)
    if result_path.resolve(strict=False) != source_path.resolve(strict=False):
        return False
    if not _regular_file(result_path) or sha256_file(result_path) != result_sha256:
        return False
    for key, value in manifest.items():
        if not key.endswith("_path") or not isinstance(value, str):
            continue
        sha_key = key[:-5] + "_sha256"
        recorded_hash = manifest.get(sha_key)
        if not isinstance(recorded_hash, str):
            continue
        path = _path_from_value(value, root)
        if not _regular_file(path) or sha256_file(path) != recorded_hash:
            return False
    return True


def _dry_run_artifact_index_hashes_verified(
    artifact_index: dict[str, object],
    root: Path,
) -> bool:
    entries = artifact_index.get("entries")
    if not isinstance(entries, list) or not entries:
        return False
    if artifact_index.get("candidate_repo_files_indexed") is True:
        return False
    if artifact_index.get("external_candidate_artifacts_indexed") is True:
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        path_value = entry.get("path")
        recorded_hash = entry.get("sha256")
        if entry.get("candidate_repo_file") is True:
            return False
        if entry.get("external_candidate_artifact") is True:
            return False
        if not isinstance(path_value, str) or not isinstance(recorded_hash, str):
            return False
        path = _path_from_value(path_value, root)
        if not _path_is_inside(path, root):
            return False
        if not _regular_file(path) or sha256_file(path) != recorded_hash:
            return False
    return True


def _dry_run_artifact_index_manifest_verified(
    index_manifest: dict[str, object],
    artifact_index_path: Path,
    root: Path,
) -> bool:
    path_value = index_manifest.get("artifact_index_path")
    recorded_hash = index_manifest.get("artifact_index_sha256")
    if not isinstance(path_value, str) or not isinstance(recorded_hash, str):
        return False
    path = _path_from_value(path_value, root)
    if path.resolve(strict=False) != artifact_index_path.resolve(strict=False):
        return False
    if not _path_is_inside(path, root):
        return False
    if not _regular_file(path):
        return False
    return sha256_file(path) == recorded_hash


def _plan_payload(
    *,
    source_path: Path,
    dry_run_plan_sha256: str | None,
    dry_run_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    execution_gate_plan_id: str,
    review_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    fixture_metadata: dict[str, object],
) -> dict[str, object]:
    return {
        "gate_plan_type": _GATE_PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_gate_plan_adapter_id": _PLAN_ADAPTER_ID,
        "execution_gate_plan_capability": _PLAN_CAPABILITY,
        "execution_gate_plan_id": execution_gate_plan_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes_sha256": (
            None if operator_notes is None else _sha256_text(operator_notes)
        ),
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else _sha256_text(review_attestation)
        ),
        "dry_run_plan_path": source_path.as_posix(),
        "dry_run_plan_sha256": dry_run_plan_sha256,
        "dry_run_plan_type": dry_run_payload.get("plan_type"),
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "usage_receipt_type": dry_run_payload.get("usage_receipt_type"),
        "usage_receipt_sha256": dry_run_payload.get("usage_receipt_sha256"),
        "promotion_type": dry_run_payload.get("promotion_type"),
        "promotion_result_sha256": dry_run_payload.get("promotion_result_sha256"),
        "source_gate_decision_type": dry_run_payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": dry_run_payload.get(
            "source_gate_decision_sha256"
        ),
        "source_gate_passed": dry_run_payload.get("source_gate_passed") is True,
        "registry_promotion_granted": (
            dry_run_payload.get("registry_promotion_granted") is True
        ),
        "aggregation_bound": True,
        "regression_bound": True,
        "local_fixture_only": True,
        "one_usage_receipt_bound": True,
        "dry_run_plan_bound": True,
        "execution_gate_plan_only": True,
        "human_approval_request_only": True,
        **fixture_metadata,
        "human_review_required": True,
        "required_human_approval": True,
        "non_production": True,
        "production_adapter": False,
        "output_dir": output_path.as_posix(),
        "execution_gate_plan_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE
        ].as_posix(),
        "execution_gate_plan_result_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE
        ].as_posix(),
        "execution_gate_plan_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE
        ].as_posix(),
        "execution_gate_plan_human_approval_request_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE
        ].as_posix(),
        "execution_gate_plan_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE
        ].as_posix(),
        "execution_gate_plan_checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "next_allowed_action": "validate_dry_run_plan_before_gate_plan_record",
        **_execution_gate_boundary_fields(),
    }


def _result_payload(
    *,
    source_path: Path,
    dry_run_plan_sha256: str | None,
    dry_run_payload: dict[str, object],
    output_path: Path,
    execution_gate_plan_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    fixture_metadata: dict[str, object],
    dry_run_plan_validated: bool,
    execution_gate_plan_granted: bool,
    execution_gate_plan_status: str,
    execution_gate_plan_decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    return {
        "gate_plan_type": _GATE_PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_gate_plan_adapter_id": _PLAN_ADAPTER_ID,
        "execution_gate_plan_capability": _PLAN_CAPABILITY,
        "execution_gate_plan_id": execution_gate_plan_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes_sha256": (
            None if operator_notes is None else _sha256_text(operator_notes)
        ),
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "dry_run_plan_path": source_path.as_posix(),
        "dry_run_plan_sha256": dry_run_plan_sha256,
        "dry_run_plan_type": dry_run_payload.get("plan_type"),
        "dry_run_plan_validated": dry_run_plan_validated,
        "invocation_plan_granted": dry_run_payload.get("invocation_plan_granted")
        is True,
        "usage_receipt_type": dry_run_payload.get("usage_receipt_type"),
        "usage_receipt_sha256": dry_run_payload.get("usage_receipt_sha256"),
        "promotion_type": dry_run_payload.get("promotion_type"),
        "promotion_result_sha256": dry_run_payload.get("promotion_result_sha256"),
        "source_gate_decision_type": dry_run_payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": dry_run_payload.get(
            "source_gate_decision_sha256"
        ),
        "source_gate_passed": dry_run_payload.get("source_gate_passed") is True,
        "registry_promotion_granted": (
            dry_run_payload.get("registry_promotion_granted") is True
        ),
        "aggregation_bound": dry_run_payload.get("aggregation_bound") is True,
        "regression_bound": dry_run_payload.get("regression_bound") is True,
        "local_fixture_only": True,
        "one_usage_receipt_bound": True,
        "dry_run_plan_bound": True,
        "execution_gate_plan_only": True,
        "human_approval_request_only": True,
        "execution_gate_plan_granted": execution_gate_plan_granted,
        **fixture_metadata,
        "human_review_required": True,
        "required_human_approval": True,
        "non_production": True,
        "production_adapter": False,
        "execution_gate_plan_status": execution_gate_plan_status,
        "execution_gate_plan_decision": execution_gate_plan_decision,
        "complete": execution_gate_plan_granted,
        "rejected": not execution_gate_plan_granted,
        "rejection_reasons": list(rejection_reasons),
        "next_allowed_action": next_allowed_action,
        "output_dir": output_path.as_posix(),
        "no_live_website": True,
        "no_general_browser_automation": True,
        "no_autonomy": True,
        **_execution_gate_boundary_fields(),
    }


def _execution_gate_boundary_fields() -> dict[str, object]:
    fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
    }
    fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
        }
    )
    fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
        }
    )
    fields["production_promotion_granted"] = False
    fields["approval_token_issued"] = False
    fields["auto_approval_performed"] = False
    fields["runnable_job_created"] = False
    fields["execution_runner_created"] = False
    fields["future_execution_requires_separate_human_approval_artifact"] = True
    fields["future_execution_requires_separate_execution_runner_pr"] = True
    return fields


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "gate_plan_type": _GATE_PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_gate_plan_adapter_id": _PLAN_ADAPTER_ID,
        "execution_gate_plan_capability": _PLAN_CAPABILITY,
        "execution_gate_plan_id": result["execution_gate_plan_id"],
        "job_dir": output_path.as_posix(),
        "plan_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE]
        ),
        "human_approval_request_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE
        ].as_posix(),
        "human_approval_request_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE]
        ),
        "dry_run_plan_path": result["dry_run_plan_path"],
        "dry_run_plan_sha256": result["dry_run_plan_sha256"],
        "local_fixture_path": result["local_fixture_path"],
        "local_fixture_sha256": result["local_fixture_sha256"],
        "execution_gate_plan_granted": result["execution_gate_plan_granted"],
        "production_promotion_granted": False,
        "next_allowed_action": result["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_execution_gate_boundary_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    execution_gate_plan_id: str,
    execution_gate_plan_granted: bool,
    execution_gate_plan_status: str,
    execution_gate_plan_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_adapter_execution_gate_plan_plan",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE],
        ),
        (
            "local_fixture_adapter_execution_gate_plan_result",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE],
        ),
        (
            "local_fixture_adapter_execution_gate_plan_manifest",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE],
        ),
        (
            "local_fixture_adapter_execution_gate_plan_human_approval_request",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE],
        ),
        (
            "local_fixture_adapter_execution_gate_plan_summary",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE],
        ),
        (
            "local_fixture_adapter_execution_gate_plan_checklist",
            paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE],
        ),
    )
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "gate_plan_type": _GATE_PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_gate_plan_adapter_id": _PLAN_ADAPTER_ID,
        "execution_gate_plan_capability": _PLAN_CAPABILITY,
        "execution_gate_plan_id": execution_gate_plan_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "execution_gate_plan_output_artifacts_only",
        "execution_gate_plan_status": execution_gate_plan_status,
        "execution_gate_plan_decision": execution_gate_plan_decision,
        "execution_gate_plan_granted": execution_gate_plan_granted,
        "execution_gate_plan_only": True,
        "human_approval_request_only": True,
        "production_promotion_granted": False,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        **_execution_gate_boundary_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "gate_plan_type": _GATE_PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "execution_gate_plan_adapter_id": _PLAN_ADAPTER_ID,
        "execution_gate_plan_capability": _PLAN_CAPABILITY,
        "execution_gate_plan_id": artifact_index["execution_gate_plan_id"],
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
        "execution_gate_plan_status": artifact_index["execution_gate_plan_status"],
        "execution_gate_plan_decision": artifact_index["execution_gate_plan_decision"],
        "execution_gate_plan_granted": artifact_index[
            "execution_gate_plan_granted"
        ],
        "execution_gate_plan_only": True,
        "human_approval_request_only": True,
        "production_promotion_granted": False,
        "next_allowed_action": artifact_index["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_execution_gate_boundary_fields(),
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
    result: dict[str, object],
) -> dict[str, object]:
    payload = {
        "workflow": "local_fixture_adapter_execution_gate_plan_workflow",
        "complete": bool(result["complete"]),
        "execution_gate_plan_granted": bool(result["execution_gate_plan_granted"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_plan_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_PLAN_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_result_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_RESULT_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_human_approval_request_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_HUMAN_APPROVAL_REQUEST_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_adapter_execution_gate_plan_checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "required_human_approval": True,
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    source_path: Path,
    output_path: Path,
    execution_gate_plan_id: str,
    rejection_reasons: list[str],
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
) -> LocalFixtureAdapterExecutionGatePlanResult:
    payload = {
        "workflow": "local_fixture_adapter_execution_gate_plan_workflow",
        "complete": False,
        "execution_gate_plan_granted": False,
        "gate_plan_type": _GATE_PLAN_TYPE,
        "execution_gate_plan_id": execution_gate_plan_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes_sha256": (
            None if operator_notes is None else _sha256_text(operator_notes)
        ),
        "dry_run_plan_path": source_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "execution_gate_plan_status": _REJECTED_STATUS,
        "execution_gate_plan_decision": _REJECTED_DECISION,
        "rejection_reasons": list(rejection_reasons),
        "required_human_approval": True,
        **_execution_gate_boundary_fields(),
    }
    return LocalFixtureAdapterExecutionGatePlanResult(
        dry_run_plan_path=source_path,
        output_dir=output_path,
        execution_gate_plan_id=execution_gate_plan_id,
        plan_path=None,
        result_path=None,
        manifest_path=None,
        human_approval_request_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        execution_gate_plan_granted=False,
        execution_gate_plan_status=_REJECTED_STATUS,
        execution_gate_plan_decision=_REJECTED_DECISION,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _human_approval_request_markdown(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Local-Fixture Adapter Execution Gate Plan Human Approval Request",
            "",
            "This is not approval.",
            "This is a request for future human approval.",
            "No approval token has been issued.",
            "No execution runner exists.",
            "No adapter execution has occurred.",
            "No Playwright execution has occurred.",
            "No browser has been opened.",
            "No live website is allowed.",
            "No general browser automation is allowed.",
            "No production promotion is allowed.",
            "A future PR is required for any execution runner.",
            "A separate human approval artifact is required before any future execution.",
            "The current artifact is only a gate plan.",
            "",
            f"Execution gate plan ID: {result['execution_gate_plan_id']}",
            f"Dry-run plan sha256: {result['dry_run_plan_sha256']}",
            f"Usage receipt sha256: {result['usage_receipt_sha256']}",
            f"Promotion result sha256: {result['promotion_result_sha256']}",
            f"Source gate decision sha256: {result['source_gate_decision_sha256']}",
            f"Local fixture sha256: {result['local_fixture_sha256']}",
            f"Local fixture path: {result['local_fixture_path']}",
            "",
            "Rejected capabilities:",
            "- Production admission",
            "- Live website admission",
            "- General browser automation admission",
            "- Arbitrary navigation admission",
            "- Account, login, and registration workflows",
            "- Scraping, bypass, and captcha workflows",
            "- Credential, cookie, and secret access",
            "- External network access",
            "- Package installation and browser download",
            "- Candidate repository access and code execution",
            "- Adapter execution",
            "- Playwright execution",
            "- Browser opening",
            "- Executable material creation",
            "- Approval material issuance",
            "- Runnable job creation",
            "- Autonomous execution",
            "",
            f"Next allowed action: {result['next_allowed_action']}",
            "",
        ]
    )


def _summary_markdown(result: dict[str, object]) -> str:
    reasons = result.get("rejection_reasons")
    if isinstance(reasons, list) and reasons:
        reason_lines = "\n".join("- " + str(reason) for reason in reasons)
    else:
        reason_lines = "- none"
    return "\n".join(
        [
            "# Local-Fixture Adapter Execution Gate Plan",
            "",
            f"Execution gate plan ID: {result['execution_gate_plan_id']}",
            f"Status: {result['execution_gate_plan_status']}",
            f"Decision: {result['execution_gate_plan_decision']}",
            f"Dry-run plan: {result['dry_run_plan_path']}",
            f"Local fixture: {result['local_fixture_path']}",
            f"Execution gate plan only: {str(result['execution_gate_plan_only']).lower()}",
            f"Human approval request only: {str(result['human_approval_request_only']).lower()}",
            f"Execution gate plan granted: {str(result['execution_gate_plan_granted']).lower()}",
            f"Adapter execution performed: {str(result['adapter_execution_performed']).lower()}",
            f"Playwright execution performed: {str(result['playwright_execution_performed']).lower()}",
            f"Browser open performed: {str(result['browser_open_performed']).lower()}",
            f"Executable command materialized: {str(result['executable_command_materialized']).lower()}",
            f"Runnable job created: {str(result['runnable_job_created']).lower()}",
            "",
            "Allowed state: execution_gate_plan_only, dry_run_plan_bound, local_fixture_only, one_usage_receipt_bound, human_approval_request_only, human_review_required, aggregation_bound, regression_bound, non_production.",
            "",
            "Rejected reasons:",
            reason_lines,
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["execution_gate_plan_granted"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Adapter Execution Gate Plan Checklist",
            "",
            f"- {checked} #430 dry-run invocation plan result validated.",
            f"- {checked} Local fixture path and hash revalidated.",
            f"- {checked} Non-executable execution-gate plan recorded.",
            f"- {checked} Human approval request recorded.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network probing was not performed.",
            "- [x] Fixture contents were not executed.",
            "- [x] Executable material was not written.",
            "- [x] Command line and argv material were not written.",
            "- [x] Node, package-manager, browser, and Playwright launch material was not written.",
            "- [x] Approval material was not issued.",
            "- [x] Runnable job and execution runner were not created.",
            "- [x] Production remains denied.",
            "- [x] Live website automation remains denied.",
            "- [x] General browser automation remains denied.",
            "- [x] Account, scraping, bypass, captcha, credential, and cookie flows remain denied.",
            "- [x] Package installation and browser download remain denied.",
            "- [x] Candidate repository access and code execution remain denied.",
            "- [x] Autonomy remains denied.",
            "",
        ]
    )


def _read_json_object_if_regular(path: Path) -> tuple[dict[str, object], bool]:
    if not _regular_file(path):
        return {}, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, False
    if not isinstance(payload, dict):
        return {}, False
    return payload, True


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_json_atomically(path, payload)


def _write_markdown_exclusive(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("output_collision")
    write_markdown_atomically(path, content)


def _source_sha256(path: Path | None) -> str | None:
    if path is not None and _regular_file(path):
        return sha256_file(path)
    return None


def _regular_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _path_from_value(value: str, root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def _path_is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except ValueError:
        return False
    return True


def _path_has_symlink_component(path: Path, root: Path) -> bool:
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError:
        return False
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _candidate_repo_marker_in_path(path: Path) -> bool:
    normalized_parts = tuple(part.lower() for part in path.parts)
    return any(
        marker in part
        for part in normalized_parts
        for marker in _CANDIDATE_PATH_MARKERS
    )


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped
