"""Telegram mock sender. No live Telegram send or network access occurs."""

from __future__ import annotations

from typing import Mapping

from kernel.tasks.run_id import digest_payload

from .notification_contract import validate_notification_envelope

__all__ = ["send_telegram_mock"]


def send_telegram_mock(envelope: Mapping[str, object]) -> dict[str, object]:
    failures = validate_notification_envelope(envelope)
    if failures:
        return {"accepted": False, "failures": list(failures), "live_send_performed": False}
    receipt = {
        "receipt_type": "telegram_mock_receipt_v1",
        "notification_digest": digest_payload(dict(envelope)),
        "sink": envelope["sink"],
        "redaction_status": envelope.get("redaction_status", "not_required"),
        "live_send_performed": False,
    }
    return {"accepted": True, "receipt": receipt, "live_send_performed": False}
