"""Tests for generated run ledger hardening foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_run_ledger_hardening_foundation import (  # type: ignore[import-not-found]
    RunLedgerReceipt,
    validate_run_ledger_entry,
    validate_run_sequence_contract,
    validate_run_status_contract,
    produce_run_ledger_receipt,
)

VALID_PAYLOAD = {
    "run_id": "RUN-001",
    "operator_id": "OP-001",
    "status": "running",
    "previous_status": "pending",
    "sequence_number": 5,
    "evidence_link": "evid-link-001",
    "mutable_ledger": False,
}


class RunLedgerHardeningFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_run_ledger_entry(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_run_ledger_entry("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_run_ledger_entry({})

    def test_validate_rejects_missing_run_id(self):
        p = {**VALID_PAYLOAD, "run_id": ""}
        with self.assertRaises(ValueError):
            validate_run_ledger_entry(p)

    def test_validate_rejects_invalid_status(self):
        p = {**VALID_PAYLOAD, "status": "magic_status"}
        with self.assertRaises(ValueError):
            validate_run_ledger_entry(p)

    def test_validate_sequence_contract(self):
        result = validate_run_sequence_contract(VALID_PAYLOAD)
        self.assertTrue(result["sequence_valid"])

    def test_validate_sequence_zero(self):
        p = {**VALID_PAYLOAD, "sequence_number": 0}
        result = validate_run_sequence_contract(p)
        self.assertFalse(result["sequence_valid"])

    def test_validate_transition_valid(self):
        result = validate_run_status_contract(VALID_PAYLOAD)
        self.assertTrue(result["transition_valid"])

    def test_validate_transition_invalid(self):
        p = {**VALID_PAYLOAD, "status": "pending", "previous_status": "completed"}
        result = validate_run_status_contract(p)
        self.assertFalse(result["transition_valid"])

    def test_validate_transition_completed_to_running_invalid(self):
        p = {**VALID_PAYLOAD, "status": "running", "previous_status": "completed"}
        result = validate_run_status_contract(p)
        self.assertFalse(result["transition_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_run_ledger_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "running")
        self.assertTrue(receipt["transition_valid"])
        self.assertTrue(receipt["no_ledger_write"])

    def test_produce_receipt_rejects_mutable(self):
        p = {**VALID_PAYLOAD, "mutable_ledger": True}
        with self.assertRaises(ValueError):
            produce_run_ledger_receipt(p)

    def test_receipt_dataclass(self):
        r = RunLedgerReceipt(
            receipt_id="rid-1", run_id="R-1", operator_id="OP-1",
            status="running", previous_status="pending",
            transition_valid=True, sequence_valid=True,
            evidence_link_present=True, mutable_claim=False,
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_ledger_write)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_run_ledger_hardening_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_run_ledger_receipt(VALID_PAYLOAD)
        result2 = produce_run_ledger_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_run_ledger_receipt(VALID_PAYLOAD)
        result2 = produce_run_ledger_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
