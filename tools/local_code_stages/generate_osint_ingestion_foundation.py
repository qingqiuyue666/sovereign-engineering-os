#!/usr/bin/env python3
"""Generate bounded local-only OSINT ingestion foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY", "TIER_3_TERTIARY"})
DOWNGRADE_ACTIONS = frozenset({"WAIT", "NO_TRADE", "FLAG_ONLY"})
FORBIDDEN_SOURCES = frozenset({"live_network", "live_scraper", "live_api"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_osint_ingestion_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/osint_ingestion_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/osint_ingestion_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/osint_ingestion_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_osint_ingestion_foundation.py"

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
"""Generated bounded local-only OSINT ingestion foundation module.

v1 — contract-only. No real ingestion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

SOURCE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY", "TIER_3_TERTIARY"})
DOWNGRADE_ACTIONS = frozenset({"WAIT", "NO_TRADE", "FLAG_ONLY"})
FORBIDDEN_SOURCES = frozenset({"live_network", "live_scraper", "live_api"})


@dataclass(frozen=True)
class OsintIngestionReceipt:
    receipt_id: str
    source_id: str
    source_tier: str
    freshness_timestamp: str
    evidence_hash_present: bool
    conflict_resolution: str
    status: str
    created_at: str
    module_version: str = "v1"
    no_ingestion: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_osint_ingestion_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"source_id", "source_tier", "timestamp", "evidence_hash", "conflict_resolution"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    source_id = payload["source_id"]
    if source_id in FORBIDDEN_SOURCES:
        raise ValueError(f"forbidden_source: {source_id}")
    tier = payload["source_tier"]
    if tier not in SOURCE_TIERS:
        raise ValueError(f"unsupported_source_tier: {tier}")
    conflict = payload.get("conflict_resolution", "")
    if conflict and conflict not in DOWNGRADE_ACTIONS and conflict != "NONE":
        raise ValueError(f"invalid_conflict_resolution: {conflict}")
    return {"valid": True, "source_id": source_id}


def validate_source_tier_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    tier = payload.get("source_tier", "")
    downgraded = tier == "TIER_3_TERTIARY"
    return {"tier": tier, "downgraded": downgraded, "action_required": "NO_TRADE" if downgraded else "ALLOW"}


def validate_freshness_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    ts = payload.get("timestamp", "")
    if not ts:
        return {"fresh": False, "reason": "missing_timestamp"}
    return {"fresh": True, "timestamp": ts}


def produce_osint_ingestion_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_osint_ingestion_request(payload)
    tier_check = validate_source_tier_contract(payload)
    freshness = validate_freshness_contract(payload)
    status = "ingested"
    if tier_check["downgraded"]:
        status = "downgraded"
    if not freshness["fresh"]:
        status = "stale_rejected"
    receipt = OsintIngestionReceipt(
        receipt_id=_hash_id(payload.get("source_id", "unknown"), _utcnow()),
        source_id=payload.get("source_id", "unknown"),
        source_tier=payload.get("source_tier", ""),
        freshness_timestamp=payload.get("timestamp", ""),
        evidence_hash_present=bool(payload.get("evidence_hash")),
        conflict_resolution=payload.get("conflict_resolution", "NONE"),
        status=status,
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "OsintIngestionReceipt",
    "validate_osint_ingestion_request",
    "validate_source_tier_contract",
    "validate_freshness_contract",
    "produce_osint_ingestion_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "osint_ingestion_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_osint_ingestion_foundation.py",
    "receipt_type": "OsintIngestionReceipt",
    "functions": [
        "validate_osint_ingestion_request",
        "validate_source_tier_contract",
        "validate_freshness_contract",
        "produce_osint_ingestion_receipt",
    ],
    "source_tiers": sorted(SOURCE_TIERS),
    "boundary": "local-only, no real ingestion in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "osint_ingestion_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "source_tiers": sorted(SOURCE_TIERS),
    "downgrade_actions": sorted(DOWNGRADE_ACTIONS),
    "forbidden_sources": sorted(FORBIDDEN_SOURCES),
    "evidence_hash_required": True,
    "timestamp_required": True,
    "live_network_ingestion_forbidden_in_v1": True,
    "no_real_ingestion_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# OSINT Ingestion Foundation v1

## Purpose
Bounded local-only OSINT ingestion foundation. Validates ingestion
requests without performing real data ingestion.

## Boundaries
- no live network ingestion in v1
- no weak source without downgrade
- no missing source tier
- no missing timestamp
- no missing evidence hash
- no conflict without WAIT/NO_TRADE downgrade
- no real ingestion in v1

## Source Tiers
TIER_1_PRIMARY, TIER_2_SECONDARY, TIER_3_TERTIARY

## Operations
1. validate_osint_ingestion_request — structural validation
2. validate_source_tier_contract — tier-based rules
3. validate_freshness_contract — timestamp freshness
4. produce_osint_ingestion_receipt — full receipt production

## Scope
Contract-only. Does not perform any real data ingestion.
"""

_TEST = r'''"""Tests for generated OSINT ingestion foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_osint_ingestion_foundation import (  # type: ignore[import-not-found]
    OsintIngestionReceipt,
    validate_osint_ingestion_request,
    validate_source_tier_contract,
    validate_freshness_contract,
    produce_osint_ingestion_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "source_id": "news-source-rss-001",
    "source_tier": "TIER_1_PRIMARY",
    "timestamp": "2025-01-01T00:00:00Z",
    "evidence_hash": VALID_SHA256,
    "conflict_resolution": "NONE",
}


class OsintIngestionFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_osint_ingestion_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_osint_ingestion_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request({})

    def test_validate_rejects_live_network_source(self):
        p = {**VALID_PAYLOAD, "source_id": "live_scraper"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_validate_rejects_bad_tier(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_99_MAGIC"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_validate_rejects_bad_conflict_resolution(self):
        p = {**VALID_PAYLOAD, "conflict_resolution": "IGNORE_AND_TRADE"}
        with self.assertRaises(ValueError):
            validate_osint_ingestion_request(p)

    def test_source_tier_contract_tier1_allows(self):
        result = validate_source_tier_contract(VALID_PAYLOAD)
        self.assertFalse(result["downgraded"])
        self.assertEqual(result["action_required"], "ALLOW")

    def test_source_tier_contract_tier3_downgrades(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_3_TERTIARY"}
        result = validate_source_tier_contract(p)
        self.assertTrue(result["downgraded"])
        self.assertEqual(result["action_required"], "NO_TRADE")

    def test_freshness_contract(self):
        result = validate_freshness_contract(VALID_PAYLOAD)
        self.assertTrue(result["fresh"])

    def test_freshness_contract_missing(self):
        p = {**VALID_PAYLOAD, "timestamp": ""}
        result = validate_freshness_contract(p)
        self.assertFalse(result["fresh"])

    def test_produce_receipt_valid(self):
        receipt = produce_osint_ingestion_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ingested")
        self.assertTrue(receipt["no_ingestion"])

    def test_produce_receipt_tier3_downgraded(self):
        p = {**VALID_PAYLOAD, "source_tier": "TIER_3_TERTIARY"}
        receipt = produce_osint_ingestion_receipt(p)
        self.assertEqual(receipt["status"], "downgraded")

    def test_receipt_dataclass(self):
        r = OsintIngestionReceipt(
            receipt_id="rid-1", source_id="S-1", source_tier="TIER_1_PRIMARY",
            freshness_timestamp="2025-01-01T00:00:00Z", evidence_hash_present=True,
            conflict_resolution="NONE", status="ingested",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_ingestion)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_osint_ingestion_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
