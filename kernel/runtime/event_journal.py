"""In-memory event journal with append-only semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from kernel.tasks.run_ledger import InMemoryRunLedger, RunLedgerAppendResult

__all__ = ["InMemoryEventJournal"]


@dataclass
class InMemoryEventJournal:
    _ledger: InMemoryRunLedger = field(default_factory=InMemoryRunLedger)

    @property
    def events(self) -> tuple[dict[str, object], ...]:
        return tuple(dict(event) for event in self._ledger.events)

    def append(self, event: Mapping[str, object]) -> RunLedgerAppendResult:
        return self._ledger.append(event)
