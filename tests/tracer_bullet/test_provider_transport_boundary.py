"""Tests for generated provider transport boundary module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_provider_transport_boundary import (  # type: ignore[import-not-found]
    ProviderTransportReceipt,
    validate_provider_transport_request,
    validate_provider_capability_boundary,
    validate_provider_transport_preflight,
    produce_provider_transport_receipt,
)

VALID_PAYLOAD = {
    "provider_id": "mock-market-data",
    "capability_token": "cap-token-xyz-123",
    "evidence_binding": "evid-binding-001",
    "request_payload": {"symbol": "TEST", "field": "price"},
}


class ProviderTransportBoundaryTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_provider_transport_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_provider_transport_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_provider_transport_request({})

    def test_validate_rejects_live_broker(self):
        p = {**VALID_PAYLOAD, "provider_id": "live-broker"}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_rejects_unknown_provider(self):
        p = {**VALID_PAYLOAD, "provider_id": "mystery-meat-api"}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_rejects_secret_in_payload(self):
        p = {**VALID_PAYLOAD, "request_payload": {"api_key": "sk-123"}}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_capability_boundary(self):
        result = validate_provider_capability_boundary(VALID_PAYLOAD)
        self.assertTrue(result["capability_valid"])

    def test_validate_capability_boundary_missing_token(self):
        p = {**VALID_PAYLOAD, "capability_token": ""}
        result = validate_provider_capability_boundary(p)
        self.assertFalse(result["capability_valid"])

    def test_validate_preflight_passes(self):
        result = validate_provider_transport_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_validate_preflight_fails_no_evidence(self):
        p = {**VALID_PAYLOAD, "evidence_binding": ""}
        result = validate_provider_transport_preflight(p)
        self.assertFalse(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_provider_transport_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "gated")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_provider_call"])

    def test_receipt_dataclass(self):
        r = ProviderTransportReceipt(
            receipt_id="rid-1", provider_id="mock-market-data",
            capability_token="tok", evidence_binding_present=True,
            status="gated", boundary_valid=True, preflight_passed=True,
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_provider_call)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_provider_transport_boundary.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
