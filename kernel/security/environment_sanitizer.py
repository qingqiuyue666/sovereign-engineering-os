"""Environment mapping sanitizer for V12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .secret_scanner import CoreSecretScanner, REDACTION, SecretFinding

__all__ = ["EnvironmentSanitizerResult", "sanitize_environment"]

_SENSITIVE_KEY_PARTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE", "CREDENTIAL")


@dataclass(frozen=True)
class EnvironmentSanitizerResult:
    accepted: bool
    sanitized: dict[str, str]
    redacted_keys: tuple[str, ...]
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def sanitize_environment(env: Mapping[str, object], *, scanner: CoreSecretScanner | None = None) -> EnvironmentSanitizerResult:
    if not isinstance(env, Mapping):
        return EnvironmentSanitizerResult(False, {}, (), (), ("environment_must_be_mapping",))
    active_scanner = scanner or CoreSecretScanner()
    sanitized: dict[str, str] = {}
    redacted: list[str] = []
    findings: list[SecretFinding] = []
    for key, value in env.items():
        key_text = str(key)
        value_text = "" if value is None else str(value)
        scan = active_scanner.scan_text(value_text, path=f"env:{key_text}")
        sensitive_key = any(part in key_text.upper() for part in _SENSITIVE_KEY_PARTS)
        if sensitive_key or not scan.clean:
            sanitized[key_text] = REDACTION
            redacted.append(key_text)
            findings.extend(scan.findings)
        else:
            sanitized[key_text] = value_text
    return EnvironmentSanitizerResult(
        accepted=True,
        sanitized=sanitized,
        redacted_keys=tuple(sorted(redacted)),
        findings=tuple(findings),
        failures=(),
    )
