"""Tests for Snapshot / Replay Reconstruction Implementation V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import (
    ZERO_HASH,
    FileBackedSnapshotReplayReconstructor,
    SnapshotReplayInputManifest,
    SnapshotReplayReconstructionError,
)


SOURCE_PATH = Path("kernel/stores/snapshot_replay_reconstruction.py")
TASK_ID = "task-517"
RUN_ID = "run-517"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _fixture(root: Path) -> FileBackedSnapshotReplayReconstructor:
    wal = FileBackedRealWalStorage(root / "runtime-wal.jsonl")
    wal.append(
        record_type="MINIMAL_CONTROLLED_EXECUTION",
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload_hash=_hash("admission"),
        digest_bindings={"request_hash": _hash("request")},
        created_at="2026-05-28T00:00:00+00:00",
    )
    wal.append(
        record_type="SNAPSHOT_EVENT",
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload_hash=_hash("snapshot-ready"),
        digest_bindings={"snapshot_preflight_hash": _hash("preflight")},
        created_at="2026-05-28T00:00:01+00:00",
    )

    artifact_store = FileBackedArtifactStore(root / "artifact-store")
    artifact_store.write_json_artifact(
        artifact_type="audit_json",
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload={"result": "artifact"},
        provenance_hash=_hash("artifact-provenance"),
        metadata={"source": "snapshot_replay_test"},
        created_at="2026-05-28T00:00:02+00:00",
    )

    queue = DurableJobQueue(path=root / "queue.jsonl", queue_id="queue-517")
    queue.submit_job(
        job_id="job-517",
        task_id=TASK_ID,
        run_id=RUN_ID,
        payload={"workload": "snapshot_replay"},
        idempotency_key="idem-517",
        submitted_at="2026-05-28T00:00:03+00:00",
    )
    queue.queue_job("job-517", queued_at="2026-05-28T00:00:04+00:00")
    leased = queue.lease_next(
        worker_id="worker-517",
        leased_at="2026-05-28T00:00:05+00:00",
    )
    queue.succeed_job(
        job_id="job-517",
        lease_id=leased.lease_id,
        completion_payload={"completion_ref": "receipt-517"},
        succeeded_at="2026-05-28T00:00:06+00:00",
    )

    return FileBackedSnapshotReplayReconstructor(
        runtime_root=root,
        wal_source_relpath="runtime-wal.jsonl",
        artifact_store_relpath="artifact-store",
        queue_source_relpath="queue.jsonl",
        queue_id="queue-517",
    )


class SnapshotReplayReconstructionImplementationV1Tests(unittest.TestCase):
    def test_wal_artifact_queue_state_reconstructs_and_reopens_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(
                task_id=TASK_ID,
                run_id=RUN_ID,
                created_at="2026-05-28T01:00:00+00:00",
            )
            receipt = reconstructor.replay_and_persist(
                manifest,
                snapshot_created_at="2026-05-28T01:00:01+00:00",
                observed_at="2026-05-28T01:00:02+00:00",
            )
            reopened_receipt = FileBackedSnapshotReplayReconstructor(
                runtime_root=root,
                wal_source_relpath="runtime-wal.jsonl",
                artifact_store_relpath="artifact-store",
                queue_source_relpath="queue.jsonl",
                queue_id="queue-517",
            ).replay_and_persist(
                manifest,
                snapshot_created_at="2026-05-28T01:00:01+00:00",
                observed_at="2030-01-01T00:00:00+00:00",
            )
            snapshot_path = root / receipt.snapshot_manifest_relpath
            snapshot_exists = snapshot_path.is_file()
            persisted = json.loads(snapshot_path.read_text(encoding="utf-8"))

        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.receipt_hash, reopened_receipt.receipt_hash)
        self.assertEqual(receipt.observed_snapshot_root_hash, manifest.expected_snapshot_root_hash)
        self.assertTrue(snapshot_exists)
        self.assertEqual(persisted["manifest_hash"], receipt.snapshot_manifest_hash)
        self.assertEqual(persisted["snapshot_id"], receipt.snapshot_id)

    def test_missing_wal_record_rejects_without_trusted_snapshot_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(task_id=TASK_ID, run_id=RUN_ID)
            (root / "runtime-wal.jsonl").write_text("", encoding="utf-8")

            receipt = reconstructor.replay_and_persist(manifest)

        self.assertFalse(receipt.accepted)
        self.assertEqual(receipt.snapshot_manifest_hash, ZERO_HASH)
        self.assertIn("wal_record_missing", receipt.failures)

    def test_artifact_content_tamper_rejects_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(task_id=TASK_ID, run_id=RUN_ID)
            artifact_store = FileBackedArtifactStore(root / "artifact-store")
            artifact_manifest = artifact_store.read_records()[0].manifest
            artifact_store.artifact_path(artifact_manifest).write_text(
                '{"result":"tampered"}',
                encoding="utf-8",
            )

            receipt = reconstructor.replay_and_persist(manifest)

        self.assertFalse(receipt.accepted)
        self.assertTrue(
            any("artifact_replay_rejected" in failure for failure in receipt.failures)
        )
        self.assertTrue(
            any("content_sha256_mismatch" in failure for failure in receipt.failures)
        )

    def test_queue_wal_binding_tamper_rejects_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(task_id=TASK_ID, run_id=RUN_ID)
            queue_wal = root / "queue.jsonl.real-wal.jsonl"
            queue_wal.write_text(
                queue_wal.read_text(encoding="utf-8").replace(
                    "QUEUE_EVENT",
                    "ARTIFACT_EVENT",
                    1,
                ),
                encoding="utf-8",
            )

            receipt = reconstructor.replay_and_persist(manifest)

        self.assertFalse(receipt.accepted)
        self.assertTrue(
            any("queue_replay_rejected" in failure for failure in receipt.failures)
        )

    def test_non_deterministic_input_ordering_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(task_id=TASK_ID, run_id=RUN_ID)
            payload = manifest.as_dict()
            payload["expected_wal_record_hashes"] = list(
                reversed(manifest.expected_wal_record_hashes)
            )
            payload["input_manifest_hash"] = ""
            reordered = SnapshotReplayInputManifest(**payload)

            receipt = reconstructor.replay_and_persist(reordered)

        self.assertFalse(receipt.accepted)
        self.assertIn("wal_non_deterministic_ordering", receipt.failures)

    def test_unknown_input_manifest_version_rejects_with_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            reconstructor = _fixture(root)
            manifest = reconstructor.build_input_manifest(task_id=TASK_ID, run_id=RUN_ID)
            payload = manifest.as_dict()
            payload["input_manifest_version"] = "snapshot_replay_input_manifest_v2"
            payload["input_manifest_hash"] = ""

            receipt = reconstructor.replay_and_persist(payload)

        self.assertFalse(receipt.accepted)
        self.assertTrue(
            any("input_manifest_version_invalid" in failure for failure in receipt.failures)
        )
        self.assertEqual(receipt.snapshot_manifest_hash, ZERO_HASH)

    def test_path_traversal_and_symlink_roots_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            with self.assertRaisesRegex(
                SnapshotReplayReconstructionError,
                "wal_source_relpath_must_be_relative",
            ):
                FileBackedSnapshotReplayReconstructor(
                    runtime_root=root,
                    wal_source_relpath="../runtime-wal.jsonl",
                )

            real_root = root / "real-root"
            real_root.mkdir()
            link_root = root / "link-root"
            link_root.symlink_to(real_root)
            with self.assertRaisesRegex(
                SnapshotReplayReconstructionError,
                "runtime_root_is_symlink",
            ):
                FileBackedSnapshotReplayReconstructor(
                    runtime_root=link_root,
                    wal_source_relpath="runtime-wal.jsonl",
                )

    def test_source_has_no_network_provider_subprocess_or_browser_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        forbidden = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imported_roots.intersection(forbidden))
        for marker in ("shell=True", "os.system", "Popen", "while True"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
