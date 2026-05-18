"""Operator daily run — main operator daily run runtime orchestrator.

Coordinates daily run request validation, evidence/replay/patch/execution
binding, human review gate, approval gate, receipt generation.

v1 — contract-only. No autonomous production action. No trading. No network.
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
    """Real operator daily run runtime — v1 contract-only.

    Validates daily run requests, enforces review/approval gates,
    and produces deterministic receipts. No autonomous production action.
    """

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
        # Security: validate action plan
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

    def approve(self, request: DailyRunRequest) -> OperatorRunReceipt:
        # Validate review gate
        review = self.validate_review(request.human_review_id, request.approval_id)
        if not review["review_passed"]:
            failure = produce_operator_run_failure_receipt(
                request.run_id,
                "review_gate_failed: " + ", ".join(review.get("failure_reasons", [])),
                "OP_RUN_REVIEW_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("review_gate_failed")

        # Security re-check
        sec = OperatorRunSecurity.validate_action_plan(request.action_plan)
        if not sec["valid"]:
            failure = produce_operator_run_failure_receipt(
                request.run_id,
                "security_violation: " + ", ".join(sec["violations"]),
                "OP_RUN_SECURITY_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("security_violation")

        evidence_bound = bool(request.evidence_summary_hash)
        replay_bound = bool(request.replay_receipt_hash)

        receipt = produce_operator_run_receipt(
            run_id=request.run_id,
            operator_id=request.operator_id,
            status="approved",
            evidence_bound=evidence_bound,
            replay_bound=replay_bound,
            review_passed=review["review_passed"],
            approval_passed=review["gates"].get("approval_present", False),
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
