"""Tracer-bullet tests for read-only operator CLI status helpers."""

import tempfile
import unittest
from pathlib import Path

from apps.operator_cli.decision_status import (
    render_decision_status_text,
    summarize_decision_store,
)
from apps.operator_cli.review_status import (
    render_review_status_text,
    summarize_review_store,
)
from kernel.runtime.operator_decision_ledger import build_ledger_entry
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_review_store import OperatorReviewStore

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


class OperatorCliReadOnlyStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.decision_path = root / "decisions.jsonl"
        self.review_path = root / "reviews.jsonl"

    def _decision_store(self):
        store = OperatorDecisionStore(self.decision_path, store_id="decision-store-001")
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        store.append_entry(entry)

    def _review_store(self):
        store = OperatorReviewStore(self.review_path, store_id="review-store-001")
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        store.append_session(session)

    def test_can_summarize_valid_decision_store(self):
        self._decision_store()
        status = summarize_decision_store(self.decision_path, store_id="decision-store-001")
        self.assertEqual(status.total_records, 1)
        self.assertEqual(status.pending_count, 1)
        self.assertTrue(status.content_hash.startswith("sha256:"))

    def test_can_summarize_valid_review_store(self):
        self._review_store()
        status = summarize_review_store(self.review_path, store_id="review-store-001")
        self.assertEqual(status.total_records, 1)
        self.assertEqual(status.session_count, 1)
        self.assertTrue(status.content_hash.startswith("sha256:"))

    def test_fails_closed_on_invalid_store(self):
        self._decision_store()
        self.decision_path.write_text(self.decision_path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        with self.assertRaises(ValueError):
            summarize_decision_store(self.decision_path, store_id="decision-store-001")

    def test_output_does_not_include_raw_payloads_or_secrets(self):
        self._decision_store()
        self._review_store()
        decision_text = render_decision_status_text(
            summarize_decision_store(self.decision_path, store_id="decision-store-001")
        )
        review_text = render_review_status_text(
            summarize_review_store(self.review_path, store_id="review-store-001")
        )
        combined = decision_text + "\n" + review_text
        for marker in ("raw_prompt", "raw_response", "raw_exception", "secret", "password", "api_key"):
            self.assertNotIn(marker, combined)

    def test_source_safety_checks_pass(self):
        for module_path in (
            Path("apps/operator_cli/decision_status.py"),
            Path("apps/operator_cli/review_status.py"),
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
                self.assertNotIn(marker, source)

    def test_no_makefile_or_root_integrity_wiring_required(self):
        decision_source = Path("apps/operator_cli/decision_status.py").read_text(encoding="utf-8")
        review_source = Path("apps/operator_cli/review_status.py").read_text(encoding="utf-8")
        self.assertNotIn("Makefile", decision_source + review_source)
        self.assertNotIn("governance/root", decision_source + review_source)


if __name__ == "__main__":
    unittest.main()
