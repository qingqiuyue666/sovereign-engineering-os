"""Tracer-bullet tests for the operator work queue."""

from dataclasses import replace
import unittest
from pathlib import Path

from kernel.runtime.operator_review_receipt import (
    build_approval_receipt,
    build_rejection_receipt,
)
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_work_queue import build_operator_work_queue_from_material

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64


def _session(session_id="session-001", promotion_accepted=True):
    return build_operator_review_session(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        promotion_decision="eligible_for_human_review" if promotion_accepted else "rejected",
        promotion_accepted=promotion_accepted,
        rollback_plan_hash=None if promotion_accepted else VALID_DIGEST_3,
    )


def _approval(session_id="session-001"):
    return build_approval_receipt(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
    )


def _rejection(session_id="session-001"):
    return build_rejection_receipt(
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        rollback_plan_hash=VALID_DIGEST_3,
    )


class OperatorWorkQueueTests(unittest.TestCase):
    def test_pending_session_becomes_pending_review_queue_item(self):
        queue = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
        )
        self.assertEqual(queue.items[0].queue_status, "pending_review")
        self.assertEqual(queue.pending_review_count, 1)

    def test_approved_session_becomes_approved_item(self):
        queue = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
            approval_receipts=(_approval(),),
        )
        self.assertEqual(queue.items[0].queue_status, "approved")
        self.assertEqual(queue.approved_count, 1)

    def test_rejected_session_becomes_rejected_item(self):
        queue = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
            rejection_receipts=(_rejection(),),
        )
        self.assertEqual(queue.items[0].queue_status, "rejected")
        self.assertEqual(queue.rejected_count, 1)

    def test_invalid_session_fails_closed(self):
        invalid = replace(_session(), content_hash=VALID_DIGEST_3)
        with self.assertRaises(ValueError):
            build_operator_work_queue_from_material(queue_id="queue-001", sessions=(invalid,))

    def test_queue_summary_counts_are_deterministic(self):
        queue = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session("session-001"), _session("session-002", promotion_accepted=False)),
            approval_receipts=(_approval("session-001"),),
            observed_at="2026-01-01T00:00:00Z",
        )
        again = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session("session-001"), _session("session-002", promotion_accepted=False)),
            approval_receipts=(_approval("session-001"),),
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(queue.approved_count, 1)
        self.assertEqual(queue.blocked_count, 1)
        self.assertEqual(queue.content_hash, again.content_hash)

    def test_observed_at_excluded(self):
        first = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.items[0].content_hash, second.items[0].content_hash)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/operator_work_queue.py").read_text(encoding="utf-8")
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
