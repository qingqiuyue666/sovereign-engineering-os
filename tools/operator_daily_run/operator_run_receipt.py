"""Operator run receipt — deterministic operator daily run receipts.

No autonomous production action. No trading. No network.
All receipts deterministic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class OperatorRunReceipt:
    """Deterministic operator daily run receipt."""

    receipt_id: str
    run_id: str
    operator_id: str
    status: str
    evidence_bound: bool
    replay_bound: bool
    review_passed: bool
    approval_passed: bool
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_production_action: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperatorRunFailureReceipt:
    """Deterministic operator run failure receipt."""

    receipt_id: str
    run_id: str
    failure_reason: str
    failure_code: str
    canonical_hash: str
    created_at: str
    module_version: str = "v1"
    no_production_action: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hash_id(*parts: str) -> str:
    return hashlib.blake2b("|".join(parts).encode(), digest_size=16).hexdigest()


def produce_operator_run_receipt(
    run_id: str,
    operator_id: str,
    status: str,
    evidence_bound: bool,
    replay_bound: bool,
    review_passed: bool,
    approval_passed: bool,
    created_at: str = "",
) -> OperatorRunReceipt:
    if status not in ("approved", "rejected"):
        raise ValueError(f"invalid status: {status}")

    raw = "|".join([
        run_id, operator_id, status,
        str(evidence_bound), str(replay_bound),
        str(review_passed), str(approval_passed),
    ])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(run_id, operator_id, canonical)

    return OperatorRunReceipt(
        receipt_id=receipt_id,
        run_id=run_id,
        operator_id=operator_id,
        status=status,
        evidence_bound=evidence_bound,
        replay_bound=replay_bound,
        review_passed=review_passed,
        approval_passed=approval_passed,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )


def produce_operator_run_failure_receipt(
    run_id: str,
    failure_reason: str,
    failure_code: str,
    created_at: str = "",
) -> OperatorRunFailureReceipt:
    if not failure_reason.strip():
        raise ValueError("failure_reason required")
    if not failure_code.strip():
        raise ValueError("failure_code required")

    raw = "|".join([run_id, failure_reason, failure_code])
    canonical = hashlib.sha256(raw.encode()).hexdigest()
    receipt_id = _hash_id(run_id, "failure", canonical)

    return OperatorRunFailureReceipt(
        receipt_id=receipt_id,
        run_id=run_id,
        failure_reason=failure_reason,
        failure_code=failure_code,
        canonical_hash=canonical,
        created_at=created_at or "1970-01-01T00:00:00Z",
    )
