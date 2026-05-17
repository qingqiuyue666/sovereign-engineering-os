"""Tests for generated asset mapping foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_asset_mapping_foundation import (  # type: ignore[import-not-found]
    AssetMappingReceipt,
    validate_asset_mapping_request,
    validate_asset_candidate_contract,
    validate_mapping_confidence_contract,
    produce_asset_mapping_receipt,
)

VALID_PAYLOAD = {
    "candidate_id": "CAND-001",
    "asset_class": "equity",
    "venue": "NYSE",
    "product_id": "AAPL",
    "evidence_refs": ["evid-001", "evid-002"],
    "confidence": 0.85,
    "friction_data": {"spread": 0.01, "liquidity": "high"},
}


class AssetMappingFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_asset_mapping_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_asset_mapping_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_asset_mapping_request({})

    def test_validate_rejects_unsupported_asset_class(self):
        p = {**VALID_PAYLOAD, "asset_class": "magic_beans"}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_rejects_empty_evidence(self):
        p = {**VALID_PAYLOAD, "evidence_refs": []}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_rejects_missing_venue(self):
        p = {**VALID_PAYLOAD, "venue": ""}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_candidate_contract(self):
        result = validate_asset_candidate_contract(VALID_PAYLOAD)
        self.assertTrue(result["candidate_valid"])

    def test_validate_confidence_contract(self):
        result = validate_mapping_confidence_contract(VALID_PAYLOAD)
        self.assertFalse(result["overclaim"])

    def test_validate_confidence_overclaim(self):
        p = {**VALID_PAYLOAD, "confidence": 0.99}
        with self.assertRaises(ValueError):
            validate_mapping_confidence_contract(p)

    def test_produce_receipt_valid(self):
        receipt = produce_asset_mapping_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "mapped")
        self.assertTrue(receipt["no_trading_decision"])

    def test_produce_receipt_rejected_bad_class(self):
        p = {**VALID_PAYLOAD, "asset_class": "magic_beans"}
        with self.assertRaises(ValueError):
            produce_asset_mapping_receipt(p)

    def test_receipt_dataclass(self):
        r = AssetMappingReceipt(
            receipt_id="rid-1", candidate_id="C-1", asset_class="equity",
            venue="NYSE", product_id="AAPL", evidence_present=True,
            confidence=0.85, confidence_overclaim=False,
            friction_data_present=True, status="mapped",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_trading_decision)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_asset_mapping_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
