"""Playwright local admission receipt aggregation.

This module aggregates existing #424 local fixture scenario suite artifacts. It
only reads and validates artifact files, then emits deterministic aggregation
evidence for human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os

from kernel.capabilities.local_only_playwright_fixture_scenario_suite import (
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE,
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE,
)
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS",
    "PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS",
    "PlaywrightLocalAdmissionReceiptAggregationResult",
    "build_playwright_local_admission_receipt_aggregation_plan",
    "run_playwright_local_admission_receipt_aggregation",
    "run_playwright_local_admission_receipt_aggregation_launcher",
]


PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE = (
    "playwright_local_admission_receipt_aggregation_plan.json"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE = (
    "playwright_local_admission_receipt_aggregation_result.json"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE = (
    "playwright_local_admission_receipt_aggregation_manifest.json"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE = (
    "playwright_local_admission_receipt_aggregation_summary.md"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE = (
    "playwright_local_admission_receipt_aggregation_checklist.md"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION = (
    "I_REVIEWED_LOCAL_ONLY_PLAYWRIGHT_SUITE_RUNS_NO_LIVE_WEBSITES_"
    "NO_ACCOUNTS_NO_SCRAPING_NO_BYPASS"
)

PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS = dict(
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_DISABLED_FIELDS
)
PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS = dict(
    LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PERFORMED_FALSE_FIELDS
)

DEFAULT_MINIMUM_SUITE_RUNS = 2
DEFAULT_MINIMUM_PASS_RATE_BPS = 10000
DEFAULT_MAXIMUM_FLAKY_RATE_BPS = 0
DEFAULT_MAXIMUM_EVIDENCE_AGE_DAYS = 30

_AGGREGATION_TYPE = "playwright_local_admission_receipt_aggregation_v1"
_RESULT_TYPE = "playwright_local_admission_receipt_aggregation_result_v1"
_MANIFEST_TYPE = "playwright_local_admission_receipt_aggregation_manifest_v1"
_ARTIFACT_INDEX_TYPE = "playwright_local_admission_receipt_aggregation_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "playwright_local_admission_receipt_aggregation_artifact_index_manifest_v1"
)
_SUITE_DIRS_MANIFEST_TYPE = "playwright_local_fixture_suite_run_dirs_manifest_v1"
_AUTHORITY = "non_authority_playwright_local_admission_receipt_aggregation_record"
_EXECUTION_CAPABILITY = "playwright_local_admission_receipt_aggregation_only"
_ADAPTER_ID = "playwright_local_admission_receipt_aggregation"
_CAPABILITY = "launch_playwright_local_admission_receipt_aggregation"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_SOURCE_SUITE_TYPE = "local_only_playwright_fixture_scenario_suite_v1"
_SOURCE_SUITE_RESULT_TYPE = "local_only_playwright_fixture_scenario_suite_result_v1"
_SOURCE_SUITE_MANIFEST_TYPE = "local_only_playwright_fixture_scenario_suite_manifest_v1"
_LOCAL_EXECUTION_SCOPE = "file_fixture_only"
_FIXTURE_SCHEME = "file"

_PLAN_READY_STATUS = "playwright_local_admission_receipt_aggregation_plan_ready"
_PASSED_STATUS = "playwright_local_admission_receipt_aggregation_passed"
_REJECTED_STATUS = "playwright_local_admission_receipt_aggregation_rejected"
_FAILED_STATUS = "playwright_local_admission_receipt_aggregation_failed"
_PLAN_READY_DECISION = "ready_to_run_playwright_local_admission_receipt_aggregation"
_PASSED_DECISION = "playwright_local_admission_receipt_aggregation_passed"
_REJECTED_DECISION = "fix_playwright_local_admission_receipts_and_retry"
_PLAN_NEXT_ACTION = "run_playwright_local_admission_receipt_aggregation"
_REVIEW_NEXT_ACTION = "review_playwright_local_admission_receipt_aggregation"
_FIX_NEXT_ACTION = "fix_playwright_local_admission_receipts_and_retry"

_PLAN_OUTPUT_FILES = (
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE,
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE,
)
_ALL_OUTPUT_FILES = _PLAN_OUTPUT_FILES + (
    PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE,
)
_REQUIRED_CORE_SCENARIO_IDS = (
    "static_click_marker",
    "repeated_local_fixture_execution_a",
    "repeated_local_fixture_execution_b",
)
_FALSE_FIELD_NAMES = frozenset(
    tuple(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS)
    + tuple(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS)
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
        "local_fixture_admission_granted",
    )
)


@dataclass(frozen=True)
class PlaywrightLocalAdmissionReceiptAggregationResult:
    suite_run_dirs_manifest_path: Path
    output_dir: Path
    aggregation_id: str
    plan_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    aggregate_success: bool
    aggregation_status: str
    aggregation_decision: str
    payload: dict[str, object]


def build_playwright_local_admission_receipt_aggregation_plan(
    suite_run_dirs_manifest: Path,
    output_dir: Path,
    aggregation_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    minimum_suite_runs: int = DEFAULT_MINIMUM_SUITE_RUNS,
    minimum_pass_rate_bps: int = DEFAULT_MINIMUM_PASS_RATE_BPS,
    maximum_flaky_rate_bps: int = DEFAULT_MAXIMUM_FLAKY_RATE_BPS,
    maximum_evidence_age_days: int = DEFAULT_MAXIMUM_EVIDENCE_AGE_DAYS,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    """Create aggregation plan artifacts without evaluating suite runs."""

    return _build_or_run_aggregation(
        suite_run_dirs_manifest=Path(suite_run_dirs_manifest),
        output_dir=Path(output_dir),
        aggregation_id=aggregation_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
        evaluate=False,
    )


def run_playwright_local_admission_receipt_aggregation_launcher(
    suite_run_dirs_manifest: Path,
    output_dir: Path,
    aggregation_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    minimum_suite_runs: int = DEFAULT_MINIMUM_SUITE_RUNS,
    minimum_pass_rate_bps: int = DEFAULT_MINIMUM_PASS_RATE_BPS,
    maximum_flaky_rate_bps: int = DEFAULT_MAXIMUM_FLAKY_RATE_BPS,
    maximum_evidence_age_days: int = DEFAULT_MAXIMUM_EVIDENCE_AGE_DAYS,
    plan_only: bool = False,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    """Launcher-oriented wrapper for plan or aggregation."""

    if plan_only:
        return build_playwright_local_admission_receipt_aggregation_plan(
            suite_run_dirs_manifest,
            output_dir,
            aggregation_id,
            review_attestation=review_attestation,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            minimum_suite_runs=minimum_suite_runs,
            minimum_pass_rate_bps=minimum_pass_rate_bps,
            maximum_flaky_rate_bps=maximum_flaky_rate_bps,
            maximum_evidence_age_days=maximum_evidence_age_days,
        )
    return run_playwright_local_admission_receipt_aggregation(
        suite_run_dirs_manifest,
        output_dir,
        aggregation_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
    )


def run_playwright_local_admission_receipt_aggregation(
    suite_run_dirs_manifest: Path,
    output_dir: Path,
    aggregation_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    minimum_suite_runs: int = DEFAULT_MINIMUM_SUITE_RUNS,
    minimum_pass_rate_bps: int = DEFAULT_MINIMUM_PASS_RATE_BPS,
    maximum_flaky_rate_bps: int = DEFAULT_MAXIMUM_FLAKY_RATE_BPS,
    maximum_evidence_age_days: int = DEFAULT_MAXIMUM_EVIDENCE_AGE_DAYS,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    """Evaluate existing #424 suite run artifacts and aggregate evidence."""

    return _build_or_run_aggregation(
        suite_run_dirs_manifest=Path(suite_run_dirs_manifest),
        output_dir=Path(output_dir),
        aggregation_id=aggregation_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
        evaluate=True,
    )


def _build_or_run_aggregation(
    *,
    suite_run_dirs_manifest: Path,
    output_dir: Path,
    aggregation_id: str,
    review_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    minimum_suite_runs: int,
    minimum_pass_rate_bps: int,
    maximum_flaky_rate_bps: int,
    maximum_evidence_age_days: int,
    evaluate: bool,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    manifest_path = Path(suite_run_dirs_manifest)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)

    preflight_error = _preflight_error(
        suite_run_dirs_manifest=manifest_path,
        output_dir=output_path,
        output_files=_ALL_OUTPUT_FILES,
        aggregation_id=aggregation_id,
        review_attestation=review_attestation,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
    )
    if preflight_error is not None:
        return _structured_failure_result(
            manifest_path,
            output_path,
            aggregation_id,
            preflight_error[0],
            preflight_error[1],
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )

    manifest_payload, _manifest_error = _read_json_object(
        manifest_path,
        "suite_run_dirs manifest",
    )
    normalized_dirs = _normalized_suite_run_dirs(manifest_payload, manifest_path)
    duplicate_paths = _duplicate_paths(normalized_dirs)
    manifest_sha256 = sha256_file(manifest_path)

    if not evaluate:
        plan = _plan_payload(
            suite_run_dirs_manifest=manifest_path,
            suite_run_dirs_manifest_sha256=manifest_sha256,
            output_dir=output_path,
            paths=paths,
            aggregation_id=aggregation_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            review_attestation=review_attestation or "",
            normalized_suite_run_dirs=normalized_dirs,
            minimum_suite_runs=minimum_suite_runs,
            minimum_pass_rate_bps=minimum_pass_rate_bps,
            maximum_flaky_rate_bps=maximum_flaky_rate_bps,
            maximum_evidence_age_days=maximum_evidence_age_days,
            status=_PLAN_READY_STATUS,
            decision=_PLAN_READY_DECISION,
            next_action=_PLAN_NEXT_ACTION,
            aggregate_success=False,
        )
        return _write_successful_payloads(
            manifest_path=manifest_path,
            output_path=output_path,
            aggregation_id=aggregation_id,
            paths=paths,
            plan=plan,
            result=None,
            complete=True,
            aggregate_success=False,
            evaluated=False,
        )

    suite_run_results = [
        _evaluate_suite_run(
            suite_dir=Path(suite_dir),
            duplicate=Path(suite_dir).as_posix() in duplicate_paths,
            maximum_evidence_age_days=maximum_evidence_age_days,
        )
        for suite_dir in normalized_dirs
    ]
    aggregate_metrics = _aggregate_metrics(
        suite_run_results=suite_run_results,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
    )
    aggregate_success = bool(aggregate_metrics["aggregate_success"])
    status = _PASSED_STATUS if aggregate_success else _REJECTED_STATUS
    decision = _PASSED_DECISION if aggregate_success else _REJECTED_DECISION
    next_action = _REVIEW_NEXT_ACTION if aggregate_success else _FIX_NEXT_ACTION
    plan = _plan_payload(
        suite_run_dirs_manifest=manifest_path,
        suite_run_dirs_manifest_sha256=manifest_sha256,
        output_dir=output_path,
        paths=paths,
        aggregation_id=aggregation_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        review_attestation=review_attestation or "",
        normalized_suite_run_dirs=normalized_dirs,
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
        status=status,
        decision=decision,
        next_action=next_action,
        aggregate_success=aggregate_success,
    )
    result = _result_payload(
        aggregation_id=aggregation_id,
        suite_run_results=suite_run_results,
        aggregate_metrics=aggregate_metrics,
        status=status,
        decision=decision,
        next_action=next_action,
    )
    return _write_successful_payloads(
        manifest_path=manifest_path,
        output_path=output_path,
        aggregation_id=aggregation_id,
        paths=paths,
        plan=plan,
        result=result,
        complete=aggregate_success,
        aggregate_success=aggregate_success,
        evaluated=True,
    )


def _preflight_error(
    *,
    suite_run_dirs_manifest: Path,
    output_dir: Path,
    output_files: tuple[str, ...],
    aggregation_id: str,
    review_attestation: str | None,
    minimum_suite_runs: int,
    minimum_pass_rate_bps: int,
    maximum_flaky_rate_bps: int,
    maximum_evidence_age_days: int,
) -> tuple[str, str] | None:
    attestation_error = _review_attestation_error(review_attestation)
    if attestation_error is not None:
        return "preflight_review_attestation", attestation_error
    output_error = _output_error(output_dir, output_files)
    if output_error is not None:
        return "preflight_output_dir", output_error
    if not _non_empty_text(aggregation_id):
        return "preflight_aggregation_id", "aggregation_id is missing"
    threshold_error = _threshold_error(
        minimum_suite_runs=minimum_suite_runs,
        minimum_pass_rate_bps=minimum_pass_rate_bps,
        maximum_flaky_rate_bps=maximum_flaky_rate_bps,
        maximum_evidence_age_days=maximum_evidence_age_days,
    )
    if threshold_error is not None:
        return "preflight_thresholds", threshold_error
    manifest_error = _suite_run_dirs_manifest_error(suite_run_dirs_manifest)
    if manifest_error is not None:
        return "preflight_suite_run_dirs_manifest", manifest_error
    return None


def _review_attestation_error(value: str | None) -> str | None:
    if not _non_empty_text(value):
        return "review_attestation is required"
    if value != PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_REVIEW_ATTESTATION:
        return "review_attestation must match required local fixture-only review phrase"
    return None


def _output_error(output_path: Path, output_files: tuple[str, ...]) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir must be a directory"
    for file_name in sorted(output_files):
        candidate = output_path / file_name
        if os.path.lexists(candidate):
            return "aggregation output artifact already exists: " + file_name
    return None


def _threshold_error(
    *,
    minimum_suite_runs: int,
    minimum_pass_rate_bps: int,
    maximum_flaky_rate_bps: int,
    maximum_evidence_age_days: int,
) -> str | None:
    if minimum_suite_runs < 1:
        return "minimum_suite_runs must be at least 1"
    for label, value in (
        ("minimum_pass_rate_bps", minimum_pass_rate_bps),
        ("maximum_flaky_rate_bps", maximum_flaky_rate_bps),
    ):
        if value < 0 or value > 10000:
            return label + " must be between 0 and 10000"
    if maximum_evidence_age_days < 0:
        return "maximum_evidence_age_days must be non-negative"
    return None


def _suite_run_dirs_manifest_error(path: Path) -> str | None:
    if not os.path.lexists(path):
        return "suite_run_dirs manifest is missing"
    if path.is_symlink():
        return "suite_run_dirs manifest must not be a symlink"
    if not path.is_file():
        return "suite_run_dirs manifest must be a regular file"
    payload, read_error = _read_json_object(path, "suite_run_dirs manifest")
    if read_error is not None:
        return read_error
    if payload.get("manifest_type") != _SUITE_DIRS_MANIFEST_TYPE:
        return "manifest_type must be " + _SUITE_DIRS_MANIFEST_TYPE
    suite_dirs = payload.get("suite_run_dirs")
    if not isinstance(suite_dirs, list) or not suite_dirs:
        return "suite_run_dirs must be a non-empty ordered list"
    if not all(isinstance(item, str) and item.strip() for item in suite_dirs):
        return "suite_run_dirs entries must be non-empty strings"
    return None


def _normalized_suite_run_dirs(
    manifest_payload: dict[str, object],
    manifest_path: Path,
) -> list[str]:
    suite_dirs = manifest_payload.get("suite_run_dirs")
    if not isinstance(suite_dirs, list):
        return []
    normalized = []
    for value in suite_dirs:
        if not isinstance(value, str):
            continue
        path = Path(value)
        if not path.is_absolute():
            path = manifest_path.parent / path
        normalized.append(Path(os.path.abspath(os.path.normpath(path))).as_posix())
    return normalized


def _duplicate_paths(paths: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for path in paths:
        if path in seen:
            duplicates.add(path)
        seen.add(path)
    return duplicates


def _evaluate_suite_run(
    *,
    suite_dir: Path,
    duplicate: bool,
    maximum_evidence_age_days: int,
) -> dict[str, object]:
    paths = _source_suite_paths(suite_dir)
    rejection_reasons: list[str] = []
    if duplicate:
        rejection_reasons.append("duplicate_suite_run_dir")
    dir_error = _source_suite_dir_error(suite_dir)
    if dir_error is not None:
        rejection_reasons.append(dir_error)
        return _suite_run_result_payload(
            suite_dir=suite_dir,
            paths=paths,
            suite_result={},
            suite_manifest={},
            artifact_index={},
            artifact_index_manifest={},
            rejected=True,
            rejection_reasons=rejection_reasons,
            hashes_verified=False,
            boundaries_false=False,
            artifact_index_under_suite_dir=False,
            candidate_repo_files_indexed=False,
            external_candidate_artifacts_indexed=False,
            stale_evidence=False,
        )
    for key in (
        "suite_result",
        "suite_manifest",
        "artifact_index",
        "artifact_index_manifest",
    ):
        file_error = _regular_file_error(paths[key], key)
        if file_error is not None:
            rejection_reasons.append(file_error)

    payloads: dict[str, dict[str, object]] = {}
    for key in (
        "suite_plan",
        "suite_result",
        "suite_manifest",
        "artifact_index",
        "artifact_index_manifest",
    ):
        if os.path.lexists(paths[key]) and not paths[key].is_symlink() and paths[key].is_file():
            payload, read_error = _read_json_object(paths[key], key)
            payloads[key] = payload
            if read_error is not None:
                rejection_reasons.append(read_error)
        else:
            payloads[key] = {}

    suite_result = payloads["suite_result"]
    suite_manifest = payloads["suite_manifest"]
    artifact_index = payloads["artifact_index"]
    artifact_index_manifest = payloads["artifact_index_manifest"]
    type_reasons = _source_type_rejection_reasons(suite_result, suite_manifest)
    rejection_reasons.extend(type_reasons)
    index_verification = _verify_index_payload(artifact_index, suite_dir)
    manifest_hashes_verified = _verify_manifest_hashes(suite_manifest, suite_dir)
    index_manifest_verified = _verify_index_manifest(
        artifact_index_manifest,
        paths["artifact_index"],
        suite_dir,
    )
    hashes_verified = (
        index_verification["all_hashes_match"]
        and manifest_hashes_verified
        and index_manifest_verified
    )
    boundaries_false = not _true_fields(payloads)
    candidate_repo_files_indexed = bool(index_verification["candidate_repo_files_indexed"])
    external_candidate_artifacts_indexed = bool(
        index_verification["external_candidate_artifacts_indexed"]
    )
    artifact_index_under_suite_dir = bool(index_verification["paths_under_suite_dir"])
    if not artifact_index_under_suite_dir:
        rejection_reasons.append("artifact_index_path_outside_suite_dir")
    if not index_verification["no_symlink_paths"]:
        rejection_reasons.append("artifact_index_symlink_path")
    if not hashes_verified:
        rejection_reasons.append("artifact_hash_mismatch")
    if not boundaries_false:
        rejection_reasons.append("boundary_false_field_true")
    if candidate_repo_files_indexed:
        rejection_reasons.append("candidate_repo_files_indexed")
    if external_candidate_artifacts_indexed:
        rejection_reasons.append("external_candidate_artifacts_indexed")
    stale_evidence = _stale_evidence_detected(
        (suite_result, suite_manifest, payloads["suite_plan"]),
        maximum_evidence_age_days,
    )
    return _suite_run_result_payload(
        suite_dir=suite_dir,
        paths=paths,
        suite_result=suite_result,
        suite_manifest=suite_manifest,
        artifact_index=artifact_index,
        artifact_index_manifest=artifact_index_manifest,
        rejected=bool(rejection_reasons),
        rejection_reasons=sorted(set(rejection_reasons)),
        hashes_verified=hashes_verified,
        boundaries_false=boundaries_false,
        artifact_index_under_suite_dir=artifact_index_under_suite_dir,
        candidate_repo_files_indexed=candidate_repo_files_indexed,
        external_candidate_artifacts_indexed=external_candidate_artifacts_indexed,
        stale_evidence=stale_evidence,
    )


def _source_suite_paths(suite_dir: Path) -> dict[str, Path]:
    return {
        "suite_plan": suite_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_PLAN_FILE,
        "suite_result": suite_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_RESULT_FILE,
        "suite_manifest": suite_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_MANIFEST_FILE,
        "artifact_index": suite_dir / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_FILE,
        "artifact_index_manifest": suite_dir
        / LOCAL_ONLY_PLAYWRIGHT_FIXTURE_SCENARIO_SUITE_ARTIFACT_INDEX_MANIFEST_FILE,
    }


def _source_suite_dir_error(path: Path) -> str | None:
    if path.is_symlink():
        return "suite_run_dir_must_not_be_symlink"
    if not path.exists():
        return "suite_run_dir_missing"
    if not path.is_dir():
        return "suite_run_dir_not_directory"
    if _path_has_any_symlink_component(path):
        return "suite_run_dir_symlink_component"
    return None


def _regular_file_error(path: Path, label: str) -> str | None:
    if not os.path.lexists(path):
        return label + "_missing"
    if path.is_symlink():
        return label + "_must_not_be_symlink"
    if not path.is_file():
        return label + "_not_regular_file"
    return None


def _source_type_rejection_reasons(
    suite_result: dict[str, object],
    suite_manifest: dict[str, object],
) -> list[str]:
    reasons = []
    if suite_result.get("result_type") != _SOURCE_SUITE_RESULT_TYPE:
        reasons.append("suite_result_type_mismatch")
    if suite_manifest.get("manifest_type") != _SOURCE_SUITE_MANIFEST_TYPE:
        reasons.append("suite_manifest_type_mismatch")
    if suite_result.get("local_execution_scope") != _LOCAL_EXECUTION_SCOPE:
        reasons.append("local_execution_scope_not_file_fixture_only")
    if suite_result.get("fixture_url_scheme") != _FIXTURE_SCHEME:
        reasons.append("fixture_url_scheme_not_file")
    if suite_result.get("selected_candidate_id") != _CANDIDATE_ID:
        reasons.append("selected_candidate_id_mismatch")
    if suite_result.get("repo_full_name") != _REPO_FULL_NAME:
        reasons.append("repo_full_name_mismatch")
    return reasons


def _suite_run_result_payload(
    *,
    suite_dir: Path,
    paths: dict[str, Path],
    suite_result: dict[str, object],
    suite_manifest: dict[str, object],
    artifact_index: dict[str, object],
    artifact_index_manifest: dict[str, object],
    rejected: bool,
    rejection_reasons: list[str],
    hashes_verified: bool,
    boundaries_false: bool,
    artifact_index_under_suite_dir: bool,
    candidate_repo_files_indexed: bool,
    external_candidate_artifacts_indexed: bool,
    stale_evidence: bool,
) -> dict[str, object]:
    scenario_results = suite_result.get("scenario_results")
    if not isinstance(scenario_results, list):
        scenario_results = []
    scenario_ids = [
        str(item.get("scenario_id"))
        for item in scenario_results
        if isinstance(item, dict) and _non_empty_text(item.get("scenario_id"))
    ]
    failed_scenario_ids = [
        str(item.get("scenario_id"))
        for item in scenario_results
        if isinstance(item, dict)
        and _non_empty_text(item.get("scenario_id"))
        and item.get("success") is not True
    ]
    return {
        "suite_run_dir": suite_dir.as_posix(),
        "suite_result_path": paths["suite_result"].as_posix(),
        "suite_manifest_path": paths["suite_manifest"].as_posix(),
        "artifact_index_path": paths["artifact_index"].as_posix(),
        "artifact_index_manifest_path": paths["artifact_index_manifest"].as_posix(),
        "suite_success": suite_result.get("suite_success") is True,
        "suite_status": suite_result.get("suite_status"),
        "suite_decision": suite_result.get("suite_decision"),
        "scenario_set": suite_result.get("scenario_set"),
        "scenario_count_planned": _int_value(suite_result.get("scenario_count_planned")),
        "scenario_count_executed": _int_value(suite_result.get("scenario_count_executed")),
        "scenario_count_passed": _int_value(suite_result.get("scenario_count_passed")),
        "scenario_count_failed": _int_value(suite_result.get("scenario_count_failed")),
        "scenario_ids": scenario_ids,
        "failed_scenario_ids": failed_scenario_ids,
        "rejected": rejected,
        "rejection_reasons": rejection_reasons,
        "hashes_verified": hashes_verified,
        "boundaries_false": boundaries_false,
        "artifact_index_under_suite_dir": artifact_index_under_suite_dir,
        "candidate_repo_files_indexed": candidate_repo_files_indexed,
        "external_candidate_artifacts_indexed": external_candidate_artifacts_indexed,
        "stale_evidence": stale_evidence,
        "suite_manifest_type": suite_manifest.get("manifest_type"),
        "artifact_index_type": artifact_index.get("index_type"),
        "artifact_index_manifest_type": artifact_index_manifest.get("manifest_type"),
    }


def _aggregate_metrics(
    *,
    suite_run_results: list[dict[str, object]],
    minimum_suite_runs: int,
    minimum_pass_rate_bps: int,
    maximum_flaky_rate_bps: int,
) -> dict[str, object]:
    comparable_runs = [item for item in suite_run_results if item["rejected"] is not True]
    suite_run_count_evaluated = len(suite_run_results)
    suite_run_count_passed = sum(
        1 for item in comparable_runs if item["suite_success"] is True
    )
    suite_run_count_failed = sum(
        1 for item in comparable_runs if item["suite_success"] is not True
    )
    suite_run_count_rejected = sum(
        1 for item in suite_run_results if item["rejected"] is True
    )
    scenario_count_total = sum(
        int(item.get("scenario_count_executed") or 0) for item in comparable_runs
    )
    scenario_count_passed = sum(
        int(item.get("scenario_count_passed") or 0) for item in comparable_runs
    )
    scenario_count_failed = sum(
        int(item.get("scenario_count_failed") or 0) for item in comparable_runs
    )
    pass_rate_bps = _rate_bps(scenario_count_passed, scenario_count_total)
    flaky_scenario_ids = _flaky_scenario_ids(comparable_runs)
    flaky_rate_bps = _rate_bps(len(flaky_scenario_ids), len(_scenario_id_union(comparable_runs)))
    regression_detected = _regression_detected(comparable_runs)
    stale_evidence_detected = any(
        item.get("stale_evidence") is True for item in suite_run_results
    )
    missing_coverage_detected = _missing_core_coverage(comparable_runs)
    hashes_verified_all = all(
        item.get("hashes_verified") is True for item in suite_run_results
    )
    boundaries_false_all = all(
        item.get("boundaries_false") is True for item in suite_run_results
    )
    artifact_indexes_under_suite_dir = all(
        item.get("artifact_index_under_suite_dir") is True
        for item in suite_run_results
    )
    candidate_repo_files_indexed_any = any(
        item.get("candidate_repo_files_indexed") is True for item in suite_run_results
    )
    external_candidate_artifacts_indexed_any = any(
        item.get("external_candidate_artifacts_indexed") is True
        for item in suite_run_results
    )
    aggregate_success = all(
        (
            suite_run_count_evaluated >= minimum_suite_runs,
            suite_run_count_rejected == 0,
            suite_run_count_failed == 0,
            pass_rate_bps >= minimum_pass_rate_bps,
            flaky_rate_bps <= maximum_flaky_rate_bps,
            not regression_detected,
            not stale_evidence_detected,
            not missing_coverage_detected,
            hashes_verified_all,
            boundaries_false_all,
            artifact_indexes_under_suite_dir,
            not candidate_repo_files_indexed_any,
            not external_candidate_artifacts_indexed_any,
        )
    )
    return {
        "suite_run_count_planned": suite_run_count_evaluated,
        "suite_run_count_evaluated": suite_run_count_evaluated,
        "suite_run_count_passed": suite_run_count_passed,
        "suite_run_count_failed": suite_run_count_failed,
        "suite_run_count_rejected": suite_run_count_rejected,
        "scenario_count_total": scenario_count_total,
        "scenario_count_passed": scenario_count_passed,
        "scenario_count_failed": scenario_count_failed,
        "pass_rate_bps": pass_rate_bps,
        "flaky_scenario_ids": flaky_scenario_ids,
        "flaky_rate_bps": flaky_rate_bps,
        "regression_detected": regression_detected,
        "stale_evidence_detected": stale_evidence_detected,
        "missing_coverage_detected": missing_coverage_detected,
        "hashes_verified_all": hashes_verified_all,
        "boundaries_false_all": boundaries_false_all,
        "artifact_indexes_under_suite_dir": artifact_indexes_under_suite_dir,
        "candidate_repo_files_indexed_any": candidate_repo_files_indexed_any,
        "external_candidate_artifacts_indexed_any": external_candidate_artifacts_indexed_any,
        "aggregate_success": aggregate_success,
        "minimum_suite_runs_satisfied": suite_run_count_evaluated >= minimum_suite_runs,
        "minimum_pass_rate_satisfied": pass_rate_bps >= minimum_pass_rate_bps,
        "maximum_flaky_rate_satisfied": flaky_rate_bps <= maximum_flaky_rate_bps,
    }


def _flaky_scenario_ids(suite_run_results: list[dict[str, object]]) -> list[str]:
    state: dict[str, set[bool]] = {}
    for run_result in suite_run_results:
        failed = set(run_result.get("failed_scenario_ids") or [])
        for scenario_id in run_result.get("scenario_ids") or []:
            if not isinstance(scenario_id, str):
                continue
            state.setdefault(scenario_id, set()).add(scenario_id not in failed)
    return sorted(scenario_id for scenario_id, outcomes in state.items() if outcomes == {False, True})


def _regression_detected(suite_run_results: list[dict[str, object]]) -> bool:
    passed_before: set[str] = set()
    for run_result in suite_run_results:
        failed = set(run_result.get("failed_scenario_ids") or [])
        for scenario_id in run_result.get("scenario_ids") or []:
            if not isinstance(scenario_id, str):
                continue
            if scenario_id in failed and scenario_id in passed_before:
                return True
            if scenario_id not in failed:
                passed_before.add(scenario_id)
    return False


def _missing_core_coverage(suite_run_results: list[dict[str, object]]) -> bool:
    if not suite_run_results:
        return True
    required = set(_REQUIRED_CORE_SCENARIO_IDS)
    for run_result in suite_run_results:
        scenario_ids = set(run_result.get("scenario_ids") or [])
        if not required.issubset(scenario_ids):
            return True
    return False


def _scenario_id_union(suite_run_results: list[dict[str, object]]) -> set[str]:
    scenario_ids: set[str] = set()
    for run_result in suite_run_results:
        for scenario_id in run_result.get("scenario_ids") or []:
            if isinstance(scenario_id, str):
                scenario_ids.add(scenario_id)
    return scenario_ids


def _stale_evidence_detected(
    payloads: tuple[dict[str, object], ...],
    maximum_evidence_age_days: int,
) -> bool:
    for payload in payloads:
        for key in ("evidence_age_days", "suite_evidence_age_days"):
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                if value > maximum_evidence_age_days:
                    return True
        for key in (
            "evidence_timestamp_utc",
            "suite_completed_at_utc",
            "completed_at_utc",
            "generated_at_utc",
            "created_at_utc",
        ):
            value = payload.get(key)
            if isinstance(value, str) and _timestamp_is_stale(
                value,
                maximum_evidence_age_days,
            ):
                return True
    return False


def _timestamp_is_stale(value: str, maximum_evidence_age_days: int) -> bool:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
    return age.days > maximum_evidence_age_days


def _verify_index_payload(
    index_payload: dict[str, object],
    suite_dir: Path,
) -> dict[str, bool]:
    entries = index_payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return {
            "paths_under_suite_dir": False,
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
        if not _path_is_inside(path, suite_dir):
            paths_under = False
            external_candidate_artifacts_indexed = True
            all_hashes = False
        if path.is_symlink() or _path_has_symlink_component(path, suite_dir):
            no_symlinks = False
            all_hashes = False
        if not path.exists() or not path.is_file() or path.is_symlink():
            all_hashes = False
            continue
        recorded_hash = entry.get("sha256")
        if not isinstance(recorded_hash, str) or not recorded_hash:
            all_hashes = False
        elif sha256_file(path) != recorded_hash:
            all_hashes = False
    return {
        "paths_under_suite_dir": paths_under,
        "no_symlink_paths": no_symlinks,
        "all_hashes_match": all_hashes,
        "candidate_repo_files_indexed": candidate_repo_files_indexed,
        "external_candidate_artifacts_indexed": external_candidate_artifacts_indexed,
    }


def _verify_index_manifest(
    index_manifest: dict[str, object],
    artifact_index_path: Path,
    suite_dir: Path,
) -> bool:
    path_value = index_manifest.get("artifact_index_path")
    recorded_hash = index_manifest.get("artifact_index_sha256")
    if not isinstance(path_value, str) or not isinstance(recorded_hash, str):
        return False
    path = Path(path_value)
    if path.resolve(strict=False) != artifact_index_path.resolve(strict=False):
        return False
    if not _path_is_inside(path, suite_dir):
        return False
    if path.is_symlink() or not path.exists() or not path.is_file():
        return False
    return sha256_file(path) == recorded_hash


def _verify_manifest_hashes(manifest: dict[str, object], suite_dir: Path) -> bool:
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
        if not _path_is_inside(path, suite_dir):
            continue
        checked += 1
        if path.is_symlink() or not path.exists() or not path.is_file():
            ok = False
            continue
        if sha256_file(path) != recorded_hash:
            ok = False
    return checked > 0 and ok


def _plan_payload(
    *,
    suite_run_dirs_manifest: Path,
    suite_run_dirs_manifest_sha256: str,
    output_dir: Path,
    paths: dict[str, Path],
    aggregation_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    review_attestation: str,
    normalized_suite_run_dirs: list[str],
    minimum_suite_runs: int,
    minimum_pass_rate_bps: int,
    maximum_flaky_rate_bps: int,
    maximum_evidence_age_days: int,
    status: str,
    decision: str,
    next_action: str,
    aggregate_success: bool,
) -> dict[str, object]:
    return {
        "aggregation_type": _AGGREGATION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "aggregation_id": aggregation_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "review_attestation_present": True,
        "review_attestation_sha256": _sha256_text(review_attestation),
        "suite_run_dirs_manifest_path": suite_run_dirs_manifest.as_posix(),
        "suite_run_dirs_manifest_sha256": suite_run_dirs_manifest_sha256,
        "suite_run_dirs": list(normalized_suite_run_dirs),
        "suite_run_count_planned": len(normalized_suite_run_dirs),
        "minimum_suite_runs": minimum_suite_runs,
        "minimum_pass_rate_bps": minimum_pass_rate_bps,
        "maximum_flaky_rate_bps": maximum_flaky_rate_bps,
        "maximum_evidence_age_days": maximum_evidence_age_days,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_suite_type": _SOURCE_SUITE_TYPE,
        "source_suite_result_type": _SOURCE_SUITE_RESULT_TYPE,
        "aggregation_output_dir": output_dir.as_posix(),
        "aggregation_plan_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE
        ].as_posix(),
        "aggregation_result_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE
        ].as_posix(),
        "aggregation_manifest_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE
        ].as_posix(),
        "aggregation_status": status,
        "aggregation_decision": decision,
        "next_allowed_action": next_action,
        "aggregate_success": aggregate_success,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }


def _result_payload(
    *,
    aggregation_id: str,
    suite_run_results: list[dict[str, object]],
    aggregate_metrics: dict[str, object],
    status: str,
    decision: str,
    next_action: str,
) -> dict[str, object]:
    aggregate_success = bool(aggregate_metrics["aggregate_success"])
    return {
        "result_type": _RESULT_TYPE,
        "aggregation_id": aggregation_id,
        "suite_run_count_planned": aggregate_metrics["suite_run_count_planned"],
        "suite_run_count_evaluated": aggregate_metrics["suite_run_count_evaluated"],
        "suite_run_count_passed": aggregate_metrics["suite_run_count_passed"],
        "suite_run_count_failed": aggregate_metrics["suite_run_count_failed"],
        "suite_run_count_rejected": aggregate_metrics["suite_run_count_rejected"],
        "scenario_count_total": aggregate_metrics["scenario_count_total"],
        "scenario_count_passed": aggregate_metrics["scenario_count_passed"],
        "scenario_count_failed": aggregate_metrics["scenario_count_failed"],
        "pass_rate_bps": aggregate_metrics["pass_rate_bps"],
        "flaky_scenario_ids": aggregate_metrics["flaky_scenario_ids"],
        "flaky_rate_bps": aggregate_metrics["flaky_rate_bps"],
        "regression_detected": aggregate_metrics["regression_detected"],
        "stale_evidence_detected": aggregate_metrics["stale_evidence_detected"],
        "missing_coverage_detected": aggregate_metrics["missing_coverage_detected"],
        "required_core_scenario_ids": list(_REQUIRED_CORE_SCENARIO_IDS),
        "suite_run_results": suite_run_results,
        "aggregate_success": aggregate_success,
        "aggregation_status": status,
        "aggregation_decision": decision,
        "next_allowed_action": next_action,
        "production_admission_granted": False,
        "live_website_admission_granted": False,
        "general_browser_automation_admission_granted": False,
        "local_fixture_aggregation_passed": aggregate_success,
        "hashes_verified_all": aggregate_metrics["hashes_verified_all"],
        "boundaries_false_all": aggregate_metrics["boundaries_false_all"],
        "candidate_repo_files_indexed_any": aggregate_metrics[
            "candidate_repo_files_indexed_any"
        ],
        "external_candidate_artifacts_indexed_any": aggregate_metrics[
            "external_candidate_artifacts_indexed_any"
        ],
        "minimum_suite_runs_satisfied": aggregate_metrics[
            "minimum_suite_runs_satisfied"
        ],
        "minimum_pass_rate_satisfied": aggregate_metrics[
            "minimum_pass_rate_satisfied"
        ],
        "maximum_flaky_rate_satisfied": aggregate_metrics[
            "maximum_flaky_rate_satisfied"
        ],
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }


def _write_successful_payloads(
    *,
    manifest_path: Path,
    output_path: Path,
    aggregation_id: str,
    paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object] | None,
    complete: bool,
    aggregate_success: bool,
    evaluated: bool,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE],
        plan,
    )
    if result is not None:
        _write_json_exclusive(
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE],
            result,
        )
    _write_text_exclusive(
        paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE],
        _summary_markdown(plan, result),
    )
    _write_text_exclusive(
        paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE],
        _checklist_markdown(plan, result),
    )
    manifest = _manifest_payload(
        output_path=output_path,
        paths=paths,
        plan=plan,
        result=result,
        evaluated=evaluated,
        aggregate_success=aggregate_success,
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        evaluated=evaluated,
        status=str(plan["aggregation_status"]),
        next_action=str(plan["next_allowed_action"]),
    )
    _write_json_exclusive(
        paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    index_manifest = _artifact_index_manifest_payload(output_path, paths, artifact_index)
    _write_json_exclusive(
        paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        index_manifest,
    )
    payload = _launcher_payload(
        suite_run_dirs_manifest=manifest_path,
        output_path=output_path,
        paths=paths,
        plan=plan,
        result=result,
        artifact_index=artifact_index,
        complete=complete,
        aggregate_success=aggregate_success,
        evaluated=evaluated,
    )
    return PlaywrightLocalAdmissionReceiptAggregationResult(
        suite_run_dirs_manifest_path=manifest_path,
        output_dir=output_path,
        aggregation_id=aggregation_id,
        plan_path=paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE],
        result_path=paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE]
        if evaluated
        else None,
        manifest_path=paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE
        ],
        summary_path=paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE],
        checklist_path=paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=complete,
        aggregate_success=aggregate_success,
        aggregation_status=str(plan["aggregation_status"]),
        aggregation_decision=str(plan["aggregation_decision"]),
        payload=payload,
    )


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object] | None,
    evaluated: bool,
    aggregate_success: bool,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "aggregation_id": plan["aggregation_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "plan_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE]
        ),
        "summary_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE]
        ),
        "suite_run_dirs_manifest_path": plan["suite_run_dirs_manifest_path"],
        "suite_run_dirs_manifest_sha256": plan["suite_run_dirs_manifest_sha256"],
        "suite_run_count_planned": plan["suite_run_count_planned"],
        "selected_candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_suite_type": _SOURCE_SUITE_TYPE,
        "source_suite_result_type": _SOURCE_SUITE_RESULT_TYPE,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "evaluated": evaluated,
        "aggregate_success": aggregate_success,
        "aggregation_status": plan["aggregation_status"],
        "aggregation_decision": plan["aggregation_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }
    if result is not None:
        result_path = paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE]
        manifest.update(
            {
                "result_path": result_path.as_posix(),
                "result_sha256": sha256_file(result_path),
                "suite_run_count_evaluated": result["suite_run_count_evaluated"],
                "suite_run_count_rejected": result["suite_run_count_rejected"],
                "scenario_count_total": result["scenario_count_total"],
                "pass_rate_bps": result["pass_rate_bps"],
                "flaky_rate_bps": result["flaky_rate_bps"],
                "local_fixture_aggregation_passed": result[
                    "local_fixture_aggregation_passed"
                ],
            }
        )
    return manifest


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    evaluated: bool,
    status: str,
    next_action: str,
) -> dict[str, object]:
    roles = [
        (
            "playwright_local_admission_receipt_aggregation_plan",
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE],
        ),
        (
            "playwright_local_admission_receipt_aggregation_manifest",
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE],
        ),
        (
            "playwright_local_admission_receipt_aggregation_summary",
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE],
        ),
        (
            "playwright_local_admission_receipt_aggregation_checklist",
            paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE],
        ),
    ]
    if evaluated:
        roles.append(
            (
                "playwright_local_admission_receipt_aggregation_result",
                paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE],
            )
        )
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "aggregation_artifacts_under_output_dir_only",
        "aggregation_status": status,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": next_action,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE]
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
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
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
    suite_run_dirs_manifest: Path,
    output_path: Path,
    paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object] | None,
    artifact_index: dict[str, object],
    complete: bool,
    aggregate_success: bool,
    evaluated: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "aggregation_id": plan["aggregation_id"],
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "output_dir": output_path.as_posix(),
        "suite_run_dirs_manifest_path": suite_run_dirs_manifest.as_posix(),
        "suite_run_dirs_manifest_sha256": plan["suite_run_dirs_manifest_sha256"],
        "playwright_local_admission_receipt_aggregation_plan_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PLAN_FILE
        ].as_posix(),
        "playwright_local_admission_receipt_aggregation_manifest_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_MANIFEST_FILE
        ].as_posix(),
        "playwright_local_admission_receipt_aggregation_summary_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_SUMMARY_FILE
        ].as_posix(),
        "playwright_local_admission_receipt_aggregation_checklist_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_CHECKLIST_FILE
        ].as_posix(),
        "playwright_local_admission_receipt_aggregation_result_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_RESULT_FILE
        ].as_posix()
        if evaluated
        else None,
        "artifact_index_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "suite_run_count_planned": plan["suite_run_count_planned"],
        "suite_run_count_evaluated": 0
        if result is None
        else result["suite_run_count_evaluated"],
        "suite_run_count_passed": 0 if result is None else result["suite_run_count_passed"],
        "suite_run_count_failed": 0 if result is None else result["suite_run_count_failed"],
        "suite_run_count_rejected": 0
        if result is None
        else result["suite_run_count_rejected"],
        "scenario_count_total": 0 if result is None else result["scenario_count_total"],
        "scenario_count_passed": 0 if result is None else result["scenario_count_passed"],
        "scenario_count_failed": 0 if result is None else result["scenario_count_failed"],
        "pass_rate_bps": 0 if result is None else result["pass_rate_bps"],
        "flaky_rate_bps": 0 if result is None else result["flaky_rate_bps"],
        "flaky_scenario_ids": [] if result is None else result["flaky_scenario_ids"],
        "regression_detected": False
        if result is None
        else result["regression_detected"],
        "stale_evidence_detected": False
        if result is None
        else result["stale_evidence_detected"],
        "missing_coverage_detected": False
        if result is None
        else result["missing_coverage_detected"],
        "aggregate_success": aggregate_success,
        "local_fixture_aggregation_passed": False
        if result is None
        else result["local_fixture_aggregation_passed"],
        "aggregation_status": plan["aggregation_status"],
        "aggregation_decision": plan["aggregation_decision"],
        "next_allowed_action": plan["next_allowed_action"],
        "selected_candidate_id": _CANDIDATE_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "local_execution_scope": _LOCAL_EXECUTION_SCOPE,
        "fixture_url_scheme": _FIXTURE_SCHEME,
        "indexed_artifacts": artifact_index["indexed_artifacts"],
        "evaluated": evaluated,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }
    return payload


def _structured_failure_result(
    suite_run_dirs_manifest_path: Path,
    output_path: Path,
    aggregation_id: str,
    failure_stage: str,
    error_message: str,
    *,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
) -> PlaywrightLocalAdmissionReceiptAggregationResult:
    payload = {
        "complete": False,
        "aggregation_type": _AGGREGATION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "aggregation_id": aggregation_id,
        "adapter_id": _ADAPTER_ID,
        "capability": _CAPABILITY,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": _safe_text(operator_notes) if operator_notes is not None else None,
        "suite_run_dirs_manifest_path": suite_run_dirs_manifest_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "aggregate_success": False,
        "aggregation_status": _FAILED_STATUS,
        "aggregation_decision": _REJECTED_DECISION,
        "next_allowed_action": _FIX_NEXT_ACTION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "playwright_local_admission_receipt_aggregation_plan_path": None,
        "playwright_local_admission_receipt_aggregation_manifest_path": None,
        "playwright_local_admission_receipt_aggregation_summary_path": None,
        "playwright_local_admission_receipt_aggregation_checklist_path": None,
        "playwright_local_admission_receipt_aggregation_result_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "required_human_review": True,
        "required_human_approval": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_DISABLED_FIELDS),
        **dict(PLAYWRIGHT_LOCAL_ADMISSION_RECEIPT_AGGREGATION_PERFORMED_FALSE_FIELDS),
    }
    return PlaywrightLocalAdmissionReceiptAggregationResult(
        suite_run_dirs_manifest_path=suite_run_dirs_manifest_path,
        output_dir=output_path,
        aggregation_id=aggregation_id,
        plan_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        aggregate_success=False,
        aggregation_status=_FAILED_STATUS,
        aggregation_decision=_REJECTED_DECISION,
        payload=payload,
    )


def _summary_markdown(
    plan: dict[str, object],
    result: dict[str, object] | None,
) -> str:
    lines = [
        "# Playwright Local Admission Receipt Aggregation",
        "",
        "Status: " + str(plan["aggregation_status"]),
        "Aggregation id: " + str(plan["aggregation_id"]),
        "Planned suite runs: " + str(plan["suite_run_count_planned"]),
        "Candidate: microsoft/playwright",
        "Scope: local file fixture suite artifacts only",
        "Fixture scheme: file",
        "Evaluated: " + str(result is not None).lower(),
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
        "Boundary: historical #424 local fixture suite artifacts only.",
    ]
    if result is not None:
        lines.insert(5, "Evaluated suite runs: " + str(result["suite_run_count_evaluated"]))
        lines.insert(6, "Passed suite runs: " + str(result["suite_run_count_passed"]))
        lines.insert(7, "Aggregate success: " + str(result["aggregate_success"]).lower())
    return "\n".join(lines)


def _checklist_markdown(
    plan: dict[str, object],
    result: dict[str, object] | None,
) -> str:
    lines = [
        "# Playwright Local Admission Receipt Aggregation Checklist",
        "",
        "- [ ] Confirm the suite run dirs manifest order matches the reviewed evidence packet.",
        "- [ ] Confirm every source suite result is #424 local file fixture evidence.",
        "- [ ] Confirm artifact index paths remain under each suite run directory.",
        "- [ ] Confirm artifact hashes verify and no indexed path is a symlink.",
        "- [ ] Confirm candidate repository files and external candidate artifacts are not indexed.",
        "- [ ] Confirm no live website, arbitrary navigation, account, login, registration, scraping, bypass, or captcha workflow is involved.",
        "- [ ] Confirm no secrets, cookies, external network, package installation, browser download, package runners, or candidate code execution occurred.",
        "- [ ] Confirm aggregation success is not production admission.",
        "",
        "Aggregation decision: " + str(plan["aggregation_decision"]),
        "Next allowed action: " + str(plan["next_allowed_action"]),
    ]
    if result is not None:
        lines.append("Aggregate success: " + str(result["aggregate_success"]).lower())
    return "\n".join(lines)


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _ALL_OUTPUT_FILES}


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


def _true_fields(payloads: dict[str, dict[str, object]]) -> dict[str, list[str]]:
    true_fields: dict[str, list[str]] = {}
    for label, payload in payloads.items():
        matches = _true_field_paths(payload)
        if matches:
            true_fields[label] = sorted(matches)
    return true_fields


def _true_field_paths(value: object, prefix: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = key if not prefix else prefix + "." + str(key)
            if key in _FALSE_FIELD_NAMES and child is True:
                matches.append(path)
            matches.extend(_true_field_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(_true_field_paths(child, prefix + "[" + str(index) + "]"))
    return matches


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


def _path_has_any_symlink_component(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _candidate_repo_marker_in_path(path: Path) -> bool:
    lowered = tuple(part.lower() for part in Path(path).parts)
    if "capability_candidates" in lowered:
        return True
    for index in range(len(lowered) - 1):
        if lowered[index] == "microsoft" and lowered[index + 1] == "playwright":
            return True
    return False


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def _rate_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return int((numerator * 10000) // denominator)


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
    return text[:240] if text else "playwright local admission receipt aggregation failed"
