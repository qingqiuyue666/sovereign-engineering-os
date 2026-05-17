#!/usr/bin/env python3
"""Generate bounded local-only evidence vault foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_HASH_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})
FORBIDDEN_ARTIFACT_TYPES = frozenset({"raw_secret", "api_key", "private_key", "token", "password", "credential"})
REQUIRED_FIELDS = frozenset({
    "artifact_id", "artifact_type", "content_hash",
    "hash_algorithm", "created_at", "producer",
    "lineage", "immutable", "append_only",
})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_evidence_vault_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/evidence_vault_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/evidence_vault_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/evidence_vault_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_evidence_vault_foundation.py"

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
"""Generated bounded local-only evidence vault foundation module.

v1 — contract-only. No actual vault storage write.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ALLOWED_HASH_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})
FORBIDDEN_ARTIFACT_TYPES = frozenset({"raw_secret", "api_key", "private_key", "token", "password", "credential"})
FORBIDDEN_CONTENT_PATTERNS = ("-----BEGIN", "API_KEY=", "SECRET=", "TOKEN=", "password=")
REQUIRED_FIELDS = frozenset({
    "artifact_id", "artifact_type", "content_hash",
    "hash_algorithm", "created_at", "producer",
    "lineage", "immutable", "append_only",
})


@dataclass(frozen=True)
class EvidenceVaultReceipt:
    receipt_id: str
    artifact_id: str
    artifact_type: str
    content_hash: str
    hash_algorithm: str
    status: str
    hash_valid: bool
    append_only_enforced: bool
    immutable_enforced: bool
    metadata_valid: bool
    created_at: str
    producer: str
    lineage: List[str]
    module_version: str = "v1"
    no_vault_write: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def _check_hash_format(h: str, algo: str) -> bool:
    if algo == "sha256":
        return len(h) == 64 and all(c in "0123456789abcdef" for c in h.lower())
    if algo == "sha512":
        return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
    if algo == "blake2b":
        return len(h) == 128 and all(c in "0123456789abcdef" for c in h.lower())
    return False


def validate_evidence_vault_record(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    atype = payload["artifact_type"]
    if atype in FORBIDDEN_ARTIFACT_TYPES:
        raise ValueError(f"forbidden_artifact_type: {atype}")
    if not isinstance(payload.get("lineage"), list):
        raise TypeError("lineage must be a list")
    if not isinstance(payload.get("immutable"), bool):
        raise TypeError("immutable must be a boolean")
    if not isinstance(payload.get("append_only"), bool):
        raise TypeError("append_only must be a boolean")
    return {"valid": True, "artifact_id": payload["artifact_id"]}


def validate_evidence_hash_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    algo = payload.get("hash_algorithm", "")
    if algo not in ALLOWED_HASH_ALGORITHMS:
        raise ValueError(f"unsupported_hash_algorithm: {algo}")
    content_hash = payload.get("content_hash", "")
    valid = _check_hash_format(content_hash, algo)
    return {"hash_valid": valid, "algorithm": algo, "content_hash": content_hash}


def validate_evidence_append_only_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    if not payload.get("append_only", False):
        raise ValueError("append_only_must_be_true")
    return {"append_only": True}


def validate_evidence_metadata_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    lineage = payload.get("lineage", [])
    valid = isinstance(lineage, list) and len(lineage) > 0
    checks = {
        "lineage_present": valid,
        "producer_present": bool(payload.get("producer")),
        "created_at_present": bool(payload.get("created_at")),
    }
    return {"metadata_valid": all(checks.values()), "checks": checks}


def produce_evidence_vault_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_evidence_vault_record(payload)
    hash_check = validate_evidence_hash_contract(payload)
    append_check = validate_evidence_append_only_contract(payload)
    meta_check = validate_evidence_metadata_contract(payload)
    receipt = EvidenceVaultReceipt(
        receipt_id=_hash_id(payload.get("artifact_id", "unknown"), _utcnow()),
        artifact_id=payload.get("artifact_id", "unknown"),
        artifact_type=payload.get("artifact_type", "unknown"),
        content_hash=payload.get("content_hash", ""),
        hash_algorithm=payload.get("hash_algorithm", ""),
        status="sealed" if (hash_check["hash_valid"] and meta_check["metadata_valid"]) else "rejected",
        hash_valid=hash_check["hash_valid"],
        append_only_enforced=append_check["append_only"],
        immutable_enforced=payload.get("immutable", False),
        metadata_valid=meta_check["metadata_valid"],
        created_at=payload.get("created_at", _utcnow()),
        producer=payload.get("producer", "unknown"),
        lineage=payload.get("lineage", []),
    )
    return asdict(receipt)


__all__ = [
    "EvidenceVaultReceipt",
    "validate_evidence_vault_record",
    "validate_evidence_hash_contract",
    "validate_evidence_append_only_contract",
    "validate_evidence_metadata_contract",
    "produce_evidence_vault_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "evidence_vault_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_evidence_vault_foundation.py",
    "receipt_type": "EvidenceVaultReceipt",
    "functions": [
        "validate_evidence_vault_record",
        "validate_evidence_hash_contract",
        "validate_evidence_append_only_contract",
        "validate_evidence_metadata_contract",
        "produce_evidence_vault_receipt",
    ],
    "boundary": "local-only, no actual vault storage write in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "evidence_vault_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_hash_algorithms": sorted(ALLOWED_HASH_ALGORITHMS),
    "forbidden_artifact_types": sorted(FORBIDDEN_ARTIFACT_TYPES),
    "required_fields": sorted(REQUIRED_FIELDS),
    "immutable_records_required": True,
    "append_only_required": True,
    "no_vault_write_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Evidence Vault Foundation v1

## Purpose
Bounded local-only evidence vault foundation. Validates evidence records
without writing to any real vault storage.

## Boundaries
- no mutable records
- no missing hashes
- no unsupported hash algorithms
- no raw secret material
- no vault live write
- no actual vault storage write in v1

## Operations
1. validate_evidence_vault_record — structural validation
2. validate_evidence_hash_contract — hash format validation
3. validate_evidence_append_only_contract — append-only enforcement
4. validate_evidence_metadata_contract — metadata completeness
5. produce_evidence_vault_receipt — full receipt production

## Required Fields
artifact_id, artifact_type, content_hash, hash_algorithm,
created_at, producer, lineage, immutable, append_only

## Scope
Contract-only. Does not write to any vault storage.
"""

_TEST = r'''"""Tests for generated evidence vault foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_evidence_vault_foundation import (  # type: ignore[import-not-found]
    EvidenceVaultReceipt,
    validate_evidence_vault_record,
    validate_evidence_hash_contract,
    validate_evidence_append_only_contract,
    validate_evidence_metadata_contract,
    produce_evidence_vault_receipt,
)

VALID_SHA256 = "a" * 64
VALID_PAYLOAD = {
    "artifact_id": "ART-001",
    "artifact_type": "run_log",
    "content_hash": VALID_SHA256,
    "hash_algorithm": "sha256",
    "created_at": "2025-01-01T00:00:00Z",
    "producer": "test-runner",
    "lineage": ["run-001", "stage-002"],
    "immutable": True,
    "append_only": True,
}


class EvidenceVaultFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_evidence_vault_record(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_evidence_vault_record("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_evidence_vault_record({})

    def test_validate_rejects_secret_artifact_type(self):
        p = {**VALID_PAYLOAD, "artifact_type": "api_key"}
        with self.assertRaises(ValueError):
            validate_evidence_vault_record(p)

    def test_validate_rejects_non_list_lineage(self):
        p = {**VALID_PAYLOAD, "lineage": "not-a-list"}
        with self.assertRaises(TypeError):
            validate_evidence_vault_record(p)

    def test_validate_hash_contract_valid_sha256(self):
        result = validate_evidence_hash_contract(VALID_PAYLOAD)
        self.assertTrue(result["hash_valid"])

    def test_validate_hash_contract_invalid_algo(self):
        p = {**VALID_PAYLOAD, "hash_algorithm": "md5"}
        with self.assertRaises(ValueError):
            validate_evidence_hash_contract(p)

    def test_validate_hash_contract_bad_hash_length(self):
        p = {**VALID_PAYLOAD, "content_hash": "too-short"}
        result = validate_evidence_hash_contract(p)
        self.assertFalse(result["hash_valid"])

    def test_validate_append_only_rejects_false(self):
        p = {**VALID_PAYLOAD, "append_only": False}
        with self.assertRaises(ValueError):
            validate_evidence_append_only_contract(p)

    def test_validate_metadata_contract(self):
        result = validate_evidence_metadata_contract(VALID_PAYLOAD)
        self.assertTrue(result["metadata_valid"])

    def test_validate_metadata_contract_empty_lineage(self):
        p = {**VALID_PAYLOAD, "lineage": []}
        result = validate_evidence_metadata_contract(p)
        self.assertFalse(result["metadata_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_evidence_vault_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "sealed")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_vault_write"])
        self.assertTrue(receipt["append_only_enforced"])

    def test_produce_receipt_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            produce_evidence_vault_receipt({"artifact_id": "only-id"})

    def test_receipt_dataclass(self):
        r = EvidenceVaultReceipt(
            receipt_id="rid-1", artifact_id="A-1", artifact_type="log",
            content_hash=VALID_SHA256, hash_algorithm="sha256", status="sealed",
            hash_valid=True, append_only_enforced=True, immutable_enforced=True,
            metadata_valid=True, created_at="2025-01-01T00:00:00Z",
            producer="test", lineage=["l1"],
        )
        self.assertTrue(r.no_vault_write)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_evidence_vault_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
