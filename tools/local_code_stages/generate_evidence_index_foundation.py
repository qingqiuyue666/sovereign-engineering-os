#!/usr/bin/env python3
"""Generate bounded local-only evidence index foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONFLICT_POLICIES = frozenset({"REJECT_DUPLICATE", "OVERWRITE_OLDEST", "KEEP_NEWEST", "MANUAL_RESOLVE"})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_evidence_index_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/evidence_index_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/evidence_index_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/evidence_index_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_evidence_index_foundation.py"

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
"""Generated bounded local-only evidence index foundation module.

v1 — contract-only. No vault write.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

CONFLICT_POLICIES = frozenset({"REJECT_DUPLICATE", "OVERWRITE_OLDEST", "KEEP_NEWEST", "MANUAL_RESOLVE"})


@dataclass(frozen=True)
class EvidenceIndexReceipt:
    receipt_id: str
    artifact_id: str
    content_hash: str
    index_key: str
    conflict_policy: str
    lookup_valid: bool
    consistency_valid: bool
    is_duplicate: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_vault_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_evidence_index_entry(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"artifact_id", "content_hash", "index_key", "conflict_policy"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    if not payload.get("artifact_id"):
        raise ValueError("missing_artifact_id")
    if not payload.get("content_hash"):
        raise ValueError("missing_content_hash")
    if not payload.get("index_key"):
        raise ValueError("missing_index_key")
    cp = payload.get("conflict_policy", "")
    if cp not in CONFLICT_POLICIES:
        raise ValueError(f"unsupported_conflict_policy: {cp}")
    return {"valid": True, "artifact_id": payload["artifact_id"]}


def validate_evidence_lookup_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    aid = payload.get("artifact_id", "")
    ik = payload.get("index_key", "")
    ch = payload.get("content_hash", "")
    valid = all([isinstance(aid, str) and len(aid) > 0,
                 isinstance(ik, str) and len(ik) > 0,
                 isinstance(ch, str) and len(ch) == 64])
    return {"lookup_valid": valid}


def validate_index_consistency_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    is_dup = payload.get("is_duplicate", False)
    cp = payload.get("conflict_policy", "")
    if is_dup and cp == "REJECT_DUPLICATE":
        raise ValueError("duplicate_rejected_by_policy")
    if is_dup and cp not in CONFLICT_POLICIES:
        raise ValueError("duplicate_without_explicit_conflict_policy")
    return {"is_duplicate": is_dup, "conflict_policy": cp, "consistent": not (is_dup and cp == "REJECT_DUPLICATE")}


def produce_evidence_index_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_evidence_index_entry(payload)
    lookup = validate_evidence_lookup_contract(payload)
    consistency = validate_index_consistency_contract(payload)
    receipt = EvidenceIndexReceipt(
        receipt_id=_hash_id(payload.get("artifact_id", "unknown"), _utcnow()),
        artifact_id=payload.get("artifact_id", "unknown"),
        content_hash=payload.get("content_hash", ""),
        index_key=payload.get("index_key", ""),
        conflict_policy=payload.get("conflict_policy", "REJECT_DUPLICATE"),
        lookup_valid=lookup["lookup_valid"],
        consistency_valid=consistency["consistent"],
        is_duplicate=consistency["is_duplicate"],
        status="indexed" if (lookup["lookup_valid"] and consistency["consistent"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "EvidenceIndexReceipt",
    "validate_evidence_index_entry",
    "validate_evidence_lookup_contract",
    "validate_index_consistency_contract",
    "produce_evidence_index_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "evidence_index_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_evidence_index_foundation.py",
    "receipt_type": "EvidenceIndexReceipt",
    "functions": [
        "validate_evidence_index_entry",
        "validate_evidence_lookup_contract",
        "validate_index_consistency_contract",
        "produce_evidence_index_receipt",
    ],
    "boundary": "local-only, no vault write in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "evidence_index_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "conflict_policies": sorted(CONFLICT_POLICIES),
    "artifact_id_required": True,
    "content_hash_required": True,
    "index_key_required": True,
    "duplicate_without_policy_forbidden": True,
    "no_vault_write_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Evidence Index Foundation v1

## Purpose
Bounded local-only evidence index foundation. Validates index entries
without writing to any vault.

## Boundaries
- no missing artifact id
- no missing content hash
- no missing index key
- no duplicate without explicit conflict policy
- no live vault write
- no vault write in v1

## Operations
1. validate_evidence_index_entry — structural validation
2. validate_evidence_lookup_contract — lookup key integrity
3. validate_index_consistency_contract — duplicate handling
4. produce_evidence_index_receipt — full receipt production

## Scope
Contract-only. Does not write to any vault.
"""

_TEST = r'''"""Tests for generated evidence index foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_evidence_index_foundation import (  # type: ignore[import-not-found]
    EvidenceIndexReceipt,
    validate_evidence_index_entry,
    validate_evidence_lookup_contract,
    validate_index_consistency_contract,
    produce_evidence_index_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "artifact_id": "ART-001",
    "content_hash": VALID_SHA256,
    "index_key": "idx-run-001-stage-002",
    "conflict_policy": "KEEP_NEWEST",
    "is_duplicate": False,
}


class EvidenceIndexFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_evidence_index_entry(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_evidence_index_entry("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_evidence_index_entry({})

    def test_validate_rejects_missing_artifact_id(self):
        p = {**VALID_PAYLOAD, "artifact_id": ""}
        with self.assertRaises(ValueError):
            validate_evidence_index_entry(p)

    def test_validate_rejects_bad_conflict_policy(self):
        p = {**VALID_PAYLOAD, "conflict_policy": "SILENT_OVERWRITE"}
        with self.assertRaises(ValueError):
            validate_evidence_index_entry(p)

    def test_validate_lookup_contract(self):
        result = validate_evidence_lookup_contract(VALID_PAYLOAD)
        self.assertTrue(result["lookup_valid"])

    def test_validate_lookup_contract_bad_hash(self):
        p = {**VALID_PAYLOAD, "content_hash": "short"}
        result = validate_evidence_lookup_contract(p)
        self.assertFalse(result["lookup_valid"])

    def test_validate_consistency_duplicate_reject(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "REJECT_DUPLICATE"}
        with self.assertRaises(ValueError):
            validate_index_consistency_contract(p)

    def test_validate_consistency_duplicate_keep_newest(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "KEEP_NEWEST"}
        result = validate_index_consistency_contract(p)
        self.assertTrue(result["is_duplicate"])

    def test_produce_receipt_valid(self):
        receipt = produce_evidence_index_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "indexed")
        self.assertTrue(receipt["no_vault_write"])

    def test_produce_receipt_duplicate_rejected(self):
        p = {**VALID_PAYLOAD, "is_duplicate": True, "conflict_policy": "REJECT_DUPLICATE"}
        with self.assertRaises(ValueError):
            produce_evidence_index_receipt(p)

    def test_receipt_dataclass(self):
        r = EvidenceIndexReceipt(
            receipt_id="rid-1", artifact_id="A-1", content_hash=VALID_SHA256,
            index_key="ik-1", conflict_policy="KEEP_NEWEST",
            lookup_valid=True, consistency_valid=True,
            is_duplicate=False, status="indexed",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_vault_write)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_evidence_index_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
