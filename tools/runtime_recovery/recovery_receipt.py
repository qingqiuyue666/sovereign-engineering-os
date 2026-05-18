"""Recovery receipt — deterministic recovery receipts.

Rollback compatible. No production mutation. No network. No secrets.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class RecoveryReceipt:
    """Deterministic recovery receipt."""

    receipt_id: str
    bundle_id: str
    plan_id: str
    status: str
    rollback_compatible: bool
    is_destructive: bool
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_recovery_execution: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def produce_recovery_receipt(
    bundle_id: str,
    plan_id: str,
    status: str,
    rollback_compatible: bool = True,
    is_destructive: bool = False,
    created_at: str = "",
) -> RecoveryReceipt:
    if status not in ("ready", "applied", "failed"):
        raise ValueError(f"invalid status: {status}")
    if not bundle_id.strip():
        raise ValueError("bundle_id required")
    if not plan_id.strip():
        raise ValueError("plan_id required")

    raw = "|".join([
        bundle_id, plan_id, status,
        str(rollback_compatible), str(is_destructive),
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = hashlib.blake2b(
        f"{bundle_id}|{plan_id}|{canonical}".encode(), digest_size=16,
    ).hexdigest()

    return RecoveryReceipt(
        receipt_id=receipt_id,
        bundle_id=bundle_id,
        plan_id=plan_id,
        status=status,
        rollback_compatible=rollback_compatible,
        is_destructive=is_destructive,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )
