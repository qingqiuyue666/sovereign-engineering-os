"""Tracer-bullet tests for command envelope admission router v1."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import json
import unittest

from kernel.runtime.command_envelope_admission_router import (
    COMMAND_REGISTRY,
    CommandExecutionReceipt,
    argv_hash,
    compute_receipt_hash,
    route_envelope,
)

POLICY_PATH = Path("governance/runtime/command_envelope_admission_router_v1.json")
SOURCE_PATH = Path("kernel/runtime/command_envelope_admission_router.py")


def _envelope(
    *,
    command_id: str = "focused_replay_engine_test",
    status: str = "PASS",
    policy_id: str = "command_envelope_admission_router_v1",
    token_id: str | None = "token-001",
    approval_id: str | None = "approval-001",
    extra: str = "",
) -> str:
    token = "" if token_id is None else f"<TOKEN_ID>{token_id}</TOKEN_ID>"
    approval = (
        "" if approval_id is None else f"<APPROVAL_ID>{approval_id}</APPROVAL_ID>"
    )
    return (
        "<COMMAND_ENVELOPE>"
        f"<STATUS>{status}</STATUS>"
        f"<COMMAND_ID>{command_id}</COMMAND_ID>"
        f"<POLICY_ID>{policy_id}</POLICY_ID>"
        f"{token}"
        f"{approval}"
        "<RUN_ID>run-001</RUN_ID>"
        f"{extra}"
        "</COMMAND_ENVELOPE>"
    )


class CommandEnvelopeAdmissionRouterTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "command_envelope_admission_router_v1")
        self.assertTrue(policy["execution_disabled_by_default"])
        self.assertFalse(policy["payload_argv_allowed"])
        self.assertFalse(policy["payload_command_line_allowed"])
        self.assertFalse(policy["shell_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])

    def test_valid_pass_execute_false_does_not_call_subprocess(self):
        with mock.patch(
            "kernel.runtime.command_envelope_admission_router.subprocess.run"
        ) as run:
            report, receipt = route_envelope(_envelope())
        self.assertTrue(report.admitted)
        self.assertTrue(report.would_execute)
        self.assertFalse(report.executed)
        self.assertIsNone(receipt)
        run.assert_not_called()

    def test_valid_pass_execute_true_calls_subprocess_with_registry_argv_only(self):
        completed = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        with mock.patch(
            "kernel.runtime.command_envelope_admission_router.subprocess.run",
            return_value=completed,
        ) as run:
            report, receipt = route_envelope(_envelope(), execute=True)

        self.assertTrue(report.admitted)
        self.assertTrue(report.executed)
        self.assertIsInstance(receipt, CommandExecutionReceipt)
        entry = COMMAND_REGISTRY["focused_replay_engine_test"]
        self.assertEqual(run.call_args.args[0], entry.argv)
        kwargs = run.call_args.kwargs
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["timeout"], entry.timeout_seconds)
        self.assertNotIn("cwd", kwargs)
        self.assertNotIn("env", kwargs)
        self.assertEqual(receipt.registry_argv_hash, entry.argv_hash)

    def test_raw_command_rejected(self):
        report, receipt = route_envelope(_envelope(extra="<COMMAND>ls</COMMAND>"))
        self.assertFalse(report.admitted)
        self.assertIn("COMMAND_forbidden", report.failures)
        self.assertIsNone(receipt)

    def test_command_line_rejected(self):
        report, _ = route_envelope(
            _envelope(extra="<COMMAND_LINE>python -m unittest</COMMAND_LINE>")
        )
        self.assertFalse(report.admitted)
        self.assertIn("COMMAND_LINE_forbidden", report.failures)

    def test_argv_rejected(self):
        report, _ = route_envelope(_envelope(extra="<ARGV>python3</ARGV>"))
        self.assertFalse(report.admitted)
        self.assertIn("ARGV_forbidden", report.failures)

    def test_shell_rejected(self):
        report, _ = route_envelope(_envelope(extra="<SHELL>true</SHELL>"))
        self.assertFalse(report.admitted)
        self.assertIn("SHELL_forbidden", report.failures)

    def test_unknown_command_id_rejected(self):
        report, _ = route_envelope(_envelope(command_id="not_registered"))
        self.assertFalse(report.admitted)
        self.assertIn("unknown_command_id", report.failures)

    def test_blocked_never_executes(self):
        with mock.patch(
            "kernel.runtime.command_envelope_admission_router.subprocess.run"
        ) as run:
            report, receipt = route_envelope(
                _envelope(status="BLOCKED"), execute=True
            )
        self.assertFalse(report.admitted)
        self.assertFalse(report.executed)
        self.assertEqual(report.failure_classification, "QUARANTINED")
        self.assertIsNone(receipt)
        run.assert_not_called()

    def test_fatal_never_executes(self):
        with mock.patch(
            "kernel.runtime.command_envelope_admission_router.subprocess.run"
        ) as run:
            report, receipt = route_envelope(_envelope(status="FATAL"), execute=True)
        self.assertFalse(report.admitted)
        self.assertFalse(report.executed)
        self.assertEqual(report.failure_classification, "QUARANTINED")
        self.assertIsNone(receipt)
        run.assert_not_called()

    def test_malformed_xml_fails_closed(self):
        report, receipt = route_envelope("<COMMAND_ENVELOPE><STATUS>PASS")
        self.assertFalse(report.admitted)
        self.assertEqual(report.failure_classification, "FAIL_CLOSED")
        self.assertIn("malformed_xml", report.failures)
        self.assertIsNone(receipt)

    def test_missing_token_rejected_when_required(self):
        report, _ = route_envelope(_envelope(token_id=None))
        self.assertFalse(report.admitted)
        self.assertIn("token_id_required", report.failures)

    def test_missing_approval_rejected_when_required(self):
        report, _ = route_envelope(_envelope(approval_id=None))
        self.assertFalse(report.admitted)
        self.assertIn("approval_id_required", report.failures)

    def test_policy_mismatch_rejected(self):
        report, _ = route_envelope(_envelope(policy_id="wrong_policy"))
        self.assertFalse(report.admitted)
        self.assertIn("policy_id_mismatch", report.failures)

    def test_registry_argv_hash_deterministic(self):
        entry = COMMAND_REGISTRY["diff_check"]
        self.assertEqual(entry.argv_hash, argv_hash(entry.argv))
        self.assertEqual(entry.argv_hash, argv_hash(("git", "diff", "--check")))

    def test_receipt_hash_deterministic_excluding_timestamps(self):
        fields = {
            "run_id": "run-001",
            "command_id": "diff_check",
            "returncode": 0,
            "stdout_sha256": "sha256:" + "a" * 64,
            "stderr_sha256": "sha256:" + "b" * 64,
            "registry_argv_hash": COMMAND_REGISTRY["diff_check"].argv_hash,
            "policy_id": "command_envelope_admission_router_v1",
            "token_id": None,
            "approval_id": None,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:01+00:00",
        }
        changed_times = dict(
            fields,
            started_at="2030-01-01T00:00:00+00:00",
            completed_at="2030-01-01T00:00:01+00:00",
        )
        self.assertEqual(compute_receipt_hash(fields), compute_receipt_hash(changed_times))

    def test_source_does_not_contain_shell_true(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)

    def test_source_does_not_execute_payload_defined_runtime_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("cwd=", source)
        self.assertNotIn("env=", source)
        self.assertNotIn("executable=", source)
        self.assertIn("registry_entry.argv", source)

    def test_no_network_browser_provider_credential_import_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in ("socket", "requests", "urllib", "webbrowser"):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
