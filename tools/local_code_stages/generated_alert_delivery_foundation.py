
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


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



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
        receipt_id=_hash_id(payload.get("alert_id", "unknown"), "v1"),
        alert_id=payload.get("alert_id", "unknown"),
        channel=payload.get("channel", ""),
        operator_acknowledged=acked,
        evidence_reference_present=bool(payload.get("evidence_reference")),
        channel_valid=channel_check["channel_allowed"] and not channel_check["channel_forbidden"],
        payload_valid=payload_check["payload_valid"],
        status="queued" if (payload_check["payload_valid"] and acked) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "AlertDeliveryReceipt",
    "validate_alert_delivery_request",
    "validate_alert_channel_policy",
    "validate_alert_payload_contract",
    "produce_alert_delivery_receipt",
]
