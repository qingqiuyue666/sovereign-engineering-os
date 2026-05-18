"""Patch security — security boundary enforcement for patch runtime.

No network. No git push/merge/branch delete. No freeform shell.
No destructive mutation in v1. No overclaim about actual patch application.
"""

from __future__ import annotations

from typing import Any, Dict, List


FORBIDDEN_ACTIONS = frozenset({
    "network", "git_push", "git_merge", "branch_delete",
    "main_mutation", "freeform_shell", "destructive_mutation",
    "production_apply", "secret_read", "env_read",
})

FORBIDDEN_PATTERNS = (
    "API_KEY", "SECRET", "TOKEN", ".env", "password", "credential",
    "private_key", "raw_secret",
)

FORBIDDEN_NETWORK_PATTERNS = (
    "curl", "wget", "ssh", "scp", "nc ", "telnet", "http://", "https://",
)


class PatchSecurity:
    """Security boundary enforcement for patch application runtime."""

    @staticmethod
    def validate_flags(flags: List[str]) -> Dict[str, Any]:
        if not isinstance(flags, list):
            raise TypeError("flags must be a list")
        violations = [f for f in flags if f in FORBIDDEN_ACTIONS]
        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def validate_no_network(text: str) -> bool:
        text_lower = text.lower()
        return not any(p in text_lower for p in FORBIDDEN_NETWORK_PATTERNS)

    @staticmethod
    def validate_no_secrets(text: str) -> bool:
        text_lower = text.lower()
        return not any(p.lower() in text_lower for p in FORBIDDEN_PATTERNS)

    @staticmethod
    def validate_no_main_mutation(text: str) -> bool:
        text_lower = text.lower()
        mutation_patterns = (
            "git checkout main", "git switch main", "git push origin main",
            "git push main", "git merge main", "git branch -d main",
            "git branch -D main",
        )
        return not any(p in text_lower for p in mutation_patterns)

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        violations: List[str] = []
        for key, value in payload.items():
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.lower() in str(key).lower():
                    violations.append(f"forbidden_key: {key}")
            if isinstance(value, str):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.lower() in value.lower():
                        violations.append(f"forbidden_value_in_{key}")

        text = str(payload)
        if not PatchSecurity.validate_no_network(text):
            violations.append("network_pattern_detected")
        if not PatchSecurity.validate_no_main_mutation(text):
            violations.append("main_mutation_detected")

        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def security_gates() -> Dict[str, bool]:
        return {
            "no_network": True,
            "no_git_push_merge_branch_delete": True,
            "no_freeform_shell": True,
            "no_destructive_mutation_in_v1": True,
            "no_overclaim_actual_application": True,
            "rollback_bundle_required": True,
            "tests_required_before_approval": True,
            "deterministic_receipts": True,
        }
