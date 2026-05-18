"""Patch allowlist — enforces allowed target paths and operations.

Only explicitly allowed paths may be patched. All other paths are rejected.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class PatchAllowlist:
    """Enforces patch allowlist for target paths and operations."""

    def __init__(self, allowed_paths: List[str] | None = None) -> None:
        self._allowed_paths: List[str] = sorted(allowed_paths or [])

    def add_path(self, path: str) -> None:
        if path not in self._allowed_paths:
            self._allowed_paths.append(path)
            self._allowed_paths.sort()

    def is_allowed(self, target_path: str) -> bool:
        if not self._allowed_paths:
            return False
        return target_path in self._allowed_paths

    def validate(self, target_path: str) -> Dict[str, Any]:
        allowed = self.is_allowed(target_path)
        return {
            "valid": allowed,
            "target_path": target_path,
            "reason": None if allowed else "target_path_not_in_allowlist",
        }

    def enforce(self, target_path: str) -> None:
        result = self.validate(target_path)
        if not result["valid"]:
            raise ValueError(result["reason"])

    def allowed_paths(self) -> List[str]:
        return list(self._allowed_paths)

    def allowlist_hash(self) -> str:
        if not self._allowed_paths:
            return hashlib.sha256(b"empty_allowlist").hexdigest()
        return hashlib.sha256("|".join(self._allowed_paths).encode()).hexdigest()
