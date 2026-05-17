"""Tests for generated decision engine foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_decision_engine_foundation import (  # type: ignore[import-not-found]
    DecisionEngineReceipt,
    validate_decision_request,
    validate_single_action_contract,
    validate_confidence_gate,
    validate_friction_gate,
    produce_decision_engine_receipt,
)

VALID_PAYLOAD = {
    "decision_id": "DEC-001",
    "actions": ["HOLD"],
    "confidence": 0.85,
    "friction_data": {"spread": 0.01, "venue": "NYSE"},
    "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
    "evidence_refs": ["evid-001"],
}


class DecisionEngineFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_decision_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_decision_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_decision_request({})

    def test_validate_rejects_empty_actions(self):
        p = {**VALID_PAYLOAD, "actions": []}
        with self.assertRaises(ValueError):
            validate_decision_request(p)

    def test_validate_single_action_rejects_multiple(self):
        p = {**VALID_PAYLOAD, "actions": ["HOLD", "FLAG"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_single_action_rejects_buy(self):
        p = {**VALID_PAYLOAD, "actions": ["BUY"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_single_action_rejects_trade(self):
        p = {**VALID_PAYLOAD, "actions": ["TRADE"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_confidence_gate_passes(self):
        result = validate_confidence_gate(VALID_PAYLOAD)
        self.assertTrue(result["gate_passed"])

    def test_validate_confidence_gate_below_threshold(self):
        p = {**VALID_PAYLOAD, "confidence": 0.50}
        result = validate_confidence_gate(p)
        self.assertFalse(result["gate_passed"])

    def test_validate_confidence_overclaim(self):
        p = {**VALID_PAYLOAD, "confidence": 0.99}
        with self.assertRaises(ValueError):
            validate_confidence_gate(p)

    def test_validate_friction_gate_passes(self):
        result = validate_friction_gate(VALID_PAYLOAD)
        self.assertTrue(result["friction_gate_passed"])

    def test_validate_friction_gate_missing_venue(self):
        p = {**VALID_PAYLOAD, "friction_data": {"spread": 0.01}}
        result = validate_friction_gate(p)
        self.assertFalse(result["friction_gate_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_decision_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertTrue(receipt["no_execution"])

    def test_produce_receipt_no_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"reviewed": False, "reviewer_id": ""}}
        receipt = produce_decision_engine_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = DecisionEngineReceipt(
            receipt_id="rid-1", decision_id="D-1", action="HOLD",
            confidence=0.85, confidence_gate_passed=True,
            friction_gate_passed=True, single_action_enforced=True,
            human_review_present=True, status="approved",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_decision_engine_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_decision_engine_receipt(VALID_PAYLOAD)
        result2 = produce_decision_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_decision_engine_receipt(VALID_PAYLOAD)
        result2 = produce_decision_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
