"""Tracer-bullet tests for the durable operator review store."""

import json
import tempfile
import unittest
from pathlib import Path

from kernel.audit.hashchain import canonical_json
from kernel.runtime.operator_review_receipt import (
    build_approval_receipt,
    build_rejection_receipt,
)
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_review_store import OperatorReviewStore

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64


def _session(session_id="session-001"):
    return build_operator_review_session(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        promotion_decision="eligible_for_human_review",
        promotion_accepted=True,
        observed_at="2026-01-01T00:00:00Z",
    )


def _approval(session_id="session-001"):
    return build_approval_receipt(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        observed_at="2026-01-01T00:00:00Z",
    )


def _rejection(session_id="session-001"):
    return build_rejection_receipt(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        rollback_plan_hash=VALID_DIGEST_3,
        observed_at="2026-01-01T00:00:00Z",
    )


def _read_records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_records(path: Path, records):
    path.write_text("".join(canonical_json(record) + "\n" for record in records), encoding="utf-8")


class OperatorReviewStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "reviews.jsonl"
        self.store = OperatorReviewStore(self.path, store_id="review-store-001")

    def test_append_pending_session(self):
        receipt = self.store.append_session(_session())
        self.assertEqual(receipt.record_type, "operator_review_session")
        self.assertEqual(receipt.record_sequence, 1)
        self.assertEqual(len(self.store.load_sessions()), 1)

    def test_append_approval_receipt(self):
        self.store.append_session(_session())
        receipt = self.store.append_approval(_approval())
        self.assertEqual(receipt.record_type, "operator_approval_receipt")
        self.assertEqual(len(self.store.load_approval_receipts()), 1)

    def test_append_rejection_receipt(self):
        self.store.append_session(_session())
        receipt = self.store.append_rejection(_rejection())
        self.assertEqual(receipt.record_type, "operator_rejection_receipt")
        self.assertEqual(len(self.store.load_rejection_receipts()), 1)

    def test_reload_all_records(self):
        self.store.append_session(_session())
        self.store.append_approval(_approval())
        reloaded = OperatorReviewStore(self.path, store_id="review-store-001")
        self.assertEqual(len(reloaded.load_sessions()), 1)
        self.assertEqual(len(reloaded.load_approval_receipts()), 1)
        self.assertEqual(len(reloaded.load_rejection_receipts()), 0)

    def test_rebuild_review_history(self):
        self.store.append_session(_session("session-001"))
        self.store.append_session(_session("session-002"))
        self.store.append_rejection(_rejection("session-002"))
        history = self.store.rebuild_review_history()
        self.assertEqual(len(history.sessions), 2)
        self.assertEqual(len(history.approval_receipts), 0)
        self.assertEqual(len(history.rejection_receipts), 1)
        self.assertTrue(history.content_hash.startswith("sha256:"))

    def test_verify_valid_store(self):
        self.store.append_session(_session())
        self.store.append_approval(_approval())
        receipt = self.store.verify_store(observed_at="2026-01-01T00:00:00Z")
        self.assertTrue(receipt.valid)
        self.assertEqual(receipt.total_records, 2)
        self.assertEqual(receipt.session_count, 1)
        self.assertEqual(receipt.approval_count, 1)
        self.assertEqual(receipt.rejection_count, 0)

    def test_wrong_sequence_fails_closed(self):
        self.store.append_session(_session())
        records = _read_records(self.path)
        records[0]["record_sequence"] = 2
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_sessions()

    def test_wrong_previous_record_hash_fails_closed(self):
        self.store.append_session(_session("session-001"))
        self.store.append_session(_session("session-002"))
        records = _read_records(self.path)
        records[1]["previous_record_hash"] = VALID_DIGEST_4
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.rebuild_review_history()

    def test_tampered_session_hash_fails_closed(self):
        self.store.append_session(_session())
        records = _read_records(self.path)
        records[0]["payload"]["content_hash"] = VALID_DIGEST_4
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_sessions()

    def test_tampered_approval_hash_fails_closed(self):
        self.store.append_session(_session())
        self.store.append_approval(_approval())
        records = _read_records(self.path)
        records[1]["payload"]["content_hash"] = VALID_DIGEST_4
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_approval_receipts()

    def test_tampered_rejection_hash_fails_closed(self):
        self.store.append_session(_session())
        self.store.append_rejection(_rejection())
        records = _read_records(self.path)
        records[1]["payload"]["content_hash"] = VALID_DIGEST_4
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_rejection_receipts()

    def test_duplicate_approval_for_same_session_fails_closed(self):
        self.store.append_session(_session())
        self.store.append_approval(_approval())
        with self.assertRaises(ValueError):
            self.store.append_approval(_approval())

    def test_approval_after_rejection_fails_closed(self):
        self.store.append_session(_session())
        self.store.append_rejection(_rejection())
        with self.assertRaises(ValueError):
            self.store.append_approval(_approval())

    def test_rejection_after_approval_fails_closed(self):
        self.store.append_session(_session())
        self.store.append_approval(_approval())
        with self.assertRaises(ValueError):
            self.store.append_rejection(_rejection())

    def test_malformed_json_fails_closed(self):
        self.path.write_text("{not-json}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.rebuild_review_history()
        self.assertFalse(self.store.verify_store().valid)

    def test_partial_final_record_fails_closed(self):
        self.store.append_session(_session())
        self.path.write_text(self.path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.rebuild_review_history()

    def test_observed_at_excluded_from_record_hash(self):
        self.store.append_session(_session())
        records = _read_records(self.path)
        original_hash = records[0]["record_hash"]
        records[0]["observed_at"] = "2027-01-01T00:00:00Z"
        records[0]["payload"]["observed_at"] = "2027-01-01T00:00:00Z"
        _write_records(self.path, records)
        self.assertEqual(_read_records(self.path)[0]["record_hash"], original_hash)
        self.assertEqual(len(self.store.load_sessions()), 1)

    def test_observed_at_excluded_from_verification_hash(self):
        self.store.append_session(_session())
        first = self.store.verify_store(observed_at="2026-01-01T00:00:00Z")
        second = self.store.verify_store(observed_at="2027-01-01T00:00:00Z")
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)


class OperatorReviewStoreSourceSafetyTests(unittest.TestCase):
    def test_source_safety_checks_pass(self):
        for module_path in (
            Path("kernel/runtime/operator_review_store.py"),
            Path("kernel/runtime/operator_review_store_replay.py"),
        ):
            source = module_path.read_text(encoding="utf-8")
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
                self.assertNotIn(marker, source, f"{module_path} contains {marker}")


if __name__ == "__main__":
    unittest.main()
