"""Tracer-bullet tests for operator decision ledger."""

import unittest
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedger,
    OperatorDecisionLedgerEntry,
    build_ledger_entry,
    validate_ledger_entry,
    compute_decision_chain_head,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64
VALID_DIGEST_5 = "sha256:" + "e" * 64


class LedgerEntryBuildTests(unittest.TestCase):
    """Test building valid ledger entries."""

    def test_builds_pending_entry(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.assertTrue(validate_ledger_entry(entry))
        self.assertEqual(entry.operator_action, "pending")
        self.assertIsNone(entry.approval_receipt_hash)
        self.assertIsNone(entry.rejection_receipt_hash)

    def test_builds_approved_entry(self):
        entry = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST,
            approval_receipt_hash=VALID_DIGEST_2,
            previous_entry_hash=VALID_DIGEST_3,
            sequence_number=2,
        )
        self.assertTrue(validate_ledger_entry(entry))
        self.assertEqual(entry.operator_action, "approved")
        self.assertEqual(entry.approval_receipt_hash, VALID_DIGEST_2)
        self.assertIsNone(entry.rejection_receipt_hash)

    def test_builds_rejected_entry(self):
        entry = build_ledger_entry(
            entry_id="entry-003",
            session_id="session-002",
            run_id="run-002",
            task_id="task-002",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST,
            rejection_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            previous_entry_hash=VALID_DIGEST_4,
            sequence_number=3,
        )
        self.assertTrue(validate_ledger_entry(entry))
        self.assertEqual(entry.operator_action, "rejected")
        self.assertEqual(entry.rejection_receipt_hash, VALID_DIGEST_2)
        self.assertEqual(entry.rollback_plan_hash, VALID_DIGEST_3)
        self.assertIsNone(entry.approval_receipt_hash)

    def test_builds_entry_with_rollback_plan_hash(self):
        entry = build_ledger_entry(
            entry_id="entry-004",
            session_id="session-003",
            run_id="run-003",
            task_id="task-003",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST,
            rejection_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            sequence_number=1,
        )
        self.assertEqual(entry.rollback_plan_hash, VALID_DIGEST_3)


class LedgerEntryFailClosedTests(unittest.TestCase):
    """Test fail-closed behavior for invalid ledger entries."""

    def test_invalid_operator_action_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="invalid_action",
                review_session_hash=VALID_DIGEST,
                sequence_number=1,
            )

    def test_missing_review_session_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash="not-a-digest",
                sequence_number=1,
            )

    def test_approval_missing_approval_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="approved",
                review_session_hash=VALID_DIGEST,
                sequence_number=1,
            )

    def test_rejection_missing_rejection_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="rejected",
                review_session_hash=VALID_DIGEST,
                sequence_number=1,
            )

    def test_pending_with_approval_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                approval_receipt_hash=VALID_DIGEST_2,
                sequence_number=1,
            )

    def test_pending_with_rejection_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                rejection_receipt_hash=VALID_DIGEST_2,
                sequence_number=1,
            )

    def test_empty_entry_id_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                sequence_number=1,
            )

    def test_sequence_number_zero_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                sequence_number=0,
            )

    def test_approved_with_rejection_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="approved",
                review_session_hash=VALID_DIGEST,
                approval_receipt_hash=VALID_DIGEST_2,
                rejection_receipt_hash=VALID_DIGEST_3,
                sequence_number=1,
            )

    def test_rejected_with_approval_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="rejected",
                review_session_hash=VALID_DIGEST,
                approval_receipt_hash=VALID_DIGEST_2,
                rejection_receipt_hash=VALID_DIGEST_3,
                sequence_number=1,
            )

    def test_invalid_rollback_plan_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="rejected",
                review_session_hash=VALID_DIGEST,
                rejection_receipt_hash=VALID_DIGEST_2,
                rollback_plan_hash="not-a-digest",
                sequence_number=1,
            )

    def test_invalid_previous_entry_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_ledger_entry(
                entry_id="entry-001",
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                previous_entry_hash="not-a-digest",
                sequence_number=1,
            )


class LedgerAppendOnlyTests(unittest.TestCase):
    """Test append-only in-memory ledger behavior."""

    def setUp(self):
        self.ledger = OperatorDecisionLedger()

    def test_append_pending_entry(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        result = self.ledger.append(entry)
        self.assertEqual(self.ledger.total_entries, 1)
        self.assertEqual(result.entry_id, "entry-001")

    def test_append_approved_entry(self):
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
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)
        self.assertEqual(self.ledger.total_entries, 2)

    def test_append_rejected_entry(self):
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
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST_2,
            rejection_receipt_hash=VALID_DIGEST_3,
            rollback_plan_hash=VALID_DIGEST_4,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)
        self.assertEqual(self.ledger.total_entries, 2)

    def test_sequence_number_continuous_increment(self):
        entries = []
        for i in range(5):
            seq = i + 1
            prev_hash = entries[-1].content_hash if entries else None
            entry = build_ledger_entry(
                entry_id=f"entry-{seq:03d}",
                session_id=f"session-{seq:03d}",
                run_id="run-001",
                task_id="task-001",
                operator_action="pending",
                review_session_hash=VALID_DIGEST,
                previous_entry_hash=prev_hash,
                sequence_number=seq,
            )
            entries.append(self.ledger.append(entry))
        self.assertEqual(self.ledger.total_entries, 5)
        for i, entry in enumerate(entries):
            self.assertEqual(entry.sequence_number, i + 1)

    def test_previous_entry_hash_binds_to_previous_entry(self):
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
        self.assertIsNone(e1.previous_entry_hash)

        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-002",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST_2,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)
        self.assertEqual(e2.previous_entry_hash, e1.content_hash)

    def test_wrong_previous_entry_hash_fail_closed(self):
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
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST_2,
            previous_entry_hash=VALID_DIGEST_5,
            sequence_number=2,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(e2)

    def test_first_entry_with_previous_hash_fail_closed(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            previous_entry_hash=VALID_DIGEST_2,
            sequence_number=1,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(entry)

    def test_sequence_number_skip_fail_closed(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=5,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(entry)

    def test_duplicate_entry_id_fail_closed(self):
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
            entry_id="entry-001",
            session_id="session-002",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST_2,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(e2)

    def test_duplicate_session_approved_fail_closed(self):
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST,
            approval_receipt_hash=VALID_DIGEST_2,
            sequence_number=1,
        )
        self.ledger.append(e1)
        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(e2)

    def test_approved_after_rejected_fail_closed(self):
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST,
            rejection_receipt_hash=VALID_DIGEST_2,
            sequence_number=1,
        )
        self.ledger.append(e1)
        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(e2)

    def test_rejected_after_approved_fail_closed(self):
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST,
            approval_receipt_hash=VALID_DIGEST_2,
            sequence_number=1,
        )
        self.ledger.append(e1)
        e2 = build_ledger_entry(
            entry_id="entry-002",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST_2,
            rejection_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        with self.assertRaises(ValueError):
            self.ledger.append(e2)

    def test_pending_to_approved_transition_allowed(self):
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
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)
        self.assertEqual(self.ledger.total_entries, 2)

    def test_pending_to_rejected_transition_allowed(self):
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
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST_2,
            rejection_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        self.ledger.append(e2)
        self.assertEqual(self.ledger.total_entries, 2)


class LedgerChainHeadTests(unittest.TestCase):
    """Test decision chain head computation."""

    def test_empty_ledger_chain_head_is_genesis(self):
        ledger = OperatorDecisionLedger()
        self.assertEqual(ledger.decision_chain_head, "sha256:" + "0" * 64)

    def test_chain_head_deterministic(self):
        ledger1 = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger1.append(e1)

        ledger2 = OperatorDecisionLedger()
        e2 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger2.append(e2)

        self.assertEqual(ledger1.decision_chain_head, ledger2.decision_chain_head)

    def test_chain_head_changes_with_different_entries(self):
        ledger1 = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger1.append(e1)

        ledger2 = OperatorDecisionLedger()
        e2 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-002",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        ledger2.append(e2)

        self.assertNotEqual(ledger1.decision_chain_head, ledger2.decision_chain_head)

    def test_chain_head_matches_compute_function(self):
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
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST_2,
            approval_receipt_hash=VALID_DIGEST_3,
            previous_entry_hash=e1.content_hash,
            sequence_number=2,
        )
        ledger.append(e2)

        self.assertEqual(
            ledger.decision_chain_head,
            compute_decision_chain_head(ledger.entries),
        )


class LedgerDeterminismTests(unittest.TestCase):
    """Test observed_at exclusion from hashes."""

    def test_observed_at_not_in_entry_content_hash(self):
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
            observed_at="2026-01-01T00:00:00Z",
        )
        e2 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
            observed_at="2027-12-31T23:59:59Z",
        )
        self.assertNotEqual(e1.observed_at, e2.observed_at)
        self.assertEqual(e1.content_hash, e2.content_hash)
        self.assertNotIn("observed_at", e1.deterministic_material())
        self.assertNotIn("content_hash", e1.deterministic_material())

    def test_observed_at_not_in_chain_head(self):
        ledger1 = OperatorDecisionLedger()
        e1 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
            observed_at="2026-01-01T00:00:00Z",
        )
        ledger1.append(e1)

        ledger2 = OperatorDecisionLedger()
        e2 = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
            observed_at="2027-12-31T23:59:59Z",
        )
        ledger2.append(e2)

        self.assertEqual(ledger1.decision_chain_head, ledger2.decision_chain_head)


class LedgerCountTests(unittest.TestCase):
    """Test pending/approved/rejected counting."""

    def test_counts_are_correct(self):
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
        ledger.append(e3)

        self.assertEqual(ledger.total_entries, 3)
        self.assertEqual(ledger.pending_count(), 1)
        self.assertEqual(ledger.approved_count(), 1)
        self.assertEqual(ledger.rejected_count(), 1)

    def test_entry_hashes_match(self):
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

        hashes = ledger.entry_hashes()
        self.assertEqual(len(hashes), 1)
        self.assertEqual(hashes[0], e1.content_hash)


class LedgerEntryValidationTests(unittest.TestCase):
    """Test validate_ledger_entry edge cases."""

    def test_validate_rejects_non_entry(self):
        self.assertFalse(validate_ledger_entry(None))
        self.assertFalse(validate_ledger_entry("not-an-entry"))

    def test_validate_accepts_valid_entry(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        self.assertTrue(validate_ledger_entry(entry))

    def test_validate_rejects_tampered_content_hash(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
        )
        tampered = OperatorDecisionLedgerEntry(
            entry_id=entry.entry_id,
            session_id=entry.session_id,
            run_id=entry.run_id,
            task_id=entry.task_id,
            operator_action=entry.operator_action,
            review_session_hash=entry.review_session_hash,
            approval_receipt_hash=entry.approval_receipt_hash,
            rejection_receipt_hash=entry.rejection_receipt_hash,
            rollback_plan_hash=entry.rollback_plan_hash,
            previous_entry_hash=entry.previous_entry_hash,
            sequence_number=entry.sequence_number,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_ledger_entry(tampered))

    def test_as_dict_includes_observed_at_and_content_hash(self):
        entry = build_ledger_entry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="pending",
            review_session_hash=VALID_DIGEST,
            sequence_number=1,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = entry.as_dict()
        self.assertEqual(d["content_hash"], entry.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")

    def test_validate_rejects_approved_without_approval_hash(self):
        entry = OperatorDecisionLedgerEntry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="approved",
            review_session_hash=VALID_DIGEST,
            approval_receipt_hash=None,
            rejection_receipt_hash=None,
            rollback_plan_hash=None,
            previous_entry_hash=None,
            sequence_number=1,
        )
        self.assertFalse(validate_ledger_entry(entry))

    def test_validate_rejects_rejected_without_rejection_hash(self):
        entry = OperatorDecisionLedgerEntry(
            entry_id="entry-001",
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            operator_action="rejected",
            review_session_hash=VALID_DIGEST,
            approval_receipt_hash=None,
            rejection_receipt_hash=None,
            rollback_plan_hash=None,
            previous_entry_hash=None,
            sequence_number=1,
        )
        self.assertFalse(validate_ledger_entry(entry))


class LedgerSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/operator_decision_ledger.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source, f"forbidden import: {marker}")
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source, f"forbidden env access: {marker}")

    def test_source_does_not_contain_raw_dump_patterns(self):
        import re
        source = Path("kernel/runtime/operator_decision_ledger.py").read_text(encoding="utf-8")
        code_only = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", '', code_only, flags=re.DOTALL)
        code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
        for marker in ("raw_prompt", "raw_response", "raw_exception", "raw_traceback",
                       "secret", "api_key", "password", "private_key", "authorization"):
            self.assertNotIn(marker.lower(), code_only.lower(),
                           f"forbidden pattern in code: {marker}")

    def test_source_does_not_contain_production_autonomy_enablement(self):
        source = Path("kernel/runtime/operator_decision_ledger.py").read_text(encoding="utf-8")
        self.assertNotIn("production_autonomy_enabled = True", source)
        self.assertNotIn("live_execution_enabled = True", source)


if __name__ == "__main__":
    unittest.main()
