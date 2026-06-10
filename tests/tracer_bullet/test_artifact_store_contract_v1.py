"""Tests for Artifact Store Contract V1."""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from kernel.stores import artifact_store_contract as contract


SOURCE_PATH = Path("kernel/stores/artifact_store_contract.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _manifest(**overrides: object) -> contract.ArtifactManifest:
    content_sha256 = _hash("artifact-content")
    payload: dict[str, object] = {
        "artifact_type": "audit_json",
        "task_id": "task-001",
        "run_id": "run-001",
        "content_sha256": content_sha256,
        "size_bytes": 128,
        "wal_record_hash": _hash("wal-record"),
        "provenance_hash": _hash("provenance"),
        "created_at": "2026-05-27T00:00:00Z",
    }
    payload.update(overrides)
    return contract.artifact_manifest_from_ingest(payload)


class ArtifactStoreContractV1Tests(unittest.TestCase):
    def test_manifest_hash_is_deterministic_and_excludes_created_at(self) -> None:
        manifest = _manifest()
        later = _manifest(created_at="2030-01-01T00:00:00Z")

        self.assertEqual(manifest.manifest_hash, contract.compute_artifact_manifest_hash(manifest))
        self.assertEqual(manifest.manifest_hash, later.manifest_hash)

    def test_ingest_builds_digest_addressed_manifest_defaults(self) -> None:
        manifest = _manifest()
        digest = manifest.content_sha256.removeprefix("sha256:")

        self.assertEqual(manifest.artifact_id, "artifact-" + digest[:24])
        self.assertTrue(manifest.storage_relpath.startswith(digest[:2] + "/" + digest[2:] + "/"))
        self.assertEqual(manifest.retention_marker, "retain")
        self.assertEqual(manifest.quarantine_marker, "clean")
        self.assertTrue(manifest.local_only)

    def test_verification_accepts_matching_digest_and_size(self) -> None:
        manifest = _manifest()

        receipt = contract.verify_artifact_manifest(
            manifest,
            observed_content_sha256=manifest.content_sha256,
            observed_size_bytes=manifest.size_bytes,
        )

        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.quarantine_required)
        self.assertEqual(
            receipt.verification_hash,
            contract.compute_artifact_verification_hash(receipt),
        )

    def test_verification_rejects_digest_and_size_mismatch(self) -> None:
        manifest = _manifest()

        receipt = contract.verify_artifact_manifest(
            manifest,
            observed_content_sha256=_hash("different-content"),
            observed_size_bytes=999,
        )

        self.assertFalse(receipt.accepted)
        self.assertTrue(receipt.quarantine_required)
        self.assertIn("content_sha256_mismatch", receipt.failures)
        self.assertIn("size_bytes_mismatch", receipt.failures)

    def test_quarantined_manifest_fails_closed(self) -> None:
        manifest = _manifest(quarantine_marker="quarantined")

        receipt = contract.verify_artifact_manifest(
            manifest,
            observed_content_sha256=manifest.content_sha256,
            observed_size_bytes=manifest.size_bytes,
        )

        self.assertFalse(receipt.accepted)
        self.assertIn("artifact_quarantined", receipt.failures)

    def test_manifest_rejects_path_escape_and_digest_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "storage_relpath_must_be_relative"):
            _manifest(storage_relpath="../escape.json")
        with self.assertRaisesRegex(ValueError, "storage_relpath_digest_mismatch"):
            _manifest(storage_relpath="00/" + "0" * 62 + "/artifact.json")

    def test_manifest_rejects_raw_content_secret_and_raw_output_fields(self) -> None:
        for field_name in ("raw_content", "content", "raw_stdout", "stderr", "api_key"):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "artifact_manifest_field_forbidden"):
                    _manifest(**{field_name: "blocked"})

    def test_manifest_rejects_bad_type_marker_and_hash(self) -> None:
        with self.assertRaisesRegex(ValueError, "artifact_type_invalid"):
            _manifest(artifact_type="raw_binary_blob")
        with self.assertRaisesRegex(ValueError, "content_sha256_must_be_sha256"):
            _manifest(content_sha256="not-a-digest")
        with self.assertRaisesRegex(ValueError, "manifest_hash_mismatch"):
            _manifest(manifest_hash=_hash("wrong"))

    def test_source_has_no_runtime_or_binary_io_surface(self) -> None:
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
            "click",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "sqlite3",
            "subprocess",
            "typer",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imported_roots.intersection(forbidden))
        self.assertNotIn(".open(", source)
        self.assertNotIn("read_bytes", source)
        self.assertNotIn("write_bytes", source)


if __name__ == "__main__":
    unittest.main()
