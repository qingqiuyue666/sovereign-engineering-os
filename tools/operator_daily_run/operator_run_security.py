"""Operator run security — security boundary enforcement for operator daily runs.

No autonomous production action. No trading. No network.
No secrets. No env reads. Human review and approval required.
"""

from __future__ import annotations

from typing import Any, Dict, List


FORBIDDEN_ACTIONS = frozenset({
    "production", "trading", "network", "autonomous",
    "deploy", "push", "merge", "branch_delete",
})


class OperatorRunSecurity:
    """Security boundary enforcement for operator daily run runtime."""

    @staticmethod
    def validate_action_plan(action_plan: str) -> Dict[str, Any]:
        if not action_plan or not action_plan.strip():
            return {"valid": False, "reason": "action_plan_required"}

        violations: List[str] = []
        plan_lower = action_plan.lower()

        if "production" in plan_lower:
            violations.append("production_action_rejected")
        if "trading" in plan_lower:
            violations.append("trading_action_rejected")
        if any(p in plan_lower for p in ("curl", "wget", "ssh", "scp", "http://", "https://")):
            violations.append("network_action_rejected")
        if any(p in plan_lower for p in (".env", "api_key", "secret", "token", "password")):
            violations.append("secret_material_rejected")
        if "autonomous" in plan_lower:
            violations.append("autonomous_action_rejected")
        if "deploy" in plan_lower and "production" in plan_lower:
            violations.append("production_deploy_rejected")

        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def validate_no_network(text: str) -> bool:
        text_lower = text.lower()
        return not any(p in text_lower for p in ("curl", "wget", "ssh", "scp ", "http://", "https://"))

    @staticmethod
    def validate_no_trading(text: str) -> bool:
        return "trading" not in text.lower()

    @staticmethod
    def validate_no_production(text: str) -> bool:
        return "production" not in text.lower()

    @staticmethod
    def security_gates() -> Dict[str, bool]:
        return {
            "no_autonomous_production_action": True,
            "no_trading": True,
            "no_network": True,
            "human_review_required": True,
            "approval_required": True,
            "single_operator_action_plan": True,
            "deterministic_receipts": True,
        }
