"""Notification envelope contract."""

from __future__ import annotations

from typing import Mapping

from kernel.security.security_classification import normalize_classification

__all__ = ["validate_notification_envelope"]


def validate_notification_envelope(envelope: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(envelope, Mapping):
        return ("notification_envelope_must_be_mapping",)
    failures: list[str] = []
    for field in ("notification_id", "sink", "message_digest", "classification"):
        if not isinstance(envelope.get(field), str) or not envelope.get(field):
            failures.append(f"{field}_required")
    if not str(envelope.get("message_digest", "")).startswith("sha256:"):
        failures.append("message_digest_required")
    if normalize_classification(envelope.get("classification")) in {"SECRET", "CROWN_JEWEL"}:
        failures.append("sensitive_notification_payload_forbidden")
    if "raw_message" in envelope:
        failures.append("raw_message_forbidden")
    return tuple(sorted(set(failures)))
