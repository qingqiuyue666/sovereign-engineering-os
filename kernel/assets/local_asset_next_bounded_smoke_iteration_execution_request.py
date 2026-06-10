"""Request-only record for a future bounded local asset smoke iteration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE",
    "LocalAssetNextBoundedSmokeIterationExecutionRequestResult",
    "build_local_asset_next_bounded_smoke_iteration_execution_request",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_execution_request.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_REQUEST_TYPE = "local_asset_next_bounded_smoke_iteration_execution_request_v1"
_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_manifest_v1"
)
_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_v1"
)
_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_execution_request_record"
_EXECUTION_CAPABILITY = (
    "local_asset_next_bounded_smoke_iteration_execution_request_only"
)

_SOURCE_ADMISSION_TYPE = "local_asset_next_bounded_smoke_iteration_admission_v1"
_SOURCE_ADMISSION_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_admission_manifest_v1"
)
_SOURCE_ADMISSION_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_admission_artifact_index_v1"
)
_SOURCE_ADMISSION_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_admission_artifact_index_manifest_v1"
)

_SOURCE_READY_STATUS = "next_bounded_smoke_iteration_admission_ready"
_SOURCE_READY_DECISION = "admit_prepare_next_bounded_smoke_iteration"
_SOURCE_READY_NEXT_ACTION = "create_next_bounded_smoke_iteration_execution_request"

_READY_STATUS = "next_bounded_smoke_iteration_execution_request_ready"
_READY_DECISION = "create_future_bounded_smoke_iteration_execution_request"
_READY_NEXT_ACTION = "await_separate_bounded_smoke_iteration_runner"

_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "create_next_iteration_output_dir",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_path_validation",
    "candidate_file_read",
    "candidate_file_hashing",
    "candidate_file_mutation",
    "duplicate_deletion",
    "media_organizer_behavior",
)
_SOURCE_REQUIRED_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_file_mutation",
    "duplicate_deletion",
    "media_organizer_behavior",
)

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_request": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "next_admission_run_performed": False,
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
    "candidate_path_validation_performed": False,
    "candidate_path_listing_performed": False,
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

_REQUEST_FALSE_FLAGS = {
    "next_bounded_smoke_iteration_execute_allowed": False,
    "next_bounded_smoke_iteration_executed": False,
    "next_iteration_output_dir_created": False,
    "candidate_input_path_checked": False,
    "candidate_input_path_listed": False,
    "candidate_input_file_read": False,
    "candidate_input_file_hashing_performed": False,
    "requested_next_iteration_output_dir_created": False,
    "production_scan_approved": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_SOURCE_BOUNDARY_FALSE_FIELDS = tuple(
    sorted(
        set(_BOUNDARY_FLAGS)
        | set(_REQUEST_FALSE_FLAGS)
        | {
            "bounded_smoke_iteration_performed_by_admission",
            "candidate_path_checked",
            "candidate_path_listed",
            "candidate_file_read",
            "candidate_file_hashing_performed",
        }
    )
)

_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_REQUEST_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_execution_request",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE,
    ),
)


@dataclass(frozen=True)
class _SourceArtifactSpec:
    role: str
    relative_path: str
    required: bool
    json_artifact: bool
    expected_field: str | None = None
    expected_value: object | None = None


_SOURCE_ARTIFACTS = (
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission",
        "local_asset_next_bounded_smoke_iteration_admission.json",
        True,
        True,
        "admission_type",
        _SOURCE_ADMISSION_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission_manifest",
        "local_asset_next_bounded_smoke_iteration_admission_manifest.json",
        True,
        True,
        "manifest_type",
        _SOURCE_ADMISSION_MANIFEST_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission_artifact_index",
        "artifact_index.json",
        True,
        True,
        "index_type",
        _SOURCE_ADMISSION_INDEX_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        _SOURCE_ADMISSION_INDEX_MANIFEST_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission_summary",
        "local_asset_next_bounded_smoke_iteration_admission_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_admission_checklist",
        "local_asset_next_bounded_smoke_iteration_admission_checklist.md",
        False,
        False,
    ),
)


@dataclass(frozen=True)
class LocalAssetNextBoundedSmokeIterationExecutionRequestResult:
    next_admission_output_dir: Path
    output_dir: Path
    request_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    request_status: str
    request_decision: str
    payload: dict[str, object]


def build_local_asset_next_bounded_smoke_iteration_execution_request(
    next_admission_output_dir: Path,
    output_dir: Path,
    *,
    requested_next_iteration_id: str,
    requested_candidate_input_dir: str,
    requested_next_iteration_output_dir: str,
    requested_max_files: int,
    requested_max_total_bytes: int,
    requested_max_depth: int,
    project_id: str | None = None,
    request_id: str | None = None,
    operator_id: str | None = None,
    operator_notes: str | None = None,
    requested_compare_previous_scan_manifest_path: str | None = None,
    requested_previous_iteration_artifact_index_path: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationExecutionRequestResult:
    """Create a durable, non-executing future iteration request record."""

    roots = {
        "next_admission_output_dir": Path(next_admission_output_dir),
        "output_dir": Path(output_dir),
    }
    paths = _output_paths(roots["output_dir"])
    request_inputs = _request_inputs(
        requested_next_iteration_id=requested_next_iteration_id,
        requested_candidate_input_dir=requested_candidate_input_dir,
        requested_next_iteration_output_dir=requested_next_iteration_output_dir,
        requested_max_files=requested_max_files,
        requested_max_total_bytes=requested_max_total_bytes,
        requested_max_depth=requested_max_depth,
        project_id=project_id,
        request_id=request_id,
        operator_id=operator_id,
        operator_notes=operator_notes,
        requested_compare_previous_scan_manifest_path=(
            requested_compare_previous_scan_manifest_path
        ),
        requested_previous_iteration_artifact_index_path=(
            requested_previous_iteration_artifact_index_path
        ),
    )
    output_error = _output_preflight_error(roots, paths)
    if output_error is not None:
        return _structured_failure_result(
            roots,
            request_inputs=request_inputs,
            failure_stage=output_error["failure_stage"],
            error_message=output_error["error_message"],
        )

    next_admission_root_error = _next_admission_root_error(
        roots["next_admission_output_dir"]
    )
    source_artifacts = _source_artifact_records(
        roots["next_admission_output_dir"],
        next_admission_root_error=next_admission_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_trust_failures(source_artifacts, source_payloads)

    request = _request_payload(
        roots=roots,
        request_inputs=request_inputs,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
        next_admission_root_error=next_admission_root_error,
    )
    summary = _summary_markdown(request)
    checklist = _checklist_markdown(request)

    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE],
        request,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE
        ],
        checklist,
    )
    manifest = _request_manifest_payload(paths, source_artifacts, request)
    _write_json_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE
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

    complete = request["request_status"] == _READY_STATUS
    payload = _launcher_payload_from_request(request, paths, complete=complete)
    return LocalAssetNextBoundedSmokeIterationExecutionRequestResult(
        next_admission_output_dir=roots["next_admission_output_dir"],
        output_dir=roots["output_dir"],
        request_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE
        ],
        manifest_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE
        ],
        summary_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE
        ],
        checklist_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        request_status=str(request["request_status"]),
        request_decision=str(request["request_decision"]),
        payload=payload,
    )


def _request_inputs(
    *,
    requested_next_iteration_id: object,
    requested_candidate_input_dir: object,
    requested_next_iteration_output_dir: object,
    requested_max_files: object,
    requested_max_total_bytes: object,
    requested_max_depth: object,
    project_id: object,
    request_id: object,
    operator_id: object,
    operator_notes: object,
    requested_compare_previous_scan_manifest_path: object,
    requested_previous_iteration_artifact_index_path: object,
) -> dict[str, object]:
    return {
        "project_id": _optional_text(project_id),
        "request_id": _optional_text(request_id),
        "operator_id": _optional_text(operator_id),
        "operator_notes": operator_notes if operator_notes is not None else None,
        "operator_notes_present": operator_notes is not None,
        "requested_next_iteration_id": _metadata_text(
            requested_next_iteration_id
        ),
        "requested_candidate_input_dir": _metadata_text(
            requested_candidate_input_dir
        ),
        "requested_next_iteration_output_dir": _metadata_text(
            requested_next_iteration_output_dir
        ),
        "requested_compare_previous_scan_manifest_path": _optional_metadata_text(
            requested_compare_previous_scan_manifest_path
        ),
        "requested_previous_iteration_artifact_index_path": _optional_metadata_text(
            requested_previous_iteration_artifact_index_path
        ),
        "requested_max_files": requested_max_files,
        "requested_max_total_bytes": requested_max_total_bytes,
        "requested_max_depth": requested_max_depth,
    }


def _metadata_text(value: object) -> str | None:
    if not isinstance(value, (str, Path)):
        return None
    text = str(value)
    return text if text else None


def _optional_metadata_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, Path)):
        return None
    return str(value)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else None


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {file_name: output_dir / file_name for file_name in _OUTPUT_FILES}


def _output_preflight_error(
    roots: dict[str, Path],
    paths: dict[str, Path],
) -> dict[str, str] | None:
    output_error = _real_existing_dir_error(roots["output_dir"], "output_dir")
    if output_error is not None:
        return {
            "failure_stage": "preflight_output_dir_missing",
            "error_message": output_error,
        }
    overlap_error = _root_overlap_error(
        roots["next_admission_output_dir"],
        roots["output_dir"],
    )
    if overlap_error is not None:
        return {
            "failure_stage": "preflight_root_overlap",
            "error_message": overlap_error,
        }
    collision = _existing_output_collision(paths)
    if collision is not None:
        return {
            "failure_stage": "preflight_output_collision",
            "error_message": (
                "local asset next bounded smoke iteration execution request output "
                "already exists: "
                + collision
            ),
        }
    return None


def _next_admission_root_error(path: Path) -> str | None:
    return _real_existing_dir_error(path, "next_admission_output_dir")


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


def _root_overlap_error(
    next_admission_output_dir: Path,
    output_dir: Path,
) -> str | None:
    try:
        admission_root = next_admission_output_dir.resolve(strict=False)
        output_root = output_dir.resolve(strict=False)
    except OSError:
        return None
    if admission_root == output_root:
        return "output_dir must not equal next_admission_output_dir"
    if _path_is_inside(output_root, admission_root):
        return "output_dir must not be inside next_admission_output_dir"
    if _path_is_inside(admission_root, output_root):
        return "next_admission_output_dir must not be inside output_dir"
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
    next_admission_output_dir: Path,
    *,
    next_admission_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    root_safe = next_admission_root_error is None
    for spec in _SOURCE_ARTIFACTS:
        path = next_admission_output_dir / spec.relative_path
        exists = root_safe and path.exists()
        is_symlink = path.is_symlink() if root_safe else False
        is_file = path.is_file() if exists and not is_symlink else False
        trusted = exists and is_file and not is_symlink
        record = {
            "role": spec.role,
            "artifact_role": spec.role,
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
        if next_admission_root_error is not None and spec.required:
            record["root_error"] = next_admission_root_error
        records.append(record)
    return sorted(records, key=lambda record: str(record["artifact_role"]))


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


def _mark_trust_failures(
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> None:
    records_by_role = _records_by_role(source_artifacts)
    for record in source_artifacts:
        if "parse_error" in record:
            _mark_untrusted(record, str(record["parse_error"]))
    for spec in _SOURCE_ARTIFACTS:
        if spec.expected_field is None:
            continue
        payload = _dict_payload(source_payloads, spec.role)
        if not payload:
            continue
        if payload.get(spec.expected_field) != spec.expected_value:
            _mark_untrusted(
                records_by_role[spec.role],
                "type_mismatch",
                expected_field=spec.expected_field,
                expected_value=spec.expected_value,
                actual_value=payload.get(spec.expected_field),
            )
    for role in _hash_mismatch_roles(records_by_role, source_payloads):
        if role in records_by_role:
            _mark_untrusted(records_by_role[role], "hash_mismatch")


def _hash_mismatch_roles(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
) -> list[str]:
    mismatches: list[str] = []
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="local_asset_next_bounded_smoke_iteration_admission_manifest",
            field_roles=(
                (
                    "admission_sha256",
                    "local_asset_next_bounded_smoke_iteration_admission",
                ),
                (
                    "summary_sha256",
                    "local_asset_next_bounded_smoke_iteration_admission_summary",
                ),
                (
                    "checklist_sha256",
                    "local_asset_next_bounded_smoke_iteration_admission_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role=(
                "local_asset_next_bounded_smoke_iteration_admission_artifact_index_manifest"
            ),
            field_roles=(
                (
                    "artifact_index_sha256",
                    "local_asset_next_bounded_smoke_iteration_admission_artifact_index",
                ),
            ),
        )
    )
    return sorted(set(mismatches))


def _manifest_file_hash_mismatches(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    manifest_role: str,
    field_roles: tuple[tuple[str, str], ...],
) -> list[str]:
    manifest = _dict_payload(source_payloads, manifest_role)
    if not manifest:
        return []
    mismatches = []
    for field_name, artifact_role in field_roles:
        record = records_by_role.get(artifact_role, {})
        if record.get("exists") is not True:
            continue
        if manifest.get(field_name) != record.get("sha256"):
            mismatches.append(manifest_role)
    return mismatches


def _mark_untrusted(
    record: dict[str, object],
    reason: str,
    **extra: object,
) -> None:
    record["trusted_generated_artifact"] = False
    reasons = _string_list(record.get("trust_failure_reasons"))
    reasons.append(reason)
    record["trust_failure_reasons"] = sorted(set(reasons))
    for key, value in extra.items():
        record[key] = value


def _request_payload(
    *,
    roots: dict[str, Path],
    request_inputs: dict[str, object],
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
    next_admission_root_error: str | None,
) -> dict[str, object]:
    admission = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_admission",
    )
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    malformed = _admission_record_malformed(admission)
    boundary_violations = _admission_boundary_violations(admission)
    invalid_limits = _invalid_requested_limits(request_inputs)
    invalid_metadata = _invalid_requested_metadata(request_inputs)

    status, decision, next_action, request_created = _request_outcome(
        missing_required=missing_required,
        untrusted=untrusted,
        malformed=malformed,
        admission=admission,
        boundary_violations=boundary_violations,
        invalid_limits=invalid_limits,
        invalid_metadata=invalid_metadata,
    )
    project = _first_text(request_inputs["project_id"], admission.get("project_id"))
    blockers = _request_blockers(
        status=status,
        missing_required=missing_required,
        untrusted=untrusted,
        malformed=malformed,
        boundary_violations=boundary_violations,
        invalid_limits=invalid_limits,
        invalid_metadata=invalid_metadata,
        next_admission_root_error=next_admission_root_error,
        admission=admission,
    )
    payload = {
        "request_type": _REQUEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project,
        "request_id": request_inputs["request_id"],
        "operator_id": request_inputs["operator_id"],
        "operator_notes_present": request_inputs["operator_notes_present"],
        "operator_notes": request_inputs["operator_notes"],
        "next_admission_output_dir": roots[
            "next_admission_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "requested_next_iteration_id": request_inputs[
            "requested_next_iteration_id"
        ],
        "requested_candidate_input_dir": request_inputs[
            "requested_candidate_input_dir"
        ],
        "requested_next_iteration_output_dir": request_inputs[
            "requested_next_iteration_output_dir"
        ],
        "requested_compare_previous_scan_manifest_path": request_inputs[
            "requested_compare_previous_scan_manifest_path"
        ],
        "requested_previous_iteration_artifact_index_path": request_inputs[
            "requested_previous_iteration_artifact_index_path"
        ],
        "requested_limits": {
            "requested_max_files": request_inputs["requested_max_files"],
            "requested_max_total_bytes": request_inputs[
                "requested_max_total_bytes"
            ],
            "requested_max_depth": request_inputs["requested_max_depth"],
        },
        "admission_status": admission.get("admission_status"),
        "admission_decision": admission.get("admission_decision"),
        "admission_next_allowed_action": admission.get("next_allowed_action"),
        "requested_next_iteration_id_from_admission": admission.get(
            "requested_next_iteration_id"
        ),
        "next_bounded_smoke_iteration_prepare_admitted": admission.get(
            "next_bounded_smoke_iteration_prepare_admitted"
        )
        is True,
        "source_admission_next_bounded_smoke_iteration_execute_allowed": (
            admission.get("next_bounded_smoke_iteration_execute_allowed")
        ),
        "source_admission_next_bounded_smoke_iteration_executed": admission.get(
            "next_bounded_smoke_iteration_executed"
        ),
        "source_admission_next_iteration_output_dir_created": admission.get(
            "next_iteration_output_dir_created"
        ),
        "source_admission_production_scan_approved": admission.get(
            "production_scan_approved"
        ),
        "source_admission_production_promotion_granted": admission.get(
            "production_promotion_granted"
        ),
        "source_admission_automatic_approval_performed": admission.get(
            "automatic_approval_performed"
        ),
        "source_admission_autonomous_execution_performed": admission.get(
            "autonomous_execution_performed"
        ),
        "request_status": status,
        "request_decision": decision,
        "next_allowed_action": next_action,
        "future_execution_request_created": request_created,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "source_artifacts": source_artifacts,
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "invalid_admission_record": malformed,
        "invalid_requested_limits": invalid_limits,
        "invalid_requested_metadata": invalid_metadata,
        "request_blockers": blockers,
        "request_checklist": {"items": _checklist_items()},
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _request_outcome(
    *,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    malformed: list[dict[str, object]],
    admission: dict[str, object],
    boundary_violations: list[dict[str, object]],
    invalid_limits: list[dict[str, object]],
    invalid_metadata: list[dict[str, object]],
) -> tuple[str, str, str, bool]:
    if missing_required:
        return (
            "blocked_missing_required_artifacts",
            "reject_and_repair_artifacts",
            "repair_artifacts",
            False,
        )
    if untrusted:
        return (
            "blocked_untrusted_artifacts",
            "reject_and_repair_artifacts",
            "repair_artifacts",
            False,
        )
    if malformed:
        return (
            "blocked_invalid_admission_record",
            "reject_and_repair_admission",
            "repair_admission",
            False,
        )
    if admission.get("admission_status") != _SOURCE_READY_STATUS:
        return (
            "blocked_admission_not_ready",
            "reject_and_repair_admission",
            "repair_admission",
            False,
        )
    if admission.get("next_bounded_smoke_iteration_prepare_admitted") is not True:
        return (
            "blocked_prepare_not_admitted",
            "reject_and_repair_admission",
            "repair_admission",
            False,
        )
    if admission.get("next_bounded_smoke_iteration_execute_allowed") is True:
        return (
            "blocked_execution_already_allowed",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if admission.get("next_bounded_smoke_iteration_executed") is True:
        return (
            "blocked_iteration_already_executed",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if admission.get("next_iteration_output_dir_created") is True:
        return (
            "blocked_next_iteration_output_already_created",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if boundary_violations:
        return (
            "blocked_production_boundary_violation",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if invalid_limits:
        return (
            "blocked_invalid_requested_limits",
            "reject_and_repair_request",
            "repair_request",
            False,
        )
    if invalid_metadata:
        return (
            "blocked_invalid_requested_metadata",
            "reject_and_repair_request",
            "repair_request",
            False,
        )
    return (_READY_STATUS, _READY_DECISION, _READY_NEXT_ACTION, True)


def _admission_record_malformed(
    admission: dict[str, object],
) -> list[dict[str, object]]:
    if not admission:
        return []
    malformed = []
    required_text_fields = ("admission_status", "admission_decision", "next_allowed_action")
    for field_name in required_text_fields:
        if not isinstance(admission.get(field_name), str) or not admission[field_name]:
            malformed.append(
                _malformed(
                    field_name,
                    "admission field is missing or not text",
                )
            )
    for field_name in (
        "next_bounded_smoke_iteration_prepare_admitted",
        "next_bounded_smoke_iteration_execute_allowed",
        "next_bounded_smoke_iteration_executed",
        "next_iteration_output_dir_created",
        "production_scan_approved",
        "production_promotion_granted",
        "automatic_approval_performed",
        "autonomous_execution_performed",
        "required_human_approval",
        "required_human_review",
    ):
        if not isinstance(admission.get(field_name), bool):
            malformed.append(
                _malformed(
                    field_name,
                    "admission field is missing or not boolean",
                )
            )
    disallowed_actions = admission.get("disallowed_actions")
    if not isinstance(disallowed_actions, list) or not all(
        isinstance(item, str) for item in disallowed_actions
    ):
        malformed.append(
            _malformed("disallowed_actions", "disallowed actions are malformed")
        )
    else:
        missing_actions = [
            action
            for action in _SOURCE_REQUIRED_DISALLOWED_ACTIONS
            if action not in disallowed_actions
        ]
        if missing_actions:
            malformed.append(
                _malformed(
                    "disallowed_actions",
                    "required disallowed actions are missing",
                    missing_actions=missing_actions,
                )
            )
    if admission.get("admission_status") == _SOURCE_READY_STATUS:
        if admission.get("admission_decision") != _SOURCE_READY_DECISION:
            malformed.append(
                _malformed(
                    "admission_decision",
                    "ready admission status must admit prepare only",
                )
            )
        if admission.get("next_allowed_action") != _SOURCE_READY_NEXT_ACTION:
            malformed.append(
                _malformed(
                    "next_allowed_action",
                    "ready admission must permit execution request creation only",
                )
            )
    elif admission.get("admission_decision") == _SOURCE_READY_DECISION:
        malformed.append(
            _malformed(
                "admission_status",
                "prepare admission decision must have ready admission status",
            )
        )
    return sorted(malformed, key=lambda item: str(item["field"]))


def _invalid_requested_limits(
    request_inputs: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    specs = (
        ("requested_max_files", 1),
        ("requested_max_total_bytes", 1),
        ("requested_max_depth", 0),
    )
    for field_name, minimum in specs:
        value = request_inputs[field_name]
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            invalid.append(
                _malformed(
                    field_name,
                    "requested limit is missing or outside the allowed bounds",
                    minimum=minimum,
                    actual_value=value,
                )
            )
    return sorted(invalid, key=lambda item: str(item["field"]))


def _invalid_requested_metadata(
    request_inputs: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    for field_name in (
        "requested_next_iteration_id",
        "requested_candidate_input_dir",
        "requested_next_iteration_output_dir",
    ):
        if not isinstance(request_inputs.get(field_name), str) or not request_inputs[
            field_name
        ]:
            invalid.append(
                _malformed(
                    field_name,
                    "requested metadata field is missing or not text",
                )
            )
    for field_name in ("project_id", "request_id", "operator_id"):
        value = request_inputs.get(field_name)
        if value is not None and (not isinstance(value, str) or not value):
            invalid.append(
                _malformed(
                    field_name,
                    "optional metadata field must be absent or non-empty text",
                )
            )
    if request_inputs["operator_notes"] is not None and not isinstance(
        request_inputs["operator_notes"],
        str,
    ):
        invalid.append(
            _malformed("operator_notes", "operator notes must be text when present")
        )
    for field_name in (
        "requested_compare_previous_scan_manifest_path",
        "requested_previous_iteration_artifact_index_path",
    ):
        value = request_inputs.get(field_name)
        if value is not None and (not isinstance(value, str) or not value):
            invalid.append(
                _malformed(
                    field_name,
                    "optional requested path metadata must be absent or non-empty text",
                )
            )
    return sorted(invalid, key=lambda item: str(item["field"]))


def _admission_boundary_violations(
    admission: dict[str, object],
) -> list[dict[str, object]]:
    if not admission:
        return []
    violations = []
    for field_name in _SOURCE_BOUNDARY_FALSE_FIELDS:
        if admission.get(field_name) is True:
            violations.append(
                {
                    "field": field_name,
                    "reason": "source admission boundary flag must be false",
                }
            )
    return sorted(violations, key=lambda item: str(item["field"]))


def _malformed(field: str, reason: str, **extra: object) -> dict[str, object]:
    payload = {"field": field, "reason": reason}
    payload.update(extra)
    return payload


def _request_blockers(
    *,
    status: str,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    malformed: list[dict[str, object]],
    boundary_violations: list[dict[str, object]],
    invalid_limits: list[dict[str, object]],
    invalid_metadata: list[dict[str, object]],
    next_admission_root_error: str | None,
    admission: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if next_admission_root_error is not None:
        blockers.append(
            _blocker("next_admission_output_dir_invalid", next_admission_root_error)
        )
    if missing_required:
        blockers.append(
            _blocker(
                "missing_required_artifacts",
                "required generated next admission artifacts are missing",
                artifacts=[item["artifact_role"] for item in missing_required],
            )
        )
    if untrusted:
        blockers.append(
            _blocker(
                "untrusted_artifacts",
                "generated next admission artifacts are untrusted, malformed, or hash mismatched",
                artifacts=[item["artifact_role"] for item in untrusted],
            )
        )
    if malformed:
        blockers.append(
            _blocker(
                "invalid_admission_record",
                "next admission record is malformed or internally inconsistent",
                violations=malformed,
            )
        )
    if status == "blocked_admission_not_ready":
        blockers.append(
            _blocker(
                "admission_not_ready",
                "next admission did not reach ready prepare-only status",
                admission_status=admission.get("admission_status"),
                admission_decision=admission.get("admission_decision"),
            )
        )
    if status == "blocked_prepare_not_admitted":
        blockers.append(
            _blocker(
                "prepare_not_admitted",
                "next admission did not admit prepare-only next iteration setup",
            )
        )
    if status == "blocked_execution_already_allowed":
        blockers.append(
            _blocker(
                "execution_already_allowed",
                "next admission unexpectedly granted execution permission",
            )
        )
    if status == "blocked_iteration_already_executed":
        blockers.append(
            _blocker(
                "iteration_already_executed",
                "next admission claims the next iteration already executed",
            )
        )
    if status == "blocked_next_iteration_output_already_created":
        blockers.append(
            _blocker(
                "next_iteration_output_already_created",
                "next admission claims the future iteration output directory already exists",
            )
        )
    if boundary_violations:
        blockers.append(
            _blocker(
                "production_or_mutation_boundary_violation",
                "next admission claims or permits disallowed production, execution, or mutation authority",
                violations=boundary_violations,
            )
        )
    if invalid_limits:
        blockers.append(
            _blocker(
                "invalid_requested_limits",
                "requested future iteration limits are invalid",
                violations=invalid_limits,
            )
        )
    if invalid_metadata:
        blockers.append(
            _blocker(
                "invalid_requested_metadata",
                "requested future iteration metadata is invalid",
                violations=invalid_metadata,
            )
        )
    return sorted(blockers, key=lambda blocker: str(blocker["blocker_role"]))


def _missing_required_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        _public_source_artifact_ref(artifact)
        for artifact in source_artifacts
        if artifact["required"] is True and artifact["exists"] is not True
    ]


def _untrusted_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        _public_source_artifact_ref(artifact)
        for artifact in source_artifacts
        if artifact["exists"] is True
        and artifact["trusted_generated_artifact"] is not True
    ]


def _public_source_artifact_ref(
    artifact: dict[str, object],
) -> dict[str, object]:
    ref = {
        "artifact_role": artifact["artifact_role"],
        "role": artifact["role"],
        "path": artifact["path"],
        "relative_path": artifact["relative_path"],
        "required": artifact["required"],
        "exists": artifact["exists"],
        "trusted_generated_artifact": artifact["trusted_generated_artifact"],
    }
    if "trust_failure_reasons" in artifact:
        ref["trust_failure_reasons"] = artifact["trust_failure_reasons"]
    if "root_error" in artifact:
        ref["root_error"] = artifact["root_error"]
    return ref


def _blocker(blocker_role: str, message: str, **extra: object) -> dict[str, object]:
    blocker = {
        "blocker_role": blocker_role,
        "message": message,
        "blocking": True,
    }
    blocker.update(extra)
    return blocker


def _summary_markdown(request: dict[str, object]) -> str:
    limits = _dict_or_empty(request["requested_limits"])
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Execution Request",
        "",
        "- Request status: " + str(request["request_status"]),
        "- Request decision: " + str(request["request_decision"]),
        "- Next allowed action: " + str(request["next_allowed_action"]),
        "- Request id: " + str(request["request_id"]),
        "- Operator id: " + str(request["operator_id"]),
        "- Requested next iteration id: "
        + str(request["requested_next_iteration_id"]),
        "- Requested candidate input dir: "
        + str(request["requested_candidate_input_dir"]),
        "- Requested next iteration output dir: "
        + str(request["requested_next_iteration_output_dir"]),
        "- Requested max files: " + str(limits.get("requested_max_files")),
        "- Requested max total bytes: "
        + str(limits.get("requested_max_total_bytes")),
        "- Requested max depth: " + str(limits.get("requested_max_depth")),
        "- Admission status: " + str(request["admission_status"]),
        "- Admission decision: " + str(request["admission_decision"]),
        "- Prepare admitted: "
        + str(request["next_bounded_smoke_iteration_prepare_admitted"]).lower(),
        "- Execute allowed: false",
        "- Next iteration executed: false",
        "- Next iteration output dir created: false",
        "- Requested next iteration output dir created: false",
        "- Candidate input path checked: false",
        "- Candidate input path listed: false",
        "- Candidate input file read: false",
        "- Candidate input file hashing performed: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: "
        + str(len(_list_or_empty(request["missing_required_artifacts"]))),
        "- Untrusted count: "
        + str(len(_list_or_empty(request["untrusted_artifacts"]))),
        "- Blocker count: " + str(len(_list_or_empty(request["request_blockers"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- No runtime stage executed.",
        "- No next bounded smoke iteration executed.",
        "- No next iteration output directory created.",
        "- No requested next iteration output directory created.",
        "- No next admission generation executed.",
        "- No candidate path validation.",
        "- No candidate path listing.",
        "- No raw candidate content read.",
        "- No candidate hashing.",
        "- No upstream mutation.",
        "- No file mutation.",
        "- No duplicate deletion.",
        "- No media organizer.",
        "- No network.",
        "- No model API.",
        "- No external runtime.",
        "- No production scan approval.",
        "- No production promotion.",
        "- No automatic approval.",
        "- Execution request artifact only.",
    ]
    return "\n".join(lines) + "\n"


def _checklist_markdown(request: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Execution Request Checklist",
        "",
    ]
    for item in _checklist_items():
        lines.append("- [ ] " + item)
    lines.extend(
        [
            "",
            "Request status: " + str(request["request_status"]),
            "Request decision: " + str(request["request_decision"]),
            "Next allowed action: " + str(request["next_allowed_action"]),
        ]
    )
    return "\n".join(lines) + "\n"


def _checklist_items() -> list[str]:
    return [
        "verify next admission artifact exists and is trusted",
        "verify admission status is ready",
        "verify admission decision admits prepare",
        "verify admission next action permits execution request creation only",
        "verify requested next iteration id is present",
        "verify requested candidate input dir is metadata only",
        "verify requested next iteration output dir is metadata only",
        "verify requested limits are positive and bounded",
        "verify execute allowed is false",
        "verify next iteration executed is false",
        "verify next iteration output dir was not created",
        "verify requested next iteration output dir was not created",
        "verify candidate path was not checked",
        "verify candidate path was not listed",
        "verify candidate file was not read",
        "verify candidate file was not hashed",
        "verify production scan is not approved",
        "verify production promotion is not granted",
        "verify no runtime stage was executed",
        "verify no input/upstream mutation occurred",
        "verify no raw private content included",
    ]


def _request_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    request: dict[str, object],
) -> dict[str, object]:
    request_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE
    ]
    summary_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE
    ]
    checklist_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE
    ]
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "request_path": request_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "checklist_path": checklist_path.as_posix(),
        "request_sha256": sha256_file(request_path),
        "summary_sha256": sha256_file(summary_path),
        "checklist_sha256": sha256_file(checklist_path),
        "source_artifacts": [
            {
                "role": artifact["role"],
                "artifact_role": artifact["artifact_role"],
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "exists": artifact["exists"],
                "required": artifact["required"],
                "trusted_generated_artifact": artifact[
                    "trusted_generated_artifact"
                ],
            }
            for artifact in source_artifacts
        ],
        "request_status": request["request_status"],
        "request_decision": request["request_decision"],
        "next_allowed_action": request["next_allowed_action"],
        "future_execution_request_created": request[
            "future_execution_request_created"
        ],
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_entry(output_dir, role, paths[file_name])
        for role, file_name in _REQUEST_ARTIFACTS
    ]
    payload = {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_next_bounded_smoke_iteration_execution_request_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "next_admission_output_recursively_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
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
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "next_admission_output_recursively_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _artifact_entry(output_dir: Path, role: str, path: Path) -> dict[str, object]:
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


def _launcher_payload_from_request(
    request: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_next_bounded_smoke_iteration_execution_request_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_MANIFEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_execution_request_summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_SUMMARY_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_EXECUTION_REQUEST_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "next_admission_output_dir": request["next_admission_output_dir"],
        "output_dir": request["output_dir"],
        "project_id": request["project_id"],
        "request_id": request["request_id"],
        "operator_id": request["operator_id"],
        "requested_next_iteration_id": request["requested_next_iteration_id"],
        "requested_candidate_input_dir": request["requested_candidate_input_dir"],
        "requested_next_iteration_output_dir": request[
            "requested_next_iteration_output_dir"
        ],
        "requested_limits": request["requested_limits"],
        "request_status": request["request_status"],
        "request_decision": request["request_decision"],
        "next_allowed_action": request["next_allowed_action"],
        "future_execution_request_created": request[
            "future_execution_request_created"
        ],
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    *,
    request_inputs: dict[str, object],
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationExecutionRequestResult:
    status = "blocked_unknown"
    decision = "reject_and_repair_artifacts"
    payload = {
        "complete": False,
        "artifacts_written": False,
        "request_type": _REQUEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": request_inputs["project_id"],
        "request_id": request_inputs["request_id"],
        "operator_id": request_inputs["operator_id"],
        "operator_notes_present": request_inputs["operator_notes_present"],
        "operator_notes": request_inputs["operator_notes"],
        "next_admission_output_dir": roots[
            "next_admission_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "requested_next_iteration_id": request_inputs[
            "requested_next_iteration_id"
        ],
        "requested_candidate_input_dir": request_inputs[
            "requested_candidate_input_dir"
        ],
        "requested_next_iteration_output_dir": request_inputs[
            "requested_next_iteration_output_dir"
        ],
        "requested_limits": {
            "requested_max_files": request_inputs["requested_max_files"],
            "requested_max_total_bytes": request_inputs[
                "requested_max_total_bytes"
            ],
            "requested_max_depth": request_inputs["requested_max_depth"],
        },
        "request_status": status,
        "request_decision": decision,
        "next_allowed_action": "repair_artifacts",
        "future_execution_request_created": False,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": error_message,
        "local_asset_next_bounded_smoke_iteration_execution_request_path": None,
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest_path": None,
        "local_asset_next_bounded_smoke_iteration_execution_request_summary_path": None,
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_REQUEST_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return LocalAssetNextBoundedSmokeIterationExecutionRequestResult(
        next_admission_output_dir=roots["next_admission_output_dir"],
        output_dir=roots["output_dir"],
        request_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        request_status=status,
        request_decision=decision,
        payload=payload,
    )


def _records_by_role(
    source_artifacts: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    return {str(record["artifact_role"]): record for record in source_artifacts}


def _dict_payload(
    source_payloads: dict[str, object],
    role: str,
) -> dict[str, object]:
    return _dict_or_empty(source_payloads.get(role))


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [str(item) for item in _list_or_empty(value)]


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)
