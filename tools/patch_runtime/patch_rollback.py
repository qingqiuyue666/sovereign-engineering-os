"""Patch rollback — rollback bundle validation and management.

Every patch must have a rollback bundle. No destructive patches allowed
in v1 without rollback capability.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class PatchRollback:
    """Immutable rollback bundle reference."""

    rollback_id: str
    patch_id: str
    rollback_hash: str
    rollback_plan: str
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        patch_id: str,
        rollback_hash: str,
        rollback_plan: str = "",
    ) -> PatchRollback:
        if not patch_id.strip():
            raise ValueError("patch_id required")
        if not rollback_hash or len(rollback_hash) != 64:
            raise ValueError("rollback_hash must be 64-char hex sha256")

        raw = "|".join([patch_id, rollback_hash, rollback_plan])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        rollback_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return PatchRollback(
            rollback_id=rollback_id,
            patch_id=patch_id,
            rollback_hash=rollback_hash,
            rollback_plan=rollback_plan,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
