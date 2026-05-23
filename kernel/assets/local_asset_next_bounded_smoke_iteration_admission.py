"""Prepare-only admission for the next bounded local asset smoke iteration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE",
    "LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE",
    "LocalAssetNextBoundedSmokeIterationAdmissionResult",
    "build_local_asset_next_bounded_smoke_iteration_admission",
]


LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE = (
    "local_asset_next_bounded_smoke_iteration_admission.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_admission_manifest.json"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE = (
    "local_asset_next_bounded_smoke_iteration_admission_summary.md"
)
LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE = (
    "local_asset_next_bounded_smoke_iteration_admission_checklist.md"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_ADMISSION_TYPE = "local_asset_next_bounded_smoke_iteration_admission_v1"
_MANIFEST_TYPE = "local_asset_next_bounded_smoke_iteration_admission_manifest_v1"
_INDEX_TYPE = "local_asset_next_bounded_smoke_iteration_admission_artifact_index_v1"
_INDEX_MANIFEST_TYPE = (
    "local_asset_next_bounded_smoke_iteration_admission_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_admission_record"
_EXECUTION_CAPABILITY = "local_asset_next_bounded_smoke_iteration_admission_only"

_READY_STATUS = "next_bounded_smoke_iteration_admission_ready"
_READY_DECISION = "admit_prepare_next_bounded_smoke_iteration"
_READY_NEXT_ACTION = "create_next_bounded_smoke_iteration_execution_request"

_APPROVED_HUMAN_REVIEW_STATUS = "human_review_approved_next_bounded_smoke_iteration"
_APPROVED_HUMAN_REVIEW_DECISION = "allow_prepare_next_bounded_smoke_iteration"
_APPROVED_HUMAN_DECISION = (
    "approve_cycle_contract_for_next_bounded_smoke_iteration"
)
_EXPECTED_CYCLE_HUMAN_REVIEW_NEXT_ACTION = (
    "prepare_next_bounded_smoke_iteration_admission"
)

_ALLOWED_CYCLE_CONTRACT_STATUSES = (
    "cycle_contract_ready",
    "cycle_contract_ready_with_warnings",
)
_ALLOWED_CYCLE_CONTRACT_DECISIONS = (
    "bind_completed_bounded_smoke_cycle",
    "bind_completed_cycle_with_human_warnings",
)

_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
    "candidate_file_mutation",
    "duplicate_deletion",
    "media_organizer_behavior",
)
_REQUIRED_CYCLE_HUMAN_REVIEW_DISALLOWED_ACTIONS = (
    "execute_next_bounded_smoke_iteration",
    "production_scan",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
)

_OUTPUT_FILES = (
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE,
    LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_ADMISSION_ARTIFACTS = (
    (
        "local_asset_next_bounded_smoke_iteration_admission",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_manifest",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_summary",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE,
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_checklist",
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE,
    ),
)

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_admission": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
    "cycle_human_review_run_performed": False,
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
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
    "production_scan_approved": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_SOURCE_BOUNDARY_FALSE_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_review",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
    "cycle_contract_run_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
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
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "production_scan_recommended",
    "automatic_approval_performed",
    "autonomous_execution_performed",
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
        "local_asset_bounded_smoke_cycle_human_review_decision",
        "local_asset_bounded_smoke_cycle_human_review_decision.json",
        True,
        True,
        "decision_type",
        "local_asset_bounded_smoke_cycle_human_review_decision_v1",
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_cycle_human_review_manifest",
        "local_asset_bounded_smoke_cycle_human_review_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_cycle_human_review_manifest_v1",
    ),
    _SourceArtifactSpec(
        "cycle_human_review_artifact_index",
        "artifact_index.json",
        True,
        True,
        "index_type",
        "local_asset_bounded_smoke_cycle_human_review_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "cycle_human_review_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_cycle_human_review_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_cycle_human_review_summary",
        "local_asset_bounded_smoke_cycle_human_review_summary.md",
        False,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_cycle_human_review_checklist",
        "local_asset_bounded_smoke_cycle_human_review_checklist.md",
        False,
        False,
    ),
)


@dataclass(frozen=True)
class LocalAssetNextBoundedSmokeIterationAdmissionResult:
    cycle_human_review_output_dir: Path
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


def build_local_asset_next_bounded_smoke_iteration_admission(
    cycle_human_review_output_dir: Path,
    output_dir: Path,
    *,
    project_id: str | None = None,
    requested_next_iteration_id: str | None = None,
    operator_notes: str | None = None,
) -> LocalAssetNextBoundedSmokeIterationAdmissionResult:
    """Admit creation of a future next-iteration execution request only."""

    roots = {
        "cycle_human_review_output_dir": Path(cycle_human_review_output_dir),
        "output_dir": Path(output_dir),
    }
    paths = _output_paths(roots["output_dir"])
    output_error = _output_preflight_error(roots, paths)
    if output_error is not None:
        return _structured_failure_result(
            roots,
            project_id=project_id,
            requested_next_iteration_id=requested_next_iteration_id,
            operator_notes=operator_notes,
            failure_stage=output_error["failure_stage"],
            error_message=output_error["error_message"],
        )

    cycle_root_error = _cycle_human_review_root_error(
        roots["cycle_human_review_output_dir"]
    )
    source_artifacts = _source_artifact_records(
        roots["cycle_human_review_output_dir"],
        cycle_root_error=cycle_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_trust_failures(source_artifacts, source_payloads)

    admission = _admission_payload(
        roots=roots,
        project_id=project_id,
        requested_next_iteration_id=requested_next_iteration_id,
        operator_notes=operator_notes,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
        cycle_root_error=cycle_root_error,
    )
    summary = _summary_markdown(admission)
    checklist = _checklist_markdown(admission)

    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE],
        admission,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE],
        checklist,
    )
    manifest = _admission_manifest_payload(paths, source_artifacts, admission)
    _write_json_exclusive(
        paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE],
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
    return LocalAssetNextBoundedSmokeIterationAdmissionResult(
        cycle_human_review_output_dir=roots["cycle_human_review_output_dir"],
        output_dir=roots["output_dir"],
        admission_path=paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE],
        manifest_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE
        ],
        summary_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE
        ],
        checklist_path=paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        admission_status=str(admission["admission_status"]),
        admission_decision=str(admission["admission_decision"]),
        payload=payload,
    )


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
        roots["cycle_human_review_output_dir"],
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
                "local asset next bounded smoke iteration admission output "
                "already exists: "
                + collision
            ),
        }
    return None


def _cycle_human_review_root_error(path: Path) -> str | None:
    return _real_existing_dir_error(path, "cycle_human_review_output_dir")


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
    cycle_human_review_output_dir: Path,
    output_dir: Path,
) -> str | None:
    try:
        cycle_root = cycle_human_review_output_dir.resolve(strict=False)
        output_root = output_dir.resolve(strict=False)
    except OSError:
        return None
    if cycle_root == output_root:
        return "output_dir must not equal cycle_human_review_output_dir"
    if _path_is_inside(output_root, cycle_root):
        return "output_dir must not be inside cycle_human_review_output_dir"
    if _path_is_inside(cycle_root, output_root):
        return "cycle_human_review_output_dir must not be inside output_dir"
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
    cycle_human_review_output_dir: Path,
    *,
    cycle_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    root_safe = cycle_root_error is None
    for spec in _SOURCE_ARTIFACTS:
        path = cycle_human_review_output_dir / spec.relative_path
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
        if cycle_root_error is not None and spec.required:
            record["root_error"] = cycle_root_error
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
            manifest_role="local_asset_bounded_smoke_cycle_human_review_manifest",
            field_roles=(
                (
                    "decision_sha256",
                    "local_asset_bounded_smoke_cycle_human_review_decision",
                ),
                (
                    "summary_sha256",
                    "local_asset_bounded_smoke_cycle_human_review_summary",
                ),
                (
                    "human_review_checklist_sha256",
                    "local_asset_bounded_smoke_cycle_human_review_checklist",
                ),
            ),
        )
    )
    mismatches.extend(
        _manifest_file_hash_mismatches(
            records_by_role,
            source_payloads,
            manifest_role="cycle_human_review_artifact_index_manifest",
            field_roles=(("artifact_index_sha256", "cycle_human_review_artifact_index"),),
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
        expected = manifest.get(field_name)
        if expected is not None and expected != record.get("sha256"):
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
    project_id: str | None,
    requested_next_iteration_id: str | None,
    operator_notes: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
    cycle_root_error: str | None,
) -> dict[str, object]:
    review = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_cycle_human_review_decision",
    )
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    malformed = _human_review_malformed(review)
    boundary_violations = _human_review_boundary_violations(review)

    status, decision, next_action, prepare_admitted = _admission_outcome(
        missing_required=missing_required,
        untrusted=untrusted,
        malformed=malformed,
        review=review,
        boundary_violations=boundary_violations,
    )
    project = _first_text(project_id, review.get("project_id"))
    blockers = _admission_blockers(
        status=status,
        missing_required=missing_required,
        untrusted=untrusted,
        malformed=malformed,
        boundary_violations=boundary_violations,
        cycle_root_error=cycle_root_error,
        review=review,
    )
    return {
        "admission_type": _ADMISSION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project,
        "requested_next_iteration_id": requested_next_iteration_id,
        "operator_notes_present": operator_notes is not None,
        "operator_notes": operator_notes,
        "cycle_human_review_output_dir": roots[
            "cycle_human_review_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "human_review_status": review.get("human_review_status"),
        "human_review_decision": review.get("human_review_decision"),
        "human_decision": review.get("human_decision"),
        "human_review_id": review.get("human_review_id"),
        "human_reviewer_id": review.get("human_reviewer_id"),
        "human_signoff_phrase_persisted": review.get(
            "human_signoff_phrase_persisted"
        ),
        "next_bounded_smoke_iteration_prepare_allowed": review.get(
            "next_bounded_smoke_iteration_prepare_allowed"
        ),
        "cycle_human_review_next_bounded_smoke_iteration_execute_allowed": (
            review.get("next_bounded_smoke_iteration_execute_allowed")
        ),
        "cycle_human_review_next_allowed_action": review.get("next_allowed_action"),
        "cycle_human_review_disallowed_actions": _list_or_empty(
            review.get("disallowed_actions")
        ),
        "cycle_contract_status": review.get("cycle_contract_status"),
        "cycle_contract_decision": review.get("cycle_contract_decision"),
        "admission_status": status,
        "admission_decision": decision,
        "next_allowed_action": next_action,
        "next_bounded_smoke_iteration_prepare_admitted": prepare_admitted,
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "production_scan_approved": False,
        "production_promotion_granted": False,
        "automatic_approval_performed": False,
        "autonomous_execution_performed": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        "source_artifacts": source_artifacts,
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "admission_blockers": blockers,
        "admission_checklist": {"items": _checklist_items()},
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        **dict(_BOUNDARY_FLAGS),
    }


def _admission_outcome(
    *,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    malformed: list[dict[str, object]],
    review: dict[str, object],
    boundary_violations: list[dict[str, object]],
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
            "blocked_invalid_human_review_record",
            "reject_and_repair_human_review",
            "repair_human_review",
            False,
        )
    if review.get("human_review_status") != _APPROVED_HUMAN_REVIEW_STATUS:
        return (
            "blocked_human_review_not_approved",
            "reject_and_repair_human_review",
            "repair_human_review",
            False,
        )
    if review.get("next_bounded_smoke_iteration_prepare_allowed") is not True:
        return (
            "blocked_prepare_not_allowed",
            "reject_and_repair_human_review",
            "repair_human_review",
            False,
        )
    if review.get("next_bounded_smoke_iteration_execute_allowed") is True:
        return (
            "blocked_execution_already_allowed",
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
    return (
        _READY_STATUS,
        _READY_DECISION,
        _READY_NEXT_ACTION,
        True,
    )


def _human_review_malformed(review: dict[str, object]) -> list[dict[str, object]]:
    if not review:
        return []
    malformed = []
    required_text_fields = (
        "human_review_status",
        "human_review_decision",
        "human_decision",
        "human_review_id",
        "human_reviewer_id",
        "next_allowed_action",
        "cycle_contract_status",
        "cycle_contract_decision",
    )
    for field_name in required_text_fields:
        if not isinstance(review.get(field_name), str) or not review[field_name]:
            malformed.append(
                _malformed(
                    field_name,
                    "human review field is missing or not text",
                )
            )
    for field_name in (
        "human_signoff_phrase_persisted",
        "next_bounded_smoke_iteration_prepare_allowed",
        "next_bounded_smoke_iteration_execute_allowed",
    ):
        if not isinstance(review.get(field_name), bool):
            malformed.append(
                _malformed(
                    field_name,
                    "human review field is missing or not boolean",
                )
            )
    disallowed_actions = review.get("disallowed_actions")
    if not isinstance(disallowed_actions, list) or not all(
        isinstance(item, str) for item in disallowed_actions
    ):
        malformed.append(
            _malformed("disallowed_actions", "disallowed actions are malformed")
        )
    else:
        missing_actions = [
            action
            for action in _REQUIRED_CYCLE_HUMAN_REVIEW_DISALLOWED_ACTIONS
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
    if review.get("human_signoff_phrase_persisted") is not False:
        malformed.append(
            _malformed(
                "human_signoff_phrase_persisted",
                "plaintext signoff phrase must not be persisted",
            )
        )
    if review.get("human_review_status") == _APPROVED_HUMAN_REVIEW_STATUS:
        if review.get("human_review_decision") != _APPROVED_HUMAN_REVIEW_DECISION:
            malformed.append(
                _malformed(
                    "human_review_decision",
                    "approved human review status must allow prepare only",
                )
            )
        if review.get("human_decision") != _APPROVED_HUMAN_DECISION:
            malformed.append(
                _malformed(
                    "human_decision",
                    "approved human review status must bind the approve decision",
                )
            )
        if (
            review.get("next_allowed_action")
            != _EXPECTED_CYCLE_HUMAN_REVIEW_NEXT_ACTION
        ):
            malformed.append(
                _malformed(
                    "next_allowed_action",
                    "approved human review must point to admission preparation",
                )
            )
        if review.get("cycle_contract_status") not in _ALLOWED_CYCLE_CONTRACT_STATUSES:
            malformed.append(
                _malformed(
                    "cycle_contract_status",
                    "approved human review must reference a ready cycle contract",
                )
            )
        if review.get("cycle_contract_decision") not in _ALLOWED_CYCLE_CONTRACT_DECISIONS:
            malformed.append(
                _malformed(
                    "cycle_contract_decision",
                    "approved human review must reference a bind-only cycle contract",
                )
            )
    elif review.get("human_review_decision") == _APPROVED_HUMAN_REVIEW_DECISION:
        malformed.append(
            _malformed(
                "human_review_status",
                "allow-prepare decision must have approved human review status",
            )
        )
    return sorted(malformed, key=lambda item: str(item["field"]))


def _malformed(field: str, reason: str, **extra: object) -> dict[str, object]:
    payload = {"field": field, "reason": reason}
    payload.update(extra)
    return payload


def _human_review_boundary_violations(
    review: dict[str, object],
) -> list[dict[str, object]]:
    if not review:
        return []
    violations = []
    for field_name in _SOURCE_BOUNDARY_FALSE_FIELDS:
        if review.get(field_name) is True:
            violations.append(
                {
                    "field": field_name,
                    "reason": "cycle human review boundary flag must be false",
                }
            )
    return sorted(violations, key=lambda item: str(item["field"]))


def _admission_blockers(
    *,
    status: str,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    malformed: list[dict[str, object]],
    boundary_violations: list[dict[str, object]],
    cycle_root_error: str | None,
    review: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if cycle_root_error is not None:
        blockers.append(
            _blocker("cycle_human_review_output_dir_invalid", cycle_root_error)
        )
    if missing_required:
        blockers.append(
            _blocker(
                "missing_required_artifacts",
                "required generated cycle human review artifacts are missing",
                artifacts=[item["artifact_role"] for item in missing_required],
            )
        )
    if untrusted:
        blockers.append(
            _blocker(
                "untrusted_artifacts",
                "generated cycle human review artifacts are untrusted, malformed, or hash mismatched",
                artifacts=[item["artifact_role"] for item in untrusted],
            )
        )
    if malformed:
        blockers.append(
            _blocker(
                "invalid_human_review_record",
                "cycle human review decision record is malformed or internally inconsistent",
                violations=malformed,
            )
        )
    if status == "blocked_human_review_not_approved":
        blockers.append(
            _blocker(
                "human_review_not_approved",
                "cycle human review did not approve next bounded smoke iteration preparation",
                human_review_status=review.get("human_review_status"),
                human_review_decision=review.get("human_review_decision"),
            )
        )
    if status == "blocked_prepare_not_allowed":
        blockers.append(
            _blocker(
                "prepare_not_allowed",
                "cycle human review did not permit prepare-only next iteration admission",
            )
        )
    if status == "blocked_execution_already_allowed":
        blockers.append(
            _blocker(
                "execution_already_allowed",
                "cycle human review unexpectedly granted next iteration execution permission",
            )
        )
    if boundary_violations:
        blockers.append(
            _blocker(
                "production_or_mutation_boundary_violation",
                "cycle human review claims or permits disallowed production or mutation authority",
                violations=boundary_violations,
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
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Admission",
        "",
        "- Admission status: " + str(admission["admission_status"]),
        "- Admission decision: " + str(admission["admission_decision"]),
        "- Next allowed action: " + str(admission["next_allowed_action"]),
        "- Requested next iteration id: "
        + str(admission["requested_next_iteration_id"]),
        "- Human review id: " + str(admission["human_review_id"]),
        "- Human reviewer id: " + str(admission["human_reviewer_id"]),
        "- Human review status: " + str(admission["human_review_status"]),
        "- Human review decision: " + str(admission["human_review_decision"]),
        "- Cycle contract status: " + str(admission["cycle_contract_status"]),
        "- Cycle contract decision: " + str(admission["cycle_contract_decision"]),
        "- Prepare admitted: "
        + str(admission["next_bounded_smoke_iteration_prepare_admitted"]).lower(),
        "- Execute allowed: false",
        "- Next iteration output dir created: false",
        "- Production scan approved: false",
        "- Production promotion granted: false",
        "- Missing required count: "
        + str(len(_list_or_empty(admission["missing_required_artifacts"]))),
        "- Untrusted count: "
        + str(len(_list_or_empty(admission["untrusted_artifacts"]))),
        "- Blocker count: "
        + str(len(_list_or_empty(admission["admission_blockers"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- No runtime stage executed.",
        "- No next bounded smoke iteration executed.",
        "- No next iteration output directory created.",
        "- No cycle human review generation executed.",
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
        "- Admission record only.",
    ]
    return "\n".join(lines) + "\n"


def _checklist_markdown(admission: dict[str, object]) -> str:
    lines = [
        "# Local Asset Next Bounded Smoke Iteration Admission Checklist",
        "",
    ]
    for item in _checklist_items():
        lines.append("- [ ] " + item)
    lines.extend(
        [
            "",
            "Admission status: " + str(admission["admission_status"]),
            "Admission decision: " + str(admission["admission_decision"]),
            "Next allowed action: " + str(admission["next_allowed_action"]),
        ]
    )
    return "\n".join(lines) + "\n"


def _checklist_items() -> list[str]:
    return [
        "verify human review decision artifact exists and is trusted",
        "verify human review status approved next bounded smoke iteration",
        "verify human review decision allows prepare only",
        "verify human supplied approve decision",
        "verify signoff phrase was not persisted",
        "verify prepare allowed is true",
        "verify execute allowed is false",
        "verify next action is create_next_bounded_smoke_iteration_execution_request",
        "verify production scan is not approved",
        "verify production promotion is not granted",
        "verify no runtime stage was executed",
        "verify no next iteration output directory was created",
        "verify no input/upstream mutation occurred",
        "verify no raw private content included",
        "verify no candidate hashing occurred",
    ]


def _admission_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    admission: dict[str, object],
) -> dict[str, object]:
    admission_path = paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE]
    summary_path = paths[LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE]
    checklist_path = paths[
        LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE
    ]
    return {
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
        "next_bounded_smoke_iteration_prepare_admitted": admission[
            "next_bounded_smoke_iteration_prepare_admitted"
        ],
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }


def _artifact_index_payload(
    output_dir: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _artifact_entry(output_dir, role, paths[file_name])
        for role, file_name in _ADMISSION_ARTIFACTS
    ]
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_next_bounded_smoke_iteration_admission_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }


def _artifact_index_manifest_payload(
    output_dir: Path,
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
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "job_dir": output_dir.as_posix(),
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "cycle_human_review_output_recursively_indexed": False,
        "cycle_contract_output_recursively_indexed": False,
        "upstream_artifacts_recursively_indexed": False,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }


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
        "local_asset_next_bounded_smoke_iteration_admission_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_admission_manifest_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_MANIFEST_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_admission_summary_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_SUMMARY_FILE
        ].as_posix(),
        "local_asset_next_bounded_smoke_iteration_admission_checklist_path": paths[
            LOCAL_ASSET_NEXT_BOUNDED_SMOKE_ITERATION_ADMISSION_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "cycle_human_review_output_dir": admission["cycle_human_review_output_dir"],
        "output_dir": admission["output_dir"],
        "project_id": admission["project_id"],
        "requested_next_iteration_id": admission["requested_next_iteration_id"],
        "admission_status": admission["admission_status"],
        "admission_decision": admission["admission_decision"],
        "next_allowed_action": admission["next_allowed_action"],
        "next_bounded_smoke_iteration_prepare_admitted": admission[
            "next_bounded_smoke_iteration_prepare_admitted"
        ],
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    *,
    project_id: str | None,
    requested_next_iteration_id: str | None,
    operator_notes: str | None,
    failure_stage: str,
    error_message: str,
) -> LocalAssetNextBoundedSmokeIterationAdmissionResult:
    status = "blocked_unknown"
    decision = "reject_and_repair_artifacts"
    payload = {
        "complete": False,
        "artifacts_written": False,
        "admission_type": _ADMISSION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project_id,
        "requested_next_iteration_id": requested_next_iteration_id,
        "operator_notes_present": operator_notes is not None,
        "operator_notes": operator_notes,
        "cycle_human_review_output_dir": roots[
            "cycle_human_review_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "admission_status": status,
        "admission_decision": decision,
        "next_allowed_action": "repair_artifacts",
        "next_bounded_smoke_iteration_prepare_admitted": False,
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_bounded_smoke_iteration_executed": False,
        "next_iteration_output_dir_created": False,
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": error_message,
        "local_asset_next_bounded_smoke_iteration_admission_path": None,
        "local_asset_next_bounded_smoke_iteration_admission_manifest_path": None,
        "local_asset_next_bounded_smoke_iteration_admission_summary_path": None,
        "local_asset_next_bounded_smoke_iteration_admission_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "required_human_approval": True,
        "required_human_review": True,
        **dict(_BOUNDARY_FLAGS),
    }
    return LocalAssetNextBoundedSmokeIterationAdmissionResult(
        cycle_human_review_output_dir=roots["cycle_human_review_output_dir"],
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
