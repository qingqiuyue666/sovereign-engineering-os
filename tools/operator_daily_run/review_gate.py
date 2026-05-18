"""Review gate — human review and approval gate for operator daily runs.

Both human review and explicit approval are required before any
operator action can be approved. No autonomous production action.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict


class ReviewGate:
    """Human review and approval gate enforcement."""

    @staticmethod
    def validate(
        human_review_id: str,
        approval_id: str,
    ) -> Dict[str, Any]:
        gates: Dict[str, bool] = {
            "human_review_present": bool(human_review_id and human_review_id.strip()),
            "approval_present": bool(approval_id and approval_id.strip()),
        }

        all_pass = all(gates.values())

        return {
            "review_passed": all_pass,
            "gates": gates,
            "failure_reasons": [k for k, v in gates.items() if not v] if not all_pass else [],
        }

    @staticmethod
    def enforce(human_review_id: str, approval_id: str) -> None:
        result = ReviewGate.validate(human_review_id, approval_id)
        if not result["review_passed"]:
            failures = result["failure_reasons"]
            raise ValueError(f"review_gate_failed: {failures}")

    @staticmethod
    def gate_hash(human_review_id: str, approval_id: str) -> str:
        return hashlib.sha256(
            f"{human_review_id}|{approval_id}".encode()
        ).hexdigest()
