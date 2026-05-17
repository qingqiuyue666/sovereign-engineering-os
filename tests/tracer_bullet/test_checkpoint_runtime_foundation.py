"""Tests for generated checkpoint runtime foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_checkpoint_runtime_foundation import (  # type: ignore[import-not-found]
    CheckpointRuntimeReceipt,
    validate_checkpoint_request,
    validate_checkpoint_scope,
    validate_checkpoint_integrity_contract,
    produce_checkpoint_runtime_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "checkpoint_id": "CKPT-001",
    "scope": {"paths": ["src/", "config/"], "module": "core"},
    "content_hash": VALID_SHA256,
    "source_revision": "abc123def456",
    "rollback_reference": "rollback-plan-001",
    "state_status": {"dirty": False, "approved": True},
    "approval": {"approved": True, "approver_id": "OP-001"},
}


class CheckpointRuntimeFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_checkpoint_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_checkpoint_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_checkpoint_request({})

    def test_validate_rejects_missing_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_rejects_missing_source_revision(self):
        p = {**VALID_PAYLOAD, "source_revision": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_rejects_missing_rollback(self):
        p = {**VALID_PAYLOAD, "rollback_reference": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_scope(self):
        result = validate_checkpoint_scope(VALID_PAYLOAD)
        self.assertTrue(result["scope_valid"])

    def test_validate_scope_empty_paths(self):
        p = {**VALID_PAYLOAD, "scope": {"paths": [], "module": "core"}}
        result = validate_checkpoint_scope(p)
        self.assertFalse(result["scope_valid"])

    def test_validate_integrity(self):
        result = validate_checkpoint_integrity_contract(VALID_PAYLOAD)
        self.assertTrue(result["integrity_valid"])

    def test_validate_integrity_bad_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": "short"}
        result = validate_checkpoint_integrity_contract(p)
        self.assertFalse(result["integrity_valid"])

    def test_produce_receipt_dirty_unapproved_rejected(self):
        p = {**VALID_PAYLOAD, "state_status": {"dirty": True, "approved": False}}
        with self.assertRaises(ValueError):
            produce_checkpoint_runtime_receipt(p)

    def test_produce_receipt_valid(self):
        receipt = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "created")
        self.assertTrue(receipt["no_checkpoint_mutation"])

    def test_receipt_dataclass(self):
        r = CheckpointRuntimeReceipt(
            receipt_id="rid-1", checkpoint_id="C-1", source_revision="abc",
            content_hash=VALID_SHA256, rollback_reference="rr-1",
            scope_valid=True, integrity_valid=True, state_clean=True,
            status="created", created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_checkpoint_mutation)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_checkpoint_runtime_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)



    def test_produce_receipt_is_deterministic_same_receipt_id(self):
        result1 = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        result2 = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["receipt_id"], result2["receipt_id"],
                         "receipt_id must be deterministic — same payload = same receipt_id")

    def test_produce_receipt_is_deterministic_same_created_at(self):
        result1 = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        result2 = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        self.assertEqual(result1["created_at"], result2["created_at"],
                         "created_at must be deterministic — same payload = same created_at")

if __name__ == "__main__":
    unittest.main()
