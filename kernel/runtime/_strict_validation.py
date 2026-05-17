"""Strict validation helpers for deterministic V12 validators.

Provides shared helpers for strict field type/format validation used across
all V12 boundary validators. All functions are pure and side-effect free.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

__all__ = [
    "strict_bool",
    "strict_digest",
    "strict_nonempty_string",
    "validate_required_string_fields",
    "validate_required_digest_fields",
    "validate_required_bool_fields",
]

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def strict_nonempty_string(value: Any) -> bool:
    """Return True if value is a non-empty, non-whitespace-only string."""
    if not isinstance(value, str):
        return False
    if not value or not value.strip():
        return False
    return True


def strict_digest(value: Any) -> bool:
    """Return True if value is a valid sha256 digest: sha256:<64 lowercase hex chars>."""
    if not isinstance(value, str):
        return False
    return bool(_DIGEST_RE.match(value))


def strict_bool(value: Any) -> bool:
    """Return True if value is an actual bool (not 0, 1, 'true', 'false', None)."""
    return isinstance(value, bool)


def validate_required_string_fields(
    payload: dict[str, object],
    fields: Sequence[str],
    failures: list[str],
) -> None:
    """Validate required string fields: must be present, non-empty string, not None."""
    for field in fields:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not isinstance(value, str):
            failures.append(f"{field}_must_be_string")
        elif not value or not value.strip():
            failures.append(f"{field}_must_be_nonempty_string")


def validate_required_digest_fields(
    payload: dict[str, object],
    fields: Sequence[str],
    failures: list[str],
) -> None:
    """Validate required digest fields: must be present and match sha256:<64 hex>."""
    for field in fields:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not isinstance(value, str):
            failures.append(f"{field}_must_be_string")
        elif not _DIGEST_RE.match(value):
            failures.append(f"{field}_must_be_valid_digest")


def validate_required_bool_fields(
    payload: dict[str, object],
    fields: Sequence[str],
    failures: list[str],
) -> None:
    """Validate required boolean fields: must be present and actual bool."""
    for field in fields:
        value = payload.get(field)
        if value is None:
            failures.append(f"{field}_must_not_be_none")
        elif not isinstance(value, bool):
            failures.append(f"{field}_must_be_bool")
