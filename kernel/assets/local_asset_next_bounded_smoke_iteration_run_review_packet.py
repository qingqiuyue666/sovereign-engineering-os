"""Review packet for the actual next bounded smoke iteration run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE",
    "LocalAssetNextBoundedSmokeIterationRunReviewPacketResult",
    "build_local_asset_next_bounded_smoke_iteration_run_review_packet",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_PACKET_TYPE = "local_asset_next_bounded_smoke_iteration_run_review_packet_v1"
_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_v1"
)
_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_v1"
)
_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_review_packet_record"
_EXECUTION_CAPABILITY = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_only"
)

_RUNNER_TYPE = "local_asset_next_bounded_smoke_iteration_runner_v1"
_RUNNER_MANIFEST_TYPE = "local_asset_next_bounded_smoke_iteration_runner_manifest_v1"
_RUNNER_INDEX_TYPE = "local_asset_next_bounded_smoke_iteration_runner_artifact_index_v1"
_RUNNER_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_artifact_index_manifest_v1"
)
_RUN_TYPE = "local_asset_next_bounded_smoke_iteration_run_v1"
_RUN_MANIFEST_TYPE = "local_asset_next_bounded_smoke_iteration_run_manifest_v1"
_CANDIDATE_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_candidate_manifest_v1"
)
_RUN_INDEX_TYPE = "local_asset_next_bounded_smoke_iteration_artifact_index_v1"
_RUN_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_artifact_index_manifest_v1"
)

_RUNNER_COMPLETED_STATUS = "next_bounded_smoke_iteration_runner_completed"
_RUNNER_COMPLETED_DECISION = "executed_bounded_smoke_iteration_under_admitted_limits"
_RUNNER_COMPLETED_NEXT_ACTION = "review_next_bounded_smoke_iteration_run"

_READY_STATUS = "next_bounded_smoke_iteration_run_review_packet_ready"
_READY_DECISION = "package_next_bounded_smoke_iteration_run_for_promotion_gate_review"
_READY_NEXT_ACTION = "run_next_bounded_smoke_iteration_run_promotion_gate"

_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_REVIEW_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE,
    ),
)

_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "rerun_runner",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_path_validation",
    "candidate_path_listing",
    "candidate_file_read",
    "candidate_file_hashing",
    "candidate_file_mutation",
    "file_move",
    "file_rename",
    "file_delete",
    "duplicate_deletion",
    "media_organizer_behavior",
    "network_access",
    "model_api_call",
    "external_runtime_invocation",
)

_BOUNDARY_FALSE_FLAGS = {
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_review_packet": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "next_admission_run_performed": False,
    "execution_request_run_performed": False,
    "runner_admission_run_performed": False,
    "runner_execution_run_performed_by_review_packet": False,
    "raw_candidate_content_read_by_review": False,
    "candidate_file_hashing_performed_by_review": False,
    "candidate_path_validation_performed_by_review": False,
    "candidate_path_listing_performed_by_review": False,
    "input_mutation_performed": False,
    "upstream_output_mutation_performed": False,
    "file_move_performed": False,
    "file_rename_performed": False,
    "file_delete_performed": False,
    "duplicate_deletion_performed": False,
    "media_organizer_behavior_performed": False,
    "output_overwrite_performed": False,
    "network_access_performed": False,
    "model_api_called": False,
    "external_runtime_invoked": False,
    "production_scan_performed": False,
    "production_scan_recommended": False,
}

_REVIEW_ACCESS_FALSE_FLAGS = {
    "runner_reexecution_performed": False,
    "candidate_input_path_checked_by_review": False,
    "candidate_input_path_listed_by_review": False,
    "candidate_input_file_read_by_review": False,
    "candidate_input_file_hashing_performed_by_review": False,
}

_SOURCE_BOUNDARY_FIELDS = (
    "input_mutation_performed",
    "upstream_output_mutation_performed",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
    "output_overwrite_performed",
    "network_access_performed",
    "model_api_called",
    "external_runtime_invoked",
    "production_scan_performed",
    "production_scan_recommended",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
)

_RUNNER_SOURCE_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner",
        "local_asset_next_bounded_smoke_iteration_runner.json",
        True,
        "runner_type",
        _RUNNER_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_manifest",
        "local_asset_next_bounded_smoke_iteration_runner_manifest.json",
        True,
        "manifest_type",
        _RUNNER_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_artifact_index",
        "artifact_index.json",
        True,
        "index_type",
        _RUNNER_INDEX_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        "manifest_type",
        _RUNNER_INDEX_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_summary",
        "local_asset_next_bounded_smoke_iteration_runner_summary.md",
        False,
        None,
        None,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_checklist",
        "local_asset_next_bounded_smoke_iteration_runner_checklist.md",
        False,
        None,
        None,
    ),
)

_ACTUAL_SOURCE_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_run",
        "local_asset_next_bounded_smoke_iteration_run.json",
        True,
        "run_type",
        _RUN_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_manifest",
        "local_asset_next_bounded_smoke_iteration_run_manifest.json",
        True,
        "manifest_type",
        _RUN_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_candidate_manifest",
        "local_asset_next_bounded_smoke_iteration_candidate_manifest.json",
        True,
        "manifest_type",
        _CANDIDATE_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_artifact_index",
        "artifact_index.json",
        True,
        "index_type",
        _RUN_INDEX_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        "manifest_type",
        _RUN_INDEX_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_summary",
        "local_asset_next_bounded_smoke_iteration_summary.md",
        False,
        None,
        None,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_checklist",
        "local_asset_next_bounded_smoke_iteration_checklist.md",
        False,
        None,
        None,
    ),
)

_ACTUAL_ARTIFACT_ROLE_TO_FILE = {
    "local_asset_next_bounded_smoke_iteration_run": (
        "local_asset_next_bounded_smoke_iteration_run.json"
    ),
    "local_asset_next_bounded_smoke_iteration_run_manifest": (
        "local_asset_next_bounded_smoke_iteration_run_manifest.json"
    ),
    "local_asset_next_bounded_smoke_iteration_candidate_manifest": (
        "local_asset_next_bounded_smoke_iteration_candidate_manifest.json"
    ),
    "local_asset_next_bounded_smoke_iteration_summary": (
        "local_asset_next_bounded_smoke_iteration_summary.md"
    ),
    "local_asset_next_bounded_smoke_iteration_checklist": (
        "local_asset_next_bounded_smoke_iteration_checklist.md"
    ),
    "artifact_index": "artifact_index.json",
    "artifact_index_manifest": "artifact_index_manifest.json",
}

_FORBIDDEN_CANDIDATE_CONTENT_FIELDS = {
    "raw_content",
    "raw_file_content",
    "file_content",
    "content",
    "extracted_text",
    "preview",
    "previews",
    "thumbnail",
    "thumbnails",
    "text_preview",
}


@dataclass(frozen=True)
class LocalAssetNextBoundedSmokeIterationRunReviewPacketResult:
    runner_output_dir: Path
    actual_next_iteration_output_dir: Path
    output_dir: Path
    review_packet_path: Path | None
    review_packet_manifest_path: Path | None
    review_packet_summary_path: Path | None
    review_packet_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    review_status: str
    review_decision: str
    payload: dict[str, object]


def build_local_asset_next_bounded_smoke_iteration_run_review_packet(
    runner_output_dir: Path,
    actual_next_iteration_output_dir: Path,
    output_dir: Path,
    *,
    review_packet_id: str,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationRunReviewPacketResult:
    """Build a non-executing review packet from generated runner artifacts."""

    roots = {
        "runner_output_dir": Path(runner_output_dir),
        "actual_next_iteration_output_dir": Path(actual_next_iteration_output_dir),
        "output_dir": Path(output_dir),
    }
    inputs = {
        "review_packet_id": review_packet_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes": operator_notes,
        "operator_notes_present": operator_notes is not None,
    }
    paths = _output_paths(roots["output_dir"])

    output_error = _real_existing_dir_error(roots["output_dir"], "output_dir")
    if output_error is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage="preflight_output_dir",
            error_message=output_error,
        )

    collision = _existing_output_collision(paths)
    if collision is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage="preflight_output_collision",
            error_message="review packet output artifact already exists: " + collision,
        )

    overlap_error = _overlap_preflight_error(roots)
    if overlap_error is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage="preflight_source_output_overlap",
            error_message=overlap_error,
        )

    runner_root_error = _real_existing_dir_error(
        roots["runner_output_dir"],
        "runner_output_dir",
    )
    actual_root_error = _real_existing_dir_error(
        roots["actual_next_iteration_output_dir"],
        "actual_next_iteration_output_dir",
    )
    source_artifacts = _source_artifact_records(
        roots,
        runner_root_error=runner_root_error,
        actual_root_error=actual_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_source_trust(source_artifacts, source_payloads)

    packet = _review_packet_payload(
        roots=roots,
        inputs=inputs,
        runner_root_error=runner_root_error,
        actual_root_error=actual_root_error,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(packet)
    checklist = _checklist_markdown()

    _write_json_exclusive(paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE], packet)
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE
        ],
        checklist,
    )
    manifest = _manifest_payload(paths, packet, source_artifacts)
    _write_json_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE
        ],
        manifest,
    )
    artifact_index = _artifact_index_payload(roots["output_dir"], paths)
    _write_json_exclusive(paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _artifact_index_manifest_payload(
        roots["output_dir"],
        paths,
        artifact_index,
    )
    _write_json_exclusive(paths[_ARTIFACT_INDEX_MANIFEST_FILE], artifact_index_manifest)

    complete = packet["review_status"] == _READY_STATUS
    payload = _launcher_payload_from_packet(packet, paths, complete=complete)
    return LocalAssetNextBoundedSmokeIterationRunReviewPacketResult(
        runner_output_dir=roots["runner_output_dir"],
        actual_next_iteration_output_dir=roots["actual_next_iteration_output_dir"],
        output_dir=roots["output_dir"],
        review_packet_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE
        ],
        review_packet_manifest_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE
        ],
        review_packet_summary_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE
        ],
        review_packet_checklist_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        review_status=str(packet["review_status"]),
        review_decision=str(packet["review_decision"]),
        payload=payload,
    )


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {file_name: output_dir / file_name for file_name in _OUTPUT_FILES}


def _real_existing_dir_error(path_value: object, label: str) -> str | None:
    path = Path(path_value)
    if path.is_symlink():
        return label + " must not be a symlink"
    if not path.exists():
        return label + " must already exist"
    if not path.is_dir():
        return label + " must be a directory"
    return None


def _existing_output_collision(paths: dict[str, Path]) -> str | None:
    for file_name in sorted(paths):
        path = paths[file_name]
        if path.exists() or path.is_symlink():
            return file_name
    return None


def _overlap_preflight_error(roots: dict[str, Path]) -> str | None:
    checks = (
        (
            "output_dir",
            "runner_output_dir",
            "output_dir must not equal runner_output_dir",
        ),
        (
            "output_dir",
            "actual_next_iteration_output_dir",
            "output_dir must not equal actual_next_iteration_output_dir",
        ),
        (
            "runner_output_dir",
            "actual_next_iteration_output_dir",
            "runner_output_dir must not equal actual_next_iteration_output_dir",
        ),
    )
    for first, second, message in checks:
        if not _overlap_checkable(roots[first], roots[second]):
            continue
        if _same_path_text(roots[first], roots[second]):
            return message
    inside_checks = (
        (
            "output_dir",
            "runner_output_dir",
            "output_dir must not be inside runner_output_dir",
        ),
        (
            "runner_output_dir",
            "output_dir",
            "runner_output_dir must not be inside output_dir",
        ),
        (
            "output_dir",
            "actual_next_iteration_output_dir",
            "output_dir must not be inside actual_next_iteration_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "output_dir",
            "actual_next_iteration_output_dir must not be inside output_dir",
        ),
        (
            "runner_output_dir",
            "actual_next_iteration_output_dir",
            "runner_output_dir must not be inside actual_next_iteration_output_dir",
        ),
        (
            "actual_next_iteration_output_dir",
            "runner_output_dir",
            "actual_next_iteration_output_dir must not be inside runner_output_dir",
        ),
    )
    for candidate, root, message in inside_checks:
        if not _overlap_checkable(roots[candidate], roots[root]):
            continue
        if _path_is_inside(roots[candidate], roots[root]):
            return message
    return None


def _overlap_checkable(first: Path, second: Path) -> bool:
    first_path = Path(first)
    second_path = Path(second)
    return (
        first_path.exists()
        and second_path.exists()
        and not first_path.is_symlink()
        and not second_path.is_symlink()
    )


def _same_path_text(first: Path, second: Path) -> bool:
    return _normalize_path_text(first) == _normalize_path_text(second)


def _normalize_path_text(path_value: Path) -> str:
    return os.path.normpath(Path(path_value).expanduser().as_posix())


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    if _same_path_text(candidate_path, root_path):
        return False
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
        return True
    except ValueError:
        return False


def _source_artifact_records(
    roots: dict[str, Path],
    *,
    runner_root_error: str | None,
    actual_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for role, relative_path, required, field_name, expected_value in _RUNNER_SOURCE_ARTIFACTS:
        records.append(
            _source_record(
                roots["runner_output_dir"],
                "runner_output_dir",
                role,
                relative_path,
                required,
                field_name,
                expected_value,
                root_error=runner_root_error,
            )
        )
    for role, relative_path, required, field_name, expected_value in _ACTUAL_SOURCE_ARTIFACTS:
        records.append(
            _source_record(
                roots["actual_next_iteration_output_dir"],
                "actual_next_iteration_output_dir",
                role,
                relative_path,
                required,
                field_name,
                expected_value,
                root_error=actual_root_error,
            )
        )
    return sorted(records, key=lambda record: str(record["role"]))


def _source_record(
    root: Path,
    source_dir_role: str,
    role: str,
    relative_path: str,
    required: bool,
    field_name: str | None,
    expected_value: str | None,
    *,
    root_error: str | None,
) -> dict[str, object]:
    path = root / relative_path
    if root_error is not None:
        return {
            "role": role,
            "artifact_role": role,
            "source_dir_role": source_dir_role,
            "relative_path": relative_path,
            "path": path.as_posix(),
            "exists": False,
            "required": required,
            "json_artifact": field_name is not None,
            "expected_field": field_name,
            "expected_value": expected_value,
            "sha256": None,
            "size_bytes": None,
            "trusted_generated_artifact": False,
            "trust_failures": [
                _blocker("source_dir_unsafe", root_error, source_dir_role=source_dir_role)
            ],
            "content_indexed": False,
            "raw_content_copied": False,
        }
    exists = path.exists() or path.is_symlink()
    is_symlink = path.is_symlink()
    is_file = exists and path.is_file() and not is_symlink
    trust_failures = []
    if exists and is_symlink:
        trust_failures.append(_blocker("source_artifact_symlink", "source artifact is a symlink"))
    elif exists and not is_file:
        trust_failures.append(_blocker("source_artifact_not_file", "source artifact is not a file"))
    return {
        "role": role,
        "artifact_role": role,
        "source_dir_role": source_dir_role,
        "relative_path": relative_path,
        "path": path.as_posix(),
        "exists": exists,
        "required": required,
        "json_artifact": field_name is not None,
        "expected_field": field_name,
        "expected_value": expected_value,
        "sha256": sha256_file(path) if is_file else None,
        "size_bytes": path.stat().st_size if is_file else None,
        "trusted_generated_artifact": False,
        "trust_failures": trust_failures,
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _read_json_source_payloads(
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payloads: dict[str, object] = {}
    for artifact in source_artifacts:
        if artifact["exists"] is not True or artifact["json_artifact"] is not True:
            continue
        if artifact.get("sha256") is None:
            continue
        try:
            payload = json.loads(Path(str(artifact["path"])).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            artifact["trust_failures"].append(
                _blocker(
                    "malformed_json",
                    "source JSON artifact is malformed",
                    error_message=str(exc),
                )
            )
            continue
        if not isinstance(payload, dict):
            artifact["trust_failures"].append(
                _blocker("malformed_json", "source JSON artifact is not an object")
            )
            continue
        payloads[str(artifact["role"])] = payload
    return payloads


def _mark_source_trust(
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> None:
    records = {str(record["role"]): record for record in source_artifacts}
    for artifact in source_artifacts:
        if artifact["exists"] is not True:
            continue
        expected_field = artifact.get("expected_field")
        if expected_field is None:
            continue
        payload = source_payloads.get(str(artifact["role"]))
        if not isinstance(payload, dict):
            artifact["trust_failures"].append(
                _blocker("malformed_json", "source JSON artifact could not be parsed")
            )
            continue
        if payload.get(str(expected_field)) != artifact.get("expected_value"):
            artifact["trust_failures"].append(
                _blocker(
                    "type_mismatch",
                    "source artifact type field did not match expected value",
                    expected_field=expected_field,
                    expected_value=artifact.get("expected_value"),
                    actual_value=payload.get(str(expected_field)),
                )
            )

    runner_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_runner_manifest",
    )
    runner_index_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_runner_artifact_index_manifest",
    )
    run_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_run_manifest",
    )
    run_index_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_artifact_index_manifest",
    )
    _mark_manifest_hash(
        records,
        runner_manifest,
        "runner_sha256",
        "local_asset_next_bounded_smoke_iteration_runner",
    )
    _mark_manifest_hash(
        records,
        runner_manifest,
        "summary_sha256",
        "local_asset_next_bounded_smoke_iteration_runner_summary",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        runner_manifest,
        "checklist_sha256",
        "local_asset_next_bounded_smoke_iteration_runner_checklist",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        runner_index_manifest,
        "artifact_index_sha256",
        "local_asset_next_bounded_smoke_iteration_runner_artifact_index",
    )
    _mark_manifest_hash(
        records,
        run_manifest,
        "run_sha256",
        "local_asset_next_bounded_smoke_iteration_run",
    )
    _mark_manifest_hash(
        records,
        run_manifest,
        "candidate_manifest_sha256",
        "local_asset_next_bounded_smoke_iteration_candidate_manifest",
    )
    _mark_manifest_hash(
        records,
        run_manifest,
        "summary_sha256",
        "local_asset_next_bounded_smoke_iteration_summary",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        run_manifest,
        "checklist_sha256",
        "local_asset_next_bounded_smoke_iteration_checklist",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        run_index_manifest,
        "artifact_index_sha256",
        "local_asset_next_bounded_smoke_iteration_artifact_index",
    )
    for artifact in source_artifacts:
        if artifact["exists"] is True and not artifact["trust_failures"]:
            artifact["trusted_generated_artifact"] = True


def _mark_manifest_hash(
    records: dict[str, dict[str, object]],
    manifest: dict[str, object],
    field_name: str,
    role: str,
    *,
    optional: bool = False,
) -> None:
    record = records.get(role)
    if record is None or record["exists"] is not True:
        return
    expected_hash = manifest.get(field_name)
    if optional and expected_hash is None:
        return
    actual_hash = record.get("sha256")
    if expected_hash != actual_hash:
        record["trust_failures"].append(
            _blocker(
                "hash_mismatch",
                "source manifest hash did not match source artifact",
                hash_field=field_name,
                expected_sha256=expected_hash,
                actual_sha256=actual_hash,
            )
        )


def _review_packet_payload(
    *,
    roots: dict[str, Path],
    inputs: dict[str, object],
    runner_root_error: str | None,
    actual_root_error: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    runner = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_runner",
    )
    run = _dict_payload(source_payloads, "local_asset_next_bounded_smoke_iteration_run")
    candidate = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_candidate_manifest",
    )
    runner_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_runner_manifest",
    )

    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    metadata_blockers = _invalid_review_packet_metadata(inputs)
    source_boundary = _source_boundary_blockers(runner, run)
    runner_checks = _runner_completion_checks(runner)
    actual_run_checks = _actual_run_checks(run)
    candidate_checks = _candidate_manifest_checks(candidate)
    cross_checks = _cross_artifact_checks(
        runner=runner,
        run=run,
        candidate=candidate,
        runner_manifest=runner_manifest,
        actual_output_dir=roots["actual_next_iteration_output_dir"],
    )
    failed_runner = _failed_checks(runner_checks)
    failed_actual = _failed_checks(actual_run_checks)
    failed_candidate = _failed_checks(candidate_checks)
    failed_cross = _failed_checks(cross_checks)

    if metadata_blockers:
        status = "blocked_invalid_review_packet_metadata"
        blockers = metadata_blockers
    elif missing_required:
        status = "blocked_missing_required_artifacts"
        blockers = missing_required
    elif untrusted:
        status = "blocked_untrusted_artifacts"
        blockers = untrusted
    elif source_boundary:
        status = "blocked_source_boundary_violation"
        blockers = source_boundary
    elif failed_runner:
        status = "blocked_runner_not_completed"
        blockers = _check_blockers(failed_runner)
    elif failed_actual:
        status = "blocked_invalid_actual_run_record"
        blockers = _check_blockers(failed_actual)
    elif failed_candidate:
        status = "blocked_invalid_candidate_manifest"
        blockers = _check_blockers(failed_candidate)
    elif failed_cross:
        status = "blocked_cross_artifact_inconsistency"
        blockers = _check_blockers(failed_cross)
    elif runner_root_error is not None or actual_root_error is not None:
        status = "blocked_missing_required_artifacts"
        blockers = missing_required
    else:
        status = _READY_STATUS
        blockers = []

    decision, next_action = _decision_and_next_action(status)
    candidate_records = _list_or_empty(
        _first_present(
            runner.get("bounded_file_records"),
            run.get("bounded_file_records"),
            candidate.get("bounded_file_records"),
        )
    )
    packet = {
        "review_packet_type": _PACKET_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": _first_text(
            inputs.get("project_id"),
            runner.get("project_id"),
            run.get("project_id"),
        ),
        "review_packet_id": inputs.get("review_packet_id"),
        "reviewer_id": inputs.get("reviewer_id"),
        "operator_notes_present": inputs["operator_notes_present"],
        "operator_notes": inputs.get("operator_notes")
        if inputs["operator_notes_present"] is True
        else None,
        "runner_output_dir": roots["runner_output_dir"].as_posix(),
        "actual_next_iteration_output_dir": roots[
            "actual_next_iteration_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "runner_execution_id": _first_present(
            runner.get("runner_execution_id"),
            run.get("runner_execution_id"),
        ),
        "runner_operator_id": _first_present(
            runner.get("runner_operator_id"),
            run.get("runner_operator_id"),
        ),
        "runner_admission_id": _first_present(
            runner.get("runner_admission_id"),
            run.get("runner_admission_id"),
        ),
        "admitted_runner_id": _first_present(
            runner.get("admitted_runner_id"),
            run.get("admitted_runner_id"),
        ),
        "admitted_runner_version": _first_present(
            runner.get("admitted_runner_version"),
            run.get("admitted_runner_version"),
        ),
        "requested_next_iteration_id": _first_present(
            runner.get("requested_next_iteration_id"),
            run.get("requested_next_iteration_id"),
            candidate.get("requested_next_iteration_id"),
        ),
        "requested_candidate_input_dir": _first_present(
            runner.get("requested_candidate_input_dir"),
            run.get("requested_candidate_input_dir"),
            candidate.get("requested_candidate_input_dir"),
        ),
        "requested_next_iteration_output_dir": _first_present(
            runner.get("requested_next_iteration_output_dir"),
            run.get("requested_next_iteration_output_dir"),
        ),
        "requested_limits": _first_dict(
            runner.get("requested_limits"),
            run.get("requested_limits"),
        ),
        "admitted_limits": _first_dict(
            runner.get("admitted_limits"),
            run.get("admitted_limits"),
            candidate.get("admitted_limits"),
        ),
        "runner_status": runner.get("runner_status"),
        "runner_decision": runner.get("runner_decision"),
        "runner_next_allowed_action": runner.get("next_allowed_action"),
        "runner_execution_performed": runner.get("runner_execution_performed", False),
        "next_bounded_smoke_iteration_executed": runner.get(
            "next_bounded_smoke_iteration_executed",
            False,
        ),
        "next_iteration_output_dir_created": runner.get(
            "next_iteration_output_dir_created",
            False,
        ),
        "actual_next_iteration_output_dir_created": runner.get(
            "actual_next_iteration_output_dir_created",
            False,
        ),
        "candidate_input_path_checked": runner.get(
            "candidate_input_path_checked",
            False,
        ),
        "candidate_input_path_listed": runner.get(
            "candidate_input_path_listed",
            False,
        ),
        "candidate_input_file_read": runner.get("candidate_input_file_read", False),
        "candidate_input_file_hashing_performed": runner.get(
            "candidate_input_file_hashing_performed",
            False,
        ),
        "candidate_file_count": _first_present(
            runner.get("candidate_file_count"),
            run.get("candidate_file_count"),
            candidate.get("candidate_file_count"),
            0,
        ),
        "candidate_total_bytes": _first_present(
            runner.get("candidate_total_bytes"),
            run.get("candidate_total_bytes"),
            candidate.get("candidate_total_bytes"),
            0,
        ),
        "candidate_max_depth_observed": _first_present(
            runner.get("candidate_max_depth_observed"),
            run.get("candidate_max_depth_observed"),
            candidate.get("candidate_max_depth_observed"),
            0,
        ),
        "candidate_limit_enforced": _first_present(
            run.get("candidate_limit_enforced"),
            candidate.get("candidate_limit_enforced"),
            runner.get("candidate_limit_enforced"),
            False,
        ),
        "candidate_symlinks_detected": _list_or_empty(
            _first_present(
                candidate.get("candidate_symlinks_detected"),
                run.get("candidate_symlinks_detected"),
                runner.get("candidate_symlinks_detected"),
            )
        ),
        "bounded_file_records": candidate_records,
        "review_status": status,
        "review_decision": decision,
        "next_allowed_action": next_action,
        "review_packet_created": True,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "cross_artifact_checks": cross_checks,
        "review_blockers": blockers,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
    }
    packet.update(_REVIEW_ACCESS_FALSE_FLAGS)
    packet.update(_BOUNDARY_FALSE_FLAGS)
    return packet


def _invalid_review_packet_metadata(inputs: dict[str, object]) -> list[dict[str, object]]:
    invalid = []
    review_packet_id = inputs.get("review_packet_id")
    if not isinstance(review_packet_id, str) or not review_packet_id:
        invalid.append(
            _blocker(
                "invalid_review_packet_metadata",
                "review_packet_id must be non-empty text",
                field="review_packet_id",
            )
        )
    project_id = inputs.get("project_id")
    if project_id is not None and (not isinstance(project_id, str) or not project_id):
        invalid.append(
            _blocker(
                "invalid_review_packet_metadata",
                "project_id must be absent or non-empty text",
                field="project_id",
            )
        )
    reviewer_id = inputs.get("reviewer_id")
    if reviewer_id is not None and (
        not isinstance(reviewer_id, str) or not reviewer_id
    ):
        invalid.append(
            _blocker(
                "invalid_review_packet_metadata",
                "reviewer_id must be absent or non-empty text",
                field="reviewer_id",
            )
        )
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        invalid.append(
            _blocker(
                "invalid_review_packet_metadata",
                "operator_notes must be text when present",
                field="operator_notes",
            )
        )
    return sorted(invalid, key=lambda item: str(item.get("field")))


def _runner_completion_checks(runner: dict[str, object]) -> list[dict[str, object]]:
    records = _list_or_empty(runner.get("bounded_file_records"))
    expected_hashing = bool(records)
    return [
        _check("runner_status_completed", runner.get("runner_status") == _RUNNER_COMPLETED_STATUS),
        _check("runner_decision_completed", runner.get("runner_decision") == _RUNNER_COMPLETED_DECISION),
        _check("runner_next_allowed_action_review", runner.get("next_allowed_action") == _RUNNER_COMPLETED_NEXT_ACTION),
        _check("runner_execution_performed", runner.get("runner_execution_performed") is True),
        _check("next_iteration_executed", runner.get("next_bounded_smoke_iteration_executed") is True),
        _check("next_iteration_output_dir_not_created", runner.get("next_iteration_output_dir_created") is False),
        _check("actual_next_iteration_output_dir_not_created", runner.get("actual_next_iteration_output_dir_created") is False),
        _check("candidate_input_path_checked_by_runner", runner.get("candidate_input_path_checked") is True),
        _check("candidate_input_path_listed_by_runner", runner.get("candidate_input_path_listed") is True),
        _check("candidate_input_file_hashing_matches_records", runner.get("candidate_input_file_hashing_performed") is expected_hashing),
    ]


def _actual_run_checks(run: dict[str, object]) -> list[dict[str, object]]:
    return [
        _check("actual_run_runner_status_completed", run.get("runner_status") == _RUNNER_COMPLETED_STATUS),
        _check("actual_run_runner_decision_completed", run.get("runner_decision") == _RUNNER_COMPLETED_DECISION),
        _check("actual_run_next_allowed_action_review", run.get("next_allowed_action") == _RUNNER_COMPLETED_NEXT_ACTION),
        _check("actual_run_runner_execution_performed", run.get("runner_execution_performed") is True),
        _check("actual_run_next_iteration_executed", run.get("next_bounded_smoke_iteration_executed") is True),
        _check("actual_run_next_iteration_output_dir_not_created", run.get("next_iteration_output_dir_created") is False),
        _check("actual_run_actual_output_dir_not_created", run.get("actual_next_iteration_output_dir_created") is False),
        _check("actual_run_candidate_limit_enforced", run.get("candidate_limit_enforced") is True),
        _check("actual_run_raw_content_not_copied", run.get("raw_content_copied") is False),
    ]


def _candidate_manifest_checks(candidate: dict[str, object]) -> list[dict[str, object]]:
    records = _list_or_empty(candidate.get("bounded_file_records"))
    sorted_records = sorted(records, key=lambda record: str(record.get("relative_path")))
    checks = [
        _check("candidate_limit_enforced", candidate.get("candidate_limit_enforced") is True),
        _check("candidate_symlink_policy_fail_closed", candidate.get("symlink_policy") == "fail_closed"),
        _check("candidate_symlinks_empty", _list_or_empty(candidate.get("candidate_symlinks_detected")) == []),
        _check("bounded_file_records_deterministic", records == sorted_records),
    ]
    for index, record in enumerate(records):
        checks.extend(
            [
                _check(
                    "bounded_file_record_" + str(index) + "_content_not_copied",
                    record.get("content_copied") is False,
                ),
                _check(
                    "bounded_file_record_" + str(index) + "_raw_content_not_copied",
                    record.get("raw_content_copied") is False,
                ),
                _check(
                    "bounded_file_record_" + str(index) + "_not_symlink",
                    record.get("is_symlink") is False,
                ),
                _check(
                    "bounded_file_record_" + str(index) + "_metadata_only",
                    _record_has_no_forbidden_content_fields(record),
                ),
            ]
        )
    checks.append(
        _check(
            "candidate_manifest_metadata_only",
            _record_has_no_forbidden_content_fields(candidate),
        )
    )
    return checks


def _source_boundary_blockers(
    runner: dict[str, object],
    run: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    for source_name, payload in (("runner", runner), ("actual_run", run)):
        for field_name in _SOURCE_BOUNDARY_FIELDS:
            if payload.get(field_name) is True:
                blockers.append(
                    _blocker(
                        "source_boundary_flag_true",
                        "source artifact boundary flag is true",
                        source=source_name,
                        field=field_name,
                    )
                )
    return sorted(blockers, key=lambda item: (str(item.get("source")), str(item.get("field"))))


def _cross_artifact_checks(
    *,
    runner: dict[str, object],
    run: dict[str, object],
    candidate: dict[str, object],
    runner_manifest: dict[str, object],
    actual_output_dir: Path,
) -> list[dict[str, object]]:
    checks = [
        _same_field_check("runner_execution_id", runner, run),
        _same_field_check("runner_operator_id", runner, run),
        _same_field_check("runner_admission_id", runner, run),
        _same_optional_field_check("requested_next_iteration_id", runner, run, candidate),
        _same_field_check("requested_candidate_input_dir", runner, run, candidate),
        _same_field_check("requested_next_iteration_output_dir", runner, run),
        _check(
            "actual_next_iteration_output_dir_matches_input",
            _path_text_matches(
                run.get("actual_next_iteration_output_dir"),
                actual_output_dir,
            ),
        ),
        _same_field_check("requested_limits", runner, run),
        _same_field_check("admitted_limits", runner, run, candidate),
        _same_field_check("candidate_file_count", runner, run, candidate),
        _same_field_check("candidate_total_bytes", runner, run, candidate),
        _same_field_check("candidate_max_depth_observed", runner, run, candidate),
        _same_field_check("bounded_file_records", runner, run, candidate),
        _check(
            "actual_iteration_artifacts_match_generated_files",
            _actual_iteration_artifacts_match(runner_manifest, actual_output_dir),
        ),
    ]
    return checks


def _same_field_check(field_name: str, *payloads: dict[str, object]) -> dict[str, object]:
    values = [payload.get(field_name) for payload in payloads]
    first = values[0] if values else None
    return _check(field_name + "_matches", all(value == first for value in values))


def _same_optional_field_check(
    field_name: str,
    *payloads: dict[str, object],
) -> dict[str, object]:
    values = [payload.get(field_name) for payload in payloads if field_name in payload]
    if not values:
        return _check(field_name + "_matches_if_present", True)
    first = values[0]
    return _check(field_name + "_matches_if_present", all(value == first for value in values))


def _actual_iteration_artifacts_match(
    runner_manifest: dict[str, object],
    actual_output_dir: Path,
) -> bool:
    artifacts = runner_manifest.get("actual_iteration_artifacts")
    if not isinstance(artifacts, list):
        return False
    by_role = {
        str(artifact.get("role")): artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
    }
    for role, file_name in sorted(_ACTUAL_ARTIFACT_ROLE_TO_FILE.items()):
        artifact = by_role.get(role)
        if not isinstance(artifact, dict):
            return False
        path = actual_output_dir / file_name
        if not path.exists() or not path.is_file() or path.is_symlink():
            return False
        if _normalize_path_text(Path(str(artifact.get("path")))) != _normalize_path_text(path):
            return False
        if artifact.get("sha256") != sha256_file(path):
            return False
        if artifact.get("size_bytes") != path.stat().st_size:
            return False
    return True


def _path_text_matches(value: object, expected_path: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return _normalize_path_text(Path(value)) == _normalize_path_text(expected_path)


def _record_has_no_forbidden_content_fields(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    return not any(key in _FORBIDDEN_CANDIDATE_CONTENT_FIELDS for key in record)


def _check(name: str, passed: bool) -> dict[str, object]:
    return {"check": name, "passed": bool(passed)}


def _failed_checks(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [check for check in checks if check.get("passed") is not True]


def _check_blockers(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        _blocker(
            "review_check_failed",
            "review packet check failed",
            check=str(check.get("check")),
        )
        for check in checks
    ]


def _decision_and_next_action(status: str) -> tuple[str, str]:
    if status == _READY_STATUS:
        return (_READY_DECISION, _READY_NEXT_ACTION)
    if status in ("blocked_missing_required_artifacts", "blocked_untrusted_artifacts"):
        return ("reject_and_repair_artifacts", "repair_artifacts")
    if status == "blocked_runner_not_completed":
        return ("reject_and_repair_runner", "repair_runner")
    if status == "blocked_invalid_actual_run_record":
        return ("reject_and_repair_runner", "repair_runner")
    if status == "blocked_invalid_candidate_manifest":
        return ("reject_and_repair_runner", "repair_runner")
    if status == "blocked_cross_artifact_inconsistency":
        return ("reject_and_repair_artifacts", "repair_artifacts")
    if status == "blocked_source_boundary_violation":
        return ("reject_boundary_violation", "reject_boundary_violation")
    if status == "blocked_invalid_review_packet_metadata":
        return ("reject_and_repair_review_packet", "repair_review_packet")
    return ("reject_and_repair_artifacts", "repair_artifacts")


def _missing_required_artifacts(source_artifacts: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        _blocker(
            "missing_required_artifact",
            "required generated source artifact is missing",
            artifact_role=artifact["artifact_role"],
            path=artifact["path"],
        )
        for artifact in source_artifacts
        if artifact["required"] is True and artifact["exists"] is not True
    ]


def _untrusted_artifacts(source_artifacts: list[dict[str, object]]) -> list[dict[str, object]]:
    untrusted = []
    for artifact in source_artifacts:
        if artifact["exists"] is True and artifact["trusted_generated_artifact"] is not True:
            untrusted.append(
                _blocker(
                    "untrusted_source_artifact",
                    "source artifact failed generated-artifact trust checks",
                    artifact_role=artifact["artifact_role"],
                    path=artifact["path"],
                    trust_failures=artifact["trust_failures"],
                )
            )
    return untrusted


def _public_source_artifact_ref(artifact: dict[str, object]) -> dict[str, object]:
    return {
        "role": artifact["role"],
        "artifact_role": artifact["artifact_role"],
        "source_dir_role": artifact["source_dir_role"],
        "relative_path": artifact["relative_path"],
        "path": artifact["path"],
        "sha256": artifact["sha256"],
        "size_bytes": artifact["size_bytes"],
        "exists": artifact["exists"],
        "required": artifact["required"],
        "trusted_generated_artifact": artifact["trusted_generated_artifact"],
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _manifest_payload(
    paths: dict[str, Path],
    packet: dict[str, object],
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "review_packet_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE
        ].as_posix(),
        "review_packet_sha256": sha256_file(
            paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE]
        ),
        "summary_sha256": sha256_file(
            paths[
                LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE
            ]
        ),
        "checklist_sha256": sha256_file(
            paths[
                LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE
            ]
        ),
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "review_status": packet["review_status"],
        "review_decision": packet["review_decision"],
        "next_allowed_action": packet["next_allowed_action"],
        "review_packet_created": packet["review_packet_created"],
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "candidate_input_path_checked_by_review": False,
        "candidate_input_path_listed_by_review": False,
        "candidate_input_file_read_by_review": False,
        "candidate_input_file_hashing_performed_by_review": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REVIEW_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["promotion_approved"] = False
    payload["production_scan_approved"] = False
    payload["production_promotion_granted"] = False
    payload["automatic_approval_performed"] = False
    payload["autonomous_execution_performed"] = False
    return payload


def _artifact_index_payload(output_dir: Path, paths: dict[str, Path]) -> dict[str, object]:
    entries = [
        _artifact_index_entry(output_dir, role, paths[file_name])
        for role, file_name in _REVIEW_ARTIFACTS
    ]
    payload = {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_run_review_packet_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "runner_output_dir_recursively_indexed": False,
        "actual_next_iteration_output_dir_recursively_indexed": False,
        "candidate_input_files_indexed": False,
        "raw_content_copied": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _artifact_index_manifest_payload(
    output_dir: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    payload = {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_sha256": sha256_file(paths[_ARTIFACT_INDEX_FILE]),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "job_dir": output_dir.as_posix(),
        "deterministic_ordering": True,
        "runner_output_dir_recursively_indexed": False,
        "actual_next_iteration_output_dir_recursively_indexed": False,
        "candidate_input_files_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _artifact_index_entry(output_dir: Path, role: str, path: Path) -> dict[str, object]:
    return {
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": path.relative_to(output_dir).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "exists": path.exists(),
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _summary_markdown(packet: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Run Review Packet",
        "",
        "- Review status: " + str(packet["review_status"]),
        "- Review decision: " + str(packet["review_decision"]),
        "- Next allowed action: " + str(packet["next_allowed_action"]),
        "- Review packet id: " + str(packet["review_packet_id"]),
        "- Reviewer id: " + str(packet["reviewer_id"]),
        "- Runner execution id: " + str(packet["runner_execution_id"]),
        "- Runner operator id: " + str(packet["runner_operator_id"]),
        "- Runner admission id: " + str(packet["runner_admission_id"]),
        "- Requested next iteration id: " + str(packet["requested_next_iteration_id"]),
        "- Requested candidate input dir: `" + str(packet["requested_candidate_input_dir"]) + "`",
        "- Requested next iteration output dir: `" + str(packet["requested_next_iteration_output_dir"]) + "`",
        "- Actual next iteration output dir: `" + str(packet["actual_next_iteration_output_dir"]) + "`",
        "- Requested limits: " + json.dumps(packet["requested_limits"], sort_keys=True),
        "- Admitted limits: " + json.dumps(packet["admitted_limits"], sort_keys=True),
        "- Candidate file count: " + str(packet["candidate_file_count"]),
        "- Candidate total bytes: " + str(packet["candidate_total_bytes"]),
        "- Max depth observed: " + str(packet["candidate_max_depth_observed"]),
        "- Candidate limit enforced: " + _bool_text(packet["candidate_limit_enforced"]),
        "- Candidate symlink count: " + str(len(_list_or_empty(packet["candidate_symlinks_detected"]))),
        "- Runner execution performed: " + _bool_text(packet["runner_execution_performed"]),
        "- Next bounded smoke iteration executed: " + _bool_text(packet["next_bounded_smoke_iteration_executed"]),
        "- Promotion approved: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: " + str(len(_list_or_empty(packet["missing_required_artifacts"]))),
        "- Untrusted count: " + str(len(_list_or_empty(packet["untrusted_artifacts"]))),
        "- Cross-artifact check count: " + str(len(_list_or_empty(packet["cross_artifact_checks"]))),
        "- Blocker count: " + str(len(_list_or_empty(packet["review_blockers"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- review packet only",
        "- no runner re-execution",
        "- no candidate path validation by review",
        "- no candidate path listing by review",
        "- no candidate file read by review",
        "- no candidate file hash by review",
        "- no production scan",
        "- no production promotion",
        "- no media organizer",
        "- no file move",
        "- no file rename",
        "- no file deletion",
        "- no duplicate deletion",
        "- no raw private content copied",
        "- no network",
        "- no model API",
        "- no external runtime",
        "- no automatic approval",
        "- no autonomy",
    ]
    return "\n".join(lines) + "\n"


def _checklist_markdown() -> str:
    items = [
        "verify runner artifact exists and is trusted",
        "verify actual run artifact exists and is trusted",
        "verify candidate manifest exists and is trusted",
        "verify runner completed exactly once",
        "verify actual run completed under admitted limits",
        "verify candidate manifest contains metadata only",
        "verify bounded file records contain no raw content",
        "verify candidate symlink list is empty",
        "verify candidate limits are enforced",
        "verify runner/run/candidate counts match",
        "verify runner/run/candidate byte totals match",
        "verify runner/run/candidate max depth match",
        "verify runner/run/candidate bounded file records match",
        "verify no runner re-execution occurred",
        "verify no candidate access occurred during review",
        "verify no production scan is approved",
        "verify no production promotion is granted",
        "verify no file move/rename/delete occurred",
        "verify no duplicate deletion occurred",
        "verify no media organizer behavior occurred",
        "verify no raw private content copied",
        "verify no network/model/external runtime was used",
        "verify promotion gate is separate",
    ]
    return "# Run Review Packet Checklist\n\n" + "\n".join(
        "- [ ] " + item for item in items
    ) + "\n"


def _launcher_payload_from_packet(
    packet: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_next_bounded_smoke_iteration_run_review_packet_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_MANIFEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_SUMMARY_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_REVIEW_PACKET_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "runner_output_dir": packet["runner_output_dir"],
        "actual_next_iteration_output_dir": packet["actual_next_iteration_output_dir"],
        "output_dir": packet["output_dir"],
        "project_id": packet["project_id"],
        "review_packet_id": packet["review_packet_id"],
        "reviewer_id": packet["reviewer_id"],
        "runner_execution_id": packet["runner_execution_id"],
        "runner_operator_id": packet["runner_operator_id"],
        "runner_admission_id": packet["runner_admission_id"],
        "requested_next_iteration_id": packet["requested_next_iteration_id"],
        "requested_candidate_input_dir": packet["requested_candidate_input_dir"],
        "requested_next_iteration_output_dir": packet[
            "requested_next_iteration_output_dir"
        ],
        "requested_limits": packet["requested_limits"],
        "admitted_limits": packet["admitted_limits"],
        "review_status": packet["review_status"],
        "review_decision": packet["review_decision"],
        "next_allowed_action": packet["next_allowed_action"],
        "review_packet_created": packet["review_packet_created"],
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REVIEW_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    payload["automatic_approval_performed"] = False
    payload["autonomous_execution_performed"] = False
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    inputs: dict[str, object],
    *,
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationRunReviewPacketResult:
    status = "blocked_unknown"
    decision, next_action = _decision_and_next_action(status)
    payload = {
        "complete": False,
        "artifacts_written": False,
        "runner_output_dir": roots["runner_output_dir"].as_posix(),
        "actual_next_iteration_output_dir": roots[
            "actual_next_iteration_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "project_id": inputs.get("project_id"),
        "review_packet_id": inputs.get("review_packet_id"),
        "reviewer_id": inputs.get("reviewer_id"),
        "review_status": status,
        "review_decision": decision,
        "next_allowed_action": next_action,
        "review_packet_created": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "failure_stage": failure_stage,
        "error_message": error_message,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REVIEW_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return LocalAssetNextBoundedSmokeIterationRunReviewPacketResult(
        runner_output_dir=roots["runner_output_dir"],
        actual_next_iteration_output_dir=roots["actual_next_iteration_output_dir"],
        output_dir=roots["output_dir"],
        review_packet_path=None,
        review_packet_manifest_path=None,
        review_packet_summary_path=None,
        review_packet_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        review_status=status,
        review_decision=decision,
        payload=payload,
    )


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    normalized = content if content.endswith("\n") else content + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(normalized)


def _dict_payload(payloads: dict[str, object], role: str) -> dict[str, object]:
    value = payloads.get(role)
    return dict(value) if isinstance(value, dict) else {}


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_dict(*values: object) -> dict[str, object]:
    for value in values:
        if isinstance(value, dict):
            return dict(value)
    return {}


def _first_present(*values: object) -> object:
    for value in values:
        if value is not None:
            return value
    return None


def _list_or_empty(value: object) -> list:
    return list(value) if isinstance(value, list) else []


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _blocker(reason: str, message: str, **extra: object) -> dict[str, object]:
    payload = {"reason": reason, "message": message}
    payload.update(extra)
    return payload
