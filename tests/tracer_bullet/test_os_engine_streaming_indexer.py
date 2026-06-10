"""Hardening tests for the low-memory streaming asset indexer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kernel.os_engine import streaming_indexer
from kernel.os_engine.streaming_indexer import (
    ASSET_EXTENSIONS,
    PathEscapeError,
    StreamingAssetIndexer,
    StreamingIndexerError,
    _asset_kind,
)


class OsEngineStreamingIndexerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="seos-indexer-"))
        self.scan_root = self.tmp / "inbox"
        self.output_root = self.tmp / "indexes"
        self.scan_root.mkdir()

    def _write(self, relative: str, data: bytes = b"asset") -> Path:
        path = self.scan_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _indexer(self) -> StreamingAssetIndexer:
        return StreamingAssetIndexer(scan_root=self.scan_root, output_root=self.output_root, chunk_size=4)

    def test_supported_asset_extensions_are_classified(self) -> None:
        cases = {
            ".hip": "houdini_scene",
            ".hda": "houdini_digital_asset",
            ".otl": "houdini_operator_type_library",
            ".vdb": "volume_cache",
            ".abc": "alembic_cache",
            ".usd": "usd_scene",
            ".exr": "render_frame",
            ".png": "image",
            ".mov": "video",
            ".hdr": "hdri",
            ".tif": "pbr_texture",
            ".cube": "lut",
            ".ocio": "ocio",
            ".fbx": "fbx",
            ".obj": "obj",
            ".blend": "blender",
            ".ztl": "zbrush",
            ".safetensors": "comfyui_model",
            ".drp": "unknown",
            ".aep": "ae_template",
            ".notknown": "unknown",
        }
        for extension, expected in cases.items():
            with self.subTest(extension=extension):
                self.assertEqual(_asset_kind(extension), expected)
        self.assertIn(".hip", ASSET_EXTENSIONS)

    def test_scanner_walks_deterministically_and_indexes_binary_metadata_only(self) -> None:
        self._write("b/file.vdb", b"\x00\x01")
        self._write("a/file.hip", b"\x00\x02")
        summary = self._indexer().scan(output_path=self.output_root / "index.jsonl")
        rows = [json.loads(line) for line in summary.output_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["relative_path"] for row in rows], ["a/file.hip", "b/file.vdb"])
        self.assertNotIn("full_text", rows[0])
        self.assertEqual(summary.indexed_count, 2)

    def test_large_hashing_uses_chunked_reads_and_never_unbounded_read_bytes(self) -> None:
        self._write("large.exr", b"abcdef")
        chunk_sizes: list[int] = []
        original_hash = streaming_indexer.sha256_file

        def tracking_hash(path: Path, *, chunk_size: int) -> str:
            chunk_sizes.append(chunk_size)
            return original_hash(path, chunk_size=chunk_size)

        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("read_bytes forbidden")):
            with mock.patch.object(streaming_indexer, "sha256_file", tracking_hash):
                self._indexer().scan(output_path=self.output_root / "index.jsonl")
        self.assertEqual(chunk_sizes, [4])

    def test_jsonl_reports_duplicates_skips_quarantines_and_budget(self) -> None:
        self._write("one.hip", b"same")
        self._write("two.hip", b"same")
        self._write("note.txt", b"skip")
        summary = self._indexer().scan(output_path=self.output_root / "index.jsonl", max_files=2, max_runtime_seconds=10)
        rows = [json.loads(line) for line in summary.output_path.read_text(encoding="utf-8").splitlines()]
        skipped = summary.skipped_report_path.read_text(encoding="utf-8")
        quarantines = [json.loads(line) for line in summary.quarantine_report_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(summary.max_files, 2)
        self.assertEqual(summary.max_runtime_seconds, 10)
        self.assertEqual(summary.duplicate_count, 1)
        self.assertIn("unsupported_extension", skipped)
        self.assertTrue(all(row["quarantine_status"] == "blocked" for row in rows))
        self.assertTrue(all(item["reason"] for item in quarantines))

    def test_max_files_limit_is_respected_and_asset_index_is_stable_for_stable_inputs(self) -> None:
        first = self._write("first.hip", b"1")
        second = self._write("second.vdb", b"2")
        for path in (first, second):
            path.touch()
        summary_one = self._indexer().scan(output_path=self.output_root / "one.jsonl", max_files=1)
        summary_two = self._indexer().scan(output_path=self.output_root / "two.jsonl", max_files=1)
        self.assertEqual(summary_one.indexed_count, 1)
        self.assertEqual(summary_one.output_path.read_text(encoding="utf-8"), summary_two.output_path.read_text(encoding="utf-8"))

    def test_symlink_handling_and_path_escape_are_fail_closed_or_explicit(self) -> None:
        target = self._write("target.hip", b"asset")
        link = self.scan_root / "link.hip"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlinks are unavailable on this filesystem")
        summary = self._indexer().scan(output_path=self.output_root / "index.jsonl")
        rows = [json.loads(line) for line in summary.output_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["relative_path"] for row in rows], ["target.hip"])
        with self.assertRaises(PathEscapeError):
            self._indexer()._record_for_path(self.scan_root.resolve(), self.tmp / "outside.hip")

    def test_invalid_budget_fails_closed(self) -> None:
        with self.assertRaises(StreamingIndexerError):
            self._indexer().scan(output_path=self.output_root / "index.jsonl", max_files=0)


if __name__ == "__main__":
    unittest.main()
