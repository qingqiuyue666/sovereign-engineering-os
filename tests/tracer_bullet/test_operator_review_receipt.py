"""Tracer-bullet tests for operator review receipts."""

import unittest
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.operator_review_receipt import (
    ApprovalReceipt,
    build_approval_receipt,
    validate_approval_receipt,
    RejectionReceipt,
    build_rejection_receipt,
    validate_rejection_receipt,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64


class ApprovalReceiptBuildTests(unittest.TestCase):
    """Test building valid approval receipts."""

    def test_builds_valid_approval_receipt(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertTrue(validate_approval_receipt(receipt))
        self.assertEqual(receipt.operator_action, "approved")
        self.assertTrue(receipt.approved_for_next_stage)

    def test_approval_receipt_hard_disables_production_autonomy(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertFalse(receipt.production_autonomy_enabled)
        self.assertEqual(receipt.production_autonomy_enabled, False)

    def test_approval_receipt_hard_disables_live_execution(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertFalse(receipt.live_execution_enabled)
        self.assertEqual(receipt.live_execution_enabled, False)

    def test_approval_receipt_hash_is_deterministic(self):
        r1 = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(r1.observed_at, r2.observed_at)
        self.assertEqual(r1.content_hash, r2.content_hash)
        self.assertNotIn("observed_at", r1.deterministic_material())
        self.assertNotIn("content_hash", r1.deterministic_material())

    def test_approved_for_next_stage_is_true_by_default(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertTrue(receipt.approved_for_next_stage)

    def test_approval_operator_action_is_always_approved(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertEqual(receipt.operator_action, "approved")

    def test_approval_receipt_rejects_missing_review_packet_hash(self):
        with self.assertRaises(ValueError):
            build_approval_receipt(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash="not-a-digest",
                promotion_receipt_hash=VALID_DIGEST_2,
            )

    def test_approval_receipt_rejects_missing_promotion_receipt_hash(self):
        with self.assertRaises(ValueError):
            build_approval_receipt(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash="not-a-digest",
            )


class ApprovalReceiptValidationTests(unittest.TestCase):
    """Test validate_approval_receipt."""

    def test_validate_rejects_non_receipt(self):
        self.assertFalse(validate_approval_receipt(None))
        self.assertFalse(validate_approval_receipt("not-a-receipt"))

    def test_validate_rejects_production_autonomy_enabled(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        tampered = ApprovalReceipt(
            session_id=receipt.session_id,
            run_id=receipt.run_id,
            task_id=receipt.task_id,
            review_packet_hash=receipt.review_packet_hash,
            promotion_receipt_hash=receipt.promotion_receipt_hash,
            operator_action=receipt.operator_action,
            approval_scope=receipt.approval_scope,
            approval_reason_code=receipt.approval_reason_code,
            approved_for_next_stage=receipt.approved_for_next_stage,
            production_autonomy_enabled=True,
            content_hash=receipt.content_hash,
        )
        self.assertFalse(validate_approval_receipt(tampered))

    def test_validate_rejects_live_execution_enabled(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        tampered = ApprovalReceipt(
            session_id=receipt.session_id,
            run_id=receipt.run_id,
            task_id=receipt.task_id,
            review_packet_hash=receipt.review_packet_hash,
            promotion_receipt_hash=receipt.promotion_receipt_hash,
            operator_action=receipt.operator_action,
            approval_scope=receipt.approval_scope,
            approval_reason_code=receipt.approval_reason_code,
            approved_for_next_stage=receipt.approved_for_next_stage,
            live_execution_enabled=True,
            content_hash=receipt.content_hash,
        )
        self.assertFalse(validate_approval_receipt(tampered))

    def test_validate_rejects_tampered_content_hash(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        tampered = ApprovalReceipt(
            session_id=receipt.session_id,
            run_id=receipt.run_id,
            task_id=receipt.task_id,
            review_packet_hash=receipt.review_packet_hash,
            promotion_receipt_hash=receipt.promotion_receipt_hash,
            operator_action=receipt.operator_action,
            approval_scope=receipt.approval_scope,
            approval_reason_code=receipt.approval_reason_code,
            approved_for_next_stage=receipt.approved_for_next_stage,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_approval_receipt(tampered))

    def test_as_dict_includes_observed_at(self):
        receipt = build_approval_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = receipt.as_dict()
        self.assertEqual(d["content_hash"], receipt.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")


class RejectionReceiptBuildTests(unittest.TestCase):
    """Test building valid rejection receipts."""

    def test_builds_valid_rejection_receipt(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertTrue(validate_rejection_receipt(receipt))
        self.assertEqual(receipt.operator_action, "rejected")
        self.assertEqual(receipt.rollback_plan_hash, VALID_DIGEST_3)

    def test_rejection_receipt_preserves_rollback_plan_hash(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
        )
        self.assertIsNotNone(receipt.rollback_plan_hash)
        self.assertEqual(receipt.rollback_plan_hash, VALID_DIGEST_3)
        self.assertIn("rollback_plan_hash", receipt.deterministic_material())

    def test_rejection_receipt_hard_disables_production_autonomy(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertFalse(receipt.production_autonomy_enabled)

    def test_rejection_receipt_hard_disables_live_execution(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertFalse(receipt.live_execution_enabled)

    def test_rejection_receipt_approved_for_next_stage_is_false(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        self.assertFalse(receipt.approved_for_next_stage)

    def test_rejection_receipt_hash_is_deterministic(self):
        r1 = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        r2 = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(r1.observed_at, r2.observed_at)
        self.assertEqual(r1.content_hash, r2.content_hash)
        self.assertNotIn("observed_at", r1.deterministic_material())

    def test_rejection_receipt_without_rollback_plan_hash(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=None,
        )
        self.assertTrue(validate_rejection_receipt(receipt))
        self.assertIsNone(receipt.rollback_plan_hash)

    def test_rejection_receipt_rejects_missing_review_packet_hash(self):
        with self.assertRaises(ValueError):
            build_rejection_receipt(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash="not-a-digest",
                promotion_receipt_hash=VALID_DIGEST_2,
            )

    def test_rejection_receipt_rejects_missing_promotion_receipt_hash(self):
        with self.assertRaises(ValueError):
            build_rejection_receipt(
                session_id="session-001",
                run_id="run-001",
                task_id="task-001",
                review_packet_hash=VALID_DIGEST,
                promotion_receipt_hash="not-a-digest",
            )


class RejectionReceiptValidationTests(unittest.TestCase):
    """Test validate_rejection_receipt."""

    def test_validate_rejects_non_receipt(self):
        self.assertFalse(validate_rejection_receipt(None))
        self.assertFalse(validate_rejection_receipt("not-a-receipt"))

    def test_validate_rejects_approved_for_next_stage_true(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        tampered = RejectionReceipt(
            session_id=receipt.session_id,
            run_id=receipt.run_id,
            task_id=receipt.task_id,
            review_packet_hash=receipt.review_packet_hash,
            promotion_receipt_hash=receipt.promotion_receipt_hash,
            operator_action=receipt.operator_action,
            rejection_reason_code=receipt.rejection_reason_code,
            rollback_plan_hash=receipt.rollback_plan_hash,
            approved_for_next_stage=True,
            content_hash=receipt.content_hash,
        )
        self.assertFalse(validate_rejection_receipt(tampered))

    def test_validate_rejects_tampered_content_hash(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
        )
        tampered = RejectionReceipt(
            session_id=receipt.session_id,
            run_id=receipt.run_id,
            task_id=receipt.task_id,
            review_packet_hash=receipt.review_packet_hash,
            promotion_receipt_hash=receipt.promotion_receipt_hash,
            operator_action=receipt.operator_action,
            rejection_reason_code=receipt.rejection_reason_code,
            rollback_plan_hash=receipt.rollback_plan_hash,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_rejection_receipt(tampered))

    def test_as_dict_includes_observed_at(self):
        receipt = build_rejection_receipt(
            session_id="session-001",
            run_id="run-001",
            task_id="task-001",
            review_packet_hash=VALID_DIGEST,
            promotion_receipt_hash=VALID_DIGEST_2,
            rollback_plan_hash=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = receipt.as_dict()
        self.assertEqual(d["content_hash"], receipt.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")


class ReceiptSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/operator_review_receipt.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source, f"forbidden import: {marker}")
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source, f"forbidden env access: {marker}")

    def test_source_does_not_contain_raw_dump_patterns(self):
        import re
        source = Path("kernel/runtime/operator_review_receipt.py").read_text(encoding="utf-8")
        code_only = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", '', code_only, flags=re.DOTALL)
        code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
        for marker in ("raw_prompt", "raw_response", "raw_exception", "raw_traceback",
                       "secret", "api_key", "password", "private_key", "authorization"):
            self.assertNotIn(marker.lower(), code_only.lower(),
                           f"forbidden pattern in code: {marker}")


if __name__ == "__main__":
    unittest.main()
