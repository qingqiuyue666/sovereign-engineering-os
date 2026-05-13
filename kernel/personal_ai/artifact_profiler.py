"""Deterministic artifact profiling from a local intake ledger."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ArtifactProfileResult",
    "build_artifact_profile",
]

_CATEGORY_ORDER = (
    "spreadsheet",
    "document",
    "image",
    "video",
    "audio",
    "archive",
    "code",
    "unknown",
)

_EXTENSION_CATEGORIES = {
    ".csv": "spreadsheet",
    ".tsv": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".xlsm": "spreadsheet",
    ".xls": "spreadsheet",
    ".txt": "document",
    ".md": "document",
    ".pdf": "document",
    ".docx": "document",
    ".rtf": "document",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".tif": "image",
    ".tiff": "image",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".avi": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".aac": "audio",
    ".flac": "audio",
    ".zip": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".7z": "archive",
    ".rar": "archive",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".json": "code",
    ".yaml": "code",
    ".yml": "code",
    ".html": "code",
    ".css": "code",
    ".sql": "code",
    ".sh": "code",
}


@dataclass(frozen=True)
class ArtifactProfileResult:
    ledger_path: Path
    output_profile_path: Path
    total_files: int
    total_bytes: int
    categories: dict[str, int]


def build_artifact_profile(
    ledger_path: Path,
    output_profile_path: Path,
) -> ArtifactProfileResult:
    ledger = Path(ledger_path)
    output_path = Path(output_profile_path)

    if not ledger.exists():
        raise ValueError("ledger_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_profile_path parent is missing")

    ledger_entries = _read_ledger_entries(ledger)
    profile_entries = [_profile_entry(entry) for entry in ledger_entries]
    profile_entries.sort(key=lambda entry: entry["relative_path"])

    categories = {category: 0 for category in _CATEGORY_ORDER}
    extensions = {}
    for entry in profile_entries:
        categories[entry["category"]] += 1
        extension = entry["extension"]
        extensions[extension] = extensions.get(extension, 0) + 1

    sorted_extensions = {
        extension: extensions[extension]
        for extension in sorted(extensions)
    }
    largest_files = sorted(
        profile_entries,
        key=lambda entry: (-entry["size_bytes"], entry["relative_path"]),
    )[:10]
    total_bytes = sum(entry["size_bytes"] for entry in profile_entries)

    profile = {
        "total_files": len(profile_entries),
        "total_bytes": total_bytes,
        "categories": categories,
        "extensions": sorted_extensions,
        "largest_files": largest_files,
        "entries": profile_entries,
    }

    write_json_atomically(output_path, profile)

    return ArtifactProfileResult(
        ledger_path=ledger,
        output_profile_path=output_path,
        total_files=len(profile_entries),
        total_bytes=total_bytes,
        categories=categories,
    )


def _read_ledger_entries(ledger):
    entries = []
    with ledger.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


def _profile_entry(entry):
    relative_path = entry["relative_path"]
    extension = Path(relative_path).suffix.lower()
    category = _EXTENSION_CATEGORIES.get(extension, "unknown")
    return {
        "relative_path": relative_path,
        "size_bytes": entry["size_bytes"],
        "sha256": entry["sha256"],
        "modified_time_ns": entry["modified_time_ns"],
        "extension": extension,
        "category": category,
    }
