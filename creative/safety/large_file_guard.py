"""Large file guard for public commits."""

from __future__ import annotations

from pathlib import Path

def find_large_files(paths: list[Path], *, max_bytes: int = 5_000_000) -> list[str]:
    return [path.as_posix() for path in paths if path.exists() and path.is_file() and path.stat().st_size > max_bytes]
