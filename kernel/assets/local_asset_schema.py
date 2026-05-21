"""Schemas and constants for the local asset runtime v1 slice."""

from dataclasses import dataclass
from pathlib import Path

RUNTIME_VERSION = "local_asset_runtime_v1"

ASSET_MANIFEST_FILE = "asset_manifest.json"
ASSET_INDEX_FILE = "asset_index.json"
DUPLICATES_REPORT_FILE = "duplicates_report.json"
MEDIA_INVENTORY_FILE = "media_inventory.md"
AUDIT_LOG_FILE = "asset_runtime_audit_log.jsonl"
VALIDATION_REPORT_FILE = "asset_runtime_validation_report.json"
QUARANTINE_MANIFEST_FILE = "asset_runtime_quarantine_manifest.json"

OUTPUT_FILENAMES = (
    ASSET_MANIFEST_FILE,
    ASSET_INDEX_FILE,
    DUPLICATES_REPORT_FILE,
    MEDIA_INVENTORY_FILE,
    AUDIT_LOG_FILE,
    VALIDATION_REPORT_FILE,
    QUARANTINE_MANIFEST_FILE,
)

ASSET_TYPE_ORDER = (
    "video",
    "image",
    "audio",
    "dcc",
    "comfyui_workflow",
    "color/lookdev",
    "fx/cache",
    "script",
    "unknown",
)


@dataclass(frozen=True)
class LocalAssetRuntimeResult:
    input_dir: Path
    output_dir: Path
    output_paths: dict[str, Path]
    files_scanned: int
    bytes_scanned: int
    duplicate_groups: int
    quarantined_paths: int
    recursive: bool
    include_hidden: bool
    project_id: str | None = None
