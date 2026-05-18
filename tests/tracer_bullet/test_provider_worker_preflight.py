"""Tracer-bullet tests for provider worker boundary preflight."""

import unittest
from pathlib import Path

from kernel.runtime.operator_review_receipt import build_approval_receipt
from kernel.runtime.provider_worker_preflight import run_provider_worker_boundary_preflight

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


def _approval():
    return build_approval_receipt(
        session_id="session-001",
        run_id="run-001",
        task_id="task-001",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
    )


def _metadata(approval_hash):
    return {
        "task_id": "task-001",
        "session_id": "session-001",
        "provider_task_ref": "provider-task:local-symbolic-001",
        "budget_policy_ref": "budget-policy:manual-review-001",
        "approval_receipt_hash": approval_hash,
        "production_autonomy_requested": False,
        "execution_mode": "preflight_only",
    }


class ProviderWorkerPreflightTests(unittest.TestCase):
    def test_valid_symbolic_provider_task_passes_preflight(self):
        approval = _approval()
        receipt = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=_metadata(approval.content_hash),
            approval_receipts=(approval,),
        )
        self.assertTrue(receipt.preflight_passed)
        self.assertFalse(receipt.provider_execution_permitted)
        self.assertFalse(receipt.production_autonomy_enabled)

    def test_missing_approval_receipt_fails_closed(self):
        receipt = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=_metadata(VALID_DIGEST),
            approval_receipts=(),
        )
        self.assertFalse(receipt.preflight_passed)
        self.assertIn("approval_receipt_missing", receipt.reasons)

    def test_missing_budget_policy_ref_fails_closed(self):
        approval = _approval()
        metadata = _metadata(approval.content_hash)
        del metadata["budget_policy_ref"]
        receipt = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=metadata,
            approval_receipts=(approval,),
        )
        self.assertFalse(receipt.preflight_passed)
        self.assertIn("budget_policy_ref_missing", receipt.reasons)

    def test_raw_prompt_fails_closed(self):
        approval = _approval()
        metadata = _metadata(approval.content_hash)
        metadata["raw_prompt"] = "blocked"
        receipt = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=metadata,
            approval_receipts=(approval,),
        )
        self.assertFalse(receipt.preflight_passed)
        self.assertIn("forbidden_field_present", receipt.reasons)

    def test_secret_env_fields_fail_closed(self):
        approval = _approval()
        for field in ("secret", "env"):
            with self.subTest(field=field):
                metadata = _metadata(approval.content_hash)
                metadata[field] = "blocked"
                receipt = run_provider_worker_boundary_preflight(
                    preflight_id="preflight-001",
                    task_metadata=metadata,
                    approval_receipts=(approval,),
                )
                self.assertFalse(receipt.preflight_passed)
                self.assertIn("forbidden_field_present", receipt.reasons)

    def test_production_autonomy_request_fails_closed(self):
        approval = _approval()
        metadata = _metadata(approval.content_hash)
        metadata["production_autonomy_requested"] = True
        receipt = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=metadata,
            approval_receipts=(approval,),
        )
        self.assertFalse(receipt.preflight_passed)
        self.assertIn("production_autonomy_request_forbidden", receipt.reasons)

    def test_observed_at_excluded(self):
        approval = _approval()
        first = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=_metadata(approval.content_hash),
            approval_receipts=(approval,),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = run_provider_worker_boundary_preflight(
            preflight_id="preflight-001",
            task_metadata=_metadata(approval.content_hash),
            approval_receipts=(approval,),
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/provider_worker_preflight.py").read_text(encoding="utf-8")
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
