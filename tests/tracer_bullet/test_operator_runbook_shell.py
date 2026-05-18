"""Tracer-bullet tests for the non-executing operator runbook shell."""

import unittest
from pathlib import Path

from kernel.runtime.operator_review_receipt import build_approval_receipt, build_rejection_receipt
from kernel.runtime.operator_review_session import build_operator_review_session
from kernel.runtime.operator_runbook_shell import build_operator_runbook_shell
from kernel.runtime.operator_work_queue import build_operator_work_queue_from_material

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64


def _session():
    return build_operator_review_session(
        session_id="session-001",
        run_id="run-001",
        task_id="task-001",
        review_packet_hash=VALID_DIGEST,
        promotion_receipt_hash=VALID_DIGEST_2,
        promotion_decision="eligible_for_human_review",
        promotion_accepted=True,
    )


class OperatorRunbookShellTests(unittest.TestCase):
    def _item(self, status):
        approvals = ()
        rejections = ()
        if status == "approved":
            approvals = (
                build_approval_receipt(
                    session_id="session-001",
                    run_id="run-001",
                    task_id="task-001",
                    review_packet_hash=VALID_DIGEST,
                    promotion_receipt_hash=VALID_DIGEST_2,
                ),
            )
        if status == "rejected":
            rejections = (
                build_rejection_receipt(
                    session_id="session-001",
                    run_id="run-001",
                    task_id="task-001",
                    review_packet_hash=VALID_DIGEST,
                    promotion_receipt_hash=VALID_DIGEST_2,
                    rollback_plan_hash=VALID_DIGEST_3,
                ),
            )
        queue = build_operator_work_queue_from_material(
            queue_id="queue-001",
            sessions=(_session(),),
            approval_receipts=approvals,
            rejection_receipts=rejections,
        )
        return queue.items[0]

    def test_pending_review_maps_to_symbolic_review_steps(self):
        plan = build_operator_runbook_shell(
            runbook_id="runbook-001",
            queue_items=(self._item("pending_review"),),
        )
        self.assertIn("operator.review.open_packet", plan.step_ids)
        self.assertIn("operator.review.record_decision", plan.step_ids)

    def test_approved_maps_to_symbolic_next_stage_steps(self):
        plan = build_operator_runbook_shell(
            runbook_id="runbook-001",
            queue_items=(self._item("approved"),),
        )
        self.assertIn("operator.approval.prepare_next_manual_stage", plan.step_ids)

    def test_rejected_maps_to_symbolic_rollback_review_steps(self):
        plan = build_operator_runbook_shell(
            runbook_id="runbook-001",
            queue_items=(self._item("rejected"),),
        )
        self.assertIn("operator.rollback.review_symbolic_plan", plan.step_ids)

    def test_shell_command_text_is_rejected(self):
        with self.assertRaises(ValueError):
            build_operator_runbook_shell(
                runbook_id="runbook-001",
                queue_items=(),
                extra_symbolic_step_ids=("rm -rf /",),
            )

    def test_raw_env_secret_fields_are_rejected(self):
        for field in ("raw_prompt", "env", "secret"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_operator_runbook_shell(
                        runbook_id="runbook-001",
                        queue_items=(),
                        operator_metadata={field: "blocked"},
                    )

    def test_observed_at_excluded(self):
        first = build_operator_runbook_shell(
            runbook_id="runbook-001",
            queue_items=(self._item("pending_review"),),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_operator_runbook_shell(
            runbook_id="runbook-001",
            queue_items=(self._item("pending_review"),),
            observed_at="2027-01-01T00:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/operator_runbook_shell.py").read_text(encoding="utf-8")
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
