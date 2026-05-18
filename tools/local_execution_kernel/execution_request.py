"""Execution request — immutable command execution request model.

Validates command categories, first-token allowlist compliance, and
rejects forbidden patterns. Uses shlex parsing only.
"""

from __future__ import annotations

import hashlib
import shlex
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


ALLOWED_CATEGORIES = frozenset({"test", "lint", "typecheck", "format-check", "build-check", "ci-check"})

FORBIDDEN_FIRST_TOKENS = frozenset({
    "curl", "wget", "ssh", "scp", "nc", "ncat", "telnet", "rsync",
    "git", "rm", "mv", "dd", "mkfs", "sh", "bash", "zsh",
})

FORBIDDEN_COMMAND_SUBSTRINGS = (
    "curl", "wget", "ssh ", "scp ", "nc ", "ncat ", "telnet ", "rsync ",
    "git checkout main", "git switch main", "git push", "git merge main",
    "git branch -d main", "git branch -D main",
    "rm -rf /", "> /dev/", "mkfs", "dd if=",
    ".env", "API_KEY", "SECRET", "TOKEN", "PASSWORD",
    "| sh", "| bash", "$(", "`",
)

GIT_DESTRUCTIVE = (
    "git checkout main", "git switch main", "git push",
    "git merge main", "git branch -d", "git branch -D",
)


@dataclass(frozen=True)
class ExecutionRequest:
    """Immutable execution request with validated command."""

    request_id: str
    execution_id: str
    command_category: str
    command_text: str
    first_token: str
    parsed_tokens: List[str]
    is_valid: bool
    canonical_hash: str

    @staticmethod
    def create(
        execution_id: str,
        command_category: str,
        command_text: str,
    ) -> ExecutionRequest:
        if not execution_id.strip():
            raise ValueError("execution_id required")
        if command_category not in ALLOWED_CATEGORIES:
            raise ValueError(f"unsupported_command_category: {command_category}")
        if not isinstance(command_text, str) or not command_text.strip():
            raise ValueError("command_text required")

        cmd = command_text.strip()

        # Check forbidden substrings first (security check)
        cmd_lower = cmd.lower()
        for pattern in FORBIDDEN_COMMAND_SUBSTRINGS:
            if pattern.lower() in cmd_lower:
                raise ValueError(f"forbidden_command_pattern: {pattern}")

        # Git destructive operations check (more specific)
        for pattern in GIT_DESTRUCTIVE:
            if pattern.lower() in cmd_lower:
                raise ValueError(f"git_destructive_operation: {pattern}")

        # shlex parse
        try:
            tokens = shlex.split(cmd)
        except ValueError as exc:
            raise ValueError(f"invalid_shell_syntax: {exc}") from exc

        if not tokens:
            raise ValueError("no_tokens_parsed")

        first_token = tokens[0]

        # Reject forbidden first tokens
        if first_token in FORBIDDEN_FIRST_TOKENS:
            raise ValueError(f"forbidden_first_token: {first_token}")

        raw = "|".join([execution_id, command_category, first_token])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        request_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ExecutionRequest(
            request_id=request_id,
            execution_id=execution_id,
            command_category=command_category,
            command_text=cmd,
            first_token=first_token,
            parsed_tokens=tokens,
            is_valid=True,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
