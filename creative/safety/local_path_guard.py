"""Detect local absolute path leaks in public artifacts."""

from __future__ import annotations

from pathlib import Path
from creative.common import LOCAL_PATH_MARKERS

def find_local_path_leaks(paths: list[Path]) -> list[str]:
    leaks: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                leaks.append(f"{path.as_posix()}:{marker}")
    return leaks
