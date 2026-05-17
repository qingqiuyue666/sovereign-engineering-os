"""Provider execution receipt — sealed descriptor only.

No raw prompts or responses. Deterministic digest-only receipt with strict
field typing for provider execution operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    validate_required_digest_fields,
    validate_required_string_fields,
)

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

_REQUIRED_STRING_FIELDS = (
    "provider_id",
    "policy_version",
    "code_version",
    "quarantine_ref",
)

_REQUIRED_DIGEST_FIELDS = (
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
    """Validate a provider execution receipt descriptor with strict typing.

    All digest fields must match sha256:<64 lowercase hex>.
    All string fields must be non-empty, non-None strings.
    No forbidden fields allowed.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return ProviderExecutionReceipt(False, tuple(failures))
    return ProviderExecutionReceipt(True, ())
