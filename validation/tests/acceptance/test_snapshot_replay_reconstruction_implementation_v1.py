"""Acceptance tests for Snapshot / Replay Reconstruction Implementation V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import (
    ZERO_HASH,
    FileBackedSnapshotReplayReconstructor,
)


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class SnapshotReplayReconstructionImplementationAcceptanceV1Tests(unittest.TestCase):
    def test_reconstructs_persisted_wal_artifact_and_queue_state_then_rejects_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            wal = FileBackedRealWalStorage(root / "runtime-wal.jsonl")
            wal.append(
                record_type="MINIMAL_CONTROLLED_EXECUTION",
                task_id="task-acceptance-517",
                run_id="run-acceptance-517",
                payload_hash=_hash("acceptance-admission"),
                digest_bindings={"request_hash": _hash("acceptance-request")},
                created_at="2026-05-28T00:00:00+00:00",
            )
            wal.append(
                record_type="SNAPSHOT_EVENT",
                task_id="task-acceptance-517",
                run_id="run-acceptance-517",
                payload_hash=_hash("acceptance-snapshot"),
                digest_bindings={"snapshot_preflight_hash": _hash("acceptance-preflight")},
                created_at="2026-05-28T00:00:01+00:00",
            )
            artifact_store = FileBackedArtifactStore(root / "artifact-store")
            artifact_store.write_json_artifact(
                artifact_type="operator_report",
                task_id="task-acceptance-517",
                run_id="run-acceptance-517",
                payload={"result": "acceptance"},
                provenance_hash=_hash("acceptance-provenance"),
                metadata={"source": "acceptance"},
                created_at="2026-05-28T00:00:02+00:00",
            )
            queue = DurableJobQueue(path=root / "queue.jsonl", queue_id="queue-acceptance-517")
            queue.submit_job(
                job_id="job-acceptance-517",
                task_id="task-acceptance-517",
                run_id="run-acceptance-517",
                payload={"workload": "acceptance"},
                idempotency_key="idem-acceptance-517",
                submitted_at="2026-05-28T00:00:03+00:00",
            )
            queue.queue_job("job-acceptance-517", queued_at="2026-05-28T00:00:04+00:00")
            lease = queue.lease_next(
                worker_id="worker-acceptance-517",
                leased_at="2026-05-28T00:00:05+00:00",
            )
            queue.succeed_job(
                job_id="job-acceptance-517",
                lease_id=lease.lease_id,
                completion_payload={"completion_ref": "acceptance-receipt"},
                succeeded_at="2026-05-28T00:00:06+00:00",
            )
            reconstructor = FileBackedSnapshotReplayReconstructor(
                runtime_root=root,
                wal_source_relpath="runtime-wal.jsonl",
                artifact_store_relpath="artifact-store",
                queue_source_relpath="queue.jsonl",
                queue_id="queue-acceptance-517",
            )
            manifest = reconstructor.build_input_manifest(
                task_id="task-acceptance-517",
                run_id="run-acceptance-517",
                created_at="2026-05-28T01:00:00+00:00",
            )
            receipt = reconstructor.replay_and_persist(
                manifest,
                snapshot_created_at="2026-05-28T01:00:01+00:00",
                observed_at="2026-05-28T01:00:02+00:00",
            )
            snapshot_path = root / receipt.snapshot_manifest_relpath
            snapshot_exists = snapshot_path.is_file()
            (root / "runtime-wal.jsonl").write_text("", encoding="utf-8")
            corrupted = reconstructor.replay_and_persist(manifest)

        self.assertTrue(receipt.accepted)
        self.assertTrue(snapshot_exists)
        self.assertEqual(receipt.observed_snapshot_root_hash, manifest.expected_snapshot_root_hash)
        self.assertEqual(len(manifest.expected_wal_record_hashes), 2)
        self.assertEqual(len(manifest.expected_artifact_record_hashes), 1)
        self.assertEqual(len(manifest.expected_queue_record_hashes), 4)
        self.assertFalse(corrupted.accepted)
        self.assertEqual(corrupted.snapshot_manifest_hash, ZERO_HASH)
        self.assertIn("wal_record_missing", corrupted.failures)


if __name__ == "__main__":
    unittest.main()
