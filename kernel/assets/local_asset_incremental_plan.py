"""Metadata-only incremental scan planning for local asset scan outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.assets.local_asset_schema import (
    ASSET_INDEX_FILE,
    ASSET_MANIFEST_FILE,
    DUPLICATES_REPORT_FILE,
    QUARANTINE_MANIFEST_FILE,
)
from kernel.assets.local_asset_sqlite_index import (
    LOCAL_ASSET_SQLITE_INDEX_FILE,
    LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
)
from kernel.personal_ai.hash_utils import sha256_file, sha256_text

__all__ = [
    "LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE",
    "LOCAL_ASSET_INCREMENTAL_OUTPUT_FILENAMES",
    "LOCAL_ASSET_INCREMENTAL_PLAN_FILE",
    "LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE",
    "LocalAssetIncrementalPlanResult",
    "build_local_asset_incremental_plan",
    "validate_previous_scan_output_dir",
]

LOCAL_ASSET_INCREMENTAL_PLAN_FILE = "local_asset_incremental_scan_plan.json"
LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE = "local_asset_incremental_scan_manifest.json"
LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE = "local_asset_incremental_scan_summary.md"
LOCAL_ASSET_INCREMENTAL_OUTPUT_FILENAMES = (
    LOCAL_ASSET_INCREMENTAL_PLAN_FILE,
    LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE,
    LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE,
)

_PLAN_TYPE = "local_asset_incremental_scan_plan_v1"
_MANIFEST_TYPE = "local_asset_incremental_scan_manifest_v1"
_AUTHORITY = "non_authority"
_EXECUTION_CAPABILITY = "local_asset_incremental_planning_only"
_NEXT_ALLOWED_ACTION = "human_review_incremental_scan_plan"
_BASELINE_MODE = "baseline_no_previous_scan"
_COMPARE_MODE = "compare_previous_scan"

_SOURCE_ARTIFACTS = (
    ("asset_manifest", ASSET_MANIFEST_FILE, True),
    ("asset_index", ASSET_INDEX_FILE, True),
    ("duplicates_report", DUPLICATES_REPORT_FILE, True),
    ("asset_runtime_quarantine_manifest", QUARANTINE_MANIFEST_FILE, True),
    ("local_asset_sqlite_index", LOCAL_ASSET_SQLITE_INDEX_FILE, False),
    (
        "local_asset_sqlite_index_manifest",
        LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
        False,
    ),
)

_BOUNDARY_FLAGS = {
    "cache_execution_performed": False,
    "automatic_skip_performed": False,
    "raw_content_copied": False,
    "content_indexed": False,
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
class LocalAssetIncrementalPlanResult:
    output_dir: Path
    plan_path: Path
    manifest_path: Path
    summary_path: Path
    plan_mode: str
    current_asset_count: int
    previous_asset_count: int
    unchanged_asset_count: int
    changed_asset_count: int
    new_asset_count: int
    missing_asset_count: int
    duplicate_state_changed_count: int
    quarantine_state_changed_count: int
    suspicious_change_count: int


@dataclass(frozen=True)
class _ScanSnapshot:
    output_dir: Path | None
    source_artifacts: list[dict[str, object]]
    asset_manifest: dict[str, object] | None
    asset_index: dict[str, object] | None
    duplicates_report: dict[str, object] | None
    quarantine_manifest: dict[str, object] | None
    assets_by_path: dict[str, dict[str, object]]
    duplicate_state_by_path: dict[str, dict[str, object]]
    quarantine_state_by_path: dict[str, dict[str, object]]
    suspicious_changes: list[dict[str, object]]


def build_local_asset_incremental_plan(
    output_dir: Path,
    *,
    previous_scan_output_dir: Path | None = None,
    project_id: str | None = None,
    recursive: bool | None = None,
    include_hidden: bool | None = None,
) -> LocalAssetIncrementalPlanResult:
    """Build deterministic incremental planning artifacts in one scan output dir."""

    output_path = _validate_current_output_dir(output_dir)
    previous_path = (
        None
        if previous_scan_output_dir is None
        else validate_previous_scan_output_dir(output_path, previous_scan_output_dir)
    )
    output_paths = _incremental_output_paths(output_path)
    _require_outputs_absent(output_paths)

    current = _read_scan_snapshot(output_path, scan_label="current")
    _validate_current_manifest_flags(
        current.asset_manifest,
        project_id=project_id,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    previous = (
        _empty_previous_snapshot()
        if previous_path is None
        else _read_scan_snapshot(previous_path, scan_label="previous")
    )

    plan_mode = _BASELINE_MODE if previous_path is None else _COMPARE_MODE
    classifications = _classify_assets(current, previous, plan_mode=plan_mode)
    summary_content = _summary_markdown(
        output_dir=output_path,
        previous_scan_output_dir=previous_path,
        plan_mode=plan_mode,
        current=current,
        previous=previous,
        classifications=classifications,
    )
    plan_payload = _plan_payload(
        output_dir=output_path,
        previous_scan_output_dir=previous_path,
        plan_mode=plan_mode,
        current=current,
        previous=previous,
        classifications=classifications,
    )

    _write_json_exclusive(
        output_paths[LOCAL_ASSET_INCREMENTAL_PLAN_FILE],
        plan_payload,
    )
    manifest_payload = _manifest_payload(
        plan_path=output_paths[LOCAL_ASSET_INCREMENTAL_PLAN_FILE],
        manifest_path=output_paths[LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE],
        summary_path=output_paths[LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE],
        summary_content=summary_content,
        plan_mode=plan_mode,
        current=current,
        previous=previous,
        classifications=classifications,
    )
    _write_json_exclusive(
        output_paths[LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE],
        manifest_payload,
    )
    _write_text_exclusive(
        output_paths[LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE],
        summary_content,
    )

    return LocalAssetIncrementalPlanResult(
        output_dir=output_path,
        plan_path=output_paths[LOCAL_ASSET_INCREMENTAL_PLAN_FILE],
        manifest_path=output_paths[LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE],
        summary_path=output_paths[LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE],
        plan_mode=plan_mode,
        current_asset_count=classifications["current_asset_count"],
        previous_asset_count=classifications["previous_asset_count"],
        unchanged_asset_count=len(classifications["unchanged_assets"]),
        changed_asset_count=len(classifications["changed_assets"]),
        new_asset_count=len(classifications["new_assets"]),
        missing_asset_count=len(classifications["missing_assets"]),
        duplicate_state_changed_count=len(classifications["duplicate_state_changes"]),
        quarantine_state_changed_count=len(
            classifications["quarantine_state_changes"]
        ),
        suspicious_change_count=len(classifications["suspicious_changes"]),
    )


def validate_previous_scan_output_dir(
    output_dir: Path,
    previous_scan_output_dir: Path,
) -> Path:
    """Validate the optional previous output dir without reading raw assets."""

    output_path = _validate_current_output_dir(output_dir)
    previous_path = Path(previous_scan_output_dir)
    if not previous_path.exists():
        raise ValueError("previous_scan_output_dir is missing")
    if not previous_path.is_dir():
        raise ValueError("previous_scan_output_dir is not a directory")
    if previous_path.is_symlink():
        raise ValueError("previous_scan_output_dir must not be a symlink")

    output_resolved = output_path.resolve(strict=True)
    previous_resolved = previous_path.resolve(strict=True)
    if output_resolved == previous_resolved:
        raise ValueError("previous_scan_output_dir must not equal output_dir")
    if _path_is_inside(previous_resolved, output_resolved):
        raise ValueError("previous_scan_output_dir must not be inside output_dir")
    if _path_is_inside(output_resolved, previous_resolved):
        raise ValueError("output_dir must not be inside previous_scan_output_dir")

    _source_artifact_records(previous_path, scan_label="previous")
    return previous_path


def _validate_current_output_dir(output_dir: Path) -> Path:
    output_path = Path(output_dir)
    if not output_path.exists():
        raise ValueError("local asset incremental output_dir is missing")
    if not output_path.is_dir():
        raise ValueError("local asset incremental output_dir is not a directory")
    if output_path.is_symlink():
        raise ValueError("local asset incremental output_dir must not be a symlink")
    return output_path


def _incremental_output_paths(output_path: Path) -> dict[str, Path]:
    paths = {
        file_name: output_path / file_name
        for file_name in LOCAL_ASSET_INCREMENTAL_OUTPUT_FILENAMES
    }
    for file_name, path in paths.items():
        _require_inside_output_dir(path, output_path, file_name)
    return paths


def _require_inside_output_dir(path: Path, output_path: Path, label: str) -> None:
    try:
        Path(path).resolve(strict=False).relative_to(output_path.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ValueError("local asset incremental output escapes output_dir: " + label) from error


def _require_outputs_absent(paths: dict[str, Path]) -> None:
    for file_name in sorted(paths):
        if paths[file_name].exists():
            raise ValueError(
                "local asset incremental output already exists: " + file_name
            )


def _read_scan_snapshot(output_dir: Path, *, scan_label: str) -> _ScanSnapshot:
    source_artifacts = _source_artifact_records(output_dir, scan_label=scan_label)
    asset_manifest = _read_required_json(
        output_dir / ASSET_MANIFEST_FILE,
        scan_label + " asset_manifest",
    )
    asset_index = _read_required_json(
        output_dir / ASSET_INDEX_FILE,
        scan_label + " asset_index",
    )
    duplicates_report = _read_required_json(
        output_dir / DUPLICATES_REPORT_FILE,
        scan_label + " duplicates_report",
    )
    quarantine_manifest = _read_required_json(
        output_dir / QUARANTINE_MANIFEST_FILE,
        scan_label + " asset_runtime_quarantine_manifest",
    )

    assets_by_path = _assets_by_path(asset_manifest, scan_label)
    suspicious_changes = []
    duplicate_state_by_path = _duplicate_state_by_path(
        assets_by_path,
        duplicates_report,
        scan_label=scan_label,
        suspicious_changes=suspicious_changes,
    )
    quarantine_state_by_path = _quarantine_state_by_path(
        quarantine_manifest,
        scan_label=scan_label,
    )
    suspicious_changes.extend(
        _scan_contradictions(
            scan_label=scan_label,
            assets_by_path=assets_by_path,
            duplicate_state_by_path=duplicate_state_by_path,
            quarantine_state_by_path=quarantine_state_by_path,
        )
    )
    return _ScanSnapshot(
        output_dir=output_dir,
        source_artifacts=source_artifacts,
        asset_manifest=asset_manifest,
        asset_index=asset_index,
        duplicates_report=duplicates_report,
        quarantine_manifest=quarantine_manifest,
        assets_by_path=assets_by_path,
        duplicate_state_by_path=duplicate_state_by_path,
        quarantine_state_by_path=quarantine_state_by_path,
        suspicious_changes=sorted(
            suspicious_changes,
            key=lambda record: (
                str(record.get("relative_path", "")),
                str(record.get("change_type", "")),
                str(record.get("scan", "")),
            ),
        ),
    )


def _empty_previous_snapshot() -> _ScanSnapshot:
    return _ScanSnapshot(
        output_dir=None,
        source_artifacts=_null_source_artifact_records(),
        asset_manifest=None,
        asset_index=None,
        duplicates_report=None,
        quarantine_manifest=None,
        assets_by_path={},
        duplicate_state_by_path={},
        quarantine_state_by_path={},
        suspicious_changes=[],
    )


def _source_artifact_records(output_dir: Path, *, scan_label: str) -> list[dict[str, object]]:
    output_path = Path(output_dir)
    records = []
    for artifact_role, file_name, required in _SOURCE_ARTIFACTS:
        path = output_path / file_name
        _require_inside_output_dir(path, output_path, artifact_role)
        if path.exists():
            if path.is_symlink():
                raise ValueError(
                    f"{scan_label} scan source artifact is a symlink: {artifact_role}"
                )
            if not path.is_file():
                raise ValueError(
                    f"{scan_label} scan source artifact is not a file: {artifact_role}"
                )
            records.append(
                {
                    "artifact_role": artifact_role,
                    "path": path.as_posix(),
                    "relative_path": file_name,
                    "exists": True,
                    "required_for_comparison": required,
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                    "content_indexed": False,
                    "raw_content_copied": False,
                }
            )
            continue
        if required:
            raise ValueError(
                f"{scan_label} scan source artifact is missing: {artifact_role}"
            )
        records.append(
            {
                "artifact_role": artifact_role,
                "path": path.as_posix(),
                "relative_path": file_name,
                "exists": False,
                "required_for_comparison": required,
                "sha256": None,
                "size_bytes": None,
                "content_indexed": False,
                "raw_content_copied": False,
            }
        )
    return sorted(records, key=lambda record: str(record["artifact_role"]))


def _null_source_artifact_records() -> list[dict[str, object]]:
    return [
        {
            "artifact_role": artifact_role,
            "path": None,
            "relative_path": file_name,
            "exists": False,
            "required_for_comparison": required,
            "sha256": None,
            "size_bytes": None,
            "content_indexed": False,
            "raw_content_copied": False,
        }
        for artifact_role, file_name, required in sorted(_SOURCE_ARTIFACTS)
    ]


def _read_required_json(path: Path, artifact_label: str) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "local asset incremental source artifact is malformed: " + artifact_label
        ) from error
    if not isinstance(payload, dict):
        raise ValueError(
            "local asset incremental source artifact is malformed: " + artifact_label
        )
    return payload


def _validate_current_manifest_flags(
    asset_manifest: dict[str, object] | None,
    *,
    project_id: str | None,
    recursive: bool | None,
    include_hidden: bool | None,
) -> None:
    if asset_manifest is None:
        raise ValueError("local asset incremental current asset manifest missing")
    manifest_project_id = asset_manifest.get("project_id")
    if project_id is not None and manifest_project_id != project_id:
        raise ValueError("local asset incremental project_id does not match manifest")
    input_section = _dict_field(asset_manifest, "input", "asset_manifest")
    manifest_recursive = _bool_field(input_section, "recursive", "asset_manifest.input")
    manifest_include_hidden = _bool_field(
        input_section,
        "include_hidden",
        "asset_manifest.input",
    )
    if recursive is not None and bool(recursive) != manifest_recursive:
        raise ValueError("local asset incremental recursive does not match manifest")
    if include_hidden is not None and bool(include_hidden) != manifest_include_hidden:
        raise ValueError("local asset incremental include_hidden does not match manifest")


def _assets_by_path(
    asset_manifest: dict[str, object],
    scan_label: str,
) -> dict[str, dict[str, object]]:
    assets = _list_field(asset_manifest, "assets", scan_label + " asset_manifest")
    by_path = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError(scan_label + " scan asset record is malformed")
        record = _asset_projection(asset, scan_label)
        relative_path = str(record["relative_path"])
        if relative_path in by_path:
            raise ValueError(scan_label + " scan duplicate relative_path in manifest")
        by_path[relative_path] = record
    return {
        relative_path: by_path[relative_path]
        for relative_path in sorted(by_path)
    }


def _asset_projection(asset: dict[str, object], scan_label: str) -> dict[str, object]:
    relative_path = _text_field(asset, "relative_path", scan_label + " asset")
    return {
        "relative_path": relative_path,
        "asset_id": _text_field(asset, "asset_id", scan_label + " asset"),
        "asset_type": _text_field(asset, "asset_type", scan_label + " asset"),
        "extension": _text_field(asset, "extension", scan_label + " asset"),
        "file_name": _text_field(asset, "file_name", scan_label + " asset"),
        "sha256": _text_field(asset, "sha256", scan_label + " asset"),
        "size_bytes": _int_field(asset, "size_bytes", scan_label + " asset"),
    }


def _duplicate_state_by_path(
    assets_by_path: dict[str, dict[str, object]],
    duplicates_report: dict[str, object],
    *,
    scan_label: str,
    suspicious_changes: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    states = {
        relative_path: _default_duplicate_state(asset)
        for relative_path, asset in assets_by_path.items()
    }
    groups = _list_field(
        duplicates_report,
        "duplicate_groups",
        scan_label + " duplicates_report",
    )
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError(scan_label + " scan duplicate group is malformed")
        digest = _text_field(group, "sha256", scan_label + " duplicate group")
        relative_paths = sorted(
            _text_list_field(
                group,
                "relative_paths",
                scan_label + " duplicate group",
            )
        )
        group_state = {
            "is_duplicate": True,
            "duplicate_sha256": digest,
            "duplicate_group_count": len(relative_paths),
            "duplicate_group_paths": relative_paths,
        }
        for relative_path in relative_paths:
            if relative_path not in assets_by_path:
                suspicious_changes.append(
                    {
                        "change_type": "duplicate_report_references_missing_asset",
                        "scan": scan_label,
                        "relative_path": relative_path,
                        "duplicate_sha256": digest,
                    }
                )
                continue
            states[relative_path] = dict(group_state)
    return {
        relative_path: states[relative_path]
        for relative_path in sorted(states)
    }


def _default_duplicate_state(asset: dict[str, object]) -> dict[str, object]:
    relative_path = str(asset["relative_path"])
    return {
        "is_duplicate": False,
        "duplicate_sha256": str(asset["sha256"]),
        "duplicate_group_count": 1,
        "duplicate_group_paths": [relative_path],
    }


def _quarantine_state_by_path(
    quarantine_manifest: dict[str, object],
    *,
    scan_label: str,
) -> dict[str, dict[str, object]]:
    items = _list_field(
        quarantine_manifest,
        "items",
        scan_label + " quarantine_manifest",
    )
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(scan_label + " scan quarantine item is malformed")
        relative_path = _text_field(
            item,
            "relative_path",
            scan_label + " quarantine item",
        )
        reason = _text_field(item, "reason", scan_label + " quarantine item")
        grouped.setdefault(relative_path, []).append(
            {
                "relative_path": relative_path,
                "reason": reason,
                "path_type": str(item.get("path_type", "unknown")),
                "detail": str(item.get("detail", "")),
            }
        )
    states = {}
    for relative_path in sorted(grouped):
        sorted_items = sorted(
            grouped[relative_path],
            key=lambda record: (
                str(record["reason"]),
                str(record["path_type"]),
                str(record["detail"]),
            ),
        )
        states[relative_path] = {
            "is_quarantined": True,
            "reasons": sorted({str(item["reason"]) for item in sorted_items}),
            "items": sorted_items,
        }
    return states


def _scan_contradictions(
    *,
    scan_label: str,
    assets_by_path: dict[str, dict[str, object]],
    duplicate_state_by_path: dict[str, dict[str, object]],
    quarantine_state_by_path: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    suspicious = []
    for relative_path in sorted(set(assets_by_path).intersection(quarantine_state_by_path)):
        suspicious.append(
            {
                "change_type": "asset_also_has_quarantine_record",
                "scan": scan_label,
                "relative_path": relative_path,
                "quarantine_reasons": quarantine_state_by_path[relative_path][
                    "reasons"
                ],
            }
        )
    for relative_path in sorted(quarantine_state_by_path):
        duplicate_state = duplicate_state_by_path.get(relative_path)
        if duplicate_state is not None and duplicate_state["is_duplicate"] is True:
            suspicious.append(
                {
                    "change_type": "quarantined_path_marked_duplicate",
                    "scan": scan_label,
                    "relative_path": relative_path,
                    "duplicate_state": duplicate_state,
                }
            )
    return suspicious


def _classify_assets(
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
    *,
    plan_mode: str,
) -> dict[str, object]:
    current_paths = set(current.assets_by_path)
    previous_paths = set(previous.assets_by_path)
    shared_paths = sorted(current_paths.intersection(previous_paths))

    unchanged_assets = []
    changed_assets = []
    new_assets = []
    missing_assets = []
    duplicate_state_changes = []
    quarantine_state_changes = []
    suspicious_changes = []

    if plan_mode == _BASELINE_MODE:
        new_assets = [
            current.assets_by_path[relative_path]
            for relative_path in sorted(current_paths)
        ]
    else:
        for relative_path in shared_paths:
            current_asset = current.assets_by_path[relative_path]
            previous_asset = previous.assets_by_path[relative_path]
            if _asset_content_identity(current_asset) == _asset_content_identity(
                previous_asset
            ):
                unchanged_assets.append(current_asset)
                continue
            change_reasons = []
            if current_asset["sha256"] != previous_asset["sha256"]:
                change_reasons.append("sha256_changed")
            if current_asset["size_bytes"] != previous_asset["size_bytes"]:
                change_reasons.append("size_bytes_changed")
            changed_record = {
                "relative_path": relative_path,
                "previous": previous_asset,
                "current": current_asset,
                "change_reasons": sorted(change_reasons),
            }
            changed_assets.append(changed_record)
            if (
                current_asset["size_bytes"] == previous_asset["size_bytes"]
                and current_asset["sha256"] != previous_asset["sha256"]
            ):
                suspicious_changes.append(
                    {
                        "change_type": "same_relative_path_same_size_different_sha256",
                        "relative_path": relative_path,
                        "previous_sha256": previous_asset["sha256"],
                        "current_sha256": current_asset["sha256"],
                        "size_bytes": current_asset["size_bytes"],
                    }
                )
        new_assets = [
            current.assets_by_path[relative_path]
            for relative_path in sorted(current_paths - previous_paths)
        ]
        missing_assets = [
            previous.assets_by_path[relative_path]
            for relative_path in sorted(previous_paths - current_paths)
        ]
        duplicate_state_changes = _duplicate_state_changes(current, previous)

    quarantine_state_changes = _quarantine_state_changes(current, previous)
    suspicious_changes.extend(previous.suspicious_changes)
    suspicious_changes.extend(current.suspicious_changes)
    suspicious_changes.extend(
        _quarantine_duplicate_transition_suspicion(
            current=current,
            previous=previous,
            quarantine_state_changes=quarantine_state_changes,
        )
    )

    return {
        "current_asset_count": len(current.assets_by_path),
        "previous_asset_count": len(previous.assets_by_path),
        "unchanged_assets": _sort_records(unchanged_assets),
        "changed_assets": _sort_records(changed_assets),
        "new_assets": _sort_records(new_assets),
        "missing_assets": _sort_records(missing_assets),
        "duplicate_state_changes": _sort_records(duplicate_state_changes),
        "quarantine_state_changes": _sort_records(quarantine_state_changes),
        "suspicious_changes": _sort_records(suspicious_changes),
    }


def _asset_content_identity(asset: dict[str, object]) -> tuple[str, int]:
    return str(asset["sha256"]), int(asset["size_bytes"])


def _duplicate_state_changes(
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
) -> list[dict[str, object]]:
    changes = []
    for relative_path in sorted(
        set(current.assets_by_path).intersection(previous.assets_by_path)
    ):
        current_state = current.duplicate_state_by_path[relative_path]
        previous_state = previous.duplicate_state_by_path[relative_path]
        if current_state == previous_state:
            continue
        changes.append(
            {
                "relative_path": relative_path,
                "previous": previous_state,
                "current": current_state,
                "change_reasons": _duplicate_change_reasons(
                    previous_state,
                    current_state,
                ),
            }
        )
    return changes


def _duplicate_change_reasons(
    previous_state: dict[str, object],
    current_state: dict[str, object],
) -> list[str]:
    reasons = []
    if previous_state["is_duplicate"] != current_state["is_duplicate"]:
        reasons.append("duplicate_membership_changed")
    if previous_state["duplicate_group_paths"] != current_state["duplicate_group_paths"]:
        reasons.append("duplicate_group_paths_changed")
    if previous_state["duplicate_sha256"] != current_state["duplicate_sha256"]:
        reasons.append("duplicate_sha256_changed")
    if previous_state["duplicate_group_count"] != current_state["duplicate_group_count"]:
        reasons.append("duplicate_group_count_changed")
    return sorted(reasons)


def _quarantine_state_changes(
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
) -> list[dict[str, object]]:
    changes = []
    all_paths = sorted(
        set(current.quarantine_state_by_path).union(previous.quarantine_state_by_path)
    )
    for relative_path in all_paths:
        current_state = current.quarantine_state_by_path.get(
            relative_path,
            _default_quarantine_state(),
        )
        previous_state = previous.quarantine_state_by_path.get(
            relative_path,
            _default_quarantine_state(),
        )
        if current_state == previous_state:
            continue
        changes.append(
            {
                "relative_path": relative_path,
                "previous": previous_state,
                "current": current_state,
                "change_reasons": _quarantine_change_reasons(
                    previous_state,
                    current_state,
                ),
            }
        )
    return changes


def _default_quarantine_state() -> dict[str, object]:
    return {
        "is_quarantined": False,
        "reasons": [],
        "items": [],
    }


def _quarantine_change_reasons(
    previous_state: dict[str, object],
    current_state: dict[str, object],
) -> list[str]:
    reasons = []
    if previous_state["is_quarantined"] != current_state["is_quarantined"]:
        if current_state["is_quarantined"]:
            reasons.append("quarantine_item_appeared")
        else:
            reasons.append("quarantine_item_disappeared")
    if previous_state["reasons"] != current_state["reasons"]:
        reasons.append("quarantine_reason_changed")
    return sorted(reasons)


def _quarantine_duplicate_transition_suspicion(
    *,
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
    quarantine_state_changes: list[dict[str, object]],
) -> list[dict[str, object]]:
    suspicious = []
    for change in quarantine_state_changes:
        relative_path = str(change["relative_path"])
        if (
            relative_path in previous.assets_by_path
            and change["current"]["is_quarantined"] is True
        ):
            suspicious.append(
                {
                    "change_type": "previous_asset_now_quarantined",
                    "relative_path": relative_path,
                    "current_quarantine_reasons": change["current"]["reasons"],
                }
            )
        if (
            relative_path in current.assets_by_path
            and change["previous"]["is_quarantined"] is True
        ):
            suspicious.append(
                {
                    "change_type": "previous_quarantine_now_asset",
                    "relative_path": relative_path,
                    "previous_quarantine_reasons": change["previous"]["reasons"],
                }
            )
    return suspicious


def _plan_payload(
    *,
    output_dir: Path,
    previous_scan_output_dir: Path | None,
    plan_mode: str,
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
    classifications: dict[str, object],
) -> dict[str, object]:
    current_manifest = current.asset_manifest or {}
    current_input = _dict_field(current_manifest, "input", "asset_manifest")
    return {
        "plan_type": _PLAN_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "plan_mode": plan_mode,
        "current_output_dir": output_dir.as_posix(),
        "previous_scan_output_dir": None
        if previous_scan_output_dir is None
        else previous_scan_output_dir.as_posix(),
        "project_id": current_manifest.get("project_id"),
        "recursive": _bool_field(current_input, "recursive", "asset_manifest.input"),
        "include_hidden": _bool_field(
            current_input,
            "include_hidden",
            "asset_manifest.input",
        ),
        "current_scan_artifacts": current.source_artifacts,
        "previous_scan_artifacts": previous.source_artifacts,
        "current_asset_count": classifications["current_asset_count"],
        "previous_asset_count": classifications["previous_asset_count"],
        "unchanged_asset_count": len(classifications["unchanged_assets"]),
        "changed_asset_count": len(classifications["changed_assets"]),
        "new_asset_count": len(classifications["new_assets"]),
        "missing_asset_count": len(classifications["missing_assets"]),
        "duplicate_state_changed_count": len(
            classifications["duplicate_state_changes"]
        ),
        "quarantine_state_changed_count": len(
            classifications["quarantine_state_changes"]
        ),
        "suspicious_change_count": len(classifications["suspicious_changes"]),
        "unchanged_assets": classifications["unchanged_assets"],
        "changed_assets": classifications["changed_assets"],
        "new_assets": classifications["new_assets"],
        "missing_assets": classifications["missing_assets"],
        "duplicate_state_changes": classifications["duplicate_state_changes"],
        "quarantine_state_changes": classifications["quarantine_state_changes"],
        "suspicious_changes": classifications["suspicious_changes"],
        "safe_to_use_as_plan": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
    }


def _manifest_payload(
    *,
    plan_path: Path,
    manifest_path: Path,
    summary_path: Path,
    summary_content: str,
    plan_mode: str,
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
    classifications: dict[str, object],
) -> dict[str, object]:
    row_counts = {
        "current_assets": classifications["current_asset_count"],
        "previous_assets": classifications["previous_asset_count"],
        "unchanged_assets": len(classifications["unchanged_assets"]),
        "changed_assets": len(classifications["changed_assets"]),
        "new_assets": len(classifications["new_assets"]),
        "missing_assets": len(classifications["missing_assets"]),
        "duplicate_state_changes": len(classifications["duplicate_state_changes"]),
        "quarantine_state_changes": len(classifications["quarantine_state_changes"]),
        "suspicious_changes": len(classifications["suspicious_changes"]),
    }
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "plan_path": plan_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "plan_sha256": sha256_file(plan_path),
        "summary_sha256": sha256_text(summary_content),
        "current_source_artifacts": current.source_artifacts,
        "previous_source_artifacts": previous.source_artifacts,
        "plan_mode": plan_mode,
        "row_counts": row_counts,
        "counts": dict(row_counts),
        "deterministic_ordering": True,
        **dict(_BOUNDARY_FLAGS),
        "required_human_approval": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
        "manifest_path": manifest_path.as_posix(),
    }


def _summary_markdown(
    *,
    output_dir: Path,
    previous_scan_output_dir: Path | None,
    plan_mode: str,
    current: _ScanSnapshot,
    previous: _ScanSnapshot,
    classifications: dict[str, object],
) -> str:
    sqlite_record = _source_artifact_by_role(
        current.source_artifacts,
        "local_asset_sqlite_index",
    )
    sqlite_path = sqlite_record.get("path") if sqlite_record else None
    sqlite_present = bool(sqlite_record and sqlite_record.get("exists"))
    lines = [
        "# Local Asset Incremental Scan Summary",
        "",
        f"- Plan mode: `{plan_mode}`",
        f"- Current output_dir: `{output_dir.as_posix()}`",
        "- Previous scan output_dir: "
        + (
            "`" + previous_scan_output_dir.as_posix() + "`"
            if previous_scan_output_dir is not None
            else "none"
        ),
        f"- Current asset count: {classifications['current_asset_count']}",
        f"- Previous asset count: {classifications['previous_asset_count']}",
        f"- Unchanged asset count: {len(classifications['unchanged_assets'])}",
        f"- Changed asset count: {len(classifications['changed_assets'])}",
        f"- New asset count: {len(classifications['new_assets'])}",
        f"- Missing asset count: {len(classifications['missing_assets'])}",
        "- Duplicate-state-changed count: "
        + str(len(classifications["duplicate_state_changes"])),
        "- Quarantine-state-changed count: "
        + str(len(classifications["quarantine_state_changes"])),
        f"- Suspicious change count: {len(classifications['suspicious_changes'])}",
        "",
        "This artifact is a metadata-only human review plan. It is not cache "
        "authority, it performed no automatic skip, and it does not approve any "
        "execution.",
        "",
        "No input files were mutated, moved, renamed, or deleted. No raw private "
        "file contents were copied into this plan. No media organizer behavior, "
        "network access, model API call, or external runtime invocation was "
        "performed.",
        "",
        "## Safe Example Review Queries",
        "",
    ]
    if sqlite_present:
        lines.extend(
            [
                f"The current per-scan SQLite index is `{sqlite_path}`.",
                "",
                "```sql",
                "SELECT relative_path, size_bytes, sha256",
                "FROM assets",
                "ORDER BY relative_path;",
                "",
                "SELECT duplicate_group_id, asset_count, total_size_bytes",
                "FROM duplicate_groups",
                "ORDER BY asset_count DESC, duplicate_group_id;",
                "",
                "SELECT relative_path, reason, severity",
                "FROM quarantine_events",
                "ORDER BY relative_path, reason;",
                "```",
            ]
        )
    else:
        lines.append("No current local_asset_index.sqlite file was present.")
    return "\n".join(lines) + "\n"


def _source_artifact_by_role(
    records: list[dict[str, object]],
    role: str,
) -> dict[str, object] | None:
    for record in records:
        if record.get("artifact_role") == role:
            return record
    return None


def _sort_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        records,
        key=lambda record: (
            str(record.get("relative_path", "")),
            str(record.get("change_type", "")),
            json.dumps(record, sort_keys=True),
        ),
    )


def _dict_field(payload: dict[str, object], field_name: str, label: str) -> dict[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(label + " " + field_name + " is malformed")
    return value


def _list_field(payload: dict[str, object], field_name: str, label: str) -> list[object]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(label + " " + field_name + " is malformed")
    return value


def _text_list_field(
    payload: dict[str, object],
    field_name: str,
    label: str,
) -> list[str]:
    value = _list_field(payload, field_name, label)
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(label + " " + field_name + " is malformed")
    return list(value)


def _text_field(payload: dict[str, object], field_name: str, label: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(label + " " + field_name + " is malformed")
    return value


def _int_field(payload: dict[str, object], field_name: str, label: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(label + " " + field_name + " is malformed")
    return value


def _bool_field(payload: dict[str, object], field_name: str, label: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(label + " " + field_name + " is malformed")
    return value


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=True)
        )
    except (OSError, ValueError):
        return False
    return True


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    try:
        with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
            json.dump(payload, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(
            "local asset incremental output already exists: " + Path(path).name
        ) from error


def _write_text_exclusive(path: Path, content: str) -> None:
    try:
        with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(content)
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(
            "local asset incremental output already exists: " + Path(path).name
        ) from error
