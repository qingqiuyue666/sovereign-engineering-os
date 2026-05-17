#!/usr/bin/env python3
"""Generate bounded local-only alert delivery foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_CHANNELS = frozenset({"log", "console", "dashboard", "queue"})
FORBIDDEN_CHANNELS = frozenset({"telegram", "slack", "email", "sms", "webhook", "http", "push"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_alert_delivery_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/alert_delivery_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/alert_delivery_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/alert_delivery_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_alert_delivery_foundation.py"

ALLOWED_OUTPUTS = {OUTPUT_MODULE, OUTPUT_REGISTRY, OUTPUT_POLICY, OUTPUT_RUNBOOK, OUTPUT_TEST}


def assert_allowed(path: Path) -> None:
    resolved = path.resolve()
    allowed = {item.resolve() for item in ALLOWED_OUTPUTS}
    if resolved not in allowed:
        raise RuntimeError(f"write_path_not_allowlisted: {path}")


def write(path: Path, text: str) -> None:
    assert_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    write(OUTPUT_MODULE, _MODULE)
    write(OUTPUT_REGISTRY, _REGISTRY)
    write(OUTPUT_POLICY, _POLICY)
    write(OUTPUT_RUNBOOK, _RUNBOOK)
    write(OUTPUT_TEST, _TEST)
    return 0


_MODULE = r'''
"""Generated bounded local-only alert delivery foundation module.

v1 — contract-only. No real message sending.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict

ALLOWED_CHANNELS = frozenset({"log", "console", "dashboard", "queue"})
FORBIDDEN_CHANNELS = frozenset({"telegram", "slack", "email", "sms", "webhook", "http", "push"})


@dataclass(frozen=True)
class AlertDeliveryReceipt:
    receipt_id: str
    alert_id: str
    channel: str
    operator_acknowledged: bool
    evidence_reference_present: bool
    channel_valid: bool
    payload_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_message_sent: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_alert_delivery_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"alert_id", "channel", "alert_payload", "operator_acknowledgement", "evidence_reference"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    channel = payload["channel"]
    if channel in FORBIDDEN_CHANNELS:
        raise ValueError(f"forbidden_channel: {channel}")
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"unsupported_channel: {channel}")
    alert_payload = payload.get("alert_payload", {})
    if not isinstance(alert_payload, dict):
        raise TypeError("alert_payload must be a mapping")
    ap_str = str(alert_payload).lower()
    for forbidden in ("secret", "api_key", "token", "password"):
        if forbidden in ap_str:
            raise ValueError(f"secret_material_in_alert: {forbidden}")
    return {"valid": True, "alert_id": payload["alert_id"]}


def validate_alert_channel_policy(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    channel = payload.get("channel", "")
    return {
        "channel": channel,
        "channel_allowed": channel in ALLOWED_CHANNELS,
        "channel_forbidden": channel in FORBIDDEN_CHANNELS,
    }


def validate_alert_payload_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    ap = payload.get("alert_payload", {})
    checks = {
        "severity_present": "severity" in ap,
        "message_present": "message" in ap,
        "timestamp_present": "timestamp" in ap,
    }
    valid = all(checks.values())
    return {"payload_valid": valid, "checks": checks}


def produce_alert_delivery_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_alert_delivery_request(payload)
    channel_check = validate_alert_channel_policy(payload)
    payload_check = validate_alert_payload_contract(payload)
    ack = payload.get("operator_acknowledgement", {})
    acked = isinstance(ack, dict) and ack.get("acknowledged", False)
    receipt = AlertDeliveryReceipt(
        receipt_id=_hash_id(payload.get("alert_id", "unknown"), _utcnow()),
        alert_id=payload.get("alert_id", "unknown"),
        channel=payload.get("channel", ""),
        operator_acknowledged=acked,
        evidence_reference_present=bool(payload.get("evidence_reference")),
        channel_valid=channel_check["channel_allowed"] and not channel_check["channel_forbidden"],
        payload_valid=payload_check["payload_valid"],
        status="queued" if (payload_check["payload_valid"] and acked) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "AlertDeliveryReceipt",
    "validate_alert_delivery_request",
    "validate_alert_channel_policy",
    "validate_alert_payload_contract",
    "produce_alert_delivery_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "alert_delivery_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_alert_delivery_foundation.py",
    "receipt_type": "AlertDeliveryReceipt",
    "functions": [
        "validate_alert_delivery_request",
        "validate_alert_channel_policy",
        "validate_alert_payload_contract",
        "produce_alert_delivery_receipt",
    ],
    "allowed_channels": sorted(ALLOWED_CHANNELS),
    "boundary": "local-only, no real message sending in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "alert_delivery_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_channels": sorted(ALLOWED_CHANNELS),
    "forbidden_channels": sorted(FORBIDDEN_CHANNELS),
    "operator_acknowledgement_required": True,
    "evidence_reference_required": True,
    "secret_material_in_alerts_forbidden": True,
    "no_real_message_sending_in_v1": True,
    "no_network_delivery_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Alert Delivery Foundation v1

## Purpose
Bounded local-only alert delivery foundation. Validates alert delivery
requests without sending any real messages.

## Boundaries
- no real Telegram/send/network delivery in v1
- no secret token
- no missing operator acknowledgement
- no missing evidence reference
- no production autonomy
- no real message sending in v1

## Operations
1. validate_alert_delivery_request — structural validation
2. validate_alert_channel_policy — channel policy check
3. validate_alert_payload_contract — payload completeness
4. produce_alert_delivery_receipt — full receipt production

## Scope
Contract-only. Does not send any messages.
"""

_TEST = r'''"""Tests for generated alert delivery foundation module."""

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
'''

if __name__ == "__main__":
    raise SystemExit(main())
