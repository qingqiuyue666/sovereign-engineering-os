"""Low-memory streaming indexer for heavy local asset dictionaries."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from kernel.os_engine.artifact_store import CHUNK_SIZE, sha256_file

DEFAULT_SCAN_ROOT = Path("/Users/qqy/Desktop/HFX_RESOURCE_INBOX/")
DEFAULT_INDEX_ROOT = Path.home() / ".sovereign_engineering_os" / "artifacts" / "indexes"
ASSET_EXTENSIONS = frozenset(
    {
        ".abc",
        ".bgeo",
        ".bgeo.sc",
        ".exr",
        ".hip",
        ".hiplc",
        ".hipnc",
        ".usd",
        ".usda",
        ".usdc",
        ".vdb",
    }
)
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "__pycache__",
        "cache",
        "caches",
        "node_modules",
    }
)


class StreamingIndexerError(RuntimeError):
    """Base error for scanner failures."""


class PathEscapeError(StreamingIndexerError):
    """Raised when a discovered path escapes the configured scan root."""


@dataclass(frozen=True, slots=True)
class AssetIndexRecord:
    relative_path: str
    absolute_path: str
    extension: str
    asset_kind: str
    size_bytes: int
    modified_at: str
    sha256: str


@dataclass(frozen=True, slots=True)
class IndexSummary:
    scan_root: Path
    output_path: Path
    indexed_count: int
    skipped_count: int
    total_size_bytes: int
    created_at: datetime


class StreamingAssetIndexer:
    def __init__(
        self,
        *,
        scan_root: Path = DEFAULT_SCAN_ROOT,
        output_root: Path = DEFAULT_INDEX_ROOT,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        self.scan_root = scan_root.expanduser()
        self.output_root = output_root.expanduser()
        self.chunk_size = chunk_size

    def scan(
        self,
        *,
        scan_root: Path | None = None,
        output_path: Path | None = None,
        extensions: frozenset[str] = ASSET_EXTENSIONS,
    ) -> IndexSummary:
        root = (scan_root or self.scan_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise StreamingIndexerError(f"scan root does not exist or is not a directory: {root}")
        output = self._resolve_output_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        indexed_count = 0
        skipped_count = 0
        total_size = 0
        with output.open("w", encoding="utf-8", buffering=1024 * 1024) as handle:
            for path in self._iter_candidate_files(root):
                suffix = _compound_suffix(path).lower()
                if suffix not in extensions:
                    skipped_count += 1
                    continue
                record = self._record_for_path(root, path)
                total_size += record.size_bytes
                indexed_count += 1
                handle.write(json.dumps(asdict(record), sort_keys=True))
                handle.write("\n")

        return IndexSummary(
            scan_root=root,
            output_path=output,
            indexed_count=indexed_count,
            skipped_count=skipped_count,
            total_size_bytes=total_size,
            created_at=datetime.now(UTC),
        )

    def _record_for_path(self, root: Path, path: Path) -> AssetIndexRecord:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise PathEscapeError(f"path escaped scan root: {resolved}") from exc
        stat = resolved.stat()
        extension = _compound_suffix(resolved).lower()
        return AssetIndexRecord(
            relative_path=relative.as_posix(),
            absolute_path=str(resolved),
            extension=extension,
            asset_kind=_asset_kind(extension),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            sha256=sha256_file(resolved, chunk_size=self.chunk_size),
        )

    def _iter_candidate_files(self, root: Path) -> Iterator[Path]:
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            continue
                        entry_path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in EXCLUDED_DIR_NAMES:
                                stack.append(entry_path)
                        elif entry.is_file(follow_symlinks=False):
                            yield entry_path
            except PermissionError:
                continue

    def _resolve_output_path(self, output_path: Path | None) -> Path:
        if output_path is None:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            return (self.output_root / f"asset_index_{stamp}.jsonl").resolve()
        candidate = output_path.expanduser()
        if candidate.suffix != ".jsonl":
            raise StreamingIndexerError("index output must use .jsonl")
        if not candidate.is_absolute():
            candidate = self.output_root / candidate
        return candidate.resolve()


def _compound_suffix(path: Path) -> str:
    name = path.name.lower()
    for compound in (".bgeo.sc",):
        if name.endswith(compound):
            return compound
    return path.suffix.lower()


def _asset_kind(extension: str) -> str:
    return {
        ".abc": "alembic_cache",
        ".bgeo": "houdini_geometry_cache",
        ".bgeo.sc": "houdini_geometry_cache",
        ".exr": "render_frame",
        ".hip": "houdini_scene",
        ".hiplc": "houdini_scene",
        ".hipnc": "houdini_scene",
        ".usd": "usd_scene",
        ".usda": "usd_scene",
        ".usdc": "usd_scene",
        ".vdb": "volume_cache",
    }.get(extension, "asset")
