#!/usr/bin/env python3
"""Generate bounded local-only decision engine foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE", "SHORT", "COVER"})
MIN_CONFIDENCE_THRESHOLD = 0.70

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_decision_engine_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/decision_engine_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/decision_engine_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/decision_engine_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_decision_engine_foundation.py"

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
"""Generated bounded local-only decision engine foundation module.

v1 — contract-only. No real trade execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

ALLOWED_ACTIONS = frozenset({"HOLD", "FLAG", "ESCALATE", "REVIEW"})
FORBIDDEN_ACTIONS = frozenset({"BUY", "SELL", "EXECUTE", "ORDER", "TRADE", "SHORT", "COVER"})
MIN_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class DecisionEngineReceipt:
    receipt_id: str
    decision_id: str
    action: str
    confidence: float
    confidence_gate_passed: bool
    friction_gate_passed: bool
    single_action_enforced: bool
    human_review_present: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_execution: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_decision_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"decision_id", "actions", "confidence", "friction_data", "human_review", "evidence_refs"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    actions = payload.get("actions", [])
    if not isinstance(actions, list):
        raise TypeError("actions must be a list")
    if len(actions) == 0:
        raise ValueError("actions_must_not_be_empty")
    return {"valid": True, "decision_id": payload["decision_id"]}


def validate_single_action_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    actions = payload.get("actions", [])
    if len(actions) > 1:
        raise ValueError("multiple_actions_forbidden")
    if not actions:
        raise ValueError("no_action_specified")
    action = actions[0]
    if not isinstance(action, str):
        raise TypeError("action must be a string")
    if action in FORBIDDEN_ACTIONS:
        raise ValueError(f"forbidden_action: {action}")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported_action: {action}")
    return {"action": action, "single_action": True}


def validate_confidence_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    conf = payload.get("confidence", 0.0)
    if not isinstance(conf, (int, float)):
        raise TypeError("confidence must be numeric")
    overclaim = conf > 0.95
    if overclaim:
        raise ValueError(f"confidence_overclaim: {conf}")
    passed = conf >= MIN_CONFIDENCE_THRESHOLD
    return {"confidence": conf, "gate_passed": passed, "overclaim": overclaim}


def validate_friction_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    fd = payload.get("friction_data", {})
    if not isinstance(fd, dict):
        raise TypeError("friction_data must be a mapping")
    checks = {
        "spread_present": "spread" in fd or "slippage" in fd or "impact" in fd,
        "venue_present": "venue" in fd,
    }
    passed = all(checks.values())
    return {"friction_gate_passed": passed, "checks": checks}


def produce_decision_engine_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_decision_request(payload)
    action_check = validate_single_action_contract(payload)
    conf_check = validate_confidence_gate(payload)
    friction_check = validate_friction_gate(payload)
    hr = payload.get("human_review", {})
    has_review = isinstance(hr, dict) and hr.get("reviewed", False) and bool(hr.get("reviewer_id"))
    receipt = DecisionEngineReceipt(
        receipt_id=_hash_id(payload.get("decision_id", "unknown"), _utcnow()),
        decision_id=payload.get("decision_id", "unknown"),
        action=action_check["action"],
        confidence=conf_check["confidence"],
        confidence_gate_passed=conf_check["gate_passed"],
        friction_gate_passed=friction_check["friction_gate_passed"],
        single_action_enforced=action_check["single_action"],
        human_review_present=has_review,
        status="approved" if (conf_check["gate_passed"] and friction_check["friction_gate_passed"] and has_review) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "DecisionEngineReceipt",
    "validate_decision_request",
    "validate_single_action_contract",
    "validate_confidence_gate",
    "validate_friction_gate",
    "produce_decision_engine_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "decision_engine_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_decision_engine_foundation.py",
    "receipt_type": "DecisionEngineReceipt",
    "functions": [
        "validate_decision_request",
        "validate_single_action_contract",
        "validate_confidence_gate",
        "validate_friction_gate",
        "produce_decision_engine_receipt",
    ],
    "boundary": "local-only, no real trade execution in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "decision_engine_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_actions": sorted(ALLOWED_ACTIONS),
    "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    "min_confidence_threshold": MIN_CONFIDENCE_THRESHOLD,
    "max_confidence": 0.95,
    "single_action_only": True,
    "human_review_required": True,
    "friction_data_required": True,
    "no_real_trade_execution_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Decision Engine Foundation v1

## Purpose
Bounded local-only decision engine foundation. Validates decision
requests without executing trades.

## Boundaries
- no multiple actions
- no confidence overclaim (max 0.95)
- no offensive action when confidence below threshold (0.70)
- no missing friction fields
- no missing human review
- no production order execution
- no real trade execution in v1

## Allowed Actions
HOLD, FLAG, ESCALATE, REVIEW

## Forbidden Actions
BUY, SELL, EXECUTE, ORDER, TRADE, SHORT, COVER

## Operations
1. validate_decision_request — structural validation
2. validate_single_action_contract — single action enforcement
3. validate_confidence_gate — confidence threshold gate
4. validate_friction_gate — friction data gate
5. produce_decision_engine_receipt — full receipt production

## Scope
Contract-only. Does not execute any trades.
"""

_TEST = r'''"""Tests for generated decision engine foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_decision_engine_foundation import (  # type: ignore[import-not-found]
    DecisionEngineReceipt,
    validate_decision_request,
    validate_single_action_contract,
    validate_confidence_gate,
    validate_friction_gate,
    produce_decision_engine_receipt,
)

VALID_PAYLOAD = {
    "decision_id": "DEC-001",
    "actions": ["HOLD"],
    "confidence": 0.85,
    "friction_data": {"spread": 0.01, "venue": "NYSE"},
    "human_review": {"reviewed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T00:00:00Z"},
    "evidence_refs": ["evid-001"],
}


class DecisionEngineFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_decision_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_decision_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_decision_request({})

    def test_validate_rejects_empty_actions(self):
        p = {**VALID_PAYLOAD, "actions": []}
        with self.assertRaises(ValueError):
            validate_decision_request(p)

    def test_validate_single_action_rejects_multiple(self):
        p = {**VALID_PAYLOAD, "actions": ["HOLD", "FLAG"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_single_action_rejects_buy(self):
        p = {**VALID_PAYLOAD, "actions": ["BUY"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_single_action_rejects_trade(self):
        p = {**VALID_PAYLOAD, "actions": ["TRADE"]}
        with self.assertRaises(ValueError):
            validate_single_action_contract(p)

    def test_validate_confidence_gate_passes(self):
        result = validate_confidence_gate(VALID_PAYLOAD)
        self.assertTrue(result["gate_passed"])

    def test_validate_confidence_gate_below_threshold(self):
        p = {**VALID_PAYLOAD, "confidence": 0.50}
        result = validate_confidence_gate(p)
        self.assertFalse(result["gate_passed"])

    def test_validate_confidence_overclaim(self):
        p = {**VALID_PAYLOAD, "confidence": 0.99}
        with self.assertRaises(ValueError):
            validate_confidence_gate(p)

    def test_validate_friction_gate_passes(self):
        result = validate_friction_gate(VALID_PAYLOAD)
        self.assertTrue(result["friction_gate_passed"])

    def test_validate_friction_gate_missing_venue(self):
        p = {**VALID_PAYLOAD, "friction_data": {"spread": 0.01}}
        result = validate_friction_gate(p)
        self.assertFalse(result["friction_gate_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_decision_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertTrue(receipt["no_execution"])

    def test_produce_receipt_no_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"reviewed": False, "reviewer_id": ""}}
        receipt = produce_decision_engine_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = DecisionEngineReceipt(
            receipt_id="rid-1", decision_id="D-1", action="HOLD",
            confidence=0.85, confidence_gate_passed=True,
            friction_gate_passed=True, single_action_enforced=True,
            human_review_present=True, status="approved",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_decision_engine_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
