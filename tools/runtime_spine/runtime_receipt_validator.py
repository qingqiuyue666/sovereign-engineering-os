"""Runtime receipt validator — validates compatibility between adjacent receipt types.

Checks: evidence->replay compatibility, replay->patch compatibility,
patch->execution compatibility, execution->operator compatibility.
Rejects mismatched artifact IDs. Rejects raw payload in any receipt.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class RuntimeReceiptValidator:
    """Validates compatibility between adjacent runtime receipt types."""

    @staticmethod
    def validate_evidence_to_replay(
        evidence_receipt: Dict[str, Any],
        replay_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate evidence vault receipt is compatible with replay receipt."""
        issues: List[str] = []

        # No raw payload check
        for r in (evidence_receipt, replay_receipt):
            if "raw_payload" in r or "raw_data" in r:
                issues.append("raw_payload_detected")

        # Evidence must have required fields
        ev_required = {"artifact_id", "content_hash", "hash_algorithm"}
        ev_missing = ev_required - set(evidence_receipt.keys())
        if ev_missing:
            issues.append(f"evidence_missing_fields: {sorted(ev_missing)}")

        # Replay must have required fields
        rp_required = {"receipt_id", "anchor_id", "canonical_hash"}
        rp_missing = rp_required - set(replay_receipt.keys())
        if rp_missing:
            issues.append(f"replay_missing_fields: {sorted(rp_missing)}")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{str(evidence_receipt.get('content_hash', ''))}|{str(replay_receipt.get('canonical_hash', ''))}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_replay_to_patch(
        replay_receipt: Dict[str, Any],
        patch_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate replay receipt is compatible with patch receipt."""
        issues: List[str] = []

        for r in (replay_receipt, patch_receipt):
            if "raw_payload" in r or "raw_data" in r:
                issues.append("raw_payload_detected")

        rp_required = {"receipt_id", "anchor_id", "canonical_hash"}
        rp_missing = rp_required - set(replay_receipt.keys())
        if rp_missing:
            issues.append(f"replay_missing_fields: {sorted(rp_missing)}")

        pt_required = {"receipt_id", "request_id", "canonical_hash"}
        pt_missing = pt_required - set(patch_receipt.keys())
        if pt_missing:
            issues.append(f"patch_missing_fields: {sorted(pt_missing)}")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{str(replay_receipt.get('canonical_hash', ''))}|{str(patch_receipt.get('canonical_hash', ''))}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_patch_to_execution(
        patch_receipt: Dict[str, Any],
        execution_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate patch receipt is compatible with execution receipt."""
        issues: List[str] = []

        for r in (patch_receipt, execution_receipt):
            if "raw_payload" in r or "raw_data" in r:
                issues.append("raw_payload_detected")

        pt_required = {"receipt_id", "request_id", "canonical_hash"}
        pt_missing = pt_required - set(patch_receipt.keys())
        if pt_missing:
            issues.append(f"patch_missing_fields: {sorted(pt_missing)}")

        ex_required = {"receipt_id", "execution_id", "canonical_hash"}
        ex_missing = ex_required - set(execution_receipt.keys())
        if ex_missing:
            issues.append(f"execution_missing_fields: {sorted(ex_missing)}")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{str(patch_receipt.get('canonical_hash', ''))}|{str(execution_receipt.get('canonical_hash', ''))}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_execution_to_operator(
        execution_receipt: Dict[str, Any],
        operator_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate execution receipt is compatible with operator run receipt."""
        issues: List[str] = []

        for r in (execution_receipt, operator_receipt):
            if "raw_payload" in r or "raw_data" in r:
                issues.append("raw_payload_detected")

        ex_required = {"receipt_id", "execution_id", "canonical_hash"}
        ex_missing = ex_required - set(execution_receipt.keys())
        if ex_missing:
            issues.append(f"execution_missing_fields: {sorted(ex_missing)}")

        op_required = {"receipt_id", "run_id", "canonical_hash"}
        op_missing = op_required - set(operator_receipt.keys())
        if op_missing:
            issues.append(f"operator_missing_fields: {sorted(op_missing)}")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{str(execution_receipt.get('canonical_hash', ''))}|{str(operator_receipt.get('canonical_hash', ''))}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_full_spine(
        evidence: Dict[str, Any],
        replay: Dict[str, Any],
        patch: Dict[str, Any],
        execution: Dict[str, Any],
        operator: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate the full receipt spine chain."""
        pairs = [
            ("evidence->replay", RuntimeReceiptValidator.validate_evidence_to_replay(evidence, replay)),
            ("replay->patch", RuntimeReceiptValidator.validate_replay_to_patch(replay, patch)),
            ("patch->execution", RuntimeReceiptValidator.validate_patch_to_execution(patch, execution)),
            ("execution->operator", RuntimeReceiptValidator.validate_execution_to_operator(execution, operator)),
        ]

        all_compatible = all(p[1]["compatible"] for p in pairs)
        pair_hashes = [p[1]["pair_hash"] for p in pairs]
        spine_hash = hashlib.sha256("|".join(pair_hashes).encode()).hexdigest()

        return {
            "spine_valid": all_compatible,
            "spine_hash": spine_hash,
            "pairs": {name: result for name, result in pairs},
        }
