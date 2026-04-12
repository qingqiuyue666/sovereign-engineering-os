"""
AT-009: Seal-time file truth mismatch must abort.

Constitutional anchors:
- v11 Section 22.1 WAL Durability and Recovery Contract
- v11 Section 22.2 Seal Transaction Ordering Contract
- v11 Section 24.1 AT-009
- v11 Section 24.2 INV-004 / INV-005
- Foundation Section 3 item 12 (git = file-content truth)

What this test proves:
  A sealed revision that was persisted through the nine-step ordering
  is immutable at the SQL layer. Attempting to modify a sealed
  revision (simulating a file-truth mismatch reconciliation attempt)
  must be rejected by the database trigger.
"""

from __future__ import annotations

import unittest
import sqlite3
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from kernel.stores.sqlite.wal_recovery import open_connection, apply_migrations
from kernel.stores.sqlite.repositories import RevisionRepository


class TestSealFileTruthMismatch(unittest.TestCase):
    """AT-009 / INV-005: sealed revision immutability at SQL layer."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.rev_repo = RevisionRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def _create_and_seal(self, revision_id: str) -> None:
        self.rev_repo.insert_pending({
            "revision_id": revision_id,
            "parent_revision_id": None,
            "project_id": "p1",
            "task_id": "t1",
            "root_hash": "rh-original",
            "snapshot_root_id": "snap-1",
            "intent_id": "i1",
            "originating_context_artifact_id": "ctx-1",
            "approval_id": None,
            "logical_sequence_at_seal": 0,
            "version_tuple_hash": "vth1:test",
            "taint_set": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self.rev_repo.transition_to_sealed(
            revision_id=revision_id,
            sealed_at=datetime.now(timezone.utc).isoformat(),
            logical_sequence_at_seal=1,
            approval_id="ap-1",
        )

    def test_sealed_revision_update_blocked(self) -> None:
        """UPDATE on a sealed revision must be blocked by SQL trigger."""
        self._create_and_seal("rev-at009-update")
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "UPDATE revisions SET root_hash = 'tampered' "
                "WHERE revision_id = 'rev-at009-update';"
            )

    def test_sealed_revision_delete_blocked(self) -> None:
        """DELETE on a sealed revision must be blocked by SQL trigger."""
        self._create_and_seal("rev-at009-delete")
        with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            self.conn.execute(
                "DELETE FROM revisions WHERE revision_id = 'rev-at009-delete';"
            )

    def test_pending_revision_can_be_updated(self) -> None:
        """A pending revision can still be updated (not yet sealed)."""
        self.rev_repo.insert_pending({
            "revision_id": "rev-pending",
            "parent_revision_id": None,
            "project_id": "p1",
            "task_id": "t1",
            "root_hash": "rh-pending",
            "snapshot_root_id": "snap-2",
            "intent_id": "i2",
            "originating_context_artifact_id": "ctx-2",
            "approval_id": None,
            "logical_sequence_at_seal": 0,
            "version_tuple_hash": "vth1:test",
            "taint_set": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # This should succeed (pending revisions are mutable).
        self.conn.execute(
            "UPDATE revisions SET root_hash = 'new-hash' "
            "WHERE revision_id = 'rev-pending';"
        )
        row = self.rev_repo.fetch("rev-pending")
        self.assertEqual(row["root_hash"], "new-hash")


if __name__ == "__main__":
    unittest.main()
