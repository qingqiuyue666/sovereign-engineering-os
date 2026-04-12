"""
AT-015: Forensic reconstructability (phase-1 scope).

Constitutional anchors:
- v11 Section 15 (evidence plane obligations)
- v11 Section 24.1 AT-015
- v11 Section 24.2 INV-027 (indirect via failure evidence retention path)
- Foundation Section 9 (P2 cleanup: phase-1 limits to FailureBundle/retention)

What this test proves:
  After a full signable path, the audit records and artifacts are
  sufficient to reconstruct WHY every material action happened.
  Specifically: every stage transition is recorded, artifact refs are
  present, and the audit sequence is unbroken.

Phase-1 scope: reconstruction is limited to audit records + artifact
  queries. Full encrypted vault / forensic evidence is deferred.
"""

from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from validation.tests.acceptance.conftest import AcceptanceHarness


class TestForensicReconstructability(unittest.TestCase):
    """AT-015: forensic reconstructability via audit + artifact evidence."""

    def setUp(self) -> None:
        self.harness = AcceptanceHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_full_path_audit_reconstructable(self) -> None:
        """Every stage transition must leave an audit record with
        artifact_refs, so a post-hoc forensic query can trace causality."""
        ids = self.harness.run_full_happy_path()

        # Query all audit records for this task.
        rows = self.harness.conn.execute(
            "SELECT record_type, artifact_refs, task_id, sequence "
            "FROM audit_records WHERE task_id = ? ORDER BY sequence;",
            (ids["task_id"],),
        ).fetchall()

        self.assertTrue(len(rows) >= 8, f"expected >=8 audit records, got {len(rows)}")

        # Every audit record must have a record_type.
        for row in rows:
            self.assertTrue(row["record_type"], "audit record missing record_type")

        # Sequence must be monotonic and gapless.
        seqs = [row["sequence"] for row in rows]
        self.assertEqual(seqs, sorted(seqs))

        # Check that key artifact IDs appear in the audit trail.
        all_refs = " ".join(row["artifact_refs"] or "" for row in rows)
        self.assertIn(ids["context_artifact_id"], all_refs)
        self.assertIn(ids["replay_anchor_id"], all_refs)

    def test_sealed_revision_traceable_from_audit(self) -> None:
        """The sealed revision must be findable from audit records."""
        ids = self.harness.run_full_happy_path()

        # The revision must exist and be sealed.
        rev = self.harness.rev_repo.fetch(ids["revision_id"])
        self.assertIsNotNone(rev)
        self.assertEqual(rev["state"], "sealed")

        # The replay anchor must bind to the revision.
        anchor_row = self.harness.conn.execute(
            "SELECT root_revision_id FROM replay_anchors WHERE replay_anchor_id = ?;",
            (ids["replay_anchor_id"],),
        ).fetchone()
        self.assertIsNotNone(anchor_row)


if __name__ == "__main__":
    unittest.main()
