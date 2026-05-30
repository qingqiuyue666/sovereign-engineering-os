"""Build a portable JSONL asset registry from read-only scan records."""

from __future__ import annotations

from pathlib import Path
from creative.common import write_jsonl
from creative.assets.license_metadata_infer import infer_license
from creative.assets.readonly_asset_scan import scan_assets

def build_registry(root: Path, output_jsonl: Path | None = None, *, max_depth: int = 4, max_file_read_bytes: int = 1_048_576) -> list[dict[str, object]]:
    records = scan_assets(root, max_depth=max_depth, max_file_read_bytes=max_file_read_bytes)
    enriched = [{**record, "license": infer_license(record)} for record in records]
    if output_jsonl is not None:
        write_jsonl(output_jsonl, enriched)
    return enriched
