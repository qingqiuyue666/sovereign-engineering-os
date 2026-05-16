"""Read-only environment sanitizer for V12 leak prevention."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

_ALLOWED_KEYS = {"PATH", "HOME", "USER", "SHELL", "TMPDIR", "LANG", "LC_ALL", "PYTHONPATH"}
_BLOCKED_FRAGMENTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE", "AUTH", "CREDENTIAL")


@dataclass(frozen=True)
class EnvironmentSanitizerResult:
    accepted: bool
    sanitized_env: dict[str, str]
    removed_keys: tuple[str, ...]
    failures: tuple[str, ...]


def sanitize_environment(env: Mapping[str, str], *, allowed_keys: set[str] | None = None) -> EnvironmentSanitizerResult:
    if not isinstance(env, Mapping):
        return EnvironmentSanitizerResult(False, {}, (), ("env_must_be_mapping",))
    allowed = allowed_keys or _ALLOWED_KEYS
    sanitized: dict[str, str] = {}
    removed: list[str] = []
    failures: list[str] = []
    for key, value in env.items():
        key_text = str(key)
        if key_text in allowed and not _blocked_key(key_text):
            sanitized[key_text] = "[REDACTED]" if value else ""
        else:
            removed.append(key_text)
            if _blocked_key(key_text):
                failures.append("blocked_environment_key_removed")
    return EnvironmentSanitizerResult(True, sanitized, tuple(sorted(removed)), tuple(sorted(set(failures))))


def _blocked_key(key: str) -> bool:
    upper = key.upper()
    return any(fragment in upper for fragment in _BLOCKED_FRAGMENTS)
