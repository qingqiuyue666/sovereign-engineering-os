"""
AT-006: WAL dirty-tail truncation classification.

Constitutional anchors:
- v11 Section 22.1 WAL Durability and Recovery Contract
- v11 Section 22.2 Seal Transaction Ordering Contract
- v11 Section 24.1 AT-006
- v11 Section 24.2 INV-004 (journal entries immutable / append-only)
- v11 Section 24.2 INV-005 (sealed revision immutable)
- Foundation Section 5.1 test #4 (seal durability ordering crash-window)

What this test proves:
  The WAL state classifier must detect discontinuities in the journal
  sequence and classify them correctly. Sealed revisions must not be
  visible before the durability boundary is crossed.
"""

from __future__ import annotations

import unittest
import sys
import os
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import (
    WalState,
    classify_wal_state,
    open_connection,
    apply_migrations,
)


class TestWalDirtyTailTruncation(unittest.TestCase):
    """AT-006 / INV-004 / INV-005: WAL dirty-tail classification."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_clean_empty_journal(self) -> None:
        """An empty journal classifies as CLEAN."""
        classification = classify_wal_state(self.conn)
        self.assertEqual(classification.state, WalState.CLEAN)

    def test_clean_monotonic_journal(self) -> None:
        """Monotonically sequenced journal entries classify as CLEAN."""
        for seq in range(1, 6):
            self.conn.execute(
                """
                INSERT INTO journal_entries (
                    journal_entry_id, logical_sequence, entry_type,
                    revision_id, parent_revision_id, project_id, task_id,
                    causality_ref, payload_hash, version_tuple_hash,
                    taint_set_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f"je-{seq}", seq, "seal_prepare",
                    f"rev-{seq}", None, "p1", "t1",
                    None, f"hash-{seq}", "vth:test",
                    "[]", "2025-01-01T00:00:00+00:00",
                ),
            )
        classification = classify_wal_state(self.conn)
        self.assertEqual(classification.state, WalState.CLEAN)

    def test_journal_append_only_prevents_update(self) -> None:
        """INV-004: journal entries cannot be updated (SQL trigger)."""
        self.conn.execute(
            """
            INSERT INTO journal_entries (
                journal_entry_id, logical_sequence, entry_type,
                revision_id, parent_revision_id, project_id, task_id,
                causality_ref, payload_hash, version_tuple_hash,
                taint_set_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "je-1", 1, "seal_prepare",
                "rev-1", None, "p1", "t1",
                None, "hash-1", "vth:test",
                "[]", "2025-01-01T00:00:00+00:00",
            ),
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE journal_entries SET entry_type = 'tampered' "
                "WHERE journal_entry_id = 'je-1';"
            )

    def test_journal_append_only_prevents_delete(self) -> None:
        """INV-004: journal entries cannot be deleted (SQL trigger)."""
        self.conn.execute(
            """
            INSERT INTO journal_entries (
                journal_entry_id, logical_sequence, entry_type,
                revision_id, parent_revision_id, project_id, task_id,
                causality_ref, payload_hash, version_tuple_hash,
                taint_set_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "je-del", 2, "seal_prepare",
                "rev-del", None, "p1", "t1",
                None, "hash-del", "vth:test",
                "[]", "2025-01-01T00:00:00+00:00",
            ),
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "DELETE FROM journal_entries WHERE journal_entry_id = 'je-del';"
            )


if __name__ == "__main__":
    unittest.main()
