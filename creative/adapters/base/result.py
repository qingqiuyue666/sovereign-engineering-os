"""Adapter result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from creative.common import SCHEMA_VERSION

@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    operation: str
    status: str
    dry_run: bool = True
    evidence: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "adapter": self.adapter,
            "operation": self.operation,
            "status": self.status,
            "dry_run": self.dry_run,
            "evidence": list(self.evidence),
            "failures": list(self.failures),
            "metadata": self.metadata,
        }
