"""Asset inventory journal binding v1.

Scans explicitly supplied asset roots with the Minimal Asset Inventory and
records one append-only SQLite WAL evidence event per scan. The journal stores
deterministic inventory digests, not asset payload bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import hashlib
import json
import sqlite3

from kernel.runtime.minimal_asset_inventory import (
    AssetInventoryRecord,
    scan_asset_inventory,
)

__all__ = [
    "ASSET_INVENTORY_EVENT_TYPE",
    "AssetInventoryScanEvent",
    "AssetInventoryScanJournal",
    "AssetInventoryJournalBinding",
    "compute_aggregate_inventory_hash",
    "compute_scan_event_content_hash",
    "scan_asset_inventory_to_journal",
]

ASSET_INVENTORY_EVENT_TYPE = "ASSET_INVENTORY_SCAN"


@dataclass(frozen=True)
class AssetInventoryScanEvent:
    event_seq: int
    event_id: str
    event_type: str
    scan_id: str
    root_ids: tuple[str, ...]
    asset_count: int
    aggregate_inventory_hash: str
    per_asset_content_hashes: tuple[str, ...]
    previous_hash: str | None
    created_at: str
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "event_seq": self.event_seq,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "scan_id": self.scan_id,
            "root_ids": list(self.root_ids),
            "asset_count": self.asset_count,
            "aggregate_inventory_hash": self.aggregate_inventory_hash,
            "per_asset_content_hashes": list(self.per_asset_content_hashes),
            "previous_hash": self.previous_hash,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class AssetInventoryJournalVerification:
    valid: bool
    failures: tuple[str, ...]


class AssetInventoryScanJournal:
    """Append-only SQLite WAL journal for inventory scan digest evidence."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            raise ValueError("asset_inventory_journal_parent_directory_missing")
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._enable_wal()
        self._create_schema()

    def append_scan(
        self,
        records: tuple[AssetInventoryRecord, ...],
    ) -> AssetInventoryScanEvent:
        event_seq = self._next_event_sequence()
        previous_hash = self._last_content_hash()
        root_ids = tuple(sorted({record.root_id for record in records}))
        per_asset_hashes = tuple(record.content_hash for record in records)
        aggregate_hash = compute_aggregate_inventory_hash(records)
        scan_id = _scan_id(root_ids, aggregate_hash)
        event_id = _event_id(event_seq, scan_id, aggregate_hash)
        created_at = _now()
        content_hash = compute_scan_event_content_hash(
            {
                "event_seq": event_seq,
                "event_id": event_id,
                "event_type": ASSET_INVENTORY_EVENT_TYPE,
                "scan_id": scan_id,
                "root_ids": root_ids,
                "asset_count": len(records),
                "aggregate_inventory_hash": aggregate_hash,
                "per_asset_content_hashes": per_asset_hashes,
                "previous_hash": previous_hash,
            }
        )
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO asset_inventory_scan_events (
                    event_seq,
                    event_id,
                    event_type,
                    scan_id,
                    root_ids_json,
                    asset_count,
                    aggregate_inventory_hash,
                    per_asset_content_hashes_json,
                    previous_hash,
                    created_at,
                    content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_seq,
                    event_id,
                    ASSET_INVENTORY_EVENT_TYPE,
                    scan_id,
                    _canonical_json(list(root_ids)),
                    len(records),
                    aggregate_hash,
                    _canonical_json(list(per_asset_hashes)),
                    previous_hash,
                    created_at,
                    content_hash,
                ),
            )
        return AssetInventoryScanEvent(
            event_seq=event_seq,
            event_id=event_id,
            event_type=ASSET_INVENTORY_EVENT_TYPE,
            scan_id=scan_id,
            root_ids=root_ids,
            asset_count=len(records),
            aggregate_inventory_hash=aggregate_hash,
            per_asset_content_hashes=per_asset_hashes,
            previous_hash=previous_hash,
            created_at=created_at,
            content_hash=content_hash,
        )

    def list_events(self) -> tuple[AssetInventoryScanEvent, ...]:
        cursor = self._connection.execute(
            "SELECT * FROM asset_inventory_scan_events ORDER BY event_seq"
        )
        events = []
        for row in cursor.fetchall():
            events.append(
                AssetInventoryScanEvent(
                    event_seq=int(row["event_seq"]),
                    event_id=str(row["event_id"]),
                    event_type=str(row["event_type"]),
                    scan_id=str(row["scan_id"]),
                    root_ids=tuple(json.loads(row["root_ids_json"])),
                    asset_count=int(row["asset_count"]),
                    aggregate_inventory_hash=str(row["aggregate_inventory_hash"]),
                    per_asset_content_hashes=tuple(
                        json.loads(row["per_asset_content_hashes_json"])
                    ),
                    previous_hash=row["previous_hash"],
                    created_at=str(row["created_at"]),
                    content_hash=str(row["content_hash"]),
                )
            )
        return tuple(events)

    def verify_chain(self) -> AssetInventoryJournalVerification:
        failures: list[str] = []
        previous_hash: str | None = None
        expected_sequence = 1
        for event in self.list_events():
            if event.event_seq != expected_sequence:
                failures.append(f"event_sequence_gap:{event.event_id}")
            if event.previous_hash != previous_hash:
                failures.append(f"previous_hash_mismatch:{event.event_id}")
            expected_hash = compute_scan_event_content_hash(event.as_dict())
            if event.content_hash != expected_hash:
                failures.append(f"content_hash_mismatch:{event.event_id}")
            previous_hash = event.content_hash
            expected_sequence += 1
        return AssetInventoryJournalVerification(not failures, tuple(failures))

    def close(self) -> None:
        self._connection.close()

    def _enable_wal(self) -> None:
        mode = self._connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise ValueError("sqlite_wal_mode_required")

    def _create_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS asset_inventory_scan_events (
                event_seq INTEGER NOT NULL UNIQUE,
                event_id TEXT NOT NULL PRIMARY KEY,
                event_type TEXT NOT NULL,
                scan_id TEXT NOT NULL,
                root_ids_json TEXT NOT NULL,
                asset_count INTEGER NOT NULL,
                aggregate_inventory_hash TEXT NOT NULL,
                per_asset_content_hashes_json TEXT NOT NULL,
                previous_hash TEXT,
                created_at TEXT NOT NULL,
                content_hash TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def _next_event_sequence(self) -> int:
        value = self._connection.execute(
            "SELECT MAX(event_seq) FROM asset_inventory_scan_events"
        ).fetchone()[0]
        return 1 if value is None else int(value) + 1

    def _last_content_hash(self) -> str | None:
        value = self._connection.execute(
            """
            SELECT content_hash FROM asset_inventory_scan_events
            ORDER BY event_seq DESC LIMIT 1
            """
        ).fetchone()
        return None if value is None else str(value[0])


class AssetInventoryJournalBinding:
    def __init__(self, journal: AssetInventoryScanJournal):
        self.journal = journal

    def scan_and_append(
        self,
        roots: Mapping[str, str | Path],
    ) -> AssetInventoryScanEvent:
        return scan_asset_inventory_to_journal(roots, self.journal)


def scan_asset_inventory_to_journal(
    roots: Mapping[str, str | Path],
    journal: AssetInventoryScanJournal,
) -> AssetInventoryScanEvent:
    records = scan_asset_inventory(roots)
    return journal.append_scan(records)


def compute_aggregate_inventory_hash(
    records: tuple[AssetInventoryRecord, ...],
) -> str:
    stable = {
        "asset_count": len(records),
        "per_asset_content_hashes": [record.content_hash for record in records],
        "root_ids": sorted({record.root_id for record in records}),
    }
    return _sha256(_canonical_json(stable))


def compute_scan_event_content_hash(event: Mapping[str, object]) -> str:
    stable = {
        "aggregate_inventory_hash": event.get("aggregate_inventory_hash"),
        "asset_count": event.get("asset_count"),
        "event_id": event.get("event_id"),
        "event_seq": event.get("event_seq"),
        "event_type": event.get("event_type"),
        "per_asset_content_hashes": tuple(event.get("per_asset_content_hashes", ())),
        "previous_hash": event.get("previous_hash"),
        "root_ids": tuple(event.get("root_ids", ())),
        "scan_id": event.get("scan_id"),
    }
    return _sha256(_canonical_json(stable))


def _scan_id(root_ids: tuple[str, ...], aggregate_hash: str) -> str:
    digest = _sha256(_canonical_json({"root_ids": root_ids, "hash": aggregate_hash}))
    return "scan_" + digest.removeprefix("sha256:")[:32]


def _event_id(event_seq: int, scan_id: str, aggregate_hash: str) -> str:
    digest = _sha256(
        _canonical_json(
            {
                "event_seq": event_seq,
                "event_type": ASSET_INVENTORY_EVENT_TYPE,
                "scan_id": scan_id,
                "aggregate_inventory_hash": aggregate_hash,
            }
        )
    )
    return "asset_evt_" + digest.removeprefix("sha256:")[:32]


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
