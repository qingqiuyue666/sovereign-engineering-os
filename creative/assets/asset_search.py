"""Search helpers for SEOS real local asset-library reports."""

from __future__ import annotations

from pathlib import Path
import json

from creative.assets.local_asset_library import build_asset_library_scan

PRESET_QUERIES = {
    "houdini-fx-assets",
    "vdb-cache-assets",
    "missing-texture-sets",
    "duplicate-video-audio",
    "incomplete-archives",
    "empty-directories",
    "incomplete-packs",
}


def load_asset_library_report(path: Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_or_load_report(
    *,
    registry_json: Path | None = None,
    root: Path | None = None,
    mode: str = "public",
    max_depth: int = 12,
) -> dict[str, object]:
    if registry_json is not None:
        return load_asset_library_report(registry_json)
    if root is not None:
        return build_asset_library_scan(root, mode=mode, max_depth=max_depth)
    default_report = Path("reports/creative/assets/asset_library_report_v1.json")
    if default_report.exists():
        return load_asset_library_report(default_report)
    return build_asset_library_scan(Path("tests/fixtures/creative/assets"), mode=mode, max_depth=max_depth)


def search_asset_library(
    report: dict[str, object],
    *,
    query: str = "",
    category: str = "",
    extension: str = "",
    likely_tool: str = "",
    min_size: int | None = None,
    max_size: int | None = None,
    duplicate_only: bool = False,
    texture_status: str = "",
    archive_status: str = "",
    empty_directories: bool = False,
    mode: str = "public",
    limit: int = 50,
) -> dict[str, object]:
    normalized_query = _normalize_query(query)
    if normalized_query and normalized_query not in PRESET_QUERIES:
        raise ValueError(f"unknown asset search query: {query}")

    assets = [dict(item) for item in report.get("assets", [])]
    duplicate_groups = [dict(item) for item in report.get("duplicate_groups", [])]
    duplicate_asset_ids = {
        str(asset_id)
        for group in duplicate_groups
        for asset_id in group.get("asset_ids", [])
    }
    assets_by_id = {str(item.get("id")): item for item in assets}

    result_type = "assets"
    items: list[dict[str, object]]

    if normalized_query == "missing-texture-sets" or texture_status:
        result_type = "texture_sets"
        desired = texture_status.upper() if texture_status else "INCOMPLETE"
        items = [
            dict(item)
            for item in report.get("texture_sets", [])
            if desired in str(item.get("status", "")).upper()
        ]
    elif normalized_query == "incomplete-archives" or archive_status:
        result_type = "archive_warnings"
        desired = archive_status.upper() if archive_status else "ARCHIVE_PART_MISSING"
        warnings = [dict(item) for item in report.get("archive_warnings", [])]
        groups = [dict(item) for item in report.get("archive_groups", [])]
        items = [
            item for item in [*warnings, *groups]
            if desired in str(item.get("status", "")).upper()
        ]
    elif normalized_query == "empty-directories" or empty_directories:
        result_type = "empty_directories"
        items = [dict(item) for item in report.get("empty_directories", [])]
    elif normalized_query == "duplicate-video-audio":
        result_type = "duplicate_groups"
        items = [
            group
            for group in duplicate_groups
            if _group_has_category(group, assets_by_id, {"video", "audio"})
        ]
    elif normalized_query == "incomplete-packs":
        result_type = "production_groups"
        items = [
            dict(item)
            for item in report.get("production_groups", [])
            if "INCOMPLETE" in str(item.get("status", "")).upper()
        ]
    else:
        items = assets
        if normalized_query == "houdini-fx-assets":
            items = [
                item for item in items
                if item.get("category") == "houdini" or item.get("likely_tool") == "houdini"
            ]
        if normalized_query == "vdb-cache-assets":
            items = [item for item in items if item.get("category") == "vdb_cache"]
        if category:
            items = [item for item in items if str(item.get("category")) == category]
        if extension:
            wanted_extension = extension if extension.startswith(".") else "." + extension
            items = [item for item in items if str(item.get("extension")) == wanted_extension.lower()]
        if likely_tool:
            items = [item for item in items if str(item.get("likely_tool")) == likely_tool]
        if min_size is not None:
            items = [item for item in items if int(item.get("size_bytes", 0)) >= min_size]
        if max_size is not None:
            items = [item for item in items if int(item.get("size_bytes", 0)) <= max_size]
        if duplicate_only:
            items = [item for item in items if str(item.get("id")) in duplicate_asset_ids]

    sanitized_items = [_sanitize_item(item, mode=mode) for item in items[:limit]]
    payload = {
        "ok": True,
        "read_only": True,
        "query": normalized_query or "filtered-assets",
        "result_type": result_type,
        "result_count": len(items),
        "returned_count": len(sanitized_items),
        "limit": limit,
        "items": sanitized_items,
        "next_actions": _next_actions(result_type, len(items)),
    }
    if result_type == "assets" and duplicate_only:
        payload["duplicate_group_count"] = len(duplicate_groups)
    return payload


def _group_has_category(
    group: dict[str, object],
    assets_by_id: dict[str, dict[str, object]],
    categories: set[str],
) -> bool:
    for asset_id in group.get("asset_ids", []):
        asset = assets_by_id.get(str(asset_id), {})
        if str(asset.get("category")) in categories:
            return True
    return False


def _sanitize_item(item: dict[str, object], *, mode: str) -> dict[str, object]:
    if mode == "local":
        return dict(item)
    sanitized = dict(item)
    sanitized.pop("absolute_path", None)
    return sanitized


def _normalize_query(query: str) -> str:
    return query.strip().lower().replace("_", "-")


def _next_actions(result_type: str, count: int) -> list[str]:
    if count == 0:
        return ["No results matched; broaden the query or rescan the asset root."]
    if result_type == "texture_sets":
        return ["Review missing texture maps before material/lookdev binding."]
    if result_type == "archive_warnings":
        return ["Restore missing archive parts before extraction or production use."]
    if result_type == "duplicate_groups":
        return ["Inspect duplicate groups manually before any cleanup; no deletion was performed."]
    if result_type == "empty_directories":
        return ["Decide whether empty directories are intentional placeholders or stale clutter."]
    if result_type == "production_groups":
        return ["Review incomplete packs before binding assets to shot plans."]
    return ["Review matched assets, verify licenses, and bind only approved assets to production plans."]
