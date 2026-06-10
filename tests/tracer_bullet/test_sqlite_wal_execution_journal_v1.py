"""Tracer-bullet tests for SQLite WAL execution journal v1."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import json
import sqlite3
import tempfile
import unittest

from kernel.runtime.command_envelope_admission_router import route_envelope
from kernel.runtime.sqlite_wal_execution_journal import (
    SQLiteWalExecutionJournal,
    compute_event_content_hash,
)

POLICY_PATH = Path("governance/runtime/sqlite_wal_execution_journal_v1.json")
SOURCE_PATH = Path("kernel/runtime/sqlite_wal_execution_journal.py")


def _pass_report():
    xml = (
        "<COMMAND_ENVELOPE>"
        "<STATUS>PASS</STATUS>"
        "<COMMAND_ID>focused_replay_engine_test</COMMAND_ID>"
        "<POLICY_ID>command_envelope_admission_router_v1</POLICY_ID>"
        "<TOKEN_ID>token-001</TOKEN_ID>"
        "<APPROVAL_ID>approval-001</APPROVAL_ID>"
        "<RUN_ID>run-001</RUN_ID>"
        "</COMMAND_ENVELOPE>"
    )
    report, _ = route_envelope(xml)
    return report


def _blocked_report():
    xml = (
        "<COMMAND_ENVELOPE>"
        "<STATUS>BLOCKED</STATUS>"
        "<COMMAND_ID>focused_replay_engine_test</COMMAND_ID>"
        "<POLICY_ID>command_envelope_admission_router_v1</POLICY_ID>"
        "<TOKEN_ID>token-001</TOKEN_ID>"
        "<APPROVAL_ID>approval-001</APPROVAL_ID>"
        "<RUN_ID>run-001</RUN_ID>"
        "</COMMAND_ENVELOPE>"
    )
    report, _ = route_envelope(xml)
    return report


def _receipt():
    completed = SimpleNamespace(returncode=0, stdout="ok", stderr="")
    xml = (
        "<COMMAND_ENVELOPE>"
        "<STATUS>PASS</STATUS>"
        "<COMMAND_ID>focused_replay_engine_test</COMMAND_ID>"
        "<POLICY_ID>command_envelope_admission_router_v1</POLICY_ID>"
        "<TOKEN_ID>token-001</TOKEN_ID>"
        "<APPROVAL_ID>approval-001</APPROVAL_ID>"
        "<RUN_ID>run-001</RUN_ID>"
        "</COMMAND_ENVELOPE>"
    )
    with mock.patch(
        "kernel.runtime.command_envelope_admission_router.subprocess.run",
        return_value=completed,
    ):
        _, receipt = route_envelope(xml, execute=True)
    return receipt


class SQLiteWalExecutionJournalTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundaries(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "sqlite_wal_execution_journal_v1")
        self.assertTrue(policy["wal_mode_required"])
        self.assertTrue(policy["append_only"])
        self.assertFalse(policy["executes_commands"])
        self.assertFalse(policy["writes_to_real_artifacts_by_default"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])

    def test_wal_mode_enabled(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "journal.sqlite3"
            journal = SQLiteWalExecutionJournal(db_path)
            connection = sqlite3.connect(db_path)
            try:
                mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            finally:
                connection.close()
            journal.close()
        self.assertEqual(str(mode).lower(), "wal")

    def test_append_admission_event(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            receipt = journal.append_admission(_pass_report())
            events = journal.list_events()
            journal.close()
        self.assertEqual(receipt.event_type, "ADMISSION")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "ADMISSION")

    def test_append_quarantine_event(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            receipt = journal.append_quarantine(_blocked_report())
            events = journal.list_events()
            journal.close()
        self.assertEqual(receipt.event_type, "QUARANTINE")
        self.assertEqual(events[0]["event_type"], "QUARANTINE")

    def test_append_receipt_event(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            receipt = journal.append_receipt(_receipt())
            events = journal.list_events()
            journal.close()
        self.assertEqual(receipt.event_type, "EXECUTION_RECEIPT")
        self.assertEqual(events[0]["event_type"], "EXECUTION_RECEIPT")

    def test_deterministic_content_hash_excludes_created_at(self):
        event = {
            "event_seq": 1,
            "event_id": "evt_abc",
            "run_id": "run-001",
            "event_type": "ADMISSION",
            "command_id": "diff_check",
            "policy_id": "command_envelope_admission_router_v1",
            "token_id": None,
            "approval_id": None,
            "previous_hash": None,
            "payload_hash": "sha256:" + "a" * 64,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        later = dict(event, created_at="2030-01-01T00:00:00+00:00")
        self.assertEqual(
            compute_event_content_hash(event),
            compute_event_content_hash(later),
        )

    def test_previous_hash_chain_valid(self):
        with tempfile.TemporaryDirectory() as tempdir:
            journal = SQLiteWalExecutionJournal(Path(tempdir) / "journal.sqlite3")
            first = journal.append_admission(_pass_report())
            second = journal.append_quarantine(_blocked_report())
            third = journal.append_receipt(_receipt())
            verification = journal.verify_chain()
            journal.close()
        self.assertEqual(second.previous_hash, first.content_hash)
        self.assertEqual(third.previous_hash, second.content_hash)
        self.assertTrue(verification.valid)

    def test_verify_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "journal.sqlite3"
            journal = SQLiteWalExecutionJournal(db_path)
            journal.append_admission(_pass_report())
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE admission_events SET event_type = 'TAMPERED'"
                )
                connection.commit()
            finally:
                connection.close()
            verification = journal.verify_chain()
            journal.close()
        self.assertFalse(verification.valid)
        self.assertTrue(
            any(failure.startswith("content_hash_mismatch") for failure in verification.failures)
        )

    def test_no_update_delete_public_method_exists(self):
        journal_methods = {
            name
            for name in dir(SQLiteWalExecutionJournal)
            if not name.startswith("_")
        }
        forbidden_prefixes = ("update", "delete", "remove", "truncate", "mutate")
        for method in journal_methods:
            self.assertFalse(method.startswith(forbidden_prefixes), method)

    def test_tempdir_isolation(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "nested" / "journal.sqlite3"
            with self.assertRaises(ValueError):
                SQLiteWalExecutionJournal(db_path)
            self.assertFalse(Path("artifacts").joinpath("journal.sqlite3").exists())

    def test_no_network_browser_provider_credential_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in ("socket", "requests", "urllib", "webbrowser"):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("subprocess", source)


if __name__ == "__main__":
    unittest.main()
