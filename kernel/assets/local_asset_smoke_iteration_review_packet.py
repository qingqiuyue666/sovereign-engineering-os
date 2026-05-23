"""Review packet for bounded local asset smoke iteration outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE",
    "LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE",
    "LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE",
    "LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE",
    "LocalAssetSmokeIterationReviewPacketResult",
    "build_local_asset_smoke_iteration_review_packet",
]


LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE = (
    "local_asset_smoke_iteration_review_packet.json"
)
LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE = (
    "local_asset_smoke_iteration_review_packet_manifest.json"
)
LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE = (
    "local_asset_smoke_iteration_review_summary.md"
)
LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE = (
    "local_asset_smoke_iteration_human_decision_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_PACKET_TYPE = "local_asset_smoke_iteration_review_packet_v1"
_MANIFEST_TYPE = "local_asset_smoke_iteration_review_packet_manifest_v1"
_INDEX_TYPE = "local_asset_smoke_iteration_review_packet_artifact_index_v1"
_INDEX_MANIFEST_TYPE = (
    "local_asset_smoke_iteration_review_packet_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_smoke_iteration_review_packet_only"
_NEXT_ALLOWED_ACTION = "human_review_smoke_iteration_review_packet"

_READY_STATUSES = {"review_ready", "review_ready_with_warnings"}
_REJECT_DECISION = "reject_and_repair_iteration"
_APPROVE_DECISION = "generate_promotion_gate_for_iteration"
_INSPECT_QUARANTINE_DECISION = "inspect_iteration_quarantine_before_promotion"
_INSPECT_DUPLICATES_DECISION = "inspect_iteration_duplicates_before_promotion"
_INSPECT_INCREMENTAL_DECISION = (
    "inspect_iteration_incremental_changes_before_promotion"
)

_BOUNDARY_FLAGS = {
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "bounded_smoke_iteration_performed_by_review_packet": False,
    "promotion_gate_run_performed": False,
    "input_mutation_performed": False,
    "iteration_output_mutation_performed": False,
    "smoke_output_mutation_performed": False,
    "file_move_performed": False,
    "file_rename_performed": False,
    "file_delete_performed": False,
    "duplicate_deletion_performed": False,
    "media_organizer_behavior_performed": False,
    "output_overwrite_performed": False,
    "network_access_performed": False,
    "model_api_called": False,
    "external_runtime_invoked": False,
}

_PRODUCTION_FLAGS = {
    "production_promotion_granted": False,
    "production_scan_approved": False,
    "production_scan_performed": False,
}

_OUTPUT_FILES = (
    LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE,
    LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE,
    LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE,
    LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_DECISION_OPTIONS = (
    _APPROVE_DECISION,
    _INSPECT_QUARANTINE_DECISION,
    _INSPECT_DUPLICATES_DECISION,
    _INSPECT_INCREMENTAL_DECISION,
    _REJECT_DECISION,
)

_RAW_PHRASE_SENTINELS = (
    "I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION",
    "I_APPROVE_LOCAL_ASSET_SMOKE_RUN",
)


@dataclass(frozen=True)
class _SourceArtifactSpec:
    artifact_role: str
    relative_path: str
    required: bool
    json_artifact: bool


_SOURCE_ARTIFACTS = (
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_result",
        "local_asset_bounded_smoke_iteration_result.json",
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_manifest",
        "local_asset_bounded_smoke_iteration_manifest.json",
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_summary",
        "local_asset_bounded_smoke_iteration_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_human_review_checklist",
        "local_asset_bounded_smoke_iteration_human_review_checklist.md",
        False,
        False,
    ),
    _SourceArtifactSpec("iteration_artifact_index", "artifact_index.json", True, True),
    _SourceArtifactSpec(
        "iteration_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_signoff",
        "control/local_asset_bounded_smoke_iteration_signoff.json",
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_iteration_admission",
        "control/local_asset_bounded_smoke_iteration_admission.json",
        True,
        True,
    ),
    _SourceArtifactSpec("smoke_artifact_index", "smoke/artifact_index.json", False, True),
    _SourceArtifactSpec(
        "smoke_artifact_index_manifest",
        "smoke/artifact_index_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "smoke_local_asset_human_smoke_run_summary",
        "smoke/local_asset_human_smoke_run_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "smoke_local_asset_human_smoke_approval",
        "smoke/control/local_asset_human_smoke_approval.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "smoke_local_asset_human_smoke_admission_receipt",
        "smoke/control/local_asset_human_smoke_admission_receipt.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_artifact_index", "smoke/scan/artifact_index.json", False, True),
    _SourceArtifactSpec(
        "scan_artifact_index_manifest",
        "smoke/scan/artifact_index_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_asset_manifest", "smoke/scan/asset_manifest.json", False, True),
    _SourceArtifactSpec("scan_asset_index", "smoke/scan/asset_index.json", False, True),
    _SourceArtifactSpec(
        "scan_duplicates_report",
        "smoke/scan/duplicates_report.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_media_inventory", "smoke/scan/media_inventory.md", False, False),
    _SourceArtifactSpec(
        "scan_asset_runtime_audit_log",
        "smoke/scan/asset_runtime_audit_log.jsonl",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_asset_runtime_validation_report",
        "smoke/scan/asset_runtime_validation_report.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_runtime_quarantine_manifest",
        "smoke/scan/asset_runtime_quarantine_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_run_receipt",
        "smoke/scan/asset_scan_run_receipt.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_launcher_summary", "smoke/scan/launcher_summary.md", False, False),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_index",
        "smoke/scan/local_asset_index.sqlite",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_index_manifest",
        "smoke/scan/local_asset_sqlite_index_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_query_summary",
        "smoke/scan/local_asset_sqlite_query_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_plan",
        "smoke/scan/local_asset_incremental_scan_plan.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_manifest",
        "smoke/scan/local_asset_incremental_scan_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_summary",
        "smoke/scan/local_asset_incremental_scan_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_failure_bundle",
        "smoke/scan/asset_scan_failure_bundle.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_failure_summary",
        "smoke/scan/asset_scan_failure_summary.md",
        False,
        False,
    ),
)

_REVIEW_ARTIFACTS = (
    (
        "local_asset_smoke_iteration_review_packet",
        LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE,
    ),
    (
        "local_asset_smoke_iteration_review_packet_manifest",
        LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE,
    ),
    (
        "local_asset_smoke_iteration_review_summary",
        LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE,
    ),
    (
        "local_asset_smoke_iteration_human_decision_checklist",
        LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE,
    ),
)


@dataclass(frozen=True)
class LocalAssetSmokeIterationReviewPacketResult:
    iteration_output_dir: Path
    output_dir: Path
    packet_path: Path | None
    packet_manifest_path: Path | None
    summary_path: Path | None
    decision_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    iteration_review_status: str
    recommended_human_decision: str
    payload: dict[str, object]


def build_local_asset_smoke_iteration_review_packet(
    iteration_output_dir: Path,
    output_dir: Path,
    *,
    project_id: str | None = None,
) -> LocalAssetSmokeIterationReviewPacketResult:
    """Build a metadata-only review packet from generated iteration artifacts."""

    iteration_path = Path(iteration_output_dir)
    output_path = Path(output_dir)
    paths = _review_output_paths(output_path)

    output_error = _real_existing_dir_error(output_path, "output_dir")
    if output_error is not None:
        return _structured_failure_result(
            iteration_path=iteration_path,
            output_path=output_path,
            failure_stage="preflight_output_dir_missing",
            error_message=output_error,
            project_id=project_id,
        )

    collision = _existing_output_collision(paths)
    if collision is not None:
        return _structured_failure_result(
            iteration_path=iteration_path,
            output_path=output_path,
            failure_stage="preflight_output_collision",
            error_message="local asset smoke iteration review output already exists: "
            + collision,
            project_id=project_id,
        )

    iteration_overlap = _existing_dir_overlap_error(
        iteration_path,
        output_path,
        left_label="iteration_output_dir",
        right_label="output_dir",
    )
    if iteration_overlap is not None:
        return _structured_failure_result(
            iteration_path=iteration_path,
            output_path=output_path,
            failure_stage="preflight_iteration_output_overlap",
            error_message=iteration_overlap,
            project_id=project_id,
        )

    iteration_error = _real_existing_dir_error(iteration_path, "iteration_output_dir")
    source_artifacts = _source_artifact_records(
        iteration_path,
        iteration_error=iteration_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)

    upstream_overlap = _upstream_output_overlap_error(source_payloads, output_path)
    if upstream_overlap is not None:
        return _structured_failure_result(
            iteration_path=iteration_path,
            output_path=output_path,
            failure_stage="preflight_upstream_output_overlap",
            error_message=upstream_overlap,
            project_id=project_id,
        )

    packet = _build_packet_payload(
        iteration_output_dir=iteration_path,
        output_dir=output_path,
        project_id=project_id,
        iteration_error=iteration_error,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(packet)
    checklist = _decision_checklist_markdown(packet)

    _write_json_exclusive(
        paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE],
        packet,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE],
        checklist,
    )
    packet_manifest = _packet_manifest_payload(
        paths=paths,
        source_artifacts=source_artifacts,
        iteration_review_status=str(packet["iteration_review_status"]),
        recommended_human_decision=str(packet["recommended_human_decision"]),
    )
    _write_json_exclusive(
        paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE],
        packet_manifest,
    )
    artifact_index = _artifact_index_payload(output_path, paths)
    _write_json_exclusive(paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(paths[_ARTIFACT_INDEX_MANIFEST_FILE], artifact_index_manifest)

    complete = packet["iteration_review_status"] in _READY_STATUSES
    payload = _launcher_payload_from_packet(packet, paths)
    return LocalAssetSmokeIterationReviewPacketResult(
        iteration_output_dir=iteration_path,
        output_dir=output_path,
        packet_path=paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE],
        packet_manifest_path=paths[
            LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE
        ],
        summary_path=paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE],
        decision_checklist_path=paths[
            LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        iteration_review_status=str(packet["iteration_review_status"]),
        recommended_human_decision=str(packet["recommended_human_decision"]),
        payload=payload,
    )


def _review_output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _real_existing_dir_error(path: Path, label: str) -> str | None:
    if not path.exists():
        return label + " is missing"
    if not path.is_dir():
        return label + " is not a directory"
    if path.is_symlink():
        return label + " must not be a symlink"
    return None


def _existing_output_collision(paths: dict[str, Path]) -> str | None:
    for file_name in sorted(paths):
        if paths[file_name].exists():
            return file_name
    return None


def _existing_dir_overlap_error(
    left_path: Path,
    right_path: Path,
    *,
    left_label: str,
    right_label: str,
) -> str | None:
    if not left_path.exists() or not right_path.exists():
        return None
    try:
        left_resolved = left_path.resolve(strict=True)
        right_resolved = right_path.resolve(strict=True)
    except OSError:
        return None
    if left_resolved == right_resolved:
        return right_label + " must not equal " + left_label
    if _path_is_inside(right_resolved, left_resolved):
        return right_label + " must not be inside " + left_label
    if _path_is_inside(left_resolved, right_resolved):
        return left_label + " must not be inside " + right_label
    return None


def _upstream_output_overlap_error(
    source_payloads: dict[str, object],
    output_path: Path,
) -> str | None:
    discovered = _discover_upstream_dirs(source_payloads)
    for label, path_value in (
        ("candidate_input_dir", discovered.get("candidate_input_dir")),
        ("promotion_output_dir", discovered.get("promotion_output_dir")),
        ("delegated smoke_output_dir", discovered.get("smoke_output_dir")),
    ):
        if not isinstance(path_value, str) or not path_value:
            continue
        root_path = Path(path_value)
        if root_path.exists() and _path_is_inside(output_path, root_path):
            return "output_dir must not be inside " + label
    return None


def _discover_upstream_dirs(source_payloads: dict[str, object]) -> dict[str, object]:
    result = _dict_payload(source_payloads, "local_asset_bounded_smoke_iteration_result")
    admission = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_admission",
    )
    signoff = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_signoff",
    )
    smoke_admission = _dict_payload(
        source_payloads,
        "smoke_local_asset_human_smoke_admission_receipt",
    )
    return {
        "candidate_input_dir": _first_text(
            result.get("candidate_input_dir"),
            admission.get("candidate_input_dir"),
            signoff.get("candidate_input_dir"),
            smoke_admission.get("candidate_input_dir"),
        ),
        "promotion_output_dir": _first_text(
            result.get("promotion_output_dir"),
            signoff.get("promotion_output_dir"),
        ),
        "smoke_output_dir": _first_text(
            result.get("smoke_output_dir"),
            admission.get("smoke_output_dir"),
            smoke_admission.get("output_dir"),
        ),
    }


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _source_artifact_records(
    iteration_path: Path,
    *,
    iteration_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for spec in _SOURCE_ARTIFACTS:
        path = iteration_path / spec.relative_path
        if iteration_error is not None:
            records.append(_missing_source_record(spec, path))
            continue
        exists = path.exists()
        is_symlink = path.is_symlink()
        is_file = path.is_file() if exists and not is_symlink else False
        trusted = exists and is_file and not is_symlink
        records.append(
            {
                "artifact_role": spec.artifact_role,
                "relative_path": spec.relative_path,
                "path": path.as_posix(),
                "exists": exists,
                "required": spec.required,
                "json_artifact": spec.json_artifact,
                "trusted_generated_artifact": trusted,
                "is_symlink": is_symlink,
                "is_file": is_file,
                "sha256": sha256_file(path) if trusted else None,
                "size_bytes": path.stat().st_size if trusted else None,
                "content_indexed": False,
                "raw_content_copied": False,
            }
        )
    return sorted(records, key=lambda record: str(record["artifact_role"]))


def _missing_source_record(
    spec: _SourceArtifactSpec,
    path: Path,
) -> dict[str, object]:
    return {
        "artifact_role": spec.artifact_role,
        "relative_path": spec.relative_path,
        "path": path.as_posix(),
        "exists": False,
        "required": spec.required,
        "json_artifact": spec.json_artifact,
        "trusted_generated_artifact": False,
        "is_symlink": False,
        "is_file": False,
        "sha256": None,
        "size_bytes": None,
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _read_json_source_payloads(
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payloads: dict[str, object] = {}
    for record in source_artifacts:
        if record.get("json_artifact") is not True:
            continue
        if record.get("trusted_generated_artifact") is not True:
            continue
        path = Path(str(record["path"]))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            record["parse_error"] = "json_malformed"
            continue
        if not isinstance(payload, dict):
            record["parse_error"] = "json_not_object"
            continue
        payloads[str(record["artifact_role"])] = payload
    return payloads


def _build_packet_payload(
    *,
    iteration_output_dir: Path,
    output_dir: Path,
    project_id: str | None,
    iteration_error: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    records_by_role = {
        str(record["artifact_role"]): record for record in source_artifacts
    }
    iteration_result = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_result",
    )
    iteration_manifest = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_manifest",
    )
    signoff = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_signoff",
    )
    admission = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_admission",
    )
    smoke_approval = _dict_payload(
        source_payloads,
        "smoke_local_asset_human_smoke_approval",
    )
    smoke_admission = _dict_payload(
        source_payloads,
        "smoke_local_asset_human_smoke_admission_receipt",
    )
    scan_receipt = _dict_payload(source_payloads, "scan_asset_scan_run_receipt")
    asset_manifest = _dict_payload(source_payloads, "scan_asset_manifest")
    validation_report = _dict_payload(
        source_payloads,
        "scan_asset_runtime_validation_report",
    )
    duplicates_report = _dict_payload(source_payloads, "scan_duplicates_report")
    quarantine_manifest = _dict_payload(
        source_payloads,
        "scan_asset_runtime_quarantine_manifest",
    )
    sqlite_manifest = _dict_payload(
        source_payloads,
        "scan_local_asset_sqlite_index_manifest",
    )
    incremental_plan = _dict_payload(
        source_payloads,
        "scan_local_asset_incremental_scan_plan",
    )
    failure_bundle = _dict_payload(source_payloads, "scan_asset_scan_failure_bundle")

    source_state = _source_state(
        source_artifacts,
        records_by_role,
        source_payloads,
        iteration_error=iteration_error,
    )
    iteration = _iteration_summary(iteration_result, admission)
    signoff_summary = _signoff_summary(signoff, records_by_role)
    admission_summary = _admission_summary(admission, iteration_result)
    promotion_summary = _promotion_summary(admission, iteration_result)
    delegated_smoke = _delegated_smoke_summary(
        smoke_approval,
        smoke_admission,
        records_by_role,
    )
    duplicate_group_count = _duplicate_group_count(
        scan_receipt,
        asset_manifest,
        validation_report,
        duplicates_report,
    )
    duplicate_asset_count = _duplicate_asset_count(duplicates_report)
    quarantined_path_count = _quarantined_path_count(
        scan_receipt,
        asset_manifest,
        validation_report,
        quarantine_manifest,
    )
    incremental_counts = _incremental_counts(incremental_plan)
    delegated_scan = _scan_summary(
        scan_receipt,
        asset_manifest,
        validation_report,
        records_by_role,
        scan_complete=bool(iteration["scan_complete"]),
        duplicate_group_count=duplicate_group_count,
        quarantined_path_count=quarantined_path_count,
    )
    quarantine = _quarantine_summary(quarantine_manifest, quarantined_path_count)
    duplicate = {
        "duplicate_group_count": duplicate_group_count,
        "duplicate_asset_count": duplicate_asset_count,
        "deletion_suggested": False,
        "no_deletion_suggested": True,
        "recommended_action": "human_inspect_only",
        "automatic_dedupe_performed": False,
        "relative_paths_included": False,
    }
    sqlite = {
        "database_present": bool(
            records_by_role["scan_local_asset_sqlite_index"]["exists"]
        ),
        "manifest_present": bool(
            records_by_role["scan_local_asset_sqlite_index_manifest"]["exists"]
        ),
        "query_summary_present": bool(
            records_by_role["scan_local_asset_sqlite_query_summary"]["exists"]
        ),
        "row_counts": _dict_or_empty(sqlite_manifest.get("row_counts")),
        "database_opened": False,
        "candidate_files_opened": False,
        "global_database_state_used": False,
    }
    incremental = {
        "plan_present": bool(
            records_by_role["scan_local_asset_incremental_scan_plan"]["exists"]
        ),
        "plan_mode": incremental_counts["plan_mode"],
        "unchanged_asset_count": incremental_counts["unchanged_asset_count"],
        "changed_asset_count": incremental_counts["changed_asset_count"],
        "new_asset_count": incremental_counts["new_asset_count"],
        "missing_asset_count": incremental_counts["missing_asset_count"],
        "suspicious_change_count": incremental_counts["suspicious_change_count"],
        "automatic_skip_performed": False,
        "cache_execution_performed": False,
    }
    failure = _failure_summary(
        failure_bundle,
        iteration_result,
        admission,
        smoke_admission,
    )
    warnings = _warning_items(
        source_state=source_state,
        iteration_summary=iteration,
        delegated_smoke_summary=delegated_smoke,
        duplicate_group_count=duplicate_group_count,
        quarantined_path_count=quarantined_path_count,
        incremental_counts=incremental_counts,
    )
    iteration_review_status = _iteration_review_status(
        source_state=source_state,
        iteration_summary=iteration,
        warnings=warnings,
    )
    recommended_human_decision = _recommended_human_decision(
        iteration_review_status=iteration_review_status,
        duplicate_group_count=duplicate_group_count,
        quarantined_path_count=quarantined_path_count,
        incremental_counts=incremental_counts,
    )
    project = _first_text(
        project_id,
        iteration_result.get("project_id"),
        admission.get("project_id"),
        signoff.get("project_id"),
        smoke_approval.get("project_id"),
        smoke_admission.get("project_id"),
        scan_receipt.get("project_id"),
        asset_manifest.get("project_id"),
    )
    artifact_summary = {
        "source_artifact_count": len(source_artifacts),
        "generated_artifacts_read_count": source_state[
            "generated_artifacts_read_count"
        ],
        "generated_artifacts_missing_count": source_state[
            "generated_artifacts_missing_count"
        ],
        "missing_required_artifacts": source_state["missing_required_artifacts"],
        "missing_optional_artifacts": source_state["missing_optional_artifacts"],
        "untrusted_artifacts": source_state["untrusted_artifacts"],
        "parse_error_artifacts": source_state["parse_error_artifacts"],
    }
    packet = {
        "packet_type": _PACKET_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "iteration_output_dir": iteration_output_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "project_id": project,
        "iteration_review_status": iteration_review_status,
        "recommended_human_decision": recommended_human_decision,
        "iteration_summary": iteration,
        "signoff_summary": signoff_summary,
        "admission_summary": admission_summary,
        "promotion_summary": promotion_summary,
        "delegated_smoke_summary": delegated_smoke,
        "delegated_scan_summary": delegated_scan,
        "artifact_summary": artifact_summary,
        "duplicate_summary": duplicate,
        "quarantine_summary": quarantine,
        "sqlite_summary": sqlite,
        "incremental_summary": incremental,
        "failure_summary": failure,
        "warning_summary": {
            "warning_count": len(warnings),
            "warnings": warnings,
            "missing_optional_artifacts": source_state["missing_optional_artifacts"],
        },
        "decision_checklist": _decision_checklist_payload(),
        "source_artifacts": source_artifacts,
        "missing_artifacts": source_state["missing_artifacts"],
        "untrusted_artifacts": source_state["untrusted_artifacts"],
        "generated_artifacts_read_count": source_state[
            "generated_artifacts_read_count"
        ],
        "generated_artifacts_missing_count": source_state[
            "generated_artifacts_missing_count"
        ],
        "deterministic_ordering": True,
        "iteration_status": iteration["iteration_status"],
        "iteration_decision": iteration["iteration_decision"],
        "promotion_gate_status": promotion_summary["promotion_gate_status"],
        "promotion_decision": promotion_summary["promotion_decision"],
        "human_signoff_valid": signoff_summary["human_signoff_valid"],
        "bounded_smoke_iteration_performed": iteration[
            "bounded_smoke_iteration_performed"
        ],
        "smoke_launcher_invoked": iteration["smoke_launcher_invoked"],
        "smoke_run_complete": iteration["smoke_run_complete"],
        "scan_complete": iteration["scan_complete"],
        "duplicate_group_count": duplicate_group_count,
        "quarantined_path_count": quarantined_path_count,
        "incremental_plan_mode": incremental["plan_mode"],
        "changed_asset_count": incremental["changed_asset_count"],
        "new_asset_count": incremental["new_asset_count"],
        "missing_asset_count": incremental["missing_asset_count"],
        "suspicious_change_count": incremental["suspicious_change_count"],
        "warning_count": len(warnings),
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    _assert_no_raw_phrase_leak(packet)
    return packet


def _source_state(
    source_artifacts: list[dict[str, object]],
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    iteration_error: str | None,
) -> dict[str, object]:
    missing_artifacts = [
        {
            "artifact_role": record["artifact_role"],
            "relative_path": record["relative_path"],
            "required": record["required"],
        }
        for record in source_artifacts
        if record.get("exists") is not True
    ]
    missing_required = [
        str(item["artifact_role"])
        for item in missing_artifacts
        if item["required"] is True
    ]
    missing_optional = [
        str(item["artifact_role"])
        for item in missing_artifacts
        if item["required"] is not True
    ]
    untrusted = [
        str(record["artifact_role"])
        for record in source_artifacts
        if record.get("exists") is True
        and record.get("trusted_generated_artifact") is not True
    ]
    parse_errors = [
        str(record["artifact_role"])
        for record in source_artifacts
        if "parse_error" in record
    ]
    untrusted.extend(parse_errors)
    untrusted.extend(_artifact_hash_mismatches(records_by_role, source_payloads))
    untrusted.extend(_artifact_type_mismatches(source_payloads))
    if iteration_error is not None and "symlink" in iteration_error:
        untrusted.append("iteration_output_dir")
    return {
        "missing_artifacts": missing_artifacts,
        "missing_required_artifacts": sorted(set(missing_required)),
        "missing_optional_artifacts": sorted(set(missing_optional)),
        "untrusted_artifacts": sorted(set(untrusted)),
        "parse_error_artifacts": sorted(set(parse_errors)),
        "generated_artifacts_read_count": sum(
            1
            for record in source_artifacts
            if record.get("trusted_generated_artifact") is True
        ),
        "generated_artifacts_missing_count": len(missing_artifacts),
    }


def _artifact_hash_mismatches(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
) -> list[str]:
    mismatches = []
    iteration_manifest = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_iteration_manifest",
    )
    if iteration_manifest:
        for field_name, role in (
            ("result_sha256", "local_asset_bounded_smoke_iteration_result"),
            ("summary_sha256", "local_asset_bounded_smoke_iteration_summary"),
            (
                "human_review_checklist_sha256",
                "local_asset_bounded_smoke_iteration_human_review_checklist",
            ),
            ("signoff_sha256", "local_asset_bounded_smoke_iteration_signoff"),
            ("admission_sha256", "local_asset_bounded_smoke_iteration_admission"),
        ):
            record = records_by_role.get(role, {})
            if record.get("exists") is True and record.get("sha256") != iteration_manifest.get(
                field_name
            ):
                mismatches.append("local_asset_bounded_smoke_iteration_manifest")
    mismatches.extend(
        _index_manifest_mismatch(
            records_by_role,
            source_payloads,
            index_role="iteration_artifact_index",
            manifest_role="iteration_artifact_index_manifest",
        )
    )
    mismatches.extend(
        _index_manifest_mismatch(
            records_by_role,
            source_payloads,
            index_role="smoke_artifact_index",
            manifest_role="smoke_artifact_index_manifest",
        )
    )
    mismatches.extend(
        _index_manifest_mismatch(
            records_by_role,
            source_payloads,
            index_role="scan_artifact_index",
            manifest_role="scan_artifact_index_manifest",
        )
    )
    return mismatches


def _index_manifest_mismatch(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    index_role: str,
    manifest_role: str,
) -> list[str]:
    manifest = _dict_payload(source_payloads, manifest_role)
    index_record = records_by_role.get(index_role, {})
    if not manifest or index_record.get("exists") is not True:
        return []
    if manifest.get("artifact_index_sha256") != index_record.get("sha256"):
        return [manifest_role]
    return []


def _artifact_type_mismatches(source_payloads: dict[str, object]) -> list[str]:
    expected = {
        "local_asset_bounded_smoke_iteration_result": (
            "result_type",
            "local_asset_bounded_smoke_iteration_result_v1",
        ),
        "local_asset_bounded_smoke_iteration_manifest": (
            "manifest_type",
            "local_asset_bounded_smoke_iteration_manifest_v1",
        ),
        "local_asset_bounded_smoke_iteration_signoff": (
            "signoff_type",
            "local_asset_bounded_smoke_iteration_signoff_v1",
        ),
        "local_asset_bounded_smoke_iteration_admission": (
            "admission_type",
            "local_asset_bounded_smoke_iteration_admission_v1",
        ),
        "iteration_artifact_index": (
            "index_type",
            "local_asset_bounded_smoke_iteration_artifact_index_v1",
        ),
        "iteration_artifact_index_manifest": (
            "manifest_type",
            "local_asset_bounded_smoke_iteration_artifact_index_manifest_v1",
        ),
        "smoke_artifact_index": (
            "index_type",
            "local_asset_human_smoke_artifact_index_v1",
        ),
        "smoke_artifact_index_manifest": (
            "manifest_type",
            "local_asset_human_smoke_artifact_index_manifest_v1",
        ),
        "smoke_local_asset_human_smoke_approval": (
            "artifact_type",
            "local_asset_human_smoke_approval_v1",
        ),
        "smoke_local_asset_human_smoke_admission_receipt": (
            "receipt_type",
            "local_asset_human_smoke_admission_receipt_v1",
        ),
    }
    mismatches = []
    for role, (field_name, expected_value) in expected.items():
        payload = _dict_payload(source_payloads, role)
        if payload and payload.get(field_name) != expected_value:
            mismatches.append(role)
    return mismatches


def _iteration_summary(
    iteration_result: dict[str, object],
    admission: dict[str, object],
) -> dict[str, object]:
    return {
        "iteration_status": _first_text(iteration_result.get("iteration_status")),
        "iteration_decision": _first_text(iteration_result.get("iteration_decision")),
        "bounded_smoke_iteration_allowed": _first_bool(
            iteration_result.get("bounded_smoke_iteration_allowed"),
            admission.get("bounded_smoke_iteration_allowed"),
            default=False,
        ),
        "bounded_smoke_iteration_performed": _first_bool(
            iteration_result.get("bounded_smoke_iteration_performed"),
            admission.get("bounded_smoke_iteration_performed"),
            default=False,
        ),
        "smoke_launcher_invoked": _first_bool(
            iteration_result.get("smoke_launcher_invoked"),
            default=False,
        ),
        "smoke_run_complete": _first_bool(
            iteration_result.get("smoke_run_complete"),
            default=False,
        ),
        "scan_complete": _first_bool(
            iteration_result.get("scan_complete"),
            default=False,
        ),
        "max_smoke_files": _first_int(
            iteration_result.get("max_smoke_files"),
            admission.get("max_smoke_files"),
        ),
        "max_smoke_bytes": _first_int(
            iteration_result.get("max_smoke_bytes"),
            admission.get("max_smoke_bytes"),
        ),
        "max_smoke_depth": _first_int(
            iteration_result.get("max_smoke_depth"),
            admission.get("max_smoke_depth"),
        ),
        "recursive": _first_bool(iteration_result.get("recursive"), admission.get("recursive")),
        "include_hidden": _first_bool(
            iteration_result.get("include_hidden"),
            admission.get("include_hidden"),
        ),
        "previous_scan_output_dir": _first_text(
            iteration_result.get("previous_scan_output_dir"),
            admission.get("previous_scan_output_dir"),
        ),
        "iteration_blocker_count": len(
            _list_or_empty(iteration_result.get("iteration_blockers"))
        ),
        "iteration_blockers": _safe_blockers(
            _list_or_empty(iteration_result.get("iteration_blockers"))
        ),
    }


def _signoff_summary(
    signoff: dict[str, object],
    records_by_role: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "signoff_artifact_present": bool(
            records_by_role["local_asset_bounded_smoke_iteration_signoff"]["exists"]
        ),
        "human_signoff_id_present": isinstance(signoff.get("human_signoff_id"), str)
        and bool(signoff.get("human_signoff_id")),
        "human_signoff_valid": _first_bool(signoff.get("signoff_valid"), default=False),
        "human_signoff_phrase_sha256_present": isinstance(
            signoff.get("human_signoff_phrase_sha256"),
            str,
        )
        and len(str(signoff.get("human_signoff_phrase_sha256"))) == 64,
        "human_signoff_phrase_plaintext_persisted": False,
        "human_signoff_phrase_stored": False,
        "required_phrase_recorded": isinstance(signoff.get("required_phrase"), str)
        and bool(signoff.get("required_phrase")),
        "raw_phrase_included": False,
    }


def _admission_summary(
    admission: dict[str, object],
    iteration_result: dict[str, object],
) -> dict[str, object]:
    blockers = _safe_blockers(_list_or_empty(admission.get("admission_blockers")))
    return {
        "admitted": _first_bool(admission.get("admitted"), default=False),
        "admission_blockers": blockers,
        "admission_blocker_count": len(blockers),
        "promotion_gate_status": _first_text(
            admission.get("promotion_gate_status"),
            iteration_result.get("promotion_gate_status"),
        ),
        "promotion_decision": _first_text(
            admission.get("promotion_decision"),
            iteration_result.get("promotion_decision"),
        ),
        "bounded_smoke_iteration_allowed": _first_bool(
            admission.get("bounded_smoke_iteration_allowed"),
            iteration_result.get("bounded_smoke_iteration_allowed"),
            default=False,
        ),
        "bounded_smoke_iteration_performed": _first_bool(
            admission.get("bounded_smoke_iteration_performed"),
            iteration_result.get("bounded_smoke_iteration_performed"),
            default=False,
        ),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_performed": False,
    }


def _promotion_summary(
    admission: dict[str, object],
    iteration_result: dict[str, object],
) -> dict[str, object]:
    return {
        "promotion_gate_status": _first_text(
            iteration_result.get("promotion_gate_status"),
            admission.get("promotion_gate_status"),
        ),
        "promotion_decision": _first_text(
            iteration_result.get("promotion_decision"),
            admission.get("promotion_decision"),
        ),
        "promotion_validated": _first_bool(
            iteration_result.get("promotion_validated"),
            default=False,
        ),
        "production_promotion_granted": False,
        "production_scan_approved": False,
    }


def _delegated_smoke_summary(
    smoke_approval: dict[str, object],
    smoke_admission: dict[str, object],
    records_by_role: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "approval_artifact_present": bool(
            records_by_role["smoke_local_asset_human_smoke_approval"]["exists"]
        ),
        "delegated_human_approval_id_present": isinstance(
            smoke_approval.get("human_approval_id"),
            str,
        )
        and bool(smoke_approval.get("human_approval_id")),
        "delegated_human_approval_phrase_plaintext_persisted": False,
        "delegated_human_approval_phrase_stored": False,
        "admission_receipt_present": bool(
            records_by_role["smoke_local_asset_human_smoke_admission_receipt"][
                "exists"
            ]
        ),
        "admitted": _first_bool(smoke_admission.get("admitted"), default=False),
        "scan_launcher_invoked": _first_bool(
            smoke_admission.get("scan_launcher_invoked"),
            default=False,
        ),
        "scan_complete": _first_bool(smoke_admission.get("scan_complete"), default=False),
        "bounded_smoke_run_performed": _first_bool(
            smoke_admission.get("bounded_smoke_run_performed"),
            default=False,
        ),
        "production_scan_performed": False,
        "failure_stage": _first_text(smoke_admission.get("failure_stage")),
    }


def _scan_summary(
    scan_receipt: dict[str, object],
    asset_manifest: dict[str, object],
    validation_report: dict[str, object],
    records_by_role: dict[str, dict[str, object]],
    *,
    scan_complete: bool,
    duplicate_group_count: int,
    quarantined_path_count: int,
) -> dict[str, object]:
    manifest_counts = _dict_or_empty(asset_manifest.get("counts"))
    validation_counts = _dict_or_empty(validation_report.get("counts"))
    files_scanned = _first_int(
        scan_receipt.get("files_scanned"),
        manifest_counts.get("files_scanned"),
        validation_counts.get("files_scanned"),
    )
    bytes_scanned = _first_int(
        scan_receipt.get("bytes_scanned"),
        manifest_counts.get("bytes_scanned"),
        validation_counts.get("bytes_scanned"),
    )
    return {
        "files_scanned": files_scanned,
        "bytes_scanned": bytes_scanned,
        "scan_complete": scan_complete,
        "scan_success_state": "complete" if scan_complete else "not_complete",
        "duplicate_group_count": duplicate_group_count,
        "quarantined_path_count": quarantined_path_count,
        "scan_artifact_index_present": bool(
            records_by_role["scan_artifact_index"]["exists"]
        ),
    }


def _duplicate_group_count(
    scan_receipt: dict[str, object],
    asset_manifest: dict[str, object],
    validation_report: dict[str, object],
    duplicates_report: dict[str, object],
) -> int:
    manifest_counts = _dict_or_empty(asset_manifest.get("counts"))
    validation_counts = _dict_or_empty(validation_report.get("counts"))
    groups = duplicates_report.get("duplicate_groups")
    return _first_int(
        scan_receipt.get("duplicate_groups"),
        duplicates_report.get("duplicate_sha256_group_count"),
        manifest_counts.get("duplicate_sha256_groups"),
        validation_counts.get("duplicate_sha256_groups"),
        len(groups) if isinstance(groups, list) else None,
        default=0,
    )


def _duplicate_asset_count(duplicates_report: dict[str, object]) -> int:
    count = _first_int(duplicates_report.get("duplicate_file_count"))
    if count is not None:
        return count
    groups = duplicates_report.get("duplicate_groups")
    if not isinstance(groups, list):
        return 0
    total = 0
    for group in groups:
        if isinstance(group, dict):
            total += _first_int(group.get("count"), default=0) or 0
    return total


def _quarantined_path_count(
    scan_receipt: dict[str, object],
    asset_manifest: dict[str, object],
    validation_report: dict[str, object],
    quarantine_manifest: dict[str, object],
) -> int:
    manifest_counts = _dict_or_empty(asset_manifest.get("counts"))
    validation_counts = _dict_or_empty(validation_report.get("counts"))
    items = quarantine_manifest.get("items")
    return _first_int(
        quarantine_manifest.get("quarantined_path_count"),
        manifest_counts.get("quarantined_paths"),
        validation_counts.get("quarantined_paths"),
        scan_receipt.get("quarantined_path_count"),
        scan_receipt.get("quarantined_paths"),
        len(items) if isinstance(items, list) else None,
        default=0,
    )


def _quarantine_summary(
    quarantine_manifest: dict[str, object],
    quarantined_path_count: int,
) -> dict[str, object]:
    counts = _dict_or_empty(quarantine_manifest.get("counts_by_reason"))
    items = quarantine_manifest.get("items")
    item_list = items if isinstance(items, list) else []
    reason_counts: dict[str, int] = {}
    for reason, count in counts.items():
        if isinstance(count, int) and not isinstance(count, bool):
            reason_counts[str(reason)] = int(count)
    if not reason_counts and item_list:
        for item in item_list:
            if isinstance(item, dict):
                reason = str(item.get("reason", "unknown"))
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    symlink_count = sum(
        1
        for item in item_list
        if isinstance(item, dict)
        and (
            str(item.get("path_type")) == "symlink"
            or "symlink" in str(item.get("reason", ""))
        )
    )
    unsafe_count = reason_counts.get("unsafe_directory", 0) + reason_counts.get(
        "unsafe_path",
        0,
    )
    return {
        "quarantined_path_count": quarantined_path_count,
        "top_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                reason_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ],
        "secret_looking_path_count": reason_counts.get("secret_looking_path", 0),
        "symlink_count": symlink_count,
        "unsafe_path_count": unsafe_count,
        "deletion_suggested": False,
        "recommended_action": "human_inspect_only",
        "relative_paths_included": False,
    }


def _incremental_counts(plan: dict[str, object]) -> dict[str, object]:
    return {
        "plan_mode": _first_text(plan.get("plan_mode")),
        "unchanged_asset_count": _first_int(
            plan.get("unchanged_asset_count"),
            default=0,
        ),
        "changed_asset_count": _first_int(plan.get("changed_asset_count"), default=0),
        "new_asset_count": _first_int(plan.get("new_asset_count"), default=0),
        "missing_asset_count": _first_int(plan.get("missing_asset_count"), default=0),
        "suspicious_change_count": _first_int(
            plan.get("suspicious_change_count"),
            default=0,
        ),
    }


def _failure_summary(
    failure_bundle: dict[str, object],
    iteration_result: dict[str, object],
    admission: dict[str, object],
    smoke_admission: dict[str, object],
) -> dict[str, object]:
    iteration_blockers = _safe_blockers(
        _list_or_empty(iteration_result.get("iteration_blockers"))
    )
    return {
        "iteration_blockers": iteration_blockers,
        "iteration_blocker_count": len(iteration_blockers),
        "delegated_smoke_failure_stage": _first_text(
            smoke_admission.get("failure_stage"),
            iteration_result.get("failure_stage"),
            admission.get("failure_stage"),
        ),
        "scan_failure_bundle_present": bool(failure_bundle),
        "safe_to_retry": _first_bool(failure_bundle.get("safe_to_retry")),
        "safe_error_message": _safe_text(failure_bundle.get("safe_error_message"))
        if failure_bundle
        else None,
        "raw_traceback_copied": False,
        "raw_exception_dump_copied": False,
        "secret_value_serialized": False,
    }


def _warning_items(
    *,
    source_state: dict[str, object],
    iteration_summary: dict[str, object],
    delegated_smoke_summary: dict[str, object],
    duplicate_group_count: int,
    quarantined_path_count: int,
    incremental_counts: dict[str, object],
) -> list[str]:
    warnings = []
    missing_optional = [
        role
        for role in source_state["missing_optional_artifacts"]
        if role
        not in (
            "scan_asset_scan_failure_bundle",
            "scan_asset_scan_failure_summary",
        )
    ]
    if missing_optional:
        warnings.append("missing_optional_artifacts")
    if iteration_summary["iteration_status"] != "iteration_completed":
        warnings.append("failed_iteration")
    if delegated_smoke_summary["scan_complete"] is not True:
        warnings.append("incomplete_delegated_smoke")
    if quarantined_path_count > 0:
        warnings.append("quarantine_present")
    if duplicate_group_count > 0:
        warnings.append("duplicate_groups_present")
    if int(incremental_counts["suspicious_change_count"]) > 0:
        warnings.append("suspicious_incremental_changes_present")
    if _incremental_needs_inspection(incremental_counts):
        warnings.append("incremental_changes_present")
    if source_state["untrusted_artifacts"]:
        warnings.append("untrusted_generated_artifact")
        warnings.append("generated_artifact_hash_mismatch")
    return sorted(set(warnings))


def _iteration_review_status(
    *,
    source_state: dict[str, object],
    iteration_summary: dict[str, object],
    warnings: list[str],
) -> str:
    if source_state["missing_required_artifacts"]:
        return "review_blocked_missing_required_artifacts"
    if source_state["untrusted_artifacts"]:
        return "review_blocked_untrusted_artifacts"
    if (
        iteration_summary["iteration_status"] != "iteration_completed"
        or iteration_summary["scan_complete"] is not True
    ):
        return "review_blocked_failed_iteration"
    if warnings:
        return "review_ready_with_warnings"
    return "review_ready"


def _recommended_human_decision(
    *,
    iteration_review_status: str,
    duplicate_group_count: int,
    quarantined_path_count: int,
    incremental_counts: dict[str, object],
) -> str:
    if iteration_review_status not in _READY_STATUSES:
        return _REJECT_DECISION
    if quarantined_path_count > 0:
        return _INSPECT_QUARANTINE_DECISION
    if duplicate_group_count > 0:
        return _INSPECT_DUPLICATES_DECISION
    if _incremental_needs_inspection(incremental_counts):
        return _INSPECT_INCREMENTAL_DECISION
    return _APPROVE_DECISION


def _incremental_needs_inspection(incremental_counts: dict[str, object]) -> bool:
    if int(incremental_counts["suspicious_change_count"]) > 0:
        return True
    return (
        incremental_counts["plan_mode"] == "compare_previous_scan"
        and (
            int(incremental_counts["changed_asset_count"]) > 0
            or int(incremental_counts["new_asset_count"]) > 0
            or int(incremental_counts["missing_asset_count"]) > 0
        )
    )


def _decision_checklist_payload() -> dict[str, object]:
    items = (
        "Verify iteration status is iteration_completed.",
        "Verify promotion gate allowed only next bounded smoke iteration.",
        "Verify production_promotion_granted=false.",
        "Verify production_scan_approved=false.",
        "Verify production_scan_performed=false.",
        "Verify signoff phrase plaintext was not persisted.",
        "Verify delegated smoke approval phrase plaintext was not persisted.",
        "Verify smoke launcher invoked only after valid gate + signoff.",
        "Verify bounded limits were enforced.",
        "Verify scan_complete status.",
        "Review quarantine summary.",
        "Review duplicate summary.",
        "Review SQLite summary.",
        "Review incremental plan summary.",
    )
    return {
        "checklist_type": "local_asset_smoke_iteration_human_decision_checklist_v1",
        "items": [{"text": item, "checked": False} for item in items],
        "decision_options": list(_DECISION_OPTIONS),
        "raw_private_file_contents_included": False,
        "automatic_approval_granted": False,
        "production_autonomy_granted": False,
        "production_scan_recommended": False,
    }


def _summary_markdown(packet: dict[str, object]) -> str:
    iteration = packet["iteration_summary"]
    signoff = packet["signoff_summary"]
    admission = packet["admission_summary"]
    promotion = packet["promotion_summary"]
    smoke = packet["delegated_smoke_summary"]
    scan = packet["delegated_scan_summary"]
    duplicate = packet["duplicate_summary"]
    quarantine = packet["quarantine_summary"]
    sqlite = packet["sqlite_summary"]
    incremental = packet["incremental_summary"]
    failure = packet["failure_summary"]
    warnings = packet["warning_summary"]
    lines = [
        "# Local Asset Smoke Iteration Review Summary",
        "",
        "- Iteration review status: `" + str(packet["iteration_review_status"]) + "`",
        "- Recommended human decision: `"
        + str(packet["recommended_human_decision"])
        + "`",
        "- Iteration output dir: `" + str(packet["iteration_output_dir"]) + "`",
        "- Review output dir: `" + str(packet["output_dir"]) + "`",
        "- Project id: `" + str(packet["project_id"]) + "`",
        "",
        "## Iteration Summary",
        "",
        "- Iteration status: `" + str(iteration["iteration_status"]) + "`",
        "- Iteration decision: `" + str(iteration["iteration_decision"]) + "`",
        "- Bounded smoke iteration allowed: "
        + _bool_text(iteration["bounded_smoke_iteration_allowed"]),
        "- Bounded smoke iteration performed: "
        + _bool_text(iteration["bounded_smoke_iteration_performed"]),
        "- Smoke launcher invoked: " + _bool_text(iteration["smoke_launcher_invoked"]),
        "- Smoke run complete: " + _bool_text(iteration["smoke_run_complete"]),
        "- Scan complete: " + _bool_text(iteration["scan_complete"]),
        "- Max smoke files: " + str(iteration["max_smoke_files"]),
        "- Max smoke bytes: " + str(iteration["max_smoke_bytes"]),
        "- Max smoke depth: " + str(iteration["max_smoke_depth"]),
        "- Recursive: " + _bool_text(iteration["recursive"]),
        "- Include hidden: " + _bool_text(iteration["include_hidden"]),
        "- Previous scan output dir: `"
        + str(iteration["previous_scan_output_dir"])
        + "`",
        "",
        "## Signoff Summary",
        "",
        "- Signoff artifact present: "
        + _bool_text(signoff["signoff_artifact_present"]),
        "- Human signoff id present: "
        + _bool_text(signoff["human_signoff_id_present"]),
        "- Human signoff valid: " + _bool_text(signoff["human_signoff_valid"]),
        "- Signoff phrase plaintext persisted: false",
        "- Signoff phrase stored: false",
        "- Required phrase recorded: "
        + _bool_text(signoff["required_phrase_recorded"]),
        "- Raw phrase included: false",
        "",
        "## Admission Summary",
        "",
        "- Admitted: " + _bool_text(admission["admitted"]),
        "- Admission blocker count: " + str(admission["admission_blocker_count"]),
        "- Promotion gate status: `" + str(admission["promotion_gate_status"]) + "`",
        "- Promotion decision: `" + str(admission["promotion_decision"]) + "`",
        "- Bounded smoke iteration allowed: "
        + _bool_text(admission["bounded_smoke_iteration_allowed"]),
        "- Bounded smoke iteration performed: "
        + _bool_text(admission["bounded_smoke_iteration_performed"]),
        "- Production promotion granted: false",
        "- Production scan approved: false",
        "- Production scan performed: false",
        "",
        "## Promotion Summary",
        "",
        "- Promotion gate status: `" + str(promotion["promotion_gate_status"]) + "`",
        "- Promotion decision: `" + str(promotion["promotion_decision"]) + "`",
        "- Promotion validated: " + _bool_text(promotion["promotion_validated"]),
        "- Production promotion granted: false",
        "- Production scan approved: false",
        "",
        "## Delegated Smoke Summary",
        "",
        "- Approval artifact present: "
        + _bool_text(smoke["approval_artifact_present"]),
        "- Delegated approval phrase plaintext persisted: false",
        "- Admission receipt present: "
        + _bool_text(smoke["admission_receipt_present"]),
        "- Admitted: " + _bool_text(smoke["admitted"]),
        "- Scan launcher invoked: " + _bool_text(smoke["scan_launcher_invoked"]),
        "- Scan complete: " + _bool_text(smoke["scan_complete"]),
        "- Bounded smoke run performed: "
        + _bool_text(smoke["bounded_smoke_run_performed"]),
        "- Production scan performed: false",
        "",
        "## Delegated Scan Summary",
        "",
        "- Files scanned: " + str(scan["files_scanned"]),
        "- Bytes scanned: " + str(scan["bytes_scanned"]),
        "- Scan complete: " + _bool_text(scan["scan_complete"]),
        "- Scan artifact index present: "
        + _bool_text(scan["scan_artifact_index_present"]),
        "",
        "## Duplicate Summary",
        "",
        "- Duplicate group count: " + str(duplicate["duplicate_group_count"]),
        "- Duplicate asset count: " + str(duplicate["duplicate_asset_count"]),
        "- Deletion suggested: false",
        "- Automatic dedupe performed: false",
        "- Recommended action: human inspect only",
        "",
        "## Quarantine Summary",
        "",
        "- Quarantined path count: "
        + str(quarantine["quarantined_path_count"]),
        "- Secret-looking path count: "
        + str(quarantine["secret_looking_path_count"]),
        "- Symlink count: " + str(quarantine["symlink_count"]),
        "- Unsafe path count: " + str(quarantine["unsafe_path_count"]),
        "- Deletion suggested: false",
        "- Recommended action: human inspect only",
        "",
        "## SQLite Summary",
        "",
        "- Database present: " + _bool_text(sqlite["database_present"]),
        "- Manifest present: " + _bool_text(sqlite["manifest_present"]),
        "- Query summary present: " + _bool_text(sqlite["query_summary_present"]),
        "- Row counts from manifest: `"
        + json.dumps(sqlite["row_counts"], sort_keys=True)
        + "`",
        "- Global database state used: false",
        "",
        "## Incremental Summary",
        "",
        "- Plan present: " + _bool_text(incremental["plan_present"]),
        "- Plan mode: `" + str(incremental["plan_mode"]) + "`",
        "- Unchanged asset count: "
        + str(incremental["unchanged_asset_count"]),
        "- Changed asset count: " + str(incremental["changed_asset_count"]),
        "- New asset count: " + str(incremental["new_asset_count"]),
        "- Missing asset count: " + str(incremental["missing_asset_count"]),
        "- Suspicious change count: "
        + str(incremental["suspicious_change_count"]),
        "- Automatic skip performed: false",
        "- Cache execution performed: false",
        "",
        "## Failure And Warning Summary",
        "",
        "- Iteration blocker count: " + str(failure["iteration_blocker_count"]),
        "- Delegated smoke failure stage: `"
        + str(failure["delegated_smoke_failure_stage"])
        + "`",
        "- Scan failure bundle present: "
        + _bool_text(failure["scan_failure_bundle_present"]),
        "- Raw traceback copied: false",
        "- Secret value serialized: false",
        "- Warning count: " + str(warnings["warning_count"]),
        "- Warnings: `" + json.dumps(warnings["warnings"]) + "`",
        "",
        "## Source Artifact Counts",
        "",
        "- Source artifact count: "
        + str(packet["artifact_summary"]["source_artifact_count"]),
        "- Missing artifact count: "
        + str(packet["generated_artifacts_missing_count"]),
        "",
        "## Explicit Boundaries",
        "",
        "- no scan performed by review packet",
        "- no readiness run performed",
        "- no human smoke run performed by review packet",
        "- no bounded smoke iteration performed by review packet",
        "- no promotion gate run performed",
        "- no raw candidate content read",
        "- no candidate hashing performed",
        "- no input mutation",
        "- no iteration output mutation",
        "- no smoke output mutation",
        "- no file move/rename/delete",
        "- no duplicate deletion",
        "- no media organizer behavior",
        "- no production scan recommendation",
        "- human approval required for next step",
    ]
    summary = "\n".join(lines) + "\n"
    _assert_no_raw_phrase_text(summary)
    return summary


def _decision_checklist_markdown(packet: dict[str, object]) -> str:
    lines = [
        "# Local Asset Smoke Iteration Human Decision Checklist",
        "",
        "- [ ] Verify iteration status is iteration_completed.",
        "- [ ] Verify promotion gate allowed only next bounded smoke iteration.",
        "- [ ] Verify production_promotion_granted=false.",
        "- [ ] Verify production_scan_approved=false.",
        "- [ ] Verify production_scan_performed=false.",
        "- [ ] Verify signoff phrase plaintext was not persisted.",
        "- [ ] Verify delegated smoke approval phrase plaintext was not persisted.",
        "- [ ] Verify smoke launcher invoked only after valid gate + signoff.",
        "- [ ] Verify bounded limits were enforced.",
        "- [ ] Verify scan_complete status.",
        "- [ ] Review quarantine summary.",
        "- [ ] Review duplicate summary.",
        "- [ ] Review SQLite summary.",
        "- [ ] Review incremental plan summary.",
        "",
        "## Decide One",
        "",
    ]
    for option in _DECISION_OPTIONS:
        checked = "x" if option == packet["recommended_human_decision"] else " "
        lines.append(f"- [{checked}] {option}")
    lines.extend(
        [
            "",
            "Do not include raw private file contents.",
            "Do not suggest deleting, moving, or renaming files.",
            "Do not suggest automatic dedupe.",
            "Do not grant production autonomy.",
            "Do not recommend production scan.",
        ]
    )
    checklist = "\n".join(lines) + "\n"
    _assert_no_raw_phrase_text(checklist)
    return checklist


def _packet_manifest_payload(
    *,
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    iteration_review_status: str,
    recommended_human_decision: str,
) -> dict[str, object]:
    packet_path = paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE]
    summary_path = paths[LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE]
    checklist_path = paths[LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE]
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "packet_path": packet_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "decision_checklist_path": checklist_path.as_posix(),
        "packet_sha256": sha256_file(packet_path),
        "summary_sha256": sha256_file(summary_path),
        "decision_checklist_sha256": sha256_file(checklist_path),
        "source_artifacts": [
            {
                "artifact_role": record["artifact_role"],
                "path": record["path"],
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
                "exists": record["exists"],
                "required": record["required"],
                "trusted_generated_artifact": record["trusted_generated_artifact"],
            }
            for record in source_artifacts
        ],
        "iteration_review_status": iteration_review_status,
        "recommended_human_decision": recommended_human_decision,
        "deterministic_ordering": True,
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    _assert_no_raw_phrase_leak(payload)
    return payload


def _artifact_index_payload(
    output_path: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = []
    for role, file_name in _REVIEW_ARTIFACTS:
        entries.append(_review_artifact_entry(output_path, role, paths[file_name]))
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "explicit_iteration_review_packet_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "iteration_output_files_recursively_indexed": False,
        "deterministic_ordering": True,
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    return {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_sha256": sha256_file(paths[_ARTIFACT_INDEX_FILE]),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [
            str(entry["relative_path"]) for entry in entries
        ],
        "job_dir": output_path.as_posix(),
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "iteration_output_files_recursively_indexed": False,
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _review_artifact_entry(root_path: Path, role: str, path: Path) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": _relative_path(path, root_path),
        "extension": path.suffix,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
    }


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _launcher_payload_from_packet(
    packet: dict[str, object],
    paths: dict[str, Path],
) -> dict[str, object]:
    incremental = packet["incremental_summary"]
    return {
        "local_asset_smoke_iteration_review_packet_path": paths[
            LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_FILE
        ].as_posix(),
        "local_asset_smoke_iteration_review_packet_manifest_path": paths[
            LOCAL_ASSET_SMOKE_ITERATION_REVIEW_PACKET_MANIFEST_FILE
        ].as_posix(),
        "local_asset_smoke_iteration_review_summary_path": paths[
            LOCAL_ASSET_SMOKE_ITERATION_REVIEW_SUMMARY_FILE
        ].as_posix(),
        "local_asset_smoke_iteration_human_decision_checklist_path": paths[
            LOCAL_ASSET_SMOKE_ITERATION_HUMAN_DECISION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "iteration_output_dir": packet["iteration_output_dir"],
        "output_dir": packet["output_dir"],
        "project_id": packet["project_id"],
        "iteration_review_status": packet["iteration_review_status"],
        "recommended_human_decision": packet["recommended_human_decision"],
        "iteration_status": packet["iteration_status"],
        "iteration_decision": packet["iteration_decision"],
        "promotion_gate_status": packet["promotion_gate_status"],
        "promotion_decision": packet["promotion_decision"],
        "human_signoff_valid": packet["human_signoff_valid"],
        "bounded_smoke_iteration_performed": packet[
            "bounded_smoke_iteration_performed"
        ],
        "smoke_launcher_invoked": packet["smoke_launcher_invoked"],
        "smoke_run_complete": packet["smoke_run_complete"],
        "scan_complete": packet["scan_complete"],
        "duplicate_group_count": packet["duplicate_group_count"],
        "quarantined_path_count": packet["quarantined_path_count"],
        "incremental_plan_mode": incremental["plan_mode"],
        "changed_asset_count": incremental["changed_asset_count"],
        "new_asset_count": incremental["new_asset_count"],
        "missing_asset_count": incremental["missing_asset_count"],
        "suspicious_change_count": incremental["suspicious_change_count"],
        "warning_count": packet["warning_count"],
        "generated_artifacts_read_count": packet["generated_artifacts_read_count"],
        "generated_artifacts_missing_count": packet[
            "generated_artifacts_missing_count"
        ],
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _structured_failure_result(
    *,
    iteration_path: Path,
    output_path: Path,
    failure_stage: str,
    error_message: str,
    project_id: str | None,
) -> LocalAssetSmokeIterationReviewPacketResult:
    status = "review_blocked_missing_required_artifacts"
    payload = {
        "complete": False,
        "iteration_output_dir": iteration_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "project_id": project_id,
        "iteration_review_status": status,
        "recommended_human_decision": _REJECT_DECISION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "local_asset_smoke_iteration_review_packet_path": None,
        "local_asset_smoke_iteration_review_packet_manifest_path": None,
        "local_asset_smoke_iteration_review_summary_path": None,
        "local_asset_smoke_iteration_human_decision_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "iteration_status": None,
        "iteration_decision": None,
        "promotion_gate_status": None,
        "promotion_decision": None,
        "human_signoff_valid": False,
        "bounded_smoke_iteration_performed": False,
        "smoke_launcher_invoked": False,
        "smoke_run_complete": False,
        "scan_complete": False,
        "duplicate_group_count": 0,
        "quarantined_path_count": 0,
        "incremental_plan_mode": None,
        "changed_asset_count": 0,
        "new_asset_count": 0,
        "missing_asset_count": 0,
        "suspicious_change_count": 0,
        "warning_count": 0,
        "generated_artifacts_read_count": 0,
        "generated_artifacts_missing_count": len(_SOURCE_ARTIFACTS),
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    return LocalAssetSmokeIterationReviewPacketResult(
        iteration_output_dir=iteration_path,
        output_dir=output_path,
        packet_path=None,
        packet_manifest_path=None,
        summary_path=None,
        decision_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        iteration_review_status=status,
        recommended_human_decision=_REJECT_DECISION,
        payload=payload,
    )


def _dict_payload(payloads: dict[str, object], role: str) -> dict[str, object]:
    payload = payloads.get(role)
    return payload if isinstance(payload, dict) else {}


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _safe_blockers(items: list[object]) -> list[dict[str, object]]:
    blockers = []
    for item in items:
        if not isinstance(item, dict):
            continue
        safe_item = {}
        for key, value in sorted(item.items()):
            if key in {"traceback", "raw_traceback", "exception", "secret"}:
                continue
            if isinstance(value, (str, int, bool)) or value is None:
                safe_item[str(key)] = _safe_text(value) if isinstance(value, str) else value
        blockers.append(safe_item)
    return blockers


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_bool(*values: object, default: bool | None = None) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
    return default


def _first_int(*values: object, default: int | None = None) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return default


def _safe_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.replace("\n", " ").replace("\r", " ")
    for sentinel in _RAW_PHRASE_SENTINELS:
        text = text.replace(sentinel, "[redacted_phrase]")
    return text[:500]


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _assert_no_raw_phrase_leak(payload: dict[str, object]) -> None:
    _assert_no_raw_phrase_text(json.dumps(payload, sort_keys=True))


def _assert_no_raw_phrase_text(text: str) -> None:
    for sentinel in _RAW_PHRASE_SENTINELS:
        if sentinel in text:
            raise ValueError("raw approval phrase leakage detected")


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _assert_no_raw_phrase_leak(payload)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, text: str) -> None:
    _assert_no_raw_phrase_text(text)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
