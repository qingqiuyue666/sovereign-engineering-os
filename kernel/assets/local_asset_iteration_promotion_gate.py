"""Non-authoritative promotion gate for local asset iteration review packets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE",
    "LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE",
    "LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE",
    "LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE",
    "LocalAssetIterationPromotionGateResult",
    "build_local_asset_iteration_promotion_gate",
]

LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE = (
    "local_asset_iteration_promotion_decision.json"
)
LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE = (
    "local_asset_iteration_promotion_gate_manifest.json"
)
LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE = (
    "local_asset_iteration_promotion_summary.md"
)
LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE = (
    "local_asset_iteration_promotion_human_signoff_checklist.md"
)

_ITERATION_REVIEW_PACKET_FILE = "local_asset_smoke_iteration_review_packet.json"
_ITERATION_REVIEW_PACKET_MANIFEST_FILE = (
    "local_asset_smoke_iteration_review_packet_manifest.json"
)
_ITERATION_REVIEW_SUMMARY_FILE = "local_asset_smoke_iteration_review_summary.md"
_ITERATION_REVIEW_CHECKLIST_FILE = (
    "local_asset_smoke_iteration_human_decision_checklist.md"
)
_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_DECISION_TYPE = "local_asset_iteration_promotion_decision_v1"
_MANIFEST_TYPE = "local_asset_iteration_promotion_gate_manifest_v1"
_INDEX_TYPE = "local_asset_iteration_promotion_gate_artifact_index_v1"
_INDEX_MANIFEST_TYPE = (
    "local_asset_iteration_promotion_gate_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_iteration_promotion_gate_only"
_NEXT_ALLOWED_ACTION = "human_review_iteration_promotion_gate"
_ALLOW_REVIEW_DECISION = "generate_promotion_gate_for_iteration"
_ALLOW_PROMOTION_DECISION = "allow_next_bounded_smoke_iteration"
_ITERATION_REVIEW_PACKET_TYPE = "local_asset_smoke_iteration_review_packet_v1"
_ITERATION_REVIEW_PACKET_MANIFEST_TYPE = (
    "local_asset_smoke_iteration_review_packet_manifest_v1"
)
_ITERATION_REVIEW_INDEX_TYPE = (
    "local_asset_smoke_iteration_review_packet_artifact_index_v1"
)
_ITERATION_REVIEW_INDEX_MANIFEST_TYPE = (
    "local_asset_smoke_iteration_review_packet_artifact_index_manifest_v1"
)

_OUTPUT_FILES = (
    LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE,
    LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE,
    LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE,
    LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
)

_BOUNDARY_FLAGS = {
    "scan_performed": False,
    "readiness_run_performed": False,
    "human_smoke_run_performed": False,
    "bounded_smoke_iteration_performed_by_gate": False,
    "iteration_review_packet_run_performed": False,
    "iteration_review_output_mutation_performed": False,
    "iteration_output_mutation_performed": False,
    "delegated_smoke_output_mutation_performed": False,
    "raw_candidate_content_read": False,
    "candidate_file_hashing_performed": False,
    "input_mutation_performed": False,
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
    "production_scan_recommended": False,
}

_SIGNOFF_OPTIONS = (
    "approve_next_bounded_smoke_iteration",
    "reject_and_repair_iteration_review_packet",
    "reject_and_repair_iteration",
    "inspect_iteration_quarantine",
    "inspect_iteration_duplicates",
    "inspect_iteration_incremental_changes",
)

_SIGNOFF_ITEMS = (
    "Verify iteration review status is review_ready.",
    "Verify recommended decision is generate_promotion_gate_for_iteration.",
    "Verify iteration status is iteration_completed.",
    "Verify bounded smoke iteration was performed.",
    "Verify smoke run complete.",
    "Verify scan complete.",
    "Verify production_promotion_granted=false.",
    "Verify production_scan_approved=false.",
    "Verify production_scan_performed=false.",
    "Verify input_mutation_performed=false.",
    "Verify duplicate_deletion_performed=false.",
    "Verify quarantine count is zero.",
    "Verify duplicate group count is zero.",
    "Verify suspicious incremental changes count is zero.",
    "Verify no blocker is present.",
    "Confirm next action is only next bounded smoke iteration, not production scan.",
)

_REJECTED_NEXT_ACTIONS = (
    "production_promotion",
    "production_scan",
    "production_scan_recommendation",
    "automatic_approval",
    "candidate_input_mutation",
    "file_move",
    "file_rename",
    "file_delete",
    "duplicate_deletion",
    "media_organizer_behavior",
)

_SAFE_INFORMATIONAL_WARNINGS = {
    "informational_only",
    "safe_informational_warning",
}


@dataclass(frozen=True)
class _SourceArtifactSpec:
    artifact_role: str
    relative_path: str
    required: bool
    json_artifact: bool


_SOURCE_ARTIFACTS = (
    _SourceArtifactSpec(
        "local_asset_smoke_iteration_review_packet",
        _ITERATION_REVIEW_PACKET_FILE,
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_smoke_iteration_review_packet_manifest",
        _ITERATION_REVIEW_PACKET_MANIFEST_FILE,
        True,
        True,
    ),
    _SourceArtifactSpec(
        "local_asset_smoke_iteration_review_summary",
        _ITERATION_REVIEW_SUMMARY_FILE,
        False,
        False,
    ),
    _SourceArtifactSpec(
        "local_asset_smoke_iteration_human_decision_checklist",
        _ITERATION_REVIEW_CHECKLIST_FILE,
        False,
        False,
    ),
    _SourceArtifactSpec(
        "iteration_review_artifact_index",
        _ARTIFACT_INDEX_FILE,
        True,
        True,
    ),
    _SourceArtifactSpec(
        "iteration_review_artifact_index_manifest",
        _ARTIFACT_INDEX_MANIFEST_FILE,
        True,
        True,
    ),
)

_PROMOTION_ARTIFACTS = (
    (
        "local_asset_iteration_promotion_decision",
        LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE,
    ),
    (
        "local_asset_iteration_promotion_gate_manifest",
        LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE,
    ),
    (
        "local_asset_iteration_promotion_summary",
        LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE,
    ),
    (
        "local_asset_iteration_promotion_human_signoff_checklist",
        LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE,
    ),
)


@dataclass(frozen=True)
class LocalAssetIterationPromotionGateResult:
    iteration_review_output_dir: Path
    output_dir: Path
    decision_path: Path | None
    gate_manifest_path: Path | None
    summary_path: Path | None
    human_signoff_checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    iteration_promotion_gate_status: str
    iteration_promotion_decision: str
    payload: dict[str, object]


def build_local_asset_iteration_promotion_gate(
    iteration_review_output_dir: Path,
    output_dir: Path,
    *,
    project_id: str | None = None,
) -> LocalAssetIterationPromotionGateResult:
    """Build promotion gate artifacts from generated iteration review artifacts."""

    review_path = Path(iteration_review_output_dir)
    output_path = Path(output_dir)
    paths = _promotion_output_paths(output_path)

    output_error = _real_existing_dir_error(output_path, "output_dir")
    if output_error is not None:
        return _structured_failure_result(
            review_path=review_path,
            output_path=output_path,
            failure_stage="preflight_output_dir_missing",
            error_message=output_error,
            project_id=project_id,
        )

    collision = _existing_output_collision(paths)
    if collision is not None:
        return _structured_failure_result(
            review_path=review_path,
            output_path=output_path,
            failure_stage="preflight_output_collision",
            error_message="local asset iteration promotion output already exists: "
            + collision,
            project_id=project_id,
        )

    review_overlap = _existing_dir_overlap_error(
        review_path,
        output_path,
        left_label="iteration_review_output_dir",
        right_label="output_dir",
    )
    if review_overlap is not None:
        return _structured_failure_result(
            review_path=review_path,
            output_path=output_path,
            failure_stage="preflight_iteration_review_output_overlap",
            error_message=review_overlap,
            project_id=project_id,
        )

    review_error = _real_existing_dir_error(
        review_path,
        "iteration_review_output_dir",
    )
    source_artifacts = _source_artifact_records(
        review_path,
        review_error=review_error,
    )
    source_payloads = _read_json_source_payloads(source_artifacts)

    upstream_overlap = _upstream_output_overlap_error(source_payloads, output_path)
    if upstream_overlap is not None:
        return _structured_failure_result(
            review_path=review_path,
            output_path=output_path,
            failure_stage="preflight_upstream_output_overlap",
            error_message=upstream_overlap,
            project_id=project_id,
        )

    decision = _build_decision_payload(
        iteration_review_output_dir=review_path,
        output_dir=output_path,
        project_id=project_id,
        review_error=review_error,
        source_artifacts=source_artifacts,
        source_payloads=source_payloads,
    )
    summary = _summary_markdown(decision)
    checklist = _human_signoff_checklist_markdown(decision)

    _write_json_exclusive(
        paths[LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE],
        decision,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE],
        checklist,
    )
    gate_manifest = _gate_manifest_payload(paths, source_artifacts, decision)
    _write_json_exclusive(
        paths[LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE],
        gate_manifest,
    )
    artifact_index = _artifact_index_payload(output_path, paths)
    _write_json_exclusive(paths[_ARTIFACT_INDEX_FILE], artifact_index)
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(paths[_ARTIFACT_INDEX_MANIFEST_FILE], artifact_index_manifest)

    complete = bool(decision["next_bounded_smoke_iteration_allowed"])
    payload = _launcher_payload_from_decision(decision, paths)
    return LocalAssetIterationPromotionGateResult(
        iteration_review_output_dir=review_path,
        output_dir=output_path,
        decision_path=paths[LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE],
        gate_manifest_path=paths[
            LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE
        ],
        summary_path=paths[LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE],
        human_signoff_checklist_path=paths[
            LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE
        ],
        artifact_index_path=paths[_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[_ARTIFACT_INDEX_MANIFEST_FILE],
        complete=complete,
        iteration_promotion_gate_status=str(
            decision["iteration_promotion_gate_status"]
        ),
        iteration_promotion_decision=str(decision["iteration_promotion_decision"]),
        payload=payload,
    )


def _promotion_output_paths(output_path: Path) -> dict[str, Path]:
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
        ("iteration_output_dir", discovered.get("iteration_output_dir")),
        ("candidate_input_dir", discovered.get("candidate_input_dir")),
        ("delegated smoke_output_dir", discovered.get("smoke_output_dir")),
        ("promotion_output_dir", discovered.get("promotion_output_dir")),
    ):
        if not isinstance(path_value, str) or not path_value:
            continue
        root_path = Path(path_value)
        if root_path.exists() and _path_is_inside(output_path, root_path):
            return "output_dir must not be inside " + label
    return None


def _discover_upstream_dirs(source_payloads: dict[str, object]) -> dict[str, object]:
    packet = _dict_payload(source_payloads, "local_asset_smoke_iteration_review_packet")
    source_artifacts = packet.get("source_artifacts")
    discovered = {
        "iteration_output_dir": _first_text(packet.get("iteration_output_dir")),
        "candidate_input_dir": _first_text(packet.get("candidate_input_dir")),
        "promotion_output_dir": _first_text(packet.get("promotion_output_dir")),
        "smoke_output_dir": _first_text(
            packet.get("smoke_output_dir"),
            packet.get("delegated_smoke_output_dir"),
        ),
    }
    if isinstance(source_artifacts, list):
        for item in source_artifacts:
            if not isinstance(item, dict):
                continue
            role = item.get("artifact_role")
            path_value = item.get("path")
            if not isinstance(path_value, str) or not path_value:
                continue
            artifact_path = Path(path_value)
            if role == "smoke_artifact_index":
                discovered["smoke_output_dir"] = discovered[
                    "smoke_output_dir"
                ] or artifact_path.parent.as_posix()
            if role == "smoke_local_asset_human_smoke_run_summary":
                discovered["smoke_output_dir"] = discovered[
                    "smoke_output_dir"
                ] or artifact_path.parent.as_posix()
            if role == "scan_artifact_index":
                discovered["smoke_output_dir"] = discovered[
                    "smoke_output_dir"
                ] or artifact_path.parent.parent.as_posix()
    return discovered


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _source_artifact_records(
    review_path: Path,
    *,
    review_error: str | None,
) -> list[dict[str, object]]:
    records = []
    for spec in _SOURCE_ARTIFACTS:
        path = review_path / spec.relative_path
        if review_error is not None:
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


def _build_decision_payload(
    *,
    iteration_review_output_dir: Path,
    output_dir: Path,
    project_id: str | None,
    review_error: str | None,
    source_artifacts: list[dict[str, object]],
    source_payloads: dict[str, object],
) -> dict[str, object]:
    records_by_role = {
        str(record["artifact_role"]): record for record in source_artifacts
    }
    packet = _dict_payload(source_payloads, "local_asset_smoke_iteration_review_packet")
    source_state = _source_state(
        source_artifacts,
        records_by_role,
        source_payloads,
        review_error=review_error,
    )
    summaries = _summaries_from_packet(packet)
    facts = _decision_facts(packet, summaries)
    blockers = _iteration_promotion_blockers(source_state, facts)
    gate_status, promotion_decision = _promotion_status_and_decision(
        blockers,
        facts,
        source_state,
    )
    allowed = gate_status == "iteration_promotion_candidate"
    project = _first_text(project_id, packet.get("project_id"))
    allowed_next_action = (
        "next_bounded_smoke_iteration" if allowed else "human_inspection_or_repair"
    )
    checklist = _human_signoff_checklist_payload()
    return {
        "decision_type": _DECISION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "iteration_review_output_dir": iteration_review_output_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "project_id": project,
        "iteration_promotion_gate_status": gate_status,
        "iteration_promotion_decision": promotion_decision,
        "next_bounded_smoke_iteration_allowed": allowed,
        **dict(_PRODUCTION_FLAGS),
        "iteration_review_status": facts["iteration_review_status"],
        "iteration_review_recommended_human_decision": facts[
            "iteration_review_recommended_human_decision"
        ],
        "iteration_summary": summaries["iteration_summary"],
        "signoff_summary": summaries["signoff_summary"],
        "admission_summary": summaries["admission_summary"],
        "promotion_summary": summaries["promotion_summary"],
        "delegated_smoke_summary": summaries["delegated_smoke_summary"],
        "delegated_scan_summary": summaries["delegated_scan_summary"],
        "duplicate_summary": summaries["duplicate_summary"],
        "quarantine_summary": summaries["quarantine_summary"],
        "sqlite_summary": summaries["sqlite_summary"],
        "incremental_summary": summaries["incremental_summary"],
        "failure_summary": summaries["failure_summary"],
        "warning_summary": summaries["warning_summary"],
        "blocker_summary": _blocker_summary(blockers),
        "iteration_promotion_blockers": blockers,
        "allowed_next_action": allowed_next_action,
        "rejected_next_actions": list(_REJECTED_NEXT_ACTIONS),
        "required_human_signoff": True,
        "human_signoff_checklist": checklist,
        "source_artifacts": source_artifacts,
        "missing_iteration_review_artifacts": source_state[
            "missing_iteration_review_artifacts"
        ],
        "untrusted_iteration_review_artifacts": source_state[
            "untrusted_iteration_review_artifacts"
        ],
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _source_state(
    source_artifacts: list[dict[str, object]],
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
    *,
    review_error: str | None,
) -> dict[str, object]:
    missing = [
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
        for item in missing
        if item["required"] is True
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
    untrusted.extend(_review_artifact_hash_mismatches(records_by_role, source_payloads))
    untrusted.extend(_review_artifact_type_mismatches(source_payloads))
    if review_error is not None and "symlink" in review_error:
        untrusted.append("iteration_review_output_dir")
    return {
        "missing_iteration_review_artifacts": [
            item for item in missing if item["required"] is True
        ],
        "missing_required_roles": sorted(set(missing_required)),
        "untrusted_iteration_review_artifacts": sorted(set(untrusted)),
        "parse_error_artifacts": sorted(set(parse_errors)),
    }


def _review_artifact_hash_mismatches(
    records_by_role: dict[str, dict[str, object]],
    source_payloads: dict[str, object],
) -> list[str]:
    mismatches = []
    packet_manifest = _dict_payload(
        source_payloads,
        "local_asset_smoke_iteration_review_packet_manifest",
    )
    packet_record = records_by_role.get("local_asset_smoke_iteration_review_packet", {})
    if packet_manifest and packet_manifest.get("packet_sha256") != packet_record.get(
        "sha256"
    ):
        mismatches.append("local_asset_smoke_iteration_review_packet_manifest")
    summary_record = records_by_role.get(
        "local_asset_smoke_iteration_review_summary",
        {},
    )
    if (
        packet_manifest
        and summary_record.get("exists") is True
        and packet_manifest.get("summary_sha256") != summary_record.get("sha256")
    ):
        mismatches.append("local_asset_smoke_iteration_review_packet_manifest")
    checklist_record = records_by_role.get(
        "local_asset_smoke_iteration_human_decision_checklist",
        {},
    )
    if (
        packet_manifest
        and checklist_record.get("exists") is True
        and packet_manifest.get("decision_checklist_sha256")
        != checklist_record.get("sha256")
    ):
        mismatches.append("local_asset_smoke_iteration_review_packet_manifest")
    index_manifest = _dict_payload(
        source_payloads,
        "iteration_review_artifact_index_manifest",
    )
    index_record = records_by_role.get("iteration_review_artifact_index", {})
    if index_manifest and index_manifest.get("artifact_index_sha256") != index_record.get(
        "sha256"
    ):
        mismatches.append("iteration_review_artifact_index_manifest")
    return mismatches


def _review_artifact_type_mismatches(source_payloads: dict[str, object]) -> list[str]:
    mismatches = []
    packet = _dict_payload(source_payloads, "local_asset_smoke_iteration_review_packet")
    if packet and packet.get("packet_type") != _ITERATION_REVIEW_PACKET_TYPE:
        mismatches.append("local_asset_smoke_iteration_review_packet")
    packet_manifest = _dict_payload(
        source_payloads,
        "local_asset_smoke_iteration_review_packet_manifest",
    )
    if (
        packet_manifest
        and packet_manifest.get("manifest_type") != _ITERATION_REVIEW_PACKET_MANIFEST_TYPE
    ):
        mismatches.append("local_asset_smoke_iteration_review_packet_manifest")
    artifact_index = _dict_payload(source_payloads, "iteration_review_artifact_index")
    if artifact_index and artifact_index.get("index_type") != _ITERATION_REVIEW_INDEX_TYPE:
        mismatches.append("iteration_review_artifact_index")
    artifact_index_manifest = _dict_payload(
        source_payloads,
        "iteration_review_artifact_index_manifest",
    )
    if (
        artifact_index_manifest
        and artifact_index_manifest.get("manifest_type")
        != _ITERATION_REVIEW_INDEX_MANIFEST_TYPE
    ):
        mismatches.append("iteration_review_artifact_index_manifest")
    return mismatches


def _summaries_from_packet(packet: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        "iteration_summary": _dict_or_empty(packet.get("iteration_summary")),
        "signoff_summary": _dict_or_empty(packet.get("signoff_summary")),
        "admission_summary": _dict_or_empty(packet.get("admission_summary")),
        "promotion_summary": _dict_or_empty(packet.get("promotion_summary")),
        "delegated_smoke_summary": _dict_or_empty(
            packet.get("delegated_smoke_summary")
        ),
        "delegated_scan_summary": _dict_or_empty(packet.get("delegated_scan_summary")),
        "duplicate_summary": _dict_or_empty(packet.get("duplicate_summary")),
        "quarantine_summary": _dict_or_empty(packet.get("quarantine_summary")),
        "sqlite_summary": _dict_or_empty(packet.get("sqlite_summary")),
        "incremental_summary": _dict_or_empty(packet.get("incremental_summary")),
        "failure_summary": _dict_or_empty(packet.get("failure_summary")),
        "warning_summary": _dict_or_empty(packet.get("warning_summary")),
    }


def _decision_facts(
    packet: dict[str, object],
    summaries: dict[str, dict[str, object]],
) -> dict[str, object]:
    iteration = summaries["iteration_summary"]
    delegated_smoke = summaries["delegated_smoke_summary"]
    delegated_scan = summaries["delegated_scan_summary"]
    duplicate = summaries["duplicate_summary"]
    quarantine = summaries["quarantine_summary"]
    incremental = summaries["incremental_summary"]
    warnings = summaries["warning_summary"]
    return {
        "iteration_review_status": _first_text(packet.get("iteration_review_status")),
        "iteration_review_recommended_human_decision": _first_text(
            packet.get("recommended_human_decision"),
            packet.get("iteration_review_recommended_human_decision"),
        ),
        "iteration_status": _first_text(
            packet.get("iteration_status"),
            iteration.get("iteration_status"),
        ),
        "iteration_decision": _first_text(
            packet.get("iteration_decision"),
            iteration.get("iteration_decision"),
        ),
        "bounded_smoke_iteration_performed": _first_bool(
            packet.get("bounded_smoke_iteration_performed"),
            iteration.get("bounded_smoke_iteration_performed"),
            default=False,
        ),
        "smoke_run_complete": _first_bool(
            packet.get("smoke_run_complete"),
            iteration.get("smoke_run_complete"),
            delegated_smoke.get("bounded_smoke_run_performed"),
            default=False,
        ),
        "scan_complete": _first_bool(
            packet.get("scan_complete"),
            iteration.get("scan_complete"),
            delegated_smoke.get("scan_complete"),
            delegated_scan.get("scan_complete"),
            default=False,
        ),
        "production_promotion_granted": _first_bool(
            packet.get("production_promotion_granted"),
            default=False,
        ),
        "production_scan_approved": _first_bool(
            packet.get("production_scan_approved"),
            default=False,
        ),
        "production_scan_performed": _first_bool(
            packet.get("production_scan_performed"),
            delegated_smoke.get("production_scan_performed"),
            default=False,
        ),
        "input_mutation_performed": _first_bool(
            packet.get("input_mutation_performed"),
            default=False,
        ),
        "duplicate_deletion_performed": _first_bool(
            packet.get("duplicate_deletion_performed"),
            duplicate.get("automatic_dedupe_performed"),
            default=False,
        ),
        "quarantined_path_count": _first_int(
            packet.get("quarantined_path_count"),
            quarantine.get("quarantined_path_count"),
            delegated_scan.get("quarantined_path_count"),
            default=0,
        ),
        "duplicate_group_count": _first_int(
            packet.get("duplicate_group_count"),
            duplicate.get("duplicate_group_count"),
            delegated_scan.get("duplicate_group_count"),
            default=0,
        ),
        "changed_asset_count": _first_int(
            packet.get("changed_asset_count"),
            incremental.get("changed_asset_count"),
            default=0,
        ),
        "new_asset_count": _first_int(
            packet.get("new_asset_count"),
            incremental.get("new_asset_count"),
            default=0,
        ),
        "missing_asset_count": _first_int(
            packet.get("missing_asset_count"),
            incremental.get("missing_asset_count"),
            default=0,
        ),
        "suspicious_change_count": _first_int(
            packet.get("suspicious_change_count"),
            incremental.get("suspicious_change_count"),
            default=0,
        ),
        "incremental_plan_mode": _first_text(
            packet.get("incremental_plan_mode"),
            incremental.get("plan_mode"),
        ),
        "warning_count": _first_int(
            packet.get("warning_count"),
            warnings.get("warning_count"),
            default=0,
        ),
        "warnings": _string_list(warnings.get("warnings")),
    }


def _iteration_promotion_blockers(
    source_state: dict[str, object],
    facts: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if source_state["missing_required_roles"]:
        blockers.append(
            _blocker(
                "missing_iteration_review_artifacts",
                "required generated iteration review artifacts are missing",
                artifacts=source_state["missing_required_roles"],
            )
        )
    if source_state["untrusted_iteration_review_artifacts"]:
        blockers.append(
            _blocker(
                "untrusted_iteration_review_artifacts",
                "generated iteration review artifacts are untrusted or hash mismatched",
                artifacts=source_state["untrusted_iteration_review_artifacts"],
            )
        )
    if facts["iteration_review_status"] != "review_ready":
        blockers.append(
            _blocker(
                "iteration_review_not_ready",
                "iteration review status is not review_ready",
                value=facts["iteration_review_status"],
            )
        )
    if facts["iteration_review_recommended_human_decision"] != _ALLOW_REVIEW_DECISION:
        blockers.append(
            _blocker(
                "iteration_review_recommended_decision_not_promotion_gate",
                "iteration review does not recommend the iteration promotion gate",
                value=facts["iteration_review_recommended_human_decision"],
            )
        )
    if facts["iteration_status"] != "iteration_completed":
        blockers.append(
            _blocker(
                "iteration_not_completed",
                "bounded smoke iteration is not complete",
                value=facts["iteration_status"],
            )
        )
    if facts["bounded_smoke_iteration_performed"] is not True:
        blockers.append(
            _blocker(
                "bounded_smoke_iteration_not_performed",
                "bounded smoke iteration was not performed",
            )
        )
    if facts["smoke_run_complete"] is not True:
        blockers.append(_blocker("smoke_run_incomplete", "smoke run is not complete"))
    if facts["scan_complete"] is not True:
        blockers.append(_blocker("scan_incomplete", "scan is not complete"))
    for role in (
        "production_promotion_granted",
        "production_scan_approved",
        "production_scan_performed",
        "input_mutation_performed",
        "duplicate_deletion_performed",
    ):
        if facts[role] is True:
            blockers.append(_blocker(role, role + " must be false"))
    if int(facts["quarantined_path_count"]) > 0 or facts[
        "iteration_review_recommended_human_decision"
    ] == "inspect_iteration_quarantine_before_promotion":
        blockers.append(
            _blocker(
                "iteration_quarantine_present",
                "iteration quarantine paths require human inspection",
                count=facts["quarantined_path_count"],
            )
        )
    if int(facts["duplicate_group_count"]) > 0 or facts[
        "iteration_review_recommended_human_decision"
    ] == "inspect_iteration_duplicates_before_promotion":
        blockers.append(
            _blocker(
                "iteration_duplicate_groups_present",
                "iteration duplicate groups require human inspection",
                count=facts["duplicate_group_count"],
            )
        )
    if _incremental_requires_inspection(facts):
        blockers.append(
            _blocker(
                "iteration_incremental_changes_require_inspection",
                "iteration incremental changes require human inspection",
                count=facts["suspicious_change_count"],
            )
        )
    if int(facts["warning_count"]) > 0 and not _warnings_are_safe_information(facts):
        blockers.append(
            _blocker(
                "warnings_present",
                "iteration review warnings require repair or explicit human review",
                warnings=facts["warnings"],
            )
        )
    return sorted(blockers, key=lambda item: str(item["blocker_role"]))


def _incremental_requires_inspection(facts: dict[str, object]) -> bool:
    if facts["iteration_review_recommended_human_decision"] == (
        "inspect_iteration_incremental_changes_before_promotion"
    ):
        return True
    if int(facts["suspicious_change_count"]) > 0:
        return True
    return (
        facts["incremental_plan_mode"] == "compare_previous_scan"
        and (
            int(facts["changed_asset_count"]) > 0
            or int(facts["new_asset_count"]) > 0
            or int(facts["missing_asset_count"]) > 0
        )
    )


def _warnings_are_safe_information(facts: dict[str, object]) -> bool:
    warnings = facts["warnings"]
    if not warnings:
        return False
    for warning in warnings:
        text = str(warning)
        if text in _SAFE_INFORMATIONAL_WARNINGS:
            continue
        if text.startswith("informational:") or text.startswith("info:"):
            continue
        return False
    return True


def _blocker(blocker_role: str, detail: str, **extra: object) -> dict[str, object]:
    item = {
        "blocker_role": blocker_role,
        "severity": "blocking",
        "detail": detail,
    }
    item.update(extra)
    return item


def _promotion_status_and_decision(
    blockers: list[dict[str, object]],
    facts: dict[str, object],
    source_state: dict[str, object],
) -> tuple[str, str]:
    roles = {str(blocker["blocker_role"]) for blocker in blockers}
    if "iteration_review_output_dir" in source_state[
        "untrusted_iteration_review_artifacts"
    ]:
        return (
            "blocked_untrusted_iteration_review_packet",
            "block_until_iteration_review_packet_repaired",
        )
    if source_state["missing_required_roles"]:
        return (
            "blocked_missing_iteration_review_artifacts",
            "block_until_iteration_review_packet_repaired",
        )
    if source_state["untrusted_iteration_review_artifacts"]:
        return (
            "blocked_untrusted_iteration_review_packet",
            "block_until_iteration_review_packet_repaired",
        )
    if facts["iteration_review_status"] == "review_blocked_missing_required_artifacts":
        return (
            "blocked_missing_iteration_review_artifacts",
            "block_until_iteration_review_packet_repaired",
        )
    if facts["iteration_review_status"] == "review_blocked_untrusted_artifacts":
        return (
            "blocked_untrusted_iteration_review_packet",
            "block_until_iteration_review_packet_repaired",
        )
    if "iteration_quarantine_present" in roles:
        return (
            "blocked_quarantine",
            "block_until_human_inspects_iteration_quarantine",
        )
    if "iteration_duplicate_groups_present" in roles:
        return (
            "blocked_duplicates",
            "block_until_human_inspects_iteration_duplicates",
        )
    if "iteration_incremental_changes_require_inspection" in roles:
        return (
            "blocked_incremental_changes",
            "block_until_human_inspects_iteration_incremental_changes",
        )
    if (
        facts["iteration_review_status"] == "review_blocked_failed_iteration"
        or "iteration_not_completed" in roles
        or "bounded_smoke_iteration_not_performed" in roles
        or "smoke_run_incomplete" in roles
        or "scan_incomplete" in roles
    ):
        return "blocked_failed_iteration", "block_until_iteration_repaired"
    if "warnings_present" in roles:
        return "blocked_warnings", "block_until_iteration_review_packet_repaired"
    if blockers:
        return "blocked_unknown", "block_until_iteration_review_packet_repaired"
    return "iteration_promotion_candidate", _ALLOW_PROMOTION_DECISION


def _blocker_summary(blockers: list[dict[str, object]]) -> dict[str, object]:
    return {
        "iteration_promotion_blocker_count": len(blockers),
        "blocker_roles": [str(blocker["blocker_role"]) for blocker in blockers],
        "no_blockers_present": len(blockers) == 0,
    }


def _human_signoff_checklist_payload() -> dict[str, object]:
    return {
        "checklist_type": (
            "local_asset_iteration_promotion_human_signoff_checklist_v1"
        ),
        "items": [{"text": item, "checked": False} for item in _SIGNOFF_ITEMS],
        "decision_options": list(_SIGNOFF_OPTIONS),
        "raw_private_file_contents_included": False,
        "automatic_approval_granted": False,
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "production_scan_recommended": False,
    }


def _summary_markdown(decision: dict[str, object]) -> str:
    lines = [
        "# Local Asset Iteration Promotion Summary",
        "",
        "- Iteration promotion gate status: `"
        + str(decision["iteration_promotion_gate_status"])
        + "`",
        "- Iteration promotion decision: `"
        + str(decision["iteration_promotion_decision"])
        + "`",
        "- Next bounded smoke iteration allowed: "
        + _bool_text(decision["next_bounded_smoke_iteration_allowed"]),
        "- Production promotion granted: false",
        "- Production scan approved: false",
        "- Production scan performed: false",
        "- Iteration review output dir: `"
        + str(decision["iteration_review_output_dir"])
        + "`",
        "- Promotion output dir: `" + str(decision["output_dir"]) + "`",
        "- Project id: `" + str(decision["project_id"]) + "`",
        "- Iteration review status: `"
        + str(decision["iteration_review_status"])
        + "`",
        "- Iteration review recommended decision: `"
        + str(decision["iteration_review_recommended_human_decision"])
        + "`",
        "",
        "## Iteration Summary",
        "",
        "```json",
        json.dumps(decision["iteration_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Delegated Smoke Summary",
        "",
        "```json",
        json.dumps(decision["delegated_smoke_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Delegated Scan Summary",
        "",
        "```json",
        json.dumps(decision["delegated_scan_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Duplicate Summary",
        "",
        "```json",
        json.dumps(decision["duplicate_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Quarantine Summary",
        "",
        "```json",
        json.dumps(decision["quarantine_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Incremental Summary",
        "",
        "```json",
        json.dumps(decision["incremental_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Failure And Warning Summary",
        "",
        "```json",
        json.dumps(
            {
                "failure_summary": decision["failure_summary"],
                "warning_summary": decision["warning_summary"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Blocker Summary",
        "",
        "- Blocker count: "
        + str(decision["blocker_summary"]["iteration_promotion_blocker_count"]),
        "- Blocker roles: `"
        + json.dumps(decision["blocker_summary"]["blocker_roles"])
        + "`",
        "- Allowed next action: `" + str(decision["allowed_next_action"]) + "`",
        "- Rejected next actions: `"
        + json.dumps(decision["rejected_next_actions"])
        + "`",
        "",
        "## Explicit Boundaries",
        "",
        "- no scan performed",
        "- no readiness run performed",
        "- no human smoke run performed",
        "- no bounded smoke iteration performed by gate",
        "- no iteration review packet run performed",
        "- no iteration review output mutation",
        "- no iteration output mutation",
        "- no delegated smoke output mutation",
        "- no raw candidate content read",
        "- no candidate hashing performed",
        "- no input mutation",
        "- no file move/rename/delete",
        "- no duplicate deletion",
        "- no media organizer behavior",
        "- no production promotion",
        "- no production scan approval",
        "- no production scan recommendation",
        "- human signoff required",
    ]
    return "\n".join(lines) + "\n"


def _human_signoff_checklist_markdown(decision: dict[str, object]) -> str:
    lines = [
        "# Local Asset Iteration Promotion Human Signoff Checklist",
        "",
    ]
    for item in _SIGNOFF_ITEMS:
        lines.append("- [ ] " + item)
    lines.extend(["", "## Signoff Decision Options", ""])
    for option in _SIGNOFF_OPTIONS:
        checked = "x" if option == _recommended_signoff_option(decision) else " "
        lines.append("- [" + checked + "] " + option)
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
    return "\n".join(lines) + "\n"


def _recommended_signoff_option(decision: dict[str, object]) -> str:
    status = decision["iteration_promotion_gate_status"]
    if status == "iteration_promotion_candidate":
        return "approve_next_bounded_smoke_iteration"
    if status == "blocked_quarantine":
        return "inspect_iteration_quarantine"
    if status == "blocked_duplicates":
        return "inspect_iteration_duplicates"
    if status == "blocked_incremental_changes":
        return "inspect_iteration_incremental_changes"
    if status == "blocked_failed_iteration":
        return "reject_and_repair_iteration"
    return "reject_and_repair_iteration_review_packet"


def _gate_manifest_payload(
    paths: dict[str, Path],
    source_artifacts: list[dict[str, object]],
    decision: dict[str, object],
) -> dict[str, object]:
    decision_path = paths[LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE]
    summary_path = paths[LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE]
    checklist_path = paths[
        LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE
    ]
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "decision_path": decision_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "human_signoff_checklist_path": checklist_path.as_posix(),
        "decision_sha256": sha256_file(decision_path),
        "summary_sha256": sha256_file(summary_path),
        "human_signoff_checklist_sha256": sha256_file(checklist_path),
        "source_artifacts": [
            {
                "artifact_role": record["artifact_role"],
                "path": record["path"],
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
                "exists": record["exists"],
                "required": record["required"],
                "trusted_generated_artifact": record[
                    "trusted_generated_artifact"
                ],
            }
            for record in source_artifacts
        ],
        "iteration_promotion_gate_status": decision[
            "iteration_promotion_gate_status"
        ],
        "iteration_promotion_decision": decision["iteration_promotion_decision"],
        "next_bounded_smoke_iteration_allowed": decision[
            "next_bounded_smoke_iteration_allowed"
        ],
        **dict(_PRODUCTION_FLAGS),
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
    for role, file_name in _PROMOTION_ARTIFACTS:
        path = paths[file_name]
        entries.append(_promotion_artifact_entry(output_path, role, path))
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "explicit_iteration_promotion_gate_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "iteration_review_output_files_recursively_indexed": False,
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
        "indexed_relative_paths": [str(entry["relative_path"]) for entry in entries],
        "job_dir": output_path.as_posix(),
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "iteration_review_output_files_recursively_indexed": False,
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _promotion_artifact_entry(
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


def _launcher_payload_from_decision(
    decision: dict[str, object],
    paths: dict[str, Path],
) -> dict[str, object]:
    iteration = _dict_or_empty(decision["iteration_summary"])
    delegated_smoke = _dict_or_empty(decision["delegated_smoke_summary"])
    delegated_scan = _dict_or_empty(decision["delegated_scan_summary"])
    duplicate = _dict_or_empty(decision["duplicate_summary"])
    quarantine = _dict_or_empty(decision["quarantine_summary"])
    incremental = _dict_or_empty(decision["incremental_summary"])
    warnings = _dict_or_empty(decision["warning_summary"])
    blockers = decision["iteration_promotion_blockers"]
    return {
        "local_asset_iteration_promotion_decision_path": paths[
            LOCAL_ASSET_ITERATION_PROMOTION_DECISION_FILE
        ].as_posix(),
        "local_asset_iteration_promotion_gate_manifest_path": paths[
            LOCAL_ASSET_ITERATION_PROMOTION_GATE_MANIFEST_FILE
        ].as_posix(),
        "local_asset_iteration_promotion_summary_path": paths[
            LOCAL_ASSET_ITERATION_PROMOTION_SUMMARY_FILE
        ].as_posix(),
        "local_asset_iteration_promotion_human_signoff_checklist_path": paths[
            LOCAL_ASSET_ITERATION_PROMOTION_HUMAN_SIGNOFF_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[_ARTIFACT_INDEX_FILE].as_posix(),
        "artifact_index_manifest_path": paths[_ARTIFACT_INDEX_MANIFEST_FILE].as_posix(),
        "iteration_review_output_dir": decision["iteration_review_output_dir"],
        "output_dir": decision["output_dir"],
        "project_id": decision["project_id"],
        "iteration_promotion_gate_status": decision[
            "iteration_promotion_gate_status"
        ],
        "iteration_promotion_decision": decision["iteration_promotion_decision"],
        "iteration_promotion_blocker_count": len(blockers),
        "iteration_promotion_blockers": blockers,
        "allowed_next_action": decision["allowed_next_action"],
        "rejected_next_actions": decision["rejected_next_actions"],
        "iteration_review_status": decision["iteration_review_status"],
        "iteration_review_recommended_human_decision": decision[
            "iteration_review_recommended_human_decision"
        ],
        "iteration_status": _first_text(
            iteration.get("iteration_status"),
        ),
        "iteration_decision": _first_text(iteration.get("iteration_decision")),
        "bounded_smoke_iteration_performed": _first_bool(
            iteration.get("bounded_smoke_iteration_performed"),
            default=False,
        ),
        "smoke_run_complete": _first_bool(
            iteration.get("smoke_run_complete"),
            delegated_smoke.get("bounded_smoke_run_performed"),
            default=False,
        ),
        "scan_complete": _first_bool(
            iteration.get("scan_complete"),
            delegated_smoke.get("scan_complete"),
            delegated_scan.get("scan_complete"),
            default=False,
        ),
        "duplicate_group_count": _first_int(
            duplicate.get("duplicate_group_count"),
            delegated_scan.get("duplicate_group_count"),
            default=0,
        ),
        "quarantined_path_count": _first_int(
            quarantine.get("quarantined_path_count"),
            delegated_scan.get("quarantined_path_count"),
            default=0,
        ),
        "suspicious_change_count": _first_int(
            incremental.get("suspicious_change_count"),
            default=0,
        ),
        "warning_count": _first_int(warnings.get("warning_count"), default=0),
        "required_human_signoff": True,
        "next_bounded_smoke_iteration_allowed": decision[
            "next_bounded_smoke_iteration_allowed"
        ],
        **dict(_PRODUCTION_FLAGS),
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _structured_failure_result(
    *,
    review_path: Path,
    output_path: Path,
    failure_stage: str,
    error_message: str,
    project_id: str | None,
) -> LocalAssetIterationPromotionGateResult:
    status = "blocked_unknown"
    promotion_decision = "block_until_iteration_review_packet_repaired"
    payload = _structured_failure_payload(
        review_path=review_path,
        output_path=output_path,
        project_id=project_id,
        iteration_promotion_gate_status=status,
        iteration_promotion_decision=promotion_decision,
        failure_stage=failure_stage,
        error_message=error_message,
    )
    return LocalAssetIterationPromotionGateResult(
        iteration_review_output_dir=review_path,
        output_dir=output_path,
        decision_path=None,
        gate_manifest_path=None,
        summary_path=None,
        human_signoff_checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        iteration_promotion_gate_status=status,
        iteration_promotion_decision=promotion_decision,
        payload=payload,
    )


def _structured_failure_payload(
    *,
    review_path: Path,
    output_path: Path,
    project_id: str | None,
    iteration_promotion_gate_status: str,
    iteration_promotion_decision: str,
    failure_stage: str,
    error_message: str,
) -> dict[str, object]:
    return {
        "complete": False,
        "iteration_review_output_dir": review_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "project_id": project_id,
        "iteration_promotion_gate_status": iteration_promotion_gate_status,
        "iteration_promotion_decision": iteration_promotion_decision,
        "iteration_promotion_blocker_count": 1,
        "iteration_promotion_blockers": [
            _blocker("preflight_failure", _safe_text(error_message))
        ],
        "allowed_next_action": "repair_preflight_failure",
        "rejected_next_actions": list(_REJECTED_NEXT_ACTIONS),
        "iteration_review_status": None,
        "iteration_review_recommended_human_decision": None,
        "iteration_status": None,
        "iteration_decision": None,
        "bounded_smoke_iteration_performed": False,
        "smoke_run_complete": False,
        "scan_complete": False,
        "duplicate_group_count": 0,
        "quarantined_path_count": 0,
        "suspicious_change_count": 0,
        "warning_count": 0,
        "required_human_signoff": True,
        "next_bounded_smoke_iteration_allowed": False,
        **dict(_PRODUCTION_FLAGS),
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "local_asset_iteration_promotion_decision_path": None,
        "local_asset_iteration_promotion_gate_manifest_path": None,
        "local_asset_iteration_promotion_summary_path": None,
        "local_asset_iteration_promotion_human_signoff_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _dict_payload(payloads: dict[str, object], role: str) -> dict[str, object]:
    payload = payloads.get(role)
    return payload if isinstance(payload, dict) else {}


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value if isinstance(item, str) and item)


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


def _first_bool(*values: object, default: bool | None = None) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
    return default


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
    return text[:240] if text else "local asset iteration promotion gate failed"


def _bool_text(value: object) -> str:
    return str(bool(value)).lower()


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()
