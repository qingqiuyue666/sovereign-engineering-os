#!/usr/bin/env python3
"""Generate bounded local-only stage pack manifest index artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_stage_pack_manifest_index.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/stage_pack_manifest_index_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/stage_pack_manifest_index_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/stage_pack_manifest_index_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_stage_pack_manifest_index.py"

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


_STAGE_IDS = [
    "patch_application_pipeline",
    "local_execution_kernel",
    "evidence_vault_foundation",
    "replay_engine_foundation",
    "provider_transport_boundary",
    "operator_daily_run_foundation",
    "alert_delivery_foundation",
    "osint_ingestion_foundation",
    "asset_mapping_foundation",
    "decision_engine_foundation",
    "recovery_rollback_foundation",
    "checkpoint_runtime_foundation",
    "run_ledger_hardening_foundation",
    "evidence_index_foundation",
    "decision_report_foundation",
    "local_operator_cli_extension_foundation",
]

_MODULE = r'''
"""Generated bounded local-only stage pack manifest index module.

v1 — catalogs all stages in this production pack.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

STAGE_IDS = [
    "patch_application_pipeline",
    "local_execution_kernel",
    "evidence_vault_foundation",
    "replay_engine_foundation",
    "provider_transport_boundary",
    "operator_daily_run_foundation",
    "alert_delivery_foundation",
    "osint_ingestion_foundation",
    "asset_mapping_foundation",
    "decision_engine_foundation",
    "recovery_rollback_foundation",
    "checkpoint_runtime_foundation",
    "run_ledger_hardening_foundation",
    "evidence_index_foundation",
    "decision_report_foundation",
    "local_operator_cli_extension_foundation",
]

REQUIRED_ARTIFACTS_PER_STAGE = [
    "generated_module",
    "registry",
    "policy",
    "runbook",
    "test",
]


@dataclass(frozen=True)
class StagePackManifestReceipt:
    receipt_id: str
    pack_version: str
    total_stages: int
    stages_indexed: List[str]
    test_coverage_valid: bool
    all_entries_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_stage_pack_manifest(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"pack_version", "stages"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    stages = payload.get("stages", [])
    if not isinstance(stages, list) or len(stages) == 0:
        raise ValueError("stages_must_be_non_empty_list")
    return {"valid": True, "stage_count": len(stages)}


def validate_stage_pack_entry(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"stage_id", "artifacts", "test_coverage"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    sid = payload["stage_id"]
    if sid not in STAGE_IDS:
        raise ValueError(f"unknown_stage_id: {sid}")
    artifacts = payload.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise TypeError("artifacts must be a list")
    return {"stage_id": sid, "artifacts_count": len(artifacts)}


def validate_stage_pack_test_coverage(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    stages = payload.get("stages", [])
    covered = 0
    uncovered: List[str] = []
    for stage in stages:
        tc = stage.get("test_coverage", False)
        if tc:
            covered += 1
        else:
            uncovered.append(stage.get("stage_id", "unknown"))
    all_covered = len(uncovered) == 0
    return {"test_coverage_valid": all_covered, "covered": covered, "total": len(stages), "uncovered": uncovered}


def produce_stage_pack_manifest_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_stage_pack_manifest(payload)
    for stage in payload.get("stages", []):
        validate_stage_pack_entry(stage)
    coverage = validate_stage_pack_test_coverage(payload)
    stage_ids = [s.get("stage_id", "unknown") for s in payload.get("stages", [])]
    receipt = StagePackManifestReceipt(
        receipt_id=_hash_id(payload.get("pack_version", "v1"), _utcnow()),
        pack_version=payload.get("pack_version", "v1"),
        total_stages=len(stage_ids),
        stages_indexed=stage_ids,
        test_coverage_valid=coverage["test_coverage_valid"],
        all_entries_valid=True,
        status="complete" if coverage["test_coverage_valid"] else "incomplete",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "StagePackManifestReceipt",
    "validate_stage_pack_manifest",
    "validate_stage_pack_entry",
    "validate_stage_pack_test_coverage",
    "produce_stage_pack_manifest_receipt",
    "STAGE_IDS",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "stage_pack_manifest_index_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_stage_pack_manifest_index.py",
    "receipt_type": "StagePackManifestReceipt",
    "functions": [
        "validate_stage_pack_manifest",
        "validate_stage_pack_entry",
        "validate_stage_pack_test_coverage",
        "produce_stage_pack_manifest_receipt",
    ],
    "stages_indexed": _STAGE_IDS,
    "total_stages": len(_STAGE_IDS),
    "boundary": "local-only, catalogs all production stages",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "stage_pack_manifest_index_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "stages_required": len(_STAGE_IDS),
    "stage_ids": _STAGE_IDS,
    "artifacts_per_stage": ["generated_module", "registry", "policy", "runbook", "test"],
    "test_coverage_required": True,
    "all_stages_must_be_indexed": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Stage Pack Manifest Index v1

## Purpose
Catalogs all 16 stages in the production code stage pack v1.

## Indexed Stages
1. patch_application_pipeline
2. local_execution_kernel
3. evidence_vault_foundation
4. replay_engine_foundation
5. provider_transport_boundary
6. operator_daily_run_foundation
7. alert_delivery_foundation
8. osint_ingestion_foundation
9. asset_mapping_foundation
10. decision_engine_foundation
11. recovery_rollback_foundation
12. checkpoint_runtime_foundation
13. run_ledger_hardening_foundation
14. evidence_index_foundation
15. decision_report_foundation
16. local_operator_cli_extension_foundation

## Per-Stage Artifacts
- generated_module
- registry
- policy
- runbook
- test

## Operations
1. validate_stage_pack_manifest — structural validation
2. validate_stage_pack_entry — per-stage validation
3. validate_stage_pack_test_coverage — coverage check
4. produce_stage_pack_manifest_receipt — full receipt production

## Scope
Catalog only. All stages are contract-only in v1.
"""

_TEST = r'''"""Tests for generated stage pack manifest index module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_stage_pack_manifest_index import (  # type: ignore[import-not-found]
    StagePackManifestReceipt,
    validate_stage_pack_manifest,
    validate_stage_pack_entry,
    validate_stage_pack_test_coverage,
    produce_stage_pack_manifest_receipt,
    STAGE_IDS,
)

VALID_STAGE = {
    "stage_id": "patch_application_pipeline",
    "artifacts": ["generated_module", "registry", "policy", "runbook", "test"],
    "test_coverage": True,
}

VALID_PAYLOAD = {
    "pack_version": "v1",
    "stages": [
        {"stage_id": sid, "artifacts": ["generated_module", "registry", "policy", "runbook", "test"], "test_coverage": True}
        for sid in STAGE_IDS
    ],
}


class StagePackManifestIndexTests(unittest.TestCase):

    def test_stage_ids_list(self):
        self.assertEqual(len(STAGE_IDS), 16)

    def test_validate_manifest_accepts_valid(self):
        result = validate_stage_pack_manifest(VALID_PAYLOAD)
        self.assertTrue(result["valid"])
        self.assertEqual(result["stage_count"], 16)

    def test_validate_manifest_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_stage_pack_manifest("not a dict")

    def test_validate_manifest_rejects_empty_stages(self):
        p = {"pack_version": "v1", "stages": []}
        with self.assertRaises(ValueError):
            validate_stage_pack_manifest(p)

    def test_validate_entry_accepts_valid(self):
        result = validate_stage_pack_entry(VALID_STAGE)
        self.assertEqual(result["stage_id"], "patch_application_pipeline")

    def test_validate_entry_rejects_unknown_stage(self):
        p = {"stage_id": "magic_unknown_stage", "artifacts": [], "test_coverage": False}
        with self.assertRaises(ValueError):
            validate_stage_pack_entry(p)

    def test_validate_test_coverage_all_covered(self):
        result = validate_stage_pack_test_coverage(VALID_PAYLOAD)
        self.assertTrue(result["test_coverage_valid"])
        self.assertEqual(result["covered"], 16)

    def test_validate_test_coverage_partial(self):
        stages = [
            {"stage_id": sid, "artifacts": [], "test_coverage": i % 2 == 0}
            for i, sid in enumerate(STAGE_IDS)
        ]
        result = validate_stage_pack_test_coverage({"pack_version": "v1", "stages": stages})
        self.assertFalse(result["test_coverage_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_stage_pack_manifest_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["total_stages"], 16)

    def test_receipt_dataclass(self):
        r = StagePackManifestReceipt(
            receipt_id="rid-1", pack_version="v1", total_stages=16,
            stages_indexed=STAGE_IDS[:2], test_coverage_valid=True,
            all_entries_valid=True, status="complete",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_stage_pack_manifest_index.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
