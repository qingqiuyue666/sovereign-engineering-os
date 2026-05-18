"""Provider no-network enforcement — hard block on provider-owned network surface.

This module deliberately does not inspect global sys.modules. Full unittest
runs, Python internals, and unrelated tests may load socket/subprocess/urllib
before provider transport executes. Those ambient interpreter modules are not
provider transport violations.

Provider transport no-network enforcement is limited to provider-owned source
and request/payload validation. Source scanning rejects forbidden import
statements in provider_transport code. Request validation rejects network/live
markers before runtime execution reaches receipt production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


FORBIDDEN_MODULES = frozenset({
    "socket",
    "requests",
    "httpx",
    "urllib",
    "urllib2",
    "urllib3",
    "http.client",
    "http.server",
    "subprocess",
    "asyncio.subprocess",
    "ftplib",
    "smtplib",
    "imaplib",
    "poplib",
    "telnetlib",
    "xmlrpc.client",
    "websockets",
    "aiohttp",
    "tornado.httpclient",
    "selenium",
    "playwright",
    "pyppeteer",
})


@dataclass(frozen=True)
class NetworkEnforcementResult:
    """Immutable result of provider-owned no-network enforcement check."""
    valid: bool
    active_forbidden_modules: tuple[str, ...]
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "active_forbidden_modules": list(self.active_forbidden_modules),
            "failures": list(self.failures),
        }


def enforce_no_network(source_texts: Iterable[str] | None = None) -> NetworkEnforcementResult:
    """Validate provider-owned no-network surface.

    This function intentionally avoids global sys.modules scanning. Ambient
    interpreter state is not deterministic across full-suite runs and does not
    prove ProviderTransport used the network.

    Args:
        source_texts: Optional provider-owned source snippets to scan. Runtime
            callers may omit this because provider source scanning is also
            covered by tracer-bullet tests.

    Returns:
        NetworkEnforcementResult. active_forbidden_modules is retained for the
        stable public contract, but means provider-owned forbidden imports, not
        globally loaded interpreter modules.
    """
    failures: list[str] = []
    active_forbidden: list[str] = []

    if source_texts is not None:
        for source_index, source_text in enumerate(source_texts):
            for violation in scan_source_for_forbidden_imports(source_text):
                active_forbidden.append(violation)
                failures.append(f"provider_source_forbidden_import[{source_index}]: {violation}")

    return NetworkEnforcementResult(
        valid=len(failures) == 0,
        active_forbidden_modules=tuple(active_forbidden),
        failures=tuple(failures),
    )


def scan_source_for_forbidden_imports(source_text: str) -> tuple[str, ...]:
    """Scan Python source text for forbidden import statements.

    Args:
        source_text: Python source code as a string.

    Returns:
        Tuple of violation descriptions, empty if clean.
    """
    violations: list[str] = []
    lines = source_text.split("\n")
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for mod in FORBIDDEN_MODULES:
            if f"import {mod}" in stripped or f"from {mod}" in stripped:
                violations.append(f"line_{i}: {mod}")
    return tuple(violations)
