"""Tracer-bullet tests for the durable operator decision store."""

import json
import tempfile
import unittest
from pathlib import Path

from kernel.audit.hashchain import canonical_json
from kernel.runtime.operator_decision_ledger import (
    OperatorDecisionLedger,
    build_ledger_entry,
)
from kernel.runtime.operator_decision_store import OperatorDecisionStore

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64
VALID_DIGEST_4 = "sha256:" + "d" * 64
VALID_DIGEST_5 = "sha256:" + "e" * 64


def _pending_entry(*, entry_id="entry-001", session_id="session-001", sequence_number=1, previous_entry_hash=None):
    return build_ledger_entry(
        entry_id=entry_id,
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        operator_action="pending",
        review_session_hash=VALID_DIGEST,
        previous_entry_hash=previous_entry_hash,
        sequence_number=sequence_number,
        observed_at="2026-01-01T00:00:00Z",
    )


def _approved_entry(*, entry_id, session_id="session-001", sequence_number, previous_entry_hash):
    return build_ledger_entry(
        entry_id=entry_id,
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        operator_action="approved",
        review_session_hash=VALID_DIGEST,
        approval_receipt_hash=VALID_DIGEST_2,
        previous_entry_hash=previous_entry_hash,
        sequence_number=sequence_number,
        observed_at="2026-01-01T00:00:00Z",
    )


def _rejected_entry(*, entry_id, session_id="session-001", sequence_number, previous_entry_hash):
    return build_ledger_entry(
        entry_id=entry_id,
        session_id=session_id,
        run_id="run-001",
        task_id=f"task-{session_id}",
        operator_action="rejected",
        review_session_hash=VALID_DIGEST,
        rejection_receipt_hash=VALID_DIGEST_3,
        rollback_plan_hash=VALID_DIGEST_4,
        previous_entry_hash=previous_entry_hash,
        sequence_number=sequence_number,
        observed_at="2026-01-01T00:00:00Z",
    )


def _read_records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_records(path: Path, records):
    path.write_text("".join(canonical_json(record) + "\n" for record in records), encoding="utf-8")


class OperatorDecisionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "decisions.jsonl"
        self.store = OperatorDecisionStore(self.path, store_id="decision-store-001")

    def test_append_one_pending_entry(self):
        entry = _pending_entry()
        receipt = self.store.append_entry(entry)
        self.assertEqual(receipt.record_sequence, 1)
        self.assertEqual(receipt.entry_content_hash, entry.content_hash)
        self.assertTrue(receipt.content_hash.startswith("sha256:"))
        self.assertEqual(len(self.store.load_entries()), 1)

    def test_append_pending_then_approved(self):
        pending = _pending_entry()
        self.store.append_entry(pending)
        approved = _approved_entry(
            entry_id="entry-002",
            previous_entry_hash=pending.content_hash,
            sequence_number=2,
        )
        self.store.append_entry(approved)
        entries = self.store.load_entries()
        self.assertEqual([entry.operator_action for entry in entries], ["pending", "approved"])

    def test_append_pending_then_rejected(self):
        pending = _pending_entry()
        self.store.append_entry(pending)
        rejected = _rejected_entry(
            entry_id="entry-002",
            previous_entry_hash=pending.content_hash,
            sequence_number=2,
        )
        self.store.append_entry(rejected)
        entries = self.store.load_entries()
        self.assertEqual([entry.operator_action for entry in entries], ["pending", "rejected"])

    def test_reload_entries_from_disk(self):
        entry = _pending_entry()
        self.store.append_entry(entry)
        reloaded = OperatorDecisionStore(self.path, store_id="decision-store-001").load_entries()
        self.assertEqual(reloaded, (entry,))

    def test_rebuild_ledger_from_disk(self):
        entry = _pending_entry()
        self.store.append_entry(entry)
        ledger = self.store.rebuild_ledger()
        self.assertIsInstance(ledger, OperatorDecisionLedger)
        self.assertEqual(ledger.total_entries, 1)
        self.assertEqual(ledger.entry_hashes(), (entry.content_hash,))

    def test_export_snapshot_from_disk_backed_ledger(self):
        entry = _pending_entry()
        self.store.append_entry(entry)
        snapshot = self.store.export_snapshot()
        self.assertEqual(snapshot.total_entries, 1)
        self.assertEqual(snapshot.pending_count, 1)
        self.assertEqual(snapshot.entry_hashes, (entry.content_hash,))

    def test_verify_store_returns_valid_receipt(self):
        entry = _pending_entry()
        self.store.append_entry(entry)
        receipt = self.store.verify_store(observed_at="2026-01-01T00:00:00Z")
        self.assertTrue(receipt.valid)
        self.assertEqual(receipt.total_records, 1)
        self.assertEqual(receipt.reasons, ())

    def test_record_sequence_is_continuous(self):
        first = _pending_entry(session_id="session-001")
        self.store.append_entry(first)
        second = _pending_entry(
            entry_id="entry-002",
            session_id="session-002",
            sequence_number=2,
            previous_entry_hash=first.content_hash,
        )
        self.store.append_entry(second)
        records = _read_records(self.path)
        self.assertEqual([record["record_sequence"] for record in records], [1, 2])

    def test_previous_record_hash_binds_records(self):
        first = _pending_entry(session_id="session-001")
        self.store.append_entry(first)
        second = _pending_entry(
            entry_id="entry-002",
            session_id="session-002",
            sequence_number=2,
            previous_entry_hash=first.content_hash,
        )
        self.store.append_entry(second)
        records = _read_records(self.path)
        self.assertIsNone(records[0]["previous_record_hash"])
        self.assertEqual(records[1]["previous_record_hash"], records[0]["record_hash"])

    def test_decision_chain_head_after_reload_equals_original_ledger(self):
        first = _pending_entry(session_id="session-001")
        self.store.append_entry(first)
        second = _pending_entry(
            entry_id="entry-002",
            session_id="session-002",
            sequence_number=2,
            previous_entry_hash=first.content_hash,
        )
        self.store.append_entry(second)
        ledger = OperatorDecisionLedger()
        ledger.append(first)
        ledger.append(second)
        self.assertEqual(self.store.rebuild_ledger().decision_chain_head, ledger.decision_chain_head)

    def test_observed_at_does_not_enter_record_hash(self):
        entry = _pending_entry()
        self.store.append_entry(entry)
        records = _read_records(self.path)
        original_hash = records[0]["record_hash"]
        records[0]["observed_at"] = "2027-01-01T00:00:00Z"
        records[0]["entry"]["observed_at"] = "2027-01-01T00:00:00Z"
        _write_records(self.path, records)
        self.assertEqual(_read_records(self.path)[0]["record_hash"], original_hash)
        self.assertEqual(self.store.load_entries()[0].content_hash, entry.content_hash)

    def test_observed_at_does_not_enter_verification_receipt_hash(self):
        self.store.append_entry(_pending_entry())
        first = self.store.verify_store(observed_at="2026-01-01T00:00:00Z")
        second = self.store.verify_store(observed_at="2027-01-01T00:00:00Z")
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_malformed_json_line_fails_closed(self):
        self.path.write_text("{not-json}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.load_entries()
        self.assertFalse(self.store.verify_store().valid)

    def test_missing_required_field_fails_closed(self):
        self.store.append_entry(_pending_entry())
        records = _read_records(self.path)
        del records[0]["entry_content_hash"]
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_entries()

    def test_tampered_entry_content_hash_fails_closed(self):
        self.store.append_entry(_pending_entry())
        records = _read_records(self.path)
        records[0]["entry"]["content_hash"] = VALID_DIGEST_5
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_entries()

    def test_wrong_previous_record_hash_fails_closed(self):
        first = _pending_entry(session_id="session-001")
        self.store.append_entry(first)
        second = _pending_entry(
            entry_id="entry-002",
            session_id="session-002",
            sequence_number=2,
            previous_entry_hash=first.content_hash,
        )
        self.store.append_entry(second)
        records = _read_records(self.path)
        records[1]["previous_record_hash"] = VALID_DIGEST_5
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_entries()

    def test_wrong_record_sequence_fails_closed(self):
        self.store.append_entry(_pending_entry())
        records = _read_records(self.path)
        records[0]["record_sequence"] = 2
        _write_records(self.path, records)
        with self.assertRaises(ValueError):
            self.store.load_entries()

    def test_duplicate_entry_id_fails_closed(self):
        first = _pending_entry()
        self.store.append_entry(first)
        duplicate = _pending_entry(
            entry_id=first.entry_id,
            session_id="session-002",
            sequence_number=2,
            previous_entry_hash=first.content_hash,
        )
        with self.assertRaises(ValueError):
            self.store.append_entry(duplicate)

    def test_duplicate_session_approved_fails_closed(self):
        approved = _approved_entry(
            entry_id="entry-001",
            session_id="session-001",
            sequence_number=1,
            previous_entry_hash=None,
        )
        self.store.append_entry(approved)
        duplicate = _approved_entry(
            entry_id="entry-002",
            session_id="session-001",
            sequence_number=2,
            previous_entry_hash=approved.content_hash,
        )
        with self.assertRaises(ValueError):
            self.store.append_entry(duplicate)

    def test_approved_after_rejected_fails_closed(self):
        pending = _pending_entry()
        self.store.append_entry(pending)
        rejected = _rejected_entry(
            entry_id="entry-002",
            sequence_number=2,
            previous_entry_hash=pending.content_hash,
        )
        self.store.append_entry(rejected)
        approved = _approved_entry(
            entry_id="entry-003",
            sequence_number=3,
            previous_entry_hash=rejected.content_hash,
        )
        with self.assertRaises(ValueError):
            self.store.append_entry(approved)

    def test_rejected_after_approved_fails_closed(self):
        pending = _pending_entry()
        self.store.append_entry(pending)
        approved = _approved_entry(
            entry_id="entry-002",
            sequence_number=2,
            previous_entry_hash=pending.content_hash,
        )
        self.store.append_entry(approved)
        rejected = _rejected_entry(
            entry_id="entry-003",
            sequence_number=3,
            previous_entry_hash=approved.content_hash,
        )
        with self.assertRaises(ValueError):
            self.store.append_entry(rejected)

    def test_partial_final_line_fails_closed(self):
        self.store.append_entry(_pending_entry())
        self.path.write_text(self.path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.load_entries()

    def test_unknown_raw_or_sensitive_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "raw_exception", "env", "secret"):
            with self.subTest(field_name=field_name):
                self.store.append_entry(_pending_entry(entry_id=f"entry-{field_name}", session_id=f"session-{field_name}"))
                records = _read_records(self.path)
                records[-1][field_name] = "blocked"
                _write_records(self.path, records)
                with self.assertRaises(ValueError):
                    self.store.load_entries()
                self.path.unlink()
                self.store = OperatorDecisionStore(self.path, store_id="decision-store-001")


class OperatorDecisionStoreSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_contain_forbidden_runtime_surfaces(self):
        for module_path in (
            Path("kernel/runtime/operator_decision_store.py"),
            Path("kernel/runtime/operator_decision_store_replay.py"),
        ):
            source = module_path.read_text(encoding="utf-8")
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
                self.assertNotIn(marker, source, f"{module_path} contains {marker}")


if __name__ == "__main__":
    unittest.main()
