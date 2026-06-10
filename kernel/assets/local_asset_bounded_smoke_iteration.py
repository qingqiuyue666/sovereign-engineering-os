"""Gated bounded smoke iteration for local asset scans."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json

from kernel.assets.local_asset_human_smoke import HUMAN_SMOKE_APPROVAL_PHRASE
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE",
    "DEFAULT_ITERATION_MAX_SMOKE_BYTES",
    "DEFAULT_ITERATION_MAX_SMOKE_DEPTH",
    "DEFAULT_ITERATION_MAX_SMOKE_FILES",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_MANIFEST_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_RESULT_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SIGNOFF_FILE",
    "LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE",
    "LocalAssetBoundedSmokeIterationResult",
    "run_local_asset_bounded_smoke_iteration",
]


BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE = (
    "I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION"
)
DEFAULT_ITERATION_MAX_SMOKE_FILES = 100
DEFAULT_ITERATION_MAX_SMOKE_BYTES = 1073741824
DEFAULT_ITERATION_MAX_SMOKE_DEPTH = 12

LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SIGNOFF_FILE = (
    "local_asset_bounded_smoke_iteration_signoff.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE = (
    "local_asset_bounded_smoke_iteration_admission.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_RESULT_FILE = (
    "local_asset_bounded_smoke_iteration_result.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_MANIFEST_FILE = (
    "local_asset_bounded_smoke_iteration_manifest.json"
)
LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE = (
    "local_asset_bounded_smoke_iteration_summary.md"
)
LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE = (
    "local_asset_bounded_smoke_iteration_human_review_checklist.md"
)

_CONTROL_DIR_NAME = "control"
_SMOKE_DIR_NAME = "smoke"
_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"

_PROMOTION_DECISION_FILE = "local_asset_smoke_promotion_decision.json"
_PROMOTION_MANIFEST_FILE = "local_asset_smoke_promotion_gate_manifest.json"
_PROMOTION_SUMMARY_FILE = "local_asset_smoke_promotion_summary.md"
_PROMOTION_CHECKLIST_FILE = "local_asset_smoke_promotion_human_signoff_checklist.md"

_RESULT_TYPE = "local_asset_bounded_smoke_iteration_result_v1"
_MANIFEST_TYPE = "local_asset_bounded_smoke_iteration_manifest_v1"
_SIGNOFF_TYPE = "local_asset_bounded_smoke_iteration_signoff_v1"
_ADMISSION_TYPE = "local_asset_bounded_smoke_iteration_admission_v1"
_INDEX_TYPE = "local_asset_bounded_smoke_iteration_artifact_index_v1"
_INDEX_MANIFEST_TYPE = "local_asset_bounded_smoke_iteration_artifact_index_manifest_v1"
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_bounded_smoke_iteration_only"
_NEXT_ACTION = "human_review_bounded_smoke_iteration_result"
_ADMISSION_NEXT_ACTION = "run_existing_human_approved_bounded_smoke_launcher"

_PROMOTION_DECISION_TYPE = "local_asset_smoke_promotion_decision_v1"
_PROMOTION_MANIFEST_TYPE = "local_asset_smoke_promotion_gate_manifest_v1"
_PROMOTION_INDEX_TYPE = "local_asset_smoke_promotion_gate_artifact_index_v1"
_PROMOTION_INDEX_MANIFEST_TYPE = (
    "local_asset_smoke_promotion_gate_artifact_index_manifest_v1"
)
_PROMOTION_EXECUTION_CAPABILITY = "local_asset_smoke_promotion_gate_only"
_READINESS_REPORT_TYPE = "local_asset_real_folder_smoke_readiness_report_v1"
_READINESS_EXECUTION_CAPABILITY = "real_folder_smoke_readiness_only"

_READY_READINESS_STATUSES = {"ready", "ready_with_warnings"}

_BOUNDARY_FLAGS = {
    "production_promotion_granted": False,
    "production_scan_approved": False,
    "production_scan_performed": False,
    "automatic_approval_performed": False,
    "watcher_daemon_started": False,
    "raw_candidate_content_read_outside_scan_runtime": False,
    "candidate_file_hashing_outside_scan_runtime": False,
    "input_mutation_performed": False,
    "promotion_output_mutation_performed": False,
    "review_output_mutation_performed": False,
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


@dataclass(frozen=True)
class LocalAssetBoundedSmokeIterationResult:
    promotion_output_dir: Path
    candidate_input_dir: Path
    readiness_report: Path
    output_dir: Path
    control_output_dir: Path
    smoke_output_dir: Path
    result_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    human_review_checklist_path: Path | None
    signoff_path: Path | None
    admission_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    iteration_status: str
    iteration_decision: str
    payload: dict[str, object]


def run_local_asset_bounded_smoke_iteration(
    promotion_output_dir: Path,
    candidate_input_dir: Path,
    readiness_report: Path,
    output_dir: Path,
    *,
    human_signoff_id: str,
    human_signoff_phrase: str,
    recursive: bool = False,
    include_hidden: bool = False,
    project_id: str | None = None,
    previous_scan_output_dir: Path | None = None,
    max_smoke_files: int = DEFAULT_ITERATION_MAX_SMOKE_FILES,
    max_smoke_bytes: int = DEFAULT_ITERATION_MAX_SMOKE_BYTES,
    max_smoke_depth: int = DEFAULT_ITERATION_MAX_SMOKE_DEPTH,
) -> LocalAssetBoundedSmokeIterationResult:
    """Run the next bounded smoke iteration after promotion-gate signoff."""

    paths = _iteration_paths(Path(output_dir))
    previous_scan_path = (
        None if previous_scan_output_dir is None else Path(previous_scan_output_dir)
    )
    common = _common_payload(
        promotion_output_dir=Path(promotion_output_dir),
        candidate_input_dir=Path(candidate_input_dir),
        readiness_report=Path(readiness_report),
        output_dir=Path(output_dir),
        control_output_dir=paths["control_output_dir"],
        smoke_output_dir=paths["smoke_output_dir"],
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        previous_scan_output_dir=previous_scan_path,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
    )

    output_error = _real_existing_dir_error(paths["output_dir"], "output_dir")
    if output_error is not None:
        return _result_without_artifacts(
            common,
            iteration_status="iteration_blocked_preflight",
            iteration_decision="block_until_preflight_repaired",
            failure_stage="preflight_output_dir_missing",
            error_message=output_error,
        )

    collision = _existing_output_collision(paths)
    if collision is not None:
        return _result_without_artifacts(
            common,
            iteration_status="iteration_blocked_preflight",
            iteration_decision="block_until_preflight_repaired",
            failure_stage="preflight_output_collision",
            error_message="local asset bounded smoke iteration output already exists: "
            + collision,
        )

    early_overlap = _early_overlap_error(common)
    if early_overlap is not None:
        return _result_without_artifacts(
            common,
            iteration_status="iteration_blocked_preflight",
            iteration_decision="block_until_preflight_repaired",
            failure_stage="preflight_output_overlap",
            error_message=early_overlap,
        )

    promotion_state = _validate_promotion_output(common["promotion_output_dir"])
    promotion_overlap = _promotion_overlap_error(
        common,
        promotion_state.get("decision"),
    )
    if promotion_overlap is not None:
        return _result_without_artifacts(
            common,
            iteration_status="iteration_blocked_preflight",
            iteration_decision="block_until_preflight_repaired",
            failure_stage="preflight_upstream_output_overlap",
            error_message=promotion_overlap,
        )

    readiness_state = _validate_readiness_report(
        common,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
    )
    limit_blocker = _limit_blocker(
        max_smoke_files,
        max_smoke_bytes,
        max_smoke_depth,
    )
    preflight_blockers = []
    preflight_blockers.extend(_path_preflight_blockers(common))
    if readiness_state["valid"] is not True:
        preflight_blockers.extend(readiness_state["blockers"])
    if limit_blocker is not None:
        preflight_blockers.append(limit_blocker)
    preflight_blockers.extend(
        _candidate_matches_promotion_blockers(common, promotion_state.get("decision"))
    )

    signoff_valid = _signoff_valid(human_signoff_id, human_signoff_phrase)
    signoff_payload = _signoff_payload(
        common,
        human_signoff_id=human_signoff_id,
        human_signoff_phrase=human_signoff_phrase,
        signoff_valid=signoff_valid,
    )
    _ensure_control_dir(paths["control_output_dir"])
    _write_json_exclusive(paths["signoff_path"], signoff_payload)

    if preflight_blockers:
        return _write_blocked_artifacts(
            common,
            paths,
            signoff_payload=signoff_payload,
            promotion_state=promotion_state,
            human_signoff_valid=signoff_valid,
            iteration_status="iteration_blocked_preflight",
            iteration_decision="block_until_preflight_repaired",
            blockers=preflight_blockers,
            smoke_payload=None,
        )

    if promotion_state["validated"] is not True:
        return _write_blocked_artifacts(
            common,
            paths,
            signoff_payload=signoff_payload,
            promotion_state=promotion_state,
            human_signoff_valid=signoff_valid,
            iteration_status="iteration_blocked_promotion_gate",
            iteration_decision="block_until_promotion_gate_repaired",
            blockers=promotion_state["blockers"],
            smoke_payload=None,
        )

    if not signoff_valid:
        return _write_blocked_artifacts(
            common,
            paths,
            signoff_payload=signoff_payload,
            promotion_state=promotion_state,
            human_signoff_valid=False,
            iteration_status="iteration_blocked_signoff",
            iteration_decision="block_until_valid_human_signoff",
            blockers=[
                _blocker(
                    "invalid_human_signoff",
                    "human signoff id or phrase did not satisfy bounded iteration gate",
                )
            ],
            smoke_payload=None,
        )

    paths["smoke_output_dir"].mkdir(exist_ok=False)
    smoke_result = _run_existing_human_smoke_launcher(
        common,
        human_signoff_id=human_signoff_id,
    )
    smoke_payload = dict(smoke_result.payload)
    smoke_launcher_invoked = True
    smoke_complete = bool(smoke_result.complete)
    status = (
        "iteration_completed" if smoke_complete else "iteration_failed_smoke_run"
    )
    decision = (
        "bounded_smoke_iteration_completed"
        if smoke_complete
        else "block_until_smoke_run_repaired"
    )
    blockers = []
    if not smoke_complete:
        blockers.append(
            _blocker(
                "delegated_smoke_run_failed",
                "existing human-approved smoke launcher did not complete",
                failure_stage=smoke_payload.get("failure_stage"),
            )
        )
    return _write_final_artifacts(
        common,
        paths,
        signoff_payload=signoff_payload,
        promotion_state=promotion_state,
        human_signoff_valid=True,
        iteration_status=status,
        iteration_decision=decision,
        blockers=blockers,
        smoke_payload=smoke_payload,
        smoke_launcher_invoked=smoke_launcher_invoked,
        smoke_run_complete=smoke_complete,
        scan_complete=bool(smoke_payload.get("scan_complete")),
        bounded_smoke_iteration_allowed=True,
        bounded_smoke_iteration_performed=smoke_complete,
    )


def _run_existing_human_smoke_launcher(
    common: dict[str, object],
    *,
    human_signoff_id: str,
):
    from kernel.personal_ai.local_launcher import run_local_asset_human_smoke_launcher

    previous_scan_value = common["previous_scan_output_dir"]
    return run_local_asset_human_smoke_launcher(
        Path(str(common["candidate_input_dir"])),
        Path(str(common["smoke_output_dir"])),
        Path(str(common["readiness_report"])),
        human_approval_id=human_signoff_id,
        human_approval_phrase=HUMAN_SMOKE_APPROVAL_PHRASE,
        recursive=bool(common["recursive"]),
        include_hidden=bool(common["include_hidden"]),
        project_id=common["project_id"]
        if isinstance(common["project_id"], str)
        else None,
        max_smoke_files=int(common["max_smoke_files"]),
        max_smoke_bytes=int(common["max_smoke_bytes"]),
        max_smoke_depth=int(common["max_smoke_depth"]),
        previous_scan_output_dir=None
        if previous_scan_value is None
        else Path(str(previous_scan_value)),
    )


def _write_blocked_artifacts(
    common: dict[str, object],
    paths: dict[str, Path],
    *,
    signoff_payload: dict[str, object],
    promotion_state: dict[str, object],
    human_signoff_valid: bool,
    iteration_status: str,
    iteration_decision: str,
    blockers: list[dict[str, object]],
    smoke_payload: dict[str, object] | None,
) -> LocalAssetBoundedSmokeIterationResult:
    return _write_final_artifacts(
        common,
        paths,
        signoff_payload=signoff_payload,
        promotion_state=promotion_state,
        human_signoff_valid=human_signoff_valid,
        iteration_status=iteration_status,
        iteration_decision=iteration_decision,
        blockers=blockers,
        smoke_payload=smoke_payload,
        smoke_launcher_invoked=False,
        smoke_run_complete=False,
        scan_complete=False,
        bounded_smoke_iteration_allowed=False,
        bounded_smoke_iteration_performed=False,
    )


def _write_final_artifacts(
    common: dict[str, object],
    paths: dict[str, Path],
    *,
    signoff_payload: dict[str, object],
    promotion_state: dict[str, object],
    human_signoff_valid: bool,
    iteration_status: str,
    iteration_decision: str,
    blockers: list[dict[str, object]],
    smoke_payload: dict[str, object] | None,
    smoke_launcher_invoked: bool,
    smoke_run_complete: bool,
    scan_complete: bool,
    bounded_smoke_iteration_allowed: bool,
    bounded_smoke_iteration_performed: bool,
) -> LocalAssetBoundedSmokeIterationResult:
    promotion_decision = _dict_or_empty(promotion_state.get("decision"))
    admission = _admission_payload(
        common,
        promotion_state=promotion_state,
        human_signoff_valid=human_signoff_valid,
        admitted=bounded_smoke_iteration_allowed,
        blockers=blockers,
        bounded_smoke_iteration_allowed=bounded_smoke_iteration_allowed,
        bounded_smoke_iteration_performed=bounded_smoke_iteration_performed,
    )
    _write_json_exclusive(paths["admission_path"], admission)
    result_payload = _result_payload(
        common,
        promotion_state=promotion_state,
        signoff_payload=signoff_payload,
        admission=admission,
        iteration_status=iteration_status,
        iteration_decision=iteration_decision,
        blockers=blockers,
        smoke_payload=smoke_payload,
        smoke_launcher_invoked=smoke_launcher_invoked,
        smoke_run_complete=smoke_run_complete,
        scan_complete=scan_complete,
        bounded_smoke_iteration_allowed=bounded_smoke_iteration_allowed,
        bounded_smoke_iteration_performed=bounded_smoke_iteration_performed,
    )
    _write_json_exclusive(paths["result_path"], result_payload)
    summary = _summary_markdown(
        result_payload,
        promotion_gate_status=promotion_decision.get("promotion_gate_status"),
        promotion_decision=promotion_decision.get("promotion_decision"),
    )
    checklist = _human_review_checklist_markdown()
    _write_text_exclusive(paths["summary_path"], summary)
    _write_text_exclusive(paths["checklist_path"], checklist)
    manifest = _manifest_payload(
        common,
        paths,
        result_payload=result_payload,
        iteration_status=iteration_status,
        iteration_decision=iteration_decision,
        bounded_smoke_iteration_performed=bounded_smoke_iteration_performed,
    )
    _write_json_exclusive(paths["manifest_path"], manifest)
    artifact_index = _artifact_index_payload(paths)
    _write_json_exclusive(paths["artifact_index_path"], artifact_index)
    artifact_index_manifest = _artifact_index_manifest_payload(
        common,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths["artifact_index_manifest_path"],
        artifact_index_manifest,
    )
    cli_payload = dict(result_payload)
    cli_payload.update(
        {
            "complete": iteration_status == "iteration_completed",
            "local_asset_bounded_smoke_iteration_result_path": paths[
                "result_path"
            ].as_posix(),
            "local_asset_bounded_smoke_iteration_manifest_path": paths[
                "manifest_path"
            ].as_posix(),
            "local_asset_bounded_smoke_iteration_summary_path": paths[
                "summary_path"
            ].as_posix(),
            "local_asset_bounded_smoke_iteration_human_review_checklist_path": paths[
                "checklist_path"
            ].as_posix(),
            "local_asset_bounded_smoke_iteration_signoff_path": paths[
                "signoff_path"
            ].as_posix(),
            "local_asset_bounded_smoke_iteration_admission_path": paths[
                "admission_path"
            ].as_posix(),
            "artifact_index_path": paths["artifact_index_path"].as_posix(),
            "artifact_index_manifest_path": paths[
                "artifact_index_manifest_path"
            ].as_posix(),
        }
    )
    return LocalAssetBoundedSmokeIterationResult(
        promotion_output_dir=Path(str(common["promotion_output_dir"])),
        candidate_input_dir=Path(str(common["candidate_input_dir"])),
        readiness_report=Path(str(common["readiness_report"])),
        output_dir=paths["output_dir"],
        control_output_dir=paths["control_output_dir"],
        smoke_output_dir=paths["smoke_output_dir"],
        result_path=paths["result_path"],
        manifest_path=paths["manifest_path"],
        summary_path=paths["summary_path"],
        human_review_checklist_path=paths["checklist_path"],
        signoff_path=paths["signoff_path"],
        admission_path=paths["admission_path"],
        artifact_index_path=paths["artifact_index_path"],
        artifact_index_manifest_path=paths["artifact_index_manifest_path"],
        complete=iteration_status == "iteration_completed",
        iteration_status=iteration_status,
        iteration_decision=iteration_decision,
        payload=cli_payload,
    )


def _result_without_artifacts(
    common: dict[str, object],
    *,
    iteration_status: str,
    iteration_decision: str,
    failure_stage: str,
    error_message: str,
) -> LocalAssetBoundedSmokeIterationResult:
    payload = _base_payload(common)
    payload.update(
        {
            "complete": False,
            "artifacts_written": False,
            "iteration_status": iteration_status,
            "iteration_decision": iteration_decision,
            "promotion_validated": False,
            "human_signoff_valid": False,
            "bounded_smoke_iteration_allowed": False,
            "bounded_smoke_iteration_performed": False,
            "smoke_launcher_invoked": False,
            "smoke_run_complete": False,
            "scan_complete": False,
            "failure_stage": failure_stage,
            "error_type": "ValueError",
            "error_message": error_message,
            "iteration_blockers": [
                _blocker("preflight_failure", error_message)
            ],
            "next_allowed_action": "repair_bounded_smoke_iteration_preflight",
            "local_asset_bounded_smoke_iteration_result_path": None,
            "local_asset_bounded_smoke_iteration_manifest_path": None,
            "local_asset_bounded_smoke_iteration_summary_path": None,
            "local_asset_bounded_smoke_iteration_human_review_checklist_path": None,
            "local_asset_bounded_smoke_iteration_signoff_path": None,
            "local_asset_bounded_smoke_iteration_admission_path": None,
            "artifact_index_path": None,
            "artifact_index_manifest_path": None,
        }
    )
    return LocalAssetBoundedSmokeIterationResult(
        promotion_output_dir=Path(str(common["promotion_output_dir"])),
        candidate_input_dir=Path(str(common["candidate_input_dir"])),
        readiness_report=Path(str(common["readiness_report"])),
        output_dir=Path(str(common["output_dir"])),
        control_output_dir=Path(str(common["control_output_dir"])),
        smoke_output_dir=Path(str(common["smoke_output_dir"])),
        result_path=None,
        manifest_path=None,
        summary_path=None,
        human_review_checklist_path=None,
        signoff_path=None,
        admission_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        iteration_status=iteration_status,
        iteration_decision=iteration_decision,
        payload=payload,
    )


def _common_payload(
    *,
    promotion_output_dir: Path,
    candidate_input_dir: Path,
    readiness_report: Path,
    output_dir: Path,
    control_output_dir: Path,
    smoke_output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    previous_scan_output_dir: Path | None,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> dict[str, object]:
    return {
        "promotion_output_dir": promotion_output_dir.as_posix(),
        "candidate_input_dir": candidate_input_dir.as_posix(),
        "readiness_report": readiness_report.as_posix(),
        "output_dir": output_dir.as_posix(),
        "iteration_output_dir": output_dir.as_posix(),
        "control_output_dir": control_output_dir.as_posix(),
        "smoke_output_dir": smoke_output_dir.as_posix(),
        "project_id": project_id,
        "recursive": bool(recursive),
        "include_hidden": bool(include_hidden),
        "previous_scan_output_dir": None
        if previous_scan_output_dir is None
        else previous_scan_output_dir.as_posix(),
        "max_smoke_files": max_smoke_files,
        "max_smoke_bytes": max_smoke_bytes,
        "max_smoke_depth": max_smoke_depth,
        "required_human_approval": True,
    }


def _base_payload(common: dict[str, object]) -> dict[str, object]:
    payload = {
        "result_type": _RESULT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "promotion_output_dir": common["promotion_output_dir"],
        "candidate_input_dir": common["candidate_input_dir"],
        "readiness_report": common["readiness_report"],
        "output_dir": common["output_dir"],
        "control_output_dir": common["control_output_dir"],
        "smoke_output_dir": common["smoke_output_dir"],
        "project_id": common["project_id"],
        "max_smoke_files": common["max_smoke_files"],
        "max_smoke_bytes": common["max_smoke_bytes"],
        "max_smoke_depth": common["max_smoke_depth"],
        "recursive": common["recursive"],
        "include_hidden": common["include_hidden"],
        "previous_scan_output_dir": common["previous_scan_output_dir"],
        "required_human_approval": True,
    }
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _result_payload(
    common: dict[str, object],
    *,
    promotion_state: dict[str, object],
    signoff_payload: dict[str, object],
    admission: dict[str, object],
    iteration_status: str,
    iteration_decision: str,
    blockers: list[dict[str, object]],
    smoke_payload: dict[str, object] | None,
    smoke_launcher_invoked: bool,
    smoke_run_complete: bool,
    scan_complete: bool,
    bounded_smoke_iteration_allowed: bool,
    bounded_smoke_iteration_performed: bool,
) -> dict[str, object]:
    promotion_decision = _dict_or_empty(promotion_state.get("decision"))
    payload = _base_payload(common)
    payload.update(
        {
            "iteration_status": iteration_status,
            "iteration_decision": iteration_decision,
            "promotion_gate_status": promotion_decision.get(
                "promotion_gate_status"
            ),
            "promotion_decision": promotion_decision.get("promotion_decision"),
            "promotion_validated": promotion_state["validated"],
            "human_signoff_valid": signoff_payload["signoff_valid"],
            "bounded_smoke_iteration_allowed": bounded_smoke_iteration_allowed,
            "bounded_smoke_iteration_performed": bounded_smoke_iteration_performed,
            "smoke_launcher_invoked": smoke_launcher_invoked,
            "smoke_run_complete": smoke_run_complete,
            "scan_complete": scan_complete,
            "smoke_payload_summary": _smoke_payload_summary(smoke_payload),
            "promotion_decision_summary": _promotion_decision_summary(
                promotion_decision,
                promotion_state,
            ),
            "admission_summary": {
                "admitted": admission["admitted"],
                "admission_blocker_count": len(admission["admission_blockers"]),
                "bounded_smoke_iteration_allowed": admission[
                    "bounded_smoke_iteration_allowed"
                ],
                "bounded_smoke_iteration_performed": admission[
                    "bounded_smoke_iteration_performed"
                ],
            },
            "signoff_summary": {
                "human_signoff_id": signoff_payload["human_signoff_id"],
                "human_signoff_valid": signoff_payload["signoff_valid"],
                "human_signoff_phrase_sha256_present": True,
                "human_signoff_phrase_plaintext_persisted": False,
                "human_signoff_phrase_stored": False,
            },
            "blocker_summary": _blocker_summary(blockers),
            "iteration_blockers": blockers,
            "artifacts_written": True,
            "output_write_scope": "iteration_output_dir_only",
            "smoke_output_write_scope": "new_smoke_subdirectory_only"
            if smoke_launcher_invoked
            else "not_written",
            "required_human_approval": True,
            "next_allowed_action": _NEXT_ACTION,
        }
    )
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _admission_payload(
    common: dict[str, object],
    *,
    promotion_state: dict[str, object],
    human_signoff_valid: bool,
    admitted: bool,
    blockers: list[dict[str, object]],
    bounded_smoke_iteration_allowed: bool,
    bounded_smoke_iteration_performed: bool,
) -> dict[str, object]:
    promotion_decision = _dict_or_empty(promotion_state.get("decision"))
    payload = {
        "admission_type": _ADMISSION_TYPE,
        "authority": _AUTHORITY,
        "admitted": admitted,
        "admission_blockers": blockers,
        "promotion_gate_status": promotion_decision.get("promotion_gate_status"),
        "promotion_decision": promotion_decision.get("promotion_decision"),
        "promotion_decision_sha256": promotion_state.get("decision_sha256"),
        "promotion_manifest_sha256": promotion_state.get("manifest_sha256"),
        "human_signoff_valid": human_signoff_valid,
        "candidate_input_dir": common["candidate_input_dir"],
        "readiness_report": common["readiness_report"],
        "iteration_output_dir": common["output_dir"],
        "smoke_output_dir": common["smoke_output_dir"],
        "control_output_dir": common["control_output_dir"],
        "recursive": common["recursive"],
        "include_hidden": common["include_hidden"],
        "max_smoke_files": common["max_smoke_files"],
        "max_smoke_bytes": common["max_smoke_bytes"],
        "max_smoke_depth": common["max_smoke_depth"],
        "previous_scan_output_dir": common["previous_scan_output_dir"],
        "bounded_smoke_iteration_allowed": bounded_smoke_iteration_allowed,
        "bounded_smoke_iteration_performed": bounded_smoke_iteration_performed,
        "required_human_approval": True,
        "next_allowed_action": _ADMISSION_NEXT_ACTION,
    }
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _signoff_payload(
    common: dict[str, object],
    *,
    human_signoff_id: str,
    human_signoff_phrase: str,
    signoff_valid: bool,
) -> dict[str, object]:
    return {
        "signoff_type": _SIGNOFF_TYPE,
        "authority": "human_signoff_required",
        "human_signoff_id": human_signoff_id,
        "human_signoff_phrase_sha256": sha256(
            human_signoff_phrase.encode("utf-8")
        ).hexdigest(),
        "human_signoff_phrase_plaintext_persisted": False,
        "human_signoff_phrase_stored": False,
        "required_phrase": BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
        "signoff_valid": signoff_valid,
        "promotion_output_dir": common["promotion_output_dir"],
        "candidate_input_dir": common["candidate_input_dir"],
        "readiness_report": common["readiness_report"],
        "output_dir": common["output_dir"],
        "project_id": common["project_id"],
        "required_human_approval": True,
        "next_allowed_action": "bounded_smoke_iteration_admission_review",
    }


def _signoff_valid(human_signoff_id: str, human_signoff_phrase: str) -> bool:
    if not isinstance(human_signoff_id, str) or not human_signoff_id:
        return False
    if human_signoff_id == BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE:
        return False
    return human_signoff_phrase == BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE


def _iteration_paths(output_dir: Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    control_path = output_path / _CONTROL_DIR_NAME
    smoke_path = output_path / _SMOKE_DIR_NAME
    return {
        "output_dir": output_path,
        "control_output_dir": control_path,
        "smoke_output_dir": smoke_path,
        "signoff_path": control_path
        / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SIGNOFF_FILE,
        "admission_path": control_path
        / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE,
        "result_path": output_path / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_RESULT_FILE,
        "manifest_path": output_path
        / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_MANIFEST_FILE,
        "summary_path": output_path / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE,
        "checklist_path": output_path
        / LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE,
        "artifact_index_path": output_path / _ARTIFACT_INDEX_FILE,
        "artifact_index_manifest_path": output_path / _ARTIFACT_INDEX_MANIFEST_FILE,
    }


def _existing_output_collision(paths: dict[str, Path]) -> str | None:
    root_paths = {
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_RESULT_FILE: paths["result_path"],
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_MANIFEST_FILE: paths["manifest_path"],
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SUMMARY_FILE: paths["summary_path"],
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_CHECKLIST_FILE: paths["checklist_path"],
        _ARTIFACT_INDEX_FILE: paths["artifact_index_path"],
        _ARTIFACT_INDEX_MANIFEST_FILE: paths["artifact_index_manifest_path"],
    }
    for name, path in sorted(root_paths.items()):
        if path.exists():
            return name
    control_path = paths["control_output_dir"]
    if control_path.exists() and (
        not control_path.is_dir() or control_path.is_symlink()
    ):
        return _CONTROL_DIR_NAME
    control_files = {
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_SIGNOFF_FILE: paths["signoff_path"],
        LOCAL_ASSET_BOUNDED_SMOKE_ITERATION_ADMISSION_FILE: paths["admission_path"],
    }
    for name, path in sorted(control_files.items()):
        if path.exists():
            return _CONTROL_DIR_NAME + "/" + name
    if paths["smoke_output_dir"].exists():
        return _SMOKE_DIR_NAME + "/"
    return None


def _real_existing_dir_error(path_value: object, label: str) -> str | None:
    path = Path(str(path_value))
    if not path.exists():
        return label + " is missing"
    if not path.is_dir():
        return label + " is not a directory"
    if path.is_symlink():
        return label + " must not be a symlink"
    return None


def _real_existing_file_error(path_value: object, label: str) -> str | None:
    path = Path(str(path_value))
    if not path.exists():
        return label + " is missing"
    if not path.is_file():
        return label + " is not a file"
    if path.is_symlink():
        return label + " must not be a symlink"
    return None


def _early_overlap_error(common: dict[str, object]) -> str | None:
    output_path = Path(str(common["output_dir"]))
    for field_name, label in (
        ("candidate_input_dir", "candidate_input_dir"),
        ("promotion_output_dir", "promotion_output_dir"),
    ):
        overlap = _existing_dir_overlap_error(
            Path(str(common[field_name])),
            output_path,
            left_label=label,
            right_label="output_dir",
        )
        if overlap is not None:
            return overlap
    return None


def _promotion_overlap_error(
    common: dict[str, object],
    decision: object,
) -> str | None:
    output_path = Path(str(common["output_dir"]))
    decision_payload = _dict_or_empty(decision)
    review_output_dir = decision_payload.get("review_output_dir")
    if isinstance(review_output_dir, str) and review_output_dir:
        overlap = _existing_dir_overlap_error(
            Path(review_output_dir),
            output_path,
            left_label="review_output_dir",
            right_label="output_dir",
        )
        if overlap is not None:
            return overlap
    smoke_output_dir = _first_text(
        decision_payload.get("smoke_output_dir"),
        _dict_or_empty(decision_payload.get("smoke_run_summary")).get(
            "smoke_output_dir"
        ),
    )
    if smoke_output_dir is not None:
        overlap = _existing_dir_overlap_error(
            Path(smoke_output_dir),
            output_path,
            left_label="smoke_output_dir",
            right_label="output_dir",
        )
        if overlap is not None:
            return overlap
    previous_candidate_dir = _first_text(
        _dict_or_empty(decision_payload.get("readiness_summary")).get(
            "candidate_input_dir"
        )
    )
    if previous_candidate_dir is not None and _path_is_inside(
        output_path,
        Path(previous_candidate_dir),
    ):
        return "output_dir must not be inside previous smoke candidate input dir"
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


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _path_preflight_blockers(common: dict[str, object]) -> list[dict[str, object]]:
    blockers = []
    for field_name, label, validator in (
        ("promotion_output_dir", "promotion_output_dir", _real_existing_dir_error),
        ("candidate_input_dir", "candidate_input_dir", _real_existing_dir_error),
        ("readiness_report", "readiness_report", _real_existing_file_error),
    ):
        error = validator(common[field_name], label)
        if error is not None:
            blockers.append(_blocker(label + "_invalid", error))
    return blockers


def _limit_blocker(
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> dict[str, object] | None:
    for name, value in (
        ("max_smoke_files", max_smoke_files),
        ("max_smoke_bytes", max_smoke_bytes),
        ("max_smoke_depth", max_smoke_depth),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            return _blocker(name + "_invalid", name + " must be an integer")
        if value < 0:
            return _blocker(name + "_invalid", name + " must be non-negative")
    return None


def _validate_readiness_report(
    common: dict[str, object],
    *,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> dict[str, object]:
    readiness_path = Path(str(common["readiness_report"]))
    path_error = _real_existing_file_error(readiness_path, "readiness_report")
    if path_error is not None:
        return {
            "valid": False,
            "payload": {},
            "sha256": None,
            "blockers": [_blocker("readiness_report_invalid", path_error)],
        }
    try:
        payload = _read_json_file(readiness_path, "readiness_report")
    except ValueError as error:
        return {
            "valid": False,
            "payload": {},
            "sha256": sha256_file(readiness_path),
            "blockers": [
                _blocker("readiness_report_invalid", str(error))
            ],
        }
    blockers = []
    if payload.get("report_type") != _READINESS_REPORT_TYPE:
        blockers.append(
            _blocker("readiness_report_type_mismatch", "readiness report type mismatch")
        )
    if payload.get("execution_capability") != _READINESS_EXECUTION_CAPABILITY:
        blockers.append(
            _blocker(
                "readiness_execution_capability_mismatch",
                "readiness report execution capability mismatch",
            )
        )
    if payload.get("metadata_only") is not True:
        blockers.append(
            _blocker("readiness_metadata_only_missing", "readiness report not metadata-only")
        )
    readiness_candidate = payload.get("candidate_input_dir")
    if not isinstance(readiness_candidate, str) or not readiness_candidate:
        blockers.append(
            _blocker(
                "readiness_candidate_input_dir_missing",
                "readiness report candidate_input_dir is missing",
            )
        )
    elif not _same_existing_path(
        Path(str(common["candidate_input_dir"])),
        Path(readiness_candidate),
    ):
        blockers.append(
            _blocker(
                "readiness_candidate_input_dir_mismatch",
                "candidate_input_dir does not match readiness report",
            )
        )
    if payload.get("recursive") is not bool(common["recursive"]):
        blockers.append(
            _blocker("readiness_recursive_mismatch", "recursive flag mismatch")
        )
    if payload.get("include_hidden") is not bool(common["include_hidden"]):
        blockers.append(
            _blocker("readiness_include_hidden_mismatch", "include_hidden flag mismatch")
        )
    if payload.get("readiness_status") not in _READY_READINESS_STATUSES:
        blockers.append(
            _blocker(
                "readiness_status_not_ready",
                "readiness status does not allow bounded smoke iteration",
                value=payload.get("readiness_status"),
            )
        )
    if payload.get("readiness_decision") != "allow_human_review_for_future_smoke":
        blockers.append(
            _blocker(
                "readiness_decision_not_allowed",
                "readiness decision does not allow future smoke",
                value=payload.get("readiness_decision"),
            )
        )
    if payload.get("required_human_approval") is not True:
        blockers.append(
            _blocker(
                "readiness_human_approval_missing",
                "readiness report must require human approval",
            )
        )
    readiness_max_total_bytes = payload.get("max_total_bytes")
    if (
        isinstance(readiness_max_total_bytes, int)
        and max_smoke_bytes > readiness_max_total_bytes
    ):
        blockers.append(
            _blocker(
                "max_smoke_bytes_exceeds_readiness",
                "max_smoke_bytes exceeds readiness max_total_bytes",
            )
        )
    readiness_max_depth = payload.get("max_depth")
    if isinstance(readiness_max_depth, int) and max_smoke_depth > readiness_max_depth:
        blockers.append(
            _blocker(
                "max_smoke_depth_exceeds_readiness",
                "max_smoke_depth exceeds readiness max_depth",
            )
        )
    return {
        "valid": not blockers,
        "payload": payload,
        "sha256": sha256_file(readiness_path),
        "blockers": blockers,
    }


def _validate_promotion_output(promotion_output_dir: object) -> dict[str, object]:
    promotion_path = Path(str(promotion_output_dir))
    dir_error = _real_existing_dir_error(promotion_path, "promotion_output_dir")
    paths = {
        "decision": promotion_path / _PROMOTION_DECISION_FILE,
        "manifest": promotion_path / _PROMOTION_MANIFEST_FILE,
        "artifact_index": promotion_path / _ARTIFACT_INDEX_FILE,
        "artifact_index_manifest": promotion_path / _ARTIFACT_INDEX_MANIFEST_FILE,
        "summary": promotion_path / _PROMOTION_SUMMARY_FILE,
        "checklist": promotion_path / _PROMOTION_CHECKLIST_FILE,
    }
    blockers = []
    if dir_error is not None:
        blockers.append(_blocker("promotion_output_dir_invalid", dir_error))
        return _promotion_state(
            validated=False,
            paths=paths,
            decision={},
            manifest={},
            artifact_index={},
            artifact_index_manifest={},
            blockers=blockers,
        )
    loaded = {}
    for key in ("decision", "manifest", "artifact_index", "artifact_index_manifest"):
        path = paths[key]
        file_error = _real_existing_file_error(path, key)
        if file_error is not None:
            blockers.append(_blocker("promotion_" + key + "_invalid", file_error))
            loaded[key] = {}
            continue
        try:
            loaded[key] = _read_json_file(path, key)
        except ValueError as error:
            blockers.append(_blocker("promotion_" + key + "_invalid", str(error)))
            loaded[key] = {}
    decision = _dict_or_empty(loaded.get("decision"))
    manifest = _dict_or_empty(loaded.get("manifest"))
    artifact_index = _dict_or_empty(loaded.get("artifact_index"))
    artifact_index_manifest = _dict_or_empty(loaded.get("artifact_index_manifest"))
    blockers.extend(_promotion_decision_blockers(decision))
    blockers.extend(_promotion_manifest_blockers(paths, manifest))
    blockers.extend(_promotion_artifact_index_blockers(artifact_index))
    blockers.extend(
        _promotion_artifact_index_manifest_blockers(
            paths,
            artifact_index_manifest,
        )
    )
    return _promotion_state(
        validated=not blockers,
        paths=paths,
        decision=decision,
        manifest=manifest,
        artifact_index=artifact_index,
        artifact_index_manifest=artifact_index_manifest,
        blockers=blockers,
    )


def _promotion_state(
    *,
    validated: bool,
    paths: dict[str, Path],
    decision: dict[str, object],
    manifest: dict[str, object],
    artifact_index: dict[str, object],
    artifact_index_manifest: dict[str, object],
    blockers: list[dict[str, object]],
) -> dict[str, object]:
    decision_path = paths["decision"]
    manifest_path = paths["manifest"]
    return {
        "validated": validated,
        "paths": {key: path.as_posix() for key, path in paths.items()},
        "decision": decision,
        "manifest": manifest,
        "artifact_index": artifact_index,
        "artifact_index_manifest": artifact_index_manifest,
        "decision_sha256": _sha256_if_file(decision_path),
        "manifest_sha256": _sha256_if_file(manifest_path),
        "artifact_index_sha256": _sha256_if_file(paths["artifact_index"]),
        "artifact_index_manifest_sha256": _sha256_if_file(
            paths["artifact_index_manifest"]
        ),
        "blockers": sorted(blockers, key=lambda item: str(item["blocker_role"])),
    }


def _promotion_decision_blockers(
    decision: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    required_values = {
        "decision_type": _PROMOTION_DECISION_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _PROMOTION_EXECUTION_CAPABILITY,
        "promotion_gate_status": "promotion_candidate",
        "promotion_decision": "allow_next_bounded_smoke_iteration",
        "next_bounded_smoke_iteration_allowed": True,
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "required_human_signoff": True,
        "required_human_approval": True,
        "review_packet_status": "review_ready",
        "review_recommended_human_decision": (
            "approve_next_bounded_smoke_iteration"
        ),
    }
    for field_name, expected in required_values.items():
        if decision.get(field_name) != expected:
            blockers.append(
                _blocker(
                    "promotion_decision_" + field_name + "_mismatch",
                    "promotion decision field mismatch",
                    field=field_name,
                    expected=expected,
                    actual=decision.get(field_name),
                )
            )
    blocker_count = _first_int(
        decision.get("promotion_blocker_count"),
        _dict_or_empty(decision.get("blocker_summary")).get("promotion_blocker_count"),
        default=None,
    )
    if blocker_count != 0:
        blockers.append(
            _blocker(
                "promotion_blocker_count_nonzero",
                "promotion blocker count must be zero",
                value=blocker_count,
            )
        )
    promotion_blockers = decision.get("promotion_blockers")
    if promotion_blockers != []:
        blockers.append(
            _blocker(
                "promotion_blockers_present",
                "promotion blockers must be empty",
                value=promotion_blockers,
            )
        )
    return blockers


def _promotion_manifest_blockers(
    paths: dict[str, Path],
    manifest: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if manifest.get("manifest_type") != _PROMOTION_MANIFEST_TYPE:
        blockers.append(
            _blocker("promotion_manifest_type_mismatch", "promotion manifest type mismatch")
        )
    expected_hashes = (
        ("decision_sha256", paths["decision"], True),
        ("summary_sha256", paths["summary"], False),
        ("human_signoff_checklist_sha256", paths["checklist"], False),
    )
    for field_name, path, required in expected_hashes:
        if not path.exists():
            if required:
                blockers.append(
                    _blocker(
                        "promotion_manifest_" + field_name + "_missing_source",
                        "promotion manifest source artifact is missing",
                    )
                )
            continue
        if not path.is_file() or path.is_symlink():
            blockers.append(
                _blocker(
                    "promotion_manifest_" + field_name + "_untrusted_source",
                    "promotion manifest source artifact is untrusted",
                )
            )
            continue
        if manifest.get(field_name) != sha256_file(path):
            blockers.append(
                _blocker(
                    "promotion_manifest_" + field_name + "_hash_mismatch",
                    "promotion manifest hash mismatch",
                )
            )
    return blockers


def _promotion_artifact_index_blockers(
    artifact_index: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if artifact_index.get("index_type") != _PROMOTION_INDEX_TYPE:
        blockers.append(
            _blocker(
                "promotion_artifact_index_type_mismatch",
                "promotion artifact index type mismatch",
            )
        )
    entries = artifact_index.get("entries")
    if not isinstance(entries, list):
        blockers.append(
            _blocker(
                "promotion_artifact_index_entries_malformed",
                "promotion artifact index entries are malformed",
            )
        )
        return blockers
    roles = {entry.get("artifact_role") for entry in entries if isinstance(entry, dict)}
    for role in (
        "local_asset_smoke_promotion_decision",
        "local_asset_smoke_promotion_gate_manifest",
    ):
        if role not in roles:
            blockers.append(
                _blocker(
                    "promotion_artifact_index_missing_" + role,
                    "promotion artifact index missing required role",
                )
            )
    return blockers


def _promotion_artifact_index_manifest_blockers(
    paths: dict[str, Path],
    artifact_index_manifest: dict[str, object],
) -> list[dict[str, object]]:
    blockers = []
    if artifact_index_manifest.get("manifest_type") != _PROMOTION_INDEX_MANIFEST_TYPE:
        blockers.append(
            _blocker(
                "promotion_artifact_index_manifest_type_mismatch",
                "promotion artifact index manifest type mismatch",
            )
        )
    artifact_index_path = paths["artifact_index"]
    if (
        artifact_index_path.exists()
        and artifact_index_path.is_file()
        and not artifact_index_path.is_symlink()
        and artifact_index_manifest.get("artifact_index_sha256")
        != sha256_file(artifact_index_path)
    ):
        blockers.append(
            _blocker(
                "promotion_artifact_index_manifest_hash_mismatch",
                "promotion artifact index manifest hash mismatch",
            )
        )
    return blockers


def _candidate_matches_promotion_blockers(
    common: dict[str, object],
    decision: object,
) -> list[dict[str, object]]:
    decision_payload = _dict_or_empty(decision)
    candidate_from_promotion = _first_text(
        _dict_or_empty(decision_payload.get("readiness_summary")).get(
            "candidate_input_dir"
        )
    )
    if candidate_from_promotion is None:
        return []
    if _same_existing_path(
        Path(str(common["candidate_input_dir"])),
        Path(candidate_from_promotion),
    ):
        return []
    return [
        _blocker(
            "promotion_candidate_input_dir_mismatch",
            "candidate_input_dir does not match promotion decision readiness summary",
        )
    ]


def _manifest_payload(
    common: dict[str, object],
    paths: dict[str, Path],
    *,
    result_payload: dict[str, object],
    iteration_status: str,
    iteration_decision: str,
    bounded_smoke_iteration_performed: bool,
) -> dict[str, object]:
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "result_path": paths["result_path"].as_posix(),
        "summary_path": paths["summary_path"].as_posix(),
        "human_review_checklist_path": paths["checklist_path"].as_posix(),
        "signoff_path": paths["signoff_path"].as_posix(),
        "admission_path": paths["admission_path"].as_posix(),
        "result_sha256": sha256_file(paths["result_path"]),
        "summary_sha256": sha256_file(paths["summary_path"]),
        "human_review_checklist_sha256": sha256_file(paths["checklist_path"]),
        "signoff_sha256": sha256_file(paths["signoff_path"]),
        "admission_sha256": sha256_file(paths["admission_path"]),
        "smoke_output_artifact_index_path": None,
        "smoke_output_artifact_index_sha256": None,
        "source_artifacts": _source_artifacts(common),
        "iteration_status": iteration_status,
        "iteration_decision": iteration_decision,
        "bounded_smoke_iteration_performed": bounded_smoke_iteration_performed,
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ACTION,
    }
    smoke_index = paths["smoke_output_dir"] / _ARTIFACT_INDEX_FILE
    if smoke_index.exists() and smoke_index.is_file() and not smoke_index.is_symlink():
        payload["smoke_output_artifact_index_path"] = smoke_index.as_posix()
        payload["smoke_output_artifact_index_sha256"] = sha256_file(smoke_index)
    payload.update(_BOUNDARY_FLAGS)
    payload["iteration_blocker_count"] = len(result_payload["iteration_blockers"])
    return payload


def _artifact_index_payload(paths: dict[str, Path]) -> dict[str, object]:
    entries = []
    for role, path in (
        ("local_asset_bounded_smoke_iteration_result", paths["result_path"]),
        ("local_asset_bounded_smoke_iteration_manifest", paths["manifest_path"]),
        ("local_asset_bounded_smoke_iteration_summary", paths["summary_path"]),
        (
            "local_asset_bounded_smoke_iteration_human_review_checklist",
            paths["checklist_path"],
        ),
        ("local_asset_bounded_smoke_iteration_signoff", paths["signoff_path"]),
        ("local_asset_bounded_smoke_iteration_admission", paths["admission_path"]),
    ):
        entries.append(_artifact_entry(paths["output_dir"], role, path))
    for role, path in (
        (
            "local_asset_bounded_smoke_iteration_smoke_artifact_index",
            paths["smoke_output_dir"] / _ARTIFACT_INDEX_FILE,
        ),
        (
            "local_asset_bounded_smoke_iteration_smoke_artifact_index_manifest",
            paths["smoke_output_dir"] / _ARTIFACT_INDEX_MANIFEST_FILE,
        ),
    ):
        if path.exists() and path.is_file() and not path.is_symlink():
            entries.append(_artifact_entry(paths["output_dir"], role, path))
    return {
        "index_type": _INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": paths["output_dir"].as_posix(),
        "artifact_index_strategy": "explicit_bounded_smoke_iteration_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "deterministic_ordering": True,
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ACTION,
        **dict(_BOUNDARY_FLAGS),
    }


def _artifact_index_manifest_payload(
    common: dict[str, object],
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    entries = artifact_index["entries"]
    return {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "artifact_index_path": paths["artifact_index_path"].as_posix(),
        "artifact_index_sha256": sha256_file(paths["artifact_index_path"]),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [
            str(entry["relative_path"]) for entry in entries
        ],
        "job_dir": common["output_dir"],
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_input_files_indexed": False,
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ACTION,
        **dict(_BOUNDARY_FLAGS),
    }


def _artifact_entry(root_path: Path, role: str, path: Path) -> dict[str, object]:
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


def _source_artifacts(common: dict[str, object]) -> list[dict[str, object]]:
    promotion_path = Path(str(common["promotion_output_dir"]))
    specs = (
        ("local_asset_smoke_promotion_decision", promotion_path / _PROMOTION_DECISION_FILE),
        (
            "local_asset_smoke_promotion_gate_manifest",
            promotion_path / _PROMOTION_MANIFEST_FILE,
        ),
        ("promotion_artifact_index", promotion_path / _ARTIFACT_INDEX_FILE),
        (
            "promotion_artifact_index_manifest",
            promotion_path / _ARTIFACT_INDEX_MANIFEST_FILE,
        ),
        ("readiness_report", Path(str(common["readiness_report"]))),
    )
    return [
        _source_artifact_entry(role, path)
        for role, path in sorted(specs, key=lambda item: item[0])
    ]


def _source_artifact_entry(role: str, path: Path) -> dict[str, object]:
    trusted = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_role": role,
        "path": path.as_posix(),
        "sha256": sha256_file(path) if trusted else None,
        "size_bytes": path.stat().st_size if trusted else None,
        "exists": path.exists(),
        "trusted_generated_artifact": trusted,
        "content_indexed": False,
        "raw_content_copied": False,
    }


def _summary_markdown(
    result_payload: dict[str, object],
    *,
    promotion_gate_status: object,
    promotion_decision: object,
) -> str:
    blockers = result_payload["iteration_blockers"]
    lines = [
        "# Local Asset Bounded Smoke Iteration",
        "",
        "- Iteration status: `" + str(result_payload["iteration_status"]) + "`",
        "- Iteration decision: `" + str(result_payload["iteration_decision"]) + "`",
        "- Promotion gate status: `" + str(promotion_gate_status) + "`",
        "- Promotion decision: `" + str(promotion_decision) + "`",
        "- Human signoff valid: "
        + _bool_text(result_payload["human_signoff_valid"]),
        "- Smoke launcher invoked: "
        + _bool_text(result_payload["smoke_launcher_invoked"]),
        "- Bounded smoke iteration performed: "
        + _bool_text(result_payload["bounded_smoke_iteration_performed"]),
        "- Smoke run complete: " + _bool_text(result_payload["smoke_run_complete"]),
        "- Scan complete: " + _bool_text(result_payload["scan_complete"]),
        "",
        "## Output Paths",
        "",
        "- Promotion output dir: `" + str(result_payload["promotion_output_dir"]) + "`",
        "- Candidate input dir: `" + str(result_payload["candidate_input_dir"]) + "`",
        "- Readiness report: `" + str(result_payload["readiness_report"]) + "`",
        "- Iteration output dir: `" + str(result_payload["output_dir"]) + "`",
        "- Control output dir: `" + str(result_payload["control_output_dir"]) + "`",
        "- Smoke output dir: `" + str(result_payload["smoke_output_dir"]) + "`",
        "",
        "## Bounded Limits",
        "",
        "- Max smoke files: " + str(result_payload["max_smoke_files"]),
        "- Max smoke bytes: " + str(result_payload["max_smoke_bytes"]),
        "- Max smoke depth: " + str(result_payload["max_smoke_depth"]),
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        for blocker in blockers:
            lines.append("- " + str(blocker["blocker_role"]) + ": " + str(blocker["detail"]))
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Explicit Boundaries",
            "",
            "- no production promotion",
            "- no production scan approval",
            "- no automatic approval",
            "- no watcher/daemon",
            "- no input mutation",
            "- no move/rename/delete",
            "- no duplicate deletion",
            "- no media organizer",
            "- no network",
            "- no model API",
            "- no external runtime",
            "- human review required",
        ]
    )
    return "\n".join(lines) + "\n"


def _human_review_checklist_markdown() -> str:
    lines = [
        "# Local Asset Bounded Smoke Iteration Human Review Checklist",
        "",
        "- [ ] Verify promotion gate status was promotion_candidate.",
        "- [ ] Verify promotion decision allowed only next bounded smoke iteration.",
        "- [ ] Verify production_promotion_granted=false.",
        "- [ ] Verify production_scan_approved=false.",
        "- [ ] Verify human signoff phrase plaintext was not persisted.",
        "- [ ] Verify bounded limits were enforced.",
        "- [ ] Verify smoke launcher invoked only after valid gate + signoff.",
        "- [ ] Verify scan complete status.",
        "- [ ] Verify input_mutation_performed=false.",
        "- [ ] Verify no file move/rename/delete.",
        "- [ ] Verify no duplicate deletion.",
        "",
        "## Decide Next",
        "",
        "- [ ] generate smoke review packet for this iteration",
        "- [ ] reject and repair iteration",
        "- [ ] inspect smoke outputs manually",
        "",
        "Do not include raw private file contents.",
        "Do not suggest deleting, moving, or renaming files.",
        "Do not grant production autonomy.",
    ]
    return "\n".join(lines) + "\n"


def _smoke_payload_summary(
    smoke_payload: dict[str, object] | None,
) -> dict[str, object]:
    if smoke_payload is None:
        return {
            "smoke_payload_present": False,
            "scan_complete": False,
            "bounded_smoke_run_performed": False,
        }
    return {
        "smoke_payload_present": True,
        "workflow": smoke_payload.get("workflow"),
        "admitted": smoke_payload.get("admitted"),
        "scan_launcher_invoked": smoke_payload.get("scan_launcher_invoked"),
        "scan_complete": smoke_payload.get("scan_complete"),
        "bounded_smoke_run_performed": smoke_payload.get(
            "bounded_smoke_run_performed"
        ),
        "failure_stage": smoke_payload.get("failure_stage"),
        "artifact_index_path": smoke_payload.get("artifact_index_path"),
        "artifact_index_manifest_path": smoke_payload.get(
            "artifact_index_manifest_path"
        ),
        "scan_artifact_index_path": smoke_payload.get("scan_artifact_index_path"),
        "scan_artifact_index_manifest_path": smoke_payload.get(
            "scan_artifact_index_manifest_path"
        ),
    }


def _promotion_decision_summary(
    decision: dict[str, object],
    promotion_state: dict[str, object],
) -> dict[str, object]:
    return {
        "promotion_validated": promotion_state["validated"],
        "promotion_gate_status": decision.get("promotion_gate_status"),
        "promotion_decision": decision.get("promotion_decision"),
        "next_bounded_smoke_iteration_allowed": decision.get(
            "next_bounded_smoke_iteration_allowed"
        ),
        "production_promotion_granted": False,
        "production_scan_approved": False,
        "review_packet_status": decision.get("review_packet_status"),
        "review_recommended_human_decision": decision.get(
            "review_recommended_human_decision"
        ),
        "promotion_blocker_count": _first_int(
            decision.get("promotion_blocker_count"),
            _dict_or_empty(decision.get("blocker_summary")).get(
                "promotion_blocker_count"
            ),
            default=None,
        ),
        "promotion_blockers": decision.get("promotion_blockers"),
    }


def _blocker_summary(blockers: list[dict[str, object]]) -> dict[str, object]:
    return {
        "blocker_count": len(blockers),
        "blocker_roles": [
            str(blocker["blocker_role"]) for blocker in blockers
        ],
        "no_blockers_present": len(blockers) == 0,
    }


def _blocker(blocker_role: str, detail: str, **extra: object) -> dict[str, object]:
    item = {
        "blocker_role": blocker_role,
        "severity": "blocking",
        "detail": detail,
    }
    item.update(extra)
    return item


def _read_json_file(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(label + " JSON is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError(label + " must be an object")
    return payload


def _dict_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_int(*values: object, default: int | None = 0) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return default


def _same_existing_path(first: Path, second: Path) -> bool:
    try:
        return first.resolve(strict=True) == second.resolve(strict=True)
    except OSError:
        return False


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _sha256_if_file(path: Path) -> str | None:
    if path.exists() and path.is_file() and not path.is_symlink():
        return sha256_file(path)
    return None


def _bool_text(value: object) -> str:
    return str(bool(value)).lower()


def _ensure_control_dir(control_path: Path) -> None:
    control_path.mkdir(exist_ok=True)
    if not control_path.is_dir() or control_path.is_symlink():
        raise ValueError("control_output_dir must be a real directory")


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()
