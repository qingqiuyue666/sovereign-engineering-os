"""Real local asset-library scan and report helpers.

The scanner is intentionally read-only for the asset root. It only records
bounded metadata, hashes, relative references, and operator-facing warnings.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import os
import re

from creative.assets.license_metadata_infer import infer_license
from creative.common import SCHEMA_VERSION, partial_sha256, safe_relative, stable_id

OUTPUT_MODES = {"public", "local"}

SKIP_NAMES = {
    ".DS_Store",
    ".git",
    "__MACOSX",
    "__pycache__",
    "Thumbs.db",
    "node_modules",
}

CATEGORY_EXTENSIONS = {
    ".hip": "houdini",
    ".hiplc": "houdini",
    ".hipnc": "houdini",
    ".hda": "houdini",
    ".otl": "houdini",
    ".uproject": "unreal",
    ".uasset": "unreal",
    ".umap": "unreal",
    ".blend": "blender",
    ".blend1": "blender",
    ".ztl": "zbrush",
    ".ztpr": "zbrush",
    ".zpr": "zbrush",
    ".aep": "after_effects",
    ".aepx": "after_effects",
    ".drp": "davinci",
    ".dra": "davinci",
    ".drt": "davinci",
    ".mtlx": "materials",
    ".mat": "materials",
    ".sbsar": "materials",
    ".vdb": "vdb_cache",
    ".bgeo": "vdb_cache",
    ".bgeo.sc": "vdb_cache",
    ".sc": "vdb_cache",
    ".sim": "vdb_cache",
    ".fbx": "fbx_obj_usd_alembic",
    ".obj": "fbx_obj_usd_alembic",
    ".usd": "fbx_obj_usd_alembic",
    ".usda": "fbx_obj_usd_alembic",
    ".usdc": "fbx_obj_usd_alembic",
    ".usdz": "fbx_obj_usd_alembic",
    ".abc": "fbx_obj_usd_alembic",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".avi": "video",
    ".webm": "video",
    ".wav": "audio",
    ".mp3": "audio",
    ".aiff": "audio",
    ".aif": "audio",
    ".flac": "audio",
    ".cube": "lut",
    ".look": "lut",
    ".ocio": "lut",
    ".py": "scripts",
    ".sh": "scripts",
    ".jsx": "scripts",
    ".js": "scripts",
    ".bat": "scripts",
    ".zip": "archives",
    ".rar": "archives",
    ".7z": "archives",
    ".tar": "archives",
    ".gz": "archives",
    ".tar.gz": "archives",
}

TEXTURE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".tga",
    ".bmp",
    ".psd",
    ".tx",
    ".exr",
}
HDRI_EXTENSIONS = {".hdr", ".hdri"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz"}
MODEL_CATEGORIES = {"fbx_obj_usd_alembic", "blender", "houdini", "unreal", "zbrush"}
TEXTURE_MAP_ALIASES = {
    "base_color": {"albedo", "base", "basecolor", "base_color", "color", "col", "diff", "diffuse"},
    "normal": {"normal", "normalgl", "normaldx", "nrm", "nor"},
    "roughness": {"rough", "roughness", "rgh"},
    "metallic": {"metal", "metallic", "metalness", "mtl"},
    "ao": {"ao", "ambientocclusion", "occlusion"},
    "height": {"bump", "disp", "displacement", "height"},
    "opacity": {"alpha", "mask", "opacity", "transparency"},
    "emissive": {"emit", "emission", "emissive"},
    "specular": {"spec", "specular"},
}
STANDARD_TEXTURE_MAPS = ("base_color", "normal", "roughness")
TOKEN_TO_MAP = {
    token: map_name
    for map_name, aliases in TEXTURE_MAP_ALIASES.items()
    for token in aliases
}

PART_PATTERNS = (
    re.compile(r"^(?P<base>.+)\.part(?P<part>\d+)\.(?P<kind>rar|zip|7z)$", re.IGNORECASE),
    re.compile(r"^(?P<base>.+)\.(?P<part>\d{3})$", re.IGNORECASE),
    re.compile(r"^(?P<base>.+)\.z(?P<part>\d{2})$", re.IGNORECASE),
)


def build_asset_library_scan(
    root: Path,
    *,
    mode: str = "public",
    max_depth: int = 12,
    max_file_read_bytes: int = 1_048_576,
) -> dict[str, object]:
    """Scan a local asset root and return a production-useful report payload."""

    if mode not in OUTPUT_MODES:
        raise ValueError(f"mode must be one of {sorted(OUTPUT_MODES)}")
    root = Path(root).expanduser()
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    assets, empty_dirs = _collect_assets(
        root,
        mode=mode,
        max_depth=max_depth,
        max_file_read_bytes=max_file_read_bytes,
    )
    duplicate_groups = _detect_duplicate_groups(root, assets)
    archive_groups, archive_warnings = _detect_archive_groups(assets)
    texture_sets = _detect_texture_sets(assets)
    production_groups = _detect_production_groups(assets, texture_sets)
    largest_dirs = _largest_directories(assets)
    summary = _build_summary(
        assets,
        empty_dirs,
        duplicate_groups,
        archive_warnings,
        texture_sets,
        production_groups,
        largest_dirs,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "real_local_asset_library_scan_v1",
        "mode": mode,
        "read_only": True,
        "destructive_actions_performed": False,
        "asset_root": _display_root(root, mode),
        "asset_root_name": root.name,
        "max_depth": max_depth,
        "summary": summary,
        "assets": assets,
        "empty_directories": empty_dirs,
        "largest_directories": largest_dirs,
        "duplicate_groups": duplicate_groups,
        "archive_groups": archive_groups,
        "archive_warnings": archive_warnings,
        "texture_sets": texture_sets,
        "production_groups": production_groups,
        "next_actions": _build_next_actions(summary),
        "safety": {
            "input_mutation": False,
            "duplicate_deletion": False,
            "archive_extraction": False,
            "dcc_execution": False,
            "public_mode_uses_relative_paths": mode == "public",
        },
    }


def write_asset_library_outputs(
    scan: dict[str, object],
    *,
    root: Path,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    """Write optional JSON and Markdown outputs outside the scanned root."""

    outputs: dict[str, object] = {}
    if output_json is not None:
        _ensure_output_outside_root(Path(root), Path(output_json))
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(scan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        outputs["json"] = output_json.as_posix()
    if output_markdown is not None:
        _ensure_output_outside_root(Path(root), Path(output_markdown))
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_asset_library_markdown(scan), encoding="utf-8")
        outputs["markdown"] = output_markdown.as_posix()
    return outputs


def render_asset_library_markdown(scan: dict[str, object]) -> str:
    """Render the scan payload as a readable operator report."""

    summary = dict(scan.get("summary", {}))
    lines = [
        "# SEOS Real Local Asset Library Report",
        "",
        f"- Mode: `{scan.get('mode')}`",
        f"- Asset root: `{scan.get('asset_root')}`",
        f"- Read-only scan: `{scan.get('read_only')}`",
        f"- Destructive actions performed: `{scan.get('destructive_actions_performed')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "total_assets",
        "total_size_bytes",
        "empty_directory_count",
        "duplicate_group_count",
        "duplicate_asset_count",
        "archive_warning_count",
        "texture_set_count",
        "incomplete_texture_set_count",
        "production_group_count",
        "likely_incomplete_pack_count",
    ):
        lines.append(f"| {key} | {summary.get(key, 0)} |")

    lines.extend(["", "## Categories", "", "| Category | Count |", "| --- | ---: |"])
    for category, count in sorted(dict(summary.get("category_counts", {})).items()):
        lines.append(f"| `{category}` | {count} |")

    lines.extend(["", "## Largest Folders", "", "| Folder | Size | Files |", "| --- | ---: | ---: |"])
    for item in scan.get("largest_directories", [])[:10]:
        row = dict(item)
        lines.append(f"| `{row.get('relative_path')}` | {row.get('size_bytes')} | {row.get('file_count')} |")

    lines.extend(["", "## Duplicate Groups", ""])
    duplicates = list(scan.get("duplicate_groups", []))
    if duplicates:
        for group in duplicates[:20]:
            row = dict(group)
            lines.append(f"- `{row.get('id')}`: {row.get('asset_count')} files, {row.get('size_bytes')} bytes, manual review only")
            for path in row.get("relative_paths", [])[:6]:
                lines.append(f"  - `{path}`")
    else:
        lines.append("- No exact duplicate groups detected.")

    lines.extend(["", "## Archive Warnings", ""])
    warnings = list(scan.get("archive_warnings", []))
    if warnings:
        for warning in warnings:
            row = dict(warning)
            lines.append(f"- `{row.get('base_name')}` missing parts: `{row.get('missing_part_numbers')}`")
    else:
        lines.append("- No missing multipart archive parts detected.")

    lines.extend(["", "## Empty Directories", ""])
    empty_dirs = list(scan.get("empty_directories", []))
    if empty_dirs:
        for item in empty_dirs[:30]:
            lines.append(f"- `{dict(item).get('relative_path')}`")
    else:
        lines.append("- No empty directories detected.")

    lines.extend(["", "## Texture Sets", ""])
    texture_sets = list(scan.get("texture_sets", []))
    if texture_sets:
        for item in texture_sets[:30]:
            row = dict(item)
            missing = row.get("missing_standard_maps", [])
            status = row.get("status")
            lines.append(f"- `{row.get('base_name')}`: `{status}`, maps `{row.get('map_types')}`, missing `{missing}`")
    else:
        lines.append("- No likely texture sets detected.")

    lines.extend(["", "## Production Groups", ""])
    groups = list(scan.get("production_groups", []))
    if groups:
        for item in groups[:30]:
            row = dict(item)
            lines.append(f"- `{row.get('id')}` in `{row.get('directory')}`: `{row.get('status')}`, categories `{row.get('categories')}`")
    else:
        lines.append("- No likely model/material/texture production groups detected.")

    lines.extend(["", "## Next Actions", ""])
    for action in scan.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend([
        "",
        "## Safety Boundary",
        "",
        "- This report does not delete duplicates.",
        "- This report does not extract archives.",
        "- This report does not execute DCC or AI tools.",
        "- Public mode uses relative asset references and does not embed absolute local paths.",
        "",
    ])
    return "\n".join(lines)


def infer_production_category(path: Path) -> str:
    suffix = _compound_suffix(path)
    lower_name = path.name.lower()
    lower_path = path.as_posix().lower()
    if suffix in HDRI_EXTENSIONS or "hdri" in lower_name:
        return "hdri"
    if suffix in TEXTURE_EXTENSIONS:
        return "textures"
    if suffix == ".json" and ("comfy" in lower_path or "workflow" in lower_name):
        return "comfyui"
    return CATEGORY_EXTENSIONS.get(suffix, "unknown")


def _collect_assets(
    root: Path,
    *,
    mode: str,
    max_depth: int,
    max_file_read_bytes: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    assets: list[dict[str, object]] = []
    empty_dirs: list[dict[str, object]] = []
    root_resolved = root.resolve()
    for current, dirs, files in os.walk(root_resolved):
        current_path = Path(current)
        relative_current = safe_relative(current_path, root_resolved)
        current_depth = 0 if relative_current == "." else len(Path(relative_current).parts)
        if current_depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = sorted(name for name in dirs if not _skip_entry(name))
        visible_files = sorted(name for name in files if not _skip_entry(name))
        if current_path != root_resolved and not dirs and not visible_files:
            empty_dirs.append(
                {
                    "id": stable_id("DIR", relative_current),
                    "relative_path": relative_current,
                    "status": "EMPTY_DIRECTORY",
                    "recommended_action": "Review whether this folder is a useful placeholder or stale clutter.",
                }
            )
        for name in visible_files:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                continue
            relative_path = safe_relative(path, root_resolved)
            file_depth = len(Path(relative_path).parts) - 1
            if file_depth > max_depth:
                continue
            stat = path.stat()
            partial_digest = partial_sha256(path, max_read_bytes=max_file_read_bytes)
            category = infer_production_category(path)
            parent = safe_relative(path.parent, root_resolved)
            record: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("AST", relative_path, stat.st_size, partial_digest),
                "relative_path": relative_path,
                "directory": "." if parent == "." else parent,
                "filename": path.name,
                "extension": _compound_suffix(path),
                "size_bytes": stat.st_size,
                "partial_sha256": partial_digest,
                "category": category,
                "likely_tool": _likely_tool(category, path),
                "license_status": "unknown_private_by_default",
                "public_asset": _is_public_fixture_path(root_resolved, path),
                "read_only": True,
            }
            if mode == "local":
                record["absolute_path"] = path.as_posix()
            record["license"] = infer_license(record)
            assets.append(record)
    assets.sort(key=lambda item: str(item.get("relative_path", "")))
    empty_dirs.sort(key=lambda item: str(item.get("relative_path", "")))
    return assets, empty_dirs


def _detect_duplicate_groups(root: Path, assets: list[dict[str, object]]) -> list[dict[str, object]]:
    by_size: dict[int, list[dict[str, object]]] = defaultdict(list)
    for asset in assets:
        by_size[int(asset.get("size_bytes", 0))].append(asset)
    groups: list[dict[str, object]] = []
    for size, records in sorted(by_size.items()):
        if len(records) < 2:
            continue
        by_hash: dict[str, list[dict[str, object]]] = defaultdict(list)
        for record in records:
            path = root / str(record.get("relative_path"))
            digest = _full_sha256(path)
            record["content_sha256"] = digest
            by_hash[digest].append(record)
        for digest, matches in sorted(by_hash.items()):
            if len(matches) < 2:
                continue
            relative_paths = sorted(str(item.get("relative_path")) for item in matches)
            groups.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "id": stable_id("DUP", digest, *relative_paths),
                    "content_sha256": digest,
                    "size_bytes": size,
                    "asset_count": len(matches),
                    "asset_ids": [str(item.get("id")) for item in matches],
                    "relative_paths": relative_paths,
                    "confidence": "exact_size_and_sha256_match",
                    "deletion_performed": False,
                    "action": "human_review_only",
                }
            )
    return groups


def _detect_archive_groups(assets: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for asset in assets:
        name = str(asset.get("filename", ""))
        base = ""
        part_number = 0
        for pattern in PART_PATTERNS:
            match = pattern.match(name)
            if not match:
                continue
            base = match.group("base")
            part_number = int(match.group("part"))
            break
        if not base and str(asset.get("extension")) in ARCHIVE_EXTENSIONS:
            base = Path(name).stem
            part_number = 1
        if base:
            grouped[base].append({**asset, "part_number": part_number})

    groups: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for base, parts in sorted(grouped.items()):
        numbers = sorted(int(part.get("part_number", 0)) for part in parts if int(part.get("part_number", 0)) > 0)
        missing = []
        if numbers and max(numbers) > 1:
            missing = sorted(set(range(min(numbers), max(numbers) + 1)).difference(numbers))
        group = {
            "schema_version": SCHEMA_VERSION,
            "id": stable_id("ARC", base, *numbers),
            "base_name": base,
            "part_numbers": numbers,
            "part_count": len(parts),
            "asset_ids": [str(item.get("id")) for item in parts],
            "relative_paths": sorted(str(item.get("relative_path")) for item in parts),
            "status": "ARCHIVE_PART_MISSING" if missing else "GROUPED",
            "read_only": True,
        }
        groups.append(group)
        if missing:
            warnings.append(
                {
                    "archive_group_id": group["id"],
                    "base_name": base,
                    "missing_part_numbers": missing,
                    "status": "ARCHIVE_PART_MISSING",
                    "recommended_action": "Find the missing archive part before extraction or production use.",
                }
            )
    return groups, warnings


def _detect_texture_sets(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for asset in assets:
        if asset.get("category") != "textures":
            continue
        directory = str(asset.get("directory", "."))
        base, map_type = _texture_base_and_map(str(asset.get("filename", "")))
        if map_type or len(base) > 2:
            buckets[(directory, base)].append({**asset, "map_type": map_type or "unknown"})
    sets: list[dict[str, object]] = []
    for (directory, base), records in sorted(buckets.items()):
        if len(records) < 2 and all(item.get("map_type") == "unknown" for item in records):
            continue
        map_types = sorted({str(item.get("map_type")) for item in records})
        missing = [item for item in STANDARD_TEXTURE_MAPS if item not in map_types]
        status = "LIKELY_TEXTURE_SET_COMPLETE" if not missing else "LIKELY_TEXTURE_SET_INCOMPLETE"
        sets.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("TEX", directory, base),
                "base_name": base,
                "directory": directory,
                "map_types": map_types,
                "missing_standard_maps": missing,
                "asset_ids": [str(item.get("id")) for item in records],
                "relative_paths": sorted(str(item.get("relative_path")) for item in records),
                "status": status,
                "recommended_action": "Bind to material/lookdev stage after human review." if not missing else "Find or generate missing standard maps before final lookdev.",
            }
        )
    return sets


def _detect_production_groups(
    assets: list[dict[str, object]],
    texture_sets: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_directory: dict[str, list[dict[str, object]]] = defaultdict(list)
    for asset in assets:
        by_directory[str(asset.get("directory", "."))].append(asset)
    texture_dirs = {
        str(item.get("directory")): item
        for item in texture_sets
    }
    groups: list[dict[str, object]] = []
    for directory, records in sorted(by_directory.items()):
        categories = sorted({str(item.get("category")) for item in records})
        has_model = bool(MODEL_CATEGORIES.intersection(categories))
        has_material = "materials" in categories
        has_texture = "textures" in categories or directory in texture_dirs
        if not (has_model or has_material or has_texture):
            continue
        if len(records) < 2 and not has_texture:
            continue
        missing: list[str] = []
        if has_model and not has_texture:
            missing.append("textures")
        if has_model and not has_material:
            missing.append("material")
        texture_set = texture_dirs.get(directory)
        if texture_set and texture_set.get("status") == "LIKELY_TEXTURE_SET_INCOMPLETE":
            missing.append("complete_texture_set")
        status = "LIKELY_INCOMPLETE_PACK" if missing else "LIKELY_MODEL_MATERIAL_TEXTURE_GROUP"
        groups.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("PKG", directory, *categories),
                "directory": directory,
                "categories": categories,
                "asset_count": len(records),
                "asset_ids": [str(item.get("id")) for item in records],
                "missing_components": missing,
                "status": status,
                "recommended_action": "Review missing components before shot binding." if missing else "Candidate pack for shot planning.",
            }
        )
    return groups


def _largest_directories(assets: list[dict[str, object]], *, limit: int = 10) -> list[dict[str, object]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"size_bytes": 0, "file_count": 0})
    for asset in assets:
        directory = str(asset.get("directory", "."))
        totals[directory]["size_bytes"] += int(asset.get("size_bytes", 0))
        totals[directory]["file_count"] += 1
    rows = [
        {"relative_path": directory, **values}
        for directory, values in totals.items()
    ]
    return sorted(rows, key=lambda item: (-int(item["size_bytes"]), str(item["relative_path"])))[:limit]


def _build_summary(
    assets: list[dict[str, object]],
    empty_dirs: list[dict[str, object]],
    duplicate_groups: list[dict[str, object]],
    archive_warnings: list[dict[str, object]],
    texture_sets: list[dict[str, object]],
    production_groups: list[dict[str, object]],
    largest_dirs: list[dict[str, object]],
) -> dict[str, object]:
    categories = Counter(str(asset.get("category", "unknown")) for asset in assets)
    duplicate_asset_count = sum(int(group.get("asset_count", 0)) for group in duplicate_groups)
    incomplete_texture_sets = [
        item for item in texture_sets
        if item.get("status") == "LIKELY_TEXTURE_SET_INCOMPLETE"
    ]
    incomplete_packs = [
        item for item in production_groups
        if item.get("status") == "LIKELY_INCOMPLETE_PACK"
    ]
    return {
        "total_assets": len(assets),
        "total_size_bytes": sum(int(asset.get("size_bytes", 0)) for asset in assets),
        "category_counts": dict(sorted(categories.items())),
        "empty_directory_count": len(empty_dirs),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_asset_count": duplicate_asset_count,
        "archive_warning_count": len(archive_warnings),
        "texture_set_count": len(texture_sets),
        "incomplete_texture_set_count": len(incomplete_texture_sets),
        "production_group_count": len(production_groups),
        "likely_incomplete_pack_count": len(incomplete_packs),
        "largest_directory_count": len(largest_dirs),
    }


def _build_next_actions(summary: dict[str, object]) -> list[str]:
    actions: list[str] = []
    if int(summary.get("duplicate_group_count", 0)):
        actions.append("Inspect duplicate groups manually before any cleanup; no deletion was performed.")
    if int(summary.get("archive_warning_count", 0)):
        actions.append("Restore missing multipart archive files before extracting or using those packs.")
    if int(summary.get("incomplete_texture_set_count", 0)):
        actions.append("Fill missing base color, normal, or roughness maps before final material/lookdev use.")
    if int(summary.get("likely_incomplete_pack_count", 0)):
        actions.append("Review incomplete model/material/texture packs before binding them to a shot plan.")
    if int(summary.get("empty_directory_count", 0)):
        actions.append("Review empty directories and decide whether they are intentional placeholders.")
    actions.append("Verify licenses for real assets before publication, sharing, or commercial production.")
    return actions


def _texture_base_and_map(filename: str) -> tuple[str, str]:
    stem = Path(filename).stem.lower()
    stem = re.sub(r"(^|[_.-])1\d{3}$", "", stem)
    tokens = [token for token in re.split(r"[^a-z0-9]+", stem) if token]
    map_type = ""
    matched_token = ""
    for token in reversed(tokens):
        normalized = token.replace("colour", "color")
        if normalized in TOKEN_TO_MAP:
            map_type = TOKEN_TO_MAP[normalized]
            matched_token = token
            break
    base_tokens = [token for token in tokens if token != matched_token]
    base = "_".join(base_tokens).strip("_") or stem
    return base, map_type


def _full_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _compound_suffix(path: Path) -> str:
    suffixes = [item.lower() for item in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".bgeo", ".sc"]:
        return ".bgeo.sc"
    if len(suffixes) >= 2 and suffixes[-2:] == [".tar", ".gz"]:
        return ".tar.gz"
    return path.suffix.lower()


def _skip_entry(name: str) -> bool:
    return name in SKIP_NAMES or name.startswith(".")


def _is_public_fixture_path(root: Path, path: Path) -> bool:
    combined = f"{root.as_posix()}/{path.as_posix()}"
    return "tests/fixtures/creative" in combined or "examples/public_demo_assets" in combined


def _likely_tool(category: str, path: Path) -> str:
    if category in {"houdini", "unreal", "blender", "zbrush", "after_effects", "davinci", "comfyui"}:
        return category
    lower = path.as_posix().lower()
    for tool in ("houdini", "unreal", "blender", "zbrush", "after_effects", "davinci", "comfyui"):
        if tool in lower:
            return tool
    return "generic_asset_library"


def _display_root(root: Path, mode: str) -> str:
    return root.resolve().as_posix() if mode == "local" else "<asset-root>"


def _ensure_output_outside_root(root: Path, output: Path) -> None:
    root_resolved = root.resolve()
    output_resolved = output.expanduser().resolve()
    try:
        output_resolved.relative_to(root_resolved)
    except ValueError:
        return
    raise ValueError("output path must be outside the scanned asset root")
