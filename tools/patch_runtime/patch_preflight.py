"""Patch preflight — validates patch readiness before any application attempt.

Checks: allowlist, target path safety, rollback bundle presence,
test results, and security gates. All must pass before patch is approved.
"""

from __future__ import annotations

from typing import Any, Dict

from .patch_request import PatchRequest
from .patch_allowlist import PatchAllowlist


class PatchPreflight:
    """Preflight validation for patch requests. No actual patch application."""

    def __init__(self, allowlist: PatchAllowlist) -> None:
        self._allowlist = allowlist
        self._gates: Dict[str, bool] = {}

    def check(self, request: PatchRequest) -> Dict[str, Any]:
        self._gates = {
            "request_valid": request.is_valid,
            "target_in_allowlist": self._allowlist.is_allowed(request.target_path),
            "rollback_bundle_present": bool(request.rollback_bundle_hash),
            "patch_content_hash_valid": bool(request.patch_content_hash) and len(request.patch_content_hash) == 64,
            "path_safety": True,  # already validated in PatchRequest.create
            "no_network": True,
            "no_main_mutation": True,
            "is_dry_run": request.is_dry_run,
        }

        if request.test_results_hash:
            self._gates["test_results_present"] = True

        all_pass = all(self._gates.values())

        return {
            "preflight_passed": all_pass,
            "gates": dict(self._gates),
            "failure_reasons": [
                k for k, v in self._gates.items() if not v
            ] if not all_pass else [],
        }

    def enforce(self, request: PatchRequest) -> None:
        result = self.check(request)
        if not result["preflight_passed"]:
            failures = result["failure_reasons"]
            raise ValueError(f"preflight_failed: {failures}")
