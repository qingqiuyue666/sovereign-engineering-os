#!/usr/bin/env python3
"""Generate bounded local-only asset mapping foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ASSET_CLASSES = frozenset({"equity", "option", "future", "forex", "crypto", "index", "commodity"})
REQUIRED_FIELDS = frozenset({"candidate_id", "asset_class", "venue", "product_id", "evidence_refs", "confidence", "friction_data"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_asset_mapping_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/asset_mapping_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/asset_mapping_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/asset_mapping_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_asset_mapping_foundation.py"

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
"""Generated bounded local-only asset mapping foundation module.

v1 — contract-only. No real trading decision.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ALLOWED_ASSET_CLASSES = frozenset({"equity", "option", "future", "forex", "crypto", "index", "commodity"})
REQUIRED_FIELDS = frozenset({"candidate_id", "asset_class", "venue", "product_id", "evidence_refs", "confidence", "friction_data"})


@dataclass(frozen=True)
class AssetMappingReceipt:
    receipt_id: str
    candidate_id: str
    asset_class: str
    venue: str
    product_id: str
    evidence_present: bool
    confidence: float
    confidence_overclaim: bool
    friction_data_present: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_trading_decision: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_asset_mapping_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    ac = payload["asset_class"]
    if ac not in ALLOWED_ASSET_CLASSES:
        raise ValueError(f"unsupported_asset_class: {ac}")
    if not payload.get("venue"):
        raise ValueError("venue_is_required")
    if not payload.get("product_id"):
        raise ValueError("product_id_is_required")
    evidence = payload.get("evidence_refs", [])
    if not isinstance(evidence, list) or len(evidence) == 0:
        raise ValueError("evidence_refs_must_be_non_empty_list")
    return {"valid": True, "candidate_id": payload["candidate_id"]}


def validate_asset_candidate_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks = {
        "venue_present": bool(payload.get("venue")),
        "product_id_present": bool(payload.get("product_id")),
        "asset_class_supported": payload.get("asset_class") in ALLOWED_ASSET_CLASSES,
    }
    return {"candidate_valid": all(checks.values()), "checks": checks}


def validate_mapping_confidence_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    conf = payload.get("confidence", 0.0)
    if not isinstance(conf, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = conf > 0.95
    if overclaim:
        raise ValueError(f"confidence_overclaim: {conf} exceeds max 0.95")
    return {"confidence": conf, "overclaim": overclaim, "within_bounds": not overclaim}


def produce_asset_mapping_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_asset_mapping_request(payload)
    candidate = validate_asset_candidate_contract(payload)
    conf_check = validate_mapping_confidence_contract(payload)
    receipt = AssetMappingReceipt(
        receipt_id=_hash_id(payload.get("candidate_id", "unknown"), "v1"),
        candidate_id=payload.get("candidate_id", "unknown"),
        asset_class=payload.get("asset_class", ""),
        venue=payload.get("venue", ""),
        product_id=payload.get("product_id", ""),
        evidence_present=len(payload.get("evidence_refs", [])) > 0,
        confidence=conf_check["confidence"],
        confidence_overclaim=conf_check["overclaim"],
        friction_data_present=bool(payload.get("friction_data")),
        status="mapped" if (candidate["candidate_valid"] and conf_check["within_bounds"]) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "AssetMappingReceipt",
    "validate_asset_mapping_request",
    "validate_asset_candidate_contract",
    "validate_mapping_confidence_contract",
    "produce_asset_mapping_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "asset_mapping_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_asset_mapping_foundation.py",
    "receipt_type": "AssetMappingReceipt",
    "functions": [
        "validate_asset_mapping_request",
        "validate_asset_candidate_contract",
        "validate_mapping_confidence_contract",
        "produce_asset_mapping_receipt",
    ],
    "allowed_asset_classes": sorted(ALLOWED_ASSET_CLASSES),
    "boundary": "local-only, no real trading decision in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "asset_mapping_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_asset_classes": sorted(ALLOWED_ASSET_CLASSES),
    "max_confidence": 0.95,
    "evidence_required": True,
    "venue_required": True,
    "product_id_required": True,
    "friction_data_required": True,
    "confidence_overclaim_forbidden": True,
    "no_real_trading_decision_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Asset Mapping Foundation v1

## Purpose
Bounded local-only asset mapping foundation. Validates asset mapping
requests without making trading decisions.

## Boundaries
- no missing evidence
- no missing venue
- no missing product id
- no unsupported asset class
- no confidence overclaim (max 0.95)
- no action without friction data
- no real trading decision in v1

## Operations
1. validate_asset_mapping_request — structural validation
2. validate_asset_candidate_contract — candidate completeness
3. validate_mapping_confidence_contract — confidence bounds
4. produce_asset_mapping_receipt — full receipt production

## Scope
Contract-only. Does not make any trading decisions.
"""

_TEST = r'''"""Tests for generated asset mapping foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_asset_mapping_foundation import (  # type: ignore[import-not-found]
    AssetMappingReceipt,
    validate_asset_mapping_request,
    validate_asset_candidate_contract,
    validate_mapping_confidence_contract,
    produce_asset_mapping_receipt,
)

VALID_PAYLOAD = {
    "candidate_id": "CAND-001",
    "asset_class": "equity",
    "venue": "NYSE",
    "product_id": "AAPL",
    "evidence_refs": ["evid-001", "evid-002"],
    "confidence": 0.85,
    "friction_data": {"spread": 0.01, "liquidity": "high"},
}


class AssetMappingFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_asset_mapping_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_asset_mapping_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_asset_mapping_request({})

    def test_validate_rejects_unsupported_asset_class(self):
        p = {**VALID_PAYLOAD, "asset_class": "magic_beans"}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_rejects_empty_evidence(self):
        p = {**VALID_PAYLOAD, "evidence_refs": []}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_rejects_missing_venue(self):
        p = {**VALID_PAYLOAD, "venue": ""}
        with self.assertRaises(ValueError):
            validate_asset_mapping_request(p)

    def test_validate_candidate_contract(self):
        result = validate_asset_candidate_contract(VALID_PAYLOAD)
        self.assertTrue(result["candidate_valid"])

    def test_validate_confidence_contract(self):
        result = validate_mapping_confidence_contract(VALID_PAYLOAD)
        self.assertFalse(result["overclaim"])

    def test_validate_confidence_overclaim(self):
        p = {**VALID_PAYLOAD, "confidence": 0.99}
        with self.assertRaises(ValueError):
            validate_mapping_confidence_contract(p)

    def test_produce_receipt_valid(self):
        receipt = produce_asset_mapping_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "mapped")
        self.assertTrue(receipt["no_trading_decision"])

    def test_produce_receipt_rejected_bad_class(self):
        p = {**VALID_PAYLOAD, "asset_class": "magic_beans"}
        with self.assertRaises(ValueError):
            produce_asset_mapping_receipt(p)

    def test_receipt_dataclass(self):
        r = AssetMappingReceipt(
            receipt_id="rid-1", candidate_id="C-1", asset_class="equity",
            venue="NYSE", product_id="AAPL", evidence_present=True,
            confidence=0.85, confidence_overclaim=False,
            friction_data_present=True, status="mapped",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_trading_decision)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_asset_mapping_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
