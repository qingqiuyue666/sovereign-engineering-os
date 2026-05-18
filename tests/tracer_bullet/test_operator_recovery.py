"""Tracer-bullet tests for operator control-plane recovery."""

import tempfile
import unittest
from pathlib import Path

from kernel.runtime.operator_decision_ledger import build_ledger_entry
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_recovery import recover_operator_control_plane
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_review_store import OperatorReviewStore

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


class OperatorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.decision_path = root / "decisions.jsonl"
        self.review_path = root / "reviews.jsonl"
        self.decision_store = OperatorDecisionStore(self.decision_path, store_id="decision-store-001")
        self.review_store = OperatorReviewStore(self.review_path, store_id="review-store-001")

    def _append_decision(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.decision_store.append_entry(entry)
        return entry

    def _append_review_session(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.review_store.append_session(session)

    def test_recovery_from_valid_decision_store(self):
        entry = self._append_decision()
        receipt = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(receipt.recovered)
        self.assertEqual(receipt.total_decision_records, 1)
        self.assertEqual(receipt.reconstructed_decision_chain_head, self.decision_store.rebuild_ledger().decision_chain_head)
        self.assertEqual(receipt.session_action_summary[0]["session_id"], entry.session_id)

    def test_recovery_from_valid_decision_and_review_stores(self):
        self._append_decision()
        self._append_review_session()
        receipt = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            review_store_path=self.review_path,
            review_store_id="review-store-001",
        )
        self.assertTrue(receipt.recovered)
        self.assertEqual(receipt.total_review_records, 1)
        self.assertIsNotNone(receipt.review_store_verification_hash)

    def test_recovery_fails_closed_on_tampered_decision_store(self):
        self._append_decision()
        raw = self.decision_path.read_text(encoding="utf-8")
        self.decision_path.write_text(raw.replace("entry-001", "entry-999"), encoding="utf-8")
        receipt = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
        )
        self.assertFalse(receipt.recovered)
        self.assertTrue(receipt.reasons)

    def test_recovery_fails_closed_on_partial_record(self):
        self._append_decision()
        self.decision_path.write_text(self.decision_path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        receipt = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
        )
        self.assertFalse(receipt.recovered)
        self.assertIn("partial_final_record", receipt.reasons)

    def test_recovery_content_hash_deterministic(self):
        self._append_decision()
        first = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(first.content_hash, second.content_hash)

    def test_observed_at_excluded(self):
        self._append_decision()
        first = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = recover_operator_control_plane(
            recovery_id="recovery-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/operator_recovery.py").read_text(encoding="utf-8")
        for marker in (
            "import subprocess",
            "import socket",
            "import requests",
            "import httpx",
            "import sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
