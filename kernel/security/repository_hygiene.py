"""Repository hygiene gate for forbidden paths and secret-like content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .secret_scanner import CoreSecretScanner, SecretFinding

__all__ = ["RepositoryHygieneResult", "check_repository_hygiene"]

_FORBIDDEN_PARTS = {".env", "secrets", "credentials", "node_modules", ".venv", "__pycache__"}
_FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".sqlite", ".db", ".log", ".dump")


@dataclass(frozen=True)
class RepositoryHygieneResult:
    clean: bool
    rejected_paths: tuple[str, ...]
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def check_repository_hygiene(
    paths: Iterable[str | Path],
    *,
    scanner: CoreSecretScanner | None = None,
    scan_file_contents: bool = False,
) -> RepositoryHygieneResult:
    active_scanner = scanner or CoreSecretScanner()
    rejected: list[str] = []
    failures: list[str] = []
    findings: list[SecretFinding] = []
    for raw_path in paths:
        path = Path(raw_path)
        normalized = path.as_posix()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        parts = set(normalized.split("/"))
        if parts & _FORBIDDEN_PARTS or normalized.endswith(_FORBIDDEN_SUFFIXES):
            rejected.append(normalized)
            failures.append("repository_path_forbidden:" + normalized)
            continue
        if scan_file_contents and path.is_file():
            scan = active_scanner.scan_file(path)
            if not scan.clean:
                findings.extend(scan.findings)
                failures.append("repository_file_contaminated:" + normalized)
    unique_failures = tuple(sorted(set(failures)))
    return RepositoryHygieneResult(
        clean=not unique_failures,
        rejected_paths=tuple(sorted(set(rejected))),
        findings=tuple(findings),
        failures=unique_failures,
    )
