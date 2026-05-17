"""Protected storage interface — contract only, no real backend.

Default disabled. No encryption implementation, no key material.
Rejects live_write=true. Fail-closed deterministic result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

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

_REQUIRED_FIELDS = (
    "storage_request_id",
    "artifact_digest",
    "policy_version",
    "code_version",
)


@dataclass(frozen=True)
class ProtectedStorageResult:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
        }


def validate_protected_storage_request(payload: Mapping[str, object]) -> ProtectedStorageResult:
    """Validate a protected storage interface request.

    Rejects live_write=true (no real storage backend).
    Requires human_approval_token field to be present (not validated for real).
    Fail-closed: any violation returns accepted=False.
    """
    failures: list[str] = []

    # Reject live_write
    if payload.get("live_write") is True:
        failures.append("live_write_rejected")

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    if "artifact_digest" in payload:
        val = payload["artifact_digest"]
        if isinstance(val, str) and val and not val.startswith("sha256:"):
            failures.append("artifact_digest_must_be_sha256_prefixed")

    # Human approval token must be present (not validated for real tokens)
    if "human_approval_token" not in payload:
        failures.append("human_approval_token_required")

    if failures:
        return ProtectedStorageResult(False, tuple(failures))

    return ProtectedStorageResult(True, ())
