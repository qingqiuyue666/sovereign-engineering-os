"""Tests for generated alert delivery foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_alert_delivery_foundation import (  # type: ignore[import-not-found]
    AlertDeliveryReceipt,
    validate_alert_delivery_request,
    validate_alert_channel_policy,
    validate_alert_payload_contract,
    produce_alert_delivery_receipt,
)

VALID_PAYLOAD = {
    "alert_id": "ALERT-001",
    "channel": "log",
    "alert_payload": {"severity": "high", "message": "Disk usage > 90%", "timestamp": "2025-01-01T00:00:00Z"},
    "operator_acknowledgement": {"acknowledged": True, "operator_id": "OP-001"},
    "evidence_reference": "evid-ref-001",
}


class AlertDeliveryFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_alert_delivery_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_alert_delivery_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_alert_delivery_request({})

    def test_validate_rejects_telegram(self):
        p = {**VALID_PAYLOAD, "channel": "telegram"}
        with self.assertRaises(ValueError):
            validate_alert_delivery_request(p)

    def test_validate_rejects_webhook(self):
        p = {**VALID_PAYLOAD, "channel": "webhook"}
        with self.assertRaises(ValueError):
            validate_alert_delivery_request(p)

    def test_validate_rejects_secret_in_payload(self):
        p = {**VALID_PAYLOAD, "alert_payload": {"severity": "high", "api_key": "sk-secret"}}
        with self.assertRaises(ValueError):
            validate_alert_delivery_request(p)

    def test_validate_channel_policy(self):
        result = validate_alert_channel_policy(VALID_PAYLOAD)
        self.assertTrue(result["channel_allowed"])

    def test_validate_channel_policy_forbidden(self):
        p = {**VALID_PAYLOAD, "channel": "telegram"}
        result = validate_alert_channel_policy(p)
        self.assertTrue(result["channel_forbidden"])

    def test_validate_payload_contract(self):
        result = validate_alert_payload_contract(VALID_PAYLOAD)
        self.assertTrue(result["payload_valid"])

    def test_validate_payload_contract_missing_severity(self):
        p = {**VALID_PAYLOAD, "alert_payload": {"message": "test", "timestamp": "t"}}
        result = validate_alert_payload_contract(p)
        self.assertFalse(result["payload_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_alert_delivery_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "queued")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_message_sent"])

    def test_produce_receipt_no_ack(self):
        p = {**VALID_PAYLOAD, "operator_acknowledgement": {"acknowledged": False}}
        receipt = produce_alert_delivery_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = AlertDeliveryReceipt(
            receipt_id="rid-1", alert_id="A-1", channel="log",
            operator_acknowledged=True, evidence_reference_present=True,
            channel_valid=True, payload_valid=True, status="queued",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_message_sent)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_alert_delivery_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
