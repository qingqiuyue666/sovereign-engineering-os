"""Tests for Replay Engine V1."""

from __future__ import annotations

import unittest
from pathlib import Path

from kernel.runtime.replay_engine import verify_replay_descriptor


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "replay_engine.py"
POLICY_PATH = ROOT / "governance" / "replay" / "replay_engine_v1.json"
DOC_PATH = ROOT / "docs" / "decisions" / "replay_engine_v1.md"

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64


def descriptor(**overrides):
    payload = {
        "replay_id": "replay-001",
        "source_receipt_id": "receipt-source",
        "candidate_receipt_id": "receipt-candidate",
        "source_receipt_digest": DIGEST_A,
        "candidate_receipt_digest": DIGEST_A,
        "expected_environment_digest": DIGEST_B,
        "actual_environment_digest": DIGEST_B,
        "expected_command_id": "make_ci",
        "actual_command_id": "make_ci",
        "expected_argv_hash": DIGEST_C,
        "actual_argv_hash": DIGEST_C,
        "expected_output_digest": DIGEST_D,
        "actual_output_digest": DIGEST_D,
        "expected_exit_code": 0,
        "actual_exit_code": 0,
        "automatic_reexecution_requested": False,
    }
    payload.update(overrides)
    return payload


class ReplayEngineV1Tests(unittest.TestCase):
    def test_matching_descriptor_reports_replay_match(self) -> None:
        report = verify_replay_descriptor(
            descriptor(),
            observed_at="2026-05-25T00:00:00+00:00",
        )
        self.assertTrue(report.accepted)
        self.assertTrue(report.replay_match)
        self.assertEqual(report.failure_classification, "REPLAY_MATCH")
        self.assertEqual(report.failures, ())

    def test_receipt_environment_command_argv_output_and_exit_mismatches_report(self) -> None:
        report = verify_replay_descriptor(
            descriptor(
                candidate_receipt_digest=DIGEST_B,
                actual_environment_digest=DIGEST_C,
                actual_command_id="diff_check",
                actual_argv_hash=DIGEST_D,
                actual_output_digest=DIGEST_A,
                actual_exit_code=1,
            )
        )
        self.assertTrue(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "MULTIPLE_MISMATCHES")
        for failure in (
            "receipt_digest_mismatch",
            "environment_digest_mismatch",
            "command_id_mismatch",
            "argv_hash_mismatch",
            "output_digest_mismatch",
            "exit_code_mismatch",
        ):
            self.assertIn(failure, report.failures)

    def test_single_mismatch_classification_is_specific(self) -> None:
        report = verify_replay_descriptor(descriptor(actual_output_digest=DIGEST_A))
        self.assertTrue(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "OUTPUT_MISMATCH")
        self.assertEqual(report.failures, ("output_digest_mismatch",))

    def test_invalid_descriptor_and_reexecution_request_fail_closed(self) -> None:
        report = verify_replay_descriptor(
            descriptor(
                actual_output_digest="not-a-digest",
                automatic_reexecution_requested=True,
            )
        )
        self.assertFalse(report.accepted)
        self.assertFalse(report.replay_match)
        self.assertEqual(report.failure_classification, "INVALID_DESCRIPTOR")
        self.assertIn("actual_output_digest_required", report.failures)
        self.assertIn("automatic_reexecution_forbidden", report.failures)

    def test_forbidden_raw_or_command_line_fields_fail_closed(self) -> None:
        report = verify_replay_descriptor(
            descriptor(raw_stdout="hello", command_line="make ci", argv_override=["make", "ci"])
        )
        self.assertFalse(report.accepted)
        self.assertIn("raw_stdout_forbidden", report.failures)
        self.assertIn("command_line_forbidden", report.failures)
        self.assertIn("argv_override_forbidden", report.failures)

    def test_report_hash_excludes_observed_at(self) -> None:
        first = verify_replay_descriptor(descriptor(), observed_at="2026-05-25T00:00:00+00:00")
        second = verify_replay_descriptor(descriptor(), observed_at="2026-05-25T00:05:00+00:00")
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
            '"arbitrary_shell_authorized": false',
            '"shell_true_authorized": false',
            '"network_authorized": false',
            '"browser_authorized": false',
            '"provider_api_authorized": false',
        ):
            self.assertIn(fragment, policy_text)
        for phrase in (
            "does not rerun the command",
            "authorizes no automatic re-execution",
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
            "threading",
            "time.sleep",
            "api_key",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
