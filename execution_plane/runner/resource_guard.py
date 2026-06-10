"""Output resource budget checks."""

from __future__ import annotations

from pathlib import Path


def output_budget_violations(
    output_root: str | Path,
    *,
    max_files: int,
    max_output_bytes: int,
) -> list[str]:
    root = Path(output_root)
    files = [path for path in root.rglob("*") if path.is_file()]
    total_size = sum(path.stat().st_size for path in files)
    violations: list[str] = []
    if len(files) > max_files:
        violations.append("max_files_exceeded")
    if total_size > max_output_bytes:
        violations.append("max_output_bytes_exceeded")
    return violations

