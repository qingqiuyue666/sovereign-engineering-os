"""Read-only local asset scanner with bounded metadata collection."""

from __future__ import annotations

from pathlib import Path
from creative.common import SCHEMA_VERSION, partial_sha256, safe_relative, stable_id

SKIP_NAMES = {".DS_Store", "__MACOSX", "Thumbs.db", "__pycache__"}
CATEGORY_HINTS = {
    ".vdb": "volume_cache",
    ".exr": "image_sequence_or_render",
    ".hdr": "hdri",
    ".blend": "blender_scene",
    ".hip": "houdini_scene",
    ".ztl": "zbrush_tool",
    ".fbx": "model",
    ".obj": "model",
    ".usd": "scene_exchange",
    ".usdz": "scene_exchange",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".rar": "archive",
    ".zip": "archive",
    ".7z": "archive",
}

def iter_asset_files(root: Path, *, max_depth: int = 4):
    root = Path(root)
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        if not path.is_file():
            continue
        try:
            depth = len(path.relative_to(root).parts) - 1
        except ValueError:
            depth = 999
        if depth > max_depth:
            continue
        yield path

def infer_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in CATEGORY_HINTS:
        return CATEGORY_HINTS[suffix]
    name = path.name.lower()
    if ".part" in name or name.endswith((".001", ".002", ".003")):
        return "multipart_archive"
    return "uncategorized"

def scan_assets(root: Path, *, max_depth: int = 4, max_file_read_bytes: int = 1_048_576) -> list[dict[str, object]]:
    root = Path(root)
    records: list[dict[str, object]] = []
    for path in iter_asset_files(root, max_depth=max_depth) or []:
        stat = path.stat()
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("AST", safe_relative(path, root), stat.st_size),
                "relative_path": safe_relative(path, root),
                "filename": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "partial_sha256": partial_sha256(path, max_read_bytes=max_file_read_bytes),
                "category": infer_category(path),
                "license_status": "unknown_private_by_default",
                "public_asset": "examples/public_demo_assets" in path.as_posix(),
                "read_only": True,
            }
        )
    return records
