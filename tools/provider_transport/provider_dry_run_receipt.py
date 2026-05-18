"""Provider dry-run receipt — deterministic, no wall-clock, hash-only.

Produces a frozen receipt for every provider transport dry-run execution.
The receipt contains hashes and metadata only — no raw payload, no secrets,
no wall-clock timestamps. Fully deterministic: same input produces same receipt.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ProviderDryRunReceipt:
    """Immutable deterministic dry-run receipt for a provider transport.

    No raw payload. No secrets. No wall-clock in the receipt hash.
    created_at is fixed to a deterministic value for the hash.
    """
    receipt_id: str
    provider_id: str
    request_id: str
    request_digest: str
    status: str
    canonical_hash: str
    capability_bits: str
    evidence_binding_hash: str
    budget_consumed: float
    rate_limit_consumed: int
    module_version: str
    no_provider_call: bool
    no_network: bool
    dry_run: bool
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "provider_id": self.provider_id,
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "status": self.status,
            "canonical_hash": self.canonical_hash,
            "capability_bits": self.capability_bits,
            "evidence_binding_hash": self.evidence_binding_hash,
            "budget_consumed": self.budget_consumed,
            "rate_limit_consumed": self.rate_limit_consumed,
            "module_version": self.module_version,
            "no_provider_call": self.no_provider_call,
            "no_network": self.no_network,
            "dry_run": self.dry_run,
            "created_at": self.created_at,
        }


def _hash_hex(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def produce_dry_run_receipt(
    provider_id: str,
    request_id: str,
    request_digest: str,
    capability_token: str,
    evidence_binding: str,
    budget_consumed: float = 0.0,
    rate_limit_consumed: int = 0,
    status: str = "gated",
) -> ProviderDryRunReceipt:
    """Produce a deterministic dry-run receipt.

    All fields in the canonical hash are stable — no wall-clock, no random.
    created_at is the epoch sentinel to signal deterministic mode.
    """
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("provider_id_must_be_nonempty_string")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id_must_be_nonempty_string")

    capability_bits = hashlib.sha256(capability_token.encode()).hexdigest()[:16]
    evidence_binding_hash = hashlib.sha256(
        f"ev_binding:{evidence_binding}".encode()
    ).hexdigest()

    receipt_id = _hash_hex(
        provider_id, request_id, request_digest, capability_bits,
    )

    # Deterministic created_at (epoch sentinel, NOT wall-clock)
    created_at = "1970-01-01T00:00:00Z"

    # Canonical hash — no wall-clock, fully deterministic
    canonical_hash = _hash_hex(
        receipt_id,
        provider_id,
        request_id,
        request_digest,
        capability_bits,
        evidence_binding_hash,
        f"{budget_consumed:.2f}",
        str(rate_limit_consumed),
        status,
        "v1",
        created_at,
    )

    return ProviderDryRunReceipt(
        receipt_id=receipt_id,
        provider_id=provider_id,
        request_id=request_id,
        request_digest=request_digest,
        status=status,
        canonical_hash=canonical_hash,
        capability_bits=capability_bits,
        evidence_binding_hash=evidence_binding_hash,
        budget_consumed=budget_consumed,
        rate_limit_consumed=rate_limit_consumed,
        module_version="v1",
        no_provider_call=True,
        no_network=True,
        dry_run=True,
        created_at=created_at,
    )
