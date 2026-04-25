"""
P0 transaction-boundary hardening (phase 1): audit `sequence` allocation
inside `KernelUnitOfWork` is monotonic.

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §23.14 AuditRecord
- v11 §24.2 INV-026 (audit append-only)
- foundation §6 (P0 sealing + crash-window proofs)

`AuditRepository.append` allocates `sequence` via
`SELECT COALESCE(MAX(sequence), 0) + 1 FROM audit_records;` followed by
the INSERT. Under autocommit (the default before P0 hardening) those
two statements are independently durable, leaving the allocation racy
under any second connection. Inside `KernelUnitOfWork(... BEGIN
IMMEDIATE)` the SELECT and INSERT run in one serialized writer
transaction; this test pins that 5 sequential appends produce the
contiguous sequence range [N+1, ..., N+5] and that the UoW commit makes
the rows durable.
"""

from __future__ import annotations

import os
import sys
import unittest
from uuid import uuid4

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.stores.sqlite.repositories import AuditRepository
from kernel.stores.sqlite.unit_of_work import KernelUnitOfWork
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


class TestAuditAppendInsideUoWMonotonicSequence(unittest.TestCase):
    """Audit `sequence` allocation inside one UoW must be monotonic [1..5]."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit_ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="kernel_unit_of_work_test",
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_audit_append_inside_uow_assigns_monotonic_sequence(self) -> None:
        """Inside one BEGIN IMMEDIATE, 5 appends produce sequences [1..5]."""
        with KernelUnitOfWork(self.conn):
            for i in range(5):
                self.audit_ledger.append(
                    record_type=f"uow_seq_probe_{i}",
                    task_id=f"task-{uuid4().hex[:8]}",
                    artifact_refs=[f"probe-{i}"],
                    payload={"i": i},
                )

        # After UoW exits successfully the rows are durable.
        rows = self.conn.execute(
            "SELECT sequence FROM audit_records "
            "WHERE record_type LIKE 'uow_seq_probe_%' "
            "ORDER BY sequence;"
        ).fetchall()
        sequences = [int(row["sequence"]) for row in rows]
        self.assertEqual(sequences, [1, 2, 3, 4, 5])


if __name__ == "__main__":
    unittest.main()
