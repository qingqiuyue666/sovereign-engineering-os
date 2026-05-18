"""Command allowlist — exact first-token allowlist enforcement.

Uses shlex to parse first token. Only commands whose first token
matches an exact entry in the allowlist are permitted.
"""

from __future__ import annotations

import hashlib
import shlex
from typing import Any, Dict, List


class CommandAllowlist:
    """Exact first-token command allowlist."""

    def __init__(self, allowed_commands: List[str] | None = None) -> None:
        self._allowed: set[str] = set()
        if allowed_commands:
            for cmd in allowed_commands:
                self.add(cmd)

    def add(self, command: str) -> None:
        if not command or not command.strip():
            raise ValueError("command must not be empty")
        self._allowed.add(command.strip())

    def remove(self, command: str) -> None:
        self._allowed.discard(command)

    def is_allowed(self, command_text: str) -> bool:
        if not command_text or not command_text.strip():
            return False
        try:
            tokens = shlex.split(command_text.strip())
        except ValueError:
            return False
        if not tokens:
            return False
        return tokens[0] in self._allowed

    def validate(self, command_text: str) -> Dict[str, Any]:
        if not command_text or not command_text.strip():
            return {"valid": False, "first_token": "", "reason": "empty_command_text"}

        try:
            tokens = shlex.split(command_text.strip())
        except ValueError:
            return {"valid": False, "first_token": "", "reason": "invalid_shell_syntax"}

        if not tokens:
            return {"valid": False, "first_token": "", "reason": "no_tokens"}

        first_token = tokens[0]
        allowed = first_token in self._allowed

        return {
            "valid": allowed,
            "first_token": first_token,
            "reason": None if allowed else f"first_token_not_in_allowlist: {first_token}",
        }

    def enforce(self, command_text: str) -> None:
        result = self.validate(command_text)
        if not result["valid"]:
            raise ValueError(result["reason"])

    def allowed_commands(self) -> List[str]:
        return sorted(self._allowed)

    def allowlist_hash(self) -> str:
        if not self._allowed:
            return hashlib.sha256(b"empty_allowlist").hexdigest()
        return hashlib.sha256("|".join(sorted(self._allowed)).encode()).hexdigest()

    def __contains__(self, command: str) -> bool:
        return command in self._allowed
