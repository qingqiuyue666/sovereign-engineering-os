"""Human-approved bounded smoke run admission for local asset scanning."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json

from kernel.assets.local_asset_quarantine import (
    has_hidden_part,
    is_secret_looking_path,
    is_unsafe_directory_name,
)
from kernel.personal_ai.asset_scan_operational_control import asset_scan_output_status
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "DEFAULT_MAX_SMOKE_BYTES",
    "DEFAULT_MAX_SMOKE_DEPTH",
    "DEFAULT_MAX_SMOKE_FILES",
    "HUMAN_SMOKE_APPROVAL_PHRASE",
    "LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE",
    "LOCAL_ASSET_HUMAN_SMOKE_APPROVAL_FILE",
    "LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE",
    "LocalAssetHumanSmokeResult",
    "run_local_asset_human_smoke",
]

HUMAN_SMOKE_APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
DEFAULT_MAX_SMOKE_FILES = 100
DEFAULT_MAX_SMOKE_BYTES = 2000000000
DEFAULT_MAX_SMOKE_DEPTH = 8

LOCAL_ASSET_HUMAN_SMOKE_APPROVAL_FILE = "local_asset_human_smoke_approval.json"
LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE = (
    "local_asset_human_smoke_admission_receipt.json"
)
LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE = (
    "local_asset_human_smoke_run_summary.md"
)

_CONTROL_DIR_NAME = "control"
_SCAN_DIR_NAME = "scan"
_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_APPROVAL_TYPE = "local_asset_human_smoke_approval_v1"
_RECEIPT_TYPE = "local_asset_human_smoke_admission_receipt_v1"
_ROOT_INDEX_TYPE = "local_asset_human_smoke_artifact_index_v1"
_ROOT_INDEX_MANIFEST_TYPE = "local_asset_human_smoke_artifact_index_manifest_v1"
_READINESS_REPORT_TYPE = "local_asset_real_folder_smoke_readiness_report_v1"
_READINESS_EXECUTION_CAPABILITY = "real_folder_smoke_readiness_only"
_ALLOW_DECISION = "allow_human_review_for_future_smoke"
_ALLOWED_READINESS_STATUSES = {"ready", "ready_with_warnings"}
_BLOCKED_READINESS_STATUSES = {
    "blocked_safety_risk",
    "blocked_limit_exceeded",
    "failed_preflight",
}

_NO_SCOPE_FLAGS = {
    "production_scan_performed": False,
    "input_mutation_performed": False,
    "file_move_performed": False,
    "file_rename_performed": False,
    "file_delete_performed": False,
    "media_organizer_behavior_performed": False,
    "output_overwrite_performed": False,
    "network_access_performed": False,
    "model_api_called": False,
    "external_runtime_invoked": False,
}


@dataclass(frozen=True)
class LocalAssetHumanSmokeResult:
    output_dir: Path
    control_output_dir: Path
    scan_output_dir: Path
    approval_path: Path | None
    admission_receipt_path: Path | None
    summary_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    payload: dict[str, object]


def run_local_asset_human_smoke(
    candidate_input_dir: Path,
    output_dir: Path,
    readiness_report: Path,
    *,
    human_approval_id: str,
    human_approval_phrase: str,
    recursive: bool = False,
    include_hidden: bool = False,
    project_id: str | None = None,
    max_smoke_files: int = DEFAULT_MAX_SMOKE_FILES,
    max_smoke_bytes: int = DEFAULT_MAX_SMOKE_BYTES,
    max_smoke_depth: int = DEFAULT_MAX_SMOKE_DEPTH,
    previous_scan_output_dir: Path | None = None,
) -> LocalAssetHumanSmokeResult:
    """Admit and run a bounded human-approved local asset smoke scan."""

    candidate_path = Path(candidate_input_dir)
    output_path = Path(output_dir)
    readiness_path = Path(readiness_report)
    control_path = output_path / _CONTROL_DIR_NAME
    scan_path = output_path / _SCAN_DIR_NAME
    summary_path = output_path / LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE
    root_artifact_index_path = output_path / _ARTIFACT_INDEX_FILE
    root_artifact_index_manifest_path = output_path / _ARTIFACT_INDEX_MANIFEST_FILE
    approval_path = control_path / LOCAL_ASSET_HUMAN_SMOKE_APPROVAL_FILE
    admission_path = control_path / LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE
    previous_scan_path = (
        None if previous_scan_output_dir is None else Path(previous_scan_output_dir)
    )
    common = _common_payload(
        candidate_path=candidate_path,
        output_path=output_path,
        control_path=control_path,
        scan_path=scan_path,
        readiness_path=readiness_path,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
        previous_scan_path=previous_scan_path,
    )

    output_error = _output_dir_error(output_path)
    if output_error is not None:
        return _result_without_artifacts(
            common,
            failure_stage="preflight_output_dir_missing",
            error_message=output_error,
        )

    collision_error = _output_collision_error(
        output_path=output_path,
        control_path=control_path,
        scan_path=scan_path,
    )
    if collision_error is not None:
        return _result_without_artifacts(
            common,
            failure_stage="preflight_output_collision",
            error_message=collision_error,
        )

    limit_error = _limit_argument_error(
        max_smoke_files,
        max_smoke_bytes,
        max_smoke_depth,
    )
    if limit_error is not None:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=None,
            admission_reason=limit_error,
            failure_stage="preflight_limit_argument_failure",
            smoke_precheck=_empty_precheck("not_run"),
        )

    if not isinstance(human_approval_id, str) or not human_approval_id:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=None,
            admission_reason="human_approval_id is missing",
            failure_stage="human_approval_missing",
            smoke_precheck=_empty_precheck("not_run"),
        )
    if human_approval_id == HUMAN_SMOKE_APPROVAL_PHRASE:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=None,
            admission_reason="human_approval_id must not be the approval phrase",
            failure_stage="human_approval_id_invalid",
            smoke_precheck=_empty_precheck("not_run"),
        )
    if human_approval_phrase != HUMAN_SMOKE_APPROVAL_PHRASE:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=None,
            admission_reason="human approval phrase mismatch",
            failure_stage="human_approval_phrase_mismatch",
            smoke_precheck=_empty_precheck("not_run"),
        )

    readiness_error = _readiness_report_path_error(readiness_path)
    if readiness_error is not None:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=None,
            admission_reason=readiness_error,
            failure_stage="readiness_report_preflight_failure",
            smoke_precheck=_empty_precheck("not_run"),
        )

    try:
        readiness_payload = _load_readiness_report(readiness_path)
    except ValueError as error:
        return _write_denial_artifacts(
            common,
            approval_path=None,
            readiness_report_payload=None,
            readiness_report_sha256=sha256_file(readiness_path),
            admission_reason=str(error),
            failure_stage="readiness_report_invalid",
            smoke_precheck=_empty_precheck("not_run"),
        )
    readiness_sha256 = sha256_file(readiness_path)
    common = dict(common)
    common["project_id"] = _effective_project_id(project_id, readiness_payload)

    approval_artifact_path = _write_approval_artifact(
        approval_path=approval_path,
        common=common,
        readiness_report_payload=readiness_payload,
        readiness_report_sha256=readiness_sha256,
        human_approval_id=human_approval_id,
        human_approval_phrase=human_approval_phrase,
    )

    validation_error = _admission_validation_error(
        candidate_path=candidate_path,
        output_path=output_path,
        readiness_payload=readiness_payload,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
    )
    if validation_error is not None:
        return _write_denial_artifacts(
            common,
            approval_path=approval_artifact_path,
            readiness_report_payload=readiness_payload,
            readiness_report_sha256=readiness_sha256,
            admission_reason=validation_error["reason"],
            failure_stage=validation_error["failure_stage"],
            smoke_precheck=_empty_precheck("not_run"),
        )

    smoke_precheck = _metadata_smoke_precheck(
        candidate_path,
        recursive=recursive,
        include_hidden=include_hidden,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
    )
    if smoke_precheck["smoke_precheck_limit_exceeded"]:
        return _write_denial_artifacts(
            common,
            approval_path=approval_artifact_path,
            readiness_report_payload=readiness_payload,
            readiness_report_sha256=readiness_sha256,
            admission_reason="bounded smoke metadata precheck limit exceeded",
            failure_stage="smoke_precheck_limit_exceeded",
            smoke_precheck=smoke_precheck,
        )

    _ensure_scan_output_dir(scan_path)
    admission = _admission_receipt_payload(
        common=common,
        admitted=True,
        admission_reason="admitted_for_bounded_human_smoke_run",
        readiness_report_payload=readiness_payload,
        readiness_report_sha256=readiness_sha256,
        approval_path=approval_artifact_path,
        smoke_precheck=smoke_precheck,
        scan_launcher_invoked=True,
        scan_complete=False,
        failure_stage=None,
        real_scan_performed=False,
    )
    _write_json_exclusive(admission_path, admission)

    scan_result = _run_scan_launcher(
        candidate_path,
        scan_path,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=str(common["project_id"])
        if common["project_id"] is not None
        else None,
        previous_scan_output_dir=previous_scan_path,
    )
    scan_payload = dict(scan_result.payload)
    scan_payload["launcher_summary_path"] = scan_result.summary_path.as_posix()
    scan_complete = bool(scan_result.complete)
    real_scan_performed = bool(scan_complete)
    final_admission = _admission_receipt_payload(
        common=common,
        admitted=True,
        admission_reason="admitted_for_bounded_human_smoke_run",
        readiness_report_payload=readiness_payload,
        readiness_report_sha256=readiness_sha256,
        approval_path=approval_artifact_path,
        smoke_precheck=smoke_precheck,
        scan_launcher_invoked=True,
        scan_complete=scan_complete,
        failure_stage=None if scan_complete else scan_payload.get("failure_stage"),
        real_scan_performed=real_scan_performed,
    )
    write_json_atomically(admission_path, final_admission)

    _write_summary_exclusive(
        summary_path,
        _summary_markdown(
            common=common,
            admission=final_admission,
            human_approval_id=human_approval_id,
            scan_payload=scan_payload,
        ),
    )
    root_index, root_manifest = _write_root_artifact_index(
        output_path=output_path,
        control_path=control_path,
        scan_path=scan_path,
        artifact_index_path=root_artifact_index_path,
        artifact_index_manifest_path=root_artifact_index_manifest_path,
        approval_path=approval_artifact_path,
        admission_path=admission_path,
        summary_path=summary_path,
        scan_payload=scan_payload,
    )
    payload = _success_payload(
        common=common,
        approval_path=approval_artifact_path,
        admission_path=admission_path,
        summary_path=summary_path,
        root_index=root_index,
        root_manifest=root_manifest,
        readiness_report_payload=readiness_payload,
        smoke_precheck=smoke_precheck,
        scan_payload=scan_payload,
        complete=scan_complete,
        failure_stage=None if scan_complete else scan_payload.get("failure_stage"),
    )
    return LocalAssetHumanSmokeResult(
        output_dir=output_path,
        control_output_dir=control_path,
        scan_output_dir=scan_path,
        approval_path=approval_artifact_path,
        admission_receipt_path=admission_path,
        summary_path=summary_path,
        artifact_index_path=root_index,
        artifact_index_manifest_path=root_manifest,
        complete=scan_complete,
        payload=payload,
    )


def _run_scan_launcher(
    candidate_path: Path,
    scan_path: Path,
    *,
    recursive: bool,
    include_hidden: bool,
    project_id: str | None,
    previous_scan_output_dir: Path | None,
):
    from kernel.personal_ai.local_launcher import run_local_asset_scan_launcher

    return run_local_asset_scan_launcher(
        candidate_path,
        scan_path,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        previous_scan_output_dir=previous_scan_output_dir,
    )


def _common_payload(
    *,
    candidate_path: Path,
    output_path: Path,
    control_path: Path,
    scan_path: Path,
    readiness_path: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
    previous_scan_path: Path | None,
) -> dict[str, object]:
    return {
        "candidate_input_dir": candidate_path.as_posix(),
        "output_dir": output_path.as_posix(),
        "control_output_dir": control_path.as_posix(),
        "scan_output_dir": scan_path.as_posix(),
        "readiness_report_path": readiness_path.as_posix(),
        "project_id": project_id,
        "recursive": bool(recursive),
        "include_hidden": bool(include_hidden),
        "max_smoke_files": int(max_smoke_files),
        "max_smoke_bytes": int(max_smoke_bytes),
        "max_smoke_depth": int(max_smoke_depth),
        "previous_scan_output_dir": None
        if previous_scan_path is None
        else previous_scan_path.as_posix(),
        "bounded_smoke_run": True,
        "required_human_approval": True,
    }


def _result_without_artifacts(
    common: dict[str, object],
    *,
    failure_stage: str,
    error_message: str,
) -> LocalAssetHumanSmokeResult:
    payload = _base_result_payload(common)
    payload.update(
        {
            "complete": False,
            "admitted": False,
            "admission_reason": error_message,
            "failure_stage": failure_stage,
            "error_type": "ValueError",
            "error_message": error_message,
            "scan_launcher_invoked": False,
            "scan_complete": False,
            "real_scan_performed": False,
            "bounded_smoke_run_performed": False,
            "next_allowed_action": "human_fix_smoke_run_preflight",
            "smoke_precheck_status": "not_run",
            "smoke_precheck_file_count": 0,
            "smoke_precheck_total_bytes": 0,
            "smoke_precheck_max_depth_observed": 0,
            "smoke_precheck_limit_exceeded": False,
        }
    )
    return LocalAssetHumanSmokeResult(
        output_dir=Path(common["output_dir"]),
        control_output_dir=Path(common["control_output_dir"]),
        scan_output_dir=Path(common["scan_output_dir"]),
        approval_path=None,
        admission_receipt_path=None,
        summary_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        payload=payload,
    )


def _write_denial_artifacts(
    common: dict[str, object],
    *,
    approval_path: Path | None,
    readiness_report_payload: dict[str, object] | None,
    readiness_report_sha256: str | None,
    admission_reason: str,
    failure_stage: str,
    smoke_precheck: dict[str, object],
) -> LocalAssetHumanSmokeResult:
    output_path = Path(common["output_dir"])
    control_path = Path(common["control_output_dir"])
    scan_path = Path(common["scan_output_dir"])
    summary_path = output_path / LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE
    admission_path = control_path / LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE
    root_artifact_index_path = output_path / _ARTIFACT_INDEX_FILE
    root_artifact_index_manifest_path = output_path / _ARTIFACT_INDEX_MANIFEST_FILE

    _ensure_control_output_dir(control_path)
    admission = _admission_receipt_payload(
        common=common,
        admitted=False,
        admission_reason=admission_reason,
        readiness_report_payload=readiness_report_payload,
        readiness_report_sha256=readiness_report_sha256,
        approval_path=approval_path,
        smoke_precheck=smoke_precheck,
        scan_launcher_invoked=False,
        scan_complete=False,
        failure_stage=failure_stage,
        real_scan_performed=False,
    )
    _write_json_exclusive(admission_path, admission)
    _write_summary_exclusive(
        summary_path,
        _summary_markdown(
            common=common,
            admission=admission,
            human_approval_id=None,
            scan_payload={},
        ),
    )
    root_index, root_manifest = _write_root_artifact_index(
        output_path=output_path,
        control_path=control_path,
        scan_path=scan_path,
        artifact_index_path=root_artifact_index_path,
        artifact_index_manifest_path=root_artifact_index_manifest_path,
        approval_path=approval_path,
        admission_path=admission_path,
        summary_path=summary_path,
        scan_payload={},
    )
    payload = _base_result_payload(common)
    payload.update(admission)
    payload.update(
        {
            "complete": False,
            "local_asset_human_smoke_approval_path": None
            if approval_path is None
            else approval_path.as_posix(),
            "local_asset_human_smoke_admission_receipt_path": (
                admission_path.as_posix()
            ),
            "local_asset_human_smoke_run_summary_path": summary_path.as_posix(),
            "artifact_index_path": root_index.as_posix(),
            "artifact_index_manifest_path": root_manifest.as_posix(),
            "scan_artifact_index_path": None,
            "scan_artifact_index_manifest_path": None,
            "indexed_artifacts": _read_indexed_artifact_count(root_index),
            "safe_to_retry": False,
            "replay_hint": (
                "Review the human smoke run admission failure and rerun with a "
                "new empty smoke output root."
            ),
        }
    )
    return LocalAssetHumanSmokeResult(
        output_dir=output_path,
        control_output_dir=control_path,
        scan_output_dir=scan_path,
        approval_path=approval_path,
        admission_receipt_path=admission_path,
        summary_path=summary_path,
        artifact_index_path=root_index,
        artifact_index_manifest_path=root_manifest,
        complete=False,
        payload=payload,
    )


def _base_result_payload(common: dict[str, object]) -> dict[str, object]:
    payload = dict(common)
    payload.update(_NO_SCOPE_FLAGS)
    payload.update(
        {
            "approval_phrase_stored": False,
            "approval_phrase_plaintext_persisted": False,
            "required_human_approval": True,
            "production_autonomy_granted": False,
        }
    )
    return payload


def _success_payload(
    *,
    common: dict[str, object],
    approval_path: Path,
    admission_path: Path,
    summary_path: Path,
    root_index: Path,
    root_manifest: Path,
    readiness_report_payload: dict[str, object],
    smoke_precheck: dict[str, object],
    scan_payload: dict[str, object],
    complete: bool,
    failure_stage: object,
) -> dict[str, object]:
    payload = _base_result_payload(common)
    payload.update(
        {
            "complete": complete,
            "admitted": True,
            "admission_reason": "admitted_for_bounded_human_smoke_run",
            "local_asset_human_smoke_approval_path": approval_path.as_posix(),
            "local_asset_human_smoke_admission_receipt_path": (
                admission_path.as_posix()
            ),
            "local_asset_human_smoke_run_summary_path": summary_path.as_posix(),
            "artifact_index_path": root_index.as_posix(),
            "artifact_index_manifest_path": root_manifest.as_posix(),
            "scan_artifact_index_path": scan_payload.get("artifact_index_path"),
            "scan_artifact_index_manifest_path": scan_payload.get(
                "artifact_index_manifest_path"
            ),
            "readiness_status": readiness_report_payload.get("readiness_status"),
            "readiness_decision": readiness_report_payload.get("readiness_decision"),
            "scan_launcher_invoked": True,
            "scan_complete": complete,
            "real_scan_performed": bool(complete),
            "bounded_smoke_run_performed": True,
            "failure_stage": failure_stage,
            "next_allowed_action": "human_review_smoke_run_outputs"
            if complete
            else "human_fix_smoke_run_preflight",
            "indexed_artifacts": _read_indexed_artifact_count(root_index),
            "scan_output_payload": dict(scan_payload),
            "scan_asset_manifest_path": scan_payload.get("asset_manifest_path"),
            "scan_asset_index_path": scan_payload.get("asset_index_path"),
            "scan_duplicates_report_path": scan_payload.get("duplicates_report_path"),
            "scan_media_inventory_path": scan_payload.get("media_inventory_path"),
            "scan_asset_runtime_audit_log_path": scan_payload.get(
                "asset_runtime_audit_log_path"
            ),
            "scan_asset_runtime_validation_report_path": scan_payload.get(
                "asset_runtime_validation_report_path"
            ),
            "scan_asset_runtime_quarantine_manifest_path": scan_payload.get(
                "asset_runtime_quarantine_manifest_path"
            ),
            "asset_scan_run_receipt_path": scan_payload.get(
                "asset_scan_run_receipt_path"
            ),
            "launcher_summary_path": scan_payload.get("launcher_summary_path"),
            "scan_launcher_summary_path": scan_payload.get("launcher_summary_path"),
        }
    )
    payload.update(smoke_precheck)
    payload.update(_NO_SCOPE_FLAGS)
    return payload


def _output_dir_error(output_path: Path) -> str | None:
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    return None


def _output_collision_error(
    *,
    output_path: Path,
    control_path: Path,
    scan_path: Path,
) -> str | None:
    root_paths = {
        LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE: (
            output_path / LOCAL_ASSET_HUMAN_SMOKE_RUN_SUMMARY_FILE
        ),
        _ARTIFACT_INDEX_FILE: output_path / _ARTIFACT_INDEX_FILE,
        _ARTIFACT_INDEX_MANIFEST_FILE: output_path / _ARTIFACT_INDEX_MANIFEST_FILE,
    }
    for file_name, path in sorted(root_paths.items()):
        if path.exists():
            return "local asset human smoke root output already exists: " + file_name
    if control_path.exists() and (not control_path.is_dir() or control_path.is_symlink()):
        return "control_output_dir must be a real directory"
    control_paths = {
        LOCAL_ASSET_HUMAN_SMOKE_APPROVAL_FILE: (
            control_path / LOCAL_ASSET_HUMAN_SMOKE_APPROVAL_FILE
        ),
        LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE: (
            control_path / LOCAL_ASSET_HUMAN_SMOKE_ADMISSION_RECEIPT_FILE
        ),
    }
    for file_name, path in sorted(control_paths.items()):
        if path.exists():
            return "local asset human smoke control output already exists: " + file_name
    if scan_path.exists():
        if not scan_path.is_dir() or scan_path.is_symlink():
            return "scan_output_dir must be a real directory"
        status = asset_scan_output_status(scan_path)
        if status["partial_outputs_written"]:
            return (
                "local asset human smoke scan output already exists: "
                + str(status["partial_outputs_written"][0])
            )
        if any(scan_path.iterdir()):
            return "scan_output_dir must be empty before human smoke scan"
    return None


def _limit_argument_error(
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> str | None:
    for name, value in (
        ("max_smoke_files", max_smoke_files),
        ("max_smoke_bytes", max_smoke_bytes),
        ("max_smoke_depth", max_smoke_depth),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            return name + " must be an integer"
        if value < 0:
            return name + " must be non-negative"
    return None


def _readiness_report_path_error(readiness_path: Path) -> str | None:
    if not readiness_path.exists():
        return "readiness_report is missing"
    if not readiness_path.is_file():
        return "readiness_report is not a file"
    if readiness_path.is_symlink():
        return "readiness_report must not be a symlink"
    return None


def _load_readiness_report(readiness_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("readiness_report JSON is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("readiness_report must be an object")
    if payload.get("report_type") != _READINESS_REPORT_TYPE:
        raise ValueError("readiness_report type mismatch")
    if payload.get("execution_capability") != _READINESS_EXECUTION_CAPABILITY:
        raise ValueError("readiness_report execution_capability mismatch")
    if payload.get("metadata_only") is not True:
        raise ValueError("readiness_report metadata_only flag mismatch")
    return payload


def _effective_project_id(
    project_id: str | None,
    readiness_payload: dict[str, object],
) -> str | None:
    if project_id is not None:
        return project_id
    readiness_project_id = readiness_payload.get("project_id")
    if isinstance(readiness_project_id, str) and readiness_project_id:
        return readiness_project_id
    return None


def _admission_validation_error(
    *,
    candidate_path: Path,
    output_path: Path,
    readiness_payload: dict[str, object],
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> dict[str, str] | None:
    candidate_error = _candidate_dir_error(candidate_path)
    if candidate_error is not None:
        return {
            "failure_stage": "preflight_candidate_input_dir_failure",
            "reason": candidate_error,
        }
    overlap = _input_output_overlap(candidate_path, output_path)
    if overlap is not None:
        return {
            "failure_stage": "preflight_input_output_overlap",
            "reason": overlap,
        }
    readiness_candidate = readiness_payload.get("candidate_input_dir")
    if not isinstance(readiness_candidate, str) or not readiness_candidate:
        return {
            "failure_stage": "readiness_report_invalid",
            "reason": "readiness_report candidate_input_dir is missing",
        }
    if not _same_existing_path(candidate_path, Path(readiness_candidate)):
        return {
            "failure_stage": "readiness_candidate_path_mismatch",
            "reason": "candidate_input_dir does not match readiness report",
        }
    readiness_project_id = readiness_payload.get("project_id")
    if (
        project_id is not None
        and readiness_project_id is not None
        and project_id != readiness_project_id
    ):
        return {
            "failure_stage": "readiness_project_id_mismatch",
            "reason": "project_id does not match readiness report",
        }
    if readiness_payload.get("recursive") is not bool(recursive):
        return {
            "failure_stage": "readiness_recursive_mismatch",
            "reason": "recursive does not match readiness report",
        }
    if readiness_payload.get("include_hidden") is not bool(include_hidden):
        return {
            "failure_stage": "readiness_include_hidden_mismatch",
            "reason": "include_hidden does not match readiness report",
        }
    readiness_status = readiness_payload.get("readiness_status")
    readiness_decision = readiness_payload.get("readiness_decision")
    if readiness_status in _BLOCKED_READINESS_STATUSES:
        return {
            "failure_stage": "readiness_status_blocked",
            "reason": "readiness_status blocks human smoke run",
        }
    if readiness_status not in _ALLOWED_READINESS_STATUSES:
        return {
            "failure_stage": "readiness_status_invalid",
            "reason": "readiness_status does not allow human smoke run",
        }
    if readiness_decision != _ALLOW_DECISION:
        return {
            "failure_stage": "readiness_decision_rejected",
            "reason": "readiness_decision does not allow future smoke",
        }
    if readiness_payload.get("required_human_approval") is not True:
        return {
            "failure_stage": "readiness_human_approval_missing",
            "reason": "readiness_report required_human_approval must be true",
        }
    limits_error = _readiness_limit_error(
        readiness_payload,
        max_smoke_files=max_smoke_files,
        max_smoke_bytes=max_smoke_bytes,
        max_smoke_depth=max_smoke_depth,
    )
    if limits_error is not None:
        return {
            "failure_stage": "readiness_smoke_limit_mismatch",
            "reason": limits_error,
        }
    return None


def _candidate_dir_error(candidate_path: Path) -> str | None:
    if not candidate_path.exists():
        return "candidate_input_dir is missing"
    if not candidate_path.is_dir():
        return "candidate_input_dir is not a directory"
    if candidate_path.is_symlink():
        return "candidate_input_dir must not be a symlink"
    return None


def _input_output_overlap(candidate_path: Path, output_path: Path) -> str | None:
    try:
        candidate_resolved = candidate_path.resolve(strict=True)
        output_resolved = output_path.resolve(strict=True)
    except OSError:
        return None
    if candidate_resolved == output_resolved:
        return "candidate_input_dir and output_dir must be different directories"
    if _path_is_inside(output_resolved, candidate_resolved):
        return "output_dir must not be inside candidate_input_dir"
    if _path_is_inside(candidate_resolved, output_resolved):
        return "candidate_input_dir must not be inside output_dir"
    return None


def _same_existing_path(first: Path, second: Path) -> bool:
    try:
        return first.resolve(strict=True) == second.resolve(strict=True)
    except OSError:
        return False


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _readiness_limit_error(
    readiness_payload: dict[str, object],
    *,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> str | None:
    readiness_max_total_bytes = readiness_payload.get("max_total_bytes")
    if (
        isinstance(readiness_max_total_bytes, int)
        and max_smoke_bytes > readiness_max_total_bytes
    ):
        return "max_smoke_bytes exceeds readiness max_total_bytes"
    readiness_max_depth = readiness_payload.get("max_depth")
    if isinstance(readiness_max_depth, int) and max_smoke_depth > readiness_max_depth:
        return "max_smoke_depth exceeds readiness max_depth"
    return None


def _metadata_smoke_precheck(
    input_path: Path,
    *,
    recursive: bool,
    include_hidden: bool,
    max_smoke_files: int,
    max_smoke_bytes: int,
    max_smoke_depth: int,
) -> dict[str, object]:
    file_count = 0
    total_bytes = 0
    max_depth_observed = 0
    limit_exceeded = False
    pending_dirs = deque([input_path])

    while pending_dirs:
        current_dir = pending_dirs.popleft()
        try:
            children = sorted(
                current_dir.iterdir(),
                key=lambda path: path.relative_to(input_path).as_posix(),
            )
        except OSError:
            limit_exceeded = True
            break

        for child in children:
            relative_path = child.relative_to(input_path)
            depth = len(relative_path.parts)
            max_depth_observed = max(max_depth_observed, depth)
            if depth > max_smoke_depth:
                limit_exceeded = True

            if child.is_symlink():
                continue

            hidden = has_hidden_part(relative_path)
            secret = is_secret_looking_path(relative_path)
            if child.is_dir():
                if is_unsafe_directory_name(child.name) or secret:
                    continue
                if hidden and not include_hidden:
                    continue
                if recursive:
                    pending_dirs.append(child)
                continue

            if not child.is_file():
                continue
            if secret or (hidden and not include_hidden):
                continue
            try:
                file_size = int(child.stat().st_size)
            except OSError:
                limit_exceeded = True
                continue
            file_count += 1
            total_bytes += file_size
            if file_count > max_smoke_files:
                limit_exceeded = True
            if total_bytes > max_smoke_bytes:
                limit_exceeded = True
            if limit_exceeded:
                pending_dirs.clear()
                break

    return {
        "smoke_precheck_status": "limit_exceeded"
        if limit_exceeded
        else "passed",
        "smoke_precheck_file_count": file_count,
        "smoke_precheck_total_bytes": total_bytes,
        "smoke_precheck_max_depth_observed": max_depth_observed,
        "smoke_precheck_limit_exceeded": limit_exceeded,
    }


def _empty_precheck(status: str) -> dict[str, object]:
    return {
        "smoke_precheck_status": status,
        "smoke_precheck_file_count": 0,
        "smoke_precheck_total_bytes": 0,
        "smoke_precheck_max_depth_observed": 0,
        "smoke_precheck_limit_exceeded": False,
    }


def _ensure_control_output_dir(control_path: Path) -> None:
    control_path.mkdir(parents=False, exist_ok=True)
    if not control_path.is_dir() or control_path.is_symlink():
        raise ValueError("control_output_dir must be a real directory")


def _ensure_scan_output_dir(scan_path: Path) -> None:
    scan_path.mkdir(parents=False, exist_ok=True)
    if not scan_path.is_dir() or scan_path.is_symlink():
        raise ValueError("scan_output_dir must be a real directory")


def _write_approval_artifact(
    *,
    approval_path: Path,
    common: dict[str, object],
    readiness_report_payload: dict[str, object],
    readiness_report_sha256: str,
    human_approval_id: str,
    human_approval_phrase: str,
) -> Path:
    _ensure_control_output_dir(approval_path.parent)
    payload = {
        "artifact_type": _APPROVAL_TYPE,
        "authority": "human_approval_required",
        "human_approval_id": human_approval_id,
        "human_approval_phrase_sha256": sha256(
            human_approval_phrase.encode("utf-8")
        ).hexdigest(),
        "approval_phrase_stored": False,
        "approval_phrase_plaintext_persisted": False,
        "approved_action": "local_asset_human_approved_smoke_run",
        "candidate_input_dir": common["candidate_input_dir"],
        "output_dir": common["output_dir"],
        "readiness_report_path": common["readiness_report_path"],
        "readiness_report_sha256": readiness_report_sha256,
        "readiness_status": readiness_report_payload.get("readiness_status"),
        "readiness_decision": readiness_report_payload.get("readiness_decision"),
        "project_id": common["project_id"],
        "recursive": common["recursive"],
        "include_hidden": common["include_hidden"],
        "max_smoke_files": common["max_smoke_files"],
        "max_smoke_bytes": common["max_smoke_bytes"],
        "max_smoke_depth": common["max_smoke_depth"],
        "approved_by_user": True,
        "required_human_approval": True,
        "approval_scope": "bounded_smoke_run_only",
        "production_autonomy_granted": False,
        "real_scan_authority": "bounded_human_smoke_only",
        "input_mutation_allowed": False,
        "file_move_allowed": False,
        "file_rename_allowed": False,
        "file_delete_allowed": False,
        "network_allowed": False,
        "model_api_allowed": False,
        "external_runtime_allowed": False,
    }
    _write_json_exclusive(approval_path, payload)
    return approval_path


def _admission_receipt_payload(
    *,
    common: dict[str, object],
    admitted: bool,
    admission_reason: str,
    readiness_report_payload: dict[str, object] | None,
    readiness_report_sha256: str | None,
    approval_path: Path | None,
    smoke_precheck: dict[str, object],
    scan_launcher_invoked: bool,
    scan_complete: bool,
    failure_stage: object,
    real_scan_performed: bool,
) -> dict[str, object]:
    approval_sha256 = (
        sha256_file(approval_path)
        if approval_path is not None
        and approval_path.exists()
        and approval_path.is_file()
        and not approval_path.is_symlink()
        else None
    )
    payload = {
        "receipt_type": _RECEIPT_TYPE,
        "authority": "non_authority",
        "admitted": admitted,
        "admission_reason": admission_reason,
        "readiness_report_path": common["readiness_report_path"],
        "readiness_report_sha256": readiness_report_sha256,
        "approval_artifact_path": None
        if approval_path is None
        else approval_path.as_posix(),
        "approval_artifact_sha256": approval_sha256,
        "candidate_input_dir": common["candidate_input_dir"],
        "output_dir": common["output_dir"],
        "scan_output_dir": common["scan_output_dir"],
        "control_output_dir": common["control_output_dir"],
        "project_id": common["project_id"],
        "recursive": common["recursive"],
        "include_hidden": common["include_hidden"],
        "max_smoke_files": common["max_smoke_files"],
        "max_smoke_bytes": common["max_smoke_bytes"],
        "max_smoke_depth": common["max_smoke_depth"],
        "bounded_smoke_run": True,
        "readiness_status": None
        if readiness_report_payload is None
        else readiness_report_payload.get("readiness_status"),
        "readiness_decision": None
        if readiness_report_payload is None
        else readiness_report_payload.get("readiness_decision"),
        "scan_launcher_invoked": scan_launcher_invoked,
        "scan_complete": scan_complete,
        "failure_stage": failure_stage,
        "required_human_approval": True,
        "next_allowed_action": "human_review_smoke_run_outputs"
        if admitted and scan_complete
        else "human_fix_smoke_run_preflight",
        "real_scan_performed": real_scan_performed,
        "bounded_smoke_run_performed": scan_launcher_invoked,
    }
    payload.update(smoke_precheck)
    payload.update(_NO_SCOPE_FLAGS)
    payload.update(
        {
            "production_scan_performed": False,
            "input_mutation_performed": False,
            "file_move_performed": False,
            "file_rename_performed": False,
            "file_delete_performed": False,
            "media_organizer_behavior_performed": False,
            "output_overwrite_performed": False,
            "network_access_performed": False,
            "model_api_called": False,
            "external_runtime_invoked": False,
        }
    )
    return payload


def _summary_markdown(
    *,
    common: dict[str, object],
    admission: dict[str, object],
    human_approval_id: str | None,
    scan_payload: dict[str, object],
) -> str:
    scan_paths = _scan_artifact_summary_lines(scan_payload)
    lines = [
        "# Local Asset Human-Approved Smoke Run",
        "",
        "Admission result: " + str(admission["admitted"]).lower(),
        "Admission reason: " + str(admission["admission_reason"]),
        "Readiness status: " + str(admission.get("readiness_status")),
        "Readiness decision: " + str(admission.get("readiness_decision")),
        "Candidate input dir: " + str(common["candidate_input_dir"]),
        "Output dir: " + str(common["output_dir"]),
        "Scan output dir: " + str(common["scan_output_dir"]),
        "Control output dir: " + str(common["control_output_dir"]),
        "Human approval id: " + str(human_approval_id),
        "Project id: " + str(common["project_id"]),
        "Max smoke files: " + str(common["max_smoke_files"]),
        "Max smoke bytes: " + str(common["max_smoke_bytes"]),
        "Max smoke depth: " + str(common["max_smoke_depth"]),
        "Precheck file count: "
        + str(admission["smoke_precheck_file_count"]),
        "Precheck total bytes: "
        + str(admission["smoke_precheck_total_bytes"]),
        "Precheck max depth observed: "
        + str(admission["smoke_precheck_max_depth_observed"]),
        "Scan complete: " + str(admission["scan_complete"]).lower(),
        "",
        "## Scan Artifact Paths",
    ]
    lines.extend(scan_paths)
    lines.extend(
        [
            "",
            "## Boundaries",
            "- bounded smoke only",
            "- no production autonomy",
            "- no input mutation",
            "- no file move/rename/delete",
            "- no network",
            "- no model API",
            "- no external runtime",
            "- human review required",
        ]
    )
    return "\n".join(lines) + "\n"


def _scan_artifact_summary_lines(scan_payload: dict[str, object]) -> list[str]:
    path_fields = (
        "asset_manifest_path",
        "asset_index_path",
        "duplicates_report_path",
        "media_inventory_path",
        "asset_runtime_audit_log_path",
        "asset_runtime_validation_report_path",
        "asset_runtime_quarantine_manifest_path",
        "asset_scan_run_receipt_path",
        "launcher_summary_path",
        "local_asset_sqlite_index_path",
        "local_asset_sqlite_index_manifest_path",
        "local_asset_sqlite_query_summary_path",
        "local_asset_incremental_scan_plan_path",
        "local_asset_incremental_scan_manifest_path",
        "local_asset_incremental_scan_summary_path",
        "artifact_index_path",
        "artifact_index_manifest_path",
    )
    lines = []
    for field_name in path_fields:
        value = scan_payload.get(field_name)
        if isinstance(value, str) and value:
            lines.append("- " + field_name + ": " + value)
    return lines or ["- none"]


def _write_root_artifact_index(
    *,
    output_path: Path,
    control_path: Path,
    scan_path: Path,
    artifact_index_path: Path,
    artifact_index_manifest_path: Path,
    approval_path: Path | None,
    admission_path: Path,
    summary_path: Path,
    scan_payload: dict[str, object],
) -> tuple[Path, Path]:
    entries = []
    for role, path in _root_artifact_paths(
        approval_path=approval_path,
        admission_path=admission_path,
        summary_path=summary_path,
        scan_payload=scan_payload,
    ):
        if path is None:
            continue
        entries.append(_artifact_entry(output_path, role, path))
    payload = {
        "index_type": _ROOT_INDEX_TYPE,
        "authority": "non_authority",
        "execution_capability": "bounded_human_approved_local_asset_smoke_only",
        "job_dir": output_path.as_posix(),
        "control_output_dir": control_path.as_posix(),
        "scan_output_dir": scan_path.as_posix(),
        "artifact_index_strategy": "explicit_control_and_scan_refs_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "raw_content_copied": False,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "external_runtime_invoked": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_smoke_run_outputs",
    }
    _write_json_exclusive(artifact_index_path, payload)
    manifest = {
        "manifest_type": _ROOT_INDEX_MANIFEST_TYPE,
        "authority": "non_authority",
        "artifact_index_path": artifact_index_path.as_posix(),
        "artifact_index_sha256": sha256_file(artifact_index_path),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            entry["artifact_role"]: entry["path"] for entry in entries
        },
        "indexed_relative_paths": [
            entry["relative_path"] for entry in entries
        ],
        "artifact_index_strategy": "explicit_control_and_scan_refs_only",
        "recursive_artifact_indexing_performed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
    }
    _write_json_exclusive(artifact_index_manifest_path, manifest)
    return artifact_index_path, artifact_index_manifest_path


def _root_artifact_paths(
    *,
    approval_path: Path | None,
    admission_path: Path,
    summary_path: Path,
    scan_payload: dict[str, object],
) -> list[tuple[str, Path | None]]:
    paths: list[tuple[str, Path | None]] = [
        ("local_asset_human_smoke_approval", approval_path),
        ("local_asset_human_smoke_admission_receipt", admission_path),
        ("local_asset_human_smoke_run_summary", summary_path),
        (
            "local_asset_human_smoke_scan_artifact_index",
            _optional_path(scan_payload.get("artifact_index_path")),
        ),
        (
            "local_asset_human_smoke_scan_artifact_index_manifest",
            _optional_path(scan_payload.get("artifact_index_manifest_path")),
        ),
    ]
    for role, field_name in (
        ("local_asset_human_smoke_scan_asset_manifest", "asset_manifest_path"),
        ("local_asset_human_smoke_scan_asset_index", "asset_index_path"),
        ("local_asset_human_smoke_scan_duplicates_report", "duplicates_report_path"),
        ("local_asset_human_smoke_scan_media_inventory", "media_inventory_path"),
        (
            "local_asset_human_smoke_scan_asset_runtime_audit_log",
            "asset_runtime_audit_log_path",
        ),
        (
            "local_asset_human_smoke_scan_asset_runtime_validation_report",
            "asset_runtime_validation_report_path",
        ),
        (
            "local_asset_human_smoke_scan_asset_runtime_quarantine_manifest",
            "asset_runtime_quarantine_manifest_path",
        ),
        (
            "local_asset_human_smoke_scan_asset_scan_run_receipt",
            "asset_scan_run_receipt_path",
        ),
        (
            "local_asset_human_smoke_scan_launcher_summary",
            "launcher_summary_path",
        ),
        (
            "local_asset_human_smoke_scan_sqlite_index",
            "local_asset_sqlite_index_path",
        ),
        (
            "local_asset_human_smoke_scan_sqlite_index_manifest",
            "local_asset_sqlite_index_manifest_path",
        ),
        (
            "local_asset_human_smoke_scan_sqlite_query_summary",
            "local_asset_sqlite_query_summary_path",
        ),
        (
            "local_asset_human_smoke_scan_incremental_scan_plan",
            "local_asset_incremental_scan_plan_path",
        ),
        (
            "local_asset_human_smoke_scan_incremental_scan_manifest",
            "local_asset_incremental_scan_manifest_path",
        ),
        (
            "local_asset_human_smoke_scan_incremental_scan_summary",
            "local_asset_incremental_scan_summary_path",
        ),
    ):
        paths.append((role, _optional_path(scan_payload.get(field_name))))
    return paths


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


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _optional_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return Path(value)


def _read_indexed_artifact_count(index_path: Path) -> int:
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    value = payload.get("indexed_artifacts")
    return value if isinstance(value, int) else 0


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _write_summary_exclusive(path: Path, content: str) -> None:
    _write_text_exclusive(path, content)


def _write_text_exclusive(path: Path, content: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
    except FileExistsError as error:
        raise ValueError("local asset human smoke output already exists") from error
