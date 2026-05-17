#!/usr/bin/env python3
"""Generate bounded local-only recovery rollback foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

IRREVERSIBLE_OPERATIONS = frozenset({"DROP_TABLE", "DELETE_WAL", "PURGE_VAULT", "HARD_DELETE", "TRUNCATE"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_recovery_rollback_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/recovery_rollback_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/recovery_rollback_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/recovery_rollback_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_recovery_rollback_foundation.py"

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
"""Generated bounded local-only recovery rollback foundation module.

v1 — contract-only. No production mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

IRREVERSIBLE_OPERATIONS = frozenset({"DROP_TABLE", "DELETE_WAL", "PURGE_VAULT", "HARD_DELETE", "TRUNCATE"})


@dataclass(frozen=True)
class RecoveryRollbackReceipt:
    receipt_id: str
    recovery_id: str
    rollback_target: str
    failure_evidence_present: bool
    rollback_plan_valid: bool
    is_reversible: bool
    approval_gate_passed: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_mutation: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_recovery_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"recovery_id", "rollback_target", "failure_evidence", "rollback_plan", "approval", "operation_type"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    optype = payload.get("operation_type", "")
    if optype in IRREVERSIBLE_OPERATIONS:
        raise ValueError(f"irreversible_operation: {optype}")
    if not payload.get("rollback_target"):
        raise ValueError("rollback_target_is_required")
    return {"valid": True, "recovery_id": payload["recovery_id"]}


def validate_rollback_plan(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    plan = payload.get("rollback_plan", {})
    if not isinstance(plan, dict):
        raise TypeError("rollback_plan must be a mapping")
    checks = {
        "target_present": bool(plan.get("target")),
        "steps_present": isinstance(plan.get("steps"), list) and len(plan.get("steps", [])) > 0,
        "verification_present": bool(plan.get("verification")),
        "is_reversible": plan.get("reversible", False),
    }
    all_pass = checks["target_present"] and checks["steps_present"] and checks["verification_present"]
    return {"rollback_plan_valid": all_pass, "checks": checks, "is_reversible": checks["is_reversible"]}


def validate_failure_bundle_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    fb = payload.get("failure_evidence", {})
    if not isinstance(fb, dict):
        raise TypeError("failure_evidence must be a mapping")
    checks = {
        "error_message_present": bool(fb.get("error_message")),
        "timestamp_present": bool(fb.get("failure_timestamp")),
        "component_present": bool(fb.get("component")),
    }
    return {"failure_bundle_valid": all(checks.values()), "checks": checks}


def produce_recovery_rollback_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_recovery_request(payload)
    plan = validate_rollback_plan(payload)
    failure = validate_failure_bundle_contract(payload)
    approval = payload.get("approval", {})
    approved = isinstance(approval, dict) and approval.get("approved", False) and bool(approval.get("approver_id"))
    receipt = RecoveryRollbackReceipt(
        receipt_id=_hash_id(payload.get("recovery_id", "unknown"), _utcnow()),
        recovery_id=payload.get("recovery_id", "unknown"),
        rollback_target=payload.get("rollback_target", ""),
        failure_evidence_present=failure["failure_bundle_valid"],
        rollback_plan_valid=plan["rollback_plan_valid"],
        is_reversible=plan["is_reversible"],
        approval_gate_passed=approved,
        status="ready" if (plan["rollback_plan_valid"] and failure["failure_bundle_valid"] and approved) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "RecoveryRollbackReceipt",
    "validate_recovery_request",
    "validate_rollback_plan",
    "validate_failure_bundle_contract",
    "produce_recovery_rollback_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "recovery_rollback_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_recovery_rollback_foundation.py",
    "receipt_type": "RecoveryRollbackReceipt",
    "functions": [
        "validate_recovery_request",
        "validate_rollback_plan",
        "validate_failure_bundle_contract",
        "produce_recovery_rollback_receipt",
    ],
    "boundary": "local-only, no production mutation in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "recovery_rollback_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "irreversible_operations": sorted(IRREVERSIBLE_OPERATIONS),
    "rollback_target_required": True,
    "failure_evidence_required": True,
    "rollback_plan_required": True,
    "approval_required": True,
    "reversible_only_allowed": True,
    "no_production_mutation_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Recovery / Rollback Foundation v1

## Purpose
Bounded local-only recovery rollback foundation. Validates recovery
requests without performing any production mutation.

## Boundaries
- no missing rollback target
- no missing failure evidence
- no irreversible operation (DROP_TABLE, DELETE_WAL, PURGE_VAULT, HARD_DELETE, TRUNCATE)
- no production mutation
- no missing approval gate
- no real recovery execution in v1

## Operations
1. validate_recovery_request — structural validation
2. validate_rollback_plan — plan completeness
3. validate_failure_bundle_contract — failure evidence completeness
4. produce_recovery_rollback_receipt — full receipt production

## Scope
Contract-only. Does not perform any production mutation.
"""

_TEST = r'''"""Tests for generated recovery rollback foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_recovery_rollback_foundation import (  # type: ignore[import-not-found]
    RecoveryRollbackReceipt,
    validate_recovery_request,
    validate_rollback_plan,
    validate_failure_bundle_contract,
    produce_recovery_rollback_receipt,
)

VALID_PAYLOAD = {
    "recovery_id": "REC-001",
    "rollback_target": "checkpoint-20250101",
    "failure_evidence": {"error_message": "NullPointer in OrderService", "failure_timestamp": "2025-01-01T00:00:00Z", "component": "OrderService"},
    "rollback_plan": {"target": "checkpoint-20250101", "steps": ["stop_service", "restore_checkpoint", "verify_health", "resume"], "verification": "health_check.py", "reversible": True},
    "approval": {"approved": True, "approver_id": "OP-001", "approved_at": "2025-01-01T00:05:00Z"},
    "operation_type": "ROLLBACK",
}


class RecoveryRollbackFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_recovery_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_recovery_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_recovery_request({})

    def test_validate_rejects_irreversible(self):
        p = {**VALID_PAYLOAD, "operation_type": "DROP_TABLE"}
        with self.assertRaises(ValueError):
            validate_recovery_request(p)

    def test_validate_rejects_empty_target(self):
        p = {**VALID_PAYLOAD, "rollback_target": ""}
        with self.assertRaises(ValueError):
            validate_recovery_request(p)

    def test_validate_rollback_plan_valid(self):
        result = validate_rollback_plan(VALID_PAYLOAD)
        self.assertTrue(result["rollback_plan_valid"])
        self.assertTrue(result["is_reversible"])

    def test_validate_rollback_plan_irreversible(self):
        p = {**VALID_PAYLOAD, "rollback_plan": {**VALID_PAYLOAD["rollback_plan"], "reversible": False}}
        result = validate_rollback_plan(p)
        self.assertFalse(result["is_reversible"])

    def test_validate_rollback_plan_missing_steps(self):
        p = {**VALID_PAYLOAD, "rollback_plan": {"target": "x", "steps": [], "verification": "v", "reversible": True}}
        result = validate_rollback_plan(p)
        self.assertFalse(result["rollback_plan_valid"])

    def test_validate_failure_bundle(self):
        result = validate_failure_bundle_contract(VALID_PAYLOAD)
        self.assertTrue(result["failure_bundle_valid"])

    def test_validate_failure_bundle_incomplete(self):
        p = {**VALID_PAYLOAD, "failure_evidence": {"error_message": "err"}}
        result = validate_failure_bundle_contract(p)
        self.assertFalse(result["failure_bundle_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_recovery_rollback_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertTrue(receipt["no_mutation"])

    def test_produce_receipt_no_approval(self):
        p = {**VALID_PAYLOAD, "approval": {"approved": False, "approver_id": ""}}
        receipt = produce_recovery_rollback_receipt(p)
        self.assertEqual(receipt["status"], "rejected")

    def test_receipt_dataclass(self):
        r = RecoveryRollbackReceipt(
            receipt_id="rid-1", recovery_id="R-1", rollback_target="c1",
            failure_evidence_present=True, rollback_plan_valid=True,
            is_reversible=True, approval_gate_passed=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_mutation)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_recovery_rollback_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
