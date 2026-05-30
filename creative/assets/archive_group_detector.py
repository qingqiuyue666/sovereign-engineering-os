"""Detect multipart archive groups from file metadata."""

from __future__ import annotations

import re
from pathlib import Path
from creative.common import SCHEMA_VERSION, stable_id

PART_PATTERNS = (
    re.compile(r"^(?P<base>.+)\.part(?P<part>\d+)\.rar$", re.IGNORECASE),
    re.compile(r"^(?P<base>.+)\.(?P<part>\d{3})$", re.IGNORECASE),
)

def detect_archive_groups(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        name = str(record.get("filename", ""))
        base = ""
        part_number = 0
        for pattern in PART_PATTERNS:
            match = pattern.match(name)
            if match:
                base = match.group("base")
                part_number = int(match.group("part"))
                break
        if not base:
            suffix = Path(name).suffix.lower()
            if suffix in {".zip", ".rar", ".7z"}:
                base = Path(name).stem
                part_number = 1
        if base:
            grouped.setdefault(base, []).append({**record, "part_number": part_number})
    groups = []
    for base, parts in sorted(grouped.items()):
        numbers = sorted(int(part.get("part_number", 0)) for part in parts if int(part.get("part_number", 0)) > 0)
        groups.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": stable_id("ARC", base),
                "base_name": base,
                "part_numbers": numbers,
                "part_count": len(parts),
                "status": "GROUPED" if parts else "EMPTY",
                "read_only": True,
            }
        )
    return groups
