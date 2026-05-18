"""Real runtime recovery / failure bundle integration.

v1 — contract-only. No destructive recovery. No production mutation.
No network. No secret material. Deterministic receipts.
"""

from __future__ import annotations

from .failure_bundle import FailureBundle
from .recovery_plan import RecoveryPlan
from .recovery_receipt import RecoveryReceipt, produce_recovery_receipt
from .runtime_recovery_canonical_hash import RuntimeRecoveryCanonicalHash

__all__ = [
    "FailureBundle",
    "RecoveryPlan",
    "RecoveryReceipt",
    "produce_recovery_receipt",
    "RuntimeRecoveryCanonicalHash",
]
