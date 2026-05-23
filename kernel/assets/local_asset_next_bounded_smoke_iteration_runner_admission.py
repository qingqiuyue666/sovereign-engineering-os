"""Runner-admission record for a future bounded local asset smoke iteration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE",
    "REQUIRED_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ACKNOWLEDGEMENT_PHRASE",
    "LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult",
    "build_local_asset_next_bounded_smoke_iteration_runner_admission",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_checklist.md"
)

REQUIRED_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ACKNOWLEDGEMENT_PHRASE = (
    "I_ACKNOWLEDGE_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ONLY"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_ADMISSION_TYPE = "local_asset_next_bounded_smoke_iteration_runner_admission_v1"
_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_v1"
)
_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_v1"
)
_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_runner_admission_record"
_EXECUTION_CAPABILITY = (
    "local_asset_next_bounded_smoke_iteration_runner_admission_only"
)

_SOURCE_REQUEST_TYPE = "local_asset_next_bounded_smoke_iteration_execution_request_v1"
_SOURCE_REQUEST_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_manifest_v1"
)
_SOURCE_REQUEST_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_v1"
)
_SOURCE_REQUEST_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_manifest_v1"
)

_SOURCE_READY_STATUS = "next_bounded_smoke_iteration_execution_request_ready"
_SOURCE_READY_DECISION = "create_future_bounded_smoke_iteration_execution_request"
_SOURCE_READY_NEXT_ACTION = "await_separate_bounded_smoke_iteration_runner"

_READY_STATUS = "next_bounded_smoke_iteration_runner_admission_ready"
_READY_DECISION = "admit_runner_to_consume_future_execution_request"
_READY_NEXT_ACTION = "await_separate_bounded_smoke_iteration_runner_execution"

_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "runner_execute_now",
    "create_next_iteration_output_dir",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_path_validation",
    "candidate_path_listing",
    "candidate_file_read",
    "candidate_file_hashing",
    "candidate_file_mutation",
    "duplicate_deletion",
    "media_organizer_behavior",
)
_SOURCE_REQUIRED_DISALLOWED_ACTIONS = (
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

_RUNNER_FALSE_FLAGS = {
    "runner_execution_allowed": False,
    "next_bounded_smoke_iteration_execute_allowed": False,
    "next_bounded_smoke_iteration_executed": False,
    "next_iteration_output_dir_created": False,
    "requested_next_iteration_output_dir_created": False,
    "candidate_input_path_checked": False,
    "candidate_input_path_listed": False,
    "candidate_input_file_read": False,
    "candidate_input_file_hashing_performed": False,
    "production_scan_approved": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_runner_admission": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "next_admission_run_performed": False,
    "execution_request_run_performed": False,
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

_SOURCE_FALSE_FIELDS = tuple(
    sorted(
        set(_RUNNER_FALSE_FLAGS)
        | set(_BOUNDARY_FLAGS)
        | {
            "bounded_smoke_iteration_performed_by_request",
        }
    )
)
_SOURCE_CANDIDATE_ACCESS_FIELDS = (
    "candidate_input_path_checked",
    "candidate_input_path_listed",
    "candidate_input_file_read",
    "candidate_input_file_hashing_performed",
    "candidate_file_hashing_performed",
    "candidate_path_validation_performed",
    "candidate_path_listing_performed",
    "raw_candidate_content_read",
)
_SOURCE_PRODUCTION_OR_MUTATION_FIELDS = tuple(
    sorted(
        (
            set(_SOURCE_FALSE_FIELDS)
            - set(_SOURCE_CANDIDATE_ACCESS_FIELDS)
            - {
                "next_bounded_smoke_iteration_execute_allowed",
                "next_bounded_smoke_iteration_executed",
                "next_iteration_output_dir_created",
                "requested_next_iteration_output_dir_created",
            }
        )
        | {
            "production_scan_approved",
            "production_promotion_granted",
            "automatic_approval_performed",
            "autonomous_execution_performed",
        }
    )
)

_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_ADMISSION_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE,
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
        "local_asset_next_bounded_smoke_iteration_execution_request",
        "local_asset_next_bounded_smoke_iteration_execution_request.json",
        True,
        True,
        "request_type",
        _SOURCE_REQUEST_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest",
        "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json",
        True,
        True,
        "manifest_type",
        _SOURCE_REQUEST_MANIFEST_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index",
        "artifact_index.json",
        True,
        True,
        "index_type",
        _SOURCE_REQUEST_INDEX_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        _SOURCE_REQUEST_INDEX_MANIFEST_TYPE,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_execution_request_summary",
        "local_asset_next_bounded_smoke_iteration_execution_request_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist",
        "local_asset_next_bounded_smoke_iteration_execution_request_checklist.md",
        False,
        False,
    ),
)


@dataclass(frozen=True)
class LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult:
    execution_request_output_dir: Path
    output_dir: Path
    admission_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    admission_status: str
    admission_decision: str
    payload: dict[str, object]


def build_local_asset_next_bounded_smoke_iteration_runner_admission(
    execution_request_output_dir: Path,
    output_dir: Path,
    *,
    runner_admission_id: str,
    runner_operator_id: str,
    runner_operator_acknowledgement_phrase: str,
    admitted_runner_id: str,
    admitted_runner_version: str,
    admitted_max_files: int,
    admitted_max_total_bytes: int,
    admitted_max_depth: int,
    project_id: str | None = None,
    operator_notes: str | None = None,
    runner_environment_label: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult:
    """Create a durable non-executing runner-admission artifact."""

    roots = {
        "execution_request_output_dir": Path(execution_request_output_dir),
        "output_dir": Path(output_dir),
    }
    paths = _output_paths(roots["output_dir"])
    inputs = _runner_inputs(
        runner_admission_id=runner_admission_id,
        runner_operator_id=runner_operator_id,
        runner_operator_acknowledgement_phrase=(
            runner_operator_acknowledgement_phrase
        ),
        admitted_runner_id=admitted_runner_id,
        admitted_runner_version=admitted_runner_version,
        admitted_max_files=admitted_max_files,
        admitted_max_total_bytes=admitted_max_total_bytes,
        admitted_max_depth=admitted_max_depth,
        project_id=project_id,
        operator_notes=operator_notes,
        runner_environment_label=runner_environment_label,
    )
    output_error = _output_preflight_error(roots, paths)
    if output_error is not None:
        return _structured_failure_result(
            roots,
            runner_inputs=inputs,
            failure_stage=output_error["failure_stage"],
            error_message=output_error["error_message"],
        )

    request_root_error = _execution_request_root_error(
        roots["execution_request_output_dir"]
    )
    source_artifacts = _source_artifact_records(
        roots["execution_request_output_dir"],
        request_root_error=request_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_trust_failures(source_artifacts, source_payloads)

    admission = _admission_payload(
        roots=roots,
        runner_inputs=inputs,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
        request_root_error=request_root_error,
    )
    summary = _summary_markdown(admission)
    checklist = _checklist_markdown(admission)

    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE],
        admission,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE],
        checklist,
    )
    manifest = _admission_manifest_payload(paths, source_artifacts, admission)
    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE],
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

    complete = admission["admission_status"] == _READY_STATUS
    payload = _launcher_payload_from_admission(admission, paths, complete=complete)
    return LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult(
        execution_request_output_dir=roots["execution_request_output_dir"],
        output_dir=roots["output_dir"],
        admission_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE
        ],
        manifest_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE
        ],
        summary_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE
        ],
        checklist_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        admission_status=str(admission["admission_status"]),
        admission_decision=str(admission["admission_decision"]),
        payload=payload,
    )


def _runner_inputs(
    *,
    runner_admission_id: object,
    runner_operator_id: object,
    runner_operator_acknowledgement_phrase: object,
    admitted_runner_id: object,
    admitted_runner_version: object,
    admitted_max_files: object,
    admitted_max_total_bytes: object,
    admitted_max_depth: object,
    project_id: object,
    operator_notes: object,
    runner_environment_label: object,
) -> dict[str, object]:
    acknowledgement_hash = (
        _sha256_text(runner_operator_acknowledgement_phrase)
        if isinstance(runner_operator_acknowledgement_phrase, str)
        else None
    )
    return {
        "project_id": _optional_text(project_id),
        "runner_admission_id": _optional_text(runner_admission_id),
        "runner_operator_id": _optional_text(runner_operator_id),
        "runner_operator_acknowledgement_phrase_sha256": acknowledgement_hash,
        "runner_operator_acknowledgement_phrase_valid": (
            runner_operator_acknowledgement_phrase
            == REQUIRED_LOCAL_ASSET_BOUNDED_SMOKE_RUNNER_ADMISSION_ACKNOWLEDGEMENT_PHRASE
        ),
        "admitted_runner_id": _optional_text(admitted_runner_id),
        "admitted_runner_version": _optional_text(admitted_runner_version),
        "admitted_max_files": admitted_max_files,
        "admitted_max_total_bytes": admitted_max_total_bytes,
        "admitted_max_depth": admitted_max_depth,
        "operator_notes": operator_notes if operator_notes is not None else None,
        "operator_notes_present": operator_notes is not None,
        "runner_environment_label": (
            runner_environment_label
            if runner_environment_label is not None
            else None
        ),
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        roots["execution_request_output_dir"],
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
                "local asset next bounded smoke iteration runner admission output "
                "already exists: "
                + collision
            ),
        }
    return None


def _execution_request_root_error(path: Path) -> str | None:
    return _real_existing_dir_error(path, "execution_request_output_dir")


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
        if paths[file_name].exists() or paths[file_name].is_symlink():
            return file_name
    return None


def _root_overlap_error(
    execution_request_output_dir: Path,
    output_dir: Path,
) -> str | None:
    try:
        request_root = execution_request_output_dir.resolve(strict=False)
        output_root = output_dir.resolve(strict=False)
    except OSError:
        return None
    if request_root == output_root:
        return "output_dir must not equal execution_request_output_dir"
    if _path_is_inside(output_root, request_root):
        return "output_dir must not be inside execution_request_output_dir"
    if _path_is_inside(request_root, output_root):
        return "execution_request_output_dir must not be inside output_dir"
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
    execution_request_output_dir: Path,
    *,
    request_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    root_safe = request_root_error is None
    for spec in _SOURCE_ARTIFACTS:
        path = execution_request_output_dir / spec.relative_path
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
        if request_root_error is not None and spec.required:
            record["root_error"] = request_root_error
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
            manifest_role=(
                "local_asset_next_bounded_smoke_iteration_execution_request_manifest"
            ),
            field_roles=(
                (
                    "request_sha256",
                    "local_asset_next_bounded_smoke_iteration_execution_request",
                ),
                (
                    "summary_sha256",
                    "local_asset_next_bounded_smoke_iteration_execution_request_summary",
                ),
                (
                    "checklist_sha256",
                    "local_asset_next_bounded_smoke_iteration_execution_request_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role=(
                "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index_manifest"
            ),
            field_roles=(
                (
                    "artifact_index_sha256",
                    "local_asset_next_bounded_smoke_iteration_execution_request_artifact_index",
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


def _admission_payload(
    *,
    roots: dict[str, Path],
    runner_inputs: dict[str, object],
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
    request_root_error: str | None,
) -> dict[str, object]:
    request = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_execution_request",
    )
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    invalid_acknowledgement = _invalid_acknowledgement(runner_inputs)
    invalid_metadata = _invalid_runner_metadata(runner_inputs)
    invalid_admitted_limits = _invalid_admitted_limits(runner_inputs)
    malformed_request = _execution_request_record_malformed(request)
    candidate_access = _candidate_access_violations(request)
    production_boundary = _production_or_mutation_boundary_violations(request)
    limits_exceeded = _admitted_limits_exceed_request(runner_inputs, request)

    status, decision, next_action, consume_admitted = _admission_outcome(
        missing_required=missing_required,
        untrusted=untrusted,
        invalid_acknowledgement=invalid_acknowledgement,
        invalid_metadata=invalid_metadata,
        invalid_admitted_limits=invalid_admitted_limits,
        malformed_request=malformed_request,
        request=request,
        candidate_access=candidate_access,
        production_boundary=production_boundary,
        limits_exceeded=limits_exceeded,
    )
    blockers = _runner_admission_blockers(
        status=status,
        missing_required=missing_required,
        untrusted=untrusted,
        invalid_acknowledgement=invalid_acknowledgement,
        invalid_metadata=invalid_metadata,
        invalid_admitted_limits=invalid_admitted_limits,
        malformed_request=malformed_request,
        candidate_access=candidate_access,
        production_boundary=production_boundary,
        limits_exceeded=limits_exceeded,
        request_root_error=request_root_error,
        request=request,
    )
    requested_limits = _requested_limits_from_request(request)
    payload = {
        "admission_type": _ADMISSION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": _first_text(
            runner_inputs["project_id"],
            request.get("project_id"),
        ),
        "runner_admission_id": runner_inputs["runner_admission_id"],
        "runner_operator_id": runner_inputs["runner_operator_id"],
        "runner_operator_acknowledgement_phrase_sha256": runner_inputs[
            "runner_operator_acknowledgement_phrase_sha256"
        ],
        "runner_operator_acknowledgement_phrase_persisted": False,
        "admitted_runner_id": runner_inputs["admitted_runner_id"],
        "admitted_runner_version": runner_inputs["admitted_runner_version"],
        "runner_environment_label": runner_inputs["runner_environment_label"],
        "operator_notes_present": runner_inputs["operator_notes_present"],
        "operator_notes": runner_inputs["operator_notes"],
        "execution_request_output_dir": roots[
            "execution_request_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "request_id": request.get("request_id"),
        "source_operator_id": request.get("operator_id"),
        "requested_next_iteration_id": request.get("requested_next_iteration_id"),
        "requested_candidate_input_dir": request.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": request.get(
            "requested_next_iteration_output_dir"
        ),
        "requested_compare_previous_scan_manifest_path": request.get(
            "requested_compare_previous_scan_manifest_path"
        ),
        "requested_previous_iteration_artifact_index_path": request.get(
            "requested_previous_iteration_artifact_index_path"
        ),
        "requested_limits": requested_limits,
        "admitted_limits": {
            "admitted_max_files": runner_inputs["admitted_max_files"],
            "admitted_max_total_bytes": runner_inputs[
                "admitted_max_total_bytes"
            ],
            "admitted_max_depth": runner_inputs["admitted_max_depth"],
        },
        "request_status": request.get("request_status"),
        "request_decision": request.get("request_decision"),
        "request_next_allowed_action": request.get("next_allowed_action"),
        "future_execution_request_created": (
            request.get("future_execution_request_created") is True
        ),
        "source_next_bounded_smoke_iteration_execute_allowed": request.get(
            "next_bounded_smoke_iteration_execute_allowed"
        ),
        "source_next_bounded_smoke_iteration_executed": request.get(
            "next_bounded_smoke_iteration_executed"
        ),
        "source_next_iteration_output_dir_created": request.get(
            "next_iteration_output_dir_created"
        ),
        "source_requested_next_iteration_output_dir_created": request.get(
            "requested_next_iteration_output_dir_created"
        ),
        "source_candidate_input_path_checked": request.get(
            "candidate_input_path_checked"
        ),
        "source_candidate_input_path_listed": request.get(
            "candidate_input_path_listed"
        ),
        "source_candidate_input_file_read": request.get(
            "candidate_input_file_read"
        ),
        "source_candidate_input_file_hashing_performed": request.get(
            "candidate_input_file_hashing_performed"
        ),
        "source_production_scan_approved": request.get(
            "production_scan_approved"
        ),
        "source_production_promotion_granted": request.get(
            "production_promotion_granted"
        ),
        "source_automatic_approval_performed": request.get(
            "automatic_approval_performed"
        ),
        "source_autonomous_execution_performed": request.get(
            "autonomous_execution_performed"
        ),
        "admission_status": status,
        "admission_decision": decision,
        "next_allowed_action": next_action,
        "runner_consume_request_admitted": consume_admitted,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "source_artifacts": source_artifacts,
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "invalid_runner_acknowledgement": invalid_acknowledgement,
        "invalid_runner_metadata": invalid_metadata,
        "invalid_admitted_limits": invalid_admitted_limits,
        "limits_exceed_request": limits_exceeded,
        "invalid_execution_request_record": malformed_request,
        "candidate_path_access_violations": candidate_access,
        "production_boundary_violations": production_boundary,
        "runner_admission_blockers": blockers,
        "runner_admission_checklist": {"items": _checklist_items()},
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
    }
    payload.update(_RUNNER_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _admission_outcome(
    *,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    invalid_acknowledgement: list[dict[str, object]],
    invalid_metadata: list[dict[str, object]],
    invalid_admitted_limits: list[dict[str, object]],
    malformed_request: list[dict[str, object]],
    request: dict[str, object],
    candidate_access: list[dict[str, object]],
    production_boundary: list[dict[str, object]],
    limits_exceeded: list[dict[str, object]],
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
    if invalid_acknowledgement:
        return (
            "blocked_invalid_runner_acknowledgement",
            "reject_and_repair_runner_admission",
            "repair_runner_admission",
            False,
        )
    if invalid_metadata:
        return (
            "blocked_invalid_runner_metadata",
            "reject_and_repair_runner_admission",
            "repair_runner_admission",
            False,
        )
    if invalid_admitted_limits:
        return (
            "blocked_invalid_admitted_limits",
            "reject_and_repair_runner_admission",
            "repair_runner_admission",
            False,
        )
    if malformed_request:
        return (
            "blocked_invalid_execution_request_record",
            "reject_and_repair_execution_request",
            "repair_execution_request",
            False,
        )
    if request.get("request_status") != _SOURCE_READY_STATUS:
        return (
            "blocked_execution_request_not_ready",
            "reject_and_repair_execution_request",
            "repair_execution_request",
            False,
        )
    if request.get("future_execution_request_created") is not True:
        return (
            "blocked_future_request_not_created",
            "reject_and_repair_execution_request",
            "repair_execution_request",
            False,
        )
    if request.get("next_bounded_smoke_iteration_execute_allowed") is True:
        return (
            "blocked_execution_already_allowed",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if request.get("next_bounded_smoke_iteration_executed") is True:
        return (
            "blocked_iteration_already_executed",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if (
        request.get("next_iteration_output_dir_created") is True
        or request.get("requested_next_iteration_output_dir_created") is True
    ):
        return (
            "blocked_next_iteration_output_already_created",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if candidate_access:
        return (
            "blocked_candidate_path_access_violation",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if production_boundary:
        return (
            "blocked_production_boundary_violation",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if limits_exceeded:
        return (
            "blocked_limits_exceed_request",
            "reject_and_repair_runner_admission",
            "repair_runner_admission",
            False,
        )
    return (_READY_STATUS, _READY_DECISION, _READY_NEXT_ACTION, True)


def _invalid_acknowledgement(
    runner_inputs: dict[str, object],
) -> list[dict[str, object]]:
    if runner_inputs["runner_operator_acknowledgement_phrase_valid"] is True:
        return []
    return [
        _malformed(
            "runner_operator_acknowledgement_phrase",
            "runner acknowledgement phrase did not exactly match required text",
        )
    ]


def _invalid_runner_metadata(
    runner_inputs: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    for field_name in (
        "runner_admission_id",
        "runner_operator_id",
        "admitted_runner_id",
        "admitted_runner_version",
    ):
        if not isinstance(runner_inputs.get(field_name), str) or not runner_inputs[
            field_name
        ]:
            invalid.append(
                _malformed(field_name, "runner metadata is missing or not text")
            )
    for field_name in ("project_id", "runner_environment_label"):
        value = runner_inputs.get(field_name)
        if value is not None and (not isinstance(value, str) or not value):
            invalid.append(
                _malformed(
                    field_name,
                    "optional runner metadata must be absent or non-empty text",
                )
            )
    if runner_inputs["operator_notes"] is not None and not isinstance(
        runner_inputs["operator_notes"],
        str,
    ):
        invalid.append(
            _malformed("operator_notes", "operator notes must be text when present")
        )
    return sorted(invalid, key=lambda item: str(item["field"]))


def _invalid_admitted_limits(
    runner_inputs: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    specs = (
        ("admitted_max_files", 1),
        ("admitted_max_total_bytes", 1),
        ("admitted_max_depth", 0),
    )
    for field_name, minimum in specs:
        value = runner_inputs[field_name]
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            invalid.append(
                _malformed(
                    field_name,
                    "admitted limit is missing or outside the allowed bounds",
                    minimum=minimum,
                    actual_value=value,
                )
            )
    return sorted(invalid, key=lambda item: str(item["field"]))


def _admitted_limits_exceed_request(
    runner_inputs: dict[str, object],
    request: dict[str, object],
) -> list[dict[str, object]]:
    requested_limits = _requested_limits_from_request(request)
    exceeded = []
    pairs = (
        (
            "admitted_max_files",
            "requested_max_files",
        ),
        (
            "admitted_max_total_bytes",
            "requested_max_total_bytes",
        ),
        (
            "admitted_max_depth",
            "requested_max_depth",
        ),
    )
    for admitted_field, requested_field in pairs:
        admitted = runner_inputs.get(admitted_field)
        requested = requested_limits.get(requested_field)
        if not isinstance(admitted, int) or isinstance(admitted, bool):
            continue
        if not isinstance(requested, int) or isinstance(requested, bool):
            continue
        if admitted > requested:
            exceeded.append(
                _malformed(
                    admitted_field,
                    "admitted limit exceeds requested execution request limit",
                    requested_field=requested_field,
                    requested_value=requested,
                    admitted_value=admitted,
                )
            )
    return sorted(exceeded, key=lambda item: str(item["field"]))


def _execution_request_record_malformed(
    request: dict[str, object],
) -> list[dict[str, object]]:
    if not request:
        return []
    malformed = []
    required_text_fields = ("request_status", "request_decision", "next_allowed_action")
    for field_name in required_text_fields:
        if not isinstance(request.get(field_name), str) or not request[field_name]:
            malformed.append(
                _malformed(
                    field_name,
                    "execution request field is missing or not text",
                )
            )
    for field_name in (
        "future_execution_request_created",
        "next_bounded_smoke_iteration_execute_allowed",
        "next_bounded_smoke_iteration_executed",
        "next_iteration_output_dir_created",
        "requested_next_iteration_output_dir_created",
        "candidate_input_path_checked",
        "candidate_input_path_listed",
        "candidate_input_file_read",
        "candidate_input_file_hashing_performed",
        "production_scan_approved",
        "production_promotion_granted",
        "automatic_approval_performed",
        "autonomous_execution_performed",
        "required_human_approval",
        "required_human_review",
    ):
        if not isinstance(request.get(field_name), bool):
            malformed.append(
                _malformed(
                    field_name,
                    "execution request field is missing or not boolean",
                )
            )
    for field_name in (
        "requested_next_iteration_id",
        "requested_candidate_input_dir",
        "requested_next_iteration_output_dir",
    ):
        if not isinstance(request.get(field_name), str) or not request[field_name]:
            malformed.append(
                _malformed(
                    field_name,
                    "requested metadata field is missing or not text",
                )
            )
    requested_limits = request.get("requested_limits")
    if not isinstance(requested_limits, dict):
        malformed.append(
            _malformed("requested_limits", "requested limits are malformed")
        )
    else:
        for field_name, minimum in (
            ("requested_max_files", 1),
            ("requested_max_total_bytes", 1),
            ("requested_max_depth", 0),
        ):
            value = requested_limits.get(field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                malformed.append(
                    _malformed(
                        field_name,
                        "requested limit is missing or outside allowed bounds",
                        minimum=minimum,
                        actual_value=value,
                    )
                )
    disallowed_actions = request.get("disallowed_actions")
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
    if request.get("request_status") == _SOURCE_READY_STATUS:
        if request.get("request_decision") != _SOURCE_READY_DECISION:
            malformed.append(
                _malformed(
                    "request_decision",
                    "ready execution request status must create a future request only",
                )
            )
        if request.get("next_allowed_action") != _SOURCE_READY_NEXT_ACTION:
            malformed.append(
                _malformed(
                    "next_allowed_action",
                    "ready execution request must await a separate runner",
                )
            )
    elif request.get("request_decision") == _SOURCE_READY_DECISION:
        malformed.append(
            _malformed(
                "request_status",
                "future request decision must have ready request status",
            )
        )
    return sorted(malformed, key=lambda item: str(item["field"]))


def _candidate_access_violations(
    request: dict[str, object],
) -> list[dict[str, object]]:
    return _true_field_violations(
        request,
        _SOURCE_CANDIDATE_ACCESS_FIELDS,
        "candidate path access flag must be false",
    )


def _production_or_mutation_boundary_violations(
    request: dict[str, object],
) -> list[dict[str, object]]:
    return _true_field_violations(
        request,
        _SOURCE_PRODUCTION_OR_MUTATION_FIELDS,
        "source execution request boundary flag must be false",
    )


def _true_field_violations(
    payload: dict[str, object],
    field_names: tuple[str, ...],
    reason: str,
) -> list[dict[str, object]]:
    if not payload:
        return []
    violations = []
    for field_name in field_names:
        if payload.get(field_name) is True:
            violations.append({"field": field_name, "reason": reason})
    return sorted(violations, key=lambda item: str(item["field"]))


def _runner_admission_blockers(
    *,
    status: str,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    invalid_acknowledgement: list[dict[str, object]],
    invalid_metadata: list[dict[str, object]],
    invalid_admitted_limits: list[dict[str, object]],
    malformed_request: list[dict[str, object]],
    candidate_access: list[dict[str, object]],
    production_boundary: list[dict[str, object]],
    limits_exceeded: list[dict[str, object]],
    request_root_error: str | None,
    request: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if request_root_error is not None:
        blockers.append(
            _blocker("execution_request_output_dir_invalid", request_root_error)
        )
    if missing_required:
        blockers.append(
            _blocker(
                "missing_required_artifacts",
                "required generated execution request artifacts are missing",
                artifacts=[item["artifact_role"] for item in missing_required],
            )
        )
    if untrusted:
        blockers.append(
            _blocker(
                "untrusted_artifacts",
                "generated execution request artifacts are untrusted, malformed, or hash mismatched",
                artifacts=[item["artifact_role"] for item in untrusted],
            )
        )
    if invalid_acknowledgement:
        blockers.append(
            _blocker(
                "invalid_runner_acknowledgement",
                "runner acknowledgement phrase is invalid",
                violations=invalid_acknowledgement,
            )
        )
    if invalid_metadata:
        blockers.append(
            _blocker(
                "invalid_runner_metadata",
                "runner admission metadata is invalid",
                violations=invalid_metadata,
            )
        )
    if invalid_admitted_limits:
        blockers.append(
            _blocker(
                "invalid_admitted_limits",
                "admitted runner limits are invalid",
                violations=invalid_admitted_limits,
            )
        )
    if malformed_request:
        blockers.append(
            _blocker(
                "invalid_execution_request_record",
                "execution request record is malformed or internally inconsistent",
                violations=malformed_request,
            )
        )
    if status == "blocked_execution_request_not_ready":
        blockers.append(
            _blocker(
                "execution_request_not_ready",
                "execution request did not reach ready request-only status",
                request_status=request.get("request_status"),
                request_decision=request.get("request_decision"),
            )
        )
    if status == "blocked_future_request_not_created":
        blockers.append(
            _blocker(
                "future_request_not_created",
                "execution request did not create a future request record",
            )
        )
    if status == "blocked_execution_already_allowed":
        blockers.append(
            _blocker(
                "execution_already_allowed",
                "execution request unexpectedly granted execution permission",
            )
        )
    if status == "blocked_iteration_already_executed":
        blockers.append(
            _blocker(
                "iteration_already_executed",
                "execution request claims the next iteration already executed",
            )
        )
    if status == "blocked_next_iteration_output_already_created":
        blockers.append(
            _blocker(
                "next_iteration_output_already_created",
                "execution request claims the future output directory already exists",
            )
        )
    if candidate_access:
        blockers.append(
            _blocker(
                "candidate_path_access_violation",
                "execution request claims candidate path validation, listing, read, or hashing occurred",
                violations=candidate_access,
            )
        )
    if production_boundary:
        blockers.append(
            _blocker(
                "production_or_mutation_boundary_violation",
                "execution request claims or permits disallowed production, execution, or mutation authority",
                violations=production_boundary,
            )
        )
    if limits_exceeded:
        blockers.append(
            _blocker(
                "limits_exceed_request",
                "admitted runner limits exceed requested execution request limits",
                violations=limits_exceeded,
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


def _summary_markdown(admission: dict[str, object]) -> str:
    requested_limits = _dict_or_empty(admission["requested_limits"])
    admitted_limits = _dict_or_empty(admission["admitted_limits"])
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Runner Admission",
        "",
        "- Runner admission status: " + str(admission["admission_status"]),
        "- Runner admission decision: " + str(admission["admission_decision"]),
        "- Next allowed action: " + str(admission["next_allowed_action"]),
        "- Runner admission id: " + str(admission["runner_admission_id"]),
        "- Runner operator id: " + str(admission["runner_operator_id"]),
        "- Runner acknowledgement hash present: "
        + str(
            bool(admission["runner_operator_acknowledgement_phrase_sha256"])
        ).lower(),
        "- Runner acknowledgement phrase persisted: false",
        "- Admitted runner id: " + str(admission["admitted_runner_id"]),
        "- Admitted runner version: " + str(admission["admitted_runner_version"]),
        "- Runner environment label: "
        + str(admission["runner_environment_label"]),
        "- Requested next iteration id: "
        + str(admission["requested_next_iteration_id"]),
        "- Requested candidate input dir: "
        + str(admission["requested_candidate_input_dir"]),
        "- Requested next iteration output dir: "
        + str(admission["requested_next_iteration_output_dir"]),
        "- Requested max files: " + str(requested_limits.get("requested_max_files")),
        "- Requested max total bytes: "
        + str(requested_limits.get("requested_max_total_bytes")),
        "- Requested max depth: " + str(requested_limits.get("requested_max_depth")),
        "- Admitted max files: " + str(admitted_limits.get("admitted_max_files")),
        "- Admitted max total bytes: "
        + str(admitted_limits.get("admitted_max_total_bytes")),
        "- Admitted max depth: " + str(admitted_limits.get("admitted_max_depth")),
        "- Execution request status: " + str(admission["request_status"]),
        "- Execution request decision: " + str(admission["request_decision"]),
        "- Future execution request created: "
        + str(admission["future_execution_request_created"]).lower(),
        "- Runner consume request admitted: "
        + str(admission["runner_consume_request_admitted"]).lower(),
        "- Runner execution allowed: false",
        "- Execute allowed: false",
        "- Next iteration executed: false",
        "- Next iteration output dir created: false",
        "- Candidate input path checked: false",
        "- Candidate input path listed: false",
        "- Candidate input file read: false",
        "- Candidate input file hashing performed: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: "
        + str(len(_list_or_empty(admission["missing_required_artifacts"]))),
        "- Untrusted count: "
        + str(len(_list_or_empty(admission["untrusted_artifacts"]))),
        "- Blocker count: "
        + str(len(_list_or_empty(admission["runner_admission_blockers"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- No runtime stage executed.",
        "- No runner executed.",
        "- No next bounded smoke iteration executed.",
        "- No next iteration output directory created.",
        "- No execution request generation executed.",
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
        "- Runner admission artifact only.",
    ]
    return "\n".join(lines) + "\n"


def _checklist_markdown(admission: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Runner Admission Checklist",
        "",
    ]
    for item in _checklist_items():
        lines.append("- [ ] " + item)
    lines.extend(
        [
            "",
            "Runner admission status: " + str(admission["admission_status"]),
            "Runner admission decision: " + str(admission["admission_decision"]),
            "Next allowed action: " + str(admission["next_allowed_action"]),
        ]
    )
    return "\n".join(lines) + "\n"


def _checklist_items() -> list[str]:
    return [
        "verify execution request artifact exists and is trusted",
        "verify execution request status is ready",
        "verify execution request decision created a future request only",
        "verify execution request next action awaits separate runner",
        "verify future execution request was created",
        "verify runner acknowledgement phrase was valid",
        "verify plaintext runner acknowledgement phrase was not persisted",
        "verify admitted runner id/version are present",
        "verify admitted limits are valid",
        "verify admitted limits do not exceed requested limits",
        "verify runner consume request is admitted only when request is ready",
        "verify runner execution allowed is false",
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


def _admission_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    admission: dict[str, object],
) -> dict[str, object]:
    admission_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE
    ]
    summary_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE
    ]
    checklist_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE
    ]
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "admission_path": admission_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "checklist_path": checklist_path.as_posix(),
        "admission_sha256": sha256_file(admission_path),
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
        "admission_status": admission["admission_status"],
        "admission_decision": admission["admission_decision"],
        "next_allowed_action": admission["next_allowed_action"],
        "runner_consume_request_admitted": admission[
            "runner_consume_request_admitted"
        ],
        "runner_operator_acknowledgement_phrase_persisted": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_RUNNER_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_entry(output_dir, role, paths[file_name])
        for role, file_name in _ADMISSION_ARTIFACTS
    ]
    payload = {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_next_bounded_smoke_iteration_runner_admission_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "execution_request_output_recursively_indexed": False,
        "next_admission_output_recursively_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_RUNNER_FALSE_FLAGS)
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
        "execution_request_output_recursively_indexed": False,
        "next_admission_output_recursively_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_RUNNER_FALSE_FLAGS)
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


def _launcher_payload_from_admission(
    admission: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_next_bounded_smoke_iteration_runner_admission_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_MANIFEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_SUMMARY_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUNNER_ADMISSION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "execution_request_output_dir": admission["execution_request_output_dir"],
        "output_dir": admission["output_dir"],
        "project_id": admission["project_id"],
        "runner_admission_id": admission["runner_admission_id"],
        "runner_operator_id": admission["runner_operator_id"],
        "admitted_runner_id": admission["admitted_runner_id"],
        "admitted_runner_version": admission["admitted_runner_version"],
        "runner_environment_label": admission["runner_environment_label"],
        "requested_next_iteration_id": admission["requested_next_iteration_id"],
        "requested_candidate_input_dir": admission["requested_candidate_input_dir"],
        "requested_next_iteration_output_dir": admission[
            "requested_next_iteration_output_dir"
        ],
        "requested_limits": admission["requested_limits"],
        "admitted_limits": admission["admitted_limits"],
        "admission_status": admission["admission_status"],
        "admission_decision": admission["admission_decision"],
        "next_allowed_action": admission["next_allowed_action"],
        "runner_consume_request_admitted": admission[
            "runner_consume_request_admitted"
        ],
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_RUNNER_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    *,
    runner_inputs: dict[str, object],
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult:
    status = "blocked_unknown"
    decision = "reject_and_repair_artifacts"
    payload = {
        "complete": False,
        "artifacts_written": False,
        "admission_type": _ADMISSION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": runner_inputs["project_id"],
        "runner_admission_id": runner_inputs["runner_admission_id"],
        "runner_operator_id": runner_inputs["runner_operator_id"],
        "runner_operator_acknowledgement_phrase_sha256": runner_inputs[
            "runner_operator_acknowledgement_phrase_sha256"
        ],
        "runner_operator_acknowledgement_phrase_persisted": False,
        "admitted_runner_id": runner_inputs["admitted_runner_id"],
        "admitted_runner_version": runner_inputs["admitted_runner_version"],
        "runner_environment_label": runner_inputs["runner_environment_label"],
        "operator_notes_present": runner_inputs["operator_notes_present"],
        "operator_notes": runner_inputs["operator_notes"],
        "execution_request_output_dir": roots[
            "execution_request_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "admitted_limits": {
            "admitted_max_files": runner_inputs["admitted_max_files"],
            "admitted_max_total_bytes": runner_inputs[
                "admitted_max_total_bytes"
            ],
            "admitted_max_depth": runner_inputs["admitted_max_depth"],
        },
        "admission_status": status,
        "admission_decision": decision,
        "next_allowed_action": "repair_artifacts",
        "runner_consume_request_admitted": False,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": error_message,
        "local_asset_next_bounded_smoke_iteration_runner_admission_path": None,
        "local_asset_next_bounded_smoke_iteration_runner_admission_manifest_path": None,
        "local_asset_next_bounded_smoke_iteration_runner_admission_summary_path": None,
        "local_asset_next_bounded_smoke_iteration_runner_admission_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_RUNNER_FALSE_FLAGS)
    payload.update(_BOUNDARY_FLAGS)
    return LocalAssetNextBoundedSmokeIterationRunnerAdmissionResult(
        execution_request_output_dir=roots["execution_request_output_dir"],
        output_dir=roots["output_dir"],
        admission_path=None,
        manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        admission_status=status,
        admission_decision=decision,
        payload=payload,
    )


def _requested_limits_from_request(request: dict[str, object]) -> dict[str, object]:
    requested_limits = _dict_or_empty(request.get("requested_limits"))
    return {
        "requested_max_files": requested_limits.get("requested_max_files"),
        "requested_max_total_bytes": requested_limits.get(
            "requested_max_total_bytes"
        ),
        "requested_max_depth": requested_limits.get("requested_max_depth"),
    }


def _malformed(field: str, reason: str, **extra: object) -> dict[str, object]:
    payload = {"field": field, "reason": reason}
    payload.update(extra)
    return payload


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
