#!/usr/bin/env python3
"""Generate bounded local-only run ledger hardening foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_STATUSES = frozenset({"pending", "running", "completed", "failed", "rolled_back", "cancelled"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_run_ledger_hardening_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/run_ledger_hardening_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/run_ledger_hardening_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/run_ledger_hardening_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_run_ledger_hardening_foundation.py"

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
"""Generated bounded local-only run ledger hardening foundation module.

v1 — contract-only. No mutable ledger claim.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

ALLOWED_STATUSES = frozenset({"pending", "running", "completed", "failed", "rolled_back", "cancelled"})
VALID_TRANSITIONS = {
    "pending": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": {"rolled_back"},
    "failed": {"rolled_back", "pending"},
    "rolled_back": set(),
    "cancelled": set(),
}
FORBIDDEN_TRANSITIONS = frozenset({"completed_to_running", "rolled_back_to_running", "completed_to_pending"})


@dataclass(frozen=True)
class RunLedgerReceipt:
    receipt_id: str
    run_id: str
    operator_id: str
    status: str
    previous_status: str
    transition_valid: bool
    sequence_valid: bool
    evidence_link_present: bool
    mutable_claim: bool
    created_at: str
    module_version: str = "v1"
    no_ledger_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_run_ledger_entry(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"run_id", "operator_id", "status", "previous_status", "sequence_number", "evidence_link"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("run_id"):
        raise ValueError("missing_run_id")
    if not payload.get("operator_id"):
        raise ValueError("missing_operator_id")
    status = payload["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid_status: {status}")
    return {"valid": True, "run_id": payload["run_id"]}


def validate_run_sequence_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    seq = payload.get("sequence_number", 0)
    if not isinstance(seq, (int, float)):
        raise TypeError("sequence_number must be numeric")
    return {"sequence_valid": seq > 0, "sequence_number": seq}


def validate_run_status_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    current = payload.get("status", "")
    previous = payload.get("previous_status", "")
    valid = False
    if previous in VALID_TRANSITIONS:
        valid = current in VALID_TRANSITIONS[previous]
    return {
        "transition_valid": valid,
        "current": current,
        "previous": previous,
        "forbidden": f"{previous}_to_{current}" in FORBIDDEN_TRANSITIONS,
    }


def produce_run_ledger_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_run_ledger_entry(payload)
    seq_check = validate_run_sequence_contract(payload)
    status_check = validate_run_status_contract(payload)
    mutable = payload.get("mutable_ledger", False)
    if mutable:
        raise ValueError("mutable_ledger_claim_rejected")
    receipt = RunLedgerReceipt(
        receipt_id=_hash_id(payload.get("run_id", "unknown"), _utcnow()),
        run_id=payload.get("run_id", "unknown"),
        operator_id=payload.get("operator_id", "unknown"),
        status=payload.get("status", ""),
        previous_status=payload.get("previous_status", ""),
        transition_valid=status_check["transition_valid"],
        sequence_valid=seq_check["sequence_valid"],
        evidence_link_present=bool(payload.get("evidence_link")),
        mutable_claim=mutable,
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "RunLedgerReceipt",
    "validate_run_ledger_entry",
    "validate_run_sequence_contract",
    "validate_run_status_contract",
    "produce_run_ledger_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "run_ledger_hardening_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_run_ledger_hardening_foundation.py",
    "receipt_type": "RunLedgerReceipt",
    "functions": [
        "validate_run_ledger_entry",
        "validate_run_sequence_contract",
        "validate_run_status_contract",
        "produce_run_ledger_receipt",
    ],
    "boundary": "local-only, no ledger write in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "run_ledger_hardening_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_statuses": sorted(ALLOWED_STATUSES),
    "mutable_ledger_forbidden": True,
    "run_id_required": True,
    "operator_id_required": True,
    "valid_transition_required": True,
    "evidence_link_required": True,
    "no_ledger_write_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Run Ledger Hardening Foundation v1

## Purpose
Bounded local-only run ledger hardening foundation. Validates ledger
entries without writing to any ledger.

## Boundaries
- no missing run id
- no missing operator id
- no missing status
- no invalid transition
- no mutable ledger claim
- no missing evidence link
- no ledger write in v1

## Valid Status Transitions
pending → running, cancelled
running → completed, failed, cancelled
completed → rolled_back
failed → rolled_back, pending

## Operations
1. validate_run_ledger_entry — structural validation
2. validate_run_sequence_contract — sequence number check
3. validate_run_status_contract — transition validity
4. produce_run_ledger_receipt — full receipt production

## Scope
Contract-only. Does not write to any ledger.
"""

_TEST = r'''"""Tests for generated run ledger hardening foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_run_ledger_hardening_foundation import (  # type: ignore[import-not-found]
    RunLedgerReceipt,
    validate_run_ledger_entry,
    validate_run_sequence_contract,
    validate_run_status_contract,
    produce_run_ledger_receipt,
)

VALID_PAYLOAD = {
    "run_id": "RUN-001",
    "operator_id": "OP-001",
    "status": "running",
    "previous_status": "pending",
    "sequence_number": 5,
    "evidence_link": "evid-link-001",
    "mutable_ledger": False,
}


class RunLedgerHardeningFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_run_ledger_entry(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_run_ledger_entry("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_run_ledger_entry({})

    def test_validate_rejects_missing_run_id(self):
        p = {**VALID_PAYLOAD, "run_id": ""}
        with self.assertRaises(ValueError):
            validate_run_ledger_entry(p)

    def test_validate_rejects_invalid_status(self):
        p = {**VALID_PAYLOAD, "status": "magic_status"}
        with self.assertRaises(ValueError):
            validate_run_ledger_entry(p)

    def test_validate_sequence_contract(self):
        result = validate_run_sequence_contract(VALID_PAYLOAD)
        self.assertTrue(result["sequence_valid"])

    def test_validate_sequence_zero(self):
        p = {**VALID_PAYLOAD, "sequence_number": 0}
        result = validate_run_sequence_contract(p)
        self.assertFalse(result["sequence_valid"])

    def test_validate_transition_valid(self):
        result = validate_run_status_contract(VALID_PAYLOAD)
        self.assertTrue(result["transition_valid"])

    def test_validate_transition_invalid(self):
        p = {**VALID_PAYLOAD, "status": "pending", "previous_status": "completed"}
        result = validate_run_status_contract(p)
        self.assertFalse(result["transition_valid"])

    def test_validate_transition_completed_to_running_invalid(self):
        p = {**VALID_PAYLOAD, "status": "running", "previous_status": "completed"}
        result = validate_run_status_contract(p)
        self.assertFalse(result["transition_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_run_ledger_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "running")
        self.assertTrue(receipt["transition_valid"])
        self.assertTrue(receipt["no_ledger_write"])

    def test_produce_receipt_rejects_mutable(self):
        p = {**VALID_PAYLOAD, "mutable_ledger": True}
        with self.assertRaises(ValueError):
            produce_run_ledger_receipt(p)

    def test_receipt_dataclass(self):
        r = RunLedgerReceipt(
            receipt_id="rid-1", run_id="R-1", operator_id="OP-1",
            status="running", previous_status="pending",
            transition_valid=True, sequence_valid=True,
            evidence_link_present=True, mutable_claim=False,
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_ledger_write)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_run_ledger_hardening_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
