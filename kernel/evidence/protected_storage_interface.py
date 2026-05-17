"""Protected storage interface — contract only, no real backend.

Default disabled. No encryption implementation, no key material.
Rejects live_write=true. Fail-closed deterministic result.
Strict field typing enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    validate_required_digest_fields,
    validate_required_string_fields,
)

__all__ = [
    "ProtectedStorageResult",
    "validate_protected_storage_request",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_STRING_FIELDS = (
    "storage_request_id",
    "policy_version",
    "code_version",
    "human_approval_token",
)

_REQUIRED_DIGEST_FIELDS = (
    "artifact_digest",
)


@dataclass(frozen=True)
class ProtectedStorageResult:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_protected_storage_request(payload: Mapping[str, object]) -> ProtectedStorageResult:
    """Validate a protected storage interface request with strict typing.

    Rejects live_write=true (must be actual bool). Fail-closed.
    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    Human approval token required as non-empty string.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    # live_write gate — must be actual bool
    lw_val = payload_dict.get("live_write")
    if lw_val is not None:
        if not isinstance(lw_val, bool):
            failures.append("live_write_must_be_bool")
        elif lw_val is True:
            failures.append("live_write_rejected")

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return ProtectedStorageResult(False, tuple(failures))
    return ProtectedStorageResult(True, ())
