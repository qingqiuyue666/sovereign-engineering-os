"""
AT-033: Audit records are append-only.

Constitutional anchors:
- v11 Section 15 (evidence plane obligations)
- v11 Section 23.14 AuditRecord
- v11 Section 24.1 AT-033
- v11 Section 24.2 INV-026 (audit records are append-only)
- Foundation Section 5.1 test #6 (evidence append-only)

What this test proves:
  Audit records cannot be mutated or deleted after creation. The
  SQL-level trigger enforces this. The append-only invariant holds
  at both the application layer (ledger) and the database layer.
"""

from __future__ import annotations

import unittest
import sqlite3
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness
from kernel.evidence.append_only_ledger import AppendOnlyLedger, LedgerViolation


class TestAuditAppendOnly(unittest.TestCase):
    """AT-033 / INV-026: audit records are append-only."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_audit_record_update_blocked(self) -> None:
        """Attempting UPDATE on an audit record must fail (SQL trigger)."""
        # Insert via the ledger.
        aud_id = self.harness.audit_ledger.append(
            record_type="test_record",
            task_id="t-test",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.harness.conn.execute(
                "UPDATE audit_records SET record_type = 'tampered' "
                "WHERE audit_record_id = ?;",
                (aud_id,),
            )

    def test_audit_record_delete_blocked(self) -> None:
        """Attempting DELETE on an audit record must fail (SQL trigger)."""
        aud_id = self.harness.audit_ledger.append(
            record_type="test_delete_record",
            task_id="t-del",
        )
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.harness.conn.execute(
                "DELETE FROM audit_records WHERE audit_record_id = ?;",
                (aud_id,),
            )

    def test_monotonic_sequence(self) -> None:
        """Audit records must have monotonically increasing sequence."""
        for i in range(5):
            self.harness.audit_ledger.append(
                record_type=f"seq_test_{i}",
                task_id="t-seq",
            )
        rows = self.harness.conn.execute(
            "SELECT sequence FROM audit_records ORDER BY sequence;"
        ).fetchall()
        seqs = [r[0] for r in rows]
        for i in range(1, len(seqs)):
            self.assertGreater(seqs[i], seqs[i - 1])

    def test_ledger_rejects_empty_record_type(self) -> None:
        """Application layer: empty record_type is rejected."""
        with self.assertRaises(LedgerViolation):
            self.harness.audit_ledger.append(
                record_type="",
                task_id="t-empty",
            )

    def test_full_path_audit_coverage(self) -> None:
        """A full happy path must produce audit records for every stage."""
        ids = self.harness.run_full_happy_path()
        rows = self.harness.conn.execute(
            "SELECT record_type FROM audit_records WHERE task_id = ? "
            "ORDER BY sequence;",
            (ids["task_id"],),
        ).fetchall()
        record_types = [r["record_type"] for r in rows]
        # Must include at minimum: context created, inference created,
        # patch proposal created, validation, review, approval, seal, evidence.
        self.assertTrue(len(record_types) >= 8)
        self.assertTrue(
            any("context" in rt for rt in record_types),
            "missing context audit record",
        )
        self.assertTrue(
            any("evidence" in rt or "replay" in rt for rt in record_types),
            "missing evidence/replay audit record",
        )


if __name__ == "__main__":
    unittest.main()
