"""Tests for the file-backed real WAL storage backend V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageCorruptionError,
    RealWalStorageError,
)
from kernel.stores.real_wal_storage_contract import (
    REAL_WAL_STORAGE_CONTRACT_VERSION,
    RealWalStorageRecord,
    serialize_real_wal_storage_record_line,
)


SOURCE_PATH = Path("kernel/stores/real_wal_storage.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class RealWalStorageBackendV1Tests(unittest.TestCase):
    def test_append_reopen_and_replay_validates_durable_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "real-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)

            first = store.append(
                record_type="MINIMAL_CONTROLLED_EXECUTION",
                task_id="task-001",
                run_id="run-001",
                payload_hash=_hash("payload-1"),
                digest_bindings={"request_hash": _hash("request-1")},
                created_at="2026-05-27T00:00:00Z",
            )
            second = store.append(
                record_type="QUEUE_EVENT",
                task_id="task-001",
                run_id="run-001",
                payload_hash=_hash("payload-2"),
                digest_bindings={"queue_event_hash": _hash("queue-2")},
                created_at="2026-05-27T00:00:01Z",
            )

            reopened = FileBackedRealWalStorage(wal_path)
            records = reopened.read_records()
            replay = reopened.replay()

        self.assertEqual([record.sequence for record in records], [1, 2])
        self.assertIsNone(records[0].previous_hash)
        self.assertEqual(records[1].previous_hash, records[0].record_hash)
        self.assertEqual(first.record_hash, records[0].record_hash)
        self.assertEqual(second.previous_hash, records[0].record_hash)
        self.assertTrue(replay.accepted)
        self.assertEqual(replay.last_record_hash, records[-1].record_hash)

    def test_existing_corruption_blocks_read_and_future_append(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "real-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)
            store.append(
                record_type="MINIMAL_CONTROLLED_EXECUTION",
                task_id="task-001",
                run_id="run-001",
                payload_hash=_hash("payload-1"),
                digest_bindings={"request_hash": _hash("request-1")},
            )
            payload = json.loads(wal_path.read_text(encoding="utf-8"))
            payload["record_type"] = "QUEUE_EVENT"
            wal_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            before = wal_path.read_text(encoding="utf-8")

            with self.assertRaisesRegex(
                RealWalStorageCorruptionError, "record_hash_mismatch"
            ):
                store.read_records()
            replay = store.replay()
            with self.assertRaisesRegex(
                RealWalStorageCorruptionError, "record_hash_mismatch"
            ):
                store.append(
                    record_type="QUEUE_EVENT",
                    task_id="task-001",
                    run_id="run-001",
                    payload_hash=_hash("payload-2"),
                    digest_bindings={"queue_event_hash": _hash("queue-2")},
                )

            after = wal_path.read_text(encoding="utf-8")

        self.assertFalse(replay.accepted)
        self.assertIn("record_hash_mismatch", replay.rejection_reasons[0])
        self.assertEqual(after, before)

    def test_partial_and_malformed_lines_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            partial_path = Path(tempdir) / "partial.jsonl"
            partial_path.write_text("{\"not\":\"complete\"}", encoding="utf-8")
            malformed_path = Path(tempdir) / "malformed.jsonl"
            malformed_path.write_text("{not-json}\n", encoding="utf-8")

            partial = FileBackedRealWalStorage(partial_path)
            malformed = FileBackedRealWalStorage(malformed_path)

            with self.assertRaisesRegex(
                RealWalStorageCorruptionError, "partial_record_line"
            ):
                partial.read_records()
            with self.assertRaisesRegex(
                RealWalStorageCorruptionError, "malformed_json"
            ):
                malformed.read_records()

            self.assertFalse(partial.replay().accepted)
            self.assertFalse(malformed.replay().accepted)

    def test_append_rejects_secret_like_digest_binding_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "real-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)

            with self.assertRaisesRegex(ValueError, "digest_binding_name_secret_like"):
                store.append(
                    record_type="MINIMAL_CONTROLLED_EXECUTION",
                    task_id="task-001",
                    run_id="run-001",
                    payload_hash=_hash("payload-1"),
                    digest_bindings={"token_hash": _hash("token")},
                )

            records = store.read_records()

        self.assertEqual(records, ())

    def test_append_record_rejects_sequence_gap_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "real-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)
            record = RealWalStorageRecord(
                wal_record_id="real-wal-record-gap",
                wal_storage_contract_version=REAL_WAL_STORAGE_CONTRACT_VERSION,
                sequence=2,
                previous_hash=None,
                record_type="QUEUE_EVENT",
                task_id="task-001",
                run_id="run-001",
                payload_hash=_hash("payload-gap"),
                digest_bindings={"queue_event_hash": _hash("queue-gap")},
                created_at="2026-05-27T00:00:00Z",
            )

            with self.assertRaisesRegex(
                RealWalStorageError, "sequence_gap_detected"
            ):
                store.append_record(record)

            text = wal_path.read_text(encoding="utf-8")

        self.assertEqual(text, "")

    def test_append_creates_contract_serialized_jsonl_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "real-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)
            store.append(
                record_type="SNAPSHOT_EVENT",
                task_id="task-001",
                run_id="run-001",
                payload_hash=_hash("snapshot-payload"),
                digest_bindings={"snapshot_hash": _hash("snapshot")},
                created_at="2026-05-27T00:00:00Z",
            )

            record = store.read_records()[0]
            raw_line = wal_path.read_text(encoding="utf-8")

        self.assertEqual(raw_line, serialize_real_wal_storage_record_line(record))

    def test_public_surface_is_append_read_replay_only(self) -> None:
        public_methods = {
            name
            for name in dir(FileBackedRealWalStorage)
            if not name.startswith("_")
        }

        self.assertLessEqual(
            public_methods,
            {"append", "append_record", "read_records", "replay"},
        )
        for forbidden_prefix in ("delete", "remove", "truncate", "update"):
            self.assertFalse(
                any(name.startswith(forbidden_prefix) for name in public_methods)
            )

    def test_source_has_no_network_provider_subprocess_or_sqlite_surface(
        self,
    ) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        forbidden = {
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "sqlite3",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imported_roots.intersection(forbidden))
        self.assertNotIn("stdout", source)
        self.assertNotIn("stderr", source)


if __name__ == "__main__":
    unittest.main()
