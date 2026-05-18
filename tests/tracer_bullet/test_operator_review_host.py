"""Tracer-bullet tests for operator review host."""

import unittest
from pathlib import Path

from kernel.runtime.operator_review_host import (
    ReviewSessionResult,
    host_review_session,
    process_operator_approval,
    process_operator_rejection,
    validate_review_session_result,
)
from kernel.runtime.operator_review_session import validate_review_session_material
from kernel.runtime.operator_review_receipt import (
    validate_approval_receipt,
    validate_rejection_receipt,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64


class HostPendingSessionTests(unittest.TestCase):
    """Test that accepted promotion creates a pending review session."""

    def test_accepted_promotion_creates_pending_session(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertTrue(validate_review_session_material(result.session))
        self.assertEqual(result.session.operator_action, "pending")
        self.assertIsNone(result.approval_receipt)
        self.assertIsNone(result.rejection_receipt)

    def test_rejected_promotion_creates_pending_session(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=False,
            promotion_decision="rejected",
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertFalse(result.session.promotion_accepted)
        self.assertEqual(result.session.rollback_plan_hash, VALID_DIGEST_3)


class HostFailClosedTests(unittest.TestCase):
    """Test that rejected promotion result fail closed."""

    def test_rejected_promotion_cannot_generate_approval_receipt(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_accepted=False,
                promotion_decision="rejected",
                operator_action="approved",
            )

    def test_missing_review_packet_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash="not-a-digest",
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_accepted=True,
                promotion_decision="eligible_for_human_review",
            )

    def test_missing_promotion_receipt_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash="not-a-digest",
                promotion_accepted=True,
                promotion_decision="eligible_for_human_review",
            )

    def test_invalid_operator_action_fail_closed(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_accepted=True,
                promotion_decision="eligible_for_human_review",
                operator_action="invalid_action",
            )

    def test_empty_session_id_fail_closed(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_accepted=True,
                promotion_decision="eligible_for_human_review",
            )

    def test_invalid_rollback_plan_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            host_review_session(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash=VALID_DIGEST_2,
                promotion_accepted=False,
                promotion_decision="rejected",
                rollback_plan_hash="not-a-digest",
            )


class HostApprovalTests(unittest.TestCase):
    """Test explicit operator approval through the host."""

    def test_explicit_approved_action_generates_approval_receipt(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertEqual(result.session.operator_action, "approved")
        self.assertIsNotNone(result.approval_receipt)
        self.assertIsNone(result.rejection_receipt)
        self.assertTrue(validate_approval_receipt(result.approval_receipt))

    def test_approval_receipt_does_not_enable_production_autonomy(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
        )
        self.assertFalse(result.approval_receipt.production_autonomy_enabled)

    def test_approval_receipt_does_not_enable_live_execution(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
        )
        self.assertFalse(result.approval_receipt.live_execution_enabled)

    def test_process_operator_approval_direct(self):
        receipt = process_operator_approval(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_approval_receipt(receipt))
        self.assertEqual(receipt.operator_action, "approved")
        self.assertFalse(receipt.production_autonomy_enabled)
        self.assertFalse(receipt.live_execution_enabled)


class HostRejectionTests(unittest.TestCase):
    """Test explicit operator rejection through the host."""

    def test_explicit_rejected_action_generates_rejection_receipt(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertEqual(result.session.operator_action, "rejected")
        self.assertIsNone(result.approval_receipt)
        self.assertIsNotNone(result.rejection_receipt)
        self.assertTrue(validate_rejection_receipt(result.rejection_receipt))

    def test_rejection_receipt_preserves_rollback_plan_hash(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertEqual(result.rejection_receipt.rollback_plan_hash, VALID_DIGEST_3)

    def test_rejection_receipt_hard_disables_production_autonomy(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertFalse(result.rejection_receipt.production_autonomy_enabled)

    def test_rejection_receipt_hard_disables_live_execution(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertFalse(result.rejection_receipt.live_execution_enabled)

    def test_process_operator_rejection_direct(self):
        receipt = process_operator_rejection(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(validate_rejection_receipt(receipt))
        self.assertEqual(receipt.operator_action, "rejected")
        self.assertEqual(receipt.rollback_plan_hash, VALID_DIGEST_3)
        self.assertFalse(receipt.approved_for_next_stage)


class HostDeterminismTests(unittest.TestCase):
    """Test deterministic output: observed_at excluded from all hashes."""

    def test_observed_at_excluded_from_session_hash(self):
        r1 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(r1.session.observed_at, r2.session.observed_at)
        self.assertEqual(r1.session.content_hash, r2.session.content_hash)

    def test_observed_at_excluded_from_approval_receipt_hash(self):
        r1 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertEqual(
            r1.approval_receipt.content_hash,
            r2.approval_receipt.content_hash,
        )

    def test_observed_at_excluded_from_rejection_receipt_hash(self):
        r1 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertEqual(
            r1.rejection_receipt.content_hash,
            r2.rejection_receipt.content_hash,
        )

    def test_observed_at_excluded_from_result_hash(self):
        r1 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotIn("observed_at", r1.deterministic_material())
        self.assertEqual(r1.content_hash, r2.content_hash)


class HostResultValidationTests(unittest.TestCase):
    """Test validate_review_session_result."""

    def test_validate_rejects_non_result(self):
        self.assertFalse(validate_review_session_result(None))
        self.assertFalse(validate_review_session_result("not-a-result"))

    def test_validate_accepts_pending_result(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
        )
        self.assertTrue(validate_review_session_result(result))

    def test_validate_accepts_approved_result(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="approved",
            decision_reason_code="operator_approved",
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertIsNotNone(result.approval_receipt)

    def test_validate_accepts_rejected_result(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            operator_action="rejected",
            decision_reason_code="operator_rejected",
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertTrue(validate_review_session_result(result))
        self.assertIsNotNone(result.rejection_receipt)

    def test_result_as_dict_includes_observed_at(self):
        result = host_review_session(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            promotion_accepted=True,
            promotion_decision="eligible_for_human_review",
            observed_at="2026-01-01T00:00:00Z",
        )
        d = result.as_dict()
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(d["content_hash"], result.content_hash)


class HostSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/operator_review_host.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source, f"forbidden import: {marker}")
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source, f"forbidden env access: {marker}")

    def test_source_does_not_contain_raw_dump_patterns(self):
        import re
        source = Path("kernel/runtime/operator_review_host.py").read_text(encoding="utf-8")
        code_only = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", '', code_only, flags=re.DOTALL)
        code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
        for marker in ("raw_prompt", "raw_response", "raw_exception", "raw_traceback",
                       "secret", "api_key", "password", "private_key", "authorization"):
            self.assertNotIn(marker.lower(), code_only.lower(),
                           f"forbidden pattern in code: {marker}")

    def test_source_does_not_contain_production_autonomy_enablement(self):
        source = Path("kernel/runtime/operator_review_host.py").read_text(encoding="utf-8")
        self.assertNotIn("production_autonomy_enabled = True", source)
        self.assertNotIn("live_execution_enabled = True", source)


if __name__ == "__main__":
    unittest.main()
