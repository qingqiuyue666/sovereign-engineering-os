"""Tracer-bullet tests for durable operator decision-store replay."""

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.operator_decision_ledger import build_ledger_entry
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_decision_store_replay import replay_decision_store

VALID_DIGEST = "sha256:" + "a" * 64


class OperatorDecisionStoreReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "decisions.jsonl"
        self.store = OperatorDecisionStore(self.path, store_id="decision-store-001")

    def test_replay_valid_store(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.store.append_entry(entry)
        receipt = replay_decision_store(
            self.path,
            store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(receipt.replayed)
        self.assertEqual(receipt.total_records, 1)
        self.assertEqual(receipt.decision_chain_head, self.store.rebuild_ledger().decision_chain_head)
        self.assertTrue(receipt.content_hash.startswith("sha256:"))

    def test_replay_fails_closed_on_partial_record(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.store.append_entry(entry)
        self.path.write_text(self.path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        receipt = replay_decision_store(self.path, store_id="decision-store-001")
        self.assertFalse(receipt.replayed)
        self.assertIn("partial_final_record", receipt.reasons)

    def test_replay_hash_excludes_observed_at(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.store.append_entry(entry)
        first = replay_decision_store(
            self.path,
            store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = replay_decision_store(
            self.path,
            store_id="decision-store-001",
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)


if __name__ == "__main__":
    unittest.main()
