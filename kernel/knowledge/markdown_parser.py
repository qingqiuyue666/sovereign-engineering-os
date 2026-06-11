"""Parse SEOS knowledge Markdown notes into bounded metadata records."""

from __future__ import annotations

from pathlib import Path

from kernel.knowledge.frontmatter import split_frontmatter
from kernel.knowledge.object_model import digest_payload, now_utc, safe_id
from kernel.knowledge.redaction import digest_text, public_path_ref
from kernel.security.secret_scanner import CoreSecretScanner

__all__ = ["parse_knowledge_note", "parse_knowledge_note_file"]

_ALLOWED_AUTHORITY = {"proposal", "mirror", "receipt", "invalid"}


def parse_knowledge_note(text: str, *, path_ref: str = "inline") -> dict[str, object]:
    """Parse Markdown frontmatter/body into a SEOS knowledge note record.

    The parser is intentionally non-authoritative: it returns metadata and
    digests only. It never creates tasks, approvals, permits, or executions.
    """

    scan = CoreSecretScanner().scan_text(text, path=path_ref)
    try:
        frontmatter, body = split_frontmatter(text)
        frontmatter_error = None
    except ValueError as exc:
        frontmatter = {"authority": "invalid"}
        body = text
        frontmatter_error = str(exc)

    authority = str(frontmatter.get("authority") or "proposal")
    problems: list[str] = []
    if frontmatter_error:
        problems.append("invalid_frontmatter")
    if authority not in _ALLOWED_AUTHORITY:
        problems.append("invalid_authority")
    if not scan.clean:
        problems.append("sensitive_content_detected")
    if bool(frontmatter.get("execution_authority_granted", False)):
        problems.append("knowledge_note_claims_execution_authority")

    note = {
        "schema": "seos_knowledge_note_parse_v1",
        "created_at": now_utc(),
        "path_ref": path_ref,
        "seos_type": str(frontmatter.get("seos_type") or "note"),
        "seos_id": safe_id(frontmatter.get("seos_id") or path_ref, fallback="note"),
        "authority": authority if authority in _ALLOWED_AUTHORITY else "invalid",
        "frontmatter": dict(frontmatter),
        "body_digest": digest_text(body),
        "note_digest": digest_text(text),
        "body_line_count": len(body.splitlines()),
        "public": frontmatter.get("public"),
        "local_path_redacted": frontmatter.get("local_path_redacted"),
        "execution_authority_granted": False,
        "sensitive_content_detected": not scan.clean,
        "finding_kinds": sorted({finding.kind for finding in scan.findings}),
        "problems": problems,
    }
    note["digest"] = digest_payload(note)
    return note


def parse_knowledge_note_file(path: str | Path, *, root: str | Path | None = None, public: bool = True) -> dict[str, object]:
    note_path = Path(path).expanduser().resolve()
    path_ref = public_path_ref(note_path, root=root) if public else note_path.as_posix()
    if not note_path.exists() or not note_path.is_file():
        return {"ok": False, "error": "knowledge_note_not_found", "path_ref": path_ref}
    parsed = parse_knowledge_note(note_path.read_text(encoding="utf-8", errors="replace"), path_ref=path_ref)
    return {"ok": not parsed["problems"], "note": parsed}
