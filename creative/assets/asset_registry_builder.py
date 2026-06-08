"""Build portable asset registries from read-only local asset scans."""

from __future__ import annotations

from pathlib import Path
from creative.common import write_jsonl
from creative.assets.local_asset_library import build_asset_library_scan

def build_registry(
    root: Path,
    output_jsonl: Path | None = None,
    *,
    max_depth: int = 12,
    max_file_read_bytes: int = 1_048_576,
    mode: str = "public",
) -> list[dict[str, object]]:
    scan = build_asset_library_scan(root, mode=mode, max_depth=max_depth, max_file_read_bytes=max_file_read_bytes)
    enriched = list(scan["assets"])
    if output_jsonl is not None:
        write_jsonl(output_jsonl, enriched)
    return enriched
