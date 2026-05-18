"""Tracer-bullet tests for local runtime rollback plan."""

import unittest
from pathlib import Path

from kernel.runtime.local_runtime_rollback_plan import (
    RollbackPlanReceipt,
    build_rollback_plan,
    validate_rollback_plan,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64


class RollbackPlanBuildTests(unittest.TestCase):
    def test_builds_valid_deterministic_rollback_plan(self):
        plan = build_rollback_plan(
            rollback_scope="manual_review_gate_promotion_rejected",
            affected_run_id="run-001",
            affected_task_id="task-001",
            receipt_hashes_to_discard=(VALID_DIGEST,),
            audit_refs_to_preserve=("audit-ref-001",),
            manual_operator_steps=("review_failure_reasons", "confirm_rejection", "archive_run"),
        )
        self.assertTrue(validate_rollback_plan(plan))
        self.assertEqual(plan.rollback_scope, "manual_review_gate_promotion_rejected")

    def test_content_hash_is_deterministic(self):
        p1 = build_rollback_plan(
            rollback_scope="rejected_promotion",
            affected_run_id="run-001",
            affected_task_id="task-001",
            receipt_hashes_to_discard=(VALID_DIGEST,),
            manual_operator_steps=("step_1", "step_2"),
            observed_at="2026-01-01T00:00:00Z",
        )
        p2 = build_rollback_plan(
            rollback_scope="rejected_promotion",
            affected_run_id="run-001",
            affected_task_id="task-001",
            receipt_hashes_to_discard=(VALID_DIGEST,),
            manual_operator_steps=("step_1", "step_2"),
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(p1.observed_at, p2.observed_at)
        self.assertEqual(p1.content_hash, p2.content_hash)
        self.assertEqual(p1.deterministic_material(), p2.deterministic_material())
        self.assertNotIn("observed_at", p1.deterministic_material())

    def test_only_symbolic_steps_allowed(self):
        plan = build_rollback_plan(
            rollback_scope="test",
            affected_run_id="run-001",
            affected_task_id="task-001",
            manual_operator_steps=(
                "STEP_REVIEW_FAILURES",
                "STEP_CONFIRM_REJECTION",
                "STEP_PRESERVE_AUDIT_TRAIL",
            ),
        )
        self.assertTrue(validate_rollback_plan(plan))

    def test_rejects_shell_commands_in_steps(self):
        for bad_step in ("rm -rf /tmp/run", "DELETE FROM runs", "sudo reboot"):
            with self.assertRaises(ValueError, msg=f"should reject: {bad_step}"):
                build_rollback_plan(
                    rollback_scope="test",
                    affected_run_id="run-001",
                    affected_task_id="task-001",
                    manual_operator_steps=(bad_step,),
                )

    def test_rejects_forbidden_field_references_in_steps(self):
        for bad_step in (
            "use_raw_exception_text",
            "include_api_key_here",
            "store_secret_value",
            "read_env_value",
            "execute_shell_command",
            "perform_database_mutation",
        ):
            with self.assertRaises(ValueError, msg=f"should reject step: {bad_step}"):
                build_rollback_plan(
                    rollback_scope="test",
                    affected_run_id="run-001",
                    affected_task_id="task-001",
                    manual_operator_steps=(bad_step,),
                )

    def test_rejects_raw_prompt_raw_response_env_secret_fields(self):
        """Prove that raw_prompt/raw_response/env/secret field names in steps are rejected."""
        for forbidden in (
            "output_raw_prompt",
            "save_raw_provider_response",
            "use_secret",
            "read_env",
            "write_token_file",
        ):
            with self.assertRaises(ValueError, msg=f"should reject: {forbidden}"):
                build_rollback_plan(
                    rollback_scope="test",
                    affected_run_id="run-001",
                    affected_task_id="task-001",
                    manual_operator_steps=(forbidden,),
                )

    def test_rejects_exec_eval_subprocess_in_steps(self):
        for bad_step in (
            "exec(malicious)",
            "eval(code)",
            "os.system('cmd')",
        ):
            with self.assertRaises(ValueError, msg=f"should reject: {bad_step}"):
                build_rollback_plan(
                    rollback_scope="test",
                    affected_run_id="run-001",
                    affected_task_id="task-001",
                    manual_operator_steps=(bad_step,),
                )

    def test_as_dict_includes_observed_at_and_content_hash(self):
        plan = build_rollback_plan(
            rollback_scope="test",
            affected_run_id="run-001",
            affected_task_id="task-001",
            manual_operator_steps=("STEP_1",),
            observed_at="2026-01-01T00:00:00Z",
        )
        d = plan.as_dict()
        self.assertEqual(d["content_hash"], plan.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")


class RollbackPlanValidationTests(unittest.TestCase):
    def test_validate_rejects_non_plan(self):
        self.assertFalse(validate_rollback_plan(None))
        self.assertFalse(validate_rollback_plan("not-a-plan"))

    def test_validate_rejects_tampered_content_hash(self):
        plan = build_rollback_plan(
            rollback_scope="test",
            affected_run_id="run-001",
            affected_task_id="task-001",
            manual_operator_steps=("STEP_1",),
        )
        tampered = RollbackPlanReceipt(
            rollback_scope=plan.rollback_scope,
            affected_run_id=plan.affected_run_id,
            affected_task_id=plan.affected_task_id,
            receipt_hashes_to_discard=plan.receipt_hashes_to_discard,
            audit_refs_to_preserve=plan.audit_refs_to_preserve,
            manual_operator_steps=plan.manual_operator_steps,
            content_hash="sha256:" + "f" * 64,
        )
        self.assertFalse(validate_rollback_plan(tampered))

    def test_empty_steps_are_valid(self):
        plan = build_rollback_plan(
            rollback_scope="no_steps_needed",
            affected_run_id="run-001",
            affected_task_id="task-001",
            manual_operator_steps=(),
        )
        self.assertTrue(validate_rollback_plan(plan))


class RollbackPlanSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        source = Path("kernel/runtime/local_runtime_rollback_plan.py").read_text(encoding="utf-8")
        for marker in ("import subprocess", "import socket", "import requests",
                       "import httpx", "import sqlite3"):
            self.assertNotIn(marker, source)
        for marker in ("os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
