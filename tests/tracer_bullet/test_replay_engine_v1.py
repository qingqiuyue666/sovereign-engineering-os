"""Tests for Replay Engine V1."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from kernel.runtime.capability_token_lifecycle import (
    CAPABILITY_TOKEN_SCOPE,
    CapabilityTokenLifecycle,
    REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
)
from kernel.runtime.local_job_queue import LocalJobQueue
from kernel.runtime.real_local_runner_boundary import (
    REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
    REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
)
from kernel.runtime.replay_engine import verify_replay_descriptor


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "replay_engine.py"
POLICY_PATH = ROOT / "governance" / "replay" / "replay_engine_v1.json"
DOC_PATH = ROOT / "docs" / "decisions" / "replay_engine_v1.md"

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
TOKEN_APPROVAL_DIGEST = "sha256:" + "1" * 64
REVISION = "4f6dcb715ba4d0adf93a0ac2f9d3f4e833a0f455"
OBSERVED_AT = "2026-05-25T00:00:00+00:00"


def descriptor(**overrides):
    payload = {
        "replay_id": "replay-001",
        "source_receipt_id": "receipt-source",
        "candidate_receipt_id": "receipt-candidate",
        "expected_command_id": "make_ci",
        "actual_command_id": "make_ci",
        "expected_argv_hash": DIGEST_A,
        "actual_argv_hash": DIGEST_A,
        "expected_resolved_argv_hash": DIGEST_B,
        "actual_resolved_argv_hash": DIGEST_B,
        "expected_executable_path": "/usr/bin/make",
        "actual_executable_path": "/usr/bin/make",
        "expected_executable_realpath": "/usr/bin/make",
        "actual_executable_realpath": "/usr/bin/make",
        "expected_executable_sha256": DIGEST_C,
        "actual_executable_sha256": DIGEST_C,
        "expected_environment_digest": DIGEST_D,
        "actual_environment_digest": DIGEST_D,
        "expected_environment_path_policy_id": REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
        "actual_environment_path_policy_id": REAL_LOCAL_RUNNER_ENVIRONMENT_PATH_POLICY_ID,
        "expected_executable_resolution_policy_id": (
            REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
        ),
        "actual_executable_resolution_policy_id": (
            REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
        ),
        "expected_resolution_policy_digest": DIGEST_E,
        "actual_resolution_policy_digest": DIGEST_E,
        "expected_stdout_sha256": DIGEST_F,
        "actual_stdout_sha256": DIGEST_F,
        "expected_stderr_sha256": DIGEST_A,
        "actual_stderr_sha256": DIGEST_A,
        "expected_receipt_sha256": DIGEST_B,
        "actual_receipt_sha256": DIGEST_B,
        "expected_exit_code": 0,
        "actual_exit_code": 0,
        "automatic_reexecution_allowed": False,
        "expected_token_id": "cap-local-runner-token-001",
        "actual_token_id": "cap-local-runner-token-001",
        "expected_token_receipt_ref": "token-receipt-001",
        "actual_token_receipt_ref": "token-receipt-001",
        "expected_token_command_id": "make_ci",
        "actual_token_command_id": "make_ci",
        "expected_token_scope": CAPABILITY_TOKEN_SCOPE,
        "actual_token_scope": CAPABILITY_TOKEN_SCOPE,
        "expected_token_repo_revision": REVISION,
        "actual_token_repo_revision": REVISION,
        "expected_token_approval_artifact_id": "approval-001",
        "actual_token_approval_artifact_id": "approval-001",
        "expected_token_approval_artifact_digest": TOKEN_APPROVAL_DIGEST,
        "actual_token_approval_artifact_digest": TOKEN_APPROVAL_DIGEST,
        "expected_token_state": "consumed",
        "actual_token_state": "consumed",
        "expected_queue_id": "queue-001",
        "actual_queue_id": "queue-001",
        "expected_queue_job_id": "job-001",
        "actual_queue_job_id": "job-001",
        "expected_queue_job_state": "completed",
        "actual_queue_job_state": "completed",
        "expected_queue_append_only_event_ref": "queue-001:000004:job-001:completed",
        "actual_queue_append_only_event_ref": "queue-001:000004:job-001:completed",
        "expected_queue_runner_receipt_ref": "runner-receipt-001",
        "actual_queue_runner_receipt_ref": "runner-receipt-001",
        "expected_queue_token_receipt_ref": "token-receipt-001",
        "actual_queue_token_receipt_ref": "token-receipt-001",
    }
    payload.update(overrides)
    return payload


class ReplayEngineV1Tests(unittest.TestCase):
    def test_valid_runner_token_and_queue_replay_evidence_verifies(self) -> None:
        report = verify_replay_descriptor(
            descriptor(),
            observed_at=OBSERVED_AT,
        )
        self.assertTrue(report.accepted)
        self.assertTrue(report.replay_match)
        self.assertEqual(report.failure_classification, "REPLAY_MATCH")
        self.assertEqual(report.failures, ())

    def test_runner_evidence_mismatches_fail_with_specific_classes(self) -> None:
        cases = (
            ("actual_command_id", "diff_check", "command_id_mismatch", "COMMAND_MISMATCH"),
            ("actual_argv_hash", DIGEST_C, "argv_hash_mismatch", "ARGV_MISMATCH"),
            (
                "actual_resolved_argv_hash",
                DIGEST_C,
                "resolved_argv_hash_mismatch",
                "RESOLVED_ARGV_MISMATCH",
            ),
            (
                "actual_executable_path",
                "/opt/homebrew/bin/make",
                "executable_path_mismatch",
                "EXECUTABLE_PATH_MISMATCH",
            ),
            (
                "actual_executable_sha256",
                DIGEST_D,
                "executable_sha256_mismatch",
                "EXECUTABLE_SHA256_MISMATCH",
            ),
            (
                "actual_environment_digest",
                DIGEST_E,
                "environment_digest_mismatch",
                "ENVIRONMENT_MISMATCH",
            ),
            (
                "actual_resolution_policy_digest",
                DIGEST_F,
                "resolution_policy_digest_mismatch",
                "RESOLUTION_POLICY_MISMATCH",
            ),
            ("actual_stdout_sha256", DIGEST_C, "stdout_sha256_mismatch", "OUTPUT_MISMATCH"),
            ("actual_stderr_sha256", DIGEST_C, "stderr_sha256_mismatch", "OUTPUT_MISMATCH"),
        )
        for field, value, failure, classification in cases:
            with self.subTest(field=field):
                report = verify_replay_descriptor(descriptor(**{field: value}))
                self.assertTrue(report.accepted)
                self.assertFalse(report.replay_match)
                self.assertEqual(report.failure_classification, classification)
                self.assertEqual(report.failures, (failure,))

    def test_automatic_reexecution_allowed_must_be_false(self) -> None:
        report = verify_replay_descriptor(descriptor(automatic_reexecution_allowed=True))
        self.assertFalse(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "INVALID_DESCRIPTOR")
        self.assertIn("automatic_reexecution_allowed_must_be_false", report.failures)

    def test_missing_required_runner_evidence_fails_closed(self) -> None:
        payload = descriptor()
        del payload["actual_resolved_argv_hash"]
        report = verify_replay_descriptor(payload)
        self.assertFalse(report.accepted)
        self.assertEqual(report.failure_classification, "INVALID_DESCRIPTOR")
        self.assertIn("actual_resolved_argv_hash_required", report.failures)

    def test_token_reference_is_checked_as_metadata_only(self) -> None:
        report = verify_replay_descriptor(descriptor(actual_token_id="token-other"))
        self.assertTrue(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "TOKEN_METADATA_MISMATCH")
        self.assertEqual(report.failures, ("token_id_mismatch",))

    def test_queue_job_reference_is_checked_as_metadata_only(self) -> None:
        queue = LocalJobQueue(queue_id="queue-001")
        queue.enqueue(
            job_id="job-001",
            task_id="task-001",
            command_id="make_ci",
            scope=CAPABILITY_TOKEN_SCOPE,
            created_at=OBSERVED_AT,
        )
        before_summary = queue.summary()
        before_events = tuple(queue.events)

        report = verify_replay_descriptor(descriptor(actual_queue_job_id="job-other"))

        self.assertTrue(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "QUEUE_METADATA_MISMATCH")
        self.assertEqual(report.failures, ("queue_job_id_mismatch",))
        self.assertEqual(queue.summary(), before_summary)
        self.assertEqual(tuple(queue.events), before_events)

    def test_replay_does_not_consume_revoke_or_issue_tokens(self) -> None:
        lifecycle = CapabilityTokenLifecycle()
        issued = lifecycle.issue(
            command_id="make_ci",
            scope=CAPABILITY_TOKEN_SCOPE,
            run_id="run-001",
            approval_artifact_id="approval-001",
            approval_artifact_digest=TOKEN_APPROVAL_DIGEST,
            repo_revision=REVISION,
            runner_policy_id=REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
            executable_resolution_policy_id=(
                REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
            ),
            expires_at="2026-05-25T01:00:00+00:00",
            issue_nonce="issue-001",
            issued_at=OBSERVED_AT,
            observed_at=OBSERVED_AT,
        )
        self.assertTrue(issued.accepted)

        report = verify_replay_descriptor(
            descriptor(
                expected_token_id=issued.token.token_id,
                actual_token_id=issued.token.token_id,
                expected_token_state="issued",
                actual_token_state="issued",
            )
        )

        self.assertTrue(report.replay_match)
        consumed = lifecycle.consume(
            token_id=issued.token.token_id,
            command_id="make_ci",
            scope=CAPABILITY_TOKEN_SCOPE,
            run_id="run-001",
            approval_artifact_id="approval-001",
            approval_artifact_digest=TOKEN_APPROVAL_DIGEST,
            repo_revision=REVISION,
            runner_policy_id=REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
            executable_resolution_policy_id=(
                REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
            ),
            consume_nonce="consume-001",
            now="2026-05-25T00:10:00+00:00",
            observed_at="2026-05-25T00:10:00+00:00",
        )
        self.assertTrue(consumed.accepted)

    def test_replay_does_not_execute_commands_or_import_execution_surfaces(self) -> None:
        report = verify_replay_descriptor(descriptor())
        self.assertTrue(report.replay_match)

        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        for module_name in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "playwright",
            "sched",
            "threading",
        ):
            self.assertNotIn(module_name, imported_modules)

    def test_forbidden_runtime_authority_fields_fail_closed(self) -> None:
        for forbidden_field in (
            "command_line",
            "argv",
            "shell",
            "network",
            "browser",
            "provider_api",
            "credentials",
            "production_autonomy",
            "consume_token",
            "enqueue_job",
        ):
            with self.subTest(forbidden_field=forbidden_field):
                report = verify_replay_descriptor(
                    descriptor(**{forbidden_field: "forbidden"})
                )
                self.assertFalse(report.accepted)
                self.assertIn(f"{forbidden_field}_forbidden", report.failures)

    def test_report_hash_excludes_observed_at(self) -> None:
        first = verify_replay_descriptor(
            descriptor(),
            observed_at="2026-05-25T00:00:00+00:00",
        )
        second = verify_replay_descriptor(
            descriptor(),
            observed_at="2026-05-25T00:05:00+00:00",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.receipt_comparison_hash, second.receipt_comparison_hash)

    def test_policy_doc_and_source_exclude_forbidden_runtime_surfaces(self) -> None:
        policy_text = POLICY_PATH.read_text(encoding="utf-8")
        doc_text = " ".join(DOC_PATH.read_text(encoding="utf-8").lower().split())
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for fragment in (
            '"automatic_reexecution_authorized": false',
            '"command_execution_authorized": false',
            '"runner_job_execution_authorized": false',
            '"token_consumption_authorized": false',
            '"queue_mutation_authorized": false',
            '"arbitrary_shell_authorized": false',
            '"shell_true_authorized": false',
            '"network_authorized": false',
            '"browser_authorized": false',
            '"provider_api_authorized": false',
            '"credential_storage_authorized": false',
            '"production_autonomy_authorized": false',
        ):
            self.assertIn(fragment, policy_text)
        for phrase in (
            "does not rerun the command",
            "verifies real local runner boundary evidence",
            "treats capability token lifecycle state as evidence",
            "treats local job queue state as evidence",
            "does not consume, revoke, or issue tokens",
            "does not enqueue, lease, complete, fail, or cancel jobs",
            "no command execution",
            "no provider api calls",
            "credential storage",
            "production autonomy",
        ):
            self.assertIn(phrase, doc_text)
        for marker in (
            "subprocess",
            "shell=True",
            "os.system",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "playwright",
            "time.sleep",
            "api_key",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
