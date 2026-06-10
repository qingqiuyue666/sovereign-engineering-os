"""Tracer-bullet tests for minimal asset inventory v1."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import tempfile
import unittest

from kernel.runtime.minimal_asset_inventory import (
    AssetInventoryRecord,
    classify_media,
    scan_asset_inventory,
    streaming_sha256,
)

POLICY_PATH = Path("governance/assets/minimal_asset_inventory_v1.json")
SOURCE_PATH = Path("kernel/runtime/minimal_asset_inventory.py")


class MinimalAssetInventoryTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundaries(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "minimal_asset_inventory_v1")
        self.assertTrue(policy["explicit_roots_only"])
        self.assertFalse(policy["home_root_allowed"])
        self.assertFalse(policy["filesystem_root_allowed"])
        self.assertFalse(policy["file_mutation_allowed"])
        self.assertFalse(policy["embeddings_allowed"])
        self.assertFalse(policy["lancedb_allowed"])
        self.assertFalse(policy["openusd_runtime_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])

    def test_inventory_fixture_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "notes.md").write_text("hello", encoding="utf-8")
            (root / "image.png").write_bytes(b"\x89PNG\r\n")
            nested = root / "nested"
            nested.mkdir()
            (nested / "scene.blend").write_bytes(b"blend")

            records = scan_asset_inventory({"fixture": root})

        self.assertEqual(len(records), 3)
        self.assertTrue(all(isinstance(record, AssetInventoryRecord) for record in records))
        self.assertEqual(
            [record.relative_path for record in records],
            ["image.png", "nested/scene.blend", "notes.md"],
        )
        self.assertEqual(records[0].root_id, "fixture")

    def test_streaming_sha256_correct(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "large.bin"
            payload = b"abc" * 400000
            path.write_bytes(payload)
            expected = "sha256:" + hashlib.sha256(payload).hexdigest()
            self.assertEqual(streaming_sha256(path), expected)

    def test_relative_path_deterministic(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            first = scan_asset_inventory({"fixture": root})
            second = scan_asset_inventory({"fixture": root})
        self.assertEqual(
            [record.relative_path for record in first],
            [record.relative_path for record in second],
        )
        self.assertEqual([record.relative_path for record in first], ["a.txt", "b.txt"])

    def test_home_and_root_scan_rejected(self):
        with self.assertRaises(ValueError):
            scan_asset_inventory({"home": Path.home()})
        with self.assertRaises(ValueError):
            scan_asset_inventory({"root": Path("/")})

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            with self.assertRaises(ValueError):
                scan_asset_inventory({"bad": root / ".." / root.name})

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "root"
            outside = Path(tempdir) / "outside"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            os.symlink(outside, root / "escape.txt")
            with self.assertRaises(ValueError):
                scan_asset_inventory({"fixture": root})

    def test_media_class_classification_works(self):
        cases = {
            "tool.py": "CODE",
            "readme.md": "TEXT",
            "plate.exr": "UNKNOWN",
            "image.jpg": "IMAGE",
            "movie.mov": "VIDEO",
            "sound.wav": "AUDIO",
            "sim.vdb": "VFX_CACHE",
            "cache.bgeo.sc": "VFX_CACHE",
            "scene.hip": "DCC_SCENE",
            "pack.zip": "ARCHIVE",
            "mystery.asset": "UNKNOWN",
        }
        for filename, media_class in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(classify_media(filename), media_class)

    def test_no_mutation(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            file_path = root / "asset.txt"
            file_path.write_text("stable", encoding="utf-8")
            before = file_path.stat().st_mtime_ns
            scan_asset_inventory({"fixture": root})
            after = file_path.stat().st_mtime_ns
        self.assertEqual(before, after)

    def test_deterministic_content_hash_excluding_observed_at(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "asset.txt").write_text("stable", encoding="utf-8")
            first = scan_asset_inventory({"fixture": root})[0]
            second = scan_asset_inventory({"fixture": root})[0]
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertNotEqual(first.observed_at, "")

    def test_no_heavy_dependency_imports(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "lancedb",
            "numpy",
            "PIL",
            "cv2",
            "pxr",
            "openusd",
            "requests",
            "socket",
            "webbrowser",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
