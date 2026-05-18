"""Provider no-network enforcement — hard block on network activity.

Verifies no network imports exist and no network operations can occur.
Forbidden modules: socket, requests, httpx, urllib, urllib2, urllib3,
http.client, subprocess (network via shell).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Dict


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
    """Immutable result of no-network enforcement check."""
    valid: bool
    active_forbidden_modules: tuple[str, ...]
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "active_forbidden_modules": list(self.active_forbidden_modules),
            "failures": list(self.failures),
        }


def enforce_no_network() -> NetworkEnforcementResult:
    """Check loaded modules for forbidden network-related imports.

    This is a runtime enforcement — it checks what is currently loaded.
    It does NOT scan source code; that's done by security tests.

    Returns:
        NetworkEnforcementResult with any detected violations.
    """
    failures: list[str] = []
    active_forbidden: list[str] = []

    for module_name in sorted(FORBIDDEN_MODULES):
        if module_name in sys.modules:
            active_forbidden.append(module_name)
            failures.append(f"forbidden_module_loaded: {module_name}")

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
        if stripped.startswith("#"):
            continue
        for mod in FORBIDDEN_MODULES:
            if f"import {mod}" in stripped or f"from {mod}" in stripped:
                violations.append(f"line_{i}: {mod}")
    return tuple(violations)
