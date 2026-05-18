"""Real operator daily run runtime tracer bullet tests.

Covers all required behaviors:
- daily run request model
- run window validation
- evidence summary binding
- replay receipt binding
- patch receipt binding
- execution receipt binding
- human review gate
- approval gate
- single operator action plan
- no autonomous production action
- no trading
- no network
- deterministic run receipt
- missing run_id rejected
- missing operator_id rejected
- missing evidence summary rejected
- missing replay receipt rejected
- missing human review rejected
- missing approval rejected
- production action rejected
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from operator_daily_run import (  # type: ignore[import-not-found]
    OperatorDailyRun,
    DailyRunRequest,
    RunWindow,
    ReviewGate,
    OperatorRunReceipt,
    OperatorRunFailureReceipt,
    OperatorRunCanonicalHash,
    OperatorRunSecurity,
    produce_operator_run_receipt,
    produce_operator_run_failure_receipt,
)

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64
VALID_SHA256_C = "c" * 64


class TestDailyRunRequest(unittest.TestCase):
    """Daily run request model tests."""

    def test_create_valid_request(self):
        req = DailyRunRequest.create(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review daily evidence", "review-1", "approval-1",
        )
        self.assertTrue(req.is_valid)
        self.assertTrue(req.canonical_hash)

    def test_reject_missing_run_id(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("", "op-1", VALID_SHA256, VALID_SHA256_B, "Review", "review-1", "approval-1")

    def test_reject_missing_operator_id(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "", VALID_SHA256, VALID_SHA256_B, "Review", "review-1", "approval-1")

    def test_reject_missing_evidence_summary(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", "", VALID_SHA256_B, "Review", "review-1", "approval-1")

    def test_reject_invalid_evidence_hash(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", "short", VALID_SHA256_B, "Review", "review-1", "approval-1")

    def test_reject_missing_replay_receipt(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, "", "Review", "review-1", "approval-1")

    def test_reject_invalid_replay_hash(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, "short", "Review", "review-1", "approval-1")

    def test_reject_missing_human_review(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review", "", "approval-1")

    def test_reject_missing_approval(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review", "review-1", "")

    def test_reject_missing_action_plan(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "", "review-1", "approval-1")

    def test_reject_production_action(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "deploy to production", "review-1", "approval-1")

    def test_reject_trading_action(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "execute trading order", "review-1", "approval-1")

    def test_reject_network_action(self):
        with self.assertRaises(ValueError):
            DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "curl http://api.example.com", "review-1", "approval-1")

    def test_request_deterministic(self):
        r1 = DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        r2 = DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        self.assertEqual(r1.request_id, r2.request_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_request_no_raw_payload(self):
        req = DailyRunRequest.create("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        d = req.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestRunWindow(unittest.TestCase):
    """Run window validation tests."""

    def test_valid_window_daily_review(self):
        self.assertTrue(RunWindow.validate("daily_review")["valid"])

    def test_valid_window_incident_response(self):
        self.assertTrue(RunWindow.validate("incident_response")["valid"])

    def test_valid_window_scheduled_maintenance(self):
        self.assertTrue(RunWindow.validate("scheduled_maintenance")["valid"])

    def test_reject_unknown_window(self):
        self.assertFalse(RunWindow.validate("middle_of_night")["valid"])

    def test_reject_empty_window(self):
        self.assertFalse(RunWindow.validate("")["valid"])

    def test_create_window(self):
        w = RunWindow.create("daily_review")
        self.assertTrue(w.is_allowed)
        self.assertTrue(w.window_id)


class TestReviewGate(unittest.TestCase):
    """Human review and approval gate tests."""

    def test_both_present(self):
        self.assertTrue(ReviewGate.validate("review-1", "approval-1")["review_passed"])

    def test_missing_review(self):
        result = ReviewGate.validate("", "approval-1")
        self.assertFalse(result["review_passed"])
        self.assertIn("human_review_present", result["failure_reasons"])

    def test_missing_approval(self):
        result = ReviewGate.validate("review-1", "")
        self.assertFalse(result["review_passed"])
        self.assertIn("approval_present", result["failure_reasons"])

    def test_both_missing(self):
        self.assertFalse(ReviewGate.validate("", "")["review_passed"])

    def test_enforce_passes(self):
        ReviewGate.enforce("review-1", "approval-1")

    def test_enforce_raises(self):
        with self.assertRaises(ValueError):
            ReviewGate.enforce("", "")

    def test_gate_hash(self):
        self.assertEqual(len(ReviewGate.gate_hash("review-1", "approval-1")), 64)


class TestOperatorRunReceipts(unittest.TestCase):
    """Operator run receipt tests."""

    def test_produce_approved_receipt(self):
        receipt = produce_operator_run_receipt("run-1", "op-1", "approved", True, True, True, True)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_production_action)
        self.assertTrue(receipt.canonical_hash)

    def test_produce_rejected_receipt(self):
        receipt = produce_operator_run_receipt("run-1", "op-1", "rejected", False, False, False, False)
        self.assertEqual(receipt.status, "rejected")

    def test_produce_failure_receipt(self):
        receipt = produce_operator_run_failure_receipt("run-1", "missing review", "OP_RUN_MISSING_REVIEW")
        self.assertEqual(receipt.failure_code, "OP_RUN_MISSING_REVIEW")
        self.assertTrue(receipt.no_production_action)

    def test_failure_receipt_requires_fields(self):
        with self.assertRaises(ValueError):
            produce_operator_run_failure_receipt("run-1", "", "CODE")
        with self.assertRaises(ValueError):
            produce_operator_run_failure_receipt("run-1", "reason", "")

    def test_receipt_deterministic(self):
        r1 = produce_operator_run_receipt("run-1", "op-1", "approved", True, True, True, True)
        r2 = produce_operator_run_receipt("run-1", "op-1", "approved", True, True, True, True)
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_no_raw_payload(self):
        r1 = produce_operator_run_receipt("r1", "o1", "approved", True, True, True, True).to_dict()
        r2 = produce_operator_run_failure_receipt("r1", "reason", "CODE").to_dict()
        for r in (r1, r2):
            self.assertNotIn("raw_payload", r)
            self.assertNotIn("raw_data", r)


class TestOperatorRunSecurity(unittest.TestCase):
    """Operator run security boundary tests."""

    def test_validate_clean_action_plan(self):
        self.assertTrue(OperatorRunSecurity.validate_action_plan("Review daily evidence and approve")["valid"])

    def test_reject_production(self):
        self.assertFalse(OperatorRunSecurity.validate_action_plan("deploy to production")["valid"])

    def test_reject_trading(self):
        self.assertFalse(OperatorRunSecurity.validate_action_plan("execute trading orders")["valid"])

    def test_reject_network(self):
        self.assertFalse(OperatorRunSecurity.validate_action_plan("curl http://api.example.com")["valid"])

    def test_reject_autonomous(self):
        self.assertFalse(OperatorRunSecurity.validate_action_plan("autonomous decision execution")["valid"])

    def test_reject_empty_action_plan(self):
        self.assertFalse(OperatorRunSecurity.validate_action_plan("")["valid"])

    def test_no_network_detection(self):
        self.assertTrue(OperatorRunSecurity.validate_no_network("review evidence"))
        self.assertFalse(OperatorRunSecurity.validate_no_network("curl example.com"))

    def test_no_trading_detection(self):
        self.assertTrue(OperatorRunSecurity.validate_no_trading("review evidence"))
        self.assertFalse(OperatorRunSecurity.validate_no_trading("trading review"))

    def test_no_production_detection(self):
        self.assertTrue(OperatorRunSecurity.validate_no_production("review evidence"))
        self.assertFalse(OperatorRunSecurity.validate_no_production("production deploy"))

    def test_security_gates(self):
        gates = OperatorRunSecurity.security_gates()
        self.assertIn("human_review_required", gates)
        self.assertIn("no_autonomous_production_action", gates)
        self.assertTrue(all(gates.values()))


class TestOperatorRunCanonicalHash(unittest.TestCase):
    """Operator run canonical hash tests."""

    def test_canonical_hash(self):
        self.assertEqual(len(OperatorRunCanonicalHash.canonical_hash("a", "b")), 64)

    def test_deterministic(self):
        h1 = OperatorRunCanonicalHash.canonical_hash("a", "b")
        h2 = OperatorRunCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(h1, h2)

    def test_run_hash(self):
        self.assertEqual(len(OperatorRunCanonicalHash.run_hash("r1", "o1", VALID_SHA256, VALID_SHA256_B)), 64)


class TestOperatorDailyRun(unittest.TestCase):
    """Full operator daily run integration tests."""

    def setUp(self):
        self.runtime = OperatorDailyRun()

    def test_full_happy_path(self):
        request = self.runtime.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review daily evidence and approve patches",
            "review-1", "approval-1",
            patch_receipt_hashes=[VALID_SHA256_C],
        )
        receipt = self.runtime.approve(request)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_production_action)
        self.assertEqual(receipt.patch_receipt_hashes, [VALID_SHA256_C])

    def test_missing_review_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review daily evidence", "", "approval-1")

    def test_missing_approval_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review daily evidence", "review-1", "")

    def test_production_action_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "deploy to production", "review-1", "approval-1")

    def test_trading_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "execute trading", "review-1", "approval-1")

    def test_network_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "curl http://api.example.com", "review-1", "approval-1")

    def test_window_validation(self):
        self.assertTrue(self.runtime.validate_window("daily_review")["valid"])

    def test_window_rejection(self):
        self.assertFalse(self.runtime.validate_window("invalid")["valid"])

    def test_patch_and_execution_bindings(self):
        request = self.runtime.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review evidence and patch bindings with local kernel validation",
            "review-1", "approval-1",
            patch_receipt_hashes=[VALID_SHA256],
            execution_receipt_hashes=[VALID_SHA256_B],
        )
        self.assertEqual(len(request.patch_receipt_hashes), 1)
        self.assertEqual(len(request.execution_receipt_hashes), 1)
        receipt = self.runtime.approve(request)
        self.assertEqual(receipt.status, "approved")

    def test_missing_patch_binding_rejected_when_action_mentions_patch(self):
        request = self.runtime.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review evidence and approve patches",
            "review-1", "approval-1",
        )
        with self.assertRaises(ValueError):
            self.runtime.approve(request)

    def test_missing_local_kernel_binding_rejected_when_action_mentions_kernel(self):
        request = self.runtime.create_request(
            "run-1", "op-1", VALID_SHA256, VALID_SHA256_B,
            "Review evidence with local kernel validation",
            "review-1", "approval-1",
        )
        with self.assertRaises(ValueError):
            self.runtime.approve(request)

    def test_failure_receipt_tracks(self):
        self.runtime.produce_failure_receipt("run-1", "missing review", "OP_RUN_MISSING_REVIEW")
        self.assertEqual(self.runtime.failure_count(), 1)

    def test_receipt_count_tracks(self):
        request = self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        self.assertEqual(self.runtime.receipt_count(), 0)
        self.runtime.approve(request)
        self.assertEqual(self.runtime.receipt_count(), 1)

    def test_runtime_hash_changes(self):
        h1 = self.runtime.runtime_hash()
        self.runtime.produce_failure_receipt("run-1", "test", "OP_RUN_TEST_FAILED")
        h2 = self.runtime.runtime_hash()
        self.assertNotEqual(h1, h2)

    def test_reset(self):
        request = self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        self.runtime.approve(request)
        self.runtime.reset()
        self.assertEqual(self.runtime.receipt_count(), 0)
        self.assertEqual(self.runtime.failure_count(), 0)

    def test_no_production_action_in_receipt(self):
        request = self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "Review evidence", "review-1", "approval-1")
        receipt = self.runtime.approve(request)
        self.assertTrue(receipt.no_production_action)

    def test_autonomous_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("run-1", "op-1", VALID_SHA256, VALID_SHA256_B, "autonomous action execution", "review-1", "approval-1")


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in operator modules."""

    def test_no_forbidden_imports(self):
        op_dir = ROOT / "tools" / "operator_daily_run"
        for py_file in op_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name}")
            self.assertNotIn("import socket", src, f"{py_file.name}")
            self.assertNotIn("import requests", src, f"{py_file.name}")
            self.assertNotIn("from urllib", src, f"{py_file.name}")
            self.assertNotIn("import anthropic", src, f"{py_file.name}")
            self.assertNotIn("import openai", src, f"{py_file.name}")

    def test_no_env_reads(self):
        op_dir = ROOT / "tools" / "operator_daily_run"
        for py_file in op_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name}")
            self.assertNotIn("os.environ", src, f"{py_file.name}")
            self.assertNotIn("os.getenv", src, f"{py_file.name}")


if __name__ == "__main__":
    unittest.main()
