"""Runtime receipt validator — validates compatibility between adjacent receipt types.

The validator checks explicit chain linkage, not just field presence.
Raw payload fields are rejected in every receipt.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


RAW_PAYLOAD_KEYS = {"raw_payload", "raw_data", "payload", "content"}


class RuntimeReceiptValidator:
    """Validates compatibility between adjacent runtime receipt types."""

    @staticmethod
    def _raw_payload_issues(*receipts: Dict[str, Any]) -> List[str]:
        issues: List[str] = []
        for idx, receipt in enumerate(receipts):
            for key in RAW_PAYLOAD_KEYS:
                if key in receipt:
                    issues.append(f"raw_payload_detected:{idx}:{key}")
        return issues

    @staticmethod
    def _missing(receipt: Dict[str, Any], required: set[str], label: str) -> List[str]:
        missing = required - set(receipt.keys())
        return [f"{label}_missing_fields: {sorted(missing)}"] if missing else []

    @staticmethod
    def validate_evidence_to_replay(
        evidence_receipt: Dict[str, Any],
        replay_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        issues.extend(RuntimeReceiptValidator._raw_payload_issues(evidence_receipt, replay_receipt))
        issues.extend(RuntimeReceiptValidator._missing(
            evidence_receipt, {"artifact_id", "content_hash", "hash_algorithm"}, "evidence"
        ))
        issues.extend(RuntimeReceiptValidator._missing(
            replay_receipt, {"receipt_id", "anchor_id", "canonical_hash"}, "replay"
        ))

        artifact_id = evidence_receipt.get("artifact_id")
        replay_ids = replay_receipt.get("evidence_artifact_ids", [])
        if artifact_id and artifact_id not in replay_ids:
            issues.append("evidence_artifact_id_not_linked_to_replay")
        if not replay_receipt.get("evidence_binding_hash"):
            issues.append("replay_missing_evidence_binding_hash")
        if replay_receipt.get("evidence_binding_valid") is not True:
            issues.append("replay_evidence_binding_not_valid")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{evidence_receipt.get('artifact_id','')}|{evidence_receipt.get('content_hash','')}|{replay_receipt.get('canonical_hash','')}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_replay_to_patch(
        replay_receipt: Dict[str, Any],
        patch_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        issues.extend(RuntimeReceiptValidator._raw_payload_issues(replay_receipt, patch_receipt))
        issues.extend(RuntimeReceiptValidator._missing(
            replay_receipt, {"receipt_id", "anchor_id", "canonical_hash"}, "replay"
        ))
        issues.extend(RuntimeReceiptValidator._missing(
            patch_receipt, {"receipt_id", "request_id", "canonical_hash"}, "patch"
        ))

        replay_hash = replay_receipt.get("canonical_hash")
        patch_replay_hash = patch_receipt.get("replay_receipt_hash")
        if patch_replay_hash is not None and patch_replay_hash != replay_hash:
            issues.append("patch_replay_receipt_hash_mismatch")
        if patch_replay_hash is None:
            issues.append("patch_missing_replay_receipt_hash")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{replay_receipt.get('canonical_hash','')}|{patch_receipt.get('canonical_hash','')}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_patch_to_execution(
        patch_receipt: Dict[str, Any],
        execution_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        issues.extend(RuntimeReceiptValidator._raw_payload_issues(patch_receipt, execution_receipt))
        issues.extend(RuntimeReceiptValidator._missing(
            patch_receipt, {"receipt_id", "request_id", "canonical_hash"}, "patch"
        ))
        issues.extend(RuntimeReceiptValidator._missing(
            execution_receipt, {"receipt_id", "execution_id", "canonical_hash"}, "execution"
        ))

        patch_hash = patch_receipt.get("canonical_hash")
        exec_patch_hash = execution_receipt.get("patch_receipt_hash")
        if exec_patch_hash is not None and exec_patch_hash != patch_hash:
            issues.append("execution_patch_receipt_hash_mismatch")
        if exec_patch_hash is None:
            issues.append("execution_missing_patch_receipt_hash")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{patch_receipt.get('canonical_hash','')}|{execution_receipt.get('canonical_hash','')}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def validate_execution_to_operator(
        execution_receipt: Dict[str, Any],
        operator_receipt: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        issues.extend(RuntimeReceiptValidator._raw_payload_issues(execution_receipt, operator_receipt))
        issues.extend(RuntimeReceiptValidator._missing(
            execution_receipt, {"receipt_id", "execution_id", "canonical_hash"}, "execution"
        ))
        issues.extend(RuntimeReceiptValidator._missing(
            operator_receipt, {"receipt_id", "run_id", "canonical_hash"}, "operator"
        ))

        execution_hash = execution_receipt.get("canonical_hash")
        op_exec_hashes = operator_receipt.get("execution_receipt_hashes", [])
        if execution_hash and execution_hash not in op_exec_hashes:
            issues.append("operator_missing_execution_receipt_link")

        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "pair_hash": hashlib.sha256(
                f"{execution_receipt.get('canonical_hash','')}|{operator_receipt.get('canonical_hash','')}".encode()
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
