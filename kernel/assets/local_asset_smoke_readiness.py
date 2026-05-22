"""Metadata-only real-folder smoke readiness preflight for local assets."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import json
import stat

from kernel.assets.local_asset_quarantine import (
    has_hidden_part,
    is_secret_looking_path,
    is_unsafe_directory_name,
)
from kernel.personal_ai.artifact_index import ArtifactIndexResult, build_artifact_index
from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "DEFAULT_SMOKE_READINESS_MAX_DEPTH",
    "DEFAULT_SMOKE_READINESS_MAX_ENTRIES",
    "DEFAULT_SMOKE_READINESS_MAX_TOTAL_BYTES",
    "LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE",
    "LOCAL_ASSET_SMOKE_READINESS_OUTPUT_FILENAMES",
    "LOCAL_ASSET_SMOKE_READINESS_REPORT_FILE",
    "LOCAL_ASSET_SMOKE_READINESS_SUMMARY_FILE",
    "LocalAssetSmokeReadinessResult",
    "run_local_asset_smoke_readiness",
]

LOCAL_ASSET_SMOKE_READINESS_REPORT_FILE = "local_asset_smoke_readiness_report.json"
LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE = (
    "local_asset_smoke_readiness_manifest.json"
)
LOCAL_ASSET_SMOKE_READINESS_SUMMARY_FILE = "local_asset_smoke_readiness_summary.md"
LOCAL_ASSET_SMOKE_READINESS_OUTPUT_FILENAMES = (
    LOCAL_ASSET_SMOKE_READINESS_REPORT_FILE,
    LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE,
    LOCAL_ASSET_SMOKE_READINESS_SUMMARY_FILE,
)

DEFAULT_SMOKE_READINESS_MAX_ENTRIES = 50000
DEFAULT_SMOKE_READINESS_MAX_DEPTH = 20
DEFAULT_SMOKE_READINESS_MAX_TOTAL_BYTES = 500000000000

_ARTIFACT_INDEX_FILE = "artifact_index.json"
_ARTIFACT_INDEX_MANIFEST_FILE = "artifact_index_manifest.json"
_REPORT_TYPE = "local_asset_real_folder_smoke_readiness_report_v1"
_MANIFEST_TYPE = "local_asset_real_folder_smoke_readiness_manifest_v1"
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "real_folder_smoke_readiness_only"
_NEXT_ALLOWED_ACTION = "human_review_real_folder_smoke_readiness"
_ALLOW_DECISION = "allow_human_review_for_future_smoke"
_BLOCK_DECISION = "block_future_smoke_until_review"
_ONE_MIB = 1024 * 1024

_RISK_TYPES = (
    "symlink",
    "secret_looking_path",
    "unsafe_directory",
    "hidden_path",
    "unreadable_entry",
    "unsupported_filesystem_entry",
    "traversal_limit_exceeded",
    "total_size_limit_exceeded",
    "depth_limit_exceeded",
    "output_input_overlap",
)

_BLOCKING_RISK_TYPES = {
    "symlink",
    "secret_looking_path",
    "unsafe_directory",
    "unreadable_entry",
    "unsupported_filesystem_entry",
    "output_input_overlap",
}

_LIMIT_RISK_TYPES = {
    "traversal_limit_exceeded",
    "total_size_limit_exceeded",
    "depth_limit_exceeded",
}

_BOUNDARY_FLAGS = {
    "real_scan_performed": False,
    "file_hashing_performed": False,
    "raw_content_read": False,
    "raw_content_copied": False,
    "thumbnail_generation_performed": False,
    "preview_generation_performed": False,
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

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv"}
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff"}
_DCC_EXTENSIONS = {".hip", ".hiplc", ".blend", ".uproject", ".aep", ".drp"}
_COLOR_LOOKDEV_EXTENSIONS = {".cube", ".ocio", ".hdr", ".hdri", ".mtlx"}
_FX_CACHE_EXTENSIONS = {".vdb", ".abc", ".usd", ".usda", ".usdc"}
_SCRIPT_EXTENSIONS = {".py", ".sh", ".jsx"}


@dataclass(frozen=True)
class LocalAssetSmokeReadinessResult:
    candidate_input_dir: Path
    output_dir: Path
    report_path: Path | None
    manifest_path: Path | None
    summary_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    readiness_status: str
    readiness_decision: str
    report: dict[str, object]
    artifact_index: ArtifactIndexResult | None
    artifacts_written: bool
    error_type: str | None = None
    error_message: str | None = None


def run_local_asset_smoke_readiness(
    candidate_input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = False,
    include_hidden: bool = False,
    project_id: str | None = None,
    max_entries: int = DEFAULT_SMOKE_READINESS_MAX_ENTRIES,
    max_depth: int = DEFAULT_SMOKE_READINESS_MAX_DEPTH,
    max_total_bytes: int = DEFAULT_SMOKE_READINESS_MAX_TOTAL_BYTES,
) -> LocalAssetSmokeReadinessResult:
    """Write metadata-only real-folder smoke readiness artifacts."""

    candidate_path = Path(candidate_input_dir)
    output_path = Path(output_dir)
    report_path = output_path / LOCAL_ASSET_SMOKE_READINESS_REPORT_FILE
    manifest_path = output_path / LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE
    summary_path = output_path / LOCAL_ASSET_SMOKE_READINESS_SUMMARY_FILE
    artifact_index_path = output_path / _ARTIFACT_INDEX_FILE
    artifact_index_manifest_path = output_path / _ARTIFACT_INDEX_MANIFEST_FILE

    common = _common_context(
        candidate_input_dir=candidate_path,
        output_dir=output_path,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
        max_entries=max_entries,
        max_depth=max_depth,
        max_total_bytes=max_total_bytes,
    )

    preflight_error = _output_preflight_error(output_path)
    if preflight_error is not None:
        return _failure_result(
            common=common,
            report_path=None,
            manifest_path=None,
            summary_path=None,
            artifact_index_path=None,
            artifact_index_manifest_path=None,
            error_message=preflight_error,
        )

    output_paths = {
        LOCAL_ASSET_SMOKE_READINESS_REPORT_FILE: report_path,
        LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE: manifest_path,
        LOCAL_ASSET_SMOKE_READINESS_SUMMARY_FILE: summary_path,
        _ARTIFACT_INDEX_FILE: artifact_index_path,
        _ARTIFACT_INDEX_MANIFEST_FILE: artifact_index_manifest_path,
    }
    collision = _existing_output_collision(output_paths)
    if collision is not None:
        return _failure_result(
            common=common,
            report_path=None,
            manifest_path=None,
            summary_path=None,
            artifact_index_path=None,
            artifact_index_manifest_path=None,
            error_message="local asset smoke readiness output already exists: "
            + collision,
        )

    limit_error = _limit_argument_error(max_entries, max_depth, max_total_bytes)
    if limit_error is not None:
        return _write_failed_preflight_artifacts(
            common=common,
            report_path=report_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            artifact_index_path=artifact_index_path,
            artifact_index_manifest_path=artifact_index_manifest_path,
            error_message=limit_error,
        )

    overlap = _input_output_overlap(candidate_path, output_path)
    if overlap is not None:
        report = _report_payload(
            common,
            readiness_status="failed_preflight",
            readiness_decision=_BLOCK_DECISION,
            risk_items=[
                _risk_item(
                    relative_path=".",
                    path_type="directory",
                    risk_type="output_input_overlap",
                    severity="critical",
                    detail=overlap,
                )
            ],
            skipped_items=[],
            traversal_complete=False,
            limit_exceeded=False,
            error_type="ValueError",
            error_message=overlap,
        )
        return _failure_result(
            common=common,
            report_path=None,
            manifest_path=None,
            summary_path=None,
            artifact_index_path=None,
            artifact_index_manifest_path=None,
            error_message=overlap,
            report=report,
        )

    candidate_error = _candidate_preflight_error(candidate_path)
    if candidate_error is not None:
        return _write_failed_preflight_artifacts(
            common=common,
            report_path=report_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            artifact_index_path=artifact_index_path,
            artifact_index_manifest_path=artifact_index_manifest_path,
            error_message=candidate_error,
        )

    scan = _inspect_candidate_tree(
        candidate_path,
        recursive=recursive,
        include_hidden=include_hidden,
        max_entries=max_entries,
        max_depth=max_depth,
        max_total_bytes=max_total_bytes,
    )
    readiness_status, readiness_decision = _readiness_status_and_decision(
        scan["risk_items"],
        bool(scan["limit_exceeded"]),
    )
    report = _report_payload(
        common,
        readiness_status=readiness_status,
        readiness_decision=readiness_decision,
        inspected_entry_count=scan["inspected_entry_count"],
        inspected_file_count=scan["inspected_file_count"],
        inspected_directory_count=scan["inspected_directory_count"],
        estimated_total_size_bytes=scan["estimated_total_size_bytes"],
        extension_counts=scan["extension_counts"],
        media_class_counts=scan["media_class_counts"],
        top_largest_files_by_metadata=scan["top_largest_files_by_metadata"],
        risk_items=scan["risk_items"],
        skipped_items=scan["skipped_items"],
        traversal_complete=scan["traversal_complete"],
        limit_exceeded=scan["limit_exceeded"],
    )

    try:
        _write_success_artifacts(
            report_path=report_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            report=report,
        )
        artifact_index = build_artifact_index(
            output_path,
            artifact_index_path,
            artifact_index_manifest_path,
        )
    except ValueError as error:
        return _failure_result(
            common=common,
            report_path=None,
            manifest_path=None,
            summary_path=None,
            artifact_index_path=None,
            artifact_index_manifest_path=None,
            error_type=error.__class__.__name__,
            error_message=str(error),
        )

    return LocalAssetSmokeReadinessResult(
        candidate_input_dir=candidate_path,
        output_dir=output_path,
        report_path=report_path,
        manifest_path=manifest_path,
        summary_path=summary_path,
        artifact_index_path=artifact_index.artifact_index_path,
        artifact_index_manifest_path=artifact_index.artifact_index_manifest_path,
        complete=True,
        readiness_status=readiness_status,
        readiness_decision=readiness_decision,
        report=report,
        artifact_index=artifact_index,
        artifacts_written=True,
    )


def _write_failed_preflight_artifacts(
    *,
    common: dict[str, object],
    report_path: Path,
    manifest_path: Path,
    summary_path: Path,
    artifact_index_path: Path,
    artifact_index_manifest_path: Path,
    error_message: str,
) -> LocalAssetSmokeReadinessResult:
    report = _report_payload(
        common,
        readiness_status="failed_preflight",
        readiness_decision=_BLOCK_DECISION,
        risk_items=[],
        skipped_items=[],
        traversal_complete=False,
        limit_exceeded=False,
        error_type="ValueError",
        error_message=error_message,
    )
    try:
        _write_success_artifacts(
            report_path=report_path,
            manifest_path=manifest_path,
            summary_path=summary_path,
            report=report,
        )
        artifact_index = build_artifact_index(
            Path(common["output_dir"]),
            artifact_index_path,
            artifact_index_manifest_path,
        )
    except ValueError as error:
        return _failure_result(
            common=common,
            report_path=None,
            manifest_path=None,
            summary_path=None,
            artifact_index_path=None,
            artifact_index_manifest_path=None,
            error_type=error.__class__.__name__,
            error_message=str(error),
            report=report,
        )

    return LocalAssetSmokeReadinessResult(
        candidate_input_dir=Path(common["candidate_input_dir"]),
        output_dir=Path(common["output_dir"]),
        report_path=report_path,
        manifest_path=manifest_path,
        summary_path=summary_path,
        artifact_index_path=artifact_index.artifact_index_path,
        artifact_index_manifest_path=artifact_index.artifact_index_manifest_path,
        complete=False,
        readiness_status="failed_preflight",
        readiness_decision=_BLOCK_DECISION,
        report=report,
        artifact_index=artifact_index,
        artifacts_written=True,
        error_type="ValueError",
        error_message=error_message,
    )


def _common_context(
    *,
    candidate_input_dir: Path,
    output_dir: Path,
    project_id: str | None,
    recursive: bool,
    include_hidden: bool,
    max_entries: int,
    max_depth: int,
    max_total_bytes: int,
) -> dict[str, object]:
    return {
        "candidate_input_dir": Path(candidate_input_dir).as_posix(),
        "output_dir": Path(output_dir).as_posix(),
        "project_id": project_id,
        "recursive": bool(recursive),
        "include_hidden": bool(include_hidden),
        "max_entries": int(max_entries),
        "max_depth": int(max_depth),
        "max_total_bytes": int(max_total_bytes),
    }


def _output_preflight_error(output_path: Path) -> str | None:
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    return None


def _existing_output_collision(output_paths: dict[str, Path]) -> str | None:
    for file_name in sorted(output_paths):
        if output_paths[file_name].exists():
            return file_name
    return None


def _limit_argument_error(
    max_entries: int,
    max_depth: int,
    max_total_bytes: int,
) -> str | None:
    if max_entries < 0:
        return "max_entries must be non-negative"
    if max_depth < 0:
        return "max_depth must be non-negative"
    if max_total_bytes < 0:
        return "max_total_bytes must be non-negative"
    return None


def _candidate_preflight_error(candidate_path: Path) -> str | None:
    if not candidate_path.exists():
        return "candidate_input_dir is missing"
    if not candidate_path.is_dir():
        return "candidate_input_dir is not a directory"
    if candidate_path.is_symlink():
        return "candidate_input_dir must not be a symlink"
    return None


def _input_output_overlap(candidate_path: Path, output_path: Path) -> str | None:
    try:
        candidate_resolved = candidate_path.resolve(strict=False)
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


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _inspect_candidate_tree(
    input_path: Path,
    *,
    recursive: bool,
    include_hidden: bool,
    max_entries: int,
    max_depth: int,
    max_total_bytes: int,
) -> dict[str, object]:
    extension_counts: Counter[str] = Counter()
    media_class_counts: Counter[str] = Counter()
    risk_items: list[dict[str, object]] = []
    skipped_items: list[dict[str, object]] = []
    largest_files: list[dict[str, object]] = []
    inspected_entry_count = 0
    inspected_file_count = 0
    inspected_directory_count = 0
    estimated_total_size_bytes = 0
    traversal_complete = True
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
            relative_path = _relative_path(current_dir, input_path)
            _append_risk(
                risk_items,
                relative_path=relative_path,
                path_type="directory",
                risk_type="unreadable_entry",
                severity="high",
                detail="directory could not be listed; no file contents were read",
            )
            _append_skipped(
                skipped_items,
                relative_path=relative_path,
                path_type="directory",
                reason="unreadable_entry",
                detail="directory could not be listed",
            )
            traversal_complete = False
            continue

        for child in children:
            relative_path = child.relative_to(input_path)
            relative_text = relative_path.as_posix()
            depth = len(relative_path.parts)
            inspected_entry_count += 1
            if inspected_entry_count > max_entries:
                _append_risk(
                    risk_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    risk_type="traversal_limit_exceeded",
                    severity="high",
                    detail="max_entries safety limit exceeded",
                )
                _append_skipped(
                    skipped_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    reason="traversal_limit_exceeded",
                    detail="max_entries safety limit exceeded",
                )
                traversal_complete = False
                limit_exceeded = True
                pending_dirs.clear()
                break

            if depth > max_depth:
                _append_risk(
                    risk_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    risk_type="depth_limit_exceeded",
                    severity="high",
                    detail="max_depth safety limit exceeded",
                )
                _append_skipped(
                    skipped_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    reason="depth_limit_exceeded",
                    detail="max_depth safety limit exceeded",
                )
                traversal_complete = False
                limit_exceeded = True
                continue

            try:
                metadata = child.lstat()
            except OSError:
                _append_risk(
                    risk_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    risk_type="unreadable_entry",
                    severity="high",
                    detail="entry metadata could not be read",
                )
                _append_skipped(
                    skipped_items,
                    relative_path=relative_text,
                    path_type="unknown",
                    reason="unreadable_entry",
                    detail="entry metadata could not be read",
                )
                traversal_complete = False
                continue

            mode = metadata.st_mode
            hidden = has_hidden_part(relative_path)
            secret = is_secret_looking_path(relative_path)

            if stat.S_ISLNK(mode):
                _append_risk(
                    risk_items,
                    relative_path=relative_text,
                    path_type="symlink",
                    risk_type="symlink",
                    severity="high",
                    detail="symlink was not followed",
                )
                _append_skipped(
                    skipped_items,
                    relative_path=relative_text,
                    path_type="symlink",
                    reason="symlink",
                    detail="symlink was not followed",
                )
                if hidden:
                    _append_hidden_risk(risk_items, relative_text, "symlink")
                continue

            if stat.S_ISDIR(mode):
                inspected_directory_count += 1
                if hidden:
                    _append_hidden_risk(risk_items, relative_text, "directory")
                    if not include_hidden:
                        _append_skipped(
                            skipped_items,
                            relative_path=relative_text,
                            path_type="directory",
                            reason="hidden_path",
                            detail="hidden directory skipped by default",
                        )
                        continue
                if is_unsafe_directory_name(child.name):
                    _append_risk(
                        risk_items,
                        relative_path=relative_text,
                        path_type="directory",
                        risk_type="unsafe_directory",
                        severity="high",
                        detail="unsafe directory was not traversed",
                    )
                    _append_skipped(
                        skipped_items,
                        relative_path=relative_text,
                        path_type="directory",
                        reason="unsafe_directory",
                        detail="unsafe directory was not traversed",
                    )
                    continue
                if secret:
                    _append_risk(
                        risk_items,
                        relative_path=relative_text,
                        path_type="directory",
                        risk_type="secret_looking_path",
                        severity="high",
                        detail="secret-looking directory was not traversed",
                    )
                    _append_skipped(
                        skipped_items,
                        relative_path=relative_text,
                        path_type="directory",
                        reason="secret_looking_path",
                        detail="secret-looking directory was not traversed",
                    )
                    continue
                if recursive:
                    pending_dirs.append(child)
                else:
                    _append_skipped(
                        skipped_items,
                        relative_path=relative_text,
                        path_type="directory",
                        reason="recursive_disabled",
                        detail="directory not traversed because recursive is false",
                    )
                continue

            if stat.S_ISREG(mode):
                inspected_file_count += 1
                file_size = int(metadata.st_size)
                extension = child.suffix.lower() or "[none]"
                media_class = _media_class_for_extension(extension)
                estimated_total_size_bytes += file_size
                extension_counts[extension] += 1
                media_class_counts[media_class] += 1
                largest_files.append(
                    {
                        "relative_path": relative_text,
                        "path_type": "file",
                        "extension": extension,
                        "media_class": media_class,
                        "size_bytes": file_size,
                    }
                )
                if estimated_total_size_bytes > max_total_bytes:
                    _append_risk(
                        risk_items,
                        relative_path=relative_text,
                        path_type="file",
                        risk_type="total_size_limit_exceeded",
                        severity="high",
                        detail="max_total_bytes safety limit exceeded",
                    )
                    traversal_complete = False
                    limit_exceeded = True
                if hidden:
                    _append_hidden_risk(risk_items, relative_text, "file")
                    if not include_hidden:
                        _append_skipped(
                            skipped_items,
                            relative_path=relative_text,
                            path_type="file",
                            reason="hidden_path",
                            detail="hidden file skipped by default",
                        )
                if secret:
                    _append_risk(
                        risk_items,
                        relative_path=relative_text,
                        path_type="file",
                        risk_type="secret_looking_path",
                        severity="high",
                        detail="secret-looking file contents were not read",
                    )
                if limit_exceeded:
                    pending_dirs.clear()
                    break
                continue

            _append_risk(
                risk_items,
                relative_path=relative_text,
                path_type="other",
                risk_type="unsupported_filesystem_entry",
                severity="medium",
                detail="unsupported filesystem entry was skipped",
            )
            _append_skipped(
                skipped_items,
                relative_path=relative_text,
                path_type="other",
                reason="unsupported_filesystem_entry",
                detail="unsupported filesystem entry was skipped",
            )

    return {
        "inspected_entry_count": inspected_entry_count,
        "inspected_file_count": inspected_file_count,
        "inspected_directory_count": inspected_directory_count,
        "estimated_total_size_bytes": estimated_total_size_bytes,
        "extension_counts": dict(sorted(extension_counts.items())),
        "media_class_counts": dict(sorted(media_class_counts.items())),
        "top_largest_files_by_metadata": _top_largest_files(largest_files),
        "risk_items": _sorted_records(risk_items),
        "skipped_items": _sorted_records(skipped_items),
        "traversal_complete": traversal_complete,
        "limit_exceeded": limit_exceeded,
    }


def _append_hidden_risk(risk_items, relative_path: str, path_type: str) -> None:
    _append_risk(
        risk_items,
        relative_path=relative_path,
        path_type=path_type,
        risk_type="hidden_path",
        severity="low",
        detail="hidden path detected",
    )


def _append_risk(
    risk_items: list[dict[str, object]],
    *,
    relative_path: str,
    path_type: str,
    risk_type: str,
    severity: str,
    detail: str,
) -> None:
    risk_items.append(
        _risk_item(
            relative_path=relative_path,
            path_type=path_type,
            risk_type=risk_type,
            severity=severity,
            detail=detail,
        )
    )


def _risk_item(
    *,
    relative_path: str,
    path_type: str,
    risk_type: str,
    severity: str,
    detail: str,
) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "path_type": path_type,
        "risk_type": risk_type,
        "severity": severity,
        "detail": detail,
    }


def _append_skipped(
    skipped_items: list[dict[str, object]],
    *,
    relative_path: str,
    path_type: str,
    reason: str,
    detail: str,
) -> None:
    skipped_items.append(
        {
            "relative_path": relative_path,
            "path_type": path_type,
            "reason": reason,
            "detail": detail,
        }
    )


def _relative_path(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "."
    text = relative.as_posix()
    return "." if not text else text


def _media_class_for_extension(extension: str) -> str:
    if extension in _IMAGE_EXTENSIONS:
        return "image"
    if extension in _VIDEO_EXTENSIONS:
        return "video"
    if extension in _AUDIO_EXTENSIONS:
        return "audio"
    if extension in _DCC_EXTENSIONS:
        return "dcc"
    if extension in _COLOR_LOOKDEV_EXTENSIONS:
        return "color/lookdev"
    if extension in _FX_CACHE_EXTENSIONS:
        return "fx/cache"
    if extension in _SCRIPT_EXTENSIONS:
        return "script"
    return "unknown"


def _top_largest_files(files: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        files,
        key=lambda record: (
            -int(record["size_bytes"]),
            str(record["relative_path"]),
        ),
    )[:10]


def _sorted_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        records,
        key=lambda record: (
            str(record.get("relative_path", "")),
            str(record.get("risk_type", record.get("reason", ""))),
            str(record.get("path_type", "")),
            str(record.get("detail", "")),
        ),
    )


def _readiness_status_and_decision(
    risk_items: list[dict[str, object]],
    limit_exceeded: bool,
) -> tuple[str, str]:
    risk_types = {str(item["risk_type"]) for item in risk_items}
    if limit_exceeded or risk_types.intersection(_LIMIT_RISK_TYPES):
        return "blocked_limit_exceeded", _BLOCK_DECISION
    if risk_types.intersection(_BLOCKING_RISK_TYPES):
        return "blocked_safety_risk", _BLOCK_DECISION
    if risk_items:
        return "ready_with_warnings", _ALLOW_DECISION
    return "ready", _ALLOW_DECISION


def _report_payload(
    common: dict[str, object],
    *,
    readiness_status: str,
    readiness_decision: str,
    inspected_entry_count: int = 0,
    inspected_file_count: int = 0,
    inspected_directory_count: int = 0,
    estimated_total_size_bytes: int = 0,
    extension_counts: dict[str, int] | None = None,
    media_class_counts: dict[str, int] | None = None,
    top_largest_files_by_metadata: list[dict[str, object]] | None = None,
    risk_items: list[dict[str, object]] | None = None,
    skipped_items: list[dict[str, object]] | None = None,
    traversal_complete: bool = False,
    limit_exceeded: bool = False,
    error_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, object]:
    safe_risk_items = [] if risk_items is None else _sorted_records(risk_items)
    safe_skipped_items = [] if skipped_items is None else _sorted_records(skipped_items)
    estimated_hash_chunks = _estimated_hash_chunks(estimated_total_size_bytes)
    payload = {
        "report_type": _REPORT_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "metadata_only": True,
        "readiness_status": readiness_status,
        "readiness_decision": readiness_decision,
        "candidate_input_dir": common["candidate_input_dir"],
        "output_dir": common["output_dir"],
        "project_id": common["project_id"],
        "recursive": common["recursive"],
        "include_hidden": common["include_hidden"],
        "max_entries": common["max_entries"],
        "max_depth": common["max_depth"],
        "max_total_bytes": common["max_total_bytes"],
        "inspected_entry_count": inspected_entry_count,
        "inspected_file_count": inspected_file_count,
        "inspected_directory_count": inspected_directory_count,
        "estimated_total_size_bytes": estimated_total_size_bytes,
        "estimated_hash_chunks_1mb": estimated_hash_chunks,
        "estimated_hash_cost_band": _estimated_hash_cost_band(
            estimated_hash_chunks
        ),
        "extension_counts": dict(sorted((extension_counts or {}).items())),
        "media_class_counts": dict(sorted((media_class_counts or {}).items())),
        "top_largest_files_by_metadata": top_largest_files_by_metadata or [],
        "risk_counts": _risk_counts(safe_risk_items),
        "risk_items": safe_risk_items,
        "skipped_items": safe_skipped_items,
        "limit_exceeded": bool(limit_exceeded),
        "traversal_complete": bool(traversal_complete),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    payload.update(_BOUNDARY_FLAGS)
    if error_type is not None:
        payload["error_type"] = error_type
    if error_message is not None:
        payload["error_message"] = error_message
    return payload


def _risk_counts(risk_items: list[dict[str, object]]) -> dict[str, int]:
    counts = {risk_type: 0 for risk_type in _RISK_TYPES}
    for item in risk_items:
        risk_type = str(item["risk_type"])
        counts[risk_type] = counts.get(risk_type, 0) + 1
    return dict(sorted(counts.items()))


def _estimated_hash_chunks(total_size_bytes: int) -> int:
    if total_size_bytes <= 0:
        return 0
    return (total_size_bytes + _ONE_MIB - 1) // _ONE_MIB


def _estimated_hash_cost_band(chunks: int) -> str:
    if chunks <= 10:
        return "tiny"
    if chunks <= 100:
        return "small"
    if chunks <= 1000:
        return "medium"
    if chunks <= 10000:
        return "large"
    return "extreme"


def _write_success_artifacts(
    *,
    report_path: Path,
    manifest_path: Path,
    summary_path: Path,
    report: dict[str, object],
) -> dict[str, object]:
    _write_json_exclusive(report_path, report)
    summary = _summary_markdown(report)
    _write_text_exclusive(summary_path, summary)
    manifest = _manifest_payload(
        report_path=report_path,
        summary_path=summary_path,
        report=report,
    )
    _write_json_exclusive(manifest_path, manifest)
    return manifest


def _manifest_payload(
    *,
    report_path: Path,
    summary_path: Path,
    report: dict[str, object],
) -> dict[str, object]:
    payload = {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "report_path": report_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "report_sha256": sha256_file(report_path),
        "summary_sha256": sha256_file(summary_path),
        "readiness_status": report["readiness_status"],
        "readiness_decision": report["readiness_decision"],
        "artifact_roles": {
            "local_asset_smoke_readiness_report": report_path.as_posix(),
            "local_asset_smoke_readiness_manifest": (
                report_path.parent
                / LOCAL_ASSET_SMOKE_READINESS_MANIFEST_FILE
            ).as_posix(),
            "local_asset_smoke_readiness_summary": summary_path.as_posix(),
        },
        "deterministic_ordering": True,
        "metadata_only": True,
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }
    payload.update(_BOUNDARY_FLAGS)
    return payload


def _summary_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Local Asset Smoke Readiness",
        "",
        "Readiness status: " + str(report["readiness_status"]),
        "Readiness decision: " + str(report["readiness_decision"]),
        "Candidate input dir: " + str(report["candidate_input_dir"]),
        "Output dir: " + str(report["output_dir"]),
        "Project id: " + str(report["project_id"]),
        "Recursive: " + str(report["recursive"]).lower(),
        "Include hidden: " + str(report["include_hidden"]).lower(),
        "Inspected entries: " + str(report["inspected_entry_count"]),
        "Inspected files: " + str(report["inspected_file_count"]),
        "Inspected directories: " + str(report["inspected_directory_count"]),
        "Estimated total bytes: " + str(report["estimated_total_size_bytes"]),
        "Estimated hash cost band: " + str(report["estimated_hash_cost_band"]),
        "",
        "## Extension Counts",
    ]
    lines.extend(_count_lines(report["extension_counts"]))
    lines.extend(["", "## Media Class Counts"])
    lines.extend(_count_lines(report["media_class_counts"]))
    lines.extend(["", "## Risk Counts"])
    lines.extend(_count_lines(report["risk_counts"]))
    lines.extend(["", "## Top Largest Files By Metadata"])
    top_files = report["top_largest_files_by_metadata"]
    if not top_files:
        lines.append("- none")
    else:
        for item in top_files:
            lines.append(
                "- "
                + str(item["relative_path"])
                + " | "
                + str(item["size_bytes"])
                + " bytes | "
                + str(item["media_class"])
            )
    lines.extend(
        [
            "",
            "No real scan performed.",
            "No file hashing performed.",
            "No raw content read.",
            "No input mutation.",
            "No file movement/rename/delete.",
            "Human approval required before real-folder smoke.",
            "",
            "Next recommended action: human review real folder smoke readiness.",
        ]
    )
    return "\n".join(lines) + "\n"


def _count_lines(counts: object) -> list[str]:
    if not isinstance(counts, dict) or not counts:
        return ["- none"]
    return [
        "- " + str(name) + ": " + str(counts[name])
        for name in sorted(counts)
    ]


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _write_text_exclusive(path: Path, content: str) -> None:
    try:
        with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(content)
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(
            "local asset smoke readiness output already exists: "
            + Path(path).name
        ) from error


def _failure_result(
    *,
    common: dict[str, object],
    report_path: Path | None,
    manifest_path: Path | None,
    summary_path: Path | None,
    artifact_index_path: Path | None,
    artifact_index_manifest_path: Path | None,
    error_message: str,
    error_type: str = "ValueError",
    report: dict[str, object] | None = None,
) -> LocalAssetSmokeReadinessResult:
    failure_report = report or _report_payload(
        common,
        readiness_status="failed_preflight",
        readiness_decision=_BLOCK_DECISION,
        risk_items=[],
        skipped_items=[],
        traversal_complete=False,
        limit_exceeded=False,
        error_type=error_type,
        error_message=error_message,
    )
    return LocalAssetSmokeReadinessResult(
        candidate_input_dir=Path(common["candidate_input_dir"]),
        output_dir=Path(common["output_dir"]),
        report_path=report_path,
        manifest_path=manifest_path,
        summary_path=summary_path,
        artifact_index_path=artifact_index_path,
        artifact_index_manifest_path=artifact_index_manifest_path,
        complete=False,
        readiness_status=str(failure_report["readiness_status"]),
        readiness_decision=str(failure_report["readiness_decision"]),
        report=failure_report,
        artifact_index=None,
        artifacts_written=False,
        error_type=error_type,
        error_message=error_message,
    )
