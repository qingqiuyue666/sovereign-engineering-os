#!/usr/bin/env python3
"""Generate bounded local-only operator CLI extension foundation artifacts.

No cloud AI, no secrets, no shell, no git mutation, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REGISTERED_COMMANDS = frozenset({
    "status", "health", "review", "approve", "reject", "list",
    "report", "checkpoint", "rollback", "evidence", "index", "run",
})
FORBIDDEN_COMMANDS = frozenset({
    "exec", "shell", "bash", "sh", "eval", "system", "sudo",
    "curl", "wget", "ssh", "scp", "nc", "telnet",
})
FORBIDDEN_ACTIONS = frozenset({
    "network", "secret_read", "main_mutation", "production_execution",
    "push_main", "merge", "branch_delete", "freeform_shell",
})

OUTPUT_MODULE = ROOT / "tools/local_code_stages/generated_local_operator_cli_extension_foundation.py"
OUTPUT_REGISTRY = ROOT / "governance/local_train/local_operator_cli_extension_foundation_registry_v1.json"
OUTPUT_POLICY = ROOT / "governance/security/local_operator_cli_extension_foundation_policy_v1.json"
OUTPUT_RUNBOOK = ROOT / "docs/runbooks/local_operator_cli_extension_foundation_v1.md"
OUTPUT_TEST = ROOT / "tests/tracer_bullet/test_local_operator_cli_extension_foundation.py"

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
"""Generated bounded local-only operator CLI extension foundation module.

v1 — contract-only. No actual CLI execution.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

REGISTERED_COMMANDS = frozenset({
    "status", "health", "review", "approve", "reject", "list",
    "report", "checkpoint", "rollback", "evidence", "index", "run",
})
FORBIDDEN_COMMANDS = frozenset({
    "exec", "shell", "bash", "sh", "eval", "system", "sudo",
    "curl", "wget", "ssh", "scp", "nc", "telnet",
})
FORBIDDEN_ACTIONS = frozenset({
    "network", "secret_read", "main_mutation", "production_execution",
    "push_main", "merge", "branch_delete", "freeform_shell",
})


@dataclass(frozen=True)
class OperatorCliExtensionReceipt:
    receipt_id: str
    command: str
    subcommand: str
    command_registered: bool
    safety_boundary_valid: bool
    command_contract_valid: bool
    status: str
    created_at: str
    module_version: str = "v1"
    no_cli_execution: bool = True


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_non_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a mapping")


def validate_cli_extension_request(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    required = {"command", "subcommand", "args", "flags"}
    missing = required - set(payload.keys())
    if missing:
        raise ValueError(f"missing_required_fields: {sorted(missing)}")
    cmd = payload["command"]
    if cmd in FORBIDDEN_COMMANDS:
        raise ValueError(f"forbidden_command: {cmd}")
    if cmd not in REGISTERED_COMMANDS:
        raise ValueError(f"unregistered_command: {cmd}")
    flags = payload.get("flags", [])
    if not isinstance(flags, list):
        raise TypeError("flags must be a list")
    for f in flags:
        if not isinstance(f, str):
            raise TypeError("each flag must be a string")
        if f in FORBIDDEN_ACTIONS:
            raise ValueError(f"forbidden_flag: {f}")
    return {"valid": True, "command": cmd}


def validate_cli_command_contract(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    cmd = payload.get("command", "")
    sub = payload.get("subcommand", "")
    args = payload.get("args", [])
    checks = {
        "command_registered": cmd in REGISTERED_COMMANDS,
        "command_not_forbidden": cmd not in FORBIDDEN_COMMANDS,
        "subcommand_present": bool(sub),
        "args_is_list": isinstance(args, list),
    }
    valid = all(checks.values())
    return {"command_contract_valid": valid, "checks": checks}


def validate_cli_safety_boundary(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    checks: Dict[str, bool] = {}
    combined = f"{payload.get('command', '')} {payload.get('subcommand', '')} {' '.join(payload.get('args', []))}"
    combined_lower = combined.lower()
    checks["no_network"] = not any(
        p in combined_lower for p in ("curl", "wget", "nc ", "telnet", "ssh ", "scp ", "http://", "https://", "socket")
    )
    checks["no_secret"] = not any(
        p in combined_lower for p in (".env", "api_key", "secret", "token", "password")
    )
    checks["no_main_mutation"] = "main" not in combined_lower.split() or "main" in ("main.py",)
    checks["no_shell"] = not any(
        p in combined_lower for p in ("exec(", "eval(", "system(", "subprocess", "os.system", "shell")
    )
    all_pass = all(checks.values())
    return {"safety_boundary_valid": all_pass, "checks": checks}


def produce_operator_cli_extension_receipt(payload: Any) -> Dict[str, Any]:
    _reject_non_mapping(payload)
    validate_cli_extension_request(payload)
    contract = validate_cli_command_contract(payload)
    safety = validate_cli_safety_boundary(payload)
    receipt = OperatorCliExtensionReceipt(
        receipt_id=_hash_id(payload.get("command", "unknown"), payload.get("subcommand", ""), _utcnow()),
        command=payload.get("command", ""),
        subcommand=payload.get("subcommand", ""),
        command_registered=contract["checks"]["command_registered"],
        safety_boundary_valid=safety["safety_boundary_valid"],
        command_contract_valid=contract["command_contract_valid"],
        status="ready" if (contract["command_contract_valid"] and safety["safety_boundary_valid"]) else "rejected",
        created_at=_utcnow(),
    )
    return asdict(receipt)


__all__ = [
    "OperatorCliExtensionReceipt",
    "validate_cli_extension_request",
    "validate_cli_command_contract",
    "validate_cli_safety_boundary",
    "produce_operator_cli_extension_receipt",
]
'''

_REGISTRY = json.dumps({
    "registry_name": "local_operator_cli_extension_foundation_registry_v1",
    "registry_version": "v1",
    "status": "active",
    "module_path": "tools/local_code_stages/generated_local_operator_cli_extension_foundation.py",
    "receipt_type": "OperatorCliExtensionReceipt",
    "functions": [
        "validate_cli_extension_request",
        "validate_cli_command_contract",
        "validate_cli_safety_boundary",
        "produce_operator_cli_extension_receipt",
    ],
    "registered_commands": sorted(REGISTERED_COMMANDS),
    "boundary": "local-only, no actual CLI execution in v1",
}, indent=2, sort_keys=True) + "\n"

_POLICY = json.dumps({
    "policy_name": "local_operator_cli_extension_foundation_policy_v1",
    "policy_version": "v1",
    "status": "active",
    "registered_commands": sorted(REGISTERED_COMMANDS),
    "forbidden_commands": sorted(FORBIDDEN_COMMANDS),
    "forbidden_actions": sorted(FORBIDDEN_ACTIONS),
    "network_forbidden": True,
    "secret_read_forbidden": True,
    "main_mutation_forbidden": True,
    "freeform_shell_forbidden": True,
    "no_cli_execution_in_v1": True,
}, indent=2, sort_keys=True) + "\n"

_RUNBOOK = """# Local Operator CLI Extension Foundation v1

## Purpose
Bounded local-only operator CLI extension foundation. Validates CLI
commands without executing them.

## Boundaries
- no unregistered command
- no freeform shell
- no network
- no secret read
- no main mutation
- no production execution
- no actual CLI execution in v1

## Registered Commands
status, health, review, approve, reject, list, report, checkpoint,
rollback, evidence, index, run

## Operations
1. validate_cli_extension_request — structural validation
2. validate_cli_command_contract — command registration check
3. validate_cli_safety_boundary — safety boundary check
4. produce_operator_cli_extension_receipt — full receipt production

## Scope
Contract-only. Does not execute any CLI commands.
"""

_TEST = r'''"""Tests for generated local operator CLI extension foundation module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_code_stages"))

from generated_local_operator_cli_extension_foundation import (  # type: ignore[import-not-found]
    OperatorCliExtensionReceipt,
    validate_cli_extension_request,
    validate_cli_command_contract,
    validate_cli_safety_boundary,
    produce_operator_cli_extension_receipt,
)

VALID_PAYLOAD = {
    "command": "status",
    "subcommand": "health",
    "args": ["--verbose"],
    "flags": [],
}


class LocalOperatorCliExtensionFoundationTests(unittest.TestCase):

    def test_validate_accepts_valid(self):
        result = validate_cli_extension_request(VALID_PAYLOAD)
        self.assertTrue(result["valid"])

    def test_validate_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            validate_cli_extension_request("not a dict")

    def test_validate_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_cli_extension_request({})

    def test_validate_rejects_forbidden_command(self):
        p = {**VALID_PAYLOAD, "command": "shell"}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_rejects_unregistered_command(self):
        p = {**VALID_PAYLOAD, "command": "yolo_deploy"}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_rejects_forbidden_flag(self):
        p = {**VALID_PAYLOAD, "flags": ["network"]}
        with self.assertRaises(ValueError):
            validate_cli_extension_request(p)

    def test_validate_command_contract(self):
        result = validate_cli_command_contract(VALID_PAYLOAD)
        self.assertTrue(result["command_contract_valid"])

    def test_validate_command_contract_unregistered(self):
        p = {**VALID_PAYLOAD, "command": "yolo"}
        result = validate_cli_command_contract(p)
        self.assertFalse(result["command_contract_valid"])

    def test_validate_safety_boundary(self):
        result = validate_cli_safety_boundary(VALID_PAYLOAD)
        self.assertTrue(result["safety_boundary_valid"])

    def test_validate_safety_boundary_rejects_curl_in_args(self):
        p = {**VALID_PAYLOAD, "args": ["curl", "http://evil.com"]}
        result = validate_cli_safety_boundary(p)
        self.assertFalse(result["safety_boundary_valid"])

    def test_validate_safety_boundary_rejects_secret(self):
        p = {**VALID_PAYLOAD, "args": ["--token", "sk-secret"]}
        result = validate_cli_safety_boundary(p)
        self.assertFalse(result["safety_boundary_valid"])

    def test_produce_receipt_valid(self):
        receipt = produce_operator_cli_extension_receipt(VALID_PAYLOAD)
        self.assertEqual(receipt["status"], "ready")
        self.assertTrue(receipt["no_cli_execution"])

    def test_receipt_dataclass(self):
        r = OperatorCliExtensionReceipt(
            receipt_id="rid-1", command="status", subcommand="health",
            command_registered=True, safety_boundary_valid=True,
            command_contract_valid=True, status="ready",
            created_at="2025-01-01T00:00:00Z",
        )
        self.assertTrue(r.no_cli_execution)

    def test_no_subprocess_import(self):
        with open(ROOT / "tools" / "local_code_stages" / "generated_local_operator_cli_extension_foundation.py") as f:
            src = f.read()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)


if __name__ == "__main__":
    unittest.main()
'''

if __name__ == "__main__":
    raise SystemExit(main())
