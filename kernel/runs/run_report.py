"""Digest-only run reports for V12 operator ledgers."""

from __future__ import annotations

from typing import Mapping

from kernel.tasks.run_id import digest_payload

__all__ = ["create_run_report"]


def create_run_report(ledger_payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "report_type": "run_report_v1",
        "task_id": ledger_payload.get("task_id"),
        "run_id": ledger_payload.get("run_id"),
        "ledger_digest": digest_payload(ledger_payload),
        "raw_input_persisted": False,
        "network_accessed": False,
        "secret_value_read": False,
        "ai_provider_call_performed": False,
        "sqlite_mutation_performed": False,
        "production_autonomy_enabled": False,
    }
