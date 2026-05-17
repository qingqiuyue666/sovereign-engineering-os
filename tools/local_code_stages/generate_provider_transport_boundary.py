#!/usr/bin/env python3
"""Generate bounded local-only provider transport boundary artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

KNOWN_PROVIDERS = frozenset({"mock-finance", "mock-market-data", "mock-news", "mock-weather"})
FORBIDDEN_PROVIDERS = frozenset({"live-broker", "live-exchange", "live-payment", "live-bank"})
REQUIRED_FIELDS = frozenset({"provider_id", "capability_token", "evidence_binding", "request_payload"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_provider_transport_boundary.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/provider_transport_boundary_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/provider_transport_boundary_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/provider_transport_boundary_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_provider_transport_boundary.py"

ALLOWED_OUTPUTS = {OUTPUT_MODULE, OUTPUT_REGISTRY, OUTPUT_POLICY, OUTPUT_RUNBOOK, OUTPUT_TEST}


def assert_allowed(path: Path) -> None:
    resolved = path.resolve()
    allowed = {item.resolve() for item in ALLOWED_OUTPUTS}
    if resolved not in allowed:
        raise RuntimeError(f"write_path_not_allowlisted: {path}")


def write(path: Path, text: str) -> None:
    assert_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    write(OUTPUT_MODULE, _MODULE)
    write(OUTPUT_REGISTRY, _REGISTRY)
    write(OUTPUT_POLICY, _POLICY)
    write(OUTPUT_RUNBOOK, _RUNBOOK)
    write(OUTPUT_TEST, _TEST)
    return 0


_MODULE = r'''
"""Generated bounded local-only provider transport boundary module.

v1 — contract-only. No real provider calls.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

KNOWN_PROVIDERS = frozenset({"mock-finance", "mock-market-data", "mock-news", "mock-weather"})
FORBIDDEN_PROVIDERS = frozenset({"live-broker", "live-exchange", "live-payment", "live-bank"})
REQUIRED_FIELDS = frozenset({"provider_id", "capability_token", "evidence_binding", "request_payload"})


@dataclass(frozen=True)
class ProviderTransportReceipt:
    receipt_id: str
    provider_id: str
    capability_token: str
    evidence_binding_present: bool
    status: str
    boundary_valid: bool
    preflight_passed: bool
    created_at: str
    module_version: str = "v1"
    no_provider_call: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_provider_transport_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    pid = payload["provider_id"]
    if pid in FORBIDDEN_PROVIDERS:
        raise ValueError(f"forbidden_provider: {pid}")
    if pid not in KNOWN_PROVIDERS:
        raise ValueError(f"unknown_provider: {pid}")
    if not isinstance(payload.get("request_payload"), dict):
        raise TypeError("request_payload must be a mapping")
    rp = payload["request_payload"]
    for forbidden in ("secret", "api_key", "token", "password", "credential"):
        if forbidden in str(rp).lower():
            raise ValueError(f"secret_material_detected: {forbidden}")
    return {"valid": True, "provider_id": pid}


def validate_provider_capability_boundary(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    token = payload.get("capability_token", "")
    valid = isinstance(token, str) and len(token) > 0
    return {"capability_valid": valid, "token_present": valid}


def validate_provider_transport_preflight(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks: Dict[str, bool] = {}
    checks["evidence_binding_present"] = bool(payload.get("evidence_binding"))
    checks["capability_token_present"] = bool(payload.get("capability_token"))
    checks["provider_known"] = payload.get("provider_id") in KNOWN_PROVIDERS
    checks["no_forbidden_provider"] = payload.get("provider_id") not in FORBIDDEN_PROVIDERS
    all_pass = all(checks.values())
    return {"preflight_passed": all_pass, "checks": checks}


def produce_provider_transport_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_provider_transport_request(payload)
    cap = validate_provider_capability_boundary(payload)
    preflight = validate_provider_transport_preflight(payload)
    receipt = ProviderTransportReceipt(
        receipt_id=_hash_id(payload.get("provider_id", "unknown"), "v1"),
        provider_id=payload.get("provider_id", "unknown"),
        capability_token=payload.get("capability_token", ""),
        evidence_binding_present=bool(payload.get("evidence_binding")),
        status="gated" if (preflight["preflight_passed"] and cap["capability_valid"]) else "rejected",
        boundary_valid=preflight["preflight_passed"],
        preflight_passed=preflight["preflight_passed"],
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "ProviderTransportReceipt",
    "validate_provider_transport_request",
    "validate_provider_capability_boundary",
    "validate_provider_transport_preflight",
    "produce_provider_transport_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "provider_transport_boundary_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_provider_transport_boundary.py",
    "receipt_type": "ProviderTransportReceipt",
    "functions": [
        "validate_provider_transport_request",
        "validate_provider_capability_boundary",
        "validate_provider_transport_preflight",
        "produce_provider_transport_receipt",
    ],
    "known_providers": sorted(KNOWN_PROVIDERS),
    "boundary": "local-only, no real provider calls in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "provider_transport_boundary_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "known_providers": sorted(KNOWN_PROVIDERS),
    "forbidden_providers": sorted(FORBIDDEN_PROVIDERS),
    "required_fields": sorted(REQUIRED_FIELDS),
    "live_provider_calls_forbidden_in_v1": True,
    "network_execution_forbidden_in_v1": True,
    "production_autonomy_forbidden_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Provider Transport Boundary v1

## Purpose
Bounded local-only provider transport boundary. Validates provider
transport requests without making real provider calls.

## Boundaries
- no live provider execution
- no unknown provider
- no missing capability token
- no missing evidence binding
- no secret material
- no network execution in v1
- no production autonomy
- no real provider calls in v1

## Operations
1. validate_provider_transport_request — structural validation
2. validate_provider_capability_boundary — token validation
3. validate_provider_transport_preflight — preflight checks
4. produce_provider_transport_receipt — full receipt production

## Scope
Contract-only. Does not make any provider calls.
"""

_TEST = r'''"""Tests for generated provider transport boundary module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_provider_transport_boundary import (  # type: ignore[import-not-found]
    ProviderTransportReceipt,
    validate_provider_transport_request,
    validate_provider_capability_boundary,
    validate_provider_transport_preflight,
    produce_provider_transport_receipt,
)

VALID_PAYLOAD = {
    "provider_id": "mock-market-data",
    "capability_token": "cap-token-xyz-123",
    "evidence_binding": "evid-binding-001",
    "request_payload": {"symbol": "TEST", "field": "price"},
}


class ProviderTransportBoundaryTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_provider_transport_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_provider_transport_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_provider_transport_request({})

    def test_validate_rejects_live_broker(self):
        p = {**VALID_PAYLOAD, "provider_id": "live-broker"}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_rejects_unknown_provider(self):
        p = {**VALID_PAYLOAD, "provider_id": "mystery-meat-api"}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_rejects_secret_in_payload(self):
        p = {**VALID_PAYLOAD, "request_payload": {"api_key": "sk-123"}}
        with self.assertRaises(ValueError):
            validate_provider_transport_request(p)

    def test_validate_capability_boundary(self):
        result = validate_provider_capability_boundary(VALID_PAYLOAD)
        self.assertTrue(result["capability_valid"])

    def test_validate_capability_boundary_missing_token(self):
        p = {**VALID_PAYLOAD, "capability_token": ""}
        result = validate_provider_capability_boundary(p)
        self.assertFalse(result["capability_valid"])

    def test_validate_preflight_passes(self):
        result = validate_provider_transport_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_validate_preflight_fails_no_evidence(self):
        p = {**VALID_PAYLOAD, "evidence_binding": ""}
        result = validate_provider_transport_preflight(p)
        self.assertFalse(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_provider_transport_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "gated")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_provider_call"])

    def test_receipt_dataclass(self):
        r = ProviderTransportReceipt(
            receipt_id="rid-1", provider_id="mock-market-data",
            capability_token="tok", evidence_binding_present=True,
            status="gated", boundary_valid=True, preflight_passed=True,
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_provider_call)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_provider_transport_boundary.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
