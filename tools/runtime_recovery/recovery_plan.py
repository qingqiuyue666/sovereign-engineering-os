"""Recovery plan — creates recovery plans from failure bundles.

Recovery plans are rollback-compatible and non-destructive.
No production mutation. No network. No secret material.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


FORBIDDEN_RECOVERY_ACTIONS = frozenset({
    "production_deploy", "production_mutation", "network_call",
    "secret_access", "env_read", "destructive_mutation",
    "branch_delete", "main_mutation", "force_push",
})


@dataclass(frozen=True)
class RecoveryPlan:
    """Immutable recovery plan with rollback compatibility."""

    plan_id: str
    bundle_id: str
    recovery_steps: List[str]
    rollback_compatible: bool
    is_destructive: bool
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        bundle_id: str,
        recovery_steps: List[str],
    ) -> RecoveryPlan:
        if not bundle_id.strip():
            raise ValueError("bundle_id required")
        if not recovery_steps:
            raise ValueError("recovery_steps must not be empty")

        # Reject destructive recovery actions
        is_destructive = False
        for step in recovery_steps:
            step_lower = step.lower()
            for forbidden in FORBIDDEN_RECOVERY_ACTIONS:
                sanitized_step = step_lower.replace(" ", "").replace("_", "")
                sanitized_forbidden = forbidden.replace("_", "")
                if sanitized_forbidden in sanitized_step:
                    is_destructive = True
                    raise ValueError(f"destructive_recovery_rejected: {step}")

        raw = "|".join([bundle_id, "|".join(recovery_steps)])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        plan_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return RecoveryPlan(
            plan_id=plan_id,
            bundle_id=bundle_id,
            recovery_steps=list(recovery_steps),
            rollback_compatible=True,
            is_destructive=False,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
