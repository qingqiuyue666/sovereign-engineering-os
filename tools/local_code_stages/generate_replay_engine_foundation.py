#!/usr/bin/env python3
"""Generate bounded local-only replay engine foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FIELDS = frozenset({
    "replay_anchor_id", "input_snapshot_hash", "policy_version",
    "code_version", "environment_fingerprint", "deterministic_mode",
    "no_cloud_requery",
})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_replay_engine_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/replay_engine_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/replay_engine_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/replay_engine_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_replay_engine_foundation.py"

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
"""Generated bounded local-only replay engine foundation module.

v1 — contract-only. No actual replay execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = frozenset({
    "replay_anchor_id", "input_snapshot_hash", "policy_version",
    "code_version", "environment_fingerprint", "deterministic_mode",
    "no_cloud_requery",
})


@dataclass(frozen=True)
class ReplayEngineReceipt:
    receipt_id: str
    replay_anchor_id: str
    input_snapshot_hash: str
    policy_version: str
    code_version: str
    environment_fingerprint: str
    deterministic_mode: bool
    no_cloud_requery: bool
    anchor_valid: bool
    snapshot_valid: bool
    version_tuple_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_replay_execution: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_replay_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not isinstance(payload.get("deterministic_mode"), bool):
        raise TypeError("deterministic_mode must be a boolean")
    if not isinstance(payload.get("no_cloud_requery"), bool):
        raise TypeError("no_cloud_requery must be a boolean")
    if not payload.get("no_cloud_requery", False):
        raise ValueError("no_cloud_requery_must_be_true_for_replay")
    return {"valid": True, "replay_anchor_id": payload["replay_anchor_id"]}


def validate_replay_anchor_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    anchor = payload.get("replay_anchor_id", "")
    valid = isinstance(anchor, str) and len(anchor) > 0
    return {"anchor_valid": valid, "replay_anchor_id": anchor}


def validate_replay_input_snapshot_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    snap = payload.get("input_snapshot_hash", "")
    valid = isinstance(snap, str) and len(snap) == 64
    if not valid and len(snap) > 0:
        raise ValueError("input_snapshot_hash_must_be_sha256_hex_64_chars")
    return {"snapshot_valid": valid, "input_snapshot_hash": snap}


def validate_replay_version_tuple(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    pv = payload.get("policy_version", "")
    cv = payload.get("code_version", "")
    ef = payload.get("environment_fingerprint", "")
    valid = all(isinstance(v, str) and len(v) > 0 for v in (pv, cv, ef))
    return {"version_tuple_valid": valid, "policy_version": pv, "code_version": cv, "environment_fingerprint": ef}


def produce_replay_engine_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_replay_request(payload)
    anchor = validate_replay_anchor_contract(payload)
    snapshot = validate_replay_input_snapshot_contract(payload)
    version = validate_replay_version_tuple(payload)
    receipt = ReplayEngineReceipt(
        receipt_id=_hash_id(payload.get("replay_anchor_id", "unknown"), _utcnow()),
        replay_anchor_id=payload.get("replay_anchor_id", "unknown"),
        input_snapshot_hash=payload.get("input_snapshot_hash", ""),
        policy_version=payload.get("policy_version", ""),
        code_version=payload.get("code_version", ""),
        environment_fingerprint=payload.get("environment_fingerprint", ""),
        deterministic_mode=payload.get("deterministic_mode", True),
        no_cloud_requery=payload.get("no_cloud_requery", True),
        anchor_valid=anchor["anchor_valid"],
        snapshot_valid=snapshot["snapshot_valid"],
        version_tuple_valid=version["version_tuple_valid"],
        status="ready" if (anchor["anchor_valid"] and snapshot["snapshot_valid"] and version["version_tuple_valid"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "ReplayEngineReceipt",
    "validate_replay_request",
    "validate_replay_anchor_contract",
    "validate_replay_input_snapshot_contract",
    "validate_replay_version_tuple",
    "produce_replay_engine_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "replay_engine_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_replay_engine_foundation.py",
    "receipt_type": "ReplayEngineReceipt",
    "functions": [
        "validate_replay_request",
        "validate_replay_anchor_contract",
        "validate_replay_input_snapshot_contract",
        "validate_replay_version_tuple",
        "produce_replay_engine_receipt",
    ],
    "boundary": "local-only, no actual replay execution in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "replay_engine_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "required_fields": sorted(REQUIRED_FIELDS),
    "cloud_requery_forbidden": True,
    "deterministic_mode_required": True,
    "no_replay_execution_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Replay Engine Foundation v1

## Purpose
Bounded local-only replay engine foundation. Validates replay requests
without executing any replays.

## Boundaries
- no cloud re-query as exact replay
- no missing input snapshot
- no missing version tuple
- no nondeterministic replay claim
- no production mutation
- no actual replay execution in v1

## Required Fields
replay_anchor_id, input_snapshot_hash, policy_version,
code_version, environment_fingerprint, deterministic_mode,
no_cloud_requery

## Operations
1. validate_replay_request — structural validation
2. validate_replay_anchor_contract — anchor integrity
3. validate_replay_input_snapshot_contract — snapshot hash validation
4. validate_replay_version_tuple — version completeness
5. produce_replay_engine_receipt — full receipt production

## Scope
Contract-only. Does not execute any replays.
"""

_TEST = r'''"""Tests for generated replay engine foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_replay_engine_foundation import (  # type: ignore[import-not-found]
    ReplayEngineReceipt,
    validate_replay_request,
    validate_replay_anchor_contract,
    validate_replay_input_snapshot_contract,
    validate_replay_version_tuple,
    produce_replay_engine_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "replay_anchor_id": "ANCHOR-001",
    "input_snapshot_hash": VALID_SHA256,
    "policy_version": "v1.0.0",
    "code_version": "abc123def456",
    "environment_fingerprint": "env-hash-001",
    "deterministic_mode": True,
    "no_cloud_requery": True,
}


class ReplayEngineFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_replay_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_replay_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_replay_request({})

    def test_validate_rejects_cloud_requery_false(self):
        p = {**VALID_PAYLOAD, "no_cloud_requery": False}
        with self.assertRaises(ValueError):
            validate_replay_request(p)

    def test_validate_anchor_contract(self):
        result = validate_replay_anchor_contract(VALID_PAYLOAD)
        self.assertTrue(result["anchor_valid"])

    def test_validate_anchor_contract_empty(self):
        p = {**VALID_PAYLOAD, "replay_anchor_id": ""}
        result = validate_replay_anchor_contract(p)
        self.assertFalse(result["anchor_valid"])

    def test_validate_snapshot_contract(self):
        result = validate_replay_input_snapshot_contract(VALID_PAYLOAD)
        self.assertTrue(result["snapshot_valid"])

    def test_validate_snapshot_contract_bad_length(self):
        p = {**VALID_PAYLOAD, "input_snapshot_hash": "too-short"}
        with self.assertRaises(ValueError):
            validate_replay_input_snapshot_contract(p)

    def test_validate_version_tuple(self):
        result = validate_replay_version_tuple(VALID_PAYLOAD)
        self.assertTrue(result["version_tuple_valid"])

    def test_validate_version_tuple_missing(self):
        p = {**VALID_PAYLOAD, "policy_version": ""}
        result = validate_replay_version_tuple(p)
        self.assertFalse(result["version_tuple_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_replay_engine_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_replay_execution"])

    def test_produce_receipt_rejects_missing(self):
        with self.assertRaises(ValueError):
            produce_replay_engine_receipt({"replay_anchor_id": "only-id"})

    def test_receipt_dataclass(self):
        r = ReplayEngineReceipt(
            receipt_id="rid-1", replay_anchor_id="A-1", input_snapshot_hash=VALID_SHA256,
            policy_version="v1", code_version="abc", environment_fingerprint="env",
            deterministic_mode=True, no_cloud_requery=True, anchor_valid=True,
            snapshot_valid=True, version_tuple_valid=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_replay_execution)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_replay_engine_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
