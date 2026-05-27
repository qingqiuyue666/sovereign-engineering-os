"""Tests for Snapshot/Replay Store Contract V1."""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from kernel.stores import snapshot_replay_contract as contract


SOURCE_PATH = Path("kernel/stores/snapshot_replay_contract.py")


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _snapshot(kind: str, **overrides: object) -> contract.SnapshotManifest:
    payload: dict[str, object] = {
        "snapshot_manifest_id": "snapshot-manifest-" + kind,
        "snapshot_replay_contract_version": contract.SNAPSHOT_REPLAY_CONTRACT_VERSION,
        "snapshot_id": "snapshot-" + kind,
        "snapshot_kind": kind,
        "task_id": "task-001",
        "run_id": "run-001",
        "snapshot_root_hash": _hash("root-" + kind),
        "changed_path_digests": (
            (_hash("path-a"), _hash("content-a-" + kind)),
            (_hash("path-b"), _hash("content-b-" + kind)),
        ),
        "artifact_manifest_hash": _hash("artifact-" + kind),
        "wal_record_hash": _hash("wal-" + kind),
        "rollback_plan_hash": _hash("rollback-plan"),
        "created_at": "2026-05-27T00:00:00Z",
    }
    payload.update(overrides)
    return contract.SnapshotManifest(**payload)  # type: ignore[arg-type]


class SnapshotReplayContractV1Tests(unittest.TestCase):
    def test_manifest_hash_is_deterministic_and_excludes_created_at(self) -> None:
        manifest = _snapshot("pre_execution")
        later = _snapshot("pre_execution", created_at="2030-01-01T00:00:00Z")

        self.assertEqual(manifest.manifest_hash, contract.compute_snapshot_manifest_hash(manifest))
        self.assertEqual(manifest.manifest_hash, later.manifest_hash)

    def test_reconstructs_matching_pre_post_snapshot_pair(self) -> None:
        pre = _snapshot("pre_execution")
        post = _snapshot("post_execution")

        receipt = contract.reconstruct_snapshot_pair(pre, post)

        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.changed_path_count, 2)
        self.assertEqual(receipt.rollback_plan_hash, _hash("rollback-plan"))
        self.assertEqual(
            receipt.reconstruction_hash,
            contract.compute_snapshot_reconstruction_hash(receipt),
        )

    def test_reconstruction_rejects_identity_and_rollback_mismatch(self) -> None:
        pre = _snapshot("pre_execution")
        post = _snapshot(
            "post_execution",
            task_id="task-other",
            rollback_plan_hash=_hash("different-rollback-plan"),
        )

        receipt = contract.reconstruct_snapshot_pair(pre, post)

        self.assertFalse(receipt.accepted)
        self.assertIn("snapshot_identity_mismatch", receipt.failures)
        self.assertIn("rollback_plan_hash_mismatch", receipt.failures)

    def test_reconstruction_rejects_wrong_snapshot_kinds(self) -> None:
        pre = _snapshot("post_execution")
        post = _snapshot("pre_execution")

        receipt = contract.reconstruct_snapshot_pair(pre, post)

        self.assertFalse(receipt.accepted)
        self.assertIn("pre_snapshot_kind_mismatch", receipt.failures)
        self.assertIn("post_snapshot_kind_mismatch", receipt.failures)

    def test_manifest_rejects_hash_mismatch_and_bad_changed_digest(self) -> None:
        with self.assertRaisesRegex(ValueError, "manifest_hash_mismatch"):
            _snapshot("pre_execution", manifest_hash=_hash("wrong"))
        with self.assertRaisesRegex(ValueError, "path_digest_duplicate"):
            _snapshot(
                "pre_execution",
                changed_path_digests=((_hash("path-a"), _hash("content-a")), (_hash("path-a"), _hash("content-b"))),
            )
        with self.assertRaisesRegex(ValueError, "content_digest_must_be_sha256"):
            _snapshot("pre_execution", changed_path_digests=((_hash("path-a"), "not-a-digest"),))

    def test_mapping_rejects_raw_path_content_and_secret_fields(self) -> None:
        manifest = _snapshot("pre_execution").as_dict()
        for field_name in ("path", "raw_path", "raw_content", "stdout", "api_key"):
            payload = dict(manifest)
            payload[field_name] = "blocked"
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "snapshot_manifest_field_forbidden"):
                    contract.validate_snapshot_manifest(payload)

    def test_source_has_no_file_io_runtime_or_rollback_surface(self) -> None:
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
        self.assertNotIn("rollback(", source)


if __name__ == "__main__":
    unittest.main()
