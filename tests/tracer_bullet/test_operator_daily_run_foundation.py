"""Tests for generated operator daily run foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_operator_daily_run_foundation import (  # type: ignore[import-not-found]
    OperatorDailyRunReceipt,
    validate_operator_daily_run_request,
    validate_operator_run_window,
    validate_operator_review_gate,
    produce_operator_daily_run_receipt,
)

VALID_PAYLOAD = {
    "run_id": "RUN-001",
    "operator_id": "OP-001",
    "runbook_reference": "docs/runbooks/daily_v1.md",
    "evidence_summary": "All checks green, 3 decisions reviewed.",
    "human_review": {"completed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T09:00:00Z"},
    "approval": {"operator_approved": True, "approver_id": "OP-001", "approval_timestamp": "2025-01-01T09:05:00Z"},
    "run_window": {"start": "2025-01-01T08:00:00Z", "end": "2025-01-01T18:00:00Z"},
}


class OperatorDailyRunFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_operator_daily_run_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_operator_daily_run_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request({})

    def test_validate_rejects_incomplete_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"completed": False, "reviewer_id": "OP-001"}}
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request(p)

    def test_validate_rejects_missing_reviewer(self):
        p = {**VALID_PAYLOAD, "human_review": {"completed": True, "reviewer_id": ""}}
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request(p)

    def test_validate_run_window_valid(self):
        result = validate_operator_run_window(VALID_PAYLOAD)
        self.assertTrue(result["run_window_valid"])

    def test_validate_run_window_invalid(self):
        p = {**VALID_PAYLOAD, "run_window": {"start": "2025-01-01T18:00:00Z", "end": "2025-01-01T08:00:00Z"}}
        result = validate_operator_run_window(p)
        self.assertFalse(result["run_window_valid"])

    def test_validate_review_gate_passes(self):
        result = validate_operator_review_gate(VALID_PAYLOAD)
        self.assertTrue(result["approval_gate_passed"])

    def test_validate_review_gate_fails_no_approval(self):
        p = {**VALID_PAYLOAD, "approval": {"operator_approved": False, "approver_id": "", "approval_timestamp": ""}}
        result = validate_operator_review_gate(p)
        self.assertFalse(result["approval_gate_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_execution_performed"])

    def test_receipt_dataclass(self):
        r = OperatorDailyRunReceipt(
            receipt_id="rid-1", run_id="R-1", operator_id="OP-1",
            runbook_reference="x", evidence_summary_present=True,
            human_review_completed=True, approval_gate_passed=True,
            run_window_valid=True, status="approved",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution_performed)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_operator_daily_run_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        result2 = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        result2 = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
