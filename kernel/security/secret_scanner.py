"""Core secret scanner shared by V12 leak-prevention gates.

The scanner is intentionally bounded: regexes are simple, input is truncated,
decoded variants are limited, and no filesystem mutation or network access is
performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import base64
import hashlib
import re
import urllib.parse

__all__ = [
    "CoreSecretScanner",
    "SecretFinding",
    "SecretScanResult",
]

SAFE_TEST_MARKER = "SEOS_FAKE_SECRET_OK"
REDACTION = "[REDACTED_BY_V12_SECURITY]"
KNOWN_SAFE_TEXT_HASHES = frozenset(
    {
        hashlib.sha256(b"known-safe-v12-fixture").hexdigest(),
        hashlib.sha256(b"SEOS_KNOWN_SAFE_FAKE_VALUE").hexdigest(),
    }
)
SAFE_FAKE_PATH_PREFIXES = ("tests/", "governance/security/fixtures/")


@dataclass(frozen=True)
class SecretFinding:
    kind: str
    detail: str
    path: str | None = None


@dataclass(frozen=True)
class SecretScanResult:
    clean: bool
    findings: tuple[SecretFinding, ...]
    scanned_text_chars: int
    decoded_items_scanned: int
    truncated: bool


class CoreSecretScanner:
    """Bounded text and path scanner for secret-like material."""

    def __init__(
        self,
        *,
        max_text_chars: int = 200_000,
        max_file_bytes: int = 1_048_576,
        max_scan_items: int = 2_000,
        known_safe_hashes: Iterable[str] = KNOWN_SAFE_TEXT_HASHES,
    ) -> None:
        self.max_text_chars = max_text_chars
        self.max_file_bytes = max_file_bytes
        self.max_scan_items = max_scan_items
        self.known_safe_hashes = frozenset(known_safe_hashes)
        self._patterns: tuple[tuple[str, re.Pattern[str]], ...] = (
            ("private_key_block", re.compile(r"-----BEGIN [A-Z ]{0,32}PRIVATE KEY-----")),
            ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
            ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,200}\b")),
            ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,200}\b")),
            ("assignment_secret", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{12,200}")),
        )

    def scan_file(self, path: str | Path) -> SecretScanResult:
        file_path = Path(path)
        data = file_path.read_bytes()[: self.max_file_bytes + 1]
        truncated = len(data) > self.max_file_bytes
        text = data[: self.max_file_bytes].decode("utf-8", errors="replace")
        result = self.scan_text(text, path=file_path.as_posix())
        return SecretScanResult(
            clean=result.clean,
            findings=result.findings,
            scanned_text_chars=result.scanned_text_chars,
            decoded_items_scanned=result.decoded_items_scanned,
            truncated=result.truncated or truncated,
        )

    def scan_text(self, text: object, *, path: str | None = None) -> SecretScanResult:
        if not isinstance(text, str):
            return SecretScanResult(
                clean=False,
                findings=(SecretFinding("non_text_input", "scanner_input_must_be_text", path),),
                scanned_text_chars=0,
                decoded_items_scanned=0,
                truncated=False,
            )
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in self.known_safe_hashes:
            return SecretScanResult(True, (), 0, 0, False)
        return self._scan_bounded_text(text, path=path, decode_depth=0)

    def _scan_bounded_text(self, text: str, *, path: str | None, decode_depth: int) -> SecretScanResult:
        scan_text = text[: self.max_text_chars]
        truncated = len(text) > self.max_text_chars
        findings: list[SecretFinding] = []

        if SAFE_TEST_MARKER in scan_text and not _path_allows_fake_marker(path):
            findings.append(SecretFinding("fake_marker_outside_safe_path", SAFE_TEST_MARKER, path))

        for kind, pattern in self._patterns:
            for match in pattern.finditer(scan_text):
                if len(findings) >= self.max_scan_items:
                    break
                findings.append(SecretFinding(kind, _bounded_detail(match.group(0)), path))
            if len(findings) >= self.max_scan_items:
                break

        decoded_items = 0
        if decode_depth == 0 and len(findings) < self.max_scan_items:
            decoded_candidates = _decoded_variants(scan_text, self.max_scan_items)
            for decoded in decoded_candidates:
                if decoded_items >= self.max_scan_items or len(findings) >= self.max_scan_items:
                    break
                decoded_items += 1
                nested = self._scan_bounded_text(decoded, path=path, decode_depth=1)
                for finding in nested.findings:
                    findings.append(
                        SecretFinding(
                            "decoded_" + finding.kind,
                            finding.detail,
                            finding.path,
                        )
                    )
                    if len(findings) >= self.max_scan_items:
                        break

        unique = tuple(_dedupe_findings(findings))
        return SecretScanResult(
            clean=not unique,
            findings=unique,
            scanned_text_chars=len(scan_text),
            decoded_items_scanned=decoded_items,
            truncated=truncated,
        )


def _path_allows_fake_marker(path: str | None) -> bool:
    if path is None:
        return False
    normalized = Path(path).as_posix().lstrip("./")
    return normalized.startswith(SAFE_FAKE_PATH_PREFIXES)


def _bounded_detail(value: str) -> str:
    return value[:80]


def _dedupe_findings(findings: Iterable[SecretFinding]) -> list[SecretFinding]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[SecretFinding] = []
    for finding in findings:
        key = (finding.kind, finding.detail, finding.path)
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result


def _decoded_variants(text: str, max_items: int) -> list[str]:
    variants: list[str] = []
    unquoted = urllib.parse.unquote(text)
    if unquoted != text:
        variants.append(unquoted[:200_000])

    token_re = re.compile(r"\b[A-Za-z0-9+/_=-]{16,512}\b")
    for match in token_re.finditer(text):
        if len(variants) >= max_items:
            break
        token = match.group(0)
        padded = token + ("=" * ((4 - len(token) % 4) % 4))
        for altchars in (None, b"-_"):
            try:
                raw = base64.b64decode(padded.encode("ascii"), altchars=altchars, validate=False)
            except Exception:
                continue
            if not raw:
                continue
            decoded = raw.decode("utf-8", errors="ignore")
            if decoded and decoded != token and any(ch.isprintable() for ch in decoded):
                variants.append(decoded[:200_000])
                break
    return variants
