"""Operational control artifacts for the local asset scan launcher."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json

from kernel.assets.local_asset_sqlite_index import LOCAL_ASSET_SQLITE_OUTPUT_FILENAMES
from kernel.assets.local_asset_schema import OUTPUT_FILENAMES

__all__ = [
    "ASSET_SCAN_FAILURE_BUNDLE_FILE",
    "ASSET_SCAN_FAILURE_SUMMARY_FILE",
    "ASSET_SCAN_RUN_RECEIPT_FILE",
    "AssetScanFailureArtifacts",
    "asset_scan_failure_artifact_paths",
    "asset_scan_failure_cli_payload",
    "asset_scan_output_status",
    "asset_scan_run_receipt_path",
    "classify_asset_scan_failure_stage",
    "pre_runtime_collision_stage",
    "write_asset_scan_failure_bundle",
    "write_asset_scan_run_receipt",
]

ASSET_SCAN_RUN_RECEIPT_FILE = "asset_scan_run_receipt.json"
ASSET_SCAN_FAILURE_BUNDLE_FILE = "asset_scan_failure_bundle.json"
ASSET_SCAN_FAILURE_SUMMARY_FILE = "asset_scan_failure_summary.md"

_WORKFLOW = "local_asset_scan_workflow"
_RECEIPT_TYPE = "local_asset_scan_operational_receipt_v1"
_FAILURE_BUNDLE_TYPE = "local_asset_scan_failure_bundle_v1"
_LAUNCHER_SUMMARY_FILE = "launcher_summary.md"
_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_MAX_ERROR_MESSAGE_LENGTH = 240

_SENSITIVE_TOKEN_MARKERS = (
    "SECRET",
    "SENTINEL",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "API_KEY",
    "BEARER",
    "COOKIE",
)

_NO_SCOPE_EXPANSION_FLAGS = {
    "input_mutation_performed": False,
    "file_move_performed": False,
    "file_rename_performed": False,
    "file_delete_performed": False,
    "media_organizer_behavior_performed": False,
    "local_asset_sqlite_content_indexed": False,
    "local_asset_sqlite_raw_content_copied": False,
    "output_overwrite_performed": False,
    "network_access_performed": False,
    "model_api_called": False,
    "desktop_ui_added": False,
    "browser_runtime_invoked": False,
    "comfyui_runtime_invoked": False,
    "blender_runtime_invoked": False,
    "houdini_runtime_invoked": False,
    "after_effects_runtime_invoked": False,
    "davinci_runtime_invoked": False,
    "external_runtime_invoked": False,
}

_RUNTIME_ARTIFACT_NAMES_BY_FILE = {
    "asset_manifest.json": "asset_manifest",
    "asset_index.json": "asset_index",
    "duplicates_report.json": "duplicates_report",
    "media_inventory.md": "media_inventory",
    "asset_runtime_audit_log.jsonl": "asset_runtime_audit_log",
    "asset_runtime_validation_report.json": "asset_runtime_validation_report",
    "asset_runtime_quarantine_manifest.json": "asset_runtime_quarantine_manifest",
}

_CONTROLLED_OUTPUT_FILES = (
    *OUTPUT_FILENAMES,
    _LAUNCHER_SUMMARY_FILE,
    ASSET_SCAN_RUN_RECEIPT_FILE,
    *LOCAL_ASSET_SQLITE_OUTPUT_FILENAMES,
    _ARTIFACT_INDEX_FILE,
    _ARTIFACT_INDEX_MANIFEST_FILE,
    ASSET_SCAN_FAILURE_BUNDLE_FILE,
    ASSET_SCAN_FAILURE_SUMMARY_FILE,
)


@dataclass(frozen=True)
class AssetScanFailureArtifacts:
    failure_bundle_path: Path
    failure_summary_path: Path
    cli_payload: dict[str, object]


def asset_scan_run_receipt_path(output_dir: Path) -> Path:
    return Path(output_dir) / ASSET_SCAN_RUN_RECEIPT_FILE


def asset_scan_failure_artifact_paths(output_dir: Path) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    return (
        output_path / ASSET_SCAN_FAILURE_BUNDLE_FILE,
        output_path / ASSET_SCAN_FAILURE_SUMMARY_FILE,
    )


def pre_runtime_collision_stage(output_dir: Path) -> str | None:
    output_path = Path(output_dir)
    if (output_path / _ARTIFACT_INDEX_FILE).exists():
        return "preflight_artifact_index_collision"
    if (output_path / _ARTIFACT_INDEX_MANIFEST_FILE).exists():
        return "preflight_artifact_index_collision"
    for file_name in LOCAL_ASSET_SQLITE_OUTPUT_FILENAMES:
        if (output_path / file_name).exists():
            return "preflight_sqlite_index_collision"
    for file_name in (
        _LAUNCHER_SUMMARY_FILE,
        ASSET_SCAN_RUN_RECEIPT_FILE,
        ASSET_SCAN_FAILURE_BUNDLE_FILE,
        ASSET_SCAN_FAILURE_SUMMARY_FILE,
    ):
        if (output_path / file_name).exists():
            return "preflight_launcher_output_collision"
    return None


def asset_scan_output_status(output_dir: Path) -> dict[str, list[str] | bool]:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        return {
            "partial_outputs_written": [],
            "partial_outputs_absent": list(_CONTROLLED_OUTPUT_FILES),
            "output_pollution_detected": False,
        }

    partial_outputs_written = [
        file_name
        for file_name in _CONTROLLED_OUTPUT_FILES
        if (output_path / file_name).exists()
    ]
    partial_outputs_absent = [
        file_name
        for file_name in _CONTROLLED_OUTPUT_FILES
        if file_name not in partial_outputs_written
    ]
    return {
        "partial_outputs_written": partial_outputs_written,
        "partial_outputs_absent": partial_outputs_absent,
        "output_pollution_detected": bool(partial_outputs_written),
    }


def write_asset_scan_run_receipt(
    *,
    input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    files_scanned: int,
    bytes_scanned: int,
    duplicate_groups: int,
    quarantined_paths: int,
    asset_runtime_output_paths: dict[str, Path],
    launcher_summary_path: Path,
    artifact_index_path: Path,
    artifact_index_manifest_path: Path,
    local_asset_sqlite_index_path: Path | None = None,
    local_asset_sqlite_index_manifest_path: Path | None = None,
    local_asset_sqlite_query_summary_path: Path | None = None,
) -> Path:
    output_path = Path(output_dir)
    receipt_path = asset_scan_run_receipt_path(output_path)
    _require_absent(receipt_path)
    scan_completed_with_quarantine = quarantined_paths > 0
    payload = {
        "receipt_type": _RECEIPT_TYPE,
        "workflow": _WORKFLOW,
        "status": "completed",
        "input_dir": Path(input_dir).as_posix(),
        "output_dir": output_path.as_posix(),
        "project_id": project_id,
        "recursive": recursive,
        "include_hidden": include_hidden,
        "files_scanned": files_scanned,
        "bytes_scanned": bytes_scanned,
        "duplicate_groups": duplicate_groups,
        "quarantined_paths": quarantined_paths,
        "quarantined_path_count": quarantined_paths,
        "scan_completed_with_quarantine": scan_completed_with_quarantine,
        "success_artifacts": _success_artifacts(
            output_path,
            asset_runtime_output_paths,
            launcher_summary_path,
            receipt_path,
        ),
        "artifact_index_path": Path(artifact_index_path).as_posix(),
        "artifact_index_manifest_path": (
            Path(artifact_index_manifest_path).as_posix()
        ),
        "local_asset_sqlite_index_path": None
        if local_asset_sqlite_index_path is None
        else Path(local_asset_sqlite_index_path).as_posix(),
        "local_asset_sqlite_index_manifest_path": None
        if local_asset_sqlite_index_manifest_path is None
        else Path(local_asset_sqlite_index_manifest_path).as_posix(),
        "local_asset_sqlite_query_summary_path": None
        if local_asset_sqlite_query_summary_path is None
        else Path(local_asset_sqlite_query_summary_path).as_posix(),
        "local_asset_sqlite_index_authority": "non_authority",
        "local_asset_sqlite_index_scope": "per_scan_output_dir_only",
        "local_asset_sqlite_content_indexed": False,
        "local_asset_sqlite_raw_content_copied": False,
        "safe_to_retry": True,
        "replay_hint": _replay_hint("completed"),
        **_NO_SCOPE_EXPANSION_FLAGS,
        "required_human_approval": True,
        "next_allowed_action": "human_review_asset_scan_outputs",
        "recommended_next_action": (
            "human_review_quarantine_manifest"
            if scan_completed_with_quarantine
            else "human_review_asset_scan_outputs"
        ),
    }
    _write_json_exclusive(receipt_path, payload)
    return receipt_path


def write_asset_scan_failure_bundle(
    *,
    input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    failure_stage: str,
    error_type: str,
    error_message: str,
    output_pollution_detected: bool | None = None,
) -> AssetScanFailureArtifacts:
    output_path = Path(output_dir)
    bundle_path, summary_path = asset_scan_failure_artifact_paths(output_path)
    _require_absent(bundle_path)
    _require_absent(summary_path)

    bundle_payload = _failure_bundle_payload(
        input_dir=input_dir,
        output_dir=output_path,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        failure_stage=failure_stage,
        error_type=error_type,
        error_message=error_message,
        output_pollution_detected=output_pollution_detected,
    )
    bundle_payload["failure_bundle_path"] = bundle_path.as_posix()
    bundle_payload["failure_summary_path"] = summary_path.as_posix()

    _write_json_exclusive(bundle_path, bundle_payload)
    _write_text_exclusive(summary_path, _failure_summary_markdown(bundle_payload))

    return AssetScanFailureArtifacts(
        failure_bundle_path=bundle_path,
        failure_summary_path=summary_path,
        cli_payload=_failure_cli_payload(
            bundle_payload,
            failure_bundle_path=bundle_path,
            failure_summary_path=summary_path,
            failure_bundle_written=True,
        ),
    )


def asset_scan_failure_cli_payload(
    *,
    input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    failure_stage: str,
    error_type: str,
    error_message: str,
    output_pollution_detected: bool | None = None,
) -> dict[str, object]:
    bundle_payload = _failure_bundle_payload(
        input_dir=input_dir,
        output_dir=output_dir,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        failure_stage=failure_stage,
        error_type=error_type,
        error_message=error_message,
        output_pollution_detected=output_pollution_detected,
    )
    return _failure_cli_payload(
        bundle_payload,
        failure_bundle_path=None,
        failure_summary_path=None,
        failure_bundle_written=False,
    )


def classify_asset_scan_failure_stage(error_message: str) -> str:
    message = str(error_message)
    if "input_dir is missing" in message:
        return "preflight_input_dir_missing"
    if "output_dir is missing" in message:
        return "preflight_output_dir_missing"
    if "launcher output already exists" in message:
        return "preflight_launcher_output_collision"
    if "artifact_index" in message and "already exists" in message:
        return "preflight_artifact_index_collision"
    if "local asset sqlite index output already exists" in message:
        return "preflight_sqlite_index_collision"
    if "asset runtime output already exists" in message:
        return "runtime_output_collision"
    if (
        "input_dir" in message
        or "output_dir" in message
        or "validation" in message.lower()
    ):
        return "runtime_validation_failure"
    if "artifact index" in message.lower() or "artifact_index" in message:
        return "artifact_index_failure"
    if "sqlite" in message.lower():
        return "sqlite_index_failure"
    return "unknown_asset_scan_failure"


def _failure_bundle_payload(
    *,
    input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    failure_stage: str,
    error_type: str,
    error_message: str,
    output_pollution_detected: bool | None,
) -> dict[str, object]:
    safe_message = _safe_error_message(error_message)
    output_status = asset_scan_output_status(Path(output_dir))
    pollution_detected = (
        output_status["output_pollution_detected"]
        if output_pollution_detected is None
        else bool(output_pollution_detected)
    )
    return {
        "bundle_type": _FAILURE_BUNDLE_TYPE,
        "workflow": _WORKFLOW,
        "status": "failed",
        "failure_stage": failure_stage,
        "error_type": _safe_error_type(error_type),
        "safe_error_message": safe_message,
        "error_message_sha256": sha256(safe_message.encode("utf-8")).hexdigest(),
        "input_dir": Path(input_dir).as_posix(),
        "output_dir": Path(output_dir).as_posix(),
        "project_id": project_id,
        "recursive": recursive,
        "include_hidden": include_hidden,
        "partial_outputs_written": output_status["partial_outputs_written"],
        "partial_outputs_absent": output_status["partial_outputs_absent"],
        "output_pollution_detected": pollution_detected,
        "safe_to_retry": _safe_to_retry(failure_stage),
        "replay_hint": _replay_hint(failure_stage),
        "recommended_next_action": _recommended_next_action(failure_stage),
        **_NO_SCOPE_EXPANSION_FLAGS,
        "raw_traceback_persisted": False,
        "raw_exception_dump_persisted": False,
        "secret_value_serialized": False,
        "required_human_approval": True,
    }


def _failure_cli_payload(
    bundle_payload: dict[str, object],
    *,
    failure_bundle_path: Path | None,
    failure_summary_path: Path | None,
    failure_bundle_written: bool,
) -> dict[str, object]:
    payload = {
        "complete": False,
        "error_type": bundle_payload["error_type"],
        "error_message": bundle_payload["safe_error_message"],
        "failure_stage": bundle_payload["failure_stage"],
        "failure_bundle_path": None
        if failure_bundle_path is None
        else failure_bundle_path.as_posix(),
        "failure_summary_path": None
        if failure_summary_path is None
        else failure_summary_path.as_posix(),
        "failure_bundle_written": failure_bundle_written,
        "partial_outputs_written": bundle_payload["partial_outputs_written"],
        "partial_outputs_absent": bundle_payload["partial_outputs_absent"],
        "output_pollution_detected": bundle_payload["output_pollution_detected"],
        "safe_to_retry": bundle_payload["safe_to_retry"],
        "replay_hint": bundle_payload["replay_hint"],
        "recommended_next_action": bundle_payload["recommended_next_action"],
        "required_human_approval": True,
    }
    payload.update(_NO_SCOPE_EXPANSION_FLAGS)
    return payload


def _success_artifacts(
    output_dir: Path,
    asset_runtime_output_paths: dict[str, Path],
    launcher_summary_path: Path,
    receipt_path: Path,
) -> list[dict[str, str]]:
    artifact_files = []
    for file_name in sorted(asset_runtime_output_paths):
        artifact_files.append(
            {
                "artifact_name": _RUNTIME_ARTIFACT_NAMES_BY_FILE[file_name],
                "relative_path": Path(file_name).as_posix(),
                "path": Path(asset_runtime_output_paths[file_name]).as_posix(),
            }
        )
    artifact_files.append(
        {
            "artifact_name": "launcher_summary",
            "relative_path": launcher_summary_path.relative_to(output_dir).as_posix(),
            "path": Path(launcher_summary_path).as_posix(),
        }
    )
    artifact_files.append(
        {
            "artifact_name": "asset_scan_run_receipt",
            "relative_path": receipt_path.relative_to(output_dir).as_posix(),
            "path": receipt_path.as_posix(),
        }
    )
    return sorted(artifact_files, key=lambda artifact: artifact["artifact_name"])


def _safe_to_retry(failure_stage: str) -> bool:
    return failure_stage in {
        "preflight_launcher_output_collision",
        "preflight_artifact_index_collision",
        "preflight_sqlite_index_collision",
        "runtime_output_collision",
        "artifact_index_failure",
        "sqlite_index_failure",
    }


def _replay_hint(stage: str) -> str:
    if stage == "preflight_output_dir_missing":
        return (
            "Create an empty output_dir after human review; the launcher will not "
            "create it automatically."
        )
    if stage == "preflight_input_dir_missing":
        return "Confirm input_dir exists before rerunning the same command."
    return (
        "Rerun launch-local-asset-scan with the same input_dir and flags using a "
        "new empty output_dir; do not reuse this output_dir."
    )


def _recommended_next_action(failure_stage: str) -> str:
    if failure_stage == "preflight_input_dir_missing":
        return "human_review_input_dir"
    if failure_stage == "preflight_output_dir_missing":
        return "human_create_empty_output_dir_then_retry"
    if failure_stage in {
        "preflight_launcher_output_collision",
        "preflight_artifact_index_collision",
        "preflight_sqlite_index_collision",
        "runtime_output_collision",
    }:
        return "human_choose_fresh_output_dir"
    if failure_stage in {"artifact_index_failure", "sqlite_index_failure"}:
        return "human_review_partial_asset_scan_outputs"
    return "human_review_asset_scan_failure_bundle"


def _failure_summary_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Local Asset Scan Failure Summary",
        "",
        f"- Workflow: `{payload['workflow']}`",
        "- Status: failed",
        f"- Failure stage: `{payload['failure_stage']}`",
        f"- Error type: `{payload['error_type']}`",
        f"- Safe error message: {payload['safe_error_message']}",
        f"- Output pollution detected: {str(payload['output_pollution_detected']).lower()}",
        f"- Safe to retry: {str(payload['safe_to_retry']).lower()}",
        f"- Replay hint: {payload['replay_hint']}",
        f"- Recommended next action: `{payload['recommended_next_action']}`",
        "- Required human approval: true",
        "",
        "Boundary: read-only local asset scan; no input mutation, file movement, "
        "network access, model API, or external runtime invocation was performed.",
    ]
    return "\n".join(lines) + "\n"


def _safe_error_type(error_type: str) -> str:
    compact = "".join(
        character
        for character in str(error_type)
        if character.isalnum() or character in "._-"
    )
    return compact[:80] or "AssetScanFailure"


def _safe_error_message(error_message: str) -> str:
    compact = " ".join(str(error_message).split())
    trace_marker = "Traceback (most recent call last)"
    if trace_marker in compact:
        compact = compact.split(trace_marker, 1)[0].strip()
    redacted_tokens = [
        _redact_token(token)
        for token in compact.split(" ")
        if token
    ]
    safe_message = " ".join(redacted_tokens) or "asset scan failed"
    if len(safe_message) > _MAX_ERROR_MESSAGE_LENGTH:
        return safe_message[: _MAX_ERROR_MESSAGE_LENGTH - 3] + "..."
    return safe_message


def _redact_token(token: str) -> str:
    upper_token = token.upper()
    if any(marker in upper_token for marker in _SENSITIVE_TOKEN_MARKERS):
        return "[redacted-sensitive-token]"
    return token


def _require_absent(path: Path) -> None:
    if Path(path).exists():
        raise ValueError("asset scan operational control output already exists")


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
        output_file.flush()


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()
