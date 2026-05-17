
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


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



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
        receipt_id=_hash_id(payload.get("pack_version", "v1"), "v1"),
        pack_version=payload.get("pack_version", "v1"),
        total_stages=len(stage_ids),
        stages_indexed=stage_ids,
        test_coverage_valid=coverage["test_coverage_valid"],
        all_entries_valid=True,
        status="complete" if coverage["test_coverage_valid"] else "incomplete",
        created_at=_created_at(payload),
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
