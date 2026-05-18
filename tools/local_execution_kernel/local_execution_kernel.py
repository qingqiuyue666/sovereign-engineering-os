"""Local execution kernel — main execution kernel runtime orchestrator.

Coordinates execution request validation, allowlist enforcement, preflight
checks, receipt generation, and failure handling.

v1 — contract-only. No command execution. No network.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .execution_request import ExecutionRequest
from .command_allowlist import CommandAllowlist
from .execution_preflight import ExecutionPreflight
from .execution_receipt import (
    ExecutionReceipt, ExecutionFailureReceipt,
    produce_execution_receipt, produce_execution_failure_receipt,
)
from .execution_canonical_hash import ExecutionCanonicalHash
from .execution_security import ExecutionSecurity


class LocalExecutionKernel:
    """Real local execution kernel runtime — v1 contract-only.

    Validates execution requests, enforces allowlists, runs preflight
    checks, and produces deterministic receipts. No actual execution.
    """

    def __init__(self) -> None:
        self._allowlist = CommandAllowlist()
        self._preflight = ExecutionPreflight(self._allowlist)
        self._receipts: List[ExecutionReceipt] = []
        self._failure_receipts: List[ExecutionFailureReceipt] = []
        self._requests: List[ExecutionRequest] = []

    def configure_allowlist(self, commands: List[str]) -> None:
        for cmd in commands:
            self._allowlist.add(cmd)

    def create_request(
        self, execution_id: str, command_category: str, command_text: str,
    ) -> ExecutionRequest:
        request = ExecutionRequest.create(
            execution_id=execution_id,
            command_category=command_category,
            command_text=command_text,
        )
        self._requests.append(request)
        return request

    def validate_request(self, request: ExecutionRequest) -> Dict[str, Any]:
        sec = ExecutionSecurity.validate_payload(request.to_dict())
        if not sec["valid"]:
            return {"valid": False, "reason": "security_violation", "details": sec["violations"]}

        allowlist_result = self._allowlist.validate(request.command_text)
        if not allowlist_result["valid"]:
            return {"valid": False, "reason": allowlist_result["reason"]}

        return {"valid": True, "reason": None}

    def run_preflight(self, request: ExecutionRequest) -> Dict[str, Any]:
        return self._preflight.check(request)

    def approve(self, request: ExecutionRequest) -> ExecutionReceipt:
        validation = self.validate_request(request)
        if not validation["valid"]:
            failure = produce_execution_failure_receipt(
                request.execution_id,
                validation.get("reason", "validation_failed"),
                "EXEC_VALIDATION_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError(validation["reason"])

        preflight = self.run_preflight(request)
        if not preflight["preflight_passed"]:
            failure = produce_execution_failure_receipt(
                request.execution_id,
                "preflight_failed: " + ", ".join(preflight.get("failure_reasons", [])),
                "EXEC_PREFLIGHT_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("preflight_failed")

        receipt = produce_execution_receipt(
            request.execution_id,
            "approved",
            request.command_category,
            preflight,
        )
        self._receipts.append(receipt)
        return receipt

    def produce_failure_receipt(
        self, execution_id: str, failure_reason: str, failure_code: str,
    ) -> ExecutionFailureReceipt:
        receipt = produce_execution_failure_receipt(execution_id, failure_reason, failure_code)
        self._failure_receipts.append(receipt)
        return receipt

    def receipt_count(self) -> int:
        return len(self._receipts)

    def failure_count(self) -> int:
        return len(self._failure_receipts)

    def kernel_hash(self) -> str:
        parts: List[str] = []
        parts.append(self._allowlist.allowlist_hash())
        for r in self._receipts:
            parts.append(r.canonical_hash)
        for f in self._failure_receipts:
            parts.append(f.canonical_hash)
        return ExecutionCanonicalHash.canonical_hash(*parts) if parts else hashlib.sha256(b"empty_kernel").hexdigest()

    def reset(self) -> None:
        self._allowlist = CommandAllowlist()
        self._preflight = ExecutionPreflight(self._allowlist)
        self._receipts = []
        self._failure_receipts = []
        self._requests = []
