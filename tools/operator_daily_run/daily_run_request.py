"""Daily run request — immutable operator daily run request model.

Requires: run_id, operator_id, evidence_summary, replay_receipt,
human_review, approval. Rejects: production action, trading, network.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class DailyRunRequest:
    """Immutable daily run request with all required bindings."""

    request_id: str
    run_id: str
    operator_id: str
    evidence_summary_hash: str
    replay_receipt_hash: str
    patch_receipt_hashes: List[str]
    execution_receipt_hashes: List[str]
    action_plan: str
    human_review_id: str
    approval_id: str
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        run_id: str,
        operator_id: str,
        evidence_summary_hash: str,
        replay_receipt_hash: str,
        action_plan: str,
        human_review_id: str,
        approval_id: str,
        *,
        patch_receipt_hashes: List[str] | None = None,
        execution_receipt_hashes: List[str] | None = None,
    ) -> DailyRunRequest:
        # Required fields
        if not run_id.strip():
            raise ValueError("run_id required")
        if not operator_id.strip():
            raise ValueError("operator_id required")
        if not evidence_summary_hash.strip() or len(evidence_summary_hash) != 64:
            raise ValueError("evidence_summary_hash must be 64-char hex sha256")
        if not replay_receipt_hash.strip() or len(replay_receipt_hash) != 64:
            raise ValueError("replay_receipt_hash must be 64-char hex sha256")
        if not human_review_id.strip():
            raise ValueError("human_review_id required")
        if not approval_id.strip():
            raise ValueError("approval_id required")
        if not action_plan.strip():
            raise ValueError("action_plan required")

        # Reject production action
        action_lower = action_plan.lower()
        if "production" in action_lower:
            raise ValueError("production_action_rejected")
        if "trading" in action_lower:
            raise ValueError("trading_action_rejected")
        if "deploy" in action_lower and "production" in action_lower:
            raise ValueError("production_deploy_rejected")
        if any(p in action_lower for p in ("curl", "wget", "ssh", "scp", "http://", "https://")):
            raise ValueError("network_action_rejected")

        raw = "|".join([
            run_id, operator_id, evidence_summary_hash, replay_receipt_hash,
            "|".join(sorted(patch_receipt_hashes or [])),
            "|".join(sorted(execution_receipt_hashes or [])),
            action_plan, human_review_id, approval_id,
        ])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        request_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return DailyRunRequest(
            request_id=request_id,
            run_id=run_id,
            operator_id=operator_id,
            evidence_summary_hash=evidence_summary_hash,
            replay_receipt_hash=replay_receipt_hash,
            patch_receipt_hashes=sorted(patch_receipt_hashes or []),
            execution_receipt_hashes=sorted(execution_receipt_hashes or []),
            action_plan=action_plan,
            human_review_id=human_review_id,
            approval_id=approval_id,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
