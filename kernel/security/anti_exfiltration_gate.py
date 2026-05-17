"""Outbound anti-exfiltration gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

from .secret_scanner import CoreSecretScanner, SecretFinding
from .security_classification import normalize_classification

__all__ = ["AntiExfiltrationResult", "inspect_outbound_payload"]


@dataclass(frozen=True)
class AntiExfiltrationResult:
    allowed: bool
    verdict: str
    findings: tuple[SecretFinding, ...]
    failures: tuple[str, ...]


def inspect_outbound_payload(
    payload: Any,
    *,
    classification: str = "INTERNAL",
    scanner: CoreSecretScanner | None = None,
) -> AntiExfiltrationResult:
    normalized = normalize_classification(classification)
    failures: list[str] = []
    if normalized is None:
        failures.append("classification_unknown")
    if normalized in {"SECRET", "CROWN_JEWEL"}:
        failures.append("classification_not_exportable")
    try:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except TypeError:
        text = str(payload)
        failures.append("payload_not_json_serializable")
    scan = (scanner or CoreSecretScanner()).scan_text(text, path="outbound_payload")
    if not scan.clean:
        failures.append("payload_contaminated")
    unique_failures = tuple(sorted(set(failures)))
    return AntiExfiltrationResult(
        allowed=not unique_failures,
        verdict="allowed" if not unique_failures else "blocked_fail_closed",
        findings=scan.findings,
        failures=unique_failures,
    )
