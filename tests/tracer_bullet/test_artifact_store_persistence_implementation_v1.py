"""Tests for Artifact Store Persistence Implementation V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.stores.artifact_store_persistence import (
    REAL_WAL_BINDING_STATUS,
    ArtifactStorePersistenceError,
    ArtifactStoreReplayError,
    FileBackedArtifactStore,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


SOURCE_PATH = Path("kernel/stores/artifact_store_persistence.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class ArtifactStorePersistenceImplementationV1Tests(unittest.TestCase):
    def test_write_reopen_replay_and_real_wal_binding_are_durable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)

            receipt = store.write_json_artifact(
                artifact_type="audit_json",
                task_id="task-001",
                run_id="run-001",
                payload={"status": "ok", "step": 1},
                provenance_hash=_hash("provenance"),
                metadata={"operator": "local", "priority": 1},
                created_at="2026-05-28T00:00:00+00:00",
            )
            reopened = FileBackedArtifactStore(root)
            records = reopened.read_records()
            replay = reopened.replay()
            wal_records = FileBackedRealWalStorage(root / "artifact-store.real-wal.jsonl").read_records()
            artifact_path = Path(receipt.artifact_path)
            artifact_exists = artifact_path.is_file()
            wal_bindings = dict(wal_records[0].digest_bindings)

        self.assertTrue(artifact_exists)
        self.assertEqual(len(records), 1)
        self.assertTrue(replay.accepted)
        self.assertEqual(records[0].manifest.artifact_id, receipt.manifest.artifact_id)
        self.assertEqual(records[0].manifest.content_sha256, receipt.manifest.content_sha256)
        self.assertEqual(records[0].real_wal_binding_status, REAL_WAL_BINDING_STATUS)
        self.assertEqual(wal_records[0].record_hash, receipt.wal_record_hash)
        self.assertEqual(wal_records[0].record_type, "ARTIFACT_EVENT")
        self.assertEqual(wal_bindings["artifact_content_hash"], receipt.manifest.content_sha256)
        self.assertEqual(wal_bindings["artifact_metadata_hash"], receipt.metadata_hash)

    def test_duplicate_content_and_existing_path_fail_closed_without_extra_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            store.write_artifact(
                artifact_type="audit_json",
                task_id="task-001",
                run_id="run-001",
                content=b"same-content",
                provenance_hash=_hash("provenance"),
                created_at="2026-05-28T00:00:00+00:00",
            )
            before_log = (root / "artifact-manifests.jsonl").read_text(encoding="utf-8")
            before_wal = (root / "artifact-store.real-wal.jsonl").read_text(encoding="utf-8")

            with self.assertRaisesRegex(ArtifactStorePersistenceError, "artifact_id_already_persisted"):
                store.write_artifact(
                    artifact_type="audit_json",
                    task_id="task-002",
                    run_id="run-002",
                    content=b"same-content",
                    provenance_hash=_hash("provenance-2"),
                    created_at="2026-05-28T00:00:01+00:00",
                )

            after_log = (root / "artifact-manifests.jsonl").read_text(encoding="utf-8")
            after_wal = (root / "artifact-store.real-wal.jsonl").read_text(encoding="utf-8")

        self.assertEqual(after_log, before_log)
        self.assertEqual(after_wal, before_wal)

    def test_metadata_and_store_paths_reject_secret_like_or_escape_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            with self.assertRaisesRegex(ArtifactStorePersistenceError, "metadata_field_forbidden"):
                store.write_json_artifact(
                    artifact_type="audit_json",
                    task_id="task-001",
                    run_id="run-001",
                    payload={"status": "ok"},
                    provenance_hash=_hash("provenance"),
                    metadata={"api_key": "blocked"},
                )
            with self.assertRaisesRegex(ArtifactStorePersistenceError, "manifest_log_path_escapes_artifact_root"):
                FileBackedArtifactStore(
                    root,
                    manifest_log_path=Path(tempdir) / "outside-manifests.jsonl",
                )
            with self.assertRaisesRegex(ArtifactStorePersistenceError, "artifact_root_secret_like"):
                FileBackedArtifactStore(Path(tempdir) / ".env")

    def test_tampered_artifact_or_manifest_log_replay_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            receipt = store.write_json_artifact(
                artifact_type="audit_json",
                task_id="task-001",
                run_id="run-001",
                payload={"status": "ok"},
                provenance_hash=_hash("provenance"),
                created_at="2026-05-28T00:00:00+00:00",
            )
            Path(receipt.artifact_path).write_text('{"status":"tampered"}', encoding="utf-8")
            replay = store.replay()

            with self.assertRaisesRegex(ArtifactStoreReplayError, "content_sha256_mismatch"):
                store.read_records()

        self.assertFalse(replay.accepted)
        self.assertIn("content_sha256_mismatch", replay.rejection_reasons)

    def test_tampered_real_wal_binding_blocks_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            store.write_json_artifact(
                artifact_type="audit_json",
                task_id="task-001",
                run_id="run-001",
                payload={"status": "ok"},
                provenance_hash=_hash("provenance"),
                created_at="2026-05-28T00:00:00+00:00",
            )
            wal_path = root / "artifact-store.real-wal.jsonl"
            wal_payload = json.loads(wal_path.read_text(encoding="utf-8"))
            wal_payload["record_type"] = "QUEUE_EVENT"
            wal_path.write_text(json.dumps(wal_payload) + "\n", encoding="utf-8")

            replay = store.replay()

            with self.assertRaisesRegex(ArtifactStoreReplayError, "real_wal_replay_failed"):
                store.read_records()

        self.assertFalse(replay.accepted)
        self.assertIn("real_wal_replay_failed", replay.rejection_reasons[0])

    def test_listing_is_deterministic_and_filters_by_contract_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "artifact-store"
            store = FileBackedArtifactStore(root)
            second = store.write_json_artifact(
                artifact_type="operator_report",
                task_id="task-002",
                run_id="run-002",
                payload={"status": "second"},
                provenance_hash=_hash("provenance-2"),
                created_at="2026-05-28T00:00:01+00:00",
            )
            first = store.write_json_artifact(
                artifact_type="audit_json",
                task_id="task-001",
                run_id="run-001",
                payload={"status": "first"},
                provenance_hash=_hash("provenance-1"),
                created_at="2026-05-28T00:00:00+00:00",
            )

            listed = store.list_manifests()
            task_filtered = store.list_manifests(task_id="task-001")

        self.assertEqual(
            [item.artifact_id for item in listed],
            sorted([first.manifest.artifact_id, second.manifest.artifact_id]),
        )
        self.assertEqual([item.artifact_id for item in task_filtered], [first.manifest.artifact_id])

    def test_source_has_no_network_credentials_subprocess_or_sqlite_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
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
        self.assertNotIn("os.environ", source)
        self.assertNotIn("Popen", source)
        self.assertNotIn("os.system", source)


if __name__ == "__main__":
    unittest.main()
