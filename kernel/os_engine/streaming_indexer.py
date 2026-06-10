"""Low-memory streaming indexer for heavy local asset dictionaries."""

from __future__ import annotations

import json
import os
import time
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
        ".aep",
        ".bgeo",
        ".bgeo.sc",
        ".blend",
        ".ckpt",
        ".cube",
        ".exr",
        ".fbx",
        ".hdr",
        ".hda",
        ".hip",
        ".hiplc",
        ".hipnc",
        ".jpg",
        ".jpeg",
        ".lut",
        ".mov",
        ".mp4",
        ".obj",
        ".ocio",
        ".otl",
        ".png",
        ".safetensors",
        ".tif",
        ".tiff",
        ".usd",
        ".usda",
        ".usdc",
        ".vdb",
        ".ztl",
        ".zpr",
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
    duplicate_of: str | None
    license_state: str
    quarantine_status: str
    quarantine_reason: str | None


@dataclass(frozen=True, slots=True)
class IndexSummary:
    scan_root: Path
    output_path: Path
    skipped_report_path: Path
    quarantine_report_path: Path
    indexed_count: int
    skipped_count: int
    duplicate_count: int
    quarantine_count: int
    total_size_bytes: int
    max_files: int | None
    max_runtime_seconds: float | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ScanBudget:
    max_files: int | None = None
    max_runtime_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.max_files is not None and self.max_files <= 0:
            raise StreamingIndexerError("max_files must be positive when provided")
        if self.max_runtime_seconds is not None and self.max_runtime_seconds <= 0:
            raise StreamingIndexerError("max_runtime_seconds must be positive when provided")


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
        max_files: int | None = None,
        max_runtime_seconds: float | None = None,
    ) -> IndexSummary:
        budget = ScanBudget(max_files=max_files, max_runtime_seconds=max_runtime_seconds)
        root = (scan_root or self.scan_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise StreamingIndexerError(f"scan root does not exist or is not a directory: {root}")
        output = self._resolve_output_path(output_path)
        skipped_report = output.with_suffix(".skipped.jsonl")
        quarantine_report = output.with_suffix(".quarantine.jsonl")
        output.parent.mkdir(parents=True, exist_ok=True)

        indexed_count = 0
        skipped_count = 0
        duplicate_count = 0
        quarantine_count = 0
        total_size = 0
        started = time.monotonic()
        seen_checksums: dict[str, str] = {}
        with (
            output.open("w", encoding="utf-8", buffering=1024 * 1024) as handle,
            skipped_report.open("w", encoding="utf-8", buffering=1024 * 1024) as skipped_handle,
            quarantine_report.open("w", encoding="utf-8", buffering=1024 * 1024) as quarantine_handle,
        ):
            for path in self._iter_candidate_files(root):
                if budget.max_runtime_seconds is not None and time.monotonic() - started > budget.max_runtime_seconds:
                    skipped_count += 1
                    self._write_jsonl(
                        skipped_handle,
                        {"path": str(path), "reason": "max_runtime_seconds_exceeded"},
                    )
                    break
                if budget.max_files is not None and indexed_count >= budget.max_files:
                    skipped_count += 1
                    self._write_jsonl(skipped_handle, {"path": str(path), "reason": "max_files_exceeded"})
                    continue
                suffix = _compound_suffix(path).lower()
                if suffix not in extensions:
                    skipped_count += 1
                    self._write_jsonl(skipped_handle, {"path": str(path), "reason": "unsupported_extension"})
                    continue
                record = self._record_for_path(root, path, seen_checksums=seen_checksums)
                if record.duplicate_of is not None:
                    duplicate_count += 1
                if record.quarantine_status == "blocked":
                    quarantine_count += 1
                    self._write_jsonl(
                        quarantine_handle,
                        {
                            "path": record.relative_path,
                            "reason": record.quarantine_reason or "unspecified_quarantine",
                        },
                    )
                total_size += record.size_bytes
                indexed_count += 1
                self._write_jsonl(handle, asdict(record))

        return IndexSummary(
            scan_root=root,
            output_path=output,
            skipped_report_path=skipped_report,
            quarantine_report_path=quarantine_report,
            indexed_count=indexed_count,
            skipped_count=skipped_count,
            duplicate_count=duplicate_count,
            quarantine_count=quarantine_count,
            total_size_bytes=total_size,
            max_files=budget.max_files,
            max_runtime_seconds=budget.max_runtime_seconds,
            created_at=datetime.now(UTC),
        )

    def _record_for_path(
        self,
        root: Path,
        path: Path,
        *,
        seen_checksums: dict[str, str] | None = None,
    ) -> AssetIndexRecord:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise PathEscapeError(f"path escaped scan root: {resolved}") from exc
        stat = resolved.stat()
        extension = _compound_suffix(resolved).lower()
        digest = sha256_file(resolved, chunk_size=self.chunk_size)
        duplicate_of: str | None = None
        if seen_checksums is not None:
            duplicate_of = seen_checksums.get(digest)
            seen_checksums.setdefault(digest, relative.as_posix())
        return AssetIndexRecord(
            relative_path=relative.as_posix(),
            absolute_path=str(resolved),
            extension=extension,
            asset_kind=_asset_kind(extension),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            sha256=digest,
            duplicate_of=duplicate_of,
            license_state="unknown",
            quarantine_status="blocked",
            quarantine_reason="license_state_unknown",
        )

    def _iter_candidate_files(self, root: Path) -> Iterator[Path]:
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    sorted_entries = sorted(entries, key=lambda item: item.name.lower())
                    child_dirs: list[Path] = []
                    for entry in sorted_entries:
                        if entry.is_symlink():
                            continue
                        entry_path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in EXCLUDED_DIR_NAMES:
                                child_dirs.append(entry_path)
                        elif entry.is_file(follow_symlinks=False):
                            yield entry_path
                    stack.extend(reversed(child_dirs))
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

    @staticmethod
    def _write_jsonl(handle: object, payload: dict[str, object]) -> None:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def _compound_suffix(path: Path) -> str:
    name = path.name.lower()
    for compound in (".bgeo.sc",):
        if name.endswith(compound):
            return compound
    return path.suffix.lower()


def _asset_kind(extension: str) -> str:
    return {
        ".abc": "alembic_cache",
        ".aep": "ae_template",
        ".bgeo": "houdini_geometry_cache",
        ".bgeo.sc": "houdini_geometry_cache",
        ".blend": "blender",
        ".ckpt": "comfyui_model",
        ".cube": "lut",
        ".exr": "render_frame",
        ".fbx": "fbx",
        ".hdr": "hdri",
        ".hda": "houdini_digital_asset",
        ".hip": "houdini_scene",
        ".hiplc": "houdini_scene",
        ".hipnc": "houdini_scene",
        ".jpg": "image",
        ".jpeg": "image",
        ".lut": "lut",
        ".mov": "video",
        ".mp4": "video",
        ".obj": "obj",
        ".ocio": "ocio",
        ".otl": "houdini_operator_type_library",
        ".png": "image",
        ".safetensors": "comfyui_model",
        ".tif": "pbr_texture",
        ".tiff": "pbr_texture",
        ".usd": "usd_scene",
        ".usda": "usd_scene",
        ".usdc": "usd_scene",
        ".vdb": "volume_cache",
        ".ztl": "zbrush",
        ".zpr": "zbrush",
    }.get(extension, "unknown")
