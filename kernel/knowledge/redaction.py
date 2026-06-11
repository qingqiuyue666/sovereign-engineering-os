"""Redaction helpers for public SEOS knowledge exports."""

from __future__ import annotations

from pathlib import Path
import hashlib

from kernel.security.secret_scanner import CoreSecretScanner

__all__ = [
    "SECRET_REDACTION_NOTICE",
    "digest_text",
    "public_path_ref",
    "redact_note_if_needed",
]

SECRET_REDACTION_NOTICE = "[redacted: secret-like content detected by SEOS knowledge export]"


def digest_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def public_path_ref(path: str | Path, *, root: str | Path | None = None) -> str:
    """Return a stable public path reference without leaking absolute paths."""

    candidate = Path(path)
    if root is not None:
        try:
            return candidate.resolve().relative_to(Path(root).resolve()).as_posix()
        except Exception:
            pass
    text = candidate.as_posix()
    if candidate.is_absolute() or text.startswith("~"):
        return "redacted-local-path:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return text


def redact_note_if_needed(text: str, *, path: str = "knowledge_note") -> tuple[str, dict[str, object]]:
    """Return text unless the bounded scanner detects secret-like content.

    The scanner returns finding kinds only. Secret details are never propagated to
    the exported note metadata.
    """

    result = CoreSecretScanner().scan_text(text, path=path)
    if result.clean:
        return text, {
            "secret_like_content_detected": False,
            "redacted": False,
            "finding_kinds": [],
            "scanner_truncated": result.truncated,
        }
    finding_kinds = sorted({finding.kind for finding in result.findings})
    safe_text = "\n".join(
        [
            "# Redacted SEOS Knowledge Note",
            "",
            SECRET_REDACTION_NOTICE,
            "",
            "The original note body was withheld because it matched secret-like patterns.",
            "SEOS knowledge exports preserve evidence digests and object IDs, not raw secret-adjacent text.",
            "",
            "## Finding Kinds",
            *[f"- {kind}" for kind in finding_kinds],
            "",
        ]
    )
    return safe_text, {
        "secret_like_content_detected": True,
        "redacted": True,
        "finding_kinds": finding_kinds,
        "scanner_truncated": result.truncated,
    }
