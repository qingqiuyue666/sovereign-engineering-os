"""Core read-only scanner for V12 leak prevention.

The scanner is pure and side-effect free. It never opens files, mutates files,
reads environment variables, performs network access, or shells out.
"""

from __future__ import annotations

import base64
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from urllib.parse import unquote

MAX_TEXT_CHARS = 200_000
MAX_FILE_BYTES = 1_048_576
MAX_SCAN_ITEMS = 1_000
FAKE_MARKER = "SEOS_FAKE_SECRET_OK"
FAKE_MARKER_ALLOWED_PREFIXES = ("tests/", "governance/security/fixtures/")
SAFE_HASH_FIELDS = {"git_blob_sha1", "sha256", "digest", "content_hash", "snapshot_root_hash", "output_hash", "root_commitment", "artifact_hash", "cross_phase_digest"}
SENSITIVE_FIELD_FRAGMENTS = ("api" + "_key", "tok" + "en", "pass" + "word", "cook" + "ie", "auth" + "orization", "sec" + "ret", "env" + "_value", "private" + "_key", "raw" + "_prompt", "raw" + "_provider" + "_response")
_PATTERNS = (
    ("private_material_block", re.compile("-" * 5 + r"BEGIN [A-Z ]*PRIVATE [A-Z ]*" + "-" * 5)),
    ("sensitive_label", re.compile(r"(?i)(api[_-]?key|tok" + r"en|sec" + r"ret|pass" + r"word|cook" + r"ie|auth" + r"orization)\s*[:=]")),
    ("raw_payload_label", re.compile(r"(?i)(raw_prompt|raw_provider_response|secret_value|env_value)\s*[:=]")),
    ("env_assignment", re.compile(r"(?m)^[A-Z][A-Z0-9_]{2,}\s*=")),
)


@dataclass(frozen=True)
class SecretFinding:
    finding_type: str
    path: str
    field: str
    message: str


@dataclass(frozen=True)
class ScanResult:
    accepted: bool
    findings: tuple[SecretFinding, ...]
    truncated: bool = False


class CoreSecretScanner:
    """Shared scanner engine for all leak-prevention gates."""

    def __init__(self, max_text_chars: int = MAX_TEXT_CHARS, max_file_bytes: int = MAX_FILE_BYTES, max_scan_items: int = MAX_SCAN_ITEMS):
        self.max_text_chars = max_text_chars
        self.max_file_bytes = max_file_bytes
        self.max_scan_items = max_scan_items

    def scan_text(self, text: str, *, path: str = "<memory>", field: str = "text") -> ScanResult:
        if not isinstance(text, str):
            return ScanResult(False, (SecretFinding("type_error", path, field, "text must be str"),))
        if FAKE_MARKER in text and not _path_allows_fake_marker(path):
            return ScanResult(False, (SecretFinding("fake_marker_outside_allowed_path", path, field, "fake marker outside approved paths"),))
        truncated = len(text) > self.max_text_chars
        sample = text[: self.max_text_chars]
        findings = list(_scan_plain(sample, path, field))
        for decoded_name, decoded in _decode_variants(sample):
            findings.extend(_scan_plain(decoded, path, f"{field}:{decoded_name}"))
        return ScanResult(not findings, tuple(findings), truncated)

    def scan_mapping(self, payload: Mapping[str, Any], *, path: str = "<mapping>") -> ScanResult:
        if not isinstance(payload, Mapping):
            return ScanResult(False, (SecretFinding("type_error", path, "payload", "payload must be mapping"),))
        findings: list[SecretFinding] = []
        count = 0
        for key, value in _walk(payload):
            count += 1
            if count > self.max_scan_items:
                findings.append(SecretFinding("scan_item_limit_exceeded", path, key, "mapping scan item limit exceeded"))
                break
            normalized_key = key.split(".")[-1].split("[")[0]
            if normalized_key not in SAFE_HASH_FIELDS and any(fragment in normalized_key.lower() for fragment in SENSITIVE_FIELD_FRAGMENTS):
                findings.append(SecretFinding("dangerous_field_name", path, key, "dangerous field name"))
            if isinstance(value, str):
                if normalized_key in SAFE_HASH_FIELDS:
                    continue
                result = self.scan_text(value, path=path, field=key)
                findings.extend(result.findings)
                if _looks_high_entropy(value):
                    findings.append(SecretFinding("high_entropy_string", path, key, "high entropy string outside safe hash field"))
        return ScanResult(not findings, tuple(findings))

    def scan_file_metadata(self, *, path: str, size_bytes: int, is_binary: bool = False) -> ScanResult:
        findings: list[SecretFinding] = []
        if size_bytes > self.max_file_bytes:
            findings.append(SecretFinding("file_too_large", path, "size", "file exceeds scanner size cap"))
        if is_binary:
            findings.append(SecretFinding("binary_file_blocked", path, "binary", "binary file blocked from text scanning"))
        return ScanResult(not findings, tuple(findings))


def _scan_plain(text: str, path: str, field: str) -> Iterable[SecretFinding]:
    for finding_type, pattern in _PATTERNS:
        if pattern.search(text):
            yield SecretFinding(finding_type, path, field, f"matched {finding_type}")


def _decode_variants(text: str) -> Iterable[tuple[str, str]]:
    url_decoded = unquote(text)
    if url_decoded != text:
        yield ("url", url_decoded[:MAX_TEXT_CHARS])
    compact = re.sub(r"\s+", "", text)
    if 16 <= len(compact) <= 4096 and re.fullmatch(r"[A-Za-z0-9+/=]+", compact or ""):
        try:
            decoded = base64.b64decode(compact, validate=True).decode("utf-8", errors="ignore")
        except Exception:
            return
        if decoded:
            yield ("base64", decoded[:MAX_TEXT_CHARS])


def _walk(payload: Mapping[str, Any], prefix: str = "") -> Iterable[tuple[str, Any]]:
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            yield from _walk(value, path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]"
                if isinstance(item, Mapping):
                    yield from _walk(item, item_path)
                else:
                    yield (item_path, item)
        else:
            yield (path, value)


def _path_allows_fake_marker(path: str) -> bool:
    return path.startswith(FAKE_MARKER_ALLOWED_PREFIXES)


def _looks_high_entropy(value: str) -> bool:
    if len(value) < 32 or len(value) > 256:
        return False
    alphabet = set(value)
    if len(alphabet) < 12:
        return False
    entropy = 0.0
    for char in alphabet:
        p = value.count(char) / len(value)
        entropy -= p * math.log2(p)
    return entropy >= 4.5
