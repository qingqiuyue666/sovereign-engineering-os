"""Acceptance coverage for Artifact Store Persistence Implementation V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class ArtifactStorePersistenceImplementationAcceptanceV1Tests(unittest.TestCase):
    def test_file_backed_store_reopens_replays_verifies_and_detects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            first = store.write_json_artifact(
                artifact_type="audit_json",
                task_id="task-acceptance",
                run_id="run-acceptance",
                payload={"result": "first"},
                provenance_hash=_hash("provenance-1"),
                metadata={"source": "acceptance", "order": 1},
                created_at="2026-05-28T00:00:00+00:00",
            )
            second = store.write_json_artifact(
                artifact_type="operator_report",
                task_id="task-acceptance",
                run_id="run-acceptance",
                payload={"result": "second"},
                provenance_hash=_hash("provenance-2"),
                metadata={"source": "acceptance", "order": 2},
                created_at="2026-05-28T00:00:01+00:00",
            )

            reopened = FileBackedArtifactStore(root)
            records = reopened.read_records()
            replay = reopened.replay()
            manifests = reopened.list_manifests(task_id="task-acceptance")
            first_verification = reopened.verify_artifact(first.manifest.artifact_id)
            wal_records = FileBackedRealWalStorage(root / "artifact-store.real-wal.jsonl").read_records()
            Path(second.artifact_path).write_text('{"result":"tampered"}', encoding="utf-8")
            tampered = reopened.replay()

        self.assertTrue(replay.accepted)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(wal_records), 2)
        self.assertEqual(
            [record.manifest.wal_record_hash for record in records],
            [record.record_hash for record in wal_records],
        )
        self.assertEqual(
            [manifest.artifact_id for manifest in manifests],
            sorted([first.manifest.artifact_id, second.manifest.artifact_id]),
        )
        self.assertTrue(first_verification.accepted)
        self.assertFalse(tampered.accepted)
        self.assertIn("content_sha256_mismatch", tampered.rejection_reasons)


if __name__ == "__main__":
    unittest.main()
