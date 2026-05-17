"""Evidence vault boundary — deterministic validation only.

Default disabled. No real encryption, KMS, or secret material. Validates
vault request descriptors against policy and produces boundary receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

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

_REQUIRED_FIELDS = (
    "artifact_digest",
    "policy_version",
    "code_version",
)


@dataclass(frozen=True)
class EvidenceVaultBoundaryReceipt:
    accepted: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
        }


def validate_evidence_vault_boundary(payload: Mapping[str, object]) -> EvidenceVaultBoundaryReceipt:
    """Validate an evidence vault request against policy boundaries.

    Returns accepted=True only if vault_enabled is not true, no forbidden
    fields are present, and all required fields are provided.
    """
    failures: list[str] = []

    # Default disabled — reject if vault_enabled is explicitly true
    if payload.get("vault_enabled") is True:
        failures.append("vault_enabled_rejected_default_disabled")

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
        return EvidenceVaultBoundaryReceipt(False, tuple(failures))

    return EvidenceVaultBoundaryReceipt(True, ())
