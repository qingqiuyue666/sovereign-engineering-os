"""Operator daily run — local-only validation runtime.

Coordinates daily run request validation, evidence/replay/patch/local-kernel
binding, human review gate, approval gate, and receipt generation.

v1 — local validation / receipt runtime only. No autonomous production action. No trading. No network.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .daily_run_request import DailyRunRequest
from .run_window import RunWindow
from .review_gate import ReviewGate
from .operator_run_receipt import (
    OperatorRunReceipt, OperatorRunFailureReceipt,
    produce_operator_run_receipt, produce_operator_run_failure_receipt,
)
from .operator_run_canonical_hash import OperatorRunCanonicalHash
from .operator_run_security import OperatorRunSecurity


class OperatorDailyRun:
    """Real operator daily run validation runtime — local-only v1."""

    def __init__(self) -> None:
        self._receipts: List[OperatorRunReceipt] = []
        self._failure_receipts: List[OperatorRunFailureReceipt] = []
        self._requests: List[DailyRunRequest] = []

    def create_request(
        self,
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
        sec = OperatorRunSecurity.validate_action_plan(action_plan)
        if not sec["valid"]:
            raise ValueError(f"action_plan_rejected: {sec['violations']}")
        request = DailyRunRequest.create(
            run_id=run_id,
            operator_id=operator_id,
            evidence_summary_hash=evidence_summary_hash,
            replay_receipt_hash=replay_receipt_hash,
            action_plan=action_plan,
            human_review_id=human_review_id,
            approval_id=approval_id,
            patch_receipt_hashes=patch_receipt_hashes,
            execution_receipt_hashes=execution_receipt_hashes,
        )
        self._requests.append(request)
        return request

    def validate_window(self, label: str) -> Dict[str, Any]:
        return RunWindow.validate(label)

    def validate_review(self, human_review_id: str, approval_id: str) -> Dict[str, Any]:
        return ReviewGate.validate(human_review_id, approval_id)

    @staticmethod
    def _requires_patch(action_plan: str) -> bool:
        return "patch" in action_plan.lower()

    @staticmethod
    def _requires_local_kernel(action_plan: str) -> bool:
        text = action_plan.lower()
        return any(marker in text for marker in ("local kernel", "kernel validation", "dry-run receipt"))

    def validate_chain_context(self, request: DailyRunRequest, chain_hash: str = "") -> Dict[str, Any]:
        issues: List[str] = []
        if not request.evidence_summary_hash:
            issues.append("evidence_summary_hash_missing")
        if not request.replay_receipt_hash:
            issues.append("replay_receipt_hash_missing")
        if self._requires_patch(request.action_plan) and not request.patch_receipt_hashes:
            issues.append("patch_receipt_hash_required_by_action_plan")
        if self._requires_local_kernel(request.action_plan) and not request.execution_receipt_hashes:
            issues.append("local_kernel_receipt_hash_required_by_action_plan")
        if chain_hash and len(chain_hash) != 64:
            issues.append("chain_hash_invalid")
        return {"valid": len(issues) == 0, "issues": issues}

    def approve(self, request: DailyRunRequest, *, chain_hash: str = "") -> OperatorRunReceipt:
        review = self.validate_review(request.human_review_id, request.approval_id)
        if not review["review_passed"]:
            failure = produce_operator_run_failure_receipt(
                request.run_id,
                "review_gate_failed: " + ", ".join(review.get("failure_reasons", [])),
                "OP_RUN_REVIEW_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("review_gate_failed")

        sec = OperatorRunSecurity.validate_action_plan(request.action_plan)
        if not sec["valid"]:
            failure = produce_operator_run_failure_receipt(
                request.run_id,
                "security_violation: " + ", ".join(sec["violations"]),
                "OP_RUN_SECURITY_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("security_violation")

        chain = self.validate_chain_context(request, chain_hash=chain_hash)
        if not chain["valid"]:
            failure = produce_operator_run_failure_receipt(
                request.run_id,
                "chain_context_failed: " + ", ".join(chain["issues"]),
                "OP_RUN_CHAIN_CONTEXT_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("chain_context_failed")

        receipt = produce_operator_run_receipt(
            run_id=request.run_id,
            operator_id=request.operator_id,
            status="approved",
            evidence_bound=bool(request.evidence_summary_hash),
            replay_bound=bool(request.replay_receipt_hash),
            review_passed=review["review_passed"],
            approval_passed=review["gates"].get("approval_present", False),
            replay_receipt_hash=request.replay_receipt_hash,
            patch_receipt_hashes=request.patch_receipt_hashes,
            execution_receipt_hashes=request.execution_receipt_hashes,
            chain_hash=chain_hash,
        )
        self._receipts.append(receipt)
        return receipt

    def produce_failure_receipt(
        self, run_id: str, failure_reason: str, failure_code: str,
    ) -> OperatorRunFailureReceipt:
        receipt = produce_operator_run_failure_receipt(run_id, failure_reason, failure_code)
        self._failure_receipts.append(receipt)
        return receipt

    def receipt_count(self) -> int:
        return len(self._receipts)

    def failure_count(self) -> int:
        return len(self._failure_receipts)

    def runtime_hash(self) -> str:
        parts: List[str] = []
        for r in self._receipts:
            parts.append(r.canonical_hash)
        for f in self._failure_receipts:
            parts.append(f.canonical_hash)
        return OperatorRunCanonicalHash.canonical_hash(*parts) if parts else hashlib.sha256(b"empty_runtime").hexdigest()

    def reset(self) -> None:
        self._receipts = []
        self._failure_receipts = []
        self._requests = []
