"""Checksum and private-storage tests for the HFX render artifact ledger."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import stat
import tempfile
import unittest

from kernel.vfx.render_artifact_ledger import (
    ArtifactLedgerError,
    hash_exr_directory,
    record_render_artifact,
)


EXR_MAGIC = b"\x76\x2f\x31\x01"


def _exr_payload(label: bytes) -> bytes:
    return EXR_MAGIC + label + (b"\x00" * 32)


def _write_exr(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


class RenderArtifactLedgerTests(unittest.TestCase):
    def test_hash_exr_directory_generates_stable_sha256_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            render_dir = Path(temp_dir_name) / "renders"
            render_dir.mkdir()
            frame_1 = _exr_payload(b"frame-0001")
            frame_2 = _exr_payload(b"frame-0002")
            _write_exr(render_dir / "shot.0001.exr", frame_1)
            _write_exr(render_dir / "shot.0002.exr", frame_2)

            directory_hash = hash_exr_directory(render_dir, sequence_glob="shot.*.exr")

            self.assertEqual(directory_hash.frame_numbers, (1, 2))
            self.assertEqual(
                [checksum.sha256 for checksum in directory_hash.files],
                [
                    hashlib.sha256(frame_1).hexdigest(),
                    hashlib.sha256(frame_2).hexdigest(),
                ],
            )
            expected_material = {
                "files": [checksum.as_dict() for checksum in directory_hash.files],
                "sequence_glob": "shot.*.exr",
            }
            expected_directory_sha256 = hashlib.sha256(
                json.dumps(
                    expected_material,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            self.assertEqual(directory_hash.directory_sha256, expected_directory_sha256)

    def test_record_render_artifact_writes_private_ledger_outside_render_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            render_dir = temp_dir / "renders"
            ledger_root = temp_dir / "private-ledger"
            render_dir.mkdir()
            _write_exr(render_dir / "shot.0001.exr", _exr_payload(b"frame-0001"))
            _write_exr(render_dir / "shot.0002.exr", _exr_payload(b"frame-0002"))

            record = record_render_artifact(
                render_dir,
                sequence_glob="shot.*.exr",
                frame_pattern="shot.%04d.exr",
                metadata={"stage": "unit-test"},
                ledger_root=ledger_root,
            )

            self.assertIsNotNone(record.ledger_path)
            assert record.ledger_path is not None
            self.assertTrue(record.ledger_path.exists())
            self.assertTrue((ledger_root / "latest.json").exists())
            self.assertTrue((ledger_root / "index.jsonl").exists())
            self.assertEqual(record.ledger_path.parent, ledger_root.resolve() / "records")
            self.assertFalse(record.ledger_path.is_relative_to(render_dir))
            self.assertEqual(stat.S_IMODE(ledger_root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(record.ledger_path.stat().st_mode), 0o600)

            payload = json.loads(record.ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["directory_sha256"], record.directory_sha256)
            self.assertEqual(payload["metadata"], {"stage": "unit-test"})
            self.assertEqual(payload["frame_count"], 2)

    def test_ledger_root_inside_git_worktree_is_rejected_before_write(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temp_dir_name:
            render_dir = Path(temp_dir_name) / "renders"
            render_dir.mkdir()
            _write_exr(render_dir / "shot.0001.exr", _exr_payload(b"frame-0001"))
            rejected_ledger_root = repo_root / ".hfx-render-ledger-test"

            with self.assertRaisesRegex(ArtifactLedgerError, "outside a Git worktree"):
                record_render_artifact(
                    render_dir,
                    sequence_glob="shot.*.exr",
                    frame_pattern="shot.%04d.exr",
                    ledger_root=rejected_ledger_root,
                )

            self.assertFalse(rejected_ledger_root.exists())


if __name__ == "__main__":
    unittest.main()
