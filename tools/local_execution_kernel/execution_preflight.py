"""Execution preflight — validates execution readiness before any command run.

Checks: allowlist, network patterns, main mutation, secret material,
production execution. All must pass before execution is approved.
No actual execution performed.
"""

from __future__ import annotations

from typing import Any, Dict

from .execution_request import ExecutionRequest
from .command_allowlist import CommandAllowlist


class ExecutionPreflight:
    """Preflight validation for execution requests. No actual execution."""

    def __init__(self, allowlist: CommandAllowlist) -> None:
        self._allowlist = allowlist
        self._gates: Dict[str, bool] = {}

    def check(self, request: ExecutionRequest) -> Dict[str, Any]:
        cmd_lower = request.command_text.lower()

        self._gates = {
            "request_valid": request.is_valid,
            "category_valid": True,  # validated in create
            "allowlist_valid": self._allowlist.is_allowed(request.command_text),
            "no_network_patterns": not any(
                p in cmd_lower for p in ("curl", "wget", "nc ", "ncat ", "telnet ", "ssh ", "scp ", "rsync ")
            ),
            "no_secret_patterns": not any(
                p in cmd_lower for p in (".env", "api_key", "secret", "token", "password")
            ),
            "no_main_mutation": not any(
                pattern in cmd_lower for pattern in (
                    "git checkout main", "git switch main", "git push origin main",
                    "git push main", "git merge main", "git branch -d main",
                    "git branch -D main",
                )
            ),
            "no_production_execution": "production" not in cmd_lower,
        }

        all_pass = all(self._gates.values())

        return {
            "preflight_passed": all_pass,
            "gates": dict(self._gates),
            "failure_reasons": [k for k, v in self._gates.items() if not v] if not all_pass else [],
        }

    def enforce(self, request: ExecutionRequest) -> None:
        result = self.check(request)
        if not result["preflight_passed"]:
            failures = result["failure_reasons"]
            raise ValueError(f"preflight_failed: {failures}")
