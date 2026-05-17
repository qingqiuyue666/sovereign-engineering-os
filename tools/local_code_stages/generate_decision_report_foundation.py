#!/usr/bin/env python3
"""Generate bounded local-only decision report foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SUPPORTED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_decision_report_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/decision_report_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/decision_report_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/decision_report_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_decision_report_foundation.py"

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
"""Generated bounded local-only decision report foundation module.

v1 — contract-only. No production report publication.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

SUPPORTED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE"})


@dataclass(frozen=True)
class DecisionReportReceipt:
    receipt_id: str
    decision_id: str
    action: str
    evidence_links_present: bool
    confidence_rationale_present: bool
    friction_summary_present: bool
    human_review_present: bool
    overclaim_detected: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_report_publication: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_decision_report(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"decision_id", "action", "evidence_links", "confidence_rationale", "friction_summary", "human_review"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("decision_id"):
        raise ValueError("missing_decision_id")
    action = payload.get("action", "")
    if action in FORBIDDEN_ACTIONS:
        raise ValueError(f"forbidden_action: {action}")
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"unsupported_action: {action}")
    return {"valid": True, "decision_id": payload["decision_id"]}


def validate_report_evidence_links(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    links = payload.get("evidence_links", [])
    if not isinstance(links, list) or len(links) == 0:
        raise ValueError("evidence_links_must_be_non_empty_list")
    return {"evidence_links_present": True, "count": len(links)}


def validate_report_non_overclaim(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    claims = payload.get("confidence_rationale", {})
    if not isinstance(claims, dict):
        raise TypeError("confidence_rationale must be a mapping")
    confidence = claims.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = confidence > 0.95
    if overclaim:
        raise ValueError(f"overclaim_detected: confidence {confidence} exceeds max 0.95")
    claims_made = claims.get("claims", [])
    if not isinstance(claims_made, list):
        raise TypeError("claims must be a list")
    bounded = all(isinstance(c, str) and len(c) > 0 for c in claims_made)
    return {"overclaim": overclaim, "confidence": confidence, "claims_bounded": bounded}


def produce_decision_report_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_decision_report(payload)
    evidence = validate_report_evidence_links(payload)
    non_overclaim = validate_report_non_overclaim(payload)
    hr = payload.get("human_review", {})
    has_review = isinstance(hr, dict) and hr.get("reviewed", False) and bool(hr.get("reviewer_id"))
    friction = payload.get("friction_summary", {})
    has_friction = isinstance(friction, dict) and bool(friction.get("summary"))
    receipt = DecisionReportReceipt(
        receipt_id=_hash_id(payload.get("decision_id", "unknown"), "v1"),
        decision_id=payload.get("decision_id", "unknown"),
        action=payload.get("action", ""),
        evidence_links_present=evidence["evidence_links_present"],
        confidence_rationale_present=bool(payload.get("confidence_rationale")),
        friction_summary_present=has_friction,
        human_review_present=has_review,
        overclaim_detected=non_overclaim["overclaim"],
        status="published" if (evidence["evidence_links_present"] and has_review and has_friction and not non_overclaim["overclaim"]) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "DecisionReportReceipt",
    "validate_decision_report",
    "validate_report_evidence_links",
    "validate_report_non_overclaim",
    "produce_decision_report_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "decision_report_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_decision_report_foundation.py",
    "receipt_type": "DecisionReportReceipt",
    "functions": [
        "validate_decision_report",
        "validate_report_evidence_links",
        "validate_report_non_overclaim",
        "produce_decision_report_receipt",
    ],
    "boundary": "local-only, no production report publication in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "decision_report_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "supported_actions": sorted(SUPPORTED_ACTIONS),
    "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    "max_confidence": 0.95,
    "evidence_links_required": True,
    "confidence_rationale_required": True,
    "friction_summary_required": True,
    "human_review_required": True,
    "overclaim_forbidden": True,
    "no_report_publication_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Decision Report Foundation v1

## Purpose
Bounded local-only decision report foundation. Validates decision
reports without publishing to production.

## Boundaries
- no missing decision id
- no missing evidence links
- no missing confidence rationale
- no missing friction summary
- no missing human review
- no unsupported action
- no overclaim (max confidence 0.95)
- no production report publication in v1

## Operations
1. validate_decision_report — structural validation
2. validate_report_evidence_links — evidence link check
3. validate_report_non_overclaim — confidence bounds
4. produce_decision_report_receipt — full receipt production

## Scope
Contract-only. Does not publish reports.
"""

_TEST = r'''"""Tests for generated decision report foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_decision_report_foundation import (  # type: ignore[import-not-found]
    DecisionReportReceipt,
    validate_decision_report,
    validate_report_evidence_links,
    validate_report_non_overclaim,
    produce_decision_report_receipt,
)

VALID_PAYLOAD = {
    "decision_id": "DEC-001",
    "action": "HOLD",
    "evidence_links": ["evid-001", "evid-002"],
    "confidence_rationale": {"confidence": 0.85, "claims": ["market_data_consistent", "risk_within_bounds"]},
    "friction_summary": {"summary": "Low spread, high liquidity on NYSE"},
    "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
}


class DecisionReportFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_decision_report(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_decision_report("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_decision_report({})

    def test_validate_rejects_forbidden_action(self):
        p = {**VALID_PAYLOAD, "action": "BUY"}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_rejects_unsupported_action(self):
        p = {**VALID_PAYLOAD, "action": "YOLO_ALL_IN"}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_rejects_missing_decision_id(self):
        p = {**VALID_PAYLOAD, "decision_id": ""}
        with self.assertRaises(ValueError):
            validate_decision_report(p)

    def test_validate_evidence_links(self):
        result = validate_report_evidence_links(VALID_PAYLOAD)
        self.assertTrue(result["evidence_links_present"])

    def test_validate_evidence_links_empty(self):
        p = {**VALID_PAYLOAD, "evidence_links": []}
        with self.assertRaises(ValueError):
            validate_report_evidence_links(p)

    def test_validate_non_overclaim(self):
        result = validate_report_non_overclaim(VALID_PAYLOAD)
        self.assertFalse(result["overclaim"])

    def test_validate_overclaim_detected(self):
        p = {**VALID_PAYLOAD, "confidence_rationale": {"confidence": 0.99, "claims": ["c1"]}}
        with self.assertRaises(ValueError):
            validate_report_non_overclaim(p)

    def test_produce_receipt_valid(self):
        receipt = produce_decision_report_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "published")
        self.assertTrue(receipt["no_report_publication"])

    def test_produce_receipt_no_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"reviewed": False, "reviewer_id": ""}}
        receipt = produce_decision_report_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = DecisionReportReceipt(
            receipt_id="rid-1", decision_id="D-1", action="HOLD",
            evidence_links_present=True, confidence_rationale_present=True,
            friction_summary_present=True, human_review_present=True,
            overclaim_detected=False, status="published",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_report_publication)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_decision_report_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
