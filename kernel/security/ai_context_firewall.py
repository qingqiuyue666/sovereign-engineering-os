"""AI context firewall with shape-preserving redaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .secret_scanner import CoreSecretScanner, REDACTION, SecretFinding

__all__ = ["AIContextFirewallResult", "filter_ai_context"]


@dataclass(frozen=True)
class AIContextFirewallResult:
    accepted: bool
    filtered_context: Any
    redaction_count: int
    findings: tuple[SecretFinding, ...]


def filter_ai_context(context: Any, *, scanner: CoreSecretScanner | None = None) -> AIContextFirewallResult:
    active_scanner = scanner or CoreSecretScanner()
    findings: list[SecretFinding] = []
    redactions = 0

    def walk(value: Any, path: str) -> Any:
        nonlocal redactions
        if isinstance(value, dict):
            return {key: walk(child, f"{path}.{key}") for key, child in value.items()}
        if isinstance(value, list):
            return [walk(child, f"{path}[{index}]") for index, child in enumerate(value)]
        if isinstance(value, tuple):
            return tuple(walk(child, f"{path}[{index}]") for index, child in enumerate(value))
        if isinstance(value, str):
            scan = active_scanner.scan_text(value, path=path)
            if not scan.clean:
                findings.extend(scan.findings)
                redactions += 1
                return REDACTION
            return value
        return value

    filtered = walk(context, "$")
    return AIContextFirewallResult(
        accepted=True,
        filtered_context=filtered,
        redaction_count=redactions,
        findings=tuple(findings),
    )
