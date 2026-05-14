"""Snapshot normalization helpers for deterministic Personal AI tests."""

from pathlib import Path
import json
from typing import Any, Mapping

__all__ = [
    "canonical_snapshot_json",
    "normalize_snapshot_payload",
]


def normalize_snapshot_payload(
    payload: Any,
    *,
    path_replacements: Mapping[Path | str, str] | None = None,
) -> Any:
    replacements = _ordered_replacements(path_replacements or {})
    return _normalize_value(payload, replacements)


def canonical_snapshot_json(
    payload: Any,
    *,
    path_replacements: Mapping[Path | str, str] | None = None,
) -> str:
    normalized = normalize_snapshot_payload(
        payload,
        path_replacements=path_replacements,
    )
    return json.dumps(
        normalized,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _ordered_replacements(path_replacements):
    replacements = [
        (Path(raw_path).as_posix(), replacement)
        for raw_path, replacement in path_replacements.items()
    ]
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    return replacements


def _normalize_value(value, replacements):
    if isinstance(value, dict):
        return {
            str(key): _normalize_value(value[key], replacements)
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, list):
        return [
            _normalize_value(item, replacements)
            for item in value
        ]
    if isinstance(value, tuple):
        return [
            _normalize_value(item, replacements)
            for item in value
        ]
    if isinstance(value, Path):
        return _normalize_string(value.as_posix(), replacements)
    if isinstance(value, str):
        return _normalize_string(value, replacements)
    return value


def _normalize_string(value, replacements):
    normalized = value
    for source, replacement in replacements:
        normalized = normalized.replace(source, replacement)
    return normalized
