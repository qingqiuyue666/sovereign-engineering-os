
"""Generated bounded local-only patch application pipeline module.

v1 — contract-only. No real repository patch application.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── allowed constants ──────────────────────────────────────────────
ALLOWED_PATCH_MODES = frozenset({"dry-run", "staged-review", "approved-only"})
FORBIDDEN_ROOTS = frozenset({"/", "/etc", "/proc", "/sys", "/dev", "/tmp", "/var"})
FORBIDDEN_PATH_PATTERNS = ("..", "~", "$", "`", "|", ";", "&", "\n", "\r")
FORBIDDEN_ACTIONS = frozenset({
    "git_merge", "git_push_main", "git_branch_delete",
    "main_branch_modification", "deployment", "production_execution",
})


@dataclass(frozen=True)
class PatchApplicationReceipt:
    receipt_id: str
    patch_id: str
    status: str
    risk_classification: str
    preflight_passed: bool
    allowlist_validated: bool
    diff_summary: str
    rollback_plan_present: bool
    tests_present: bool
    created_at: str
    module_version: str = "v1"
    no_side_effects: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _created_at(payload: Dict[str, Any]) -> str:
    value = payload.get("created_at")
    return value if isinstance(value, str) and value.strip() else "1970-01-01T00:00:00Z"



def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def _check_forbidden_flags(payload: Dict[str, Any]) -> None:
    flags = payload.get("flags", [])
    if not isinstance(flags, list):
        raise TypeError("flags must be a list")
    for f in flags:
        if not isinstance(f, str):
            raise TypeError("each flag must be a string")
        if f in FORBIDDEN_ACTIONS:
            raise ValueError(f"forbidden_flag: {f}")


def validate_patch_application_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"patch_id", "target_files", "diff_summary", "rollback_plan", "tests", "patch_mode", "flags"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    _check_forbidden_flags(payload)
    mode = payload["patch_mode"]
    if mode not in ALLOWED_PATCH_MODES:
        raise ValueError(f"unsupported_patch_mode: {mode}")
    files = payload.get("target_files", [])
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise TypeError("target_files must be a list of strings")
    for f in files:
        if any(p in f for p in FORBIDDEN_PATH_PATTERNS):
            raise ValueError(f"path_traversal_rejected: {f}")
        if f.startswith("/"):
            raise ValueError(f"absolute_path_rejected: {f}")
    return {"valid": True, "patch_id": payload["patch_id"]}


def classify_patch_risk(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    risk = "low"
    reasons: List[str] = []
    files = payload.get("target_files", [])
    if not files:
        reasons.append("zero-target-files")
        risk = "high"
    if any("security" in f.lower() or "auth" in f.lower() for f in files):
        risk = "high"
        reasons.append("security-sensitive-paths")
    if payload.get("patch_mode") not in ALLOWED_PATCH_MODES:
        risk = "rejected"
        reasons.append("unsupported-patch-mode")
    return {"risk": risk, "reasons": reasons}


def validate_patch_allowlist(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    allowlist = payload.get("allowlist", [])
    if not isinstance(allowlist, list):
        raise TypeError("allowlist must be a list")
    for item in allowlist:
        if not isinstance(item, str):
            raise TypeError("allowlist entries must be strings")
    targets = set(payload.get("target_files", []))
    allowed_set = set(allowlist)
    violations = targets - allowed_set
    return {"valid": len(violations) == 0, "violations": sorted(violations)}


def validate_patch_preflight(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks: Dict[str, bool] = {}
    checks["diff_summary_present"] = bool(payload.get("diff_summary"))
    checks["rollback_plan_present"] = bool(payload.get("rollback_plan"))
    checks["tests_present"] = bool(payload.get("tests"))
    checks["patch_mode_valid"] = payload.get("patch_mode") in ALLOWED_PATCH_MODES
    all_pass = all(checks.values())
    return {"preflight_passed": all_pass, "checks": checks}


def produce_patch_application_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_patch_application_request(payload)
    risk = classify_patch_risk(payload)
    allowlist = validate_patch_allowlist(payload)
    preflight = validate_patch_preflight(payload)
    receipt = PatchApplicationReceipt(
        receipt_id=_hash_id(payload.get("patch_id", "unknown"), "v1"),
        patch_id=payload.get("patch_id", "unknown"),
        status="approved" if (preflight["preflight_passed"] and allowlist["valid"] and risk["risk"] != "rejected") else "rejected",
        risk_classification=risk["risk"],
        preflight_passed=preflight["preflight_passed"],
        allowlist_validated=allowlist["valid"],
        diff_summary=payload.get("diff_summary", ""),
        rollback_plan_present=bool(payload.get("rollback_plan")),
        tests_present=bool(payload.get("tests")),
        created_at=_created_at(payload),
    )
    return asdict(receipt)


# ── boundary assertion ────────────────────────────────────────────
__all__ = [
    "PatchApplicationReceipt",
    "validate_patch_application_request",
    "classify_patch_risk",
    "validate_patch_allowlist",
    "validate_patch_preflight",
    "produce_patch_application_receipt",
]
