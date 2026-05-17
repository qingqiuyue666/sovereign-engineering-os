"""Tests for generated evidence index foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_evidence_index_foundation import (  # type: ignore[import-not-found]
    EvidenceIndexReceipt,
    validate_evidence_index_entry,
    validate_evidence_lookup_contract,
    validate_index_consistency_contract,
    produce_evidence_index_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "artifact_id": "ART-001",
    "content_hash": VALID_SHA256,
    "index_key": "idx-run-001-stage-002",
    "conflict_policy": "KEEP_NEWEST",
    "is_duplicate": False,
}


class EvidenceIndexFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_evidence_index_entry(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_evidence_index_entry("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_evidence_index_entry({})

    def test_validate_rejects_missing_artifact_id(self):
        p = {**VALID_PAYLOAD, "artifact_id": ""}
        with self.assertRaises(ValueError):
            validate_evidence_index_entry(p)

    def test_validate_rejects_bad_conflict_policy(self):
        p = {**VALID_PAYLOAD, "conflict_policy": "SILENT_OVERWRITE"}
        with self.assertRaises(ValueError):
            validate_evidence_index_entry(p)

    def test_validate_lookup_contract(self):
        result = validate_evidence_lookup_contract(VALID_PAYLOAD)
        self.assertTrue(result["lookup_valid"])

    def test_validate_lookup_contract_bad_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": "short"}
        result = validate_evidence_lookup_contract(p)
        self.assertFalse(result["lookup_valid"])

    def test_validate_consistency_duplicate_reject(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "REJECT_DUPLICATE"}
        with self.assertRaises(ValueError):
            validate_index_consistency_contract(p)

    def test_validate_consistency_duplicate_keep_newest(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "KEEP_NEWEST"}
        result = validate_index_consistency_contract(p)
        self.assertTrue(result["is_duplicate"])

    def test_produce_receipt_valid(self):
        receipt = produce_evidence_index_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "indexed")
        self.assertTrue(receipt["no_vault_write"])

    def test_produce_receipt_duplicate_rejected(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "REJECT_DUPLICATE"}
        with self.assertRaises(ValueError):
            produce_evidence_index_receipt(p)

    def test_receipt_dataclass(self):
        r = EvidenceIndexReceipt(
            receipt_id="rid-1", artifact_id="A-1", content_hash=VALID_SHA256,
            index_key="ik-1", conflict_policy="KEEP_NEWEST",
            lookup_valid=True, consistency_valid=True,
            is_duplicate=False, status="indexed",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_vault_write)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_evidence_index_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
