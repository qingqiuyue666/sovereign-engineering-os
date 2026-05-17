"""Evidence vault receipt — descriptor only, no secret values.

Produces a deterministic receipt descriptor for vault operations.
Approved is false by default. Strict field typing enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    validate_required_digest_fields,
    validate_required_string_fields,
)

__all__ = [
    "EvidenceVaultReceipt",
    "validate_evidence_vault_receipt",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_STRING_FIELDS = (
    "receipt_id",
    "storage_classification",
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS = (
    "artifact_digest",
)


@dataclass(frozen=True)
class EvidenceVaultReceipt:
    accepted: bool
    approved: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "approved": self.approved,
            "failures": list(self.failures),
        }


def validate_evidence_vault_receipt(payload: Mapping[str, object]) -> EvidenceVaultReceipt:
    """Validate an evidence vault receipt descriptor with strict typing.

    Receipt is always approved=false by default.
    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    if failures:
        return EvidenceVaultReceipt(False, False, tuple(failures))
    return EvidenceVaultReceipt(True, False, ())
