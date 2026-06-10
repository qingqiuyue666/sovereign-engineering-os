"""Retry budget model for execution attempts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from execution_plane.runtime.token_policy import normalize_runtime_policy


@dataclass(frozen=True)
class RetryBudget:
    enabled: bool
    max_attempts: int
    backoff_seconds: int

    @classmethod
    def from_token(cls, token: Mapping[str, Any]) -> "RetryBudget":
        section = normalize_runtime_policy(token)["retry"]
        return cls(
            enabled=bool(section["enabled"]),
            max_attempts=int(section["max_attempts"]),
            backoff_seconds=int(section["backoff_seconds"]),
        )

    def attempt_allowed(self, attempt_index: int) -> bool:
        if attempt_index <= 0:
            return False
        if attempt_index == 1:
            return True
        return self.enabled and attempt_index <= self.max_attempts
