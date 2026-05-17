"""Tests for generated replay engine foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_replay_engine_foundation import (  # type: ignore[import-not-found]
    ReplayEngineReceipt,
    validate_replay_request,
    validate_replay_anchor_contract,
    validate_replay_input_snapshot_contract,
    validate_replay_version_tuple,
    produce_replay_engine_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "replay_anchor_id": "ANCHOR-001",
    "input_snapshot_hash": VALID_SHA256,
    "policy_version": "v1.0.0",
    "code_version": "abc123def456",
    "environment_fingerprint": "env-hash-001",
    "deterministic_mode": True,
    "no_cloud_requery": True,
}


class ReplayEngineFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_replay_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_replay_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_replay_request({})

    def test_validate_rejects_cloud_requery_false(self):
        p = {**VALID_PAYLOAD, "no_cloud_requery": False}
        with self.assertRaises(ValueError):
            validate_replay_request(p)

    def test_validate_anchor_contract(self):
        result = validate_replay_anchor_contract(VALID_PAYLOAD)
        self.assertTrue(result["anchor_valid"])

    def test_validate_anchor_contract_empty(self):
        p = {**VALID_PAYLOAD, "replay_anchor_id": ""}
        result = validate_replay_anchor_contract(p)
        self.assertFalse(result["anchor_valid"])

    def test_validate_snapshot_contract(self):
        result = validate_replay_input_snapshot_contract(VALID_PAYLOAD)
        self.assertTrue(result["snapshot_valid"])

    def test_validate_snapshot_contract_bad_length(self):
        p = {**VALID_PAYLOAD, "input_snapshot_hash": "too-short"}
        with self.assertRaises(ValueError):
            validate_replay_input_snapshot_contract(p)

    def test_validate_version_tuple(self):
        result = validate_replay_version_tuple(VALID_PAYLOAD)
        self.assertTrue(result["version_tuple_valid"])

    def test_validate_version_tuple_missing(self):
        p = {**VALID_PAYLOAD, "policy_version": ""}
        result = validate_replay_version_tuple(p)
        self.assertFalse(result["version_tuple_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_replay_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_replay_execution"])

    def test_produce_receipt_rejects_missing(self):
        with self.assertRaises(ValueError):
            produce_replay_engine_receipt({"replay_anchor_id": "only-id"})

    def test_receipt_dataclass(self):
        r = ReplayEngineReceipt(
            receipt_id="rid-1", replay_anchor_id="A-1", input_snapshot_hash=VALID_SHA256,
            policy_version="v1", code_version="abc", environment_fingerprint="env",
            deterministic_mode=True, no_cloud_requery=True, anchor_valid=True,
            snapshot_valid=True, version_tuple_valid=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_replay_execution)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_replay_engine_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
