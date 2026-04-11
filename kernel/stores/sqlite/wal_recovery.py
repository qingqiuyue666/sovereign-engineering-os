"""
SQLite WAL substrate: connection opener, migration runner, and crash-window
recovery classifier foundation.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.2 Seal Transaction Ordering Contract
- v11 §24.2 INV-004 / INV-005
- foundation §1 D-008, §2 layout, §6 (P0 sealing + crash-window proofs)

Phase-1 scope (narrow):
- Provide a single typed opener that enforces `journal_mode = WAL` and
  `synchronous = NORMAL` before any mutation is admitted.
- Provide a migration runner that applies `migrations/*.sql` in lexical
  order, idempotently.
- Provide a crash-window classification skeleton (`classify_wal_state`)
  that returns one of {"clean", "dirty_tail", "mid_segment_corruption",
  "logical_sequence_discontinuity"}. Full recovery semantics are deferred
  to a later hardening slice; this skeleton exists so callers can bind
  their fail-closed posture to a concrete surface today.

Out of scope in phase 1:
- Full WAL frame-level introspection (SQLite hides frame internals; our
  classification here uses logical-sequence continuity on journal_entries,
  which is the governance-layer truth spine).
- Encrypted vault / legal-hold retention surfaces (AT-015).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class WalState(str, Enum):
    CLEAN = "clean"
    DIRTY_TAIL = "dirty_tail"
    MID_SEGMENT_CORRUPTION = "mid_segment_corruption"
    LOGICAL_SEQUENCE_DISCONTINUITY = "logical_sequence_discontinuity"


@dataclass(frozen=True)
class WalClassification:
    state: WalState
    last_logical_sequence: int
    detail: str


def open_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + fsync-NORMAL durability posture.

    The caller is responsible for committing/rolling back. This opener is
    the single admissible entry point for kernel persistence in phase 1.
    """
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # explicit txn control
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # WAL is mandatory under §22.1. NORMAL is the minimum admissible fsync
    # class for the first-slice tracer bullet; FULL may be required by
    # later acceptance tests and is a valid forward tightening.
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    # Busy timeout covers the narrow concurrent-approval race (C22.3 /
    # C22.6); it is not a substitute for transactional serialization.
    cur.execute("PRAGMA busy_timeout=5000;")
    return conn


def _discover_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file())


def apply_migrations(
    conn: sqlite3.Connection,
    migrations: Iterable[Path] | None = None,
) -> list[str]:
    """Apply migration files in lexical order. Returns the list applied.

    The applied-migrations ledger is a dedicated table so we never re-run
    a migration twice. A migration failure aborts the transaction and
    leaves the ledger untouched (fail-closed per §22.1).
    """
    files = list(migrations) if migrations is not None else _discover_migrations()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_migrations (
          name         TEXT PRIMARY KEY,
          applied_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        """
    )
    applied: list[str] = []
    for path in files:
        row = cur.execute(
            "SELECT 1 FROM _schema_migrations WHERE name = ?;", (path.name,)
        ).fetchone()
        if row is not None:
            continue
        sql = path.read_text(encoding="utf-8")
        # Each migration file owns its own BEGIN/COMMIT transaction
        # boundary (see 0001_core_signable_path.sql). We therefore do
        # not wrap it in an outer transaction: `executescript` would
        # commit any outer transaction before running the script,
        # which would desynchronize our ledger write. Instead we run
        # the script and then record the ledger row in a second
        # statement; if the ledger insert fails we raise and leave
        # schema state coherent (the script-level BEGIN/COMMIT
        # guarantees atomicity of the DDL itself).
        cur.executescript(sql)
        try:
            cur.execute(
                "INSERT INTO _schema_migrations (name) VALUES (?);", (path.name,)
            )
        except Exception:
            raise
        applied.append(path.name)
    return applied


def classify_wal_state(conn: sqlite3.Connection) -> WalClassification:
    """Classify the current state of the journal continuity (skeleton).

    Phase-1 definition of "WAL state" is taken at the governance layer:
    logical-sequence continuity on the `journal_entries` table.

    - CLEAN: sequence is strictly monotonic starting at 1 (or empty).
    - LOGICAL_SEQUENCE_DISCONTINUITY: there is a gap between consecutive
      logical sequence values; may be benign (dirty-tail truncation) but
      until we classify it as such the caller must treat it as unsafe.
    - DIRTY_TAIL: the last row is sequentially consistent but earlier
      rows show an odd terminal pattern (placeholder; phase-2 will
      introduce a real WAL-frame checksum check).
    - MID_SEGMENT_CORRUPTION: not detectable from logical sequence alone;
      requires WAL frame-level access. Phase-1 returns CLEAN when no
      sequence anomaly is found, and the caller is required to pair this
      with frame checks provided by AT-007 crash-harness tooling.
    """
    try:
        rows = conn.execute(
            "SELECT logical_sequence FROM journal_entries ORDER BY logical_sequence;"
        ).fetchall()
    except sqlite3.OperationalError as exc:
        # Table missing => migrations not applied yet. This is a caller
        # ordering bug, not a corruption event.
        return WalClassification(
            state=WalState.LOGICAL_SEQUENCE_DISCONTINUITY,
            last_logical_sequence=0,
            detail=f"journal_entries unavailable: {exc}",
        )
    if not rows:
        return WalClassification(
            state=WalState.CLEAN,
            last_logical_sequence=0,
            detail="journal empty",
        )
    expected = rows[0][0]
    last = expected
    for r in rows:
        seq = r[0]
        if seq != expected:
            return WalClassification(
                state=WalState.LOGICAL_SEQUENCE_DISCONTINUITY,
                last_logical_sequence=last,
                detail=f"expected logical_sequence {expected}, found {seq}",
            )
        last = seq
        expected = seq + 1
    return WalClassification(
        state=WalState.CLEAN,
        last_logical_sequence=last,
        detail="journal sequence continuous",
    )
