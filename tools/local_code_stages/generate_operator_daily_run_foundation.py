#!/usr/bin/env python3
"""Generate bounded local-only operator daily run foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_operator_daily_run_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/operator_daily_run_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/operator_daily_run_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/operator_daily_run_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_operator_daily_run_foundation.py"

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
"""Generated bounded local-only operator daily run foundation module.

v1 — contract-only. No real execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class OperatorDailyRunReceipt:
    receipt_id: str
    run_id: str
    operator_id: str
    runbook_reference: str
    evidence_summary_present: bool
    human_review_completed: bool
    approval_gate_passed: bool
    run_window_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_execution_performed: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_operator_daily_run_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"run_id", "operator_id", "runbook_reference", "evidence_summary", "human_review", "approval", "run_window"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not isinstance(payload.get("human_review"), dict):
        raise TypeError("human_review must be a mapping")
    hr = payload["human_review"]
    if not hr.get("completed", False):
        raise ValueError("human_review_not_completed")
    if not hr.get("reviewer_id"):
        raise ValueError("human_review_missing_reviewer_id")
    return {"valid": True, "run_id": payload["run_id"]}


def validate_operator_run_window(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    window = payload.get("run_window", {})
    if not isinstance(window, dict):
        raise TypeError("run_window must be a mapping")
    start = window.get("start", "")
    end = window.get("end", "")
    valid = bool(start and end and start < end)
    return {"run_window_valid": valid, "start": start, "end": end}


def validate_operator_review_gate(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    approval = payload.get("approval", {})
    if not isinstance(approval, dict):
        raise TypeError("approval must be a mapping")
    checks = {
        "operator_approved": approval.get("operator_approved", False),
        "approver_id_present": bool(approval.get("approver_id")),
        "approval_timestamp_present": bool(approval.get("approval_timestamp")),
    }
    all_pass = all(checks.values())
    return {"approval_gate_passed": all_pass, "checks": checks}


def produce_operator_daily_run_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_operator_daily_run_request(payload)
    window = validate_operator_run_window(payload)
    review = validate_operator_review_gate(payload)
    receipt = OperatorDailyRunReceipt(
        receipt_id=_hash_id(payload.get("run_id", "unknown"), _utcnow()),
        run_id=payload.get("run_id", "unknown"),
        operator_id=payload.get("operator_id", "unknown"),
        runbook_reference=payload.get("runbook_reference", ""),
        evidence_summary_present=bool(payload.get("evidence_summary")),
        human_review_completed=payload.get("human_review", {}).get("completed", False),
        approval_gate_passed=review["approval_gate_passed"],
        run_window_valid=window["run_window_valid"],
        status="approved" if (review["approval_gate_passed"] and window["run_window_valid"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "OperatorDailyRunReceipt",
    "validate_operator_daily_run_request",
    "validate_operator_run_window",
    "validate_operator_review_gate",
    "produce_operator_daily_run_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "operator_daily_run_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_operator_daily_run_foundation.py",
    "receipt_type": "OperatorDailyRunReceipt",
    "functions": [
        "validate_operator_daily_run_request",
        "validate_operator_run_window",
        "validate_operator_review_gate",
        "produce_operator_daily_run_receipt",
    ],
    "boundary": "local-only, no real execution in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "operator_daily_run_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "human_review_required": True,
    "runbook_reference_required": True,
    "evidence_summary_required": True,
    "approval_required": True,
    "autonomous_production_action_forbidden": True,
    "no_real_execution_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Operator Daily Run Foundation v1

## Purpose
Bounded local-only operator daily run foundation. Validates daily run
requests without executing any actions.

## Boundaries
- no autonomous production action
- no missing human review
- no missing runbook reference
- no missing evidence summary
- no action without approval
- no real execution in v1

## Operations
1. validate_operator_daily_run_request — structural validation
2. validate_operator_run_window — window validation
3. validate_operator_review_gate — review gate validation
4. produce_operator_daily_run_receipt — full receipt production

## Scope
Contract-only. Does not execute any actions.
"""

_TEST = r'''"""Tests for generated operator daily run foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_operator_daily_run_foundation import (  # type: ignore[import-not-found]
    OperatorDailyRunReceipt,
    validate_operator_daily_run_request,
    validate_operator_run_window,
    validate_operator_review_gate,
    produce_operator_daily_run_receipt,
)

VALID_PAYLOAD = {
    "run_id": "RUN-001",
    "operator_id": "OP-001",
    "runbook_reference": "docs/runbooks/daily_v1.md",
    "evidence_summary": "All checks green, 3 decisions reviewed.",
    "human_review": {"completed": True, "reviewer_id": "OP-001", "reviewed_at": "2025-01-01T09:00:00Z"},
    "approval": {"operator_approved": True, "approver_id": "OP-001", "approval_timestamp": "2025-01-01T09:05:00Z"},
    "run_window": {"start": "2025-01-01T08:00:00Z", "end": "2025-01-01T18:00:00Z"},
}


class OperatorDailyRunFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_operator_daily_run_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_operator_daily_run_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request({})

    def test_validate_rejects_incomplete_review(self):
        p = {**VALID_PAYLOAD, "human_review": {"completed": False, "reviewer_id": "OP-001"}}
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request(p)

    def test_validate_rejects_missing_reviewer(self):
        p = {**VALID_PAYLOAD, "human_review": {"completed": True, "reviewer_id": ""}}
        with self.assertRaises(ValueError):
            validate_operator_daily_run_request(p)

    def test_validate_run_window_valid(self):
        result = validate_operator_run_window(VALID_PAYLOAD)
        self.assertTrue(result["run_window_valid"])

    def test_validate_run_window_invalid(self):
        p = {**VALID_PAYLOAD, "run_window": {"start": "2025-01-01T18:00:00Z", "end": "2025-01-01T08:00:00Z"}}
        result = validate_operator_run_window(p)
        self.assertFalse(result["run_window_valid"])

    def test_validate_review_gate_passes(self):
        result = validate_operator_review_gate(VALID_PAYLOAD)
        self.assertTrue(result["approval_gate_passed"])

    def test_validate_review_gate_fails_no_approval(self):
        p = {**VALID_PAYLOAD, "approval": {"operator_approved": False, "approver_id": "", "approval_timestamp": ""}}
        result = validate_operator_review_gate(p)
        self.assertFalse(result["approval_gate_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_operator_daily_run_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_execution_performed"])

    def test_receipt_dataclass(self):
        r = OperatorDailyRunReceipt(
            receipt_id="rid-1", run_id="R-1", operator_id="OP-1",
            runbook_reference="x", evidence_summary_present=True,
            human_review_completed=True, approval_gate_passed=True,
            run_window_valid=True, status="approved",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution_performed)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_operator_daily_run_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
