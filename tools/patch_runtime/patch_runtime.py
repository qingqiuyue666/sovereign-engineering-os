"""Patch runtime — main patch application runtime orchestrator.

Coordinates dry-run patch request validation, allowlist enforcement, preflight
checks, receipt generation, and failure handling.

v1 — dry-run validation only. No actual patch application. No network.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from .patch_request import PatchRequest
from .patch_allowlist import PatchAllowlist
from .patch_preflight import PatchPreflight
from .patch_receipt import (
    PatchReceipt, PatchFailureReceipt,
    produce_patch_receipt, produce_patch_failure_receipt,
)
from .patch_rollback import PatchRollback
from .patch_canonical_hash import PatchCanonicalHash
from .patch_security import PatchSecurity


class PatchRuntime:
    """Real patch validation runtime — v1 dry-run only.

    Validates patch requests, enforces allowlists, runs preflight checks,
    and produces deterministic receipts. No actual patch application.
    """

    def __init__(self) -> None:
        self._allowlist = PatchAllowlist()
        self._preflight = PatchPreflight(self._allowlist)
        self._receipts: List[PatchReceipt] = []
        self._failure_receipts: List[PatchFailureReceipt] = []
        self._requests: List[PatchRequest] = []

    def configure_allowlist(self, paths: List[str]) -> None:
        for path in paths:
            self._allowlist.add_path(path)

    def create_request(
        self,
        patch_id: str,
        target_path: str,
        patch_content_hash: str,
        rollback_bundle_hash: str,
        *,
        allowlist_ids: List[str] | None = None,
        test_results_hash: str = "",
        operation: str = "validate_only",
        replay_receipt_hash: str = "",
    ) -> PatchRequest:
        request = PatchRequest.create(
            patch_id=patch_id,
            target_path=target_path,
            patch_content_hash=patch_content_hash,
            rollback_bundle_hash=rollback_bundle_hash,
            allowlist_ids=allowlist_ids,
            test_results_hash=test_results_hash,
            is_dry_run=True,
            operation=operation,
            replay_receipt_hash=replay_receipt_hash,
        )
        self._requests.append(request)
        return request

    def create_rollback(self, patch_id: str, rollback_hash: str, plan: str = "") -> PatchRollback:
        return PatchRollback.create(
            patch_id=patch_id,
            rollback_hash=rollback_hash,
            rollback_plan=plan,
        )

    def validate_request(self, request: PatchRequest) -> Dict[str, Any]:
        sec = PatchSecurity.validate_payload(request.to_dict())
        if not sec["valid"]:
            return {"valid": False, "reason": "security_violation", "details": sec["violations"]}

        allowlist_result = self._allowlist.validate(request.target_path)
        if not allowlist_result["valid"]:
            return {"valid": False, "reason": allowlist_result["reason"]}

        if request.is_dry_run is not True:
            return {"valid": False, "reason": "patch_runtime_v1_requires_dry_run"}

        return {"valid": True, "reason": None}

    def run_preflight(self, request: PatchRequest) -> Dict[str, Any]:
        return self._preflight.check(request)

    def approve(self, request: PatchRequest) -> PatchReceipt:
        validation = self.validate_request(request)
        if not validation["valid"]:
            failure = produce_patch_failure_receipt(
                request.request_id,
                validation.get("reason", "validation_failed"),
                "PATCH_VALIDATION_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError(validation["reason"])

        preflight = self.run_preflight(request)
        if not preflight["preflight_passed"]:
            failure = produce_patch_failure_receipt(
                request.request_id,
                "preflight_failed: " + ", ".join(preflight.get("failure_reasons", [])),
                "PATCH_PREFLIGHT_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("preflight_failed")

        sec_payload = {
            "patch_id": request.patch_id,
            "target_path": request.target_path,
            "operation": request.operation,
            "replay_receipt_hash": request.replay_receipt_hash,
            "flags": [],
        }
        sec_result = PatchSecurity.validate_payload(sec_payload)
        if not sec_result["valid"]:
            failure = produce_patch_failure_receipt(
                request.request_id,
                "security_gate_failed: " + ", ".join(sec_result["violations"]),
                "PATCH_SECURITY_FAILED",
            )
            self._failure_receipts.append(failure)
            raise ValueError("security_gate_failed")

        receipt = produce_patch_receipt(request, preflight)
        self._receipts.append(receipt)
        return receipt

    def produce_failure_receipt(
        self, request_id: str, failure_reason: str, failure_code: str,
    ) -> PatchFailureReceipt:
        receipt = produce_patch_failure_receipt(request_id, failure_reason, failure_code)
        self._failure_receipts.append(receipt)
        return receipt

    def receipt_count(self) -> int:
        return len(self._receipts)

    def failure_count(self) -> int:
        return len(self._failure_receipts)

    def runtime_hash(self) -> str:
        parts: List[str] = []
        parts.append(self._allowlist.allowlist_hash())
        for r in self._receipts:
            parts.append(r.canonical_hash)
        for f in self._failure_receipts:
            parts.append(f.canonical_hash)
        return PatchCanonicalHash.canonical_hash(*parts) if parts else hashlib.sha256(b"empty_runtime").hexdigest()

    def reset(self) -> None:
        self._allowlist = PatchAllowlist()
        self._preflight = PatchPreflight(self._allowlist)
        self._receipts = []
        self._failure_receipts = []
        self._requests = []
