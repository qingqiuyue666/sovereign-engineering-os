"""Scan SEOS Markdown control vaults without granting authority."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from kernel.knowledge.frontmatter import split_frontmatter
from kernel.knowledge.redaction import digest_text, public_path_ref
from kernel.security.secret_scanner import CoreSecretScanner

__all__ = ["scan_control_vault"]

_ALLOWED_AUTHORITIES = {"proposal", "mirror", "receipt", "invalid"}


def scan_control_vault(vault: str | Path, *, public: bool = True) -> dict[str, object]:
    """Return a bounded inventory of SEOS notes in a Markdown vault.

    The scanner reads Markdown metadata and text digests only. It never executes
    commands, never treats a note as approval, and never mutates SEOS workspace
    artifacts.
    """

    root = Path(vault).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return {"ok": False, "error": "vault_not_found", "vault": root.as_posix()}
    notes: list[dict[str, object]] = []
    problems: list[dict[str, object]] = []
    scanner = CoreSecretScanner()
    for path in _iter_markdown(root):
        rel = public_path_ref(path, root=root) if public else path.as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        scan = scanner.scan_text(text, path=rel)
        try:
            frontmatter, _body = split_frontmatter(text)
        except ValueError as exc:
            problems.append({"path_ref": rel, "problem": "invalid_frontmatter", "message": str(exc)})
            frontmatter = {"authority": "invalid"}
        authority = str(frontmatter.get("authority") or "proposal")
        execution_claim = bool(frontmatter.get("execution_authority_granted", False))
        if authority not in _ALLOWED_AUTHORITIES:
            problems.append({"path_ref": rel, "problem": "invalid_authority", "authority": authority})
        if execution_claim:
            problems.append({"path_ref": rel, "problem": "knowledge_note_claims_execution_authority"})
        if scan.clean is False:
            problems.append({"path_ref": rel, "problem": "sensitive_content_detected", "finding_kinds": sorted({item.kind for item in scan.findings})})
        notes.append(
            {
                "path_ref": rel,
                "digest": digest_text(text),
                "seos_type": frontmatter.get("seos_type"),
                "seos_id": frontmatter.get("seos_id"),
                "authority": authority,
                "public": frontmatter.get("public"),
                "local_path_redacted": frontmatter.get("local_path_redacted"),
                "execution_authority_granted": False,
                "claimed_execution_authority": execution_claim,
                "sensitive_content_detected": not scan.clean,
            }
        )
    return {
        "ok": not problems,
        "schema": "seos_control_vault_scan_v1",
        "vault_ref": public_path_ref(root) if public else root.as_posix(),
        "public": public,
        "note_count": len(notes),
        "problem_count": len(problems),
        "notes": notes,
        "problems": problems,
        "execution_authority_granted": False,
    }


def _iter_markdown(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())
