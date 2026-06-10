"""Detect gaps in multipart archive groups."""

from __future__ import annotations

def detect_missing_parts(groups: list[dict[str, object]]) -> list[dict[str, object]]:
    missing: list[dict[str, object]] = []
    for group in groups:
        numbers = sorted(int(item) for item in group.get("part_numbers", []))
        if not numbers:
            continue
        expected = set(range(numbers[0], numbers[-1] + 1))
        absent = sorted(expected.difference(numbers))
        if absent:
            missing.append(
                {
                    "archive_group_id": group.get("id"),
                    "base_name": group.get("base_name"),
                    "missing_part_numbers": absent,
                    "status": "ARCHIVE_PART_MISSING",
                }
            )
    return missing
