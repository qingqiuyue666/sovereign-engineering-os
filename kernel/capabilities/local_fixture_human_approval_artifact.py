"""Metadata-only human approval artifact for a local-fixture gate plan.

This module validates a #431 local-fixture adapter execution-gate plan result
and records human approval metadata for a future runner-contract PR. It does
not issue tokens, create runners, execute adapters, open browsers, access
networks, admit live websites, or grant production/autonomous authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.capabilities.local_fixture_adapter_execution_gate_plan import (
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS,
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION",
    "LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS",
    "LocalFixtureHumanApprovalArtifactResult",
    "run_local_fixture_human_approval_artifact",
    "run_local_fixture_human_approval_artifact_launcher",
]


LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE = (
    "local_fixture_human_approval_artifact.json"
)
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE = (
    "local_fixture_human_approval_artifact_result.json"
)
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE = (
    "local_fixture_human_approval_artifact_manifest.json"
)
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE = (
    "local_fixture_human_approval_artifact_summary.md"
)
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE = (
    "local_fixture_human_approval_artifact_checklist.md"
)
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE = "artifact_index.json"
LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION = (
    "I_REVIEWED_LOCAL_FIXTURE_EXECUTION_GATE_PLAN_AND_APPROVE_METADATA_ONLY_"
    "NEXT_STEP_NO_TOKEN_NO_RUNNER_NO_EXECUTION_NO_BROWSER_NO_NETWORK_NO_AUTONOMY"
)

LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS = (
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_DENIED_ADMISSION_FIELDS
    + LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_FORBIDDEN_PERFORMED_FIELDS
    + LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_MATERIALIZED_FALSE_FIELDS
    + (
        "production_adapter",
        "production_promotion_granted",
        "approval_token_issued",
        "auto_approval_performed",
        "runnable_job_created",
        "execution_runner_created",
    )
)

_OPTIONAL_SOURCE_FALSE_FIELDS = (
    "execution_token_issued",
    "runner_created",
    "network_access_performed",
    "live_website_access_performed",
)
_OUTPUT_FALSE_FIELDS = (
    "approval_token_issued",
    "execution_token_issued",
    "runner_created",
    "runnable_job_created",
    "adapter_execution_performed",
    "playwright_execution_performed",
    "browser_open_performed",
    "network_access_performed",
    "live_website_access_performed",
    "autonomous_execution_performed",
    "production_promotion_granted",
)
_SOURCE_REQUIRED_TRUE_FIELDS = (
    "execution_gate_plan_granted",
    "dry_run_plan_validated",
    "invocation_plan_granted",
    "usage_receipt_validated",
    "usage_receipt_granted",
    "registry_promotion_granted",
    "source_gate_passed",
    "aggregation_bound",
    "regression_bound",
    "local_fixture_only",
    "one_usage_receipt_bound",
    "dry_run_plan_bound",
    "execution_gate_plan_only",
    "human_approval_request_only",
    "human_review_required",
    "required_human_approval",
    "non_production",
    "future_execution_requires_separate_human_approval_artifact",
    "future_execution_requires_separate_execution_runner_pr",
    "local_fixture_revalidated",
    "local_fixture_exists",
    "local_fixture_regular_file",
    "local_fixture_under_allowed_root",
)
_SOURCE_EXPECTED_FIELDS = {
    "gate_plan_type": "local_fixture_adapter_execution_gate_plan_v1",
    "execution_gate_plan_status": "local_fixture_adapter_execution_gate_plan_completed",
    "execution_gate_plan_decision": "record_execution_gate_plan_only",
    "adapter_id": "bounded_playwright_worker_adapter_draft",
    "candidate_id": "github-candidate-microsoft-playwright-v1",
    "repo_full_name": "microsoft/playwright",
}
_SOURCE_REQUIRED_HASH_FIELDS = (
    "dry_run_plan_sha256",
    "usage_receipt_sha256",
    "promotion_result_sha256",
    "source_gate_decision_sha256",
    "local_fixture_sha256",
)
_SOURCE_REQUIRED_FALSE_FIELD_REASONS = {
    "production_adapter": "source_production_adapter_claimed",
    "production_promotion_granted": "source_production_promotion_claimed",
    "approval_token_issued": "source_approval_token_claimed",
    "auto_approval_performed": "source_auto_approval_claimed",
    "runnable_job_created": "source_runnable_job_claimed",
    "execution_runner_created": "source_execution_runner_claimed",
    "adapter_execution_performed": "source_adapter_execution_claimed",
    "playwright_execution_performed": "source_playwright_execution_claimed",
    "browser_open_performed": "source_browser_open_claimed",
    "external_network_performed": "source_network_access_claimed",
    "network_probe_performed": "source_network_access_claimed",
    "autonomous_execution_performed": "source_autonomy_claimed",
}
_FORBIDDEN_TRUE_KEY_TERMS = (
    "token",
    "runner",
    "execution",
    "browser",
    "network",
    "autonomy",
    "production",
)
_FORBIDDEN_TRUE_KEY_ALLOWLIST = frozenset(
    _SOURCE_REQUIRED_TRUE_FIELDS
    + (
        "execution_gate_plan_granted",
        "execution_gate_plan_only",
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
_ARTIFACT_TYPE = "local_fixture_human_approval_artifact_v1"
_MANIFEST_TYPE = "local_fixture_human_approval_artifact_manifest_v1"
_ARTIFACT_INDEX_TYPE = "local_fixture_human_approval_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "local_fixture_human_approval_artifact_index_manifest_v1"
)
_AUTHORITY = "human_review_metadata_record_only"
_ADAPTER_ID = "local_fixture_human_approval_artifact"
_CAPABILITY = "launch_local_fixture_human_approval_artifact"
_COMPLETED_STATUS = "local_fixture_human_approval_artifact_completed"
_REJECTED_STATUS = "local_fixture_human_approval_artifact_rejected"
_COMPLETED_DECISION = "record_human_approval_artifact_only"
_REJECTED_DECISION = "reject_human_approval_artifact"
_NEXT_ALLOWED_ACTION = "human_review_approval_artifact_before_runner_contract_pr"
_RETRY_NEXT_ALLOWED_ACTION = "fix_execution_gate_plan_or_approval_artifact_and_retry"
_OUTPUT_FILES = (
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE,
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE,
)


@dataclass(frozen=True)
class LocalFixtureHumanApprovalArtifactResult:
    execution_gate_plan_path: Path
    output_dir: Path
    approval_artifact_id: str
    artifact_path: Path | None
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    approval_recorded: bool
    approval_artifact_status: str
    approval_artifact_decision: str
    rejection_reasons: tuple[str, ...]
    payload: dict[str, object]


def run_local_fixture_human_approval_artifact_launcher(
    execution_gate_plan: Path,
    output_dir: Path,
    approval_artifact_id: str,
    reviewer_id: str,
    approval_attestation: str,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureHumanApprovalArtifactResult:
    """Launcher-oriented wrapper for the metadata-only approval artifact."""

    return run_local_fixture_human_approval_artifact(
        execution_gate_plan,
        output_dir,
        approval_artifact_id,
        reviewer_id,
        approval_attestation,
        project_id=project_id,
        operator_notes=operator_notes,
    )


def run_local_fixture_human_approval_artifact(
    execution_gate_plan: Path,
    output_dir: Path,
    approval_artifact_id: str,
    reviewer_id: str,
    approval_attestation: str,
    *,
    project_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalFixtureHumanApprovalArtifactResult:
    """Validate a #431 execution-gate plan and record approval metadata."""

    source_path = Path(execution_gate_plan)
    output_path = Path(output_dir)
    paths = _output_paths(output_path)
    preflight_reasons = _preflight_rejection_reasons(output_path, paths)
    if preflight_reasons:
        return _unwritten_result(
            source_path=source_path,
            output_path=output_path,
            approval_artifact_id=approval_artifact_id,
            reviewer_id=reviewer_id,
            project_id=project_id,
            operator_notes=operator_notes,
            rejection_reasons=preflight_reasons,
        )

    source_payload, read_reasons = _read_source_execution_gate_plan(source_path)
    source_sha256 = _source_sha256(source_path)
    rejection_reasons = _dedupe_strings(
        _approval_input_rejection_reasons(
            approval_artifact_id,
            reviewer_id,
            approval_attestation,
        )
        + read_reasons
        + (
            []
            if read_reasons
            else _source_execution_gate_plan_rejection_reasons(source_payload)
        )
    )
    approval_recorded = not rejection_reasons
    status = _COMPLETED_STATUS if approval_recorded else _REJECTED_STATUS
    decision = _COMPLETED_DECISION if approval_recorded else _REJECTED_DECISION
    next_allowed_action = (
        _NEXT_ALLOWED_ACTION if approval_recorded else _RETRY_NEXT_ALLOWED_ACTION
    )

    artifact = _approval_payload(
        source_path=source_path,
        source_sha256=source_sha256,
        source_payload=source_payload,
        output_path=output_path,
        paths=paths,
        approval_artifact_id=approval_artifact_id,
        reviewer_id=reviewer_id,
        project_id=project_id,
        operator_notes=operator_notes,
        approval_recorded=approval_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
        rejection_reasons=rejection_reasons,
    )

    _write_json_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE],
        artifact,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE],
        artifact,
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE],
        _summary_markdown(artifact),
    )
    _write_markdown_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE],
        _checklist_markdown(artifact),
    )
    manifest = _manifest_payload(output_path=output_path, paths=paths, result=artifact)
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE],
        manifest,
    )
    artifact_index = _artifact_index_payload(
        output_path=output_path,
        paths=paths,
        approval_artifact_id=approval_artifact_id,
        approval_recorded=approval_recorded,
        status=status,
        decision=decision,
        next_allowed_action=next_allowed_action,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    payload = _launcher_payload(output_path=output_path, paths=paths, result=artifact)
    return LocalFixtureHumanApprovalArtifactResult(
        execution_gate_plan_path=source_path,
        output_dir=output_path,
        approval_artifact_id=approval_artifact_id,
        artifact_path=paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE],
        result_path=paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE],
        manifest_path=paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE],
        summary_path=paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE],
        checklist_path=paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE],
        artifact_index_path=paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE
        ],
        artifact_index_manifest_path=paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=approval_recorded,
        approval_recorded=approval_recorded,
        approval_artifact_status=status,
        approval_artifact_decision=decision,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_rejection_reasons(
    output_path: Path,
    paths: dict[str, Path],
) -> list[str]:
    reasons: list[str] = []
    if output_path.is_symlink() or not output_path.exists() or not output_path.is_dir():
        reasons.append("output_dir_missing")
        return reasons
    for candidate in paths.values():
        if candidate.exists() or candidate.is_symlink():
            reasons.append("output_collision")
            break
    return reasons


def _approval_input_rejection_reasons(
    approval_artifact_id: str,
    reviewer_id: str,
    approval_attestation: str,
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(approval_artifact_id):
        reasons.append("approval_artifact_id_missing")
    if not _non_empty_text(reviewer_id):
        reasons.append("reviewer_id_missing")
    if not _non_empty_text(approval_attestation):
        reasons.append("approval_attestation_missing")
    elif approval_attestation != LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION:
        reasons.append("approval_attestation_mismatch")
    return reasons


def _read_source_execution_gate_plan(
    source_path: Path,
) -> tuple[dict[str, object], list[str]]:
    reasons: list[str] = []
    if _candidate_repo_marker_in_path(source_path):
        reasons.append("candidate_repo_path_rejected")
    if not source_path.exists():
        reasons.append("source_execution_gate_plan_missing")
        return {}, _dedupe_strings(reasons)
    if source_path.is_symlink():
        reasons.append("source_execution_gate_plan_is_symlink")
        return {}, _dedupe_strings(reasons)
    if not source_path.is_file():
        reasons.append("source_execution_gate_plan_not_regular_file")
        return {}, _dedupe_strings(reasons)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append("source_execution_gate_plan_not_json_object")
        return {}, _dedupe_strings(reasons)
    if not isinstance(payload, dict):
        reasons.append("source_execution_gate_plan_not_json_object")
        return {}, _dedupe_strings(reasons)
    return payload, _dedupe_strings(reasons)


def _source_execution_gate_plan_rejection_reasons(
    payload: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if not _non_empty_text(payload.get("execution_gate_plan_id")):
        reasons.append("source_execution_gate_plan_id_missing")
    for field_name, expected in _SOURCE_EXPECTED_FIELDS.items():
        if payload.get(field_name) != expected:
            reasons.append(f"source_{field_name}_mismatch")
    for field_name in _SOURCE_REQUIRED_TRUE_FIELDS:
        if field_name not in payload:
            reasons.append("source_required_true_field_missing")
        elif payload.get(field_name) is not True:
            reasons.append("source_required_true_field_not_true")
    for field_name in LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_REQUIRED_SOURCE_FALSE_FIELDS:
        if field_name not in payload:
            reasons.append("source_required_false_field_missing")
        elif payload.get(field_name) is not False:
            reasons.append(
                _SOURCE_REQUIRED_FALSE_FIELD_REASONS.get(
                    field_name,
                    "source_forbidden_capability_claimed",
                )
            )
    for field_name in _OPTIONAL_SOURCE_FALSE_FIELDS:
        if field_name in payload and payload.get(field_name) is not False:
            reasons.append("source_forbidden_capability_claimed")
    for field_name in _SOURCE_REQUIRED_HASH_FIELDS:
        if not _non_empty_text(payload.get(field_name)):
            reasons.append("source_required_hash_missing")
    if payload.get("local_fixture_symlink_detected") is not False:
        reasons.append("source_local_fixture_symlink_claimed")
    reasons.extend(_forbidden_true_source_field_reasons(payload))
    return _dedupe_strings(reasons)


def _forbidden_true_source_field_reasons(payload: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for key, value in payload.items():
        if value is not True:
            continue
        key_lower = str(key).lower()
        if key_lower in _FORBIDDEN_TRUE_KEY_ALLOWLIST or key_lower.startswith("no_"):
            continue
        if any(term in key_lower for term in _FORBIDDEN_TRUE_KEY_TERMS):
            reasons.append("source_forbidden_true_field_claimed")
            break
    return reasons


def _approval_payload(
    *,
    source_path: Path,
    source_sha256: str | None,
    source_payload: dict[str, object],
    output_path: Path,
    paths: dict[str, Path],
    approval_artifact_id: str,
    reviewer_id: str,
    project_id: str | None,
    operator_notes: str | None,
    approval_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
    rejection_reasons: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "approval_artifact_type": _ARTIFACT_TYPE,
        "authority": _AUTHORITY,
        "approval_artifact_adapter_id": _ADAPTER_ID,
        "approval_artifact_capability": _CAPABILITY,
        "approval_artifact_id": approval_artifact_id,
        "reviewer_id": reviewer_id,
        "source_execution_gate_plan_path": source_path.as_posix(),
        "source_execution_gate_plan_sha256": source_sha256,
        "source_gate_plan_type": source_payload.get("gate_plan_type"),
        "source_gate_plan_status": source_payload.get("execution_gate_plan_status"),
        "source_gate_plan_decision": source_payload.get("execution_gate_plan_decision"),
        "source_execution_gate_plan_id": source_payload.get("execution_gate_plan_id"),
        "adapter_id": source_payload.get("adapter_id"),
        "candidate_id": source_payload.get("candidate_id"),
        "repo_full_name": source_payload.get("repo_full_name"),
        "local_fixture_sha256": source_payload.get("local_fixture_sha256"),
        "dry_run_plan_sha256": source_payload.get("dry_run_plan_sha256"),
        "usage_receipt_sha256": source_payload.get("usage_receipt_sha256"),
        "promotion_result_sha256": source_payload.get("promotion_result_sha256"),
        "source_gate_decision_sha256": source_payload.get(
            "source_gate_decision_sha256"
        ),
        "approval_recorded": approval_recorded,
        "approval_artifact_status": status,
        "approval_artifact_decision": decision,
        "human_review_recorded": approval_recorded,
        "metadata_only": True,
        "future_runner_requires_separate_pr": True,
        "future_execution_requires_separate_runner_receipt": True,
        "future_execution_requires_explicit_local_fixture_runner_gate": True,
        "next_allowed_action": next_allowed_action,
        "output_dir": output_path.as_posix(),
        "approval_artifact_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE
        ].as_posix(),
        "approval_artifact_result_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "approval_artifact_manifest_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE
        ].as_posix(),
        "approval_artifact_summary_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "approval_artifact_checklist_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "rejection_reasons": list(rejection_reasons),
        "complete": approval_recorded,
        "rejected": not approval_recorded,
        "required_human_approval": True,
        "non_production": True,
        "production_adapter": False,
    }
    payload.update(_output_boundary_false_fields())
    if project_id is not None:
        payload["project_id"] = project_id
    if operator_notes is not None:
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = _sha256_text(operator_notes)
    return payload


def _output_boundary_false_fields() -> dict[str, object]:
    return {field_name: False for field_name in _OUTPUT_FALSE_FIELDS}


def _manifest_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    result: dict[str, object],
) -> dict[str, object]:
    return {
        "manifest_type": _MANIFEST_TYPE,
        "approval_artifact_type": _ARTIFACT_TYPE,
        "authority": _AUTHORITY,
        "approval_artifact_adapter_id": _ADAPTER_ID,
        "approval_artifact_capability": _CAPABILITY,
        "approval_artifact_id": result["approval_artifact_id"],
        "job_dir": output_path.as_posix(),
        "approval_artifact_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE
        ].as_posix(),
        "approval_artifact_sha256": sha256_file(
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE]
        ),
        "result_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "result_sha256": sha256_file(
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE]
        ),
        "summary_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "summary_sha256": sha256_file(
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE]
        ),
        "checklist_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "checklist_sha256": sha256_file(
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE]
        ),
        "source_execution_gate_plan_path": result[
            "source_execution_gate_plan_path"
        ],
        "source_execution_gate_plan_sha256": result[
            "source_execution_gate_plan_sha256"
        ],
        "approval_recorded": result["approval_recorded"],
        "approval_artifact_status": result["approval_artifact_status"],
        "approval_artifact_decision": result["approval_artifact_decision"],
        "metadata_only": True,
        "next_allowed_action": result["next_allowed_action"],
        **_output_boundary_false_fields(),
    }


def _artifact_index_payload(
    *,
    output_path: Path,
    paths: dict[str, Path],
    approval_artifact_id: str,
    approval_recorded: bool,
    status: str,
    decision: str,
    next_allowed_action: str,
) -> dict[str, object]:
    roles = (
        (
            "local_fixture_human_approval_artifact",
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE],
        ),
        (
            "local_fixture_human_approval_artifact_result",
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE],
        ),
        (
            "local_fixture_human_approval_artifact_manifest",
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE],
        ),
        (
            "local_fixture_human_approval_artifact_summary",
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE],
        ),
        (
            "local_fixture_human_approval_artifact_checklist",
            paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE],
        ),
    )
    entries = [_generated_artifact_entry(output_path, role, path) for role, path in roles]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "approval_artifact_type": _ARTIFACT_TYPE,
        "authority": _AUTHORITY,
        "approval_artifact_adapter_id": _ADAPTER_ID,
        "approval_artifact_capability": _CAPABILITY,
        "approval_artifact_id": approval_artifact_id,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "human_approval_artifact_output_artifacts_only",
        "approval_recorded": approval_recorded,
        "approval_artifact_status": status,
        "approval_artifact_decision": decision,
        "metadata_only": True,
        "next_allowed_action": next_allowed_action,
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_files_indexed": False,
        "external_candidate_artifacts_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        **_output_boundary_false_fields(),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "approval_artifact_type": _ARTIFACT_TYPE,
        "authority": _AUTHORITY,
        "approval_artifact_adapter_id": _ADAPTER_ID,
        "approval_artifact_capability": _CAPABILITY,
        "approval_artifact_id": artifact_index["approval_artifact_id"],
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
        "approval_recorded": artifact_index["approval_recorded"],
        "approval_artifact_status": artifact_index["approval_artifact_status"],
        "approval_artifact_decision": artifact_index["approval_artifact_decision"],
        "metadata_only": True,
        "next_allowed_action": artifact_index["next_allowed_action"],
        **_output_boundary_false_fields(),
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
        "workflow": "local_fixture_human_approval_artifact_workflow",
        "complete": bool(result["complete"]),
        "approval_recorded": bool(result["approval_recorded"]),
        "output_dir": output_path.as_posix(),
        "human_summary_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_human_approval_artifact_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_FILE
        ].as_posix(),
        "local_fixture_human_approval_artifact_result_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_RESULT_FILE
        ].as_posix(),
        "local_fixture_human_approval_artifact_manifest_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_MANIFEST_FILE
        ].as_posix(),
        "local_fixture_human_approval_artifact_summary_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_SUMMARY_FILE
        ].as_posix(),
        "local_fixture_human_approval_artifact_checklist_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "required_human_approval": True,
    }
    payload.update(result)
    return payload


def _unwritten_result(
    *,
    source_path: Path,
    output_path: Path,
    approval_artifact_id: str,
    reviewer_id: str,
    project_id: str | None,
    operator_notes: str | None,
    rejection_reasons: list[str],
) -> LocalFixtureHumanApprovalArtifactResult:
    payload: dict[str, object] = {
        "workflow": "local_fixture_human_approval_artifact_workflow",
        "complete": False,
        "approval_recorded": False,
        "approval_artifact_type": _ARTIFACT_TYPE,
        "authority": _AUTHORITY,
        "approval_artifact_id": approval_artifact_id,
        "reviewer_id": reviewer_id,
        "source_execution_gate_plan_path": source_path.as_posix(),
        "source_execution_gate_plan_sha256": _source_sha256(source_path),
        "output_dir": output_path.as_posix(),
        "approval_artifact_status": _REJECTED_STATUS,
        "approval_artifact_decision": _REJECTED_DECISION,
        "rejection_reasons": list(rejection_reasons),
        "next_allowed_action": _RETRY_NEXT_ALLOWED_ACTION,
        "required_human_approval": True,
        "metadata_only": True,
        "human_review_recorded": False,
        **_output_boundary_false_fields(),
    }
    if project_id is not None:
        payload["project_id"] = project_id
    if operator_notes is not None:
        payload["operator_notes"] = operator_notes
        payload["operator_notes_sha256"] = _sha256_text(operator_notes)
    return LocalFixtureHumanApprovalArtifactResult(
        execution_gate_plan_path=source_path,
        output_dir=output_path,
        approval_artifact_id=approval_artifact_id,
        artifact_path=None,
        result_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        approval_recorded=False,
        approval_artifact_status=_REJECTED_STATUS,
        approval_artifact_decision=_REJECTED_DECISION,
        rejection_reasons=tuple(rejection_reasons),
        payload=payload,
    )


def _summary_markdown(result: dict[str, object]) -> str:
    reasons = result.get("rejection_reasons")
    if isinstance(reasons, list) and reasons:
        reason_lines = "\n".join("- " + str(reason) for reason in reasons)
    else:
        reason_lines = "- none"
    return "\n".join(
        [
            "# Local-Fixture Human Approval Artifact",
            "",
            "Metadata-only human approval artifact.",
            "This is not an execution token.",
            "This does not create runner.",
            "This does not execute adapter.",
            "This does not open browser.",
            "This does not access network.",
            "This does not authorize live websites.",
            "This does not authorize production.",
            "Separate runner-contract PR required.",
            "Separate local-fixture runner gate required before future execution.",
            "Separate runner receipt required after future runner invocation.",
            "",
            f"Approval artifact ID: {result['approval_artifact_id']}",
            f"Reviewer ID: {result['reviewer_id']}",
            f"Source execution gate plan path: {result['source_execution_gate_plan_path']}",
            f"Source execution gate plan sha256: {result['source_execution_gate_plan_sha256']}",
            f"Execution gate plan ID: {result['source_execution_gate_plan_id']}",
            f"Adapter ID: {result['adapter_id']}",
            f"Candidate ID: {result['candidate_id']}",
            f"Repo full name: {result['repo_full_name']}",
            f"Local fixture sha256: {result['local_fixture_sha256']}",
            "",
            "Rejected capabilities:",
            "- execution token issuance",
            "- approval token issuance",
            "- runner creation",
            "- adapter execution",
            "- Playwright execution",
            "- browser opening",
            "- network access",
            "- live website access",
            "- production promotion",
            "- autonomous execution",
            "",
            f"Next allowed action: {result['next_allowed_action']}",
            "",
            "Rejected reasons:",
            reason_lines,
            "",
        ]
    )


def _checklist_markdown(result: dict[str, object]) -> str:
    checked = "[x]" if result["approval_recorded"] else "[ ]"
    return "\n".join(
        [
            "# Local-Fixture Human Approval Artifact Checklist",
            "",
            f"- {checked} #431 execution-gate plan result validated.",
            f"- {checked} Human reviewer identity recorded.",
            f"- {checked} Exact metadata-only attestation recorded.",
            "- [x] Approval token was not issued.",
            "- [x] Execution token was not issued.",
            "- [x] Runner was not created.",
            "- [x] Runnable job was not created.",
            "- [x] Adapter execution was not performed.",
            "- [x] Playwright execution was not performed.",
            "- [x] Browser opening was not performed.",
            "- [x] Network access was not performed.",
            "- [x] Live website access was not performed.",
            "- [x] Autonomous execution was not performed.",
            "- [x] Production promotion remains denied.",
            "",
        ]
    )


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
