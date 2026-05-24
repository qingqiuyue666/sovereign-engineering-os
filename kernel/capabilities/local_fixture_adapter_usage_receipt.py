"""Local-fixture adapter usage receipt evidence.

This module reads an existing #428 local-fixture registry promotion result and
writes one bounded usage receipt. It is metadata-only evidence: no adapter
execution, Playwright execution, browser opening, network access, package
installation, candidate repository access, or autonomous action is performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from urllib.parse import unquote, urlsplit

from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS",
    "LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS",
    "LocalFixtureAdapterUsageReceiptResult",
    "run_local_fixture_adapter_usage_receipt",
    "run_local_fixture_adapter_usage_receipt_launcher",
]


LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE = (
    "local_fixture_adapter_usage_receipt_plan.json"
)
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE = (
    "local_fixture_adapter_usage_receipt_result.json"
)
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE = (
    "local_fixture_adapter_usage_receipt_manifest.json"
)
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE = (
    "local_fixture_adapter_usage_receipt_summary.md"
)
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE = (
    "local_fixture_adapter_usage_receipt_checklist.md"
)
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE = "artifact_index.json"
LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_ONLY_REGISTRY_PROMOTION_FOR_ONE_USAGE_"
    "NO_PRODUCTION_NO_LIVE_WEBSITES_NO_AUTONOMY"
)

LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS = (
    "production_admission_granted",
    "live_website_admission_granted",
    "general_browser_automation_admission_granted",
    "arbitrary_url_navigation_admission_granted",
    "account_workflow_admission_granted",
    "login_workflow_admission_granted",
    "registration_workflow_admission_granted",
    "scraping_admission_granted",
    "bypass_admission_granted",
    "captcha_workflow_admission_granted",
    "credential_input_admission_granted",
    "cookie_access_admission_granted",
    "external_network_admission_granted",
    "package_install_admission_granted",
    "browser_download_admission_granted",
    "npm_admission_granted",
    "npx_admission_granted",
    "candidate_repo_access_admission_granted",
    "candidate_code_import_admission_granted",
    "candidate_code_execution_admission_granted",
    "arbitrary_command_admission_granted",
    "autonomous_execution_admission_granted",
)

LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS = (
    "live_website_automation_performed",
    "arbitrary_url_navigation_performed",
    "user_supplied_url_used",
    "account_workflow_performed",
    "login_workflow_performed",
    "registration_workflow_performed",
    "scraping_performed",
    "bypass_performed",
    "captcha_workflow_performed",
    "credential_input_performed",
    "cookie_access_performed",
    "external_network_performed",
    "package_install_performed",
    "browser_download_performed",
    "npm_performed",
    "npx_performed",
    "git_clone_performed",
    "git_command_performed",
    "dependency_installation_performed",
    "third_party_code_execution_performed",
    "candidate_repo_access_performed",
    "candidate_code_imported",
    "candidate_code_execution_performed",
    "candidate_repo_mutation_performed",
    "arbitrary_command_execution_performed",
    "model_api_called",
    "secret_access_performed",
    "adapter_registered",
    "auto_adoption_performed",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_probe_performed",
    "fixture_content_execution_performed",
)

_RECEIPT_TYPE = "local_fixture_adapter_usage_receipt_v1"
_PLAN_TYPE = "local_fixture_adapter_usage_receipt_plan_v1"
_MANIFEST_TYPE = "local_fixture_adapter_usage_receipt_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_adapter_usage_receipt_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_adapter_usage_receipt_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_local_fixture_usage_receipt_record"
_EXECUTION_CAPABILITY = "local_fixture_adapter_usage_receipt_only"
_RECEIPT_ADAPTER_ID = "local_fixture_adapter_usage_receipt"
_RECEIPT_CAPABILITY = "launch_local_fixture_adapter_usage_receipt"
_PROMOTION_TYPE = "admission_gated_local_adapter_registry_promotion_v1"
_PROMOTION_COMPLETED_STATUS = (
    "admission_gated_local_adapter_registry_promotion_completed"
)
_PROMOTION_COMPLETED_DECISION = "promote_local_fixture_only_adapter_registration"
_SOURCE_DECISION_TYPE = "local_fixture_playwright_adapter_admission_gate_decision_v1"
_PROMOTED_ADAPTER_ID = "bounded_playwright_worker_adapter_draft"
_CANDIDATE_ID = "github-candidate-microsoft-playwright-v1"
_REPO_FULL_NAME = "microsoft/playwright"
_REGISTRY_ENTRY_TYPE = "local_fixture_only_adapter_registry_entry_v1"
_REGISTRY_ENTRY_STATUS = "enabled_local_fixture_only"
_ALLOWED_SCOPE = "local_fixture_only"
_COMPLETED_STATUS = "local_fixture_adapter_usage_receipt_completed"
_REJECTED_STATUS = "local_fixture_adapter_usage_receipt_rejected"
_COMPLETED_DECISION = "record_one_local_fixture_adapter_usage_receipt"
_REJECTED_DECISION = "reject_local_fixture_adapter_usage_receipt"
_NEXT_ALLOWED_ACTION = "human_review_local_fixture_usage_receipt_before_any_execution"
_FIX_PROMOTION_NEXT_ACTION = "fix_local_fixture_registry_promotion_and_retry"
_SOURCE_MANIFEST_FILE = "admission_gated_local_adapter_registry_promotion_manifest.json"
_SOURCE_ARTIFACT_INDEX_FILE = "artifact_index.json"
_SOURCE_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_FORBIDDEN_REFERENCE_SCHEMES = frozenset(
    (
        "http",
        "https",
        "ws",
        "wss",
        "ftp",
        "data",
        "javascript",
        "about",
        "chrome",
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
_OUTPUT_FILES = (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE,
)


@dataclass(frozen=True)
class LocalFixtureAdapterUsageReceiptResult:
    promotion_result_path: Path
    output_dir: Path
    usage_receipt_id: str
    plan_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    registry_entry_path: Path | None
    complete: bool
    usage_receipt_granted: bool
    promotion_status: str
    promotion_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_adapter_usage_receipt_launcher(
    promotion_result: Path,
    output_dir: Path,
    usage_receipt_id: str,
    *,
    review_attestation: str | None = None,
    local_fixture_reference: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    registry_entry: Path | None = None,
) -> LocalFixtureAdapterUsageReceiptResult:
    """Launcher-oriented wrapper for the metadata-only usage receipt."""

    return run_local_fixture_adapter_usage_receipt(
        promotion_result,
        output_dir,
        usage_receipt_id,
        review_attestation=review_attestation,
        local_fixture_reference=local_fixture_reference,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_entry=registry_entry,
    )


def run_local_fixture_adapter_usage_receipt(
    promotion_result: Path,
    output_dir: Path,
    usage_receipt_id: str,
    *,
    review_attestation: str | None = None,
    local_fixture_reference: str | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
    registry_entry: Path | None = None,
) -> LocalFixtureAdapterUsageReceiptResult:
    """Validate a #428 promotion result and write one local-fixture receipt."""

    source_path = Path(promotion_result)
    output_path = Path(output_dir)
    registry_entry_path = _normalized_optional_path(registry_entry, output_path)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(output_path, usage_receipt_id, paths)
    if preflight_reasons:
        return _unwritten_result(
            source_path=source_path,
            output_path=output_path,
            usage_receipt_id=usage_receipt_id,
            registry_entry_path=registry_entry_path,
            rejection_reasons=preflight_reasons,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            local_fixture_reference=local_fixture_reference,
        )

    promotion_payload, promotion_read_reasons = _read_promotion_result(source_path)
    promotion_validation_reasons = list(promotion_read_reasons)
    if not promotion_validation_reasons:
        promotion_validation_reasons.extend(
            _promotion_result_rejection_reasons(source_path, promotion_payload)
        )
    rejection_reasons = list(promotion_validation_reasons)
    registry_entry_payload, registry_entry_reasons = _read_registry_entry(
        registry_entry_path,
        output_path,
        source_path,
    )
    registry_entry_validation_reasons = list(registry_entry_reasons)
    if registry_entry_payload:
        registry_entry_validation_reasons.extend(
            _registry_entry_rejection_reasons(registry_entry_payload, promotion_payload)
        )
    rejection_reasons.extend(registry_entry_validation_reasons)
    fixture_metadata, fixture_reasons = _local_fixture_reference_metadata(
        local_fixture_reference,
        output_path,
    )
    rejection_reasons.extend(fixture_reasons)
    rejection_reasons.extend(_review_attestation_rejection_reasons(review_attestation))
    rejection_reasons = _dedupe_strings(rejection_reasons)

    usage_granted = not rejection_reasons
    promotion_status = _COMPLETED_STATUS if usage_granted else _REJECTED_STATUS
    promotion_decision = _COMPLETED_DECISION if usage_granted else _REJECTED_DECISION
    next_allowed_action = _NEXT_ALLOWED_ACTION if usage_granted else _FIX_PROMOTION_NEXT_ACTION
    promotion_sha256 = _source_sha256(source_path)
    registry_entry_sha256 = _source_sha256(registry_entry_path)

    plan = _plan_payload(
        source_path=source_path,
        promotion_sha256=promotion_sha256,
        promotion_payload=promotion_payload,
        output_path=output_path,
        paths=paths,
        usage_receipt_id=usage_receipt_id,
        review_attestation=review_attestation,
        local_fixture_reference=local_fixture_reference,
        fixture_metadata=fixture_metadata,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_entry_path=registry_entry_path,
        registry_entry_sha256=registry_entry_sha256,
    )
    result = _receipt_result_payload(
        source_path=source_path,
        promotion_sha256=promotion_sha256,
        promotion_payload=promotion_payload,
        output_path=output_path,
        usage_receipt_id=usage_receipt_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        registry_entry_path=registry_entry_path,
        registry_entry_sha256=registry_entry_sha256,
        registry_entry_payload=registry_entry_payload,
        fixture_metadata=fixture_metadata,
        promotion_validated=not promotion_validation_reasons,
        registry_entry_validated=(
            registry_entry_path is not None and not registry_entry_validation_reasons
        ),
        usage_granted=usage_granted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )

    _write_json_exclusive(paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE], plan)
    _write_json_exclusive(paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE], result)
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE],
        _summary_markdown(result),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE],
        _checklist_markdown(result),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=result)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        usage_receipt_id=usage_receipt_id,
        usage_granted=usage_granted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=result)
    return LocalFixtureAdapterUsageReceiptResult(
        promotion_result_path=source_path,
        output_dir=output_path,
        usage_receipt_id=usage_receipt_id,
        plan_path=paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE],
        result_path=paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE],
        manifest_path=paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE],
        summary_path=paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE],
        checklist_path=paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE],
        artifact_index_path=paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        registry_entry_path=registry_entry_path,
        complete=usage_granted,
        usage_receipt_granted=usage_granted,
        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
    output_path: Path,
    usage_receipt_id: str,
    paths: dict[str, Path],
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink() or not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    if not _non_empty_text(usage_receipt_id):
        reasons.append("usage_receipt_id_missing")
    for candidate in paths.values():
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return _dedupe_strings(reasons)


def _read_promotion_result(source_path: Path) -> tuple[dict[str, object], list[str]]:
    reasons: list[str] = []
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    if not source_path.exists():
        reasons.append("promotion_result_path_missing")
        return {}, _dedupe_strings(reasons)
    if source_path.is_symlink():
        reasons.append("promotion_result_path_is_symlink")
        return {}, _dedupe_strings(reasons)
    if not source_path.is_file():
        reasons.append("promotion_result_path_missing")
        return {}, _dedupe_strings(reasons)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("promotion_result_not_json_object")
        return {}, _dedupe_strings(reasons)
    if not isinstance(payload, dict):
        reasons.append("promotion_result_not_json_object")
        return {}, _dedupe_strings(reasons)
    reasons.extend(_discoverable_promotion_hash_rejection_reasons(source_path))
    return payload, _dedupe_strings(reasons)


def _promotion_result_rejection_reasons(
    source_path: Path,
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if payload.get("promotion_type") != _PROMOTION_TYPE:
        reasons.append("promotion_type_mismatch")
    if payload.get("promotion_status") != _PROMOTION_COMPLETED_STATUS:
        reasons.append("promotion_status_not_completed")
    if payload.get("promotion_decision") != _PROMOTION_COMPLETED_DECISION:
        reasons.append("promotion_decision_mismatch")
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
        for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
    ):
        reasons.append("forbidden_admission_claimed")
    if any(
        payload.get(field_name) is not False
        for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
    ):
        reasons.append("performed_forbidden_action")
    registry_record = payload.get("registry_record")
    if not isinstance(registry_record, dict) or _registry_record_invalid(
        registry_record,
        payload,
    ):
        reasons.append("registry_record_missing_or_invalid")
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    return _dedupe_strings(reasons)


def _registry_record_invalid(
    record: dict[str, object],
    promotion_payload: dict[str, object],
) -> bool:
    if record.get("registry_entry_type") != _REGISTRY_ENTRY_TYPE:
        return True
    if record.get("registry_entry_status") != _REGISTRY_ENTRY_STATUS:
        return True
    if record.get("allowed_scope") != _ALLOWED_SCOPE:
        return True
    if record.get("adapter_id") != _PROMOTED_ADAPTER_ID:
        return True
    if record.get("candidate_id") != _CANDIDATE_ID:
        return True
    if record.get("repo_full_name") != _REPO_FULL_NAME:
        return True
    if record.get("registry_promotion_granted") is not True:
        return True
    if record.get("production_promotion_granted") is not False:
        return True
    if record.get("production_adapter") is not False:
        return True
    if record.get("source_gate_decision_sha256") != promotion_payload.get(
        "source_gate_decision_sha256"
    ):
        return True
    denied_scope = record.get("denied_scope")
    if not isinstance(denied_scope, list) or not set(
        ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE
    ).issubset(set(str(item) for item in denied_scope)):
        return True
    return False


def _read_registry_entry(
    registry_entry_path: Path | None,
    output_path: Path,
    promotion_path: Path,
) -> tuple[dict[str, object], list[str]]:
    if registry_entry_path is None:
        return {}, []
    reasons: list[str] = []
    if not registry_entry_path.exists():
        reasons.append("registry_entry_path_missing")
        return {}, reasons
    if registry_entry_path.is_symlink():
        reasons.append("registry_entry_path_is_symlink")
        return {}, reasons
    if not registry_entry_path.is_file():
        reasons.append("registry_entry_path_missing")
        return {}, reasons
    if not (
        _path_is_inside(registry_entry_path, output_path)
        or _path_is_inside(registry_entry_path, promotion_path.parent)
    ):
        reasons.append("registry_entry_identity_mismatch")
    try:
        payload = json.loads(registry_entry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("registry_entry_not_json_object")
        return {}, _dedupe_strings(reasons)
    if not isinstance(payload, dict):
        reasons.append("registry_entry_not_json_object")
        return {}, _dedupe_strings(reasons)
    return payload, _dedupe_strings(reasons)


def _registry_entry_rejection_reasons(
    registry_entry: dict[str, object],
    promotion_payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if (
        registry_entry.get("registry_entry_type") != _REGISTRY_ENTRY_TYPE
        or registry_entry.get("registry_entry_status") != _REGISTRY_ENTRY_STATUS
    ):
        reasons.append("registry_entry_identity_mismatch")
    if registry_entry.get("allowed_scope") != _ALLOWED_SCOPE:
        reasons.append("registry_entry_scope_invalid")
    if (
        registry_entry.get("adapter_id") != _PROMOTED_ADAPTER_ID
        or registry_entry.get("candidate_id") != _CANDIDATE_ID
        or registry_entry.get("repo_full_name") != _REPO_FULL_NAME
        or registry_entry.get("registry_promotion_granted") is not True
        or registry_entry.get("production_promotion_granted") is not False
        or registry_entry.get("production_adapter") is not False
    ):
        reasons.append("registry_entry_identity_mismatch")
    embedded_record = promotion_payload.get("registry_record")
    if isinstance(embedded_record, dict):
        for field_name in (
            "registry_entry_type",
            "registry_entry_status",
            "adapter_id",
            "candidate_id",
            "repo_full_name",
            "allowed_scope",
            "registry_promotion_granted",
            "production_promotion_granted",
            "production_adapter",
        ):
            if registry_entry.get(field_name) != embedded_record.get(field_name):
                reasons.append("registry_entry_identity_mismatch")
                break
        for field_name in (
            "source_gate_decision_sha256",
            "source_gate_decision_type",
            "source_gate_passed",
            "aggregation_bound",
            "regression_bound",
            "local_fixture_only",
            "human_review_required",
            "required_human_approval",
            "non_production",
        ):
            if (
                field_name not in registry_entry
                or field_name not in embedded_record
                or registry_entry.get(field_name) != embedded_record.get(field_name)
            ):
                reasons.append("registry_entry_identity_mismatch")
                break
    for field_name in (
        "source_gate_decision_sha256",
        "source_gate_decision_type",
        "source_gate_passed",
        "aggregation_bound",
        "regression_bound",
        "local_fixture_only",
        "human_review_required",
        "required_human_approval",
        "non_production",
    ):
        if (
            field_name in promotion_payload
            and registry_entry.get(field_name) != promotion_payload.get(field_name)
        ):
            reasons.append("registry_entry_identity_mismatch")
            break
    denied_scope = registry_entry.get("denied_scope")
    if not isinstance(denied_scope, list) or not set(
        ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE
    ).issubset(set(str(item) for item in denied_scope)):
        reasons.append("registry_entry_denied_scope_incomplete")
    return _dedupe_strings(reasons)


def _local_fixture_reference_metadata(
    local_fixture_reference: str | None,
    output_path: Path,
) -> tuple[dict[str, object], list[str]]:
    metadata = _empty_fixture_metadata(local_fixture_reference)
    reasons: list[str] = []
    if not _non_empty_text(local_fixture_reference):
        reasons.append("local_fixture_reference_missing")
        return metadata, reasons
    reference = str(local_fixture_reference).strip()
    metadata["local_fixture_reference"] = reference
    scheme, fixture_path, reference_reasons = _fixture_path_from_reference(
        reference,
        output_path,
    )
    metadata["local_fixture_reference_scheme"] = scheme
    if fixture_path is None:
        reasons.extend(reference_reasons)
        return metadata, _dedupe_strings(reasons)
    metadata["local_fixture_path"] = fixture_path.as_posix()
    reasons.extend(reference_reasons)
    if not _path_is_inside(fixture_path, output_path):
        reasons.append("local_fixture_path_outside_allowed_root")
    if fixture_path.is_symlink():
        metadata["local_fixture_symlink_detected"] = True
        reasons.append("local_fixture_path_is_symlink")
    if _path_has_symlink_component(fixture_path, output_path):
        metadata["local_fixture_symlink_detected"] = True
        reasons.append("local_fixture_path_has_symlink_component")
    if not fixture_path.exists():
        reasons.append("local_fixture_path_missing")
    elif not fixture_path.is_file():
        reasons.append("local_fixture_path_not_regular_file")

    exists = fixture_path.exists()
    regular = exists and fixture_path.is_file() and not fixture_path.is_symlink()
    under_root = _path_is_inside(fixture_path, output_path)
    metadata["local_fixture_exists"] = exists
    metadata["local_fixture_regular_file"] = regular
    metadata["local_fixture_under_allowed_root"] = under_root
    metadata["local_fixture_symlink_detected"] = bool(
        metadata["local_fixture_symlink_detected"]
    )
    if regular and under_root and not metadata["local_fixture_symlink_detected"]:
        metadata["local_fixture_sha256"] = sha256_file(fixture_path)
    return metadata, _dedupe_strings(reasons)


def _fixture_path_from_reference(
    reference: str,
    output_path: Path,
) -> tuple[str | None, Path | None, list[str]]:
    reasons: list[str] = []
    parsed = urlsplit(reference)
    if parsed.scheme:
        scheme = parsed.scheme.lower()
        if scheme != "file":
            reasons.append("local_fixture_reference_forbidden_scheme")
            if scheme in _FORBIDDEN_REFERENCE_SCHEMES or "://" in reference:
                reasons.append("local_fixture_reference_looks_like_url")
            return scheme, None, _dedupe_strings(reasons)
        if parsed.netloc not in ("", "localhost"):
            reasons.append("local_fixture_reference_forbidden_scheme")
            return "file", None, _dedupe_strings(reasons)
        return "file", Path(unquote(parsed.path)), reasons
    if _looks_like_external_reference(reference):
        reasons.append("local_fixture_reference_looks_like_url")
        return None, None, reasons
    path = Path(reference)
    if path.is_absolute():
        return "file", path, reasons
    return "relative_path", output_path / path, reasons


def _empty_fixture_metadata(reference: str | None) -> dict[str, object]:
    return {
        "local_fixture_reference": reference,
        "local_fixture_reference_scheme": None,
        "local_fixture_path": None,
        "local_fixture_sha256": None,
        "local_fixture_exists": False,
        "local_fixture_regular_file": False,
        "local_fixture_symlink_detected": False,
        "local_fixture_under_allowed_root": False,
    }


def _review_attestation_rejection_reasons(value: str | None) -> list[str]:
    if not _non_empty_text(value):
        return ["review_attestation_missing"]
    if value != LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION:
        return ["review_attestation_mismatch"]
    return []


def _discoverable_promotion_hash_rejection_reasons(source_path: Path) -> list[str]:
    reasons: list[str] = []
    root = source_path.parent
    manifest_path = root / _SOURCE_MANIFEST_FILE
    if manifest_path.exists() or manifest_path.is_symlink():
        manifest, ok = _read_json_object_if_regular(manifest_path)
        if not ok or not _promotion_manifest_hashes_verified(
            manifest,
            source_path,
            root,
        ):
            reasons.append("promotion_manifest_hash_mismatch")
    artifact_index_path = root / _SOURCE_ARTIFACT_INDEX_FILE
    if artifact_index_path.exists() or artifact_index_path.is_symlink():
        artifact_index, ok = _read_json_object_if_regular(artifact_index_path)
        if not ok or not _promotion_artifact_index_hashes_verified(
            artifact_index,
            root,
        ):
            reasons.append("promotion_artifact_index_hash_mismatch")
    index_manifest_path = root / _SOURCE_ARTIFACT_INDEX_MANIFEST_FILE
    if index_manifest_path.exists() or index_manifest_path.is_symlink():
        index_manifest, ok = _read_json_object_if_regular(index_manifest_path)
        if not ok or not _promotion_artifact_index_manifest_verified(
            index_manifest,
            artifact_index_path,
            root,
        ):
            reasons.append("promotion_artifact_index_hash_mismatch")
    return _dedupe_strings(reasons)


def _promotion_manifest_hashes_verified(
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


def _promotion_artifact_index_hashes_verified(
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


def _promotion_artifact_index_manifest_verified(
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
    promotion_sha256: str | None,
    promotion_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    usage_receipt_id: str,
    review_attestation: str | None,
    local_fixture_reference: str | None,
    fixture_metadata: dict[str, object],
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    registry_entry_path: Path | None,
    registry_entry_sha256: str | None,
) -> dict[str, object]:
    return {
        "plan_type": _PLAN_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "usage_receipt_id": usage_receipt_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "review_attestation_present": _non_empty_text(review_attestation),
        "review_attestation_sha256": (
            None if review_attestation is None else _sha256_text(review_attestation)
        ),
        "promotion_result_path": source_path.as_posix(),
        "promotion_result_sha256": promotion_sha256,
        "promotion_type": promotion_payload.get("promotion_type"),
        "source_gate_decision_type": promotion_payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": promotion_payload.get(
            "source_gate_decision_sha256"
        ),
        "local_fixture_reference": local_fixture_reference,
        **fixture_metadata,
        "output_dir": output_path.as_posix(),
        "receipt_plan_path": paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE].as_posix(),
        "receipt_result_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE
        ].as_posix(),
        "receipt_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE
        ].as_posix(),
        "receipt_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "receipt_checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "registry_entry_path": (
            None if registry_entry_path is None else registry_entry_path.as_posix()
        ),
        "registry_entry_sha256": registry_entry_sha256,
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "local_fixture_only": True,
        "one_usage_receipt_only": True,
        "human_review_required": True,
        "required_human_approval": True,
        "aggregation_bound": True,
        "regression_bound": True,
        "non_production": True,
        "production_adapter": False,
        "next_allowed_action": "validate_local_fixture_promotion_before_receipt",
        **_receipt_boundary_fields(),
    }


def _receipt_result_payload(
    *,
    source_path: Path,
    promotion_sha256: str | None,
    promotion_payload: dict[str, object],
    output_path: Path,
    usage_receipt_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    registry_entry_path: Path | None,
    registry_entry_sha256: str | None,
    registry_entry_payload: dict[str, object],
    fixture_metadata: dict[str, object],
    promotion_validated: bool,
    registry_entry_validated: bool,
    usage_granted: bool,
    promotion_status: str,
    promotion_decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    result = {
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "usage_receipt_id": usage_receipt_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "adapter_id": _PROMOTED_ADAPTER_ID,
        "candidate_id": _CANDIDATE_ID,
        "repo_full_name": _REPO_FULL_NAME,
        "promotion_result_path": source_path.as_posix(),
        "promotion_result_sha256": promotion_sha256,
        "promotion_type": promotion_payload.get("promotion_type"),
        "source_gate_decision_type": promotion_payload.get("source_gate_decision_type"),
        "source_gate_decision_sha256": promotion_payload.get(
            "source_gate_decision_sha256"
        ),
        "source_gate_passed": promotion_payload.get("source_gate_passed") is True,
        "registry_promotion_granted": (
            promotion_payload.get("registry_promotion_granted") is True
        ),
        "promotion_validated": promotion_validated,
        "registry_entry_validated": registry_entry_validated,
        "registry_entry_path": (
            None if registry_entry_path is None else registry_entry_path.as_posix()
        ),
        "registry_entry_sha256": registry_entry_sha256,
        "aggregation_bound": promotion_payload.get("aggregation_bound") is True,
        "regression_bound": promotion_payload.get("regression_bound") is True,
        "local_fixture_only": True,
        "one_usage_receipt_only": True,
        **fixture_metadata,
        "human_review_required": True,
        "required_human_approval": True,
        "non_production": True,
        "production_adapter": False,
        "usage_receipt_granted": usage_granted,
        "promotion_status": promotion_status,
        "promotion_decision": promotion_decision,
        "complete": usage_granted,
        "rejected": not usage_granted,
        "rejection_reasons": list(rejection_reasons),
        "next_allowed_action": next_allowed_action,
        "output_dir": output_path.as_posix(),
        "no_live_website": True,
        "no_general_browser_automation": True,
        "no_autonomy": True,
        **_receipt_boundary_fields(),
    }
    return result


def _receipt_boundary_fields() -> dict[str, object]:
    fields = {
        field_name: False
        for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
    }
    fields.update(
        {
            field_name: False
            for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
        }
    )
    fields["production_promotion_granted"] = False
    return fields


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "usage_receipt_id": result["usage_receipt_id"],
        "job_dir": output_path.as_posix(),
        "plan_path": paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE].as_posix(),
        "plan_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE]
        ),
        "result_path": paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE]
        ),
        "promotion_result_path": result["promotion_result_path"],
        "promotion_result_sha256": result["promotion_result_sha256"],
        "local_fixture_path": result["local_fixture_path"],
        "local_fixture_sha256": result["local_fixture_sha256"],
        "usage_receipt_granted": result["usage_receipt_granted"],
        "production_promotion_granted": False,
        "next_allowed_action": result["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_receipt_boundary_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    usage_receipt_id: str,
    usage_granted: bool,
    promotion_status: str,
    promotion_decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_adapter_usage_receipt_plan",
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE],
        ),
        (
            "local_fixture_adapter_usage_receipt_result",
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE],
        ),
        (
            "local_fixture_adapter_usage_receipt_manifest",
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE],
        ),
        (
            "local_fixture_adapter_usage_receipt_summary",
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE],
        ),
        (
            "local_fixture_adapter_usage_receipt_checklist",
            paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE],
        ),
    )
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "usage_receipt_id": usage_receipt_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "usage_receipt_output_artifacts_only",
        "promotion_status": promotion_status,
        "promotion_decision": promotion_decision,
        "usage_receipt_granted": usage_granted,
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
        **_receipt_boundary_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "receipt_type": _RECEIPT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "receipt_adapter_id": _RECEIPT_ADAPTER_ID,
        "receipt_capability": _RECEIPT_CAPABILITY,
        "usage_receipt_id": artifact_index["usage_receipt_id"],
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
        "usage_receipt_granted": artifact_index["usage_receipt_granted"],
        "production_promotion_granted": False,
        "next_allowed_action": artifact_index["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **_receipt_boundary_fields(),
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
        "workflow": "local_fixture_adapter_usage_receipt_workflow",
        "complete": bool(result["complete"]),
        "usage_receipt_granted": bool(result["usage_receipt_granted"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_adapter_usage_receipt_plan_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_PLAN_FILE
        ].as_posix(),
        "local_fixture_adapter_usage_receipt_result_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_RESULT_FILE
        ].as_posix(),
        "local_fixture_adapter_usage_receipt_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_adapter_usage_receipt_summary_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_adapter_usage_receipt_checklist_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "required_human_approval": True,
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    source_path: Path,
    output_path: Path,
    usage_receipt_id: str,
    registry_entry_path: Path | None,
    rejection_reasons: list[str],
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    local_fixture_reference: str | None,
) -> LocalFixtureAdapterUsageReceiptResult:
    payload = {
        "workflow": "local_fixture_adapter_usage_receipt_workflow",
        "complete": False,
        "usage_receipt_granted": False,
        "receipt_type": _RECEIPT_TYPE,
        "usage_receipt_id": usage_receipt_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "promotion_result_path": source_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "registry_entry_path": (
            None if registry_entry_path is None else registry_entry_path.as_posix()
        ),
        "local_fixture_reference": local_fixture_reference,
        "promotion_status": _REJECTED_STATUS,
        "promotion_decision": _REJECTED_DECISION,
        "rejection_reasons": list(rejection_reasons),
        "required_human_approval": True,
        **_receipt_boundary_fields(),
    }
    return LocalFixtureAdapterUsageReceiptResult(
        promotion_result_path=source_path,
        output_dir=output_path,
        usage_receipt_id=usage_receipt_id,
        plan_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        registry_entry_path=registry_entry_path,
        complete=False,
        usage_receipt_granted=False,
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
            "# Local-Fixture Adapter Usage Receipt",
            "",
            f"Usage receipt ID: {result['usage_receipt_id']}",
            f"Status: {result['promotion_status']}",
            f"Decision: {result['promotion_decision']}",
            f"Promotion result: {result['promotion_result_path']}",
            f"Local fixture: {result['local_fixture_path']}",
            f"Usage receipt granted: {str(result['usage_receipt_granted']).lower()}",
            f"Production promotion granted: {str(result['production_promotion_granted']).lower()}",
            "",
            "Allowed state: local_fixture_only, one_usage_receipt_only, human_review_required, aggregation_bound, regression_bound, non_production.",
            "",
            "Rejected reasons:",
            reason_lines,
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["usage_receipt_granted"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Adapter Usage Receipt Checklist",
            "",
            f"- {checked} #428 local-fixture registry promotion validated.",
            f"- {checked} Local fixture path exists under the allowed output directory.",
            f"- {checked} Local fixture file hash recorded.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network probing was not performed.",
            "- [x] Production remains denied.",
            "- [x] Live website automation remains denied.",
            "- [x] General browser automation remains denied.",
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


def _normalized_optional_path(path: Path | None, output_path: Path) -> Path | None:
    if path is None:
        return None
    normalized = Path(path)
    if normalized.is_absolute():
        return normalized
    return output_path / normalized


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


def _looks_like_external_reference(reference: str) -> bool:
    lower = reference.lower()
    if "://" in lower:
        return True
    return any(lower.startswith(scheme + ":") for scheme in _FORBIDDEN_REFERENCE_SCHEMES)


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))
