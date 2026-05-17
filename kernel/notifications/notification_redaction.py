"""Notification redaction helpers."""

from __future__ import annotations

from typing import Any

from kernel.audit.audit_redaction import redact_audit_payload

__all__ = ["redact_notification_payload"]


def redact_notification_payload(payload: Any) -> dict[str, object]:
    return redact_audit_payload(payload)
