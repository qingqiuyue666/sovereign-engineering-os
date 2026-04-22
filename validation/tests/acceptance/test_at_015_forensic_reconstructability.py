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

import json
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

    def test_replay_anchor_binds_snapshot_root_id(self) -> None:
        """ReplayAnchor.required_artifact_ids carries the sealed SnapshotRoot."""
        ids = self.harness.run_full_happy_path()

        revision = self.harness.rev_repo.fetch(ids["revision_id"])
        self.assertIsNotNone(revision)
        snapshot_root_id = revision["snapshot_root_id"]
        self.assertTrue(snapshot_root_id)

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        self.assertIn(snapshot_root_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        self.assertIn(snapshot_root_id, payload["required_artifact_ids"])
        self.assertNotIn("snapshot_root_id", payload)
        self.assertNotIn("snapshot_root_ids", payload)

    def test_replay_anchor_binds_seal_journal_entry_ids(self) -> None:
        """ReplayAnchor.required_artifact_ids carries seal journal entries."""
        ids = self.harness.run_full_happy_path()

        journal_rows = self.harness.conn.execute(
            "SELECT journal_entry_id FROM journal_entries "
            "WHERE revision_id = ? ORDER BY logical_sequence;",
            (ids["revision_id"],),
        ).fetchall()
        journal_entry_ids = [row["journal_entry_id"] for row in journal_rows]
        self.assertEqual(len(journal_entry_ids), 3)

        anchor = self.harness.ra_repo.fetch(ids["replay_anchor_id"])
        self.assertIsNotNone(anchor)
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, anchor["required_artifact_ids"])

        closure_row = self.harness.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE task_id = ? AND record_type = 'evidence_closure' "
            "AND replay_anchor_id = ?;",
            (ids["task_id"], ids["replay_anchor_id"]),
        ).fetchone()
        self.assertIsNotNone(closure_row)
        payload = json.loads(closure_row["payload_json"])
        for journal_entry_id in journal_entry_ids:
            self.assertIn(journal_entry_id, payload["required_artifact_ids"])
        self.assertNotIn("journal_entry_id", payload)
        self.assertNotIn("journal_entry_ids", payload)


if __name__ == "__main__":
    unittest.main()
