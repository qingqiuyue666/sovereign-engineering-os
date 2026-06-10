"""Human review decision record for bounded local asset smoke cycle contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE",
    "LocalAssetBoundedSmokeCycleHumanReviewResult",
    "build_local_asset_bounded_smoke_cycle_human_review",
]


LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE = (
    "local_asset_bounded_smoke_cycle_human_review_decision.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE = (
    "local_asset_bounded_smoke_cycle_human_review_manifest.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE = (
    "local_asset_bounded_smoke_cycle_human_review_summary.md"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE = (
    "local_asset_bounded_smoke_cycle_human_review_checklist.md"
)
LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE = (
    "I_REVIEWED_LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_CONTRACT"
)

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_DECISION_TYPE = "local_asset_bounded_smoke_cycle_human_review_decision_v1"
_MANIFEST_TYPE = "local_asset_bounded_smoke_cycle_human_review_manifest_v1"
_INDEX_TYPE = "local_asset_bounded_smoke_cycle_human_review_artifact_index_v1"
_INDEX_MANIFEST_TYPE = (
    "local_asset_bounded_smoke_cycle_human_review_artifact_index_manifest_v1"
)
_AUTHORITY = "human_review_record"
_EXECUTION_CAPABILITY = "local_asset_bounded_smoke_cycle_human_review_only"

_VALID_HUMAN_DECISIONS = (
    "approve_cycle_contract_for_next_bounded_smoke_iteration",
    "stop_cycle",
    "repair_artifacts",
    "repair_cycle",
    "inspect_quarantine",
    "inspect_duplicates",
    "inspect_incremental_changes",
    "reject_boundary_violation",
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

_REVIEW_DECISION_OPTIONS = _VALID_HUMAN_DECISIONS

_OUTPUT_FILES = (
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE,
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_REVIEW_ARTIFACTS = (
    (
        "local_asset_bounded_smoke_cycle_human_review_decision",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_manifest",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_summary",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE,
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_checklist",
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE,
    ),
)

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "smoke_review_packet_run_performed": False,
    "smoke_promotion_gate_run_performed": False,
    "bounded_smoke_iteration_performed_by_review": False,
    "iteration_review_packet_run_performed": False,
    "iteration_promotion_gate_run_performed": False,
    "cycle_contract_run_performed": False,
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
    "production_promotion_granted": False,
    "production_scan_approved": False,
    "production_scan_performed": False,
    "production_scan_recommended": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_CYCLE_BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_contract",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
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
        "local_asset_bounded_smoke_cycle_contract",
        "local_asset_bounded_smoke_cycle_contract.json",
        True,
        True,
        "contract_type",
        "local_asset_bounded_smoke_cycle_contract_v1",
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_cycle_contract_manifest",
        "local_asset_bounded_smoke_cycle_contract_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_cycle_contract_manifest_v1",
    ),
    _SourceArtifactSpec(
        "cycle_contract_artifact_index",
        "artifact_index.json",
        True,
        True,
        "index_type",
        "local_asset_bounded_smoke_cycle_contract_artifact_index_v1",
    ),
    _SourceArtifactSpec(
        "cycle_contract_artifact_index_manifest",
        "artifact_index_manifest.json",
        True,
        True,
        "manifest_type",
        "local_asset_bounded_smoke_cycle_contract_artifact_index_manifest_v1",
    ),
    _SourceArtifactSpec(
        "local_asset_bounded_smoke_cycle_summary",
        "local_asset_bounded_smoke_cycle_summary.md",
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
class LocalAssetBoundedSmokeCycleHumanReviewResult:
    cycle_contract_output_dir: Path
    output_dir: Path
    decision_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    human_review_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    human_review_status: str
    human_review_decision: str
    payload: dict[str, object]


def build_local_asset_bounded_smoke_cycle_human_review(
    cycle_contract_output_dir: Path,
    output_dir: Path,
    human_review_id: str,
    human_reviewer_id: str,
    human_decision: str,
    human_signoff_phrase: str,
    *,
    project_id: str | None = None,
    human_review_notes: str | None = None,
) -> LocalAssetBoundedSmokeCycleHumanReviewResult:
    """Record a human review decision over an existing cycle contract output."""

    roots = {
        "cycle_contract_output_dir": Path(cycle_contract_output_dir),
        "output_dir": Path(output_dir),
    }
    paths = _output_paths(roots["output_dir"])
    output_error = _output_preflight_error(roots, paths)
    if output_error is not None:
        return _structured_failure_result(
            roots,
            project_id=project_id,
            human_review_id=human_review_id,
            human_reviewer_id=human_reviewer_id,
            human_decision=human_decision,
            failure_stage=output_error["failure_stage"],
            error_message=output_error["error_message"],
        )

    identity_error = _human_identity_error(human_review_id, human_reviewer_id)
    if identity_error is not None:
        return _structured_failure_result(
            roots,
            project_id=project_id,
            human_review_id=human_review_id,
            human_reviewer_id=human_reviewer_id,
            human_decision=human_decision,
            failure_stage="preflight_human_review_identity",
            error_message=identity_error,
        )

    cycle_root_error = _cycle_contract_root_error(roots["cycle_contract_output_dir"])
    source_artifacts = _source_artifact_records(
        roots["cycle_contract_output_dir"],
        cycle_root_error=cycle_root_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)
    _mark_trust_failures(source_artifacts, source_payloads)

    decision = _decision_payload(
        roots=roots,
        project_id=project_id,
        human_review_id=human_review_id,
        human_reviewer_id=human_reviewer_id,
        human_decision=human_decision,
        human_signoff_phrase=human_signoff_phrase,
        human_review_notes=human_review_notes,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
        cycle_root_error=cycle_root_error,
    )
    summary = _summary_markdown(decision)
    checklist = _human_review_checklist_markdown(decision)

    _write_json_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE],
        decision,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE],
        checklist,
    )
    manifest = _review_manifest_payload(paths, source_artifacts, decision)
    _write_json_exclusive(
        paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE],
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

    complete = not str(decision["human_review_status"]).startswith("blocked_")
    payload = _launcher_payload_from_decision(decision, paths, complete=complete)
    return LocalAssetBoundedSmokeCycleHumanReviewResult(
        cycle_contract_output_dir=roots["cycle_contract_output_dir"],
        output_dir=roots["output_dir"],
        decision_path=paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE],
        manifest_path=paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE],
        summary_path=paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE],
        human_review_checklist_path=paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        human_review_status=str(decision["human_review_status"]),
        human_review_decision=str(decision["human_review_decision"]),
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
    collision = _existing_output_collision(paths)
    if collision is not None:
        return {
            "failure_stage": "preflight_output_collision",
            "error_message": (
                "local asset bounded smoke cycle human review output already exists: "
                + collision
            ),
        }
    overlap_error = _root_overlap_error(
        roots["cycle_contract_output_dir"],
        roots["output_dir"],
    )
    if overlap_error is not None:
        return {
            "failure_stage": "preflight_root_overlap",
            "error_message": overlap_error,
        }
    return None


def _cycle_contract_root_error(path: Path) -> str | None:
    return _real_existing_dir_error(path, "cycle_contract_output_dir")


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


def _root_overlap_error(cycle_contract_output_dir: Path, output_dir: Path) -> str | None:
    try:
        cycle_root = cycle_contract_output_dir.resolve(strict=True)
        output_root = output_dir.resolve(strict=True)
    except OSError:
        return None
    if cycle_root == output_root:
        return "output_dir must not equal cycle_contract_output_dir"
    if _path_is_inside(output_root, cycle_root):
        return "output_dir must not be inside cycle_contract_output_dir"
    if _path_is_inside(cycle_root, output_root):
        return "cycle_contract_output_dir must not be inside output_dir"
    return None


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _human_identity_error(human_review_id: str, human_reviewer_id: str) -> str | None:
    if not isinstance(human_review_id, str) or not human_review_id:
        return "human_review_id is required"
    if not isinstance(human_reviewer_id, str) or not human_reviewer_id:
        return "human_reviewer_id is required"
    return None


def _source_artifact_records(
    cycle_contract_output_dir: Path,
    *,
    cycle_root_error: str | None,
) -> list[dict[str, object]]:
    records = []
    root_safe = cycle_root_error is None
    for spec in _SOURCE_ARTIFACTS:
        path = cycle_contract_output_dir / spec.relative_path
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
            manifest_role="local_asset_bounded_smoke_cycle_contract_manifest",
            field_roles=(
                ("contract_sha256", "local_asset_bounded_smoke_cycle_contract"),
                ("summary_sha256", "local_asset_bounded_smoke_cycle_summary"),
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
            manifest_role="cycle_contract_artifact_index_manifest",
            field_roles=(("artifact_index_sha256", "cycle_contract_artifact_index"),),
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


def _decision_payload(
    *,
    roots: dict[str, Path],
    project_id: str | None,
    human_review_id: str,
    human_reviewer_id: str,
    human_decision: str,
    human_signoff_phrase: str,
    human_review_notes: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
    cycle_root_error: str | None,
) -> dict[str, object]:
    contract = _dict_payload(
        source_payloads,
        "local_asset_bounded_smoke_cycle_contract",
    )
    missing_required = _missing_required_artifacts(source_artifacts)
    untrusted = _untrusted_artifacts(source_artifacts)
    invalid_decision = human_decision not in _VALID_HUMAN_DECISIONS
    signoff_valid = human_signoff_phrase == (
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE
    )
    boundary_violations = _cycle_contract_boundary_violations(contract)

    status, review_decision, next_action, prepare_allowed = _human_review_outcome(
        human_decision=human_decision,
        invalid_decision=invalid_decision,
        signoff_valid=signoff_valid,
        missing_required=missing_required,
        untrusted=untrusted,
        contract=contract,
        boundary_violations=boundary_violations,
    )
    project = _first_text(project_id, contract.get("project_id"))
    blockers = _human_review_blockers(
        status=status,
        missing_required=missing_required,
        untrusted=untrusted,
        boundary_violations=boundary_violations,
        contract=contract,
        cycle_root_error=cycle_root_error,
    )
    return {
        "decision_type": _DECISION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project,
        "cycle_contract_output_dir": roots[
            "cycle_contract_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "human_review_id": human_review_id,
        "human_reviewer_id": human_reviewer_id,
        "human_decision": human_decision,
        "human_signoff_phrase_sha256": _sha256_text(human_signoff_phrase),
        "human_signoff_phrase_persisted": False,
        "human_review_notes_present": human_review_notes is not None,
        "human_review_notes": human_review_notes,
        "cycle_contract_status": contract.get("cycle_contract_status"),
        "cycle_contract_decision": contract.get("cycle_contract_decision"),
        "cycle_contract_next_allowed_action": contract.get("next_allowed_action"),
        "cycle_contract_allowed_after_human_review": _list_or_empty(
            contract.get("allowed_after_human_review")
        ),
        "cycle_contract_disallowed_actions": _list_or_empty(
            contract.get("disallowed_actions")
        ),
        "cycle_contract_blocker_count": len(
            _list_or_empty(contract.get("cycle_blockers"))
        ),
        "cycle_contract_blockers": _list_or_empty(contract.get("cycle_blockers")),
        "source_artifacts": source_artifacts,
        "missing_required_artifacts": missing_required,
        "untrusted_artifacts": untrusted,
        "human_review_status": status,
        "human_review_decision": review_decision,
        "next_bounded_smoke_iteration_prepare_allowed": prepare_allowed,
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_allowed_action": next_action,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "human_review_blockers": blockers,
        "human_review_checklist": {
            "items": _checklist_items(),
            "decision_options": list(_REVIEW_DECISION_OPTIONS),
        },
        "deterministic_ordering": True,
        "required_human_approval": True,
        "required_human_review": True,
        **dict(_BOUNDARY_FLAGS),
    }


def _human_review_outcome(
    *,
    human_decision: str,
    invalid_decision: bool,
    signoff_valid: bool,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    contract: dict[str, object],
    boundary_violations: list[dict[str, object]],
) -> tuple[str, str, str, bool]:
    if invalid_decision:
        return (
            "blocked_invalid_human_decision",
            "reject_and_repair_human_review",
            "repair_human_review",
            False,
        )
    if not signoff_valid:
        return (
            "blocked_invalid_human_signoff",
            "reject_and_repair_human_review",
            "repair_human_review",
            False,
        )
    if missing_required:
        return (
            "blocked_missing_required_artifacts",
            "repair_artifacts",
            "repair_artifacts",
            False,
        )
    if untrusted:
        return (
            "blocked_untrusted_artifacts",
            "repair_artifacts",
            "repair_artifacts",
            False,
        )
    if boundary_violations:
        return (
            "blocked_cycle_contract_boundary_violation",
            "reject_boundary_violation",
            "reject_boundary_violation",
            False,
        )
    if human_decision == "approve_cycle_contract_for_next_bounded_smoke_iteration":
        if _cycle_contract_ready_for_human_approval(contract):
            return (
                "human_review_approved_next_bounded_smoke_iteration",
                "allow_prepare_next_bounded_smoke_iteration",
                "prepare_next_bounded_smoke_iteration_admission",
                True,
            )
        return (
            "blocked_cycle_contract_not_ready",
            "repair_cycle",
            "repair_cycle",
            False,
        )
    return _non_approval_outcome(human_decision)


def _non_approval_outcome(human_decision: str) -> tuple[str, str, str, bool]:
    mapping = {
        "stop_cycle": (
            "human_review_stopped_cycle",
            "stop_cycle",
            "stop_cycle",
        ),
        "repair_artifacts": (
            "human_review_requires_artifact_repair",
            "repair_artifacts",
            "repair_artifacts",
        ),
        "repair_cycle": (
            "human_review_requires_cycle_repair",
            "repair_cycle",
            "repair_cycle",
        ),
        "inspect_quarantine": (
            "human_review_requires_quarantine_inspection",
            "inspect_quarantine",
            "inspect_quarantine",
        ),
        "inspect_duplicates": (
            "human_review_requires_duplicate_inspection",
            "inspect_duplicates",
            "inspect_duplicates",
        ),
        "inspect_incremental_changes": (
            "human_review_requires_incremental_inspection",
            "inspect_incremental_changes",
            "inspect_incremental_changes",
        ),
        "reject_boundary_violation": (
            "human_review_rejected_boundary_violation",
            "reject_boundary_violation",
            "reject_boundary_violation",
        ),
    }
    status, decision, next_action = mapping[human_decision]
    return status, decision, next_action, False


def _cycle_contract_ready_for_human_approval(contract: dict[str, object]) -> bool:
    status = contract.get("cycle_contract_status")
    decision = contract.get("cycle_contract_decision")
    if status == "cycle_contract_ready":
        status_ready = decision == "bind_completed_bounded_smoke_cycle"
    elif status == "cycle_contract_ready_with_warnings":
        status_ready = (
            decision == "bind_completed_cycle_with_human_warnings"
            and _only_non_blocking_contract_warnings(contract)
        )
    else:
        status_ready = False
    if not status_ready:
        return False
    return (
        contract.get("next_allowed_action")
        == "human_review_bounded_smoke_cycle_contract"
        and "production_scan" in _string_list(contract.get("disallowed_actions"))
        and "production_promotion" in _string_list(contract.get("disallowed_actions"))
        and contract.get("required_human_review") is True
        and not _list_or_empty(contract.get("cycle_blockers"))
        and not _list_or_empty(contract.get("missing_required_artifacts"))
        and not _list_or_empty(contract.get("untrusted_artifacts"))
    )


def _only_non_blocking_contract_warnings(contract: dict[str, object]) -> bool:
    blockers = _list_or_empty(contract.get("cycle_blockers"))
    if not blockers:
        return True
    for blocker in blockers:
        if not isinstance(blocker, dict):
            return False
        if blocker.get("blocking") is False:
            continue
        role = str(blocker.get("blocker_role", blocker.get("role", "")))
        if role not in ("informational_warning", "non_blocking_warning"):
            return False
    return True


def _cycle_contract_boundary_violations(
    contract: dict[str, object],
) -> list[dict[str, object]]:
    if not contract:
        return []
    violations = []
    for field_name in _CYCLE_BOUNDARY_FIELDS:
        if contract.get(field_name) is True:
            violations.append(
                {
                    "field": field_name,
                    "reason": "cycle contract boundary flag must be false",
                }
            )
    disallowed = _string_list(contract.get("disallowed_actions"))
    for required_action in ("production_scan", "production_promotion"):
        if required_action not in disallowed:
            violations.append(
                {
                    "field": "disallowed_actions",
                    "reason": required_action + " must be disallowed",
                }
            )
    if contract.get("required_human_review") is not True:
        violations.append(
            {
                "field": "required_human_review",
                "reason": "cycle contract must require human review",
            }
        )
    return sorted(violations, key=lambda item: str(item["field"]))


def _human_review_blockers(
    *,
    status: str,
    missing_required: list[dict[str, object]],
    untrusted: list[dict[str, object]],
    boundary_violations: list[dict[str, object]],
    contract: dict[str, object],
    cycle_root_error: str | None,
) -> list[dict[str, object]]:
    blockers = []
    if cycle_root_error is not None:
        blockers.append(_blocker("cycle_contract_output_dir_invalid", cycle_root_error))
    if missing_required:
        blockers.append(
            _blocker(
                "missing_required_artifacts",
                "required generated cycle contract artifacts are missing",
                artifacts=[item["artifact_role"] for item in missing_required],
            )
        )
    if untrusted:
        blockers.append(
            _blocker(
                "untrusted_artifacts",
                "generated cycle contract artifacts are untrusted, malformed, or hash mismatched",
                artifacts=[item["artifact_role"] for item in untrusted],
            )
        )
    if boundary_violations:
        blockers.append(
            _blocker(
                "cycle_contract_boundary_violation",
                "cycle contract claims or permits disallowed production or mutation authority",
                violations=boundary_violations,
            )
        )
    if status == "blocked_cycle_contract_not_ready":
        blockers.append(
            _blocker(
                "cycle_contract_not_ready",
                "cycle contract is not ready for approval of next bounded smoke iteration preparation",
                cycle_contract_status=contract.get("cycle_contract_status"),
                cycle_contract_decision=contract.get("cycle_contract_decision"),
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


def _summary_markdown(decision: dict[str, object]) -> str:
    lines = [
        "# Local Asset Bounded Smoke Cycle Human Review",
        "",
        "- Human review status: " + str(decision["human_review_status"]),
        "- Human review decision: " + str(decision["human_review_decision"]),
        "- Human review id: " + str(decision["human_review_id"]),
        "- Human reviewer id: " + str(decision["human_reviewer_id"]),
        "- Human signoff hash present: "
        + str(bool(decision["human_signoff_phrase_sha256"])).lower(),
        "- Human signoff phrase persisted: false",
        "- Human notes present: "
        + str(bool(decision["human_review_notes_present"])).lower(),
        "- Cycle contract status: " + str(decision["cycle_contract_status"]),
        "- Cycle contract decision: " + str(decision["cycle_contract_decision"]),
        "- Next bounded smoke iteration prepare allowed: "
        + str(decision["next_bounded_smoke_iteration_prepare_allowed"]).lower(),
        "- Next bounded smoke iteration execute allowed: false",
        "- Next allowed action: " + str(decision["next_allowed_action"]),
        "- Disallowed actions: " + ", ".join(_string_list(decision["disallowed_actions"])),
        "- Missing required count: "
        + str(len(_list_or_empty(decision["missing_required_artifacts"]))),
        "- Untrusted count: " + str(len(_list_or_empty(decision["untrusted_artifacts"]))),
        "",
        "## Explicit Boundaries",
        "",
        "- No runtime stage executed.",
        "- No cycle contract generation executed.",
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
        "- Human review recorded.",
    ]
    return "\n".join(lines) + "\n"


def _human_review_checklist_markdown(decision: dict[str, object]) -> str:
    lines = [
        "# Local Asset Bounded Smoke Cycle Human Review Checklist",
        "",
    ]
    for item in _checklist_items():
        lines.append("- [ ] " + item)
    lines.extend(
        [
            "",
            "## Decision Options",
            "",
        ]
    )
    for option in _REVIEW_DECISION_OPTIONS:
        lines.append("- " + option)
    lines.extend(
        [
            "",
            "Human review status: " + str(decision["human_review_status"]),
            "Human review decision: " + str(decision["human_review_decision"]),
        ]
    )
    return "\n".join(lines) + "\n"


def _checklist_items() -> list[str]:
    return [
        "verify cycle contract artifact exists and is trusted",
        "verify cycle contract status is ready or ready_with_warnings",
        "verify cycle contract decision permits binding only, not production",
        (
            "verify cycle contract next allowed action is "
            "human_review_bounded_smoke_cycle_contract"
        ),
        "verify human decision was explicitly supplied",
        "verify human signoff phrase was valid",
        "verify plaintext signoff phrase was not persisted",
        (
            "verify next bounded smoke iteration prepare is allowed only for "
            "approval decision"
        ),
        "verify next bounded smoke iteration execution is not allowed",
        "verify production scan is not approved",
        "verify production promotion is not granted",
        "verify no runtime stage was executed",
        "verify no input/upstream mutation occurred",
        "verify no raw private content included",
    ]


def _review_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    decision: dict[str, object],
) -> dict[str, object]:
    decision_path = paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE]
    summary_path = paths[LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE]
    checklist_path = paths[
        LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE
    ]
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "decision_path": decision_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "human_review_checklist_path": checklist_path.as_posix(),
        "decision_sha256": sha256_file(decision_path),
        "summary_sha256": sha256_file(summary_path),
        "human_review_checklist_sha256": sha256_file(checklist_path),
        "source_artifacts": [
            {
                "role": artifact["artifact_role"],
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
        "human_review_status": decision["human_review_status"],
        "human_review_decision": decision["human_review_decision"],
        "next_bounded_smoke_iteration_prepare_allowed": decision[
            "next_bounded_smoke_iteration_prepare_allowed"
        ],
        "next_bounded_smoke_iteration_execute_allowed": False,
        "human_signoff_phrase_persisted": False,
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
        for role, file_name in _REVIEW_ARTIFACTS
    ]
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_dir.as_posix(),
        "artifact_index_strategy": "explicit_cycle_human_review_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
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


def _launcher_payload_from_decision(
    decision: dict[str, object],
    paths: dict[str, Path],
    *,
    complete: bool,
) -> dict[str, object]:
    payload = {
        "complete": complete,
        "artifacts_written": True,
        "local_asset_bounded_smoke_cycle_human_review_decision_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_DECISION_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_human_review_manifest_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_MANIFEST_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_human_review_summary_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SUMMARY_FILE
        ].as_posix(),
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": paths[
            LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "cycle_contract_output_dir": decision["cycle_contract_output_dir"],
        "output_dir": decision["output_dir"],
        "project_id": decision["project_id"],
        "human_review_id": decision["human_review_id"],
        "human_reviewer_id": decision["human_reviewer_id"],
        "human_decision": decision["human_decision"],
        "human_review_status": decision["human_review_status"],
        "human_review_decision": decision["human_review_decision"],
        "next_bounded_smoke_iteration_prepare_allowed": decision[
            "next_bounded_smoke_iteration_prepare_allowed"
        ],
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_allowed_action": decision["next_allowed_action"],
        "disallowed_actions": decision["disallowed_actions"],
        "required_human_approval": True,
        "required_human_review": True,
    }
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _structured_failure_result(
    roots: dict[str, Path],
    *,
    project_id: str | None,
    human_review_id: str,
    human_reviewer_id: str,
    human_decision: str,
    failure_stage: str,
    error_message: str,
) -> LocalAssetBoundedSmokeCycleHumanReviewResult:
    status = "blocked_unknown"
    decision = "reject_and_repair_human_review"
    payload = {
        "complete": False,
        "artifacts_written": False,
        "decision_type": _DECISION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "project_id": project_id,
        "cycle_contract_output_dir": roots[
            "cycle_contract_output_dir"
        ].as_posix(),
        "output_dir": roots["output_dir"].as_posix(),
        "human_review_id": human_review_id,
        "human_reviewer_id": human_reviewer_id,
        "human_decision": human_decision,
        "human_review_status": status,
        "human_review_decision": decision,
        "next_bounded_smoke_iteration_prepare_allowed": False,
        "next_bounded_smoke_iteration_execute_allowed": False,
        "next_allowed_action": "repair_human_review",
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": error_message,
        "local_asset_bounded_smoke_cycle_human_review_decision_path": None,
        "local_asset_bounded_smoke_cycle_human_review_manifest_path": None,
        "local_asset_bounded_smoke_cycle_human_review_summary_path": None,
        "local_asset_bounded_smoke_cycle_human_review_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "required_human_review": True,
    }
    return LocalAssetBoundedSmokeCycleHumanReviewResult(
        cycle_contract_output_dir=roots["cycle_contract_output_dir"],
        output_dir=roots["output_dir"],
        decision_path=None,
        manifest_path=None,
        summary_path=None,
        human_review_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        human_review_status=status,
        human_review_decision=decision,
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)
