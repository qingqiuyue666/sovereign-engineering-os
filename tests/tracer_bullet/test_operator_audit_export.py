"""Tracer-bullet tests for operator audit export reports."""

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.operator_audit_export import build_operator_audit_export_report
from kernel.runtime.operator_decision_ledger import build_ledger_entry
from kernel.runtime.operator_decision_store import OperatorDecisionStore
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_review_store import OperatorReviewStore

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


class OperatorAuditExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.decision_path = root / "decisions.jsonl"
        self.review_path = root / "reviews.jsonl"
        self.decision_store = OperatorDecisionStore(self.decision_path, store_id="decision-store-001")
        self.review_store = OperatorReviewStore(self.review_path, store_id="review-store-001")
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

    def test_export_from_valid_decision_store(self):
        report = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
        )
        self.assertEqual(report.total_decisions, 1)
        self.assertIn("decision_store_verification", report.export_sections)
        self.assertTrue(report.content_hash.startswith("sha256:"))

    def test_export_includes_chain_head_and_counts(self):
        self._append_review_session()
        report = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            review_store_path=self.review_path,
            review_store_id="review-store-001",
        )
        self.assertEqual(report.decision_chain_head, self.decision_store.rebuild_ledger().decision_chain_head)
        self.assertEqual(report.pending_count, 1)
        self.assertEqual(report.approved_count, 0)
        self.assertEqual(report.rejected_count, 0)
        self.assertEqual(report.session_count, 1)

    def test_export_hash_deterministic(self):
        first = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(first.content_hash, second.content_hash)

    def test_observed_at_excluded(self):
        first = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_operator_audit_export_report(
            export_id="export-001",
            decision_store_path=self.decision_path,
            decision_store_id="decision-store-001",
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_tampered_verification_receipt_fails_closed(self):
        verification = self.decision_store.verify_store()
        tampered = replace(verification, content_hash=VALID_DIGEST_2)
        with self.assertRaises(ValueError):
            build_operator_audit_export_report(
                export_id="export-001",
                decision_store_path=self.decision_path,
                decision_store_id="decision-store-001",
                decision_store_verification=tampered,
            )

    def test_missing_chain_head_fails_closed(self):
        verification = self.decision_store.verify_store()
        tampered = replace(verification, decision_chain_head="")
        with self.assertRaises(ValueError):
            build_operator_audit_export_report(
                export_id="export-001",
                decision_store_path=self.decision_path,
                decision_store_id="decision-store-001",
                decision_store_verification=tampered,
            )

    def test_raw_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_audit_export_report(
                export_id="export-001",
                decision_store_path=self.decision_path,
                decision_store_id="decision-store-001",
                extra_export_material={"raw_prompt": "blocked"},
            )

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/operator_audit_export.py").read_text(encoding="utf-8")
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
