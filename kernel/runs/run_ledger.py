"""Caller-scoped run ledger writer for V12 operator dry runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
import json

from kernel.tasks.run_ledger import InMemoryRunLedger

from .run_report import create_run_report

__all__ = ["FileRunLedgerResult", "write_run_ledger"]


@dataclass(frozen=True)
class FileRunLedgerResult:
    accepted: bool
    ledger_path: str | None
    report: dict[str, object]
    failures: tuple[str, ...]


def write_run_ledger(
    *,
    output_dir: str | Path,
    task_id: str,
    run_id: str,
    events: Sequence[Mapping[str, object]],
) -> FileRunLedgerResult:
    output_path = Path(output_dir)
    ledger_path = output_path / "run_ledger_v1.json"
    if ledger_path.exists():
        return FileRunLedgerResult(False, None, {}, ("run_ledger_overwrite_forbidden",))

    ledger = InMemoryRunLedger()
    failures: list[str] = []
    accepted_events: list[dict[str, object]] = []
    for event in events:
        result = ledger.append(event)
        if not result.accepted:
            failures.extend(result.failures)
        else:
            accepted_events.append(dict(event))

    if not isinstance(task_id, str) or not task_id:
        failures.append("task_id_required")
    if not isinstance(run_id, str) or not run_id:
        failures.append("run_id_required")
    if failures:
        return FileRunLedgerResult(False, None, {}, tuple(sorted(set(failures))))

    output_path.mkdir(parents=True, exist_ok=True)
    payload = {
        "ledger_type": "run_ledger_v1",
        "task_id": task_id,
        "run_id": run_id,
        "events": accepted_events,
        "raw_input_persisted": False,
        "network_accessed": False,
        "secret_value_read": False,
        "ai_provider_call_performed": False,
        "sqlite_mutation_performed": False,
        "production_autonomy_enabled": False,
    }
    ledger_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return FileRunLedgerResult(True, str(ledger_path), create_run_report(payload), ())
