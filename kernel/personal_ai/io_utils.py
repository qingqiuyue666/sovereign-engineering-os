"""Deterministic local artifact output helpers for Personal AI."""

from pathlib import Path
import json
import tempfile
from typing import Any, Iterable, Mapping

__all__ = [
    "write_json_atomically",
    "write_jsonl_atomically",
]


def write_json_atomically(
    output_path: Path,
    payload: Mapping[str, Any],
) -> None:
    output_file = Path(output_path)
    _require_existing_parent(output_file)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_file.parent,
        prefix=f".{output_file.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        json.dump(payload, temporary_file, indent=2, sort_keys=True)
        temporary_file.write("\n")
        temporary_file.flush()

    temporary_path.replace(output_file)


def write_jsonl_atomically(
    output_path: Path,
    entries: Iterable[Mapping[str, Any]],
) -> None:
    output_file = Path(output_path)
    _require_existing_parent(output_file)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_file.parent,
        prefix=f".{output_file.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        for entry in entries:
            temporary_file.write(
                json.dumps(entry, separators=(",", ":"), sort_keys=True)
            )
            temporary_file.write("\n")
        temporary_file.flush()

    temporary_path.replace(output_file)


def _require_existing_parent(output_file):
    parent = output_file.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("output_path parent is missing")
