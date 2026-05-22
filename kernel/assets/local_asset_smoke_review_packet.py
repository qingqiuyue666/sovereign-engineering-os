"""Post-smoke-run review packet for human-approved local asset smoke runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE",
    "LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE",
    "LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE",
    "LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE",
    "LocalAssetSmokeReviewPacketResult",
    "build_local_asset_smoke_review_packet",
]

LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE = "local_asset_smoke_review_packet.json"
LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE = (
    "local_asset_smoke_review_packet_manifest.json"
)
LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE = "local_asset_smoke_review_summary.md"
LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE = (
    "local_asset_smoke_human_decision_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_PACKET_TYPE = "local_asset_smoke_review_packet_v1"
_MANIFEST_TYPE = "local_asset_smoke_review_packet_manifest_v1"
_INDEX_TYPE = "local_asset_smoke_review_packet_artifact_index_v1"
_INDEX_MANIFEST_TYPE = "local_asset_smoke_review_packet_artifact_index_manifest_v1"
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_smoke_review_packet_only"
_NEXT_ALLOWED_ACTION = "human_review_smoke_review_packet"

_READY_STATUSES = {"review_ready", "review_ready_with_warnings"}
_REJECT_DECISION = "reject_and_repair_smoke_run"
_APPROVE_DECISION = "approve_next_bounded_smoke_iteration"
_INSPECT_QUARANTINE_DECISION = "inspect_quarantine_before_next_run"
_INSPECT_DUPLICATES_DECISION = "inspect_duplicates_before_next_run"
_INSPECT_INCREMENTAL_DECISION = "inspect_incremental_changes_before_next_run"

_OUTPUT_FILES = (
    LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE,
    LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE,
    LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE,
    LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_BOUNDARY_FLAGS = {
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
    "scan_performed": False,
    "readiness_run_performed": False,
    "input_mutation_performed": False,
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

_DECISION_OPTIONS = (
    _APPROVE_DECISION,
    _INSPECT_QUARANTINE_DECISION,
    _INSPECT_DUPLICATES_DECISION,
    _INSPECT_INCREMENTAL_DECISION,
    _REJECT_DECISION,
)


@dataclass(frozen=True)
class _SourceArtifactSpec:
    artifact_role: str
    relative_path: str
    required: bool
    json_artifact: bool


_SOURCE_ARTIFACTS = (
    _SourceArtifactSpec("smoke_root_artifact_index", "artifact_index.json", True, True),
    _SourceArtifactSpec(
        "smoke_root_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_human_smoke_run_summary",
        "local_asset_human_smoke_run_summary.md",
        True,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_human_smoke_approval",
        "control/local_asset_human_smoke_approval.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_human_smoke_admission_receipt",
        "control/local_asset_human_smoke_admission_receipt.json",
        True,
        True,
    ),
    _SourceArtifactSpec("scan_artifact_index", "scan/artifact_index.json", False, True),
    _SourceArtifactSpec(
        "scan_artifact_index_manifest",
        "scan/artifact_index_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_asset_manifest", "scan/asset_manifest.json", False, True),
    _SourceArtifactSpec("scan_asset_index", "scan/asset_index.json", False, True),
    _SourceArtifactSpec(
        "scan_duplicates_report",
        "scan/duplicates_report.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_media_inventory", "scan/media_inventory.md", False, False),
    _SourceArtifactSpec(
        "scan_asset_runtime_audit_log",
        "scan/asset_runtime_audit_log.jsonl",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_asset_runtime_validation_report",
        "scan/asset_runtime_validation_report.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_runtime_quarantine_manifest",
        "scan/asset_runtime_quarantine_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_run_receipt",
        "scan/asset_scan_run_receipt.json",
        False,
        True,
    ),
    _SourceArtifactSpec("scan_launcher_summary", "scan/launcher_summary.md", False, False),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_index",
        "scan/local_asset_index.sqlite",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_index_manifest",
        "scan/local_asset_sqlite_index_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_sqlite_query_summary",
        "scan/local_asset_sqlite_query_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_plan",
        "scan/local_asset_incremental_scan_plan.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_manifest",
        "scan/local_asset_incremental_scan_manifest.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_local_asset_incremental_scan_summary",
        "scan/local_asset_incremental_scan_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_failure_bundle",
        "scan/asset_scan_failure_bundle.json",
        False,
        True,
    ),
    _SourceArtifactSpec(
        "scan_asset_scan_failure_summary",
        "scan/asset_scan_failure_summary.md",
        False,
        False,
    ),
)

_REVIEW_ARTIFACTS = (
    ("local_asset_smoke_review_packet", LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE),
    (
        "local_asset_smoke_review_packet_manifest",
        LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE,
    ),
    ("local_asset_smoke_review_summary", LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE),
    (
        "local_asset_smoke_human_decision_checklist",
        LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE,
    ),
)


@dataclass(frozen=True)
class LocalAssetSmokeReviewPacketResult:
    smoke_output_dir: Path
    output_dir: Path
    packet_path: Path | None
    packet_manifest_path: Path | None
    summary_path: Path | None
    decision_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    review_packet_status: str
    recommended_human_decision: str
    payload: dict[str, object]


def build_local_asset_smoke_review_packet(
    smoke_output_dir: Path,
    output_dir: Path,
    *,
    project_id: str | None = None,
) -> LocalAssetSmokeReviewPacketResult:
    """Build a metadata-only human review packet from generated smoke artifacts."""

    smoke_path = Path(smoke_output_dir)
    output_path = Path(output_dir)
    paths = _review_output_paths(output_path)
    output_error = _real_existing_dir_error(output_path, "output_dir")
    if output_error is not None:
        return _structured_failure_result(
            smoke_path=smoke_path,
            output_path=output_path,
            failure_stage="preflight_output_dir_missing",
            error_message=output_error,
            project_id=project_id,
        )

    collision = _existing_output_collision(paths)
    if collision is not None:
        return _structured_failure_result(
            smoke_path=smoke_path,
            output_path=output_path,
            failure_stage="preflight_output_collision",
            error_message="local asset smoke review output already exists: "
            + collision,
            project_id=project_id,
        )

    overlap_error = _existing_dir_overlap_error(smoke_path, output_path)
    if overlap_error is not None:
        return _structured_failure_result(
            smoke_path=smoke_path,
            output_path=output_path,
            failure_stage="preflight_smoke_output_overlap",
            error_message=overlap_error,
            project_id=project_id,
        )

    smoke_error = _real_existing_dir_error(smoke_path, "smoke_output_dir")
    source_artifacts = _source_artifact_records(smoke_path, smoke_error=smoke_error)
    source_payloads = _read_json_source_payloads(source_artifacts)

    candidate_overlap = _candidate_output_overlap_error(source_payloads, output_path)
    if candidate_overlap is not None:
        return _structured_failure_result(
            smoke_path=smoke_path,
            output_path=output_path,
            failure_stage="preflight_candidate_output_overlap",
            error_message=candidate_overlap,
            project_id=project_id,
        )

    packet = _build_packet_payload(
        smoke_output_dir=smoke_path,
        output_dir=output_path,
        project_id=project_id,
        smoke_error=smoke_error,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(packet)
    checklist = _decision_checklist_markdown(packet)

    _write_json_exclusive(paths[LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE], packet)
    _write_text_exclusive(paths[LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE], summary)
    _write_text_exclusive(
        paths[LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE],
        checklist,
    )
    packet_manifest = _packet_manifest_payload(
        paths=paths,
        source_artifacts=source_artifacts,
        review_packet_status=str(packet["review_packet_status"]),
        recommended_human_decision=str(packet["recommended_human_decision"]),
    )
    _write_json_exclusive(
        paths[LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE],
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

    complete = packet["review_packet_status"] in _READY_STATUSES
    payload = _launcher_payload_from_packet(packet, paths)
    return LocalAssetSmokeReviewPacketResult(
        smoke_output_dir=smoke_path,
        output_dir=output_path,
        packet_path=paths[LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE],
        packet_manifest_path=paths[LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE],
        summary_path=paths[LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE],
        decision_checklist_path=paths[
            LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        review_packet_status=str(packet["review_packet_status"]),
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


def _existing_dir_overlap_error(smoke_path: Path, output_path: Path) -> str | None:
    if not smoke_path.exists() or not output_path.exists():
        return None
    try:
        smoke_resolved = smoke_path.resolve(strict=True)
        output_resolved = output_path.resolve(strict=True)
    except OSError:
        return None
    if smoke_resolved == output_resolved:
        return "output_dir must not equal smoke_output_dir"
    if _path_is_inside(output_resolved, smoke_resolved):
        return "output_dir must not be inside smoke_output_dir"
    if _path_is_inside(smoke_resolved, output_resolved):
        return "smoke_output_dir must not be inside output_dir"
    return None


def _candidate_output_overlap_error(
    source_payloads: dict[str, object],
    output_path: Path,
) -> str | None:
    admission = _dict_payload(
        source_payloads,
        "local_asset_human_smoke_admission_receipt",
    )
    candidate_value = admission.get("candidate_input_dir")
    if not isinstance(candidate_value, str) or not candidate_value:
        return None
    candidate_path = Path(candidate_value)
    if _path_is_inside(output_path, candidate_path):
        return "output_dir must not be inside candidate_input_dir"
    return None


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _source_artifact_records(
    smoke_path: Path,
    *,
    smoke_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for spec in _SOURCE_ARTIFACTS:
        path = smoke_path / spec.relative_path
        if smoke_error is not None:
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


def _missing_source_record(spec: _SourceArtifactSpec, path: Path) -> dict[str, object]:
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
    smoke_output_dir: Path,
    output_dir: Path,
    project_id: str | None,
    smoke_error: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    records_by_role = {
        str(record["artifact_role"]): record for record in source_artifacts
    }
    admission = _dict_payload(
        source_payloads,
        "local_asset_human_smoke_admission_receipt",
    )
    approval = _dict_payload(source_payloads, "local_asset_human_smoke_approval")
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

    smoke_run_admitted = bool(admission.get("admitted", False))
    scan_launcher_invoked = bool(admission.get("scan_launcher_invoked", False))
    scan_complete = bool(admission.get("scan_complete", False))
    bounded_smoke_run_performed = bool(
        admission.get("bounded_smoke_run_performed", False)
    )
    production_scan_performed = bool(admission.get("production_scan_performed", False))
    failure_stage = _first_text(
        admission.get("failure_stage"),
        failure_bundle.get("failure_stage"),
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
    project = _first_text(
        project_id,
        admission.get("project_id"),
        approval.get("project_id"),
        scan_receipt.get("project_id"),
        asset_manifest.get("project_id"),
    )

    source_state = _source_state(
        source_artifacts,
        records_by_role,
        source_payloads,
        smoke_error=smoke_error,
    )
    warnings = _warning_items(
        source_state=source_state,
        scan_complete=scan_complete,
        duplicate_group_count=duplicate_group_count,
        quarantined_path_count=quarantined_path_count,
        incremental_counts=incremental_counts,
    )
    review_packet_status = _review_packet_status(
        source_state=source_state,
        smoke_run_admitted=smoke_run_admitted,
        scan_complete=scan_complete,
        warnings=warnings,
    )
    recommended_human_decision = _recommended_human_decision(
        review_packet_status=review_packet_status,
        duplicate_group_count=duplicate_group_count,
        quarantined_path_count=quarantined_path_count,
        incremental_counts=incremental_counts,
    )

    packet = {
        "packet_type": _PACKET_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "smoke_output_dir": smoke_output_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "project_id": project,
        "review_packet_status": review_packet_status,
        "recommended_human_decision": recommended_human_decision,
        "smoke_run_summary": {
            "smoke_run_complete": scan_complete,
            "smoke_run_admitted": smoke_run_admitted,
            "scan_launcher_invoked": scan_launcher_invoked,
            "scan_complete": scan_complete,
            "bounded_smoke_run_performed": bounded_smoke_run_performed,
            "production_scan_performed": production_scan_performed,
            "failure_stage": failure_stage,
        },
        "approval_summary": {
            "approval_artifact_present": bool(
                records_by_role["local_asset_human_smoke_approval"]["exists"]
            ),
            "human_approval_id_present": isinstance(
                approval.get("human_approval_id"),
                str,
            )
            and bool(approval.get("human_approval_id")),
            "approval_phrase_plaintext_persisted": False,
            "approval_phrase_stored": False,
        },
        "admission_summary": {
            "admitted": smoke_run_admitted,
            "scan_launcher_invoked": scan_launcher_invoked,
            "scan_complete": scan_complete,
            "failure_stage": failure_stage,
            "bounded_smoke_run_performed": bounded_smoke_run_performed,
            "production_scan_performed": production_scan_performed,
        },
        "readiness_summary": _readiness_summary(admission, approval),
        "scan_summary": _scan_summary(
            scan_receipt,
            asset_manifest,
            validation_report,
            records_by_role,
            scan_complete=scan_complete,
            duplicate_group_count=duplicate_group_count,
            quarantined_path_count=quarantined_path_count,
        ),
        "artifact_summary": {
            "source_artifact_count": len(source_artifacts),
            "generated_artifacts_read_count": source_state[
                "generated_artifacts_read_count"
            ],
            "generated_artifacts_missing_count": source_state[
                "generated_artifacts_missing_count"
            ],
            "missing_required_artifacts": source_state[
                "missing_required_artifacts"
            ],
            "missing_optional_artifacts": source_state[
                "missing_optional_artifacts"
            ],
            "untrusted_artifacts": source_state["untrusted_artifacts"],
            "parse_error_artifacts": source_state["parse_error_artifacts"],
        },
        "duplicate_summary": {
            "duplicate_group_count": duplicate_group_count,
            "duplicate_asset_count": duplicate_asset_count,
            "deletion_suggested": False,
            "no_deletion_suggested": True,
            "recommended_action": "human_inspect_only",
            "automatic_dedupe_performed": False,
            "relative_paths_included": False,
        },
        "quarantine_summary": _quarantine_summary(
            quarantine_manifest,
            quarantined_path_count,
        ),
        "sqlite_summary": {
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
        },
        "incremental_summary": {
            "plan_present": bool(
                records_by_role["scan_local_asset_incremental_scan_plan"]["exists"]
            ),
            "plan_mode": incremental_counts["plan_mode"],
            "unchanged_asset_count": incremental_counts["unchanged_asset_count"],
            "changed_asset_count": incremental_counts["changed_asset_count"],
            "new_asset_count": incremental_counts["new_asset_count"],
            "missing_asset_count": incremental_counts["missing_asset_count"],
            "suspicious_change_count": incremental_counts[
                "suspicious_change_count"
            ],
            "automatic_skip_performed": False,
            "cache_execution_performed": False,
        },
        "failure_summary": _failure_summary(failure_bundle, failure_stage),
        "warning_summary": {
            "warning_count": len(warnings),
            "warnings": warnings,
            "missing_optional_artifacts": source_state[
                "missing_optional_artifacts"
            ],
        },
        "decision_checklist": _decision_checklist_payload(),
        "source_artifacts": source_artifacts,
        "missing_artifacts": source_state["missing_artifacts"],
        "generated_artifacts_read_count": source_state[
            "generated_artifacts_read_count"
        ],
        "generated_artifacts_missing_count": source_state[
            "generated_artifacts_missing_count"
        ],
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    return packet


def _dict_payload(payloads: dict[str, object], role: str) -> dict[str, object]:
    payload = payloads.get(role)
    return payload if isinstance(payload, dict) else {}


def _source_state(
    source_artifacts: list[dict[str, object]],
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    smoke_error: str | None,
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
    untrusted.extend(
        _artifact_index_hash_mismatches(records_by_role, source_payloads)
    )
    if smoke_error is not None and "symlink" in smoke_error:
        untrusted.append("smoke_output_dir")
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


def _artifact_index_hash_mismatches(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
) -> list[str]:
    mismatches = []
    root_manifest = _dict_payload(source_payloads, "smoke_root_artifact_index_manifest")
    root_index = records_by_role.get("smoke_root_artifact_index", {})
    if root_manifest and root_manifest.get("artifact_index_sha256") != root_index.get(
        "sha256"
    ):
        mismatches.append("smoke_root_artifact_index_manifest")
    scan_manifest = _dict_payload(source_payloads, "scan_artifact_index_manifest")
    scan_index = records_by_role.get("scan_artifact_index", {})
    if scan_manifest and scan_index.get("exists") is True:
        if scan_manifest.get("artifact_index_sha256") != scan_index.get("sha256"):
            mismatches.append("scan_artifact_index_manifest")
    return mismatches


def _warning_items(
    *,
    source_state: dict[str, object],
    scan_complete: bool,
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
    if not scan_complete:
        warnings.append("smoke_run_incomplete")
    if quarantined_path_count > 0:
        warnings.append("quarantine_present")
    if duplicate_group_count > 0:
        warnings.append("duplicate_groups_present")
    if int(incremental_counts["suspicious_change_count"]) > 0:
        warnings.append("suspicious_incremental_changes_present")
    if _incremental_needs_inspection(incremental_counts):
        warnings.append("incremental_changes_present")
    return sorted(set(warnings))


def _review_packet_status(
    *,
    source_state: dict[str, object],
    smoke_run_admitted: bool,
    scan_complete: bool,
    warnings: list[str],
) -> str:
    if source_state["missing_required_artifacts"]:
        return "review_blocked_missing_required_artifacts"
    if source_state["untrusted_artifacts"] or any(
        role in source_state["parse_error_artifacts"]
        for role in (
            "smoke_root_artifact_index",
            "smoke_root_artifact_index_manifest",
            "local_asset_human_smoke_admission_receipt",
        )
    ):
        return "review_blocked_untrusted_artifacts"
    if not smoke_run_admitted or not scan_complete:
        return "review_blocked_failed_smoke_run"
    if warnings:
        return "review_ready_with_warnings"
    return "review_ready"


def _recommended_human_decision(
    *,
    review_packet_status: str,
    duplicate_group_count: int,
    quarantined_path_count: int,
    incremental_counts: dict[str, object],
) -> str:
    if review_packet_status not in _READY_STATUSES:
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


def _readiness_summary(
    admission: dict[str, object],
    approval: dict[str, object],
) -> dict[str, object]:
    return {
        "readiness_status": _first_text(
            admission.get("readiness_status"),
            approval.get("readiness_status"),
        ),
        "readiness_decision": _first_text(
            admission.get("readiness_decision"),
            approval.get("readiness_decision"),
        ),
        "candidate_input_dir": _first_text(
            admission.get("candidate_input_dir"),
            approval.get("candidate_input_dir"),
        ),
        "recursive": _first_bool(admission.get("recursive"), approval.get("recursive")),
        "include_hidden": _first_bool(
            admission.get("include_hidden"),
            approval.get("include_hidden"),
        ),
        "max_smoke_files": _first_int(admission.get("max_smoke_files")),
        "max_smoke_bytes": _first_int(admission.get("max_smoke_bytes")),
        "max_smoke_depth": _first_int(admission.get("max_smoke_depth")),
        "estimated_total_size_bytes": _first_int(
            admission.get("smoke_precheck_total_bytes")
        ),
        "estimated_file_count": _first_int(admission.get("smoke_precheck_file_count")),
        "risk_counts_available": False,
        "risk_counts": {},
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
        "duplicate_group_count": duplicate_group_count,
        "quarantined_path_count": quarantined_path_count,
        "scan_complete": scan_complete,
        "scan_success_state": "complete" if scan_complete else "not_complete",
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
    reason_counts = {
        str(reason): int(count)
        for reason, count in counts.items()
        if isinstance(count, int) and not isinstance(count, bool)
    }
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
        "unsafe_path_count": reason_counts.get("unsafe_directory", 0),
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
    failure_stage: str | None,
) -> dict[str, object]:
    return {
        "failure_bundle_present": bool(failure_bundle),
        "failure_stage": failure_stage,
        "safe_to_retry": _first_bool(failure_bundle.get("safe_to_retry")),
        "safe_error_message": _safe_text(
            failure_bundle.get("safe_error_message"),
        )
        if failure_bundle
        else None,
        "raw_traceback_copied": False,
        "raw_exception_dump_copied": False,
        "secret_value_serialized": False,
    }


def _decision_checklist_payload() -> dict[str, object]:
    items = (
        "Verify approval artifact exists.",
        "Verify approval phrase plaintext was not persisted.",
        "Verify admission receipt says bounded smoke only.",
        "Verify production_scan_performed=false.",
        "Verify input_mutation_performed=false.",
        "Verify scan_complete status.",
        "Review quarantine summary.",
        "Review duplicate summary.",
        "Review SQLite summary.",
        "Review incremental plan summary.",
    )
    return {
        "checklist_type": "local_asset_smoke_human_decision_checklist_v1",
        "items": [
            {"text": item, "checked": False}
            for item in items
        ],
        "decision_options": list(_DECISION_OPTIONS),
        "raw_private_file_contents_included": False,
        "automatic_approval_granted": False,
        "production_autonomy_granted": False,
    }


def _summary_markdown(packet: dict[str, object]) -> str:
    approval = packet["approval_summary"]
    admission = packet["admission_summary"]
    readiness = packet["readiness_summary"]
    scan = packet["scan_summary"]
    duplicate = packet["duplicate_summary"]
    quarantine = packet["quarantine_summary"]
    sqlite = packet["sqlite_summary"]
    incremental = packet["incremental_summary"]
    failure = packet["failure_summary"]
    warnings = packet["warning_summary"]
    lines = [
        "# Local Asset Smoke Review Summary",
        "",
        "- Review packet status: `" + str(packet["review_packet_status"]) + "`",
        "- Recommended human decision: `"
        + str(packet["recommended_human_decision"])
        + "`",
        "- Smoke output dir: `" + str(packet["smoke_output_dir"]) + "`",
        "- Review output dir: `" + str(packet["output_dir"]) + "`",
        "- Project id: `" + str(packet["project_id"]) + "`",
        "",
        "## Approval Summary",
        "",
        "- Approval artifact present: "
        + _bool_text(approval["approval_artifact_present"]),
        "- Human approval id present: "
        + _bool_text(approval["human_approval_id_present"]),
        "- Approval phrase plaintext persisted: false",
        "- Approval phrase stored: false",
        "",
        "## Admission Summary",
        "",
        "- Admitted: " + _bool_text(admission["admitted"]),
        "- Scan launcher invoked: "
        + _bool_text(admission["scan_launcher_invoked"]),
        "- Scan complete: " + _bool_text(admission["scan_complete"]),
        "- Bounded smoke run performed: "
        + _bool_text(admission["bounded_smoke_run_performed"]),
        "- Production scan performed: false",
        "- Failure stage: `" + str(admission["failure_stage"]) + "`",
        "",
        "## Readiness Summary",
        "",
        "- Readiness status: `" + str(readiness["readiness_status"]) + "`",
        "- Readiness decision: `" + str(readiness["readiness_decision"]) + "`",
        "- Candidate input dir: `" + str(readiness["candidate_input_dir"]) + "`",
        "- Recursive: " + _bool_text(readiness["recursive"]),
        "- Include hidden: " + _bool_text(readiness["include_hidden"]),
        "- Estimated file count: " + str(readiness["estimated_file_count"]),
        "- Estimated total size bytes: "
        + str(readiness["estimated_total_size_bytes"]),
        "",
        "## Scan Summary",
        "",
        "- Files scanned: " + str(scan["files_scanned"]),
        "- Bytes scanned: " + str(scan["bytes_scanned"]),
        "- Duplicate group count: " + str(scan["duplicate_group_count"]),
        "- Quarantined path count: " + str(scan["quarantined_path_count"]),
        "- Scan artifact index present: "
        + _bool_text(scan["scan_artifact_index_present"]),
        "",
        "## Duplicate Summary",
        "",
        "- Duplicate group count: " + str(duplicate["duplicate_group_count"]),
        "- Duplicate asset count: " + str(duplicate["duplicate_asset_count"]),
        "- Deletion suggested: false",
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
        "- Recommended action: human inspect only",
        "",
        "## SQLite Summary",
        "",
        "- Database present: " + _bool_text(sqlite["database_present"]),
        "- Manifest present: " + _bool_text(sqlite["manifest_present"]),
        "- Query summary present: " + _bool_text(sqlite["query_summary_present"]),
        "- Database opened by review packet: false",
        "- Row counts: `" + json.dumps(sqlite["row_counts"], sort_keys=True) + "`",
        "",
        "## Incremental Summary",
        "",
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
        "- Failure bundle present: "
        + _bool_text(failure["failure_bundle_present"]),
        "- Failure stage: `" + str(failure["failure_stage"]) + "`",
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
        "- no scan performed",
        "- no readiness run performed",
        "- no raw candidate content read",
        "- no candidate hashing performed",
        "- no input mutation",
        "- no smoke output mutation",
        "- no file move/rename/delete",
        "- no duplicate deletion",
        "- no media organizer behavior",
        "- human approval required for next step",
    ]
    return "\n".join(lines) + "\n"


def _decision_checklist_markdown(packet: dict[str, object]) -> str:
    lines = [
        "# Local Asset Smoke Human Decision Checklist",
        "",
        "- [ ] Verify approval artifact exists.",
        "- [ ] Verify approval phrase plaintext was not persisted.",
        "- [ ] Verify admission receipt says bounded smoke only.",
        "- [ ] Verify production_scan_performed=false.",
        "- [ ] Verify input_mutation_performed=false.",
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
            "Do not delete, move, or rename files from this checklist.",
            "Do not perform automatic dedupe.",
            "Do not grant production autonomy.",
        ]
    )
    return "\n".join(lines) + "\n"


def _packet_manifest_payload(
    *,
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    review_packet_status: str,
    recommended_human_decision: str,
) -> dict[str, object]:
    packet_path = paths[LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE]
    summary_path = paths[LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE]
    checklist_path = paths[LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE]
    return {
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
            }
            for record in source_artifacts
        ],
        "review_packet_status": review_packet_status,
        "recommended_human_decision": recommended_human_decision,
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _artifact_index_payload(
    output_path: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = []
    for role, file_name in _REVIEW_ARTIFACTS:
        path = paths[file_name]
        entries.append(_review_artifact_entry(output_path, role, path))
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "explicit_review_packet_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[_ARTIFACT_INDEX_FILE]
    entries = artifact_index["entries"]
    return {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
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
    smoke = packet["smoke_run_summary"]
    readiness = packet["readiness_summary"]
    duplicate = packet["duplicate_summary"]
    quarantine = packet["quarantine_summary"]
    incremental = packet["incremental_summary"]
    return {
        "local_asset_smoke_review_packet_path": paths[
            LOCAL_ASSET_SMOKE_REVIEW_PACKET_FILE
        ].as_posix(),
        "local_asset_smoke_review_packet_manifest_path": paths[
            LOCAL_ASSET_SMOKE_REVIEW_PACKET_MANIFEST_FILE
        ].as_posix(),
        "local_asset_smoke_review_summary_path": paths[
            LOCAL_ASSET_SMOKE_REVIEW_SUMMARY_FILE
        ].as_posix(),
        "local_asset_smoke_human_decision_checklist_path": paths[
            LOCAL_ASSET_SMOKE_HUMAN_DECISION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[
            _ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "smoke_output_dir": packet["smoke_output_dir"],
        "output_dir": packet["output_dir"],
        "project_id": packet["project_id"],
        "smoke_run_complete": smoke["smoke_run_complete"],
        "smoke_run_admitted": smoke["smoke_run_admitted"],
        "scan_launcher_invoked": smoke["scan_launcher_invoked"],
        "scan_complete": smoke["scan_complete"],
        "readiness_status": readiness["readiness_status"],
        "readiness_decision": readiness["readiness_decision"],
        "duplicate_group_count": duplicate["duplicate_group_count"],
        "quarantined_path_count": quarantine["quarantined_path_count"],
        "incremental_plan_mode": incremental["plan_mode"],
        "changed_asset_count": incremental["changed_asset_count"],
        "new_asset_count": incremental["new_asset_count"],
        "missing_asset_count": incremental["missing_asset_count"],
        "suspicious_change_count": incremental["suspicious_change_count"],
        "review_packet_status": packet["review_packet_status"],
        "recommended_human_decision": packet["recommended_human_decision"],
        "generated_artifacts_read_count": packet["generated_artifacts_read_count"],
        "generated_artifacts_missing_count": packet[
            "generated_artifacts_missing_count"
        ],
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _structured_failure_result(
    *,
    smoke_path: Path,
    output_path: Path,
    failure_stage: str,
    error_message: str,
    project_id: str | None,
) -> LocalAssetSmokeReviewPacketResult:
    status = "review_blocked_missing_required_artifacts"
    payload = {
        "complete": False,
        "smoke_output_dir": smoke_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "project_id": project_id,
        "review_packet_status": status,
        "recommended_human_decision": _REJECT_DECISION,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "local_asset_smoke_review_packet_path": None,
        "local_asset_smoke_review_packet_manifest_path": None,
        "local_asset_smoke_review_summary_path": None,
        "local_asset_smoke_human_decision_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "smoke_run_complete": False,
        "smoke_run_admitted": False,
        "scan_launcher_invoked": False,
        "scan_complete": False,
        "readiness_status": None,
        "readiness_decision": None,
        "duplicate_group_count": 0,
        "quarantined_path_count": 0,
        "incremental_plan_mode": None,
        "changed_asset_count": 0,
        "new_asset_count": 0,
        "missing_asset_count": 0,
        "suspicious_change_count": 0,
        "generated_artifacts_read_count": 0,
        "generated_artifacts_missing_count": len(_SOURCE_ARTIFACTS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    return LocalAssetSmokeReviewPacketResult(
        smoke_output_dir=smoke_path,
        output_dir=output_path,
        packet_path=None,
        packet_manifest_path=None,
        summary_path=None,
        decision_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        review_packet_status=status,
        recommended_human_decision=_REJECT_DECISION,
        payload=payload,
    )


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_int(*values: object, default: int | None = None) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return default


def _first_bool(*values: object) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
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
    return text[:240] if text else "local asset smoke review failed"


def _bool_text(value: object) -> str:
    return str(bool(value)).lower()


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()
