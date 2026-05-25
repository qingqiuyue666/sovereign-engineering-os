"""SQLite WAL execution journal v1.

This module persists command admission, quarantine, and execution receipt
metadata into local append-only SQLite tables. It stores deterministic content
hashes that exclude creation timestamps and chains rows through
``previous_hash`` for tamper evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import hashlib
import json
import sqlite3

from kernel.runtime.command_envelope_admission_router import (
    CommandAdmissionReport,
    CommandExecutionReceipt,
)

__all__ = [
    "JournalAppendReceipt",
    "JournalVerification",
    "SQLiteWalExecutionJournal",
    "compute_event_content_hash",
]

TABLES = ("admission_events", "quarantine_events", "execution_receipts")
EVENT_TYPES_BY_TABLE = {
    "admission_events": "ADMISSION",
    "quarantine_events": "QUARANTINE",
    "execution_receipts": "EXECUTION_RECEIPT",
}


@dataclass(frozen=True)
class JournalAppendReceipt:
    event_id: str
    run_id: str
    event_type: str
    command_id: str | None
    policy_id: str | None
    token_id: str | None
    approval_id: str | None
    content_hash: str
    previous_hash: str | None
    created_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "command_id": self.command_id,
            "policy_id": self.policy_id,
            "token_id": self.token_id,
            "approval_id": self.approval_id,
            "content_hash": self.content_hash,
            "previous_hash": self.previous_hash,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class JournalVerification:
    valid: bool
    failures: tuple[str, ...]


class SQLiteWalExecutionJournal:
    """Append-only SQLite WAL journal for command admission evidence."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            raise ValueError("journal_parent_directory_missing")
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._enable_wal()
        self._create_schema()

    def append_admission(
        self, report: CommandAdmissionReport
    ) -> JournalAppendReceipt:
        return self._append_report("admission_events", report)

    def append_quarantine(
        self, report: CommandAdmissionReport
    ) -> JournalAppendReceipt:
        return self._append_report("quarantine_events", report)

    def append_receipt(
        self, receipt: CommandExecutionReceipt
    ) -> JournalAppendReceipt:
        return self._append_payload(
            table_name="execution_receipts",
            run_id=receipt.run_id,
            command_id=receipt.command_id,
            policy_id=receipt.policy_id,
            token_id=receipt.token_id,
            approval_id=receipt.approval_id,
            payload_hash=receipt.receipt_hash,
        )

    def list_events(self) -> tuple[dict[str, object], ...]:
        rows: list[dict[str, object]] = []
        for table_name in TABLES:
            cursor = self._connection.execute(
                f"SELECT * FROM {table_name} ORDER BY event_seq"
            )
            for row in cursor.fetchall():
                event = dict(row)
                event["table_name"] = table_name
                rows.append(event)
        rows.sort(key=lambda item: int(item["event_seq"]))
        return tuple(rows)

    def verify_chain(self) -> JournalVerification:
        failures: list[str] = []
        previous_hash: str | None = None
        expected_sequence = 1
        for event in self.list_events():
            if int(event["event_seq"]) != expected_sequence:
                failures.append(f"event_sequence_gap:{event['event_id']}")
            if event["previous_hash"] != previous_hash:
                failures.append(f"previous_hash_mismatch:{event['event_id']}")
            expected_hash = compute_event_content_hash(event)
            if event["content_hash"] != expected_hash:
                failures.append(f"content_hash_mismatch:{event['event_id']}")
            previous_hash = str(event["content_hash"])
            expected_sequence += 1
        return JournalVerification(not failures, tuple(failures))

    def close(self) -> None:
        self._connection.close()

    def _enable_wal(self) -> None:
        mode = self._connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise ValueError("sqlite_wal_mode_required")

    def _create_schema(self) -> None:
        for table_name in TABLES:
            self._connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    event_seq INTEGER NOT NULL UNIQUE,
                    event_id TEXT NOT NULL PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    command_id TEXT,
                    policy_id TEXT,
                    token_id TEXT,
                    approval_id TEXT,
                    content_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    created_at TEXT NOT NULL,
                    payload_hash TEXT NOT NULL
                )
                """
            )
        self._connection.commit()

    def _append_report(
        self,
        table_name: str,
        report: CommandAdmissionReport,
    ) -> JournalAppendReceipt:
        return self._append_payload(
            table_name=table_name,
            run_id=report.run_id,
            command_id=report.command_id,
            policy_id=report.policy_id,
            token_id=report.token_id,
            approval_id=report.approval_id,
            payload_hash=report.content_hash,
        )

    def _append_payload(
        self,
        *,
        table_name: str,
        run_id: str,
        command_id: str | None,
        policy_id: str | None,
        token_id: str | None,
        approval_id: str | None,
        payload_hash: str,
    ) -> JournalAppendReceipt:
        if table_name not in EVENT_TYPES_BY_TABLE:
            raise ValueError("unknown_journal_table")
        event_seq = self._next_event_sequence()
        previous_hash = self._last_content_hash()
        event_type = EVENT_TYPES_BY_TABLE[table_name]
        event_id = _event_id(
            event_seq=event_seq,
            event_type=event_type,
            run_id=run_id,
            payload_hash=payload_hash,
        )
        created_at = _now()
        event_payload = {
            "event_seq": event_seq,
            "event_id": event_id,
            "run_id": run_id,
            "event_type": event_type,
            "command_id": command_id,
            "policy_id": policy_id,
            "token_id": token_id,
            "approval_id": approval_id,
            "previous_hash": previous_hash,
            "payload_hash": payload_hash,
        }
        content_hash = compute_event_content_hash(event_payload)
        with self._connection:
            self._connection.execute(
                f"""
                INSERT INTO {table_name} (
                    event_seq,
                    event_id,
                    run_id,
                    event_type,
                    command_id,
                    policy_id,
                    token_id,
                    approval_id,
                    content_hash,
                    previous_hash,
                    created_at,
                    payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_seq,
                    event_id,
                    run_id,
                    event_type,
                    command_id,
                    policy_id,
                    token_id,
                    approval_id,
                    content_hash,
                    previous_hash,
                    created_at,
                    payload_hash,
                ),
            )
        return JournalAppendReceipt(
            event_id=event_id,
            run_id=run_id,
            event_type=event_type,
            command_id=command_id,
            policy_id=policy_id,
            token_id=token_id,
            approval_id=approval_id,
            content_hash=content_hash,
            previous_hash=previous_hash,
            created_at=created_at,
        )

    def _next_event_sequence(self) -> int:
        max_sequence = 0
        for table_name in TABLES:
            value = self._connection.execute(
                f"SELECT MAX(event_seq) FROM {table_name}"
            ).fetchone()[0]
            if value is not None:
                max_sequence = max(max_sequence, int(value))
        return max_sequence + 1

    def _last_content_hash(self) -> str | None:
        events = self.list_events()
        if not events:
            return None
        return str(events[-1]["content_hash"])


def compute_event_content_hash(event: Mapping[str, object]) -> str:
    """Compute deterministic event content hash excluding created_at."""

    stable = {
        "approval_id": event.get("approval_id"),
        "command_id": event.get("command_id"),
        "event_id": event.get("event_id"),
        "event_seq": event.get("event_seq"),
        "event_type": event.get("event_type"),
        "payload_hash": event.get("payload_hash"),
        "policy_id": event.get("policy_id"),
        "previous_hash": event.get("previous_hash"),
        "run_id": event.get("run_id"),
        "token_id": event.get("token_id"),
    }
    return _sha256(_canonical_json(stable))


def _event_id(
    *,
    event_seq: int,
    event_type: str,
    run_id: str,
    payload_hash: str,
) -> str:
    digest = _sha256(
        _canonical_json(
            {
                "event_seq": event_seq,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "run_id": run_id,
            }
        )
    )
    return "evt_" + digest.removeprefix("sha256:")[:32]


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
