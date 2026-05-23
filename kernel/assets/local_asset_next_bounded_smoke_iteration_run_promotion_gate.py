"""Promotion gate for reviewed next bounded smoke iteration runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE",
    "LocalAssetNextBoundedSmokeIterationRunPromotionGateResult",
    "build_local_asset_next_bounded_smoke_iteration_run_promotion_gate",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_GATE_TYPE = "local_asset_next_bounded_smoke_iteration_run_promotion_gate_v1"
_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_v1"
)
_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_artifact_index_v1"
)
_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_bounded_run_promotion_gate_record"
_EXECUTION_CAPABILITY = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_only"
)

_REVIEW_PACKET_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet.json"
)
_REVIEW_PACKET_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest.json"
)
_REVIEW_PACKET_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_summary.md"
)
_REVIEW_PACKET_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist.md"
)

_REVIEW_PACKET_TYPE = "local_asset_next_bounded_smoke_iteration_run_review_packet_v1"
_REVIEW_PACKET_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest_v1"
)
_REVIEW_PACKET_INDEX_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_v1"
)
_REVIEW_PACKET_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_manifest_v1"
)

_READY_REVIEW_STATUS = "next_bounded_smoke_iteration_run_review_packet_ready"
_READY_REVIEW_DECISION = (
    "package_next_bounded_smoke_iteration_run_for_promotion_gate_review"
)
_READY_REVIEW_NEXT_ACTION = (
    "run_next_bounded_smoke_iteration_run_promotion_gate"
)

_READY_GATE_STATUS = "next_bounded_smoke_iteration_run_promotion_gate_ready"
_READY_GATE_DECISION = "approve_next_bounded_smoke_iteration_run_for_cycle_contract"
_READY_NEXT_ACTION = "create_next_bounded_smoke_cycle_contract_from_run"

_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_SOURCE_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet",
        _REVIEW_PACKET_FILE,
        True,
        "review_packet_type",
        _REVIEW_PACKET_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest",
        _REVIEW_PACKET_MANIFEST_FILE,
        True,
        "manifest_type",
        _REVIEW_PACKET_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        "index_type",
        _REVIEW_PACKET_INDEX_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        "manifest_type",
        _REVIEW_PACKET_INDEX_MANIFEST_TYPE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary",
        _REVIEW_PACKET_SUMMARY_FILE,
        False,
        None,
        None,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist",
        _REVIEW_PACKET_CHECKLIST_FILE,
        False,
        None,
        None,
    ),
)

_GATE_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE,
    ),
)

_REQUIRED_FALSE_SOURCE_FIELDS = (
    "promotion_approved",
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "runner_reexecution_performed",
    "candidate_input_path_checked_by_review",
    "candidate_input_path_listed_by_review",
    "candidate_input_file_read_by_review",
    "candidate_input_file_hashing_performed_by_review",
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
)

_REQUIRED_TRUE_SOURCE_FIELDS = (
    "review_packet_created",
    "required_human_approval",
    "required_human_review",
)

_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "rerun_runner",
    "generate_cycle_contract",
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
    "bounded_smoke_iteration_performed_by_gate": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "next_admission_run_performed": False,
    "execution_request_run_performed": False,
    "runner_admission_run_performed": False,
    "runner_execution_run_performed_by_gate": False,
    "run_review_packet_run_performed_by_gate": False,
    "raw_candidate_content_read_by_gate": False,
    "candidate_file_hashing_performed_by_gate": False,
    "candidate_path_validation_performed_by_gate": False,
    "candidate_path_listing_performed_by_gate": False,
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

_GATE_ACCESS_FALSE_FLAGS = {
    "candidate_input_path_checked_by_gate": False,
    "candidate_input_path_listed_by_gate": False,
    "candidate_input_file_read_by_gate": False,
    "candidate_input_file_hashing_performed_by_gate": False,
}

_FORBIDDEN_CONTENT_FIELDS = {
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
class LocalAssetNextBoundedSmokeIterationRunPromotionGateResult:
    run_review_packet_output_dir: Path
    output_dir: Path
    promotion_gate_path: Path | None
    promotion_gate_manifest_path: Path | None
    promotion_gate_summary_path: Path | None
    promotion_gate_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    gate_status: str
    gate_decision: str
    payload: dict[str, object]


def build_local_asset_next_bounded_smoke_iteration_run_promotion_gate(
    run_review_packet_output_dir: Path,
    output_dir: Path,
    *,
    promotion_gate_id: str,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationRunPromotionGateResult:
    """Build a non-executing promotion gate from generated review artifacts."""

    roots = {
        "run_review_packet_output_dir": Path(run_review_packet_output_dir),
        "output_dir": Path(output_dir),
    }
    inputs = {
        "promotion_gate_id": promotion_gate_id,
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
            error_message="promotion gate output artifact already exists: "
            + collision,
        )

    overlap_error = _overlap_preflight_error(roots)
    if overlap_error is not None:
        return _structured_failure_result(
            roots,
            inputs,
            failure_stage="preflight_source_output_overlap",
            error_message=overlap_error,
        )

    source_root_error = _real_existing_dir_error(
        roots["run_review_packet_output_dir"],
        "run_review_packet_output_dir",
    )
    source_artifacts = _source_artifact_records(
        roots["run_review_packet_output_dir"],
        source_root_error=source_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_source_trust(source_artifacts, source_payloads)

    gate = _promotion_gate_payload(
        roots=roots,
        inputs=inputs,
        source_root_error=source_root_error,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(gate)
    checklist = _checklist_markdown()

    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE],
        gate,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE
        ],
        checklist,
    )
    manifest = _manifest_payload(paths, gate, source_artifacts)
    _write_json_exclusive(
        paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE
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

    complete = gate["gate_status"] == _READY_GATE_STATUS
    payload = _launcher_payload_from_gate(gate, paths, complete=complete)
    return LocalAssetNextBoundedSmokeIterationRunPromotionGateResult(
        run_review_packet_output_dir=roots["run_review_packet_output_dir"],
        output_dir=roots["output_dir"],
        promotion_gate_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE
        ],
        promotion_gate_manifest_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE
        ],
        promotion_gate_summary_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE
        ],
        promotion_gate_checklist_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        gate_status=str(gate["gate_status"]),
        gate_decision=str(gate["gate_decision"]),
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
    source = roots["run_review_packet_output_dir"]
    output = roots["output_dir"]
    if not _overlap_checkable(source, output):
        return None
    if _same_path_text(source, output):
        return "output_dir must not equal run_review_packet_output_dir"
    if _path_is_inside(output, source):
        return "output_dir must not be inside run_review_packet_output_dir"
    if _path_is_inside(source, output):
        return "run_review_packet_output_dir must not be inside output_dir"
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
    source_root: Path,
    *,
    source_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for role, relative_path, required, expected_field, expected_value in _SOURCE_ARTIFACTS:
        path = source_root / relative_path
        if source_root_error is not None:
            records.append(
                {
                    "role": role,
                    "artifact_role": role,
                    "relative_path": relative_path,
                    "path": path.as_posix(),
                    "exists": False,
                    "required": required,
                    "json_artifact": expected_field is not None,
                    "expected_field": expected_field,
                    "expected_value": expected_value,
                    "sha256": None,
                    "size_bytes": None,
                    "trusted_generated_artifact": False,
                    "trust_failures": [
                        _blocker("source_dir_unsafe", source_root_error)
                    ],
                    "content_indexed": False,
                    "raw_content_copied": False,
                }
            )
            continue
        exists = path.exists() or path.is_symlink()
        is_symlink = path.is_symlink()
        is_file = exists and path.is_file() and not is_symlink
        trust_failures = []
        if exists and is_symlink:
            trust_failures.append(
                _blocker("source_artifact_symlink", "source artifact is a symlink")
            )
        elif exists and not is_file:
            trust_failures.append(
                _blocker("source_artifact_not_file", "source artifact is not a file")
            )
        records.append(
            {
                "role": role,
                "artifact_role": role,
                "relative_path": relative_path,
                "path": path.as_posix(),
                "exists": exists,
                "required": required,
                "json_artifact": expected_field is not None,
                "expected_field": expected_field,
                "expected_value": expected_value,
                "sha256": sha256_file(path) if is_file else None,
                "size_bytes": path.stat().st_size if is_file else None,
                "trusted_generated_artifact": False,
                "trust_failures": trust_failures,
                "content_indexed": False,
                "raw_content_copied": False,
            }
        )
    return sorted(records, key=lambda record: str(record["role"]))


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
            payload = json.loads(
                Path(str(artifact["path"])).read_text(encoding="utf-8")
            )
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

    review_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_run_review_packet_manifest",
    )
    index_manifest = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index_manifest",
    )
    _mark_manifest_hash(
        records,
        review_manifest,
        "review_packet_sha256",
        "local_asset_next_bounded_smoke_iteration_run_review_packet",
    )
    _mark_manifest_hash(
        records,
        review_manifest,
        "summary_sha256",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_summary",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        review_manifest,
        "checklist_sha256",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_checklist",
        optional=True,
    )
    _mark_manifest_hash(
        records,
        index_manifest,
        "artifact_index_sha256",
        "local_asset_next_bounded_smoke_iteration_run_review_packet_artifact_index",
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


def _promotion_gate_payload(
    *,
    roots: dict[str, Path],
    inputs: dict[str, object],
    source_root_error: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    review_packet = _dict_payload(
        source_payloads,
        "local_asset_next_bounded_smoke_iteration_run_review_packet",
    )
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    metadata_blockers = _invalid_promotion_gate_metadata(inputs)
    invalid_safety, boundary_violations = _source_safety_blockers(review_packet)
    invalid_record = _review_packet_record_blockers(review_packet)
    reviewed_run_fact_blockers = _reviewed_run_fact_blockers(review_packet)
    source_blockers = _source_review_packet_blockers(review_packet)
    gate_status = _gate_status(
        metadata_blockers=metadata_blockers,
        missing_required=missing_required,
        untrusted=untrusted,
        invalid_safety=invalid_safety,
        invalid_record=invalid_record,
        boundary_violations=boundary_violations,
        reviewed_run_fact_blockers=reviewed_run_fact_blockers,
        source_blockers=source_blockers,
        review_packet=review_packet,
        source_root_error=source_root_error,
    )
    gate_decision, next_allowed_action = _decision_and_next_action(gate_status)
    bounded_run_promotion_approved = gate_status == _READY_GATE_STATUS
    gate_blockers = _gate_blockers_for_status(
        gate_status=gate_status,
        metadata_blockers=metadata_blockers,
        missing_required=missing_required,
        untrusted=untrusted,
        invalid_safety=invalid_safety,
        invalid_record=invalid_record,
        boundary_violations=boundary_violations,
        reviewed_run_fact_blockers=reviewed_run_fact_blockers,
        source_blockers=source_blockers,
    )
    project_id = _first_text(inputs.get("project_id"), review_packet.get("project_id"))
    gate = {
        "gate_type": _GATE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project_id,
        "promotion_gate_id": inputs.get("promotion_gate_id"),
        "reviewer_id": inputs.get("reviewer_id"),
        "operator_notes_present": inputs["operator_notes_present"],
        "operator_notes": inputs.get("operator_notes")
        if inputs["operator_notes_present"] is True
        else None,
        "run_review_packet_output_dir": roots[
            "run_review_packet_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "review_packet_id": review_packet.get("review_packet_id"),
        "runner_execution_id": review_packet.get("runner_execution_id"),
        "runner_operator_id": review_packet.get("runner_operator_id"),
        "runner_admission_id": review_packet.get("runner_admission_id"),
        "admitted_runner_id": review_packet.get("admitted_runner_id"),
        "admitted_runner_version": review_packet.get("admitted_runner_version"),
        "requested_next_iteration_id": review_packet.get(
            "requested_next_iteration_id"
        ),
        "requested_candidate_input_dir": review_packet.get(
            "requested_candidate_input_dir"
        ),
        "requested_next_iteration_output_dir": review_packet.get(
            "requested_next_iteration_output_dir"
        ),
        "actual_next_iteration_output_dir": review_packet.get(
            "actual_next_iteration_output_dir"
        ),
        "requested_limits": _dict_or_empty(review_packet.get("requested_limits")),
        "admitted_limits": _dict_or_empty(review_packet.get("admitted_limits")),
        "candidate_file_count": review_packet.get("candidate_file_count"),
        "candidate_total_bytes": review_packet.get("candidate_total_bytes"),
        "candidate_max_depth_observed": review_packet.get(
            "candidate_max_depth_observed"
        ),
        "candidate_limit_enforced": review_packet.get("candidate_limit_enforced"),
        "candidate_symlinks_detected": _list_or_empty(
            review_packet.get("candidate_symlinks_detected")
        ),
        "bounded_file_records": _list_or_empty(
            review_packet.get("bounded_file_records")
        ),
        "review_status": review_packet.get("review_status"),
        "review_decision": review_packet.get("review_decision"),
        "review_next_allowed_action": review_packet.get("next_allowed_action"),
        "review_packet_created": review_packet.get(
            "review_packet_created",
            False,
        ),
        "source_promotion_approved": review_packet.get("promotion_approved", False),
        "source_production_scan_approved": review_packet.get(
            "production_scan_approved",
            False,
        ),
        "source_production_promotion_granted": review_packet.get(
            "production_promotion_granted",
            False,
        ),
        "source_automatic_approval_performed": review_packet.get(
            "automatic_approval_performed",
            False,
        ),
        "source_autonomous_execution_performed": review_packet.get(
            "autonomous_execution_performed",
            False,
        ),
        "source_runner_reexecution_performed": review_packet.get(
            "runner_reexecution_performed",
            False,
        ),
        "source_candidate_input_path_checked_by_review": review_packet.get(
            "candidate_input_path_checked_by_review",
            False,
        ),
        "source_candidate_input_path_listed_by_review": review_packet.get(
            "candidate_input_path_listed_by_review",
            False,
        ),
        "source_candidate_input_file_read_by_review": review_packet.get(
            "candidate_input_file_read_by_review",
            False,
        ),
        "source_candidate_input_file_hashing_performed_by_review": review_packet.get(
            "candidate_input_file_hashing_performed_by_review",
            False,
        ),
        "gate_status": gate_status,
        "gate_decision": gate_decision,
        "next_allowed_action": next_allowed_action,
        "bounded_run_promotion_approved": bounded_run_promotion_approved,
        "cycle_contract_generation_allowed": bounded_run_promotion_approved,
        "cycle_contract_generated": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "gate_blockers": gate_blockers,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
    }
    gate.update(_GATE_ACCESS_FALSE_FLAGS)
    gate.update(_BOUNDARY_FALSE_FLAGS)
    return gate


def _invalid_promotion_gate_metadata(
    inputs: dict[str, object],
) -> list[dict[str, object]]:
    invalid = []
    promotion_gate_id = inputs.get("promotion_gate_id")
    if not isinstance(promotion_gate_id, str) or not promotion_gate_id:
        invalid.append(
            _blocker(
                "invalid_promotion_gate_metadata",
                "promotion_gate_id must be non-empty text",
                field="promotion_gate_id",
            )
        )
    project_id = inputs.get("project_id")
    if project_id is not None and (not isinstance(project_id, str) or not project_id):
        invalid.append(
            _blocker(
                "invalid_promotion_gate_metadata",
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
                "invalid_promotion_gate_metadata",
                "reviewer_id must be absent or non-empty text",
                field="reviewer_id",
            )
        )
    operator_notes = inputs.get("operator_notes")
    if operator_notes is not None and not isinstance(operator_notes, str):
        invalid.append(
            _blocker(
                "invalid_promotion_gate_metadata",
                "operator_notes must be text when present",
                field="operator_notes",
            )
        )
    return sorted(invalid, key=lambda item: str(item.get("field")))


def _source_safety_blockers(
    review_packet: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    invalid = []
    boundary = []
    for field_name in _REQUIRED_FALSE_SOURCE_FIELDS:
        if field_name not in review_packet:
            invalid.append(
                _blocker(
                    "source_safety_field_missing",
                    "source review packet required false field is missing",
                    field=field_name,
                )
            )
            continue
        value = review_packet[field_name]
        if not isinstance(value, bool):
            invalid.append(
                _blocker(
                    "source_safety_field_not_boolean",
                    "source review packet required false field is not boolean",
                    field=field_name,
                    actual_value=value,
                )
            )
            continue
        if value is not False:
            boundary.append(
                _blocker(
                    "source_boundary_flag_true",
                    "source review packet boundary flag is true",
                    field=field_name,
                )
            )
    for field_name in _REQUIRED_TRUE_SOURCE_FIELDS:
        if field_name not in review_packet:
            invalid.append(
                _blocker(
                    "source_safety_field_missing",
                    "source review packet required true field is missing",
                    field=field_name,
                )
            )
            continue
        value = review_packet[field_name]
        if not isinstance(value, bool):
            invalid.append(
                _blocker(
                    "source_safety_field_not_boolean",
                    "source review packet required true field is not boolean",
                    field=field_name,
                    actual_value=value,
                )
            )
            continue
        if value is not True:
            boundary.append(
                _blocker(
                    "source_boundary_required_flag_false",
                    "source review packet required true boundary flag is false",
                    field=field_name,
                )
            )
    invalid.sort(key=lambda item: str(item.get("field")))
    boundary.sort(key=lambda item: str(item.get("field")))
    return invalid, boundary


def _review_packet_record_blockers(
    review_packet: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if review_packet.get("review_packet_type") != _REVIEW_PACKET_TYPE:
        blockers.append(
            _blocker(
                "review_packet_type_mismatch",
                "source review packet type is invalid",
            )
        )
    if review_packet.get("review_status") == _READY_REVIEW_STATUS:
        if review_packet.get("review_decision") != _READY_REVIEW_DECISION:
            blockers.append(
                _blocker(
                    "ready_review_packet_decision_invalid",
                    "ready source review packet has an invalid decision",
                    field="review_decision",
                )
            )
        if review_packet.get("next_allowed_action") != _READY_REVIEW_NEXT_ACTION:
            blockers.append(
                _blocker(
                    "ready_review_packet_next_action_invalid",
                    "ready source review packet has an invalid next action",
                    field="next_allowed_action",
                )
            )
    if "cross_artifact_checks" in review_packet and not isinstance(
        review_packet.get("cross_artifact_checks"),
        list,
    ):
        blockers.append(
            _blocker(
                "cross_artifact_checks_malformed",
                "source review packet cross_artifact_checks must be a list",
            )
        )
    for field_name in (
        "review_blockers",
        "missing_required_artifacts",
        "untrusted_artifacts",
    ):
        if field_name in review_packet and not isinstance(
            review_packet.get(field_name),
            list,
        ):
            blockers.append(
                _blocker(
                    "review_packet_list_field_malformed",
                    "source review packet list field is malformed",
                    field=field_name,
                )
            )
    return sorted(blockers, key=lambda item: str(item.get("reason")))


def _reviewed_run_fact_blockers(
    review_packet: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if review_packet.get("runner_execution_performed") is not True:
        blockers.append(
            _blocker(
                "runner_execution_not_performed",
                "reviewed runner execution was not performed",
                field="runner_execution_performed",
            )
        )
    if review_packet.get("next_bounded_smoke_iteration_executed") is not True:
        blockers.append(
            _blocker(
                "next_iteration_not_executed",
                "reviewed next bounded smoke iteration was not executed",
                field="next_bounded_smoke_iteration_executed",
            )
        )
    if review_packet.get("candidate_limit_enforced") is not True:
        blockers.append(
            _blocker(
                "candidate_limit_not_enforced",
                "reviewed run did not enforce candidate limits",
                field="candidate_limit_enforced",
            )
        )
    symlinks = review_packet.get("candidate_symlinks_detected")
    if not isinstance(symlinks, list) or symlinks:
        blockers.append(
            _blocker(
                "candidate_symlinks_detected",
                "reviewed candidate symlink list must be empty",
                field="candidate_symlinks_detected",
            )
        )
    for field_name in (
        "candidate_file_count",
        "candidate_total_bytes",
        "candidate_max_depth_observed",
    ):
        value = review_packet.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            blockers.append(
                _blocker(
                    "reviewed_run_integer_fact_invalid",
                    "reviewed run integer fact must be a non-negative integer",
                    field=field_name,
                    actual_value=value,
                )
            )
    records = review_packet.get("bounded_file_records")
    if not isinstance(records, list):
        blockers.append(
            _blocker(
                "bounded_file_records_malformed",
                "bounded_file_records must be a list",
                field="bounded_file_records",
            )
        )
    else:
        if records != sorted(records, key=lambda record: str(record.get("relative_path"))):
            blockers.append(
                _blocker(
                    "bounded_file_records_not_deterministic",
                    "bounded_file_records must be sorted by relative_path",
                    field="bounded_file_records",
                )
            )
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                blockers.append(
                    _blocker(
                        "bounded_file_record_malformed",
                        "bounded file record must be an object",
                        record_index=index,
                    )
                )
                continue
            if _record_has_forbidden_content_fields(record):
                blockers.append(
                    _blocker(
                        "bounded_file_record_contains_raw_content_field",
                        "bounded file records must not contain raw content fields",
                        record_index=index,
                    )
                )
    return sorted(blockers, key=lambda item: str(item.get("field", item["reason"])))


def _source_review_packet_blockers(
    review_packet: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    cross_checks = review_packet.get("cross_artifact_checks")
    if not isinstance(cross_checks, list):
        blockers.append(
            _blocker(
                "cross_artifact_checks_missing_or_malformed",
                "source review packet cross_artifact_checks must exist as a list",
            )
        )
    else:
        for index, check in enumerate(cross_checks):
            if not isinstance(check, dict) or check.get("passed") is not True:
                blockers.append(
                    _blocker(
                        "cross_artifact_check_failed",
                        "source review packet cross-artifact check failed",
                        check_index=index,
                    )
                )
    for field_name in (
        "review_blockers",
        "missing_required_artifacts",
        "untrusted_artifacts",
    ):
        values = _list_or_empty(review_packet.get(field_name))
        if values:
            blockers.append(
                _blocker(
                    "source_review_packet_contains_" + field_name,
                    "source review packet contains blocking review fields",
                    field=field_name,
                    count=len(values),
                )
            )
    if review_packet.get("deterministic_ordering") is not True:
        blockers.append(
            _blocker(
                "source_review_packet_not_deterministic",
                "source review packet deterministic_ordering must be true",
                field="deterministic_ordering",
            )
        )
    return sorted(blockers, key=lambda item: str(item.get("field", item["reason"])))


def _gate_status(
    *,
    metadata_blockers: list[dict[str, object]],
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    invalid_safety: list[dict[str, object]],
    invalid_record: list[dict[str, object]],
    boundary_violations: list[dict[str, object]],
    reviewed_run_fact_blockers: list[dict[str, object]],
    source_blockers: list[dict[str, object]],
    review_packet: dict[str, object],
    source_root_error: str | None,
) -> str:
    if metadata_blockers:
        return "blocked_invalid_promotion_gate_metadata"
    if missing_required:
        return "blocked_missing_required_artifacts"
    if untrusted:
        return "blocked_untrusted_artifacts"
    if invalid_safety or invalid_record:
        return "blocked_invalid_review_packet_record"
    if boundary_violations:
        return "blocked_source_boundary_violation"
    if reviewed_run_fact_blockers:
        return "blocked_invalid_reviewed_run_facts"
    if source_blockers:
        return "blocked_review_packet_contains_blockers"
    if source_root_error is not None:
        return "blocked_missing_required_artifacts"
    if (
        review_packet.get("review_status") != _READY_REVIEW_STATUS
        or review_packet.get("review_decision") != _READY_REVIEW_DECISION
        or review_packet.get("next_allowed_action") != _READY_REVIEW_NEXT_ACTION
    ):
        return "blocked_review_packet_not_ready"
    return _READY_GATE_STATUS


def _gate_blockers_for_status(
    *,
    gate_status: str,
    metadata_blockers: list[dict[str, object]],
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    invalid_safety: list[dict[str, object]],
    invalid_record: list[dict[str, object]],
    boundary_violations: list[dict[str, object]],
    reviewed_run_fact_blockers: list[dict[str, object]],
    source_blockers: list[dict[str, object]],
) -> list[dict[str, object]]:
    if gate_status == "blocked_invalid_promotion_gate_metadata":
        return metadata_blockers
    if gate_status == "blocked_missing_required_artifacts":
        return missing_required
    if gate_status == "blocked_untrusted_artifacts":
        return untrusted
    if gate_status == "blocked_invalid_review_packet_record":
        return invalid_safety + invalid_record
    if gate_status == "blocked_source_boundary_violation":
        return boundary_violations
    if gate_status == "blocked_invalid_reviewed_run_facts":
        return reviewed_run_fact_blockers
    if gate_status == "blocked_review_packet_contains_blockers":
        return source_blockers
    if gate_status == "blocked_review_packet_not_ready":
        return [
            _blocker(
                "review_packet_not_ready",
                "source review packet is not ready for run promotion gate",
            )
        ]
    return []


def _decision_and_next_action(status: str) -> tuple[str, str]:
    if status == _READY_GATE_STATUS:
        return (_READY_GATE_DECISION, _READY_NEXT_ACTION)
    if status in ("blocked_missing_required_artifacts", "blocked_untrusted_artifacts"):
        return ("reject_and_repair_artifacts", "repair_artifacts")
    if status == "blocked_source_boundary_violation":
        return ("reject_boundary_violation", "reject_boundary_violation")
    if status == "blocked_invalid_promotion_gate_metadata":
        return ("reject_and_repair_promotion_gate", "repair_promotion_gate")
    if status in (
        "blocked_review_packet_not_ready",
        "blocked_invalid_review_packet_record",
        "blocked_invalid_reviewed_run_facts",
        "blocked_review_packet_contains_blockers",
    ):
        return ("reject_and_repair_review_packet", "repair_review_packet")
    return ("reject_and_repair_artifacts", "repair_artifacts")


def _missing_required_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
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


def _untrusted_artifacts(
    source_artifacts: list[dict[str, object]],
) -> list[dict[str, object]]:
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
    gate: dict[str, object],
    source_artifacts: list[dict[str, object]],
) -> dict[str, object]:
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "gate_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE
        ].as_posix(),
        "summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE
        ].as_posix(),
        "checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "gate_sha256": sha256_file(
            paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE]
        ),
        "summary_sha256": sha256_file(
            paths[
                LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE
            ]
        ),
        "checklist_sha256": sha256_file(
            paths[
                LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE
            ]
        ),
        "source_artifacts": [
            _public_source_artifact_ref(artifact) for artifact in source_artifacts
        ],
        "gate_status": gate["gate_status"],
        "gate_decision": gate["gate_decision"],
        "next_allowed_action": gate["next_allowed_action"],
        "bounded_run_promotion_approved": gate["bounded_run_promotion_approved"],
        "cycle_contract_generation_allowed": gate[
            "cycle_contract_generation_allowed"
        ],
        "cycle_contract_generated": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_GATE_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_index_entry(output_dir, role, paths[file_name])
        for role, file_name in _GATE_ARTIFACTS
    ]
    payload = {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_promotion_gate_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "run_review_packet_output_dir_recursively_indexed": False,
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
        "run_review_packet_output_dir_recursively_indexed": False,
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


def _summary_markdown(gate: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Run Promotion Gate",
        "",
        "- Gate status: " + str(gate["gate_status"]),
        "- Gate decision: " + str(gate["gate_decision"]),
        "- Next allowed action: " + str(gate["next_allowed_action"]),
        "- Promotion gate id: " + str(gate["promotion_gate_id"]),
        "- Reviewer id: " + str(gate["reviewer_id"]),
        "- Review packet id: " + str(gate["review_packet_id"]),
        "- Runner execution id: " + str(gate["runner_execution_id"]),
        "- Runner operator id: " + str(gate["runner_operator_id"]),
        "- Runner admission id: " + str(gate["runner_admission_id"]),
        "- Requested next iteration id: " + str(gate["requested_next_iteration_id"]),
        "- Requested candidate input dir: `"
        + str(gate["requested_candidate_input_dir"])
        + "`",
        "- Requested next iteration output dir: `"
        + str(gate["requested_next_iteration_output_dir"])
        + "`",
        "- Actual next iteration output dir: `"
        + str(gate["actual_next_iteration_output_dir"])
        + "`",
        "- Requested limits: " + json.dumps(gate["requested_limits"], sort_keys=True),
        "- Admitted limits: " + json.dumps(gate["admitted_limits"], sort_keys=True),
        "- Candidate file count: " + str(gate["candidate_file_count"]),
        "- Candidate total bytes: " + str(gate["candidate_total_bytes"]),
        "- Max depth observed: " + str(gate["candidate_max_depth_observed"]),
        "- Candidate limit enforced: " + _bool_text(gate["candidate_limit_enforced"]),
        "- Candidate symlink count: "
        + str(len(_list_or_empty(gate["candidate_symlinks_detected"]))),
        "- Bounded run promotion approved: "
        + _bool_text(gate["bounded_run_promotion_approved"]),
        "- Cycle contract generation allowed: "
        + _bool_text(gate["cycle_contract_generation_allowed"]),
        "- Cycle contract generated: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: "
        + str(len(_list_or_empty(gate["missing_required_artifacts"]))),
        "- Untrusted count: " + str(len(_list_or_empty(gate["untrusted_artifacts"]))),
        "- Blocker count: " + str(len(_list_or_empty(gate["gate_blockers"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- bounded run promotion gate only",
        "- no runner re-execution",
        "- no review packet re-generation",
        "- no candidate path validation by gate",
        "- no candidate path listing by gate",
        "- no candidate file read by gate",
        "- no candidate file hash by gate",
        "- no cycle contract generated",
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
        "verify review packet artifact exists and is trusted",
        "verify review packet status is ready",
        "verify review packet next action routes to promotion gate",
        "verify review packet contains no blockers",
        "verify cross-artifact checks all passed",
        "verify source boundary booleans are present and type-correct",
        "verify bounded run completed under admitted limits",
        "verify candidate manifest was already metadata-only",
        "verify candidate symlink list is empty",
        "verify candidate limits were enforced",
        "verify bounded run promotion is bounded-only",
        "verify cycle contract generation is allowed but not executed",
        "verify no runner re-execution occurred",
        "verify no review packet re-generation occurred",
        "verify no candidate access occurred during gate",
        "verify no production scan is approved",
        "verify no production promotion is granted",
        "verify no file move/rename/delete occurred",
        "verify no duplicate deletion occurred",
        "verify no media organizer behavior occurred",
        "verify no raw private content copied",
        "verify no network/model/external runtime was used",
        "verify production gate is separate",
    ]
    return "# Run Promotion Gate Checklist\n\n" + "\n".join(
        "- [ ] " + item for item in items
    ) + "\n"


def _launcher_payload_from_gate(
    gate: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_MANIFEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_SUMMARY_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_run_promotion_gate_checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_RUN_PROMOTION_GATE_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "run_review_packet_output_dir": gate["run_review_packet_output_dir"],
        "output_dir": gate["output_dir"],
        "project_id": gate["project_id"],
        "promotion_gate_id": gate["promotion_gate_id"],
        "reviewer_id": gate["reviewer_id"],
        "review_packet_id": gate["review_packet_id"],
        "runner_execution_id": gate["runner_execution_id"],
        "runner_operator_id": gate["runner_operator_id"],
        "runner_admission_id": gate["runner_admission_id"],
        "requested_next_iteration_id": gate["requested_next_iteration_id"],
        "requested_candidate_input_dir": gate["requested_candidate_input_dir"],
        "requested_next_iteration_output_dir": gate[
            "requested_next_iteration_output_dir"
        ],
        "actual_next_iteration_output_dir": gate["actual_next_iteration_output_dir"],
        "requested_limits": gate["requested_limits"],
        "admitted_limits": gate["admitted_limits"],
        "gate_status": gate["gate_status"],
        "gate_decision": gate["gate_decision"],
        "next_allowed_action": gate["next_allowed_action"],
        "bounded_run_promotion_approved": gate[
            "bounded_run_promotion_approved"
        ],
        "cycle_contract_generation_allowed": gate[
            "cycle_contract_generation_allowed"
        ],
        "cycle_contract_generated": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_GATE_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    inputs: dict[str, object],
    *,
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationRunPromotionGateResult:
    gate_status = "blocked_unknown"
    gate_decision, next_action = _decision_and_next_action(gate_status)
    payload = {
        "complete": False,
        "artifacts_written": False,
        "run_review_packet_output_dir": roots[
            "run_review_packet_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "project_id": inputs.get("project_id"),
        "promotion_gate_id": inputs.get("promotion_gate_id"),
        "reviewer_id": inputs.get("reviewer_id"),
        "gate_status": gate_status,
        "gate_decision": gate_decision,
        "next_allowed_action": next_action,
        "bounded_run_promotion_approved": False,
        "cycle_contract_generation_allowed": False,
        "cycle_contract_generated": False,
        "promotion_approved": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "runner_reexecution_performed": False,
        "failure_stage": failure_stage,
        "error_message": error_message,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_GATE_ACCESS_FALSE_FLAGS)
    payload.update(_BOUNDARY_FALSE_FLAGS)
    return LocalAssetNextBoundedSmokeIterationRunPromotionGateResult(
        run_review_packet_output_dir=roots["run_review_packet_output_dir"],
        output_dir=roots["output_dir"],
        promotion_gate_path=None,
        promotion_gate_manifest_path=None,
        promotion_gate_summary_path=None,
        promotion_gate_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        gate_status=gate_status,
        gate_decision=gate_decision,
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


def _dict_or_empty(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _list_or_empty(value: object) -> list:
    return list(value) if isinstance(value, list) else []


def _record_has_forbidden_content_fields(record: object) -> bool:
    if not isinstance(record, dict):
        return True
    return any(key in _FORBIDDEN_CONTENT_FIELDS for key in record)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _blocker(reason: str, message: str, **extra: object) -> dict[str, object]:
    payload = {"reason": reason, "message": message}
    payload.update(extra)
    return payload
