"""Tests for generated decision report foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_decision_report_foundation import (  # type: ignore[import-not-found]
    DecisionReportReceipt,
    validate_decision_report,
    validate_report_evidence_links,
    validate_report_non_overclaim,
    produce_decision_report_receipt,
)

VALID_PAYLOAD = {
    "decision_id": "DEC-001",
    "action": "HOLD",
    "evidence_links": ["evid-001", "evid-002"],
    "confidence_rationale": {"confidence": 0.85, "claims": ["market_data_consistent", "risk_within_bounds"]},
    "friction_summary": {"summary": "Low spread, high liquidity on NYSE"},
    "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
}


class DecisionReportFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_decision_report(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_decision_report("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_decision_report({})

    def test_validate_rejects_forbidden_action(self):
        p = {**VALID_PAYLOAD, "action": "BUY"}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_rejects_unsupported_action(self):
        p = {**VALID_PAYLOAD, "action": "YOLO_ALL_IN"}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_rejects_missing_decision_id(self):
        p = {**VALID_PAYLOAD, "decision_id": ""}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_evidence_links(self):
        result = validate_report_evidence_links(VALID_PAYLOAD)
        self.assertTrue(result["evidence_links_present"])

    def test_validate_evidence_links_empty(self):
        p = {**VALID_PAYLOAD, "evidence_links": []}
        with self.assertRaises(ValueError):
            validate_report_evidence_links(p)

    def test_validate_non_overclaim(self):
        result = validate_report_non_overclaim(VALID_PAYLOAD)
        self.assertFalse(result["overclaim"])

    def test_validate_overclaim_detected(self):
        p = {**VALID_PAYLOAD, "confidence_rationale": {"confidence": 0.99, "claims": ["c1"]}}
        with self.assertRaises(ValueError):
            validate_report_non_overclaim(p)

    def test_produce_receipt_valid(self):
        receipt = produce_decision_report_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "published")
        self.assertTrue(receipt["no_report_publication"])

    def test_produce_receipt_no_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"reviewed": False, "reviewer_id": ""}}
        receipt = produce_decision_report_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = DecisionReportReceipt(
            receipt_id="rid-1", decision_id="D-1", action="HOLD",
            evidence_links_present=True, confidence_rationale_present=True,
            friction_summary_present=True, human_review_present=True,
            overclaim_detected=False, status="published",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_report_publication)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_decision_report_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_decision_report_receipt(VALID_PAYLOAD)
        result2 = produce_decision_report_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_decision_report_receipt(VALID_PAYLOAD)
        result2 = produce_decision_report_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
