"""Minimal local asset inventory v1.

Scans only explicitly supplied local roots, rejects dangerous roots and symlink
escapes, and produces deterministic file inventory records with streaming
SHA-256 hashes. This module does not mutate files, create thumbnails, compute
embeddings, launch DCC applications, or use non-standard-library packages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import hashlib
import json
import os

__all__ = [
    "AssetInventoryRecord",
    "MEDIA_CLASS_BY_EXTENSION",
    "classify_media",
    "scan_asset_inventory",
    "streaming_sha256",
]

CHUNK_SIZE = 1024 * 1024

MEDIA_CLASS_BY_EXTENSION = {
    ".py": "CODE",
    ".js": "CODE",
    ".ts": "CODE",
    ".tsx": "CODE",
    ".jsx": "CODE",
    ".css": "CODE",
    ".html": "CODE",
    ".sh": "CODE",
    ".md": "TEXT",
    ".txt": "TEXT",
    ".json": "TEXT",
    ".yaml": "TEXT",
    ".yml": "TEXT",
    ".csv": "TEXT",
    ".tsv": "TEXT",
    ".png": "IMAGE",
    ".jpg": "IMAGE",
    ".jpeg": "IMAGE",
    ".webp": "IMAGE",
    ".gif": "IMAGE",
    ".tif": "IMAGE",
    ".tiff": "IMAGE",
    ".mp4": "VIDEO",
    ".mov": "VIDEO",
    ".mkv": "VIDEO",
    ".avi": "VIDEO",
    ".wav": "AUDIO",
    ".mp3": "AUDIO",
    ".flac": "AUDIO",
    ".aiff": "AUDIO",
    ".abc": "VFX_CACHE",
    ".vdb": "VFX_CACHE",
    ".bgeo": "VFX_CACHE",
    ".bgeo.sc": "VFX_CACHE",
    ".usd": "VFX_CACHE",
    ".usda": "VFX_CACHE",
    ".usdc": "VFX_CACHE",
    ".blend": "DCC_SCENE",
    ".hip": "DCC_SCENE",
    ".hipnc": "DCC_SCENE",
    ".ma": "DCC_SCENE",
    ".mb": "DCC_SCENE",
    ".c4d": "DCC_SCENE",
    ".ztl": "DCC_SCENE",
    ".zip": "ARCHIVE",
    ".tar": "ARCHIVE",
    ".gz": "ARCHIVE",
    ".tgz": "ARCHIVE",
    ".7z": "ARCHIVE",
    ".rar": "ARCHIVE",
}


@dataclass(frozen=True)
class AssetInventoryRecord:
    asset_id: str
    root_id: str
    relative_path: str
    size_bytes: int
    sha256: str
    extension: str
    media_class: str
    observed_at: str
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def scan_asset_inventory(roots: Mapping[str, str | Path]) -> tuple[AssetInventoryRecord, ...]:
    """Scan explicitly supplied roots and return deterministic records."""

    if not isinstance(roots, Mapping) or not roots:
        raise ValueError("asset_roots_mapping_required")
    records: list[AssetInventoryRecord] = []
    for root_id in sorted(roots):
        if not isinstance(root_id, str) or not root_id.strip():
            raise ValueError("root_id_must_be_nonempty_string")
        root = _validate_root(Path(roots[root_id]))
        for file_path in _iter_files(root):
            records.append(_record_for_file(root_id=root_id, root=root, file_path=file_path))
    records.sort(key=lambda record: (record.root_id, record.relative_path))
    return tuple(records)


def streaming_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def classify_media(path: str | Path) -> str:
    name = Path(path).name.lower()
    if name.endswith(".bgeo.sc"):
        return "VFX_CACHE"
    extension = Path(name).suffix
    return MEDIA_CLASS_BY_EXTENSION.get(extension, "UNKNOWN")


def _validate_root(root: Path) -> Path:
    if _contains_traversal(root):
        raise ValueError("asset_root_path_traversal_forbidden")
    resolved = root.expanduser().resolve()
    home = Path.home().resolve()
    if resolved == home:
        raise ValueError("asset_root_home_forbidden")
    if resolved.parent == resolved:
        raise ValueError("asset_root_filesystem_root_forbidden")
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError("asset_root_directory_required")
    if resolved.is_symlink():
        raise ValueError("asset_root_symlink_forbidden")
    return resolved


def _iter_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current_dir = Path(dirpath)
        _reject_escape(root, current_dir)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_dir / dirname
            if candidate.is_symlink():
                _reject_escape(root, candidate.resolve())
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames
        for filename in sorted(filenames):
            candidate = current_dir / filename
            if candidate.is_symlink():
                _reject_escape(root, candidate.resolve())
            _reject_escape(root, candidate.resolve())
            if candidate.is_file():
                files.append(candidate)
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    return tuple(files)


def _record_for_file(
    *,
    root_id: str,
    root: Path,
    file_path: Path,
) -> AssetInventoryRecord:
    relative_path = file_path.relative_to(root).as_posix()
    stat = file_path.stat()
    digest = streaming_sha256(file_path)
    extension = ".bgeo.sc" if file_path.name.lower().endswith(".bgeo.sc") else file_path.suffix.lower()
    media_class = classify_media(file_path)
    asset_id = _hash(
        {
            "root_id": root_id,
            "relative_path": relative_path,
            "sha256": digest,
            "size_bytes": stat.st_size,
        }
    )
    observed_at = _now()
    content_hash = _hash(
        {
            "asset_id": asset_id,
            "root_id": root_id,
            "relative_path": relative_path,
            "size_bytes": stat.st_size,
            "sha256": digest,
            "extension": extension,
            "media_class": media_class,
        }
    )
    return AssetInventoryRecord(
        asset_id=asset_id,
        root_id=root_id,
        relative_path=relative_path,
        size_bytes=stat.st_size,
        sha256=digest,
        extension=extension,
        media_class=media_class,
        observed_at=observed_at,
        content_hash=content_hash,
    )


def _reject_escape(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("asset_symlink_escape_forbidden") from error


def _contains_traversal(path: Path) -> bool:
    return any(part == ".." for part in path.parts)


def _hash(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
