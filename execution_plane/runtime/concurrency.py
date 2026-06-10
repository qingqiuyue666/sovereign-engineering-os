"""Runtime concurrency budget helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from execution_plane.runtime.token_policy import max_adapter_jobs, max_global_jobs


@dataclass
class ConcurrencyBudget:
    max_global_jobs: int
    max_per_adapter_jobs: dict[str, int]
    running_global_jobs: int = 0
    running_per_adapter_jobs: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_token(cls, token: Mapping[str, Any]) -> "ConcurrencyBudget":
        policy = token.get("concurrency", {})
        per_adapter = policy.get("max_per_adapter_jobs", {}) if isinstance(policy, Mapping) else {}
        return cls(
            max_global_jobs=max_global_jobs(token),
            max_per_adapter_jobs={str(adapter): int(limit) for adapter, limit in dict(per_adapter).items()},
        )

    def can_start(self, adapter: str) -> bool:
        adapter_running = self.running_per_adapter_jobs.get(adapter, 0)
        adapter_limit = self.max_per_adapter_jobs.get(adapter, 1)
        return self.running_global_jobs < self.max_global_jobs and adapter_running < adapter_limit

    def start(self, adapter: str) -> None:
        if not self.can_start(adapter):
            raise RuntimeError(f"concurrency budget exhausted for adapter:{adapter}")
        self.running_global_jobs += 1
        self.running_per_adapter_jobs[adapter] = self.running_per_adapter_jobs.get(adapter, 0) + 1

    def finish(self, adapter: str) -> None:
        self.running_global_jobs = max(0, self.running_global_jobs - 1)
        current = self.running_per_adapter_jobs.get(adapter, 0)
        if current <= 1:
            self.running_per_adapter_jobs.pop(adapter, None)
        else:
            self.running_per_adapter_jobs[adapter] = current - 1


def adapter_budget(token: Mapping[str, Any], adapter: str) -> int:
    return max_adapter_jobs(token, adapter)
