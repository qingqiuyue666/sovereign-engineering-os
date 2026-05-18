"""Tracer-bullet tests for operator decision snapshot."""

import unittest
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedger,
    build_ledger_entry,
)
from kernel.runtime.operator_decision_snapshot import (
    OperatorDecisionLedgerSnapshot,
    build_ledger_snapshot,
    validate_ledger_snapshot,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64


class SnapshotBuildTests(unittest.TestCase):
    """Test building ledger snapshots."""

    def setUp(self):
        self.ledger = OperatorDecisionLedger()

    def test_builds_snapshot_of_empty_ledger(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        self.assertTrue(validate_ledger_snapshot(snapshot))
        self.assertEqual(snapshot.total_entries, 0)
        self.assertEqual(snapshot.pending_count, 0)
        self.assertEqual(snapshot.approved_count, 0)
        self.assertEqual(snapshot.rejected_count, 0)
        self.assertEqual(snapshot.entry_hashes, ())
        self.assertEqual(snapshot.decision_chain_head, "sha256:" + "0" * 64)

    def test_builds_snapshot_with_entries(self):
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.ledger.append(e1)

        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-002",
            run_id="run-001",
            task_id="task-002",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)

        e3 = build_ledger_entry(
            entry_id="entry-003",
            session_id="session-003",
            run_id="run-001",
            task_id="task-003",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST_2,
            rejection_receipt_hash=VALID_DIGEST_3,
            rollback_plan_hash=VALID_DIGEST_4,
            previous_entry_hash=e2.content_hash,
            sequence_number=3,
        )
        self.ledger.append(e3)

        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        self.assertTrue(validate_ledger_snapshot(snapshot))
        self.assertEqual(snapshot.total_entries, 3)
        self.assertEqual(snapshot.pending_count, 1)
        self.assertEqual(snapshot.approved_count, 1)
        self.assertEqual(snapshot.rejected_count, 1)


class SnapshotCountTests(unittest.TestCase):
    """Test snapshot counts are correct."""

    def test_snapshot_counts_correct(self):
        ledger = OperatorDecisionLedger()

        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger.append(e1)

        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-002",
            run_id="run-001",
            task_id="task-002",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        ledger.append(e2)

        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=ledger,
        )

        self.assertEqual(snapshot.total_entries, 2)
        self.assertEqual(snapshot.pending_count, 1)
        self.assertEqual(snapshot.approved_count, 1)
        self.assertEqual(snapshot.rejected_count, 0)
        self.assertEqual(snapshot.total_entries,
                         snapshot.pending_count + snapshot.approved_count + snapshot.rejected_count)

    def test_snapshot_entry_hashes_match_ledger(self):
        ledger = OperatorDecisionLedger()

        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger.append(e1)

        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-002",
            run_id="run-001",
            task_id="task-002",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        ledger.append(e2)

        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=ledger,
        )
        self.assertEqual(snapshot.entry_hashes, ledger.entry_hashes())
        self.assertEqual(len(snapshot.entry_hashes), 2)
        self.assertEqual(snapshot.entry_hashes[0], e1.content_hash)
        self.assertEqual(snapshot.entry_hashes[1], e2.content_hash)


class SnapshotTamperDetectionTests(unittest.TestCase):
    """Test tamper detection in snapshots."""

    def setUp(self):
        self.ledger = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.ledger.append(e1)

    def test_validate_rejects_non_snapshot(self):
        self.assertFalse(validate_ledger_snapshot(None))
        self.assertFalse(validate_ledger_snapshot("not-a-snapshot"))

    def test_validate_accepts_valid_snapshot(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        self.assertTrue(validate_ledger_snapshot(snapshot))

    def test_validate_rejects_tampered_content_hash(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        tampered = OperatorDecisionLedgerSnapshot(
            ledger_id=snapshot.ledger_id,
            entry_hashes=snapshot.entry_hashes,
            decision_chain_head=snapshot.decision_chain_head,
            total_entries=snapshot.total_entries,
            pending_count=snapshot.pending_count,
            approved_count=snapshot.approved_count,
            rejected_count=snapshot.rejected_count,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_ledger_snapshot(tampered))

    def test_validate_rejects_tampered_total_entries(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        tampered = OperatorDecisionLedgerSnapshot(
            ledger_id=snapshot.ledger_id,
            entry_hashes=snapshot.entry_hashes,
            decision_chain_head=snapshot.decision_chain_head,
            total_entries=999,
            pending_count=snapshot.pending_count,
            approved_count=snapshot.approved_count,
            rejected_count=snapshot.rejected_count,
        )
        self.assertFalse(validate_ledger_snapshot(tampered))

    def test_validate_rejects_tampered_counts(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        tampered = OperatorDecisionLedgerSnapshot(
            ledger_id=snapshot.ledger_id,
            entry_hashes=snapshot.entry_hashes,
            decision_chain_head=snapshot.decision_chain_head,
            total_entries=snapshot.total_entries,
            pending_count=0,
            approved_count=999,
            rejected_count=snapshot.rejected_count,
        )
        self.assertFalse(validate_ledger_snapshot(tampered))

    def test_validate_rejects_tampered_entry_hashes_count(self):
        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        tampered = OperatorDecisionLedgerSnapshot(
            ledger_id=snapshot.ledger_id,
            entry_hashes=(),
            decision_chain_head=snapshot.decision_chain_head,
            total_entries=snapshot.total_entries,
            pending_count=snapshot.pending_count,
            approved_count=snapshot.approved_count,
            rejected_count=snapshot.rejected_count,
        )
        self.assertFalse(validate_ledger_snapshot(tampered))


class SnapshotDeterminismTests(unittest.TestCase):
    """Test observed_at excluded from snapshot hashes."""

    def setUp(self):
        self.ledger = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.ledger.append(e1)

    def test_observed_at_not_in_snapshot_content_hash(self):
        s1 = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
            observed_at="2026-01-01T00:00:00Z",
        )
        s2 = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
            observed_at="2027-12-31T23:59:59Z",
        )
        self.assertNotEqual(s1.observed_at, s2.observed_at)
        self.assertEqual(s1.content_hash, s2.content_hash)
        self.assertNotIn("observed_at", s1.deterministic_material())
        self.assertNotIn("content_hash", s1.deterministic_material())

    def test_snapshot_deterministic_across_builds(self):
        s1 = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
            observed_at="2026-01-01T00:00:00Z",
        )
        s2 = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(s1.content_hash, s2.content_hash)
        self.assertEqual(s1.decision_chain_head, s2.decision_chain_head)

    def test_snapshot_changes_with_different_ledger_id(self):
        s1 = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=self.ledger,
        )
        s2 = build_ledger_snapshot(
            ledger_id="ledger-002",
            ledger=self.ledger,
        )
        self.assertNotEqual(s1.content_hash, s2.content_hash)


class SnapshotAsDictTests(unittest.TestCase):
    """Test snapshot as_dict includes observed_at and content_hash."""

    def test_as_dict_includes_observed_at_and_content_hash(self):
        ledger = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger.append(e1)

        snapshot = build_ledger_snapshot(
            ledger_id="ledger-001",
            ledger=ledger,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = snapshot.as_dict()
        self.assertEqual(d["content_hash"], snapshot.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")


class SnapshotFailClosedTests(unittest.TestCase):
    """Test fail-closed behavior of snapshot builder."""

    def test_empty_ledger_id_fail_closed(self):
        ledger = OperatorDecisionLedger()
        with self.assertRaises(ValueError):
            build_ledger_snapshot(
                ledger_id="",
                ledger=ledger,
            )

    def test_invalid_ledger_type_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_snapshot(
                ledger_id="ledger-001",
                ledger="not-a-ledger",
            )


class SnapshotSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/operator_decision_snapshot.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source, f"forbidden import: {marker}")
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source, f"forbidden env access: {marker}")

    def test_source_does_not_contain_raw_dump_patterns(self):
        import re
        source = Path("kernel/runtime/operator_decision_snapshot.py").read_text(encoding="utf-8")
        code_only = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", '', code_only, flags=re.DOTALL)
        code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
        for marker in ("raw_prompt", "raw_response", "raw_exception", "raw_traceback",
                       "secret", "api_key", "password", "private_key", "authorization"):
            self.assertNotIn(marker.lower(), code_only.lower(),
                           f"forbidden pattern in code: {marker}")

    def test_source_does_not_contain_production_autonomy_enablement(self):
        source = Path("kernel/runtime/operator_decision_snapshot.py").read_text(encoding="utf-8")
        self.assertNotIn("production_autonomy_enabled = True", source)
        self.assertNotIn("live_execution_enabled = True", source)


if __name__ == "__main__":
    unittest.main()
