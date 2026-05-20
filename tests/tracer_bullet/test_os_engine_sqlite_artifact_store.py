"""Tracer bullet tests for the SQLite-backed artifact metadata store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.database import OSDatabase
from kernel.os_engine.sqlite_artifact_store import (
    ArtifactPathError,
    ArtifactType,
    ArtifactValidationError,
    QuarantineStatus,
    ReviewStatus,
    SQLiteArtifactStore,
    SQLiteArtifactStoreError,
)


class OSEngineSQLiteArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.artifact_root = self.root / "artifacts"
        self.store = SQLiteArtifactStore(
            database=OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3"),
            artifact_root=self.artifact_root,
        )
        self.store.initialize()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _file(self, name: str, data: bytes = b"payload") -> Path:
        path = self.artifact_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_required_artifact_types_are_declared(self) -> None:
        expected = {
            "audit_json",
            "audit_md",
            "render_frame",
            "preview_image",
            "preview_video",
            "exr_sequence",
            "png_sequence",
            "mov_file",
            "mp4_file",
            "context_packet",
            "asset_index",
            "checksum_manifest",
            "license_report",
            "failure_bundle",
            "screenshot",
            "davinci_handoff",
            "comfyui_output",
            "hfx_proof_result",
            "materialization_summary",
        }
        self.assertTrue(expected.issubset({item.value for item in ArtifactType}))

    def test_checksum_is_deterministic_and_missing_file_fails_closed(self) -> None:
        path = self._file("summary.json", b"{}")
        first = self.store.validate_artifact_file(path)
        second = self.store.validate_artifact_file(path)
        self.assertEqual(first.sha256, second.sha256)
        record = self.store.record_artifact(job_id="job_1", local_path=path, artifact_type="materialization_summary")
        self.assertEqual(record.sha256, first.sha256)
        with self.assertRaises(SQLiteArtifactStoreError):
            self.store.validate_artifact_file(self.artifact_root / "missing.json")

    def test_root_escape_and_symlink_escape_are_rejected(self) -> None:
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaises(ArtifactPathError):
            self.store.record_artifact(job_id="job_1", local_path=outside, artifact_type="audit_json")
        target = self._file("target.json", b"{}")
        link = self.artifact_root / "link.json"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlinks are unavailable on this filesystem")
        with self.assertRaises(ArtifactPathError):
            self.store.record_artifact(job_id="job_1", local_path=link, artifact_type="audit_json")

    def test_review_quarantine_and_publish_policy_validation(self) -> None:
        path = self._file("audit.json", b"{}")
        with self.assertRaises(ArtifactValidationError):
            self.store.record_artifact(job_id="job_1", local_path=path, artifact_type="unsafe")
        with self.assertRaises(ArtifactValidationError):
            self.store.record_artifact(job_id="job_1", local_path=path, artifact_type="audit_json", review_status="unsafe")
        with self.assertRaises(ArtifactValidationError):
            self.store.record_artifact(
                job_id="job_1",
                local_path=path,
                artifact_type="audit_json",
                quarantine_status=QuarantineStatus.QUARANTINED,
            )
        record = self.store.record_artifact(job_id="job_1", local_path=path, artifact_type="audit_json")
        self.assertFalse(record.safe_to_publish)
        with self.assertRaises(ArtifactValidationError):
            self.store.record_artifact(
                job_id="job_2",
                local_path=path,
                artifact_type="audit_json",
                local_only=True,
                safe_to_publish=True,
            )
        reviewed = self.store.review_artifact(record.artifact_id, review_status=ReviewStatus.APPROVED)
        self.assertEqual(reviewed.review_status, "approved")
        with self.assertRaises(ArtifactValidationError):
            self.store.quarantine_artifact(record.artifact_id, reason="")
        quarantined = self.store.quarantine_artifact(record.artifact_id, reason="bad checksum")
        self.assertEqual(quarantined.quarantine_status, "quarantined")

    def test_reopen_preserves_artifact_and_large_binary_defaults_to_not_publish_safe(self) -> None:
        path = self._file("frame.exr", b"\x00" * 64)
        record = self.store.record_artifact(job_id="job_1", local_path=path, artifact_type="render_frame")
        self.assertFalse(record.safe_to_publish)
        reopened = SQLiteArtifactStore(
            database=OSDatabase(root=self.root, db_path=self.root / "brain.sqlite3"),
            artifact_root=self.artifact_root,
        )
        self.assertEqual(reopened.get_artifact(record.artifact_id).sha256, record.sha256)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
