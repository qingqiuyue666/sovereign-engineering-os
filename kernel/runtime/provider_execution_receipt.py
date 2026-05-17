"""Provider execution receipt — sealed descriptor only.

No raw prompts or responses. Deterministic digest-only receipt for
provider execution operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "ProviderExecutionReceipt",
    "validate_provider_execution_receipt",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_FIELDS = (
    "provider_id",
    "request_digest",
    "response_digest",
    "authorization_digest",
    "policy_version",
    "code_version",
    "post_run_health_digest",
    "quarantine_ref",
)

_DIGEST_FIELDS = (
    "request_digest",
    "response_digest",
    "authorization_digest",
    "post_run_health_digest",
)


@dataclass(frozen=True)
class ProviderExecutionReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_provider_execution_receipt(payload: Mapping[str, object]) -> ProviderExecutionReceipt:
    """Validate a provider execution receipt descriptor.

    All digest fields must have sha256: prefix. No forbidden fields allowed.
    """
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    for field in _DIGEST_FIELDS:
        if field in payload:
            val = payload[field]
            if isinstance(val, str) and val and not val.startswith("sha256:"):
                failures.append(f"{field}_must_be_sha256_prefixed")

    if failures:
        return ProviderExecutionReceipt(False, tuple(failures))
    return ProviderExecutionReceipt(True, ())
