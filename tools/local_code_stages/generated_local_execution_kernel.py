
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
