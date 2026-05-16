"""Outbound leak gate using the shared scanner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.security.secret_scanner import CoreSecretScanner, SecretFinding

_ALLOWED_SINKS = {"provider_request", "run_report", "exported_artifact", "ledger_record", "failure_bundle", "telegram_message", "stdout"}


@dataclass(frozen=True)
class ExfiltrationGateResult:
    accepted: bool
    sink: str
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def validate_outbound_payload(payload: Mapping[str, Any] | str, *, sink: str, path: str = "<outbound>", scanner: CoreSecretScanner | None = None) -> ExfiltrationGateResult:
    engine = scanner or CoreSecretScanner()
    if sink not in _ALLOWED_SINKS:
        return ExfiltrationGateResult(False, sink, (), ("sink_not_declared",))
    if isinstance(payload, str):
        result = engine.scan_text(payload, path=path, field=sink)
    elif isinstance(payload, Mapping):
        result = engine.scan_mapping(payload, path=path)
    else:
        return ExfiltrationGateResult(False, sink, (), ("payload_type_invalid",))
    failures = () if result.accepted else ("payload_blocked",)
    return ExfiltrationGateResult(result.accepted, sink, result.findings, failures)
