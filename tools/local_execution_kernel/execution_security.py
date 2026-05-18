"""Execution security — security boundary enforcement for execution kernel.

No network. No main mutation. No branch delete. No production execution.
No secret/.env reads. No freeform shell. No execution by default.
"""

from __future__ import annotations

from typing import Any, Dict, List


FORBIDDEN_ACTIONS = frozenset({
    "network", "secrets", "env_read", "main_mutation", "merge",
    "push_main", "branch_delete", "production_execution", "freeform_shell",
    "execute",  # no execution in v1
})


class ExecutionSecurity:
    """Security boundary enforcement for local execution kernel."""

    @staticmethod
    def validate_flags(flags: List[str]) -> Dict[str, Any]:
        if not isinstance(flags, list):
            raise TypeError("flags must be a list")
        violations = [f for f in flags if f in FORBIDDEN_ACTIONS]
        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def validate_no_network(command_text: str) -> bool:
        cmd_lower = command_text.lower()
        network_patterns = ("curl", "wget", "nc ", "ncat ", "telnet ", "ssh ", "scp ", "rsync ")
        return not any(p in cmd_lower for p in network_patterns)

    @staticmethod
    def validate_no_main_mutation(command_text: str) -> bool:
        cmd_lower = command_text.lower()
        patterns = (
            "git checkout main", "git switch main", "git push origin main",
            "git push main", "git merge main", "git branch -d main",
            "git branch -D main",
        )
        return not any(p in cmd_lower for p in patterns)

    @staticmethod
    def validate_no_secrets(command_text: str) -> bool:
        cmd_lower = command_text.lower()
        secret_patterns = (".env", "api_key", "secret", "token", "password")
        return not any(p in cmd_lower for p in secret_patterns)

    @staticmethod
    def validate_no_production(command_text: str) -> bool:
        return "production" not in command_text.lower()

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        violations: List[str] = []
        cmd = str(payload.get("command_text", ""))

        if not ExecutionSecurity.validate_no_network(cmd):
            violations.append("network_command_detected")
        if not ExecutionSecurity.validate_no_main_mutation(cmd):
            violations.append("main_mutation_detected")
        if not ExecutionSecurity.validate_no_secrets(cmd):
            violations.append("secret_material_detected")
        if not ExecutionSecurity.validate_no_production(cmd):
            violations.append("production_execution_detected")

        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def security_gates() -> Dict[str, bool]:
        return {
            "no_network": True,
            "no_main_mutation": True,
            "no_branch_delete": True,
            "no_secret_material": True,
            "no_env_read": True,
            "no_production_execution": True,
            "no_execution_by_default": True,
            "deterministic_receipts": True,
        }
