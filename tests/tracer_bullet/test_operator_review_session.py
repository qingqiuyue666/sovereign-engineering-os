"""Tracer-bullet tests for operator review session."""

import unittest
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_review_session import (
    OperatorReviewSession,
    build_operator_review_session,
    validate_review_session_material,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64


class ReviewSessionBuildTests(unittest.TestCase):
    """Test building valid pending review sessions."""

    def test_builds_valid_pending_session_from_accepted_promotion(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.assertTrue(validate_review_session_material(session))
        self.assertEqual(session.operator_action, "pending")
        self.assertTrue(session.promotion_accepted)

    def test_builds_valid_pending_session_from_rejected_promotion(self):
        """Rejected promotion can create a pending session for audit trail."""
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="rejected",
            promotion_accepted=False,
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertTrue(validate_review_session_material(session))
        self.assertEqual(session.operator_action, "pending")
        self.assertFalse(session.promotion_accepted)
        self.assertEqual(session.rollback_plan_hash, VALID_DIGEST_3)

    def test_builds_session_with_rollback_plan_hash(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="rejected",
            promotion_accepted=False,
            rollback_plan_hash=VALID_DIGEST_3,
            operator_action="rejected",
            decision_reason_code="operator_rejected",
        )
        self.assertTrue(validate_review_session_material(session))
        self.assertEqual(session.rollback_plan_hash, VALID_DIGEST_3)
        self.assertEqual(session.operator_action, "rejected")


class ReviewSessionFailClosedTests(unittest.TestCase):
    """Test fail-closed behavior."""

    def test_rejected_promotion_cannot_be_approved(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="rejected",
                promotion_accepted=False,
                operator_action="approved",
            )

    def test_invalid_operator_action_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="eligible_for_human_review",
                promotion_accepted=True,
                operator_action="invalid_action",
            )

    def test_missing_review_packet_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash="not-a-digest",
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="eligible_for_human_review",
                promotion_accepted=True,
            )

    def test_missing_promotion_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash="not-a-digest",
                promotion_decision="eligible_for_human_review",
                promotion_accepted=True,
            )

    def test_empty_session_id_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="eligible_for_human_review",
                promotion_accepted=True,
            )

    def test_approval_blocked_when_promotion_rejected(self):
        """Approval is blocked even with explicit operator_action approved on rejected promotion."""
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="rejected",
                promotion_accepted=False,
                operator_action="approved",
            )

    def test_invalid_rollback_plan_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            build_operator_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_decision="rejected",
                promotion_accepted=False,
                rollback_plan_hash="not-a-digest",
            )


class ReviewSessionDeterminismTests(unittest.TestCase):
    """Test deterministic content hashing excludes observation metadata."""

    def test_content_hash_excludes_observed_at(self):
        s1 = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
            observed_at="2026-01-01T00:00:00Z",
        )
        s2 = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(s1.observed_at, s2.observed_at)
        self.assertEqual(s1.content_hash, s2.content_hash)
        self.assertNotIn("observed_at", s1.deterministic_material())
        self.assertNotIn("content_hash", s1.deterministic_material())

    def test_content_hash_changes_with_different_inputs(self):
        s1 = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        s2 = build_operator_review_session(
            session_id="session-002",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.assertNotEqual(s1.content_hash, s2.content_hash)

    def test_rejected_session_deterministic(self):
        s1 = build_operator_review_session(
            session_id="rej-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="rejected",
            promotion_accepted=False,
            rollback_plan_hash=VALID_DIGEST_3,
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            observed_at="2026-01-01T00:00:00Z",
        )
        s2 = build_operator_review_session(
            session_id="rej-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="rejected",
            promotion_accepted=False,
            rollback_plan_hash=VALID_DIGEST_3,
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            observed_at="2027-12-31T23:59:59Z",
        )
        self.assertNotEqual(s1.observed_at, s2.observed_at)
        self.assertEqual(s1.content_hash, s2.content_hash)


class ReviewSessionValidationTests(unittest.TestCase):
    """Test validate_review_session_material."""

    def test_validate_rejects_non_session(self):
        self.assertFalse(validate_review_session_material(None))
        self.assertFalse(validate_review_session_material("not-a-session"))

    def test_validate_accepts_valid_session(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        self.assertTrue(validate_review_session_material(session))

    def test_validate_rejects_approved_on_rejected_promotion(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="rejected",
            promotion_accepted=False,
            rollback_plan_hash=VALID_DIGEST_3,
            operator_action="rejected",
            decision_reason_code="operator_rejected",
        )
        self.assertTrue(validate_review_session_material(session))
        self.assertEqual(session.operator_action, "rejected")
        self.assertFalse(session.promotion_accepted)

    def test_validate_rejects_tampered_content_hash(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
        )
        tampered = OperatorReviewSession(
            session_id=session.session_id,
            run_id=session.run_id,
            task_id=session.task_id,
            review_packet_hash=session.review_packet_hash,
            promotion_receipt_hash=session.promotion_receipt_hash,
            promotion_decision=session.promotion_decision,
            promotion_accepted=session.promotion_accepted,
            rollback_plan_hash=session.rollback_plan_hash,
            operator_action=session.operator_action,
            decision_reason_code=session.decision_reason_code,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_review_session_material(tampered))

    def test_as_dict_includes_observed_at_and_content_hash(self):
        session = build_operator_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_decision="eligible_for_human_review",
            promotion_accepted=True,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = session.as_dict()
        self.assertEqual(d["content_hash"], session.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")


class ReviewSessionSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/operator_review_session.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source, f"forbidden import: {marker}")
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source, f"forbidden env access: {marker}")

    def test_source_does_not_contain_raw_dump_patterns(self):
        import re
        source = Path("kernel/runtime/operator_review_session.py").read_text(encoding="utf-8")
        # Strip docstrings before checking — the docstring says "no secrets"
        # which is a security boundary statement, not a leakage.
        code_only = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", '', code_only, flags=re.DOTALL)
        code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
        for marker in ("raw_prompt", "raw_response", "raw_exception", "raw_traceback",
                       "secret", "api_key", "password", "private_key", "authorization"):
            self.assertNotIn(marker.lower(), code_only.lower(),
                           f"forbidden pattern in code: {marker}")


if __name__ == "__main__":
    unittest.main()
