"""Tests for generated OSINT ingestion foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_osint_ingestion_foundation import (  # type: ignore[import-not-found]
    OsintIngestionReceipt,
    validate_osint_ingestion_request,
    validate_source_tier_contract,
    validate_freshness_contract,
    produce_osint_ingestion_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "source_id": "news-source-rss-001",
    "source_tier": "TIER_1_PRIMARY",
    "timestamp": "2025-01-01T00:00:00Z",
    "evidence_hash": VALID_SHA256,
    "conflict_resolution": "NONE",
}


class OsintIngestionFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_osint_ingestion_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_osint_ingestion_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request({})

    def test_validate_rejects_live_network_source(self):
        p = {**VALID_PAYLOAD, "source_id": "live_scraper"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_validate_rejects_bad_tier(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_99_MAGIC"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_validate_rejects_bad_conflict_resolution(self):
        p = {**VALID_PAYLOAD, "conflict_resolution": "IGNORE_AND_TRADE"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_source_tier_contract_tier1_allows(self):
        result = validate_source_tier_contract(VALID_PAYLOAD)
        self.assertFalse(result["downgraded"])
        self.assertEqual(result["action_required"], "ALLOW")

    def test_source_tier_contract_tier3_downgrades(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_3_TERTIARY"}
        result = validate_source_tier_contract(p)
        self.assertTrue(result["downgraded"])
        self.assertEqual(result["action_required"], "NO_TRADE")

    def test_freshness_contract(self):
        result = validate_freshness_contract(VALID_PAYLOAD)
        self.assertTrue(result["fresh"])

    def test_freshness_contract_missing(self):
        p = {**VALID_PAYLOAD, "timestamp": ""}
        result = validate_freshness_contract(p)
        self.assertFalse(result["fresh"])

    def test_produce_receipt_valid(self):
        receipt = produce_osint_ingestion_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ingested")
        self.assertTrue(receipt["no_ingestion"])

    def test_produce_receipt_tier3_downgraded(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_3_TERTIARY"}
        receipt = produce_osint_ingestion_receipt(p)
        self.assertEqual(receipt["status"], "downgraded")

    def test_receipt_dataclass(self):
        r = OsintIngestionReceipt(
            receipt_id="rid-1", source_id="S-1", source_tier="TIER_1_PRIMARY",
            freshness_timestamp="2025-01-01T00:00:00Z", evidence_hash_present=True,
            conflict_resolution="NONE", status="ingested",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_ingestion)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_osint_ingestion_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
