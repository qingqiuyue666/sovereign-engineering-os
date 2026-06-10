"""Acceptance coverage for the real WAL storage backend V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.stores.real_wal_storage import (
    FileBackedRealWalStorage,
    RealWalStorageCorruptionError,
)


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class RealWalStorageBackendAcceptanceV1Tests(unittest.TestCase):
    def test_file_backed_wal_reopens_replays_and_detects_corruption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            wal_path = Path(tempdir) / "runtime-wal.jsonl"
            store = FileBackedRealWalStorage(wal_path)
            store.append(
                record_type="MINIMAL_CONTROLLED_EXECUTION",
                task_id="task-acceptance",
                run_id="run-acceptance",
                payload_hash=_hash("payload-1"),
                digest_bindings={"request_hash": _hash("request-1")},
                created_at="2026-05-27T00:00:00Z",
            )
            store.append(
                record_type="ARTIFACT_EVENT",
                task_id="task-acceptance",
                run_id="run-acceptance",
                payload_hash=_hash("payload-2"),
                digest_bindings={"artifact_manifest_hash": _hash("artifact-2")},
                created_at="2026-05-27T00:00:01Z",
            )

            reopened = FileBackedRealWalStorage(wal_path)
            replay = reopened.replay()
            records = reopened.read_records()
            wal_text = wal_path.read_text(encoding="utf-8")
            wal_path.write_text(
                wal_text.replace("ARTIFACT_EVENT", "QUEUE_EVENT", 1),
                encoding="utf-8",
            )
            corrupted = reopened.replay()

            with self.assertRaisesRegex(
                RealWalStorageCorruptionError, "record_hash_mismatch"
            ):
                reopened.read_records()

        self.assertTrue(replay.accepted)
        self.assertEqual(replay.record_count, 2)
        self.assertEqual(records[1].previous_hash, records[0].record_hash)
        self.assertFalse(corrupted.accepted)
        self.assertIn("record_hash_mismatch", corrupted.rejection_reasons[0])


if __name__ == "__main__":
    unittest.main()
