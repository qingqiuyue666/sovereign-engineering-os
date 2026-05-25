"""Tracer-bullet tests for router WAL binding v1."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import json
import tempfile
import unittest

from kernel.runtime.command_envelope_admission_router import COMMAND_REGISTRY
from kernel.runtime.router_wal_binding import (
    RouterWalBinding,
    bind_router_envelope_to_wal,
)
from kernel.runtime.sqlite_wal_execution_journal import SQLiteWalExecutionJournal

POLICY_PATH = Path("governance/runtime/router_wal_binding_v1.json")
SOURCE_PATH = Path("kernel/runtime/router_wal_binding.py")


def _envelope(
    *,
    command_id: str = "focused_replay_engine_test",
    status: str = "PASS",
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
        "<POLICY_ID>command_envelope_admission_router_v1</POLICY_ID>"
        f"{token}"
        f"{approval}"
        "<RUN_ID>run-binding-001</RUN_ID>"
        f"{extra}"
        "</COMMAND_ENVELOPE>"
    )


class RouterWalBindingTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "router_wal_binding_v1")
        self.assertTrue(policy["uses_command_envelope_admission_router"])
        self.assertTrue(policy["uses_sqlite_wal_execution_journal"])
        self.assertFalse(policy["payload_material_storage_allowed"])
        self.assertFalse(policy["shell_allowed"])
        self.assertFalse(policy["payload_argv_allowed"])
        self.assertFalse(policy["payload_command_line_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])

    def test_valid_pass_execute_false_writes_admission_event(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            result = bind_router_envelope_to_wal(_envelope(), journal)
            events = journal.list_events()
            journal.close()

        self.assertTrue(result.report.admitted)
        self.assertIsNotNone(result.admission_event)
        self.assertIsNone(result.quarantine_event)
        self.assertIsNone(result.receipt)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "ADMISSION")
        self.assertEqual(events[0]["payload_hash"], result.report.content_hash)

    def test_execute_false_never_calls_subprocess(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            with mock.patch(
                "kernel.runtime.command_envelope_admission_router.subprocess.run"
            ) as run:
                bind_router_envelope_to_wal(_envelope(), journal, execute=False)
            journal.close()
        run.assert_not_called()

    def test_blocked_writes_quarantine_event(self):
        self._assert_quarantine(_envelope(status="BLOCKED"), "QUARANTINE")

    def test_fatal_writes_quarantine_event(self):
        self._assert_quarantine(_envelope(status="FATAL"), "QUARANTINE")

    def test_forbidden_command_writes_quarantine_event(self):
        self._assert_quarantine(_envelope(extra="<COMMAND>ls</COMMAND>"), "QUARANTINE")

    def test_malformed_xml_writes_quarantine_event(self):
        self._assert_quarantine("<COMMAND_ENVELOPE><STATUS>PASS", "QUARANTINE")

    def test_execute_true_valid_registry_command_writes_receipt_event(self):
        completed = SimpleNamespace(returncode=0, stdout=b"ok", stderr=b"")
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            with mock.patch(
                "kernel.runtime.command_envelope_admission_router.subprocess.run",
                return_value=completed,
            ) as run:
                result = bind_router_envelope_to_wal(
                    _envelope(command_id="diff_check", token_id=None, approval_id=None),
                    journal,
                    execute=True,
                )
            events = journal.list_events()
            journal.close()

        entry = COMMAND_REGISTRY["diff_check"]
        self.assertEqual(run.call_args.args[0], entry.argv)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertNotIn("cwd", run.call_args.kwargs)
        self.assertNotIn("env", run.call_args.kwargs)
        self.assertTrue(result.report.executed)
        self.assertIsNotNone(result.receipt)
        self.assertIsNotNone(result.receipt_event)
        self.assertEqual([event["event_type"] for event in events], ["ADMISSION", "EXECUTION_RECEIPT"])
        self.assertEqual(events[1]["payload_hash"], result.receipt.receipt_hash)

    def test_journal_chain_verifies_after_binding_writes(self):
        completed = SimpleNamespace(returncode=0, stdout=b"ok", stderr=b"")
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            bind_router_envelope_to_wal(_envelope(), journal)
            bind_router_envelope_to_wal(_envelope(status="BLOCKED"), journal)
            with mock.patch(
                "kernel.runtime.command_envelope_admission_router.subprocess.run",
                return_value=completed,
            ):
                RouterWalBinding(journal).bind(
                    _envelope(command_id="diff_check", token_id=None, approval_id=None),
                    execute=True,
                )
            verification = journal.verify_chain()
            journal.close()
        self.assertTrue(verification.valid, verification.failures)

    def test_no_raw_xml_payload_stored_in_journal(self):
        xml = _envelope(extra="<REASON>safe reason only</REASON>")
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "journal.sqlite3"
            journal = SQLiteWalExecutionJournal(db_path)
            bind_router_envelope_to_wal(xml, journal)
            events = journal.list_events()
            journal.close()
            raw_db = db_path.read_bytes()
        self.assertNotIn(xml.encode("utf-8"), raw_db)
        self.assertEqual(events[0]["payload_hash"].startswith("sha256:"), True)

    def test_no_shell_true_in_binding_source(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)

    def test_binding_does_not_accept_payload_provided_runtime_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("cwd=", source)
        self.assertNotIn("env=", source)
        self.assertNotIn("executable=", source)
        self.assertNotIn("timeout=", source)
        self.assertNotIn("subprocess", source)

    def _assert_quarantine(self, xml: str, event_type: str) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            with mock.patch(
                "kernel.runtime.command_envelope_admission_router.subprocess.run"
            ) as run:
                result = bind_router_envelope_to_wal(xml, journal, execute=True)
            events = journal.list_events()
            journal.close()

        run.assert_not_called()
        self.assertFalse(result.report.admitted)
        self.assertIsNone(result.admission_event)
        self.assertIsNotNone(result.quarantine_event)
        self.assertIsNone(result.receipt)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], event_type)
        self.assertEqual(events[0]["payload_hash"], result.report.content_hash)


if __name__ == "__main__":
    unittest.main()
