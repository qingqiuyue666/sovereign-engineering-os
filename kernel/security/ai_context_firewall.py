"""AI context firewall using the shared scanner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from kernel.security.secret_scanner import CoreSecretScanner, SecretFinding


@dataclass(frozen=True)
class AIContextFirewallResult:
    accepted: bool
    sanitized_payload: Any
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def filter_ai_context(payload: Mapping[str, Any] | str, *, path: str = "<ai-context>", scanner: CoreSecretScanner | None = None) -> AIContextFirewallResult:
    engine = scanner or CoreSecretScanner()
    if isinstance(payload, str):
        result = engine.scan_text(payload, path=path, field="ai_context")
        if result.accepted:
            return AIContextFirewallResult(True, payload, (), ())
        return AIContextFirewallResult(False, "[REDACTED]", result.findings, ("ai_context_blocked",))
    if isinstance(payload, Mapping):
        result = engine.scan_mapping(payload, path=path)
        if result.accepted:
            return AIContextFirewallResult(True, payload, (), ())
        sanitized = _redact_shape(payload)
        return AIContextFirewallResult(False, sanitized, result.findings, ("ai_context_blocked",))
    return AIContextFirewallResult(False, None, (), ("payload_type_invalid",))


def _redact_shape(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    def redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: redact(child) for key, child in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, str):
            return "[REDACTED]"
        return value
    redacted = redact(payload)
    json.dumps(redacted, sort_keys=True)
    return redacted
