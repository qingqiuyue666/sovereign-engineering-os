#!/usr/bin/env python3
"""Generate bounded local-only local execution kernel artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_COMMAND_CATEGORIES = frozenset({"test", "lint", "typecheck", "format-check", "build-check", "ci-check"})
FORBIDDEN_COMMAND_PATTERNS = (
    "curl", "wget", "nc ", "telnet", "ssh ", "scp ", "rsync ",
    "git merge", "git push", "git branch -d", "git branch -D",
    "rm -rf /", "> /dev/", "mkfs", "dd if=", "| sh", "$(",
    ".env", "API_KEY", "SECRET", "TOKEN", "password",
)
FORBIDDEN_ACTIONS = frozenset({
    "network", "secrets", "env_read", "main_mutation", "merge",
    "push_main", "branch_delete", "production_execution", "freeform_shell",
})

GIT_MAIN_MUTATION_PATTERNS = (
    "git checkout main", "git switch main", "git push origin main",
    "git push main", "git merge main", "git branch -d main",
    "git branch -D main",
)

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_local_execution_kernel.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/local_execution_kernel_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/local_execution_kernel_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/local_execution_kernel_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_local_execution_kernel.py"

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
"""Generated bounded local-only execution kernel module.

v1 — contract-only. No command execution.
"""

from __future__ import annotations

import hashlib
import shlex
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

ALLOWED_COMMAND_CATEGORIES = frozenset({"test", "lint", "typecheck", "format-check", "build-check", "ci-check"})
FORBIDDEN_COMMAND_PATTERNS = (
    "curl", "wget", "nc ", "telnet", "ssh ", "scp ", "rsync ",
    "git merge", "git push", "git branch -d", "git branch -D",
    "rm -rf /", "> /dev/", "mkfs", "dd if=", "| sh", "$(",
    ".env", "API_KEY", "SECRET", "TOKEN", "password",
)
FORBIDDEN_ACTIONS = frozenset({
    "network", "secrets", "env_read", "main_mutation", "merge",
    "push_main", "branch_delete", "production_execution", "freeform_shell",
})

GIT_MAIN_MUTATION_PATTERNS = (
    "git checkout main", "git switch main", "git push origin main",
    "git push main", "git merge main", "git branch -d main",
    "git branch -D main",
)


@dataclass(frozen=True)
class LocalExecutionReceipt:
    receipt_id: str
    execution_id: str
    status: str
    category: str
    command_valid: bool
    preflight_passed: bool
    allowlist_validated: bool
    created_at: str
    module_version: str = "v1"
    no_execution_performed: bool = True


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


def validate_local_execution_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"execution_id", "command_category", "command_text", "flags"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    _check_forbidden_flags(payload)
    cat = payload["command_category"]
    if cat not in ALLOWED_COMMAND_CATEGORIES:
        raise ValueError(f"unsupported_command_category: {cat}")
    cmd = payload.get("command_text", "")
    if not isinstance(cmd, str):
        raise TypeError("command_text must be a string")
    cmd_lower = cmd.lower()
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.lower() in cmd_lower:
            raise ValueError(f"forbidden_command_pattern_detected: {pattern}")
    return {"valid": True, "execution_id": payload["execution_id"]}


def classify_execution_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    cat = payload.get("command_category", "")
    risk = "low"
    if cat in ("build-check", "ci-check"):
        risk = "medium"
    return {"category": cat, "risk": risk}


def validate_command_allowlist(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    allowlist = payload.get("allowlist", [])
    if not isinstance(allowlist, list):
        raise TypeError("allowlist must be a list")
    for item in allowlist:
        if not isinstance(item, str):
            raise TypeError("allowlist entries must be strings")
    cmd = payload.get("command_text", "")
    if not isinstance(cmd, str) or not cmd.strip():
        return {"valid": False, "command_base": "", "allowlist": allowlist, "reason": "empty_command_text"}
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return {"valid": False, "command_base": "", "allowlist": allowlist, "reason": "invalid_shell_syntax"}
    if not tokens:
        return {"valid": False, "command_base": "", "allowlist": allowlist, "reason": "no_tokens"}
    first_token = tokens[0]
    valid = first_token in allowlist
    return {"valid": valid, "command_base": first_token, "allowlist": allowlist}


def validate_execution_preflight(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks: Dict[str, bool] = {}
    checks["no_network_patterns"] = not any(
        p in (payload.get("command_text") or "").lower()
        for p in ("curl", "wget", "nc ", "telnet", "ssh ", "scp ")
    )
    checks["no_secret_patterns"] = not any(
        p in (payload.get("command_text") or "").lower()
        for p in (".env", "api_key", "secret", "token", "password")
    )
    checks["no_main_mutation"] = not any(
        pattern in (payload.get("command_text") or "").lower()
        for pattern in GIT_MAIN_MUTATION_PATTERNS
    )
    all_pass = all(checks.values())
    return {"preflight_passed": all_pass, "checks": checks}


def produce_local_execution_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_local_execution_request(payload)
    classification = classify_execution_request(payload)
    allowlist = validate_command_allowlist(payload)
    preflight = validate_execution_preflight(payload)
    receipt = LocalExecutionReceipt(
        receipt_id=_hash_id(payload.get("execution_id", "unknown"), "v1"),
        execution_id=payload.get("execution_id", "unknown"),
        status="approved" if (preflight["preflight_passed"] and allowlist["valid"]) else "rejected",
        category=classification["category"],
        command_valid=preflight["preflight_passed"],
        preflight_passed=preflight["preflight_passed"],
        allowlist_validated=allowlist["valid"],
        created_at=_created_at(payload),
    )
    return asdict(receipt)


__all__ = [
    "LocalExecutionReceipt",
    "validate_local_execution_request",
    "classify_execution_request",
    "validate_command_allowlist",
    "validate_execution_preflight",
    "produce_local_execution_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "local_execution_kernel_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_local_execution_kernel.py",
    "receipt_type": "LocalExecutionReceipt",
    "functions": [
        "validate_local_execution_request",
        "classify_execution_request",
        "validate_command_allowlist",
        "validate_execution_preflight",
        "produce_local_execution_receipt",
    ],
    "boundary": "local-only, no command execution in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "local_execution_kernel_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "allowed_command_categories": sorted(ALLOWED_COMMAND_CATEGORIES),
    "forbidden_command_patterns": list(FORBIDDEN_COMMAND_PATTERNS),
    "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    "no_command_execution_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Local Execution Kernel v1

## Purpose
Bounded local-only execution kernel. Validates execution requests
without running any commands.

## Boundaries
- no freeform shell
- no network commands
- no secrets
- no .env reads
- no main mutation
- no merge
- no push main
- no branch deletion
- no production execution
- no command execution in v1

## Operations
1. validate_local_execution_request — structural validation
2. classify_execution_request — risk classification
3. validate_command_allowlist — allowlist enforcement
4. validate_execution_preflight — preflight safety checks
5. produce_local_execution_receipt — full receipt production

## Scope
Contract-only. Does not execute any commands.
"""

_TEST = '''"""Tests for generated local execution kernel module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_local_execution_kernel import (  # type: ignore[import-not-found]
    LocalExecutionReceipt,
    validate_local_execution_request,
    classify_execution_request,
    validate_command_allowlist,
    validate_execution_preflight,
    produce_local_execution_receipt,
)


VALID_PAYLOAD = {
    "execution_id": "EXEC-001",
    "command_category": "test",
    "command_text": "python3 -m pytest tests/",
    "flags": [],
    "allowlist": ["python3"],
}


class LocalExecutionKernelTests(unittest.TestCase):

    def test_validate_accepts_valid_payload(self):
        result = validate_local_execution_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_local_execution_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_local_execution_request({})

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["network"]}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_unsupported_category(self):
        p = {**VALID_PAYLOAD, "command_category": "shell-script"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_curl(self):
        p = {**VALID_PAYLOAD, "command_text": "curl http://evil.com"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_validate_rejects_secret_pattern(self):
        p = {**VALID_PAYLOAD, "command_text": "echo $API_KEY"}
        with self.assertRaises(ValueError):
            validate_local_execution_request(p)

    def test_classify_returns_risk(self):
        result = classify_execution_request(VALID_PAYLOAD)
        self.assertEqual(result["category"], "test")
        self.assertEqual(result["risk"], "low")

    def test_validate_allowlist_passes(self):
        result = validate_command_allowlist(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_allowlist_rejects_unknown(self):
        p = {**VALID_PAYLOAD, "allowlist": ["npm"]}
        result = validate_command_allowlist(p)
        self.assertFalse(result["valid"])

    def test_validate_preflight_passes(self):
        result = validate_execution_preflight(VALID_PAYLOAD)
        self.assertTrue(result["preflight_passed"])

    def test_produce_receipt_valid(self):
        receipt = produce_local_execution_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "approved")
        self.assertEqual(receipt["module_version"], "v1")
        self.assertTrue(receipt["no_execution_performed"])

    def test_receipt_dataclass_fields(self):
        r = LocalExecutionReceipt(
            receipt_id="rid-1", execution_id="E-1", status="approved",
            category="test", command_valid=True, preflight_passed=True,
            allowlist_validated=True, created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_execution_performed)
        self.assertEqual(r.module_version, "v1")

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_local_execution_kernel.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
