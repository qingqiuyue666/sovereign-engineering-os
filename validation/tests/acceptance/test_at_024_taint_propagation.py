"""
AT-024: Taint propagation durability.

Constitutional anchors:
- v11 Section 22.11 Taint Propagation Graph Contract
- v11 Section 24.1 AT-024
- v11 Section 24.2 INV-019 (taint propagation auditable)
- Foundation Section 5.1 test #9 (taint transition durability)

What this test proves:
  Taint transitions are durably recorded via append-only TaintRecord
  emission. Once a taint record is inserted, it cannot be updated or
  deleted at the SQL layer.
"""

from __future__ import annotations

import unittest
import sqlite3
import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import TaintRepository


class TestTaintPropagation(unittest.TestCase):
    """AT-024 / INV-019: taint propagation is durable and append-only."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.taint_repo = TaintRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_taint_record_insertable(self) -> None:
        """A taint record can be inserted and read back."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-123",
            taint_class="quarantine_breach_suspect",
            taint_state="tainted",
            source_ref="at-024-test",
        )
        row = self.conn.execute(
            "SELECT * FROM taint_records WHERE taint_record_id = ?;",
            (taint_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["taint_class"], "quarantine_breach_suspect")
        self.assertEqual(row["taint_state"], "tainted")

    def test_taint_record_append_only_no_update(self) -> None:
        """INV-022: taint records cannot be updated in place."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-456",
            taint_class="policy_degraded",
            taint_state="suspected",
            source_ref="at-024-update-test",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE taint_records SET taint_state = 'clean' "
                "WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_taint_record_append_only_no_delete(self) -> None:
        """INV-022: taint records cannot be deleted."""
        taint_id = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id,
            subject_id="ctx-test-789",
            taint_class="untrusted_text",
            taint_state="tainted",
            source_ref="at-024-delete-test",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "DELETE FROM taint_records WHERE taint_record_id = ?;",
                (taint_id,),
            )

    def test_taint_escalation_requires_new_record(self) -> None:
        """Clearing taint requires inserting a new record, not updating."""
        # Insert initial taint.
        taint_id_1 = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id_1,
            subject_id="ctx-escalation",
            taint_class="quarantine_breach_suspect",
            taint_state="tainted",
            source_ref="escalation-source",
        )

        # "Clear" by inserting a new record with cleared state.
        taint_id_2 = f"taint-{uuid4().hex[:8]}"
        self.taint_repo.append(
            taint_record_id=taint_id_2,
            subject_id="ctx-escalation",
            taint_class="quarantine_breach_suspect",
            taint_state="cleared_by_policy",
            source_ref="clearing-source",
            cleared_at=datetime.now(timezone.utc).isoformat(),
            clearing_identity="operator:admin",
            clearing_reason="manual investigation confirmed clean",
        )

        # Both records must exist.
        rows = self.conn.execute(
            "SELECT * FROM taint_records WHERE subject_id = ? ORDER BY created_at;",
            ("ctx-escalation",),
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["taint_state"], "tainted")
        self.assertEqual(rows[1]["taint_state"], "cleared_by_policy")


if __name__ == "__main__":
    unittest.main()
