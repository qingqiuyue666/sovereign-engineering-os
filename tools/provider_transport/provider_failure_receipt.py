"""Provider failure receipt — deterministic failure record.

When a provider transport is rejected, a failure receipt captures the reason.
Deterministic: same inputs produce the same failure receipt. No wall-clock.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ProviderFailureReceipt:
    """Immutable deterministic failure receipt for a rejected provider transport."""
    failure_id: str
    provider_id: str
    request_id: str
    failure_reason: str
    canonical_hash: str
    rejected_at_gate: str
    module_version: str
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "provider_id": self.provider_id,
            "request_id": self.request_id,
            "failure_reason": self.failure_reason,
            "canonical_hash": self.canonical_hash,
            "rejected_at_gate": self.rejected_at_gate,
            "module_version": self.module_version,
            "created_at": self.created_at,
        }


def _hash_hex(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def produce_failure_receipt(
    provider_id: str,
    request_id: str,
    failure_reason: str,
    rejected_at_gate: str = "preflight",
) -> ProviderFailureReceipt:
    """Produce a deterministic failure receipt.

    failure_reason and rejected_at_gate are embedded in the canonical hash,
    making the receipt fully deterministic for the same failure scenario.
    """
    created_at = "1970-01-01T00:00:00Z"

    failure_id = _hash_hex(
        provider_id, request_id, failure_reason, rejected_at_gate,
    )

    canonical_hash = _hash_hex(
        failure_id,
        provider_id,
        request_id,
        failure_reason,
        rejected_at_gate,
        created_at,
    )

    return ProviderFailureReceipt(
        failure_id=failure_id,
        provider_id=provider_id,
        request_id=request_id,
        failure_reason=failure_reason,
        canonical_hash=canonical_hash,
        rejected_at_gate=rejected_at_gate,
        module_version="v1",
        created_at=created_at,
    )
