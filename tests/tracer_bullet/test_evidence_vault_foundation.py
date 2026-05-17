"""Tests for generated evidence vault foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_evidence_vault_foundation import (  # type: ignore[import-not-found]
    EvidenceVaultReceipt,
    validate_evidence_vault_record,
    validate_evidence_hash_contract,
    validate_evidence_append_only_contract,
    validate_evidence_metadata_contract,
    produce_evidence_vault_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "artifact_id": "ART-001",
    "artifact_type": "run_log",
    "content_hash": VALID_SHA256,
    "hash_algorithm": "sha256",
    "created_at": "2025-01-01T00:00:00Z",
    "producer": "test-runner",
    "lineage": ["run-001", "stage-002"],
    "immutable": True,
    "append_only": True,
}


class EvidenceVaultFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_evidence_vault_record(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_evidence_vault_record("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_evidence_vault_record({})

    def test_validate_rejects_secret_artifact_type(self):
        p = {**VALID_PAYLOAD, "artifact_type": "api_key"}
        with self.assertRaises(ValueError):
            validate_evidence_vault_record(p)

    def test_validate_rejects_non_list_lineage(self):
        p = {**VALID_PAYLOAD, "lineage": "not-a-list"}
        with self.assertRaises(TypeError):
            validate_evidence_vault_record(p)

    def test_validate_hash_contract_valid_sha256(self):
        result = validate_evidence_hash_contract(VALID_PAYLOAD)
        self.assertTrue(result["hash_valid"])

    def test_validate_hash_contract_invalid_algo(self):
        p = {**VALID_PAYLOAD, "hash_algorithm": "md5"}
        with self.assertRaises(ValueError):
            validate_evidence_hash_contract(p)

    def test_validate_hash_contract_bad_hash_length(self):
        p = {**VALID_PAYLOAD, "content_hash": "too-short"}
        result = validate_evidence_hash_contract(p)
        self.assertFalse(result["hash_valid"])

    def test_validate_append_only_rejects_false(self):
        p = {**VALID_PAYLOAD, "append_only": False}
        with self.assertRaises(ValueError):
            validate_evidence_append_only_contract(p)

    def test_validate_metadata_contract(self):
        result = validate_evidence_metadata_contract(VALID_PAYLOAD)
        self.assertTrue(result["metadata_valid"])

    def test_validate_metadata_contract_empty_lineage(self):
        p = {**VALID_PAYLOAD, "lineage": []}
        result = validate_evidence_metadata_contract(p)
        self.assertFalse(result["metadata_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_evidence_vault_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "sealed")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_vault_write"])
        self.assertTrue(receipt["append_only_enforced"])

    def test_produce_receipt_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            produce_evidence_vault_receipt({"artifact_id": "only-id"})

    def test_receipt_dataclass(self):
        r = EvidenceVaultReceipt(
            receipt_id="rid-1", artifact_id="A-1", artifact_type="log",
            content_hash=VALID_SHA256, hash_algorithm="sha256", status="sealed",
            hash_valid=True, append_only_enforced=True, immutable_enforced=True,
            metadata_valid=True, created_at="2025-01-01T00:00:00Z",
            producer="test", lineage=["l1"],
        )
        self.assertTrue(r.no_vault_write)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_evidence_vault_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
