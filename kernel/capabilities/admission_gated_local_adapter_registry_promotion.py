"""Admission-gated local adapter registry promotion evidence.

This module reads an existing #427 local-fixture admission gate decision and
writes a restricted registry promotion record. It is metadata-only evidence:
no Playwright execution, dependency installation, candidate repository access,
runtime activation, production promotion, or autonomous adoption is performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.capabilities.local_fixture_playwright_adapter_admission_gate import (
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS,
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION",
    "ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE",
    "AdmissionGatedLocalAdapterRegistryPromotionResult",
    "run_admission_gated_local_adapter_registry_promotion",
    "run_admission_gated_local_adapter_registry_promotion_launcher",
]


ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE = (
    "admission_gated_local_adapter_registry_promotion_plan.json"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE = (
    "admission_gated_local_adapter_registry_promotion_result.json"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE = (
    "admission_gated_local_adapter_registry_promotion_manifest.json"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE = (
    "admission_gated_local_adapter_registry_promotion_summary.md"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE = (
    "admission_gated_local_adapter_registry_promotion_checklist.md"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE = (
    "artifact_index.json"
)
ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION = (
    "I_REVIEWED_AGGREGATION_BOUND_LOCAL_FIXTURE_ADMISSION_GATE_NO_PRODUCTION_"
    "NO_LIVE_WEBSITES_NO_AUTONOMY"
)

ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE = (
    "production",
    "live_website",
    "general_browser_automation",
    "arbitrary_url_navigation",
    "account_workflow",
    "scraping",
    "bypass",
    "captcha",
    "external_network",
    "credential_or_cookie_access",
    "package_install",
    "browser_download",
    "npm_or_npx",
    "candidate_repo_code",
    "arbitrary_command",
    "autonomy",
)

_PROMOTION_TYPE = "admission_gated_local_adapter_registry_promotion_v1"
_PLAN_TYPE = "admission_gated_local_adapter_registry_promotion_plan_v1"
_MANIFEST_TYPE = "admission_gated_local_adapter_registry_promotion_manifest_v1"
_ARTIFACT_INDEX_TYPE = (
    "admission_gated_local_adapter_registry_promotion_artifact_index_v1"
)
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "admission_gated_local_adapter_registry_promotion_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_local_fixture_registry_promotion_record"
_EXECUTION_CAPABILITY = "admission_gated_local_adapter_registry_promotion_only"
_PROMOTION_ADAPTER_ID = "admission_gated_local_adapter_registry_promotion"
_PROMOTION_CAPABILITY = "launch_admission_gated_local_adapter_registry_promotion"
_PROMOTED_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_PROMOTED_ADAPTER_CAPABILITY = "launch_bounded_playwright_worker_adapter_draft"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_SOURCE_DECISION_TYPE = "local_fixture_playwright_adapter_admission_gate_decision_v1"
_SOURCE_ADMITTED_STATUS = "local_fixture_playwright_adapter_admission_gate_admitted"
_SOURCE_ADMIT_DECISION = "admit_local_fixture_only_playwright_adapter"
_COMPLETED_STATUS = "admission_gated_local_adapter_registry_promotion_completed"
_REJECTED_STATUS = "admission_gated_local_adapter_registry_promotion_rejected"
_COMPLETED_DECISION = "promote_local_fixture_only_adapter_registration"
_REJECTED_DECISION = "reject_local_fixture_only_adapter_registration"
_NEXT_ALLOWED_ACTION = "use_local_fixture_only_adapter_under_human_review"
_FIX_SOURCE_NEXT_ACTION = "fix_admission_gate_decision_and_retry"
_REGISTRY_ENTRY_TYPE = "local_fixture_only_adapter_registry_entry_v1"
_REGISTRY_ENTRY_STATUS = "enabled_local_fixture_only"
_SOURCE_MANIFEST_FILE = "local_fixture_playwright_adapter_admission_gate_manifest.json"
_SOURCE_ARTIFACT_INDEX_FILE = "artifact_index.json"
_SOURCE_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_OUTPUT_FILES = (
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE,
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE,
)

_ADMISSION_FALSE_FIELDS = tuple(
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_FALSE_FIELDS
)
_PERFORMED_FALSE_FIELDS = tuple(
    LOCAL_FIXTURE_PLAYWRIGHT_ADAPTER_ADMISSION_PERFORMED_FALSE_FIELDS
)
_FORBIDDEN_ADMISSION_FIELDS = tuple(
    field_name
    for field_name in _ADMISSION_FALSE_FIELDS
    if field_name
    not in (
        "local_fixture_admission_granted",
        "production_admission_granted",
        "live_website_admission_granted",
        "general_browser_automation_admission_granted",
    )
)
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


@dataclass(frozen=True)
class AdmissionGatedLocalAdapterRegistryPromotionResult:
    admission_gate_decision_path: Path
    output_dir: Path
    promotion_id: str
    plan_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    registry_output_path: Path | None
    complete: bool
    promoted: bool
    promotion_status: str
    promotion_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_admission_gated_local_adapter_registry_promotion_launcher(
    admission_gate_decision: Path,
    output_dir: Path,
    promotion_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    registry_output: Path | None = None,
) -> AdmissionGatedLocalAdapterRegistryPromotionResult:
    """Launcher-oriented wrapper for the metadata-only promotion."""

    return run_admission_gated_local_adapter_registry_promotion(
        admission_gate_decision,
        output_dir,
        promotion_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_output=registry_output,
    )


def run_admission_gated_local_adapter_registry_promotion(
    admission_gate_decision: Path,
    output_dir: Path,
    promotion_id: str,
    *,
    review_attestation: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    registry_output: Path | None = None,
) -> AdmissionGatedLocalAdapterRegistryPromotionResult:
    """Validate a #427 decision and write a restricted promotion record."""

    source_path = Path(admission_gate_decision)
    output_path = Path(output_dir)
    registry_output_path = _normalized_registry_output(registry_output, output_path)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(
        output_path=output_path,
        promotion_id=promotion_id,
        registry_output_path=registry_output_path,
    )
    if preflight_reasons:
        return _unwritten_result(
            source_path=source_path,
            output_path=output_path,
            promotion_id=promotion_id,
            registry_output_path=registry_output_path,
            rejection_reasons=preflight_reasons,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
        )

    source_payload, source_read_reasons = _read_source_decision(source_path)
    rejection_reasons = list(source_read_reasons)
    if not rejection_reasons:
        rejection_reasons.extend(
            _source_decision_rejection_reasons(source_path, source_payload)
        )
    rejection_reasons.extend(_review_attestation_rejection_reasons(review_attestation))
    rejection_reasons = _dedupe_strings(rejection_reasons)
    promoted = not rejection_reasons
    promotion_status = _COMPLETED_STATUS if promoted else _REJECTED_STATUS
    promotion_decision = _COMPLETED_DECISION if promoted else _REJECTED_DECISION
    next_allowed_action = _NEXT_ALLOWED_ACTION if promoted else _FIX_SOURCE_NEXT_ACTION
    source_sha256 = _source_sha256(source_path)

    plan = _plan_payload(
        source_path=source_path,
        output_path=output_path,
        paths=paths,
        promotion_id=promotion_id,
        review_attestation=review_attestation,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_output_path=registry_output_path,
        source_sha256=source_sha256,
        source_payload=source_payload,
    )
    registry_record = _registry_record_payload(
        source_path=source_path,
        source_sha256=source_sha256,
        source_payload=source_payload,
        promotion_id=promotion_id,
        promoted=promoted,
    )
    result = _promotion_result_payload(
        source_path=source_path,
        source_sha256=source_sha256,
        source_payload=source_payload,
        promotion_id=promotion_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_output_path=registry_output_path,
        registry_record=registry_record,
        promoted=promoted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )

    _write_json_exclusive(paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE], plan)
    _write_json_exclusive(paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE], result)
    _write_markdown_exclusive(
        paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    if registry_output_path is not None:
        _write_json_exclusive(registry_output_path, registry_record)

    manifest = _manifest_payload(
        output_path=output_path,
        paths=paths,
        plan=plan,
        result=result,
        registry_output_path=registry_output_path,
    )
    _write_json_exclusive(
        paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        promotion_id=promotion_id,
        promoted=promoted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        next_allowed_action=next_allowed_action,
        registry_output_path=registry_output_path,
    )
    _write_json_exclusive(
        paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        artifact_index_manifest,
    )

    payload = _launcher_payload(
        output_path=output_path,
        paths=paths,
        result=result,
        registry_output_path=registry_output_path,
    )
    return AdmissionGatedLocalAdapterRegistryPromotionResult(
        admission_gate_decision_path=source_path,
        output_dir=output_path,
        promotion_id=promotion_id,
        plan_path=paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE],
        result_path=paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE],
        manifest_path=paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE
        ],
        summary_path=paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE
        ],
        checklist_path=paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        registry_output_path=registry_output_path,
        complete=promoted,
        promoted=promoted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
    *,
    output_path: Path,
    promotion_id: str,
    registry_output_path: Path | None,
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink() or not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    if not _non_empty_text(promotion_id):
        reasons.append("promotion_id_missing")
    output_candidates = [output_path / file_name for file_name in _OUTPUT_FILES]
    if registry_output_path is not None:
        if registry_output_path.is_symlink():
            reasons.append("registry_output_is_symlink")
        if not _path_is_inside(registry_output_path, output_path):
            reasons.append("registry_output_outside_output_dir")
        elif not registry_output_path.parent.exists() or not registry_output_path.parent.is_dir():
            reasons.append("registry_output_outside_output_dir")
        output_candidates.append(registry_output_path)
    for candidate in output_candidates:
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return _dedupe_strings(reasons)


def _read_source_decision(source_path: Path) -> tuple[dict[str, object], list[str]]:
    reasons: list[str] = []
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    if not source_path.exists():
        reasons.append("gate_decision_path_missing")
        return {}, _dedupe_strings(reasons)
    if source_path.is_symlink():
        reasons.append("gate_decision_path_is_symlink")
        return {}, _dedupe_strings(reasons)
    if not source_path.is_file():
        reasons.append("gate_decision_path_missing")
        return {}, _dedupe_strings(reasons)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("gate_decision_not_json_object")
        return {}, _dedupe_strings(reasons)
    if not isinstance(payload, dict):
        reasons.append("gate_decision_not_json_object")
        return {}, _dedupe_strings(reasons)
    reasons.extend(_discoverable_source_hash_rejection_reasons(source_path))
    return payload, _dedupe_strings(reasons)


def _review_attestation_rejection_reasons(value: str | None) -> list[str]:
    if not _non_empty_text(value):
        return ["review_attestation_missing"]
    if value != ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_REVIEW_ATTESTATION:
        return ["review_attestation_mismatch"]
    return []


def _source_decision_rejection_reasons(
    source_path: Path,
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if payload.get("decision_type") != _SOURCE_DECISION_TYPE:
        reasons.append("gate_decision_type_mismatch")
    if payload.get("admission_gate_result") != "pass":
        reasons.append("gate_decision_not_passed")
    if payload.get("gate_status") != _SOURCE_ADMITTED_STATUS:
        reasons.append("gate_status_not_admitted")
    if payload.get("gate_decision") != _SOURCE_ADMIT_DECISION:
        reasons.append("gate_decision_not_local_fixture_admit")
    if payload.get("local_fixture_admission_granted") is not True:
        reasons.append("local_fixture_admission_not_granted")
    if payload.get("production_admission_granted") is not False:
        reasons.append("production_admission_claimed")
    if payload.get("live_website_admission_granted") is not False:
        reasons.append("live_website_admission_claimed")
    if payload.get("general_browser_automation_admission_granted") is not False:
        reasons.append("general_browser_admission_claimed")
    if any(payload.get(field_name) is not False for field_name in _FORBIDDEN_ADMISSION_FIELDS):
        reasons.append("forbidden_admission_claimed")

    if payload.get("aggregation_evidence_supplied") is not True:
        reasons.append("aggregation_evidence_missing")
    if payload.get("aggregation_evidence_required") is not True:
        reasons.append("aggregation_evidence_not_required")
    if payload.get("aggregation_result_valid") is not True:
        reasons.append("aggregation_result_not_valid")
    if payload.get("local_fixture_aggregation_bound_to_admission_gate") is not True:
        reasons.append("aggregation_not_bound_to_gate")
    if _int_or_none(payload.get("aggregation_suite_run_count_evaluated")) is None:
        reasons.append("aggregation_suite_run_threshold_not_satisfied")
    elif int(payload["aggregation_suite_run_count_evaluated"]) < 1:
        reasons.append("aggregation_suite_run_threshold_not_satisfied")
    if (
        _int_or_zero(payload.get("aggregation_suite_run_count_failed")) > 0
        or _int_or_zero(payload.get("aggregation_suite_run_count_rejected")) > 0
    ):
        reasons.append("aggregation_failed_or_rejected_runs_present")
    if _int_or_none(payload.get("aggregation_pass_rate_bps")) != 10000:
        reasons.append("aggregation_pass_rate_not_perfect")
    if _int_or_none(payload.get("aggregation_flaky_rate_bps")) != 0:
        reasons.append("aggregation_flaky_rate_nonzero")
    if payload.get("aggregation_regression_detected") is not False:
        reasons.append("aggregation_regression_detected")
    if payload.get("aggregation_stale_evidence_detected") is not False:
        reasons.append("aggregation_stale_evidence_detected")
    if payload.get("aggregation_missing_coverage_detected") is not False:
        reasons.append("aggregation_missing_coverage_detected")
    if payload.get("aggregation_hashes_verified_all") is not True:
        reasons.append("aggregation_hashes_not_verified")
    if payload.get("aggregation_boundaries_false_all") is not True:
        reasons.append("aggregation_boundaries_not_false")

    if payload.get("regression_evidence_required") is not True:
        reasons.append("regression_evidence_not_required")
    if payload.get("regression_evidence_present") is not True:
        reasons.append("regression_evidence_missing")
    if payload.get("regression_scenario_coverage_complete") is not True:
        reasons.append("regression_scenario_coverage_incomplete")

    if payload.get("artifact_hashes_verified") is not True:
        reasons.append("artifact_hashes_not_verified")
    if (
        payload.get("candidate_repo_files_indexed") is not False
        or payload.get("external_candidate_artifacts_indexed") is not False
    ):
        reasons.append("candidate_artifacts_present")
    if payload.get("embedded_fixture_url_scheme") != "file":
        reasons.append("embedded_fixture_scheme_not_file")
    if _int_or_none(payload.get("embedded_non_local_request_count")) != 0:
        reasons.append("embedded_non_local_request_count_not_zero")
    if payload.get("required_human_review") is not True:
        reasons.append("human_review_not_required")
    if payload.get("required_human_approval") is not True:
        reasons.append("human_approval_not_required")
    if payload.get("security_review_required") is not True:
        reasons.append("security_review_not_required")
    if payload.get("sandbox_review_required") is not True:
        reasons.append("sandbox_review_not_required")
    if payload.get("production_review_required") is not True:
        reasons.append("production_review_not_required")
    if any(payload.get(field_name) is not False for field_name in _PERFORMED_FALSE_FIELDS):
        reasons.append("performed_forbidden_action")
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    return _dedupe_strings(reasons)


def _discoverable_source_hash_rejection_reasons(source_path: Path) -> list[str]:
    reasons: list[str] = []
    root = source_path.parent
    manifest_path = root / _SOURCE_MANIFEST_FILE
    if manifest_path.exists() or manifest_path.is_symlink():
        manifest, ok = _read_json_object_if_regular(manifest_path)
        if not ok or not _source_manifest_hashes_verified(manifest, source_path, root):
            reasons.append("source_manifest_hash_mismatch")
    artifact_index_path = root / _SOURCE_ARTIFACT_INDEX_FILE
    if artifact_index_path.exists() or artifact_index_path.is_symlink():
        artifact_index, ok = _read_json_object_if_regular(artifact_index_path)
        if not ok or not _source_artifact_index_hashes_verified(artifact_index, root):
            reasons.append("source_artifact_index_hash_mismatch")
    index_manifest_path = root / _SOURCE_ARTIFACT_INDEX_MANIFEST_FILE
    if index_manifest_path.exists() or index_manifest_path.is_symlink():
        index_manifest, ok = _read_json_object_if_regular(index_manifest_path)
        if not ok or not _source_artifact_index_manifest_verified(
            index_manifest,
            artifact_index_path,
            root,
        ):
            reasons.append("source_artifact_index_hash_mismatch")
    return _dedupe_strings(reasons)


def _source_manifest_hashes_verified(
    manifest: dict[str, object],
    source_path: Path,
    root: Path,
) -> bool:
    decision_path_value = manifest.get("decision_path")
    decision_sha256 = manifest.get("decision_sha256")
    if not isinstance(decision_path_value, str) or not isinstance(decision_sha256, str):
        return False
    decision_path = _path_from_value(decision_path_value, root)
    if decision_path.resolve(strict=False) != source_path.resolve(strict=False):
        return False
    if not _regular_file(decision_path) or sha256_file(decision_path) != decision_sha256:
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


def _source_artifact_index_hashes_verified(
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


def _source_artifact_index_manifest_verified(
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
    output_path: Path,
    paths: dict[str, Path],
    promotion_id: str,
    review_attestation: str | None,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    registry_output_path: Path | None,
    source_sha256: str | None,
    source_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "plan_type": _PLAN_TYPE,
        "promotion_type": _PROMOTION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_adapter_id": _PROMOTION_ADAPTER_ID,
        "promotion_capability": _PROMOTION_CAPABILITY,
        "promotion_id": promotion_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else _sha256_text(review_attestation)
        ),
        "source_gate_decision_path": source_path.as_posix(),
        "source_gate_decision_sha256": source_sha256,
        "source_gate_decision_type": source_payload.get("decision_type"),
        "output_dir": output_path.as_posix(),
        "promotion_plan_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE
        ].as_posix(),
        "promotion_result_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE
        ].as_posix(),
        "promotion_manifest_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE
        ].as_posix(),
        "promotion_summary_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE
        ].as_posix(),
        "promotion_checklist_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "registry_output_path": (
            None if registry_output_path is None else registry_output_path.as_posix()
        ),
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "local_fixture_only": True,
        "human_review_required": True,
        "required_human_approval": True,
        "aggregation_bound": True,
        "non_production": True,
        "no_live_website": True,
        "no_general_browser_automation": True,
        "no_autonomy": True,
        "next_allowed_action": "validate_gate_decision_before_local_registry_record",
        **_promotion_boundary_fields(promoted=False, source_local_fixture=False),
    }


def _registry_record_payload(
    *,
    source_path: Path,
    source_sha256: str | None,
    source_payload: dict[str, object],
    promotion_id: str,
    promoted: bool,
) -> dict[str, object]:
    return {
        "registry_entry_type": _REGISTRY_ENTRY_TYPE,
        "registry_entry_status": _REGISTRY_ENTRY_STATUS if promoted else "rejected",
        "promotion_type": _PROMOTION_TYPE,
        "promotion_id": promotion_id,
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "adapter_capability": _PROMOTED_ADAPTER_CAPABILITY,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_gate_decision_path": source_path.as_posix(),
        "source_gate_decision_sha256": source_sha256,
        "source_gate_decision_type": source_payload.get("decision_type"),
        "source_gate_passed": promoted,
        "allowed_scope": "local_fixture_only",
        "denied_scope": list(ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE),
        "local_fixture_only": True,
        "human_review_required": True,
        "required_human_approval": True,
        "aggregation_bound": promoted,
        "regression_bound": promoted,
        "non_production": True,
        "production_adapter": False,
        "registry_promotion_granted": promoted,
        "production_promotion_granted": False,
        "next_allowed_action": _NEXT_ALLOWED_ACTION if promoted else _FIX_SOURCE_NEXT_ACTION,
        **_promotion_boundary_fields(
            promoted=promoted,
            source_local_fixture=promoted,
        ),
    }


def _promotion_result_payload(
    *,
    source_path: Path,
    source_sha256: str | None,
    source_payload: dict[str, object],
    promotion_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    registry_output_path: Path | None,
    registry_record: dict[str, object],
    promoted: bool,
    promotion_status: str,
    promotion_decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    boundary_fields = _promotion_boundary_fields(
        promoted=promoted,
        source_local_fixture=promoted,
    )
    result = {
        "promotion_type": _PROMOTION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_adapter_id": _PROMOTION_ADAPTER_ID,
        "promotion_capability": _PROMOTION_CAPABILITY,
        "promotion_id": promotion_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "source_gate_decision_path": source_path.as_posix(),
        "source_gate_decision_sha256": source_sha256,
        "source_gate_decision_type": source_payload.get("decision_type"),
        "source_gate_passed": promoted,
        "aggregation_bound": promoted,
        "regression_bound": promoted,
        "local_fixture_only": True,
        "human_review_required": True,
        "required_human_approval": True,
        "non_production": True,
        "production_adapter": False,
        "registry_promotion_granted": promoted,
        "promotion_status": promotion_status,
        "promotion_decision": promotion_decision,
        "next_allowed_action": next_allowed_action,
        "complete": promoted,
        "promoted": promoted,
        "rejected": not promoted,
        "rejection_reasons": list(rejection_reasons),
        "registry_output_path": (
            None if registry_output_path is None else registry_output_path.as_posix()
        ),
        "registry_record": registry_record,
        "registry_entry_type": registry_record["registry_entry_type"],
        "registry_entry_status": registry_record["registry_entry_status"],
        "allowed_scope": registry_record["allowed_scope"],
        "denied_scope": registry_record["denied_scope"],
        "required_human_review": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "production_review_required": True,
        "no_live_website": True,
        "no_general_browser_automation": True,
        "no_autonomy": True,
        **boundary_fields,
    }
    return result


def _promotion_boundary_fields(
    *,
    promoted: bool,
    source_local_fixture: bool,
) -> dict[str, object]:
    fields = {
        "local_fixture_admission_granted": source_local_fixture,
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
        "registry_promotion_granted": promoted,
    }
    fields.update({field_name: False for field_name in _PERFORMED_FALSE_FIELDS})
    fields["adapter_registered"] = False
    fields["auto_adoption_performed"] = False
    fields["autonomous_execution_performed"] = False
    return fields


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    plan: dict[str, object],
    result: dict[str, object],
    registry_output_path: Path | None,
) -> dict[str, object]:
    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "promotion_type": _PROMOTION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_adapter_id": _PROMOTION_ADAPTER_ID,
        "promotion_capability": _PROMOTION_CAPABILITY,
        "promotion_id": result["promotion_id"],
        "job_dir": output_path.as_posix(),
        "plan_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE
        ].as_posix(),
        "plan_sha256": sha256_file(
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE]
        ),
        "result_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE]
        ),
        "summary_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE]
        ),
        "source_gate_decision_path": result["source_gate_decision_path"],
        "source_gate_decision_sha256": result["source_gate_decision_sha256"],
        "source_gate_decision_type": result["source_gate_decision_type"],
        "source_gate_passed": result["source_gate_passed"],
        "promotion_status": result["promotion_status"],
        "promotion_decision": result["promotion_decision"],
        "registry_promotion_granted": result["registry_promotion_granted"],
        "production_promotion_granted": False,
        "next_allowed_action": result["next_allowed_action"],
        "registry_output_path": (
            None if registry_output_path is None else registry_output_path.as_posix()
        ),
        "required_human_review": True,
        "required_human_approval": True,
        **_promotion_boundary_fields(
            promoted=bool(result["registry_promotion_granted"]),
            source_local_fixture=bool(result["source_gate_passed"]),
        ),
    }
    if registry_output_path is not None:
        manifest["registry_output_sha256"] = sha256_file(registry_output_path)
    return manifest


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    promotion_id: str,
    promoted: bool,
    promotion_status: str,
    promotion_decision: str,
    next_allowed_action: str,
    registry_output_path: Path | None,
) -> dict[str, object]:
    roles = [
        (
            "admission_gated_local_adapter_registry_promotion_plan",
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE],
        ),
        (
            "admission_gated_local_adapter_registry_promotion_result",
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE],
        ),
        (
            "admission_gated_local_adapter_registry_promotion_manifest",
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE],
        ),
        (
            "admission_gated_local_adapter_registry_promotion_summary",
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE],
        ),
        (
            "admission_gated_local_adapter_registry_promotion_checklist",
            paths[ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE],
        ),
    ]
    if registry_output_path is not None:
        roles.append(("local_fixture_only_adapter_registry_entry", registry_output_path))
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "promotion_type": _PROMOTION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_adapter_id": _PROMOTION_ADAPTER_ID,
        "promotion_capability": _PROMOTION_CAPABILITY,
        "promotion_id": promotion_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "promotion_output_artifacts_only",
        "promotion_status": promotion_status,
        "promotion_decision": promotion_decision,
        "registry_promotion_granted": promoted,
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
        **_promotion_boundary_fields(promoted=promoted, source_local_fixture=promoted),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[
        ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE
    ]
    entries = list(artifact_index["entries"])
    promoted = bool(artifact_index["registry_promotion_granted"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "promotion_type": _PROMOTION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_adapter_id": _PROMOTION_ADAPTER_ID,
        "promotion_capability": _PROMOTION_CAPABILITY,
        "promotion_id": artifact_index["promotion_id"],
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
        "promotion_status": artifact_index["promotion_status"],
        "promotion_decision": artifact_index["promotion_decision"],
        "registry_promotion_granted": promoted,
        "production_promotion_granted": False,
        "next_allowed_action": artifact_index["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_promotion_boundary_fields(promoted=promoted, source_local_fixture=promoted),
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
    registry_output_path: Path | None,
) -> dict[str, object]:
    payload = {
        "workflow": "admission_gated_local_adapter_registry_promotion_workflow",
        "complete": bool(result["complete"]),
        "promoted": bool(result["promoted"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE
        ].as_posix(),
        "admission_gated_local_adapter_registry_promotion_plan_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_PLAN_FILE
        ].as_posix(),
        "admission_gated_local_adapter_registry_promotion_result_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_RESULT_FILE
        ].as_posix(),
        "admission_gated_local_adapter_registry_promotion_manifest_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_MANIFEST_FILE
        ].as_posix(),
        "admission_gated_local_adapter_registry_promotion_summary_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_SUMMARY_FILE
        ].as_posix(),
        "admission_gated_local_adapter_registry_promotion_checklist_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "registry_output_path": (
            None if registry_output_path is None else registry_output_path.as_posix()
        ),
        "required_human_approval": True,
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    source_path: Path,
    output_path: Path,
    promotion_id: str,
    registry_output_path: Path | None,
    rejection_reasons: list[str],
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
) -> AdmissionGatedLocalAdapterRegistryPromotionResult:
    payload = {
        "workflow": "admission_gated_local_adapter_registry_promotion_workflow",
        "complete": False,
        "promoted": False,
        "promotion_type": _PROMOTION_TYPE,
        "promotion_id": promotion_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "source_gate_decision_path": source_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "registry_output_path": (
            None if registry_output_path is None else registry_output_path.as_posix()
        ),
        "promotion_status": _REJECTED_STATUS,
        "promotion_decision": _REJECTED_DECISION,
        "rejection_reasons": list(rejection_reasons),
        "required_human_approval": True,
        **_promotion_boundary_fields(promoted=False, source_local_fixture=False),
    }
    return AdmissionGatedLocalAdapterRegistryPromotionResult(
        admission_gate_decision_path=source_path,
        output_dir=output_path,
        promotion_id=promotion_id,
        plan_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        registry_output_path=registry_output_path,
        complete=False,
        promoted=False,
        promotion_status=_REJECTED_STATUS,
        promotion_decision=_REJECTED_DECISION,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _summary_markdown(result: dict[str, object]) -> str:
    reasons = result.get("rejection_reasons")
    reason_lines = ""
    if isinstance(reasons, list) and reasons:
        reason_lines = "\n".join("- " + str(reason) for reason in reasons)
    else:
        reason_lines = "- none"
    return "\n".join(
        [
            "# Admission-Gated Local Adapter Registry Promotion",
            "",
            f"Promotion ID: {result['promotion_id']}",
            f"Status: {result['promotion_status']}",
            f"Decision: {result['promotion_decision']}",
            f"Source gate decision: {result['source_gate_decision_path']}",
            f"Registry promotion granted: {str(result['registry_promotion_granted']).lower()}",
            f"Production promotion granted: {str(result['production_promotion_granted']).lower()}",
            "",
            "Allowed state: local_fixture_only, human_review_required, aggregation_bound, non_production.",
            "",
            "Rejected reasons:",
            reason_lines,
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["registry_promotion_granted"] else "[ ]"
    return "\n".join(
        [
            "# Local Adapter Registry Promotion Checklist",
            "",
            f"- {checked} Source #427 gate decision passed.",
            f"- {checked} Aggregation and regression evidence remain bound.",
            f"- {checked} Registry entry is local-fixture-only.",
            "- [x] Production remains denied.",
            "- [x] Live website automation remains denied.",
            "- [x] General browser automation remains denied.",
            "- [x] Arbitrary navigation remains denied.",
            "- [x] Account, scraping, bypass, captcha, credential, and cookie flows remain denied.",
            "- [x] Package installation, browser download, npm, and npx remain denied.",
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


def _normalized_registry_output(
    registry_output: Path | None,
    output_path: Path,
) -> Path | None:
    if registry_output is None:
        return None
    path = Path(registry_output)
    if path.is_absolute():
        return path
    return output_path / path


def _source_sha256(source_path: Path) -> str | None:
    if _regular_file(source_path):
        return sha256_file(source_path)
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


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _int_or_zero(value: object) -> int:
    parsed = _int_or_none(value)
    return 0 if parsed is None else parsed


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))
