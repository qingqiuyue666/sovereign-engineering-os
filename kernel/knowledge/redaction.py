"""Redaction helpers for public SEOS knowledge exports."""

from __future__ import annotations

from pathlib import Path
import hashlib
import re

from kernel.security.secret_scanner import CoreSecretScanner, SecretScanResult

__all__ = [
    "SECRET_REDACTION_NOTICE",
    "digest_text",
    "normalize_digest_tokens_for_scan",
    "public_path_ref",
    "redact_note_if_needed",
    "scan_knowledge_text",
]

SECRET_REDACTION_NOTICE = "[redacted: secret-like content detected by SEOS knowledge export]"
_DIGEST_RE = re.compile(r"sha256:[0-9a-fA-F]{16,64}")
_REDACTED_LOCAL_PATH_RE = re.compile(r"redacted-local-path:[0-9a-fA-F]{8,32}")


def digest_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_digest_tokens_for_scan(text: str) -> str:
    """Replace known-safe SEOS digest/path tokens before secret scanning.

    SEOS knowledge notes intentionally contain many SHA-256 digests and redacted
    local-path identifiers. These are not secrets, but they are long token-like
    strings. Normalizing them reduces bounded scanner false positives while still
    scanning human text, commands, URLs, and metadata for real secret-like values.
    """

    text = _DIGEST_RE.sub("sha256:SEOS_DIGEST_REDACTED", text)
    text = _REDACTED_LOCAL_PATH_RE.sub("redacted-local-path:SEOS_PATH_DIGEST_REDACTED", text)
    return text


def scan_knowledge_text(text: str, *, path: str = "knowledge_note") -> SecretScanResult:
    return CoreSecretScanner().scan_text(normalize_digest_tokens_for_scan(text), path=path)


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

    result = scan_knowledge_text(text, path=path)
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
