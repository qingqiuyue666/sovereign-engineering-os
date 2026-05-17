#!/usr/bin/env python3
"""Generate bounded local-only checkpoint runtime foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_checkpoint_runtime_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/checkpoint_runtime_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/checkpoint_runtime_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/checkpoint_runtime_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_checkpoint_runtime_foundation.py"

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
"""Generated bounded local-only checkpoint runtime foundation module.

v1 — contract-only. No real checkpoint mutation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class CheckpointRuntimeReceipt:
    receipt_id: str
    checkpoint_id: str
    source_revision: str
    content_hash: str
    rollback_reference: str
    scope_valid: bool
    integrity_valid: bool
    state_clean: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_checkpoint_mutation: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_checkpoint_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"checkpoint_id", "scope", "content_hash", "source_revision", "rollback_reference", "state_status", "approval"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("content_hash"):
        raise ValueError("checkpoint_without_hash")
    if not payload.get("source_revision"):
        raise ValueError("checkpoint_without_source_revision")
    if not payload.get("rollback_reference"):
        raise ValueError("checkpoint_without_rollback_reference")
    return {"valid": True, "checkpoint_id": payload["checkpoint_id"]}


def validate_checkpoint_scope(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    scope = payload.get("scope", {})
    if not isinstance(scope, dict):
        raise TypeError("scope must be a mapping")
    checks = {
        "paths_present": isinstance(scope.get("paths"), list) and len(scope.get("paths", [])) > 0,
        "module_present": bool(scope.get("module")),
    }
    valid = all(checks.values())
    return {"scope_valid": valid, "checks": checks}


def validate_checkpoint_integrity_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    ch = payload.get("content_hash", "")
    sr = payload.get("source_revision", "")
    rr = payload.get("rollback_reference", "")
    valid = all([
        isinstance(ch, str) and len(ch) == 64,
        isinstance(sr, str) and len(sr) > 0,
        isinstance(rr, str) and len(rr) > 0,
    ])
    return {"integrity_valid": valid}


def produce_checkpoint_runtime_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_checkpoint_request(payload)
    scope = validate_checkpoint_scope(payload)
    integrity = validate_checkpoint_integrity_contract(payload)
    state_status = payload.get("state_status", {})
    dirty = isinstance(state_status, dict) and state_status.get("dirty", True)
    unapproved = not (isinstance(state_status, dict) and state_status.get("approved", False))
    if dirty and unapproved:
        raise ValueError("checkpoint_on_dirty_unapproved_state")
    approval = payload.get("approval", {})
    approved = isinstance(approval, dict) and approval.get("approved", False)
    receipt = CheckpointRuntimeReceipt(
        receipt_id=_hash_id(payload.get("checkpoint_id", "unknown"), "v1"),
        checkpoint_id=payload.get("checkpoint_id", "unknown"),
        source_revision=payload.get("source_revision", ""),
        content_hash=payload.get("content_hash", ""),
        rollback_reference=payload.get("rollback_reference", ""),
        scope_valid=scope["scope_valid"],
        integrity_valid=integrity["integrity_valid"],
        state_clean=not dirty,
        status="created" if (scope["scope_valid"] and integrity["integrity_valid"] and approved and not dirty) else "rejected",
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "CheckpointRuntimeReceipt",
    "validate_checkpoint_request",
    "validate_checkpoint_scope",
    "validate_checkpoint_integrity_contract",
    "produce_checkpoint_runtime_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "checkpoint_runtime_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_checkpoint_runtime_foundation.py",
    "receipt_type": "CheckpointRuntimeReceipt",
    "functions": [
        "validate_checkpoint_request",
        "validate_checkpoint_scope",
        "validate_checkpoint_integrity_contract",
        "produce_checkpoint_runtime_receipt",
    ],
    "boundary": "local-only, no real checkpoint mutation in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "checkpoint_runtime_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "content_hash_required": True,
    "source_revision_required": True,
    "rollback_reference_required": True,
    "dirty_state_checkpoint_forbidden": True,
    "approval_required": True,
    "no_checkpoint_mutation_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Checkpoint Runtime Foundation v1

## Purpose
Bounded local-only checkpoint runtime foundation. Validates checkpoint
requests without creating real checkpoints.

## Boundaries
- no checkpoint without hash
- no checkpoint without source revision
- no checkpoint without rollback reference
- no checkpoint on dirty unapproved state
- no production mutation
- no real checkpoint mutation in v1

## Operations
1. validate_checkpoint_request — structural validation
2. validate_checkpoint_scope — scope completeness
3. validate_checkpoint_integrity_contract — hash integrity
4. produce_checkpoint_runtime_receipt — full receipt production

## Scope
Contract-only. Does not create real checkpoints.
"""

_TEST = r'''"""Tests for generated checkpoint runtime foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_checkpoint_runtime_foundation import (  # type: ignore[import-not-found]
    CheckpointRuntimeReceipt,
    validate_checkpoint_request,
    validate_checkpoint_scope,
    validate_checkpoint_integrity_contract,
    produce_checkpoint_runtime_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "checkpoint_id": "CKPT-001",
    "scope": {"paths": ["src/", "config/"], "module": "core"},
    "content_hash": VALID_SHA256,
    "source_revision": "abc123def456",
    "rollback_reference": "rollback-plan-001",
    "state_status": {"dirty": False, "approved": True},
    "approval": {"approved": True, "approver_id": "OP-001"},
}


class CheckpointRuntimeFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_checkpoint_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_checkpoint_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_checkpoint_request({})

    def test_validate_rejects_missing_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_rejects_missing_source_revision(self):
        p = {**VALID_PAYLOAD, "source_revision": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_rejects_missing_rollback(self):
        p = {**VALID_PAYLOAD, "rollback_reference": ""}
        with self.assertRaises(ValueError):
            validate_checkpoint_request(p)

    def test_validate_scope(self):
        result = validate_checkpoint_scope(VALID_PAYLOAD)
        self.assertTrue(result["scope_valid"])

    def test_validate_scope_empty_paths(self):
        p = {**VALID_PAYLOAD, "scope": {"paths": [], "module": "core"}}
        result = validate_checkpoint_scope(p)
        self.assertFalse(result["scope_valid"])

    def test_validate_integrity(self):
        result = validate_checkpoint_integrity_contract(VALID_PAYLOAD)
        self.assertTrue(result["integrity_valid"])

    def test_validate_integrity_bad_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": "short"}
        result = validate_checkpoint_integrity_contract(p)
        self.assertFalse(result["integrity_valid"])

    def test_produce_receipt_dirty_unapproved_rejected(self):
        p = {**VALID_PAYLOAD, "state_status": {"dirty": True, "approved": False}}
        with self.assertRaises(ValueError):
            produce_checkpoint_runtime_receipt(p)

    def test_produce_receipt_valid(self):
        receipt = produce_checkpoint_runtime_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "created")
        self.assertTrue(receipt["no_checkpoint_mutation"])

    def test_receipt_dataclass(self):
        r = CheckpointRuntimeReceipt(
            receipt_id="rid-1", checkpoint_id="C-1", source_revision="abc",
            content_hash=VALID_SHA256, rollback_reference="rr-1",
            scope_valid=True, integrity_valid=True, state_clean=True,
            status="created", created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_checkpoint_mutation)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_checkpoint_runtime_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
