
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
