"""Tracer-bullet tests for durable operator review-store replay."""

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_review_store import OperatorReviewStore
from kernel.runtime.operator_review_store_replay import replay_review_store

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


class OperatorReviewStoreReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "reviews.jsonl"
        self.store = OperatorReviewStore(self.path, store_id="review-store-001")

    def test_replay_valid_store(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.store.append_session(session)
        receipt = replay_review_store(
            self.path,
            store_id="review-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(receipt.replayed)
        self.assertEqual(receipt.total_records, 1)
        self.assertEqual(receipt.session_count, 1)
        self.assertTrue(receipt.content_hash.startswith("sha256:"))

    def test_replay_fails_closed_on_partial_record(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.store.append_session(session)
        self.path.write_text(self.path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        receipt = replay_review_store(self.path, store_id="review-store-001")
        self.assertFalse(receipt.replayed)
        self.assertIn("partial_final_record", receipt.reasons)

    def test_replay_hash_excludes_observed_at(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.store.append_session(session)
        first = replay_review_store(
            self.path,
            store_id="review-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = replay_review_store(
            self.path,
            store_id="review-store-001",
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)


if __name__ == "__main__":
    unittest.main()
