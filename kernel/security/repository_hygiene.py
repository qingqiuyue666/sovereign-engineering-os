"""Repository hygiene checks for V12 leak prevention.

This module is read-only. It validates path metadata and optional text content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from kernel.security.secret_scanner import CoreSecretScanner, SecretFinding

_BLOCKED_EXACT = {".env", ".env.local"}
_BLOCKED_PREFIXES = ("secrets/", "credentials/", "node_modules/", ".venv/", "__pycache__/")
_BLOCKED_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".mobileprovision", ".sqlite", ".db", ".log")


@dataclass(frozen=True)
class RepositoryHygieneResult:
    accepted: bool
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def validate_repo_paths(paths: Iterable[str]) -> RepositoryHygieneResult:
    findings: list[SecretFinding] = []
    for path in paths:
        normalized = path.strip().replace("\\", "/")
        if normalized in _BLOCKED_EXACT:
            findings.append(SecretFinding("blocked_repo_path", normalized, "path", "blocked exact path"))
        if normalized.startswith(_BLOCKED_PREFIXES):
            findings.append(SecretFinding("blocked_repo_prefix", normalized, "path", "blocked path prefix"))
        if normalized.endswith(_BLOCKED_SUFFIXES):
            findings.append(SecretFinding("blocked_repo_suffix", normalized, "path", "blocked path suffix"))
    return RepositoryHygieneResult(not findings, tuple(findings), () if not findings else ("repository_hygiene_failed",))


def validate_repo_file_content(path: str, text: str, *, scanner: CoreSecretScanner | None = None) -> RepositoryHygieneResult:
    engine = scanner or CoreSecretScanner()
    meta = validate_repo_paths([path])
    scan = engine.scan_text(text, path=path, field="content")
    findings = tuple(meta.findings) + tuple(scan.findings)
    return RepositoryHygieneResult(not findings, findings, () if not findings else ("repository_hygiene_failed",))
