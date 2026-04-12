"""
AT-028: No silent taint clearing.

Constitutional anchors:
- v11 Section 22.11 Taint Propagation Graph Contract
- v11 Section 24.1 AT-028
- v11 Section 24.2 INV-022 (taint clearing requires new record, not
  in-place update)
- Foundation Section 5.2 (AT-024/AT-028 -> INV-019/INV-022)

What this test proves:
  Taint cannot be silently cleared by updating an existing record. The
  SQL-level append-only trigger blocks in-place mutation. Clearing
  requires an explicit new TaintRecord insertion with clearing metadata.
"""

from __future__ import annotations

import unittest
import sqlite3
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import TaintRepository


class TestNoSilentTaintClearing(unittest.TestCase):
    """AT-028 / INV-022: no silent taint clearing."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.taint_repo = TaintRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_silent_clear_via_update_blocked(self) -> None:
        """Attempting to clear taint via UPDATE must fail at SQL layer."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="artifact-x",
            taint_class="security_suspect",
            taint_state="tainted",
            source_ref="test-source",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE taint_records SET taint_state = 'clean', "
                "cleared_at = '2025-01-01T00:00:00+00:00' "
                "WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_silent_delete_blocked(self) -> None:
        """Attempting to delete a taint record must fail at SQL layer."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="artifact-y",
            taint_class="replay_degraded",
            taint_state="downgraded",
            source_ref="test-source",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "DELETE FROM taint_records WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_explicit_clearing_record_accepted(self) -> None:
        """A new clearing record (not an update) must succeed."""
        taint_id_orig = f"taint-{uuid4().hex[:8]}"
        taint_id_clear = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id_orig,
            subject_id="artifact-z",
            taint_class="policy_degraded",
            taint_state="tainted",
            source_ref="original-source",
        )
        self.taint_repo.append(
            taint_record_id=taint_id_clear,
            subject_id="artifact-z",
            taint_class="policy_degraded",
            taint_state="cleared_by_policy",
            source_ref="clearing-source",
            cleared_at="2025-06-01T00:00:00+00:00",
            clearing_identity="operator:test",
            clearing_reason="test confirmed clean",
        )
        rows = self.conn.execute(
            "SELECT taint_state FROM taint_records WHERE subject_id = ? "
            "ORDER BY created_at;",
            ("artifact-z",),
        ).fetchall()
        self.assertEqual(len(rows), 2)
        states = [r["taint_state"] for r in rows]
        self.assertIn("tainted", states)
        self.assertIn("cleared_by_policy", states)


if __name__ == "__main__":
    unittest.main()
