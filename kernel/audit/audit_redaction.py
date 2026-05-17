"""Shape-preserving audit redaction."""

from __future__ import annotations

from typing import Any

from kernel.security.ai_context_firewall import filter_ai_context

__all__ = ["redact_audit_payload"]


def redact_audit_payload(payload: Any) -> dict[str, object]:
    result = filter_ai_context(payload)
    return {
        "redacted_payload": result.filtered_context,
        "redaction_count": result.redaction_count,
        "redaction_status": "redacted" if result.redaction_count else "not_required",
    }
