"""Tests for generated recovery rollback foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_recovery_rollback_foundation import (  # type: ignore[import-not-found]
    RecoveryRollbackReceipt,
    validate_recovery_request,
    validate_rollback_plan,
    validate_failure_bundle_contract,
    produce_recovery_rollback_receipt,
)

VALID_PAYLOAD = {
    "recovery_id": "REC-001",
    "rollback_target": "checkpoint-20250101",
    "failure_evidence": {"error_message": "NullPointer in OrderService", "failure_timestamp": "2025-01-01T00:00:00Z", "component": "OrderService"},
    "rollback_plan": {"target": "checkpoint-20250101", "steps": ["stop_service", "restore_checkpoint", "verify_health", "resume"], "verification": "health_check.py", "reversible": True},
    "approval": {"approved": True, "approver_id": "OP-001", "approved_at": "2025-01-01T00:05:00Z"},
    "operation_type": "ROLLBACK",
}


class RecoveryRollbackFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_recovery_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_recovery_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_recovery_request({})

    def test_validate_rejects_irreversible(self):
        p = {**VALID_PAYLOAD, "operation_type": "DROP_TABLE"}
        with self.assertRaises(ValueError):
            validate_recovery_request(p)

    def test_validate_rejects_empty_target(self):
        p = {**VALID_PAYLOAD, "rollback_target": ""}
        with self.assertRaises(ValueError):
            validate_recovery_request(p)

    def test_validate_rollback_plan_valid(self):
        result = validate_rollback_plan(VALID_PAYLOAD)
        self.assertTrue(result["rollback_plan_valid"])
        self.assertTrue(result["is_reversible"])

    def test_validate_rollback_plan_irreversible(self):
        p = {**VALID_PAYLOAD, "rollback_plan": {**VALID_PAYLOAD["rollback_plan"], "reversible": False}}
        result = validate_rollback_plan(p)
        self.assertFalse(result["is_reversible"])

    def test_validate_rollback_plan_missing_steps(self):
        p = {**VALID_PAYLOAD, "rollback_plan": {"target": "x", "steps": [], "verification": "v", "reversible": True}}
        result = validate_rollback_plan(p)
        self.assertFalse(result["rollback_plan_valid"])

    def test_validate_failure_bundle(self):
        result = validate_failure_bundle_contract(VALID_PAYLOAD)
        self.assertTrue(result["failure_bundle_valid"])

    def test_validate_failure_bundle_incomplete(self):
        p = {**VALID_PAYLOAD, "failure_evidence": {"error_message": "err"}}
        result = validate_failure_bundle_contract(p)
        self.assertFalse(result["failure_bundle_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertTrue(receipt["no_mutation"])

    def test_produce_receipt_no_approval(self):
        p = {**VALID_PAYLOAD, "approval": {"approved": False, "approver_id": ""}}
        receipt = produce_recovery_rollback_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = RecoveryRollbackReceipt(
            receipt_id="rid-1", recovery_id="R-1", rollback_target="c1",
            failure_evidence_present=True, rollback_plan_valid=True,
            is_reversible=True, approval_gate_passed=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_mutation)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_recovery_rollback_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        result2 = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        result2 = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
