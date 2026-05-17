"""Evidence vault receipt — descriptor only, no secret values.

Produces a deterministic receipt descriptor for vault operations.
Approved is false by default (requires explicit human approval).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

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

_REQUIRED_FIELDS = (
    "receipt_id",
    "artifact_digest",
    "storage_classification",
    "policy_version",
    "code_version",
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
    """Validate an evidence vault receipt descriptor.

    Receipt is always approved=false by default. Only validates structural
    integrity and forbidden fields.
    """
    failures: list[str] = []

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

    if failures:
        return EvidenceVaultReceipt(False, False, tuple(failures))

    return EvidenceVaultReceipt(True, False, ())
