"""Hardening tests for local-only artifact metadata storage."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.artifact_store import (
    ArtifactIsolationError,
    ArtifactRecord,
    ArtifactStore,
    ArtifactStoreError,
    ArtifactType,
    ArtifactValidationError,
    QuarantineStatus,
    ReviewStatus,
    infer_artifact_type,
)


class OsEngineArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="seos-artifacts-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.root = self.tmp / "local_artifacts"
        self.store = ArtifactStore(db_path=self.tmp / "catalog.sqlite3", artifact_root=self.root, repo_root=self.repo)
        self.store.initialize()

    def _file(self, name: str, data: bytes = b"payload") -> Path:
        path = self.root / name
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
            "context_packet",
            "asset_index",
            "checksum_manifest",
            "failure_bundle",
            "davinci_handoff",
            "comfyui_output",
            "hfx_proof_result",
        }
        self.assertTrue(expected.issubset({kind.value for kind in ArtifactType}))

    def test_required_fields_and_missing_files_fail_closed(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            ArtifactRecord(
                artifact_id="",
                job_id="job",
                local_path=Path("x"),
                sha256="0" * 64,
                size_bytes=1,
                artifact_type=ArtifactType.AUDIT_JSON.value,
                review_status=ReviewStatus.NEW.value,
                quarantine_status=QuarantineStatus.CLEAN.value,
                quarantine_reason=None,
                local_only=True,
                safe_for_github=False,
                path_policy="absolute_local_only",
                created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
        with self.assertRaises(ArtifactStoreError):
            self.store.register_artifact(job_id="job_1", local_path=self.root / "missing.json")

    def test_checksum_size_type_and_deterministic_serialization_are_recorded(self) -> None:
        path = self._file("context_pack.md", b"hello")
        record = self.store.register_artifact(
            job_id="job_1",
            local_path=path,
            artifact_type=ArtifactType.CONTEXT_PACKET,
        )
        self.assertEqual(record.size_bytes, 5)
        self.assertEqual(record.sha256, self.store.sha256_file(path))
        self.assertEqual(record.artifact_type, "context_packet")
        self.assertEqual(record.to_json(), record.to_json())
        self.assertEqual(json.loads(record.to_json())["artifact_id"], record.artifact_id)

    def test_artifact_review_quarantine_and_publish_policy_are_validated(self) -> None:
        path = self._file("audit.json", b"{}")
        with self.assertRaises(ValueError):
            self.store.register_artifact(job_id="job_1", local_path=path, artifact_type="not_real")
        with self.assertRaises(ArtifactValidationError):
            self.store.register_artifact(
                job_id="job_1",
                local_path=path,
                quarantine_status=QuarantineStatus.QUARANTINED,
            )
        with self.assertRaises(ArtifactValidationError):
            self.store.register_artifact(
                job_id="job_1",
                local_path=path,
                review_status=ReviewStatus.PUBLISH_READY,
                local_only=True,
            )
        record = self.store.register_artifact(
            job_id="job_1",
            local_path=path,
            quarantine_status=QuarantineStatus.QUARANTINED,
            quarantine_reason="operator review",
        )
        self.assertEqual(record.quarantine_reason, "operator review")

    def test_large_binary_artifacts_are_not_github_safe_by_default(self) -> None:
        path = self._file("frame.exr", b"\x00" * 64)
        record = self.store.register_artifact(job_id="job_1", local_path=path, artifact_type=ArtifactType.RENDER_FRAME)
        self.assertFalse(record.safe_for_github)
        self.assertEqual(record.path_policy, "absolute_local_only")

    def test_path_escape_symlink_and_secret_paths_fail_closed(self) -> None:
        outside = self.tmp / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaises(ArtifactIsolationError):
            self.store.register_artifact(job_id="job_1", local_path=outside)

        target = self._file("target.json", b"{}")
        link = self.root / "link.json"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlinks are unavailable on this filesystem")
        with self.assertRaises(ArtifactIsolationError):
            self.store.register_artifact(job_id="job_1", local_path=link)

        secret_path = self.root / ".env"
        secret_path.write_text("TOKEN=raw", encoding="utf-8")
        with self.assertRaises(ArtifactValidationError):
            self.store.register_artifact(job_id="job_1", local_path=secret_path)

    def test_artifact_type_inference_covers_required_outputs(self) -> None:
        cases = {
            "audit.json": ArtifactType.AUDIT_JSON,
            "README.md": ArtifactType.AUDIT_MD,
            "context_pack.md": ArtifactType.CONTEXT_PACKET,
            "index.jsonl": ArtifactType.ASSET_INDEX,
            "SHA256SUMS.txt": ArtifactType.CHECKSUM_MANIFEST,
            "crash.json": ArtifactType.FAILURE_BUNDLE,
            "davinci_handoff.json": ArtifactType.DAVINCI_HANDOFF,
            "comfyui_output.json": ArtifactType.COMFYUI_OUTPUT,
            "shot.hip": ArtifactType.HFX_PROOF_RESULT,
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(infer_artifact_type(Path(name)), expected)


if __name__ == "__main__":
    unittest.main()
