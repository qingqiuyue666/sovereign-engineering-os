#!/usr/bin/env python3
"""Generate bounded local-only patch application pipeline artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_ACTIONS = frozenset({
    "git_merge", "git_push_main", "git_branch_delete",
    "main_branch_modification", "deployment", "production_execution",
})
ALLOWED_PATCH_MODES = frozenset({"dry-run", "staged-review", "approved-only"})
FORBIDDEN_ROOTS = frozenset({"/", "/etc", "/proc", "/sys", "/dev", "/tmp", "/var"})
FORBIDDEN_PATH_PATTERNS = ("..", "~", "$", "`", "|", ";", "&", "\n", "\r")

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_patch_application_pipeline.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/patch_application_pipeline_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/patch_application_pipeline_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/patch_application_pipeline_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_patch_application_pipeline.py"

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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        receipt_id=_hash_id(payload.get("patch_id", "unknown"), _utcnow()),
        patch_id=payload.get("patch_id", "unknown"),
        status="approved" if (preflight["preflight_passed"] and allowlist["valid"] and risk["risk"] != "rejected") else "rejected",
        risk_classification=risk["risk"],
        preflight_passed=preflight["preflight_passed"],
        allowlist_validated=allowlist["valid"],
        diff_summary=payload.get("diff_summary", ""),
        rollback_plan_present=bool(payload.get("rollback_plan")),
        tests_present=bool(payload.get("tests")),
        created_at=_utcnow(),
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
'''

_REGISTRY = json.dumps({
    "registry_name": "patch_application_pipeline_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_patch_application_pipeline.py",
    "receipt_type": "PatchApplicationReceipt",
    "functions": [
        "validate_patch_application_request",
        "classify_patch_risk",
        "validate_patch_allowlist",
        "validate_patch_preflight",
        "produce_patch_application_receipt",
    ],
    "boundary": "local-only, no real patch application in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "patch_application_pipeline_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_patch_modes": ["dry-run", "staged-review", "approved-only"],
    "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    "forbidden_roots": sorted(FORBIDDEN_ROOTS),
    "forbidden_path_patterns": list(FORBIDDEN_PATH_PATTERNS),
    "no_real_patch_application_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Patch Application Pipeline v1

## Purpose
Bounded local-only patch application pipeline. Validates patch requests
without applying them to the real repository.

## Boundaries
- no freeform shell
- no git mutation
- no main mutation
- no absolute paths
- no path traversal
- no forbidden roots
- no deployment
- no production execution
- no real patch application in v1

## Operations
1. validate_patch_application_request — structural validation
2. classify_patch_risk — risk classification
3. validate_patch_allowlist — allowlist enforcement
4. validate_patch_preflight — preflight checks
5. produce_patch_application_receipt — full receipt production

## Scope
Contract-only. Does not implement production runtime behavior.
"""

_TEST = '''"""Tests for generated patch application pipeline module."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_patch_application_pipeline import (  # type: ignore[import-not-found]
    PatchApplicationReceipt,
    validate_patch_application_request,
    classify_patch_risk,
    validate_patch_allowlist,
    validate_patch_preflight,
    produce_patch_application_receipt,
)


VALID_PAYLOAD = {
    "patch_id": "PATCH-001",
    "target_files": ["src/app/main.py", "src/lib/utils.py"],
    "diff_summary": "Fix typo in main.py, update util",
    "rollback_plan": "git revert PATCH-001",
    "tests": ["test_main.py", "test_utils.py"],
    "patch_mode": "dry-run",
    "flags": [],
    "allowlist": ["src/app/main.py", "src/lib/utils.py"],
}


class PatchApplicationPipelineTests(unittest.TestCase):

    def test_validate_accepts_valid_payload(self):
        result = validate_patch_application_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_patch_application_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_patch_application_request({})

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["git_merge"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_unsupported_patch_mode(self):
        p = {**VALID_PAYLOAD, "patch_mode": "unsafe-force-push"}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_absolute_path(self):
        p = {**VALID_PAYLOAD, "target_files": ["/etc/passwd"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_validate_rejects_path_traversal(self):
        p = {**VALID_PAYLOAD, "target_files": ["../../../etc/passwd"]}
        with self.assertRaises(ValueError):
            validate_patch_application_request(p)

    def test_classify_patch_risk_low_for_normal(self):
        result = classify_patch_risk(VALID_PAYLOAD)
        self.assertEqual(result["risk"], "low")

    def test_classify_patch_risk_high_for_security_paths(self):
        p = {**VALID_PAYLOAD, "target_files": ["src/security/auth.py"]}
        result = classify_patch_risk(p)
        self.assertEqual(result["risk"], "high")

    def test_classify_patch_risk_rejected_for_bad_mode(self):
        p = {**VALID_PAYLOAD, "patch_mode": "invalid"}
        result = classify_patch_risk(p)
        self.assertEqual(result["risk"], "rejected")

    def test_validate_allowlist_passes(self):
        result = validate_patch_allowlist(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_allowlist_rejects_unknown_file(self):
        p = {**VALID_PAYLOAD, "allowlist": ["src/app/main.py"]}
        result = validate_patch_allowlist(p)
        self.assertFalse(result["valid"])
        self.assertIn("src/lib/utils.py", result["violations"])

    def test_validate_preflight_passes(self):
        result = validate_patch_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_validate_preflight_fails_missing_tests(self):
        p = {**VALID_PAYLOAD, "tests": []}
        result = validate_patch_preflight(p)
        self.assertFalse(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_patch_application_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_side_effects"])

    def test_produce_receipt_rejected_missing_fields(self):
        with self.assertRaises(ValueError):
            produce_patch_application_receipt({"patch_id": "only-id"})

    def test_receipt_dataclass_fields(self):
        r = PatchApplicationReceipt(
            receipt_id="rid-1", patch_id="P-1", status="approved",
            risk_classification="low", preflight_passed=True,
            allowlist_validated=True, diff_summary="x", rollback_plan_present=True,
            tests_present=True, created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_side_effects)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_patch_application_pipeline.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import http.client", src)
        self.assertNotIn("import urllib.request", src)

    def test_no_forbidden_strings_in_module(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_patch_application_pipeline.py") as f:
            src = f.read()
        for forbidden in ["cloud_ai", "API_KEY", ".env", "push main", "merge main", "branch delete"]:
            self.assertNotIn(forbidden, src.lower() if forbidden != ".env" else src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
