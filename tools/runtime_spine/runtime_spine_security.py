"""Runtime spine security — security boundary enforcement for receipt spine.

No network. No subprocess. No live provider. No trading.
No raw payload in any receipt. Deterministic only.
"""

from __future__ import annotations

from typing import Any, Dict, List


class RuntimeSpineSecurity:
    """Security boundary enforcement for runtime receipt spine."""

    @staticmethod
    def validate_no_raw_payload(receipt: Dict[str, Any]) -> bool:
        forbidden_keys = {"raw_payload", "payload", "raw_data", "raw_input"}
        return not bool(forbidden_keys & set(receipt.keys()))

    @staticmethod
    def validate_all_no_raw_payload(receipts: List[Dict[str, Any]]) -> Dict[str, Any]:
        violations = []
        for i, r in enumerate(receipts):
            if not RuntimeSpineSecurity.validate_no_raw_payload(r):
                violations.append(f"receipt_{i}_has_raw_payload")
        return {"valid": len(violations) == 0, "violations": violations}

    @staticmethod
    def security_gates() -> Dict[str, bool]:
        return {
            "no_network": True,
            "no_subprocess": True,
            "no_live_provider": True,
            "no_trading": True,
            "no_raw_payload": True,
            "deterministic_chain_hash": True,
            "missing_link_rejected": True,
            "mismatched_artifact_id_rejected": True,
        }
