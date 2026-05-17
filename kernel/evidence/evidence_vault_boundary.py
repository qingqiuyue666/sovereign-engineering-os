"""Evidence vault boundary — deterministic validation only.

Default disabled. No real encryption, KMS, or secret material. Validates
vault request descriptors against policy with strict field typing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    validate_required_digest_fields,
    validate_required_string_fields,
)

__all__ = [
    "EvidenceVaultBoundaryReceipt",
    "validate_evidence_vault_boundary",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "real_secret_material",
)

_REQUIRED_STRING_FIELDS = (
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS = (
    "artifact_digest",
)


@dataclass(frozen=True)
class EvidenceVaultBoundaryReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"accepted": self.accepted, "failures": list(self.failures)}


def validate_evidence_vault_boundary(payload: Mapping[str, object]) -> EvidenceVaultBoundaryReceipt:
    """Validate an evidence vault request with strict typing.

    Default disabled — rejects vault_enabled=true (must be actual bool).
    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    # vault_enabled gate — must be actual bool
    vault_val = payload_dict.get("vault_enabled")
    if vault_val is not None:
        if not isinstance(vault_val, bool):
            failures.append("vault_enabled_must_be_bool")
        elif vault_val is True:
            failures.append("vault_enabled_rejected_default_disabled")

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return EvidenceVaultBoundaryReceipt(False, tuple(failures))
    return EvidenceVaultBoundaryReceipt(True, ())
