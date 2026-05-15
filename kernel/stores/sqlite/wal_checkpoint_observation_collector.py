"""SQLite WAL checkpoint observation collector.

This module collects non-mutating WAL metadata for the checkpoint planner. It
may read file metadata and may query read-only SQLite page size metadata. It
never executes checkpointing, never truncates WAL files, and never mutates
SQLite state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import json
import sqlite3
import time

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.stores.sqlite.wal_checkpoint_policy import WalCheckpointObservation

__all__ = [
    "WalCheckpointObservationCollectorResult",
    "collect_wal_checkpoint_observation",
    "write_wal_checkpoint_observation",
]

_OBSERVATION_FILE = "wal_checkpoint_observation.json"
_OBSERVATION_TYPE = "seos_wal_checkpoint_observation_v1"
_DEFAULT_PAGE_SIZE = 4096
_ALLOWED_DB_SUFFIXES = frozenset({".sqlite", ".sqlite3", ".db"})


@dataclass(frozen=True)
class WalCheckpointObservationCollectorResult:
    observation: WalCheckpointObservation
    payload: dict[str, object]
    observation_path: Path | None
    database_opened_read_only: bool
    checkpoint_executed: bool
    wal_truncate_executed: bool
    sqlite_state_mutated: bool
    required_human_approval: bool


def collect_wal_checkpoint_observation(
    *,
    db_path: Path,
    now_seconds: int | None = None,
    snapshot_creation_pending: bool = False,
    dirty_tail_detected: bool = False,
    mid_segment_corruption_detected: bool = False,
    allow_readonly_page_size_query: bool = False,
    page_size_override: int | None = None,
) -> WalCheckpointObservationCollectorResult:
    database_path = Path(db_path)
    if database_path.suffix not in _ALLOWED_DB_SUFFIXES:
        raise ValueError("db_path suffix is not allowed")
    if database_path.is_symlink():
        raise ValueError("db_path symlink is forbidden")
    if not isinstance(snapshot_creation_pending, bool):
        raise ValueError("snapshot_creation_pending must be boolean")
    if not isinstance(dirty_tail_detected, bool):
        raise ValueError("dirty_tail_detected must be boolean")
    if not isinstance(mid_segment_corruption_detected, bool):
        raise ValueError("mid_segment_corruption_detected must be boolean")
    if not isinstance(allow_readonly_page_size_query, bool):
        raise ValueError("allow_readonly_page_size_query must be boolean")
    now_value = _normalize_now(now_seconds)
    wal_path = _wal_path_for(database_path)
    wal_exists = wal_path.is_file() and not wal_path.is_symlink()
    wal_bytes = wal_path.stat().st_size if wal_exists else 0
    wal_mtime_seconds = int(wal_path.stat().st_mtime) if wal_exists else None
    age_seconds = 0 if wal_mtime_seconds is None else max(0, now_value - wal_mtime_seconds)
    page_size, database_opened_read_only = _resolve_page_size(
        database_path,
        allow_readonly_page_size_query=allow_readonly_page_size_query,
        page_size_override=page_size_override,
    )
    estimated_wal_pages = _estimate_pages(wal_bytes, page_size)
    observation = WalCheckpointObservation(
        wal_pages=estimated_wal_pages,
        wal_bytes=wal_bytes,
        age_seconds=age_seconds,
        snapshot_creation_pending=snapshot_creation_pending,
        dirty_tail_detected=dirty_tail_detected,
        mid_segment_corruption_detected=mid_segment_corruption_detected,
    )
    payload = {
        "observation_type": _OBSERVATION_TYPE,
        "db_path": database_path.as_posix(),
        "wal_path": wal_path.as_posix(),
        "wal_exists": wal_exists,
        "wal_bytes": wal_bytes,
        "page_size": page_size,
        "estimated_wal_pages": estimated_wal_pages,
        "age_seconds": age_seconds,
        "snapshot_creation_pending": snapshot_creation_pending,
        "dirty_tail_detected": dirty_tail_detected,
        "mid_segment_corruption_detected": mid_segment_corruption_detected,
        "database_opened_read_only": database_opened_read_only,
        "readonly_page_size_query_allowed": allow_readonly_page_size_query,
        "checkpoint_executed": False,
        "pragma_wal_checkpoint_executed": False,
        "wal_truncate_executed": False,
        "sqlite_state_mutated": False,
        "write_transaction_opened": False,
        "planner_compatible": True,
        "required_human_approval": True,
    }
    return WalCheckpointObservationCollectorResult(
        observation=observation,
        payload=payload,
        observation_path=None,
        database_opened_read_only=database_opened_read_only,
        checkpoint_executed=False,
        wal_truncate_executed=False,
        sqlite_state_mutated=False,
        required_human_approval=True,
    )


def write_wal_checkpoint_observation(
    *,
    db_path: Path,
    output_dir: Path,
    now_seconds: int | None = None,
    snapshot_creation_pending: bool = False,
    dirty_tail_detected: bool = False,
    mid_segment_corruption_detected: bool = False,
    allow_readonly_page_size_query: bool = False,
    page_size_override: int | None = None,
) -> WalCheckpointObservationCollectorResult:
    out = Path(output_dir)
    if not out.exists() or not out.is_dir():
        raise ValueError("output_dir is missing")
    observation_path = out / _OBSERVATION_FILE
    if observation_path.exists():
        raise ValueError("wal checkpoint observation already exists")
    result = collect_wal_checkpoint_observation(
        db_path=db_path,
        now_seconds=now_seconds,
        snapshot_creation_pending=snapshot_creation_pending,
        dirty_tail_detected=dirty_tail_detected,
        mid_segment_corruption_detected=mid_segment_corruption_detected,
        allow_readonly_page_size_query=allow_readonly_page_size_query,
        page_size_override=page_size_override,
    )
    write_json_atomically(observation_path, result.payload)
    return WalCheckpointObservationCollectorResult(
        observation=result.observation,
        payload=result.payload,
        observation_path=observation_path,
        database_opened_read_only=result.database_opened_read_only,
        checkpoint_executed=False,
        wal_truncate_executed=False,
        sqlite_state_mutated=False,
        required_human_approval=True,
    )


def _wal_path_for(db_path: Path) -> Path:
    return Path(db_path.as_posix() + "-wal")


def _estimate_pages(wal_bytes: int, page_size: int) -> int:
    if wal_bytes <= 0:
        return 0
    return (wal_bytes + page_size - 1) // page_size


def _normalize_now(now_seconds: int | None) -> int:
    if now_seconds is None:
        return int(time.time())
    if isinstance(now_seconds, bool) or not isinstance(now_seconds, int):
        raise ValueError("now_seconds must be integer")
    if now_seconds < 0:
        raise ValueError("now_seconds must be non-negative")
    return now_seconds


def _resolve_page_size(
    db_path: Path,
    *,
    allow_readonly_page_size_query: bool,
    page_size_override: int | None,
) -> tuple[int, bool]:
    if page_size_override is not None:
        if isinstance(page_size_override, bool) or not isinstance(page_size_override, int):
            raise ValueError("page_size_override must be integer")
        if page_size_override <= 0:
            raise ValueError("page_size_override must be positive")
        return page_size_override, False
    if allow_readonly_page_size_query:
        if not db_path.is_file():
            return _DEFAULT_PAGE_SIZE, False
        return _read_page_size_readonly(db_path), True
    return _DEFAULT_PAGE_SIZE, False


def _read_page_size_readonly(db_path: Path) -> int:
    uri = "file:" + db_path.as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        row = conn.execute("PRAGMA page_size;").fetchone()
    finally:
        conn.close()
    if row is None:
        return _DEFAULT_PAGE_SIZE
    value = row[0]
    if not isinstance(value, int) or value <= 0:
        return _DEFAULT_PAGE_SIZE
    return value
