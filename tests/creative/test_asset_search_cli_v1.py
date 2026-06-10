from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.assets.asset_search import search_asset_library
from creative.assets.local_asset_library import build_asset_library_scan, write_asset_library_outputs

REPO = Path(__file__).resolve().parents[2]


class AssetSearchCliV1Tests(unittest.TestCase):
    def test_practical_queries_return_actionable_result_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            _write_search_fixture(asset_root)
            scan = build_asset_library_scan(asset_root, mode="public", max_depth=8)

            cases = {
                "houdini-fx-assets": ("assets", 1),
                "vdb-cache-assets": ("assets", 1),
                "missing-texture-sets": ("texture_sets", 1),
                "duplicate-video-audio": ("duplicate_groups", 1),
                "incomplete-archives": ("archive_warnings", 1),
                "empty-directories": ("empty_directories", 1),
                "incomplete-packs": ("production_groups", 1),
            }
            for query, (result_type, minimum_count) in cases.items():
                with self.subTest(query=query):
                    result = search_asset_library(scan, query=query, mode="public")
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["result_type"], result_type)
                    self.assertGreaterEqual(result["result_count"], minimum_count)
                    self.assertTrue(result["next_actions"])

    def test_generic_filters_and_duplicate_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            _write_search_fixture(asset_root)
            scan = build_asset_library_scan(asset_root, mode="public", max_depth=8)

            houdini = search_asset_library(scan, category="houdini", mode="public")
            self.assertEqual(houdini["result_count"], 1)
            self.assertEqual(houdini["items"][0]["extension"], ".hda")

            duplicate_videos = search_asset_library(scan, category="video", duplicate_only=True, mode="public")
            self.assertEqual(duplicate_videos["result_count"], 2)
            self.assertNotIn("absolute_path", json.dumps(duplicate_videos, sort_keys=True))

            small = search_asset_library(scan, extension="vdb", min_size=1, max_size=1000, mode="public")
            self.assertEqual(small["result_count"], 1)

    def test_cli_loads_registry_json_without_rescanning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            output_dir = Path(temp_dir) / "outputs"
            output_dir.mkdir()
            _write_search_fixture(asset_root)
            scan = build_asset_library_scan(asset_root, mode="public", max_depth=8)
            registry_json = output_dir / "asset_library.json"
            write_asset_library_outputs(scan, root=asset_root, output_json=registry_json)

            result = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "search-assets",
                    "--registry-json",
                    registry_json.as_posix(),
                    "--query",
                    "missing-texture-sets",
                    "--mode",
                    "public",
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["result_type"], "texture_sets")
            self.assertGreaterEqual(payload["result_count"], 1)
            self.assertNotIn(asset_root.as_posix(), result.stdout)


def _write_search_fixture(root: Path) -> None:
    files = {
        "houdini/impact_fx.hda": "houdini asset",
        "cache/smoke.vdb": "vdb cache",
        "lookdev/energy_BaseColor.png": "base",
        "lookdev/energy_Normal.png": "normal",
        "lookdev/energy.mtlx": "<materialx />",
        "models/energy.fbx": "model",
        "archives/fx_pack.part1.rar": "archive part one",
        "archives/fx_pack.part3.rar": "archive part three",
        "media/plate_a.mkv": "same media duplicate",
        "media/plate_b.mkv": "same media duplicate",
        "audio/hit_a.wav": "same audio duplicate",
        "audio/hit_b.wav": "same audio duplicate",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "empty" / "placeholder").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    unittest.main()
