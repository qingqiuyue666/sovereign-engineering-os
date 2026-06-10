from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.assets.local_asset_library import (
    build_asset_library_scan,
    write_asset_library_outputs,
)

REPO = Path(__file__).resolve().parents[2]


class RealLocalAssetScannerV1Tests(unittest.TestCase):
    def test_public_scan_classifies_and_flags_production_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            _write_fixture_library(asset_root)

            scan = build_asset_library_scan(asset_root, mode="public", max_depth=8)
            summary = scan["summary"]
            categories = summary["category_counts"]

            self.assertEqual(scan["asset_root"], "<asset-root>")
            self.assertTrue(scan["read_only"])
            self.assertFalse(scan["destructive_actions_performed"])
            self.assertNotIn(asset_root.as_posix(), json.dumps(scan, sort_keys=True))
            self.assertGreaterEqual(summary["total_assets"], 17)
            for category in (
                "houdini",
                "unreal",
                "blender",
                "zbrush",
                "after_effects",
                "davinci",
                "comfyui",
                "textures",
                "materials",
                "hdri",
                "vdb_cache",
                "fbx_obj_usd_alembic",
                "video",
                "audio",
                "lut",
                "scripts",
                "archives",
                "unknown",
            ):
                self.assertIn(category, categories)
            self.assertEqual(summary["duplicate_group_count"], 1)
            self.assertEqual(scan["duplicate_groups"][0]["deletion_performed"], False)
            self.assertEqual(scan["archive_warnings"][0]["missing_part_numbers"], [2])
            self.assertGreaterEqual(summary["empty_directory_count"], 1)
            self.assertGreaterEqual(summary["incomplete_texture_set_count"], 1)
            self.assertGreaterEqual(summary["likely_incomplete_pack_count"], 1)
            self.assertTrue(any(item["relative_path"] == "empty/placeholder" for item in scan["empty_directories"]))
            self.assertTrue(any("missing multipart archive" in action.lower() for action in scan["next_actions"]))

    def test_cli_writes_sanitized_json_and_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            output_dir = Path(temp_dir) / "outputs"
            output_dir.mkdir()
            _write_fixture_library(asset_root)
            output_json = output_dir / "asset_library.json"
            output_md = output_dir / "asset_library.md"

            result = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "scan-assets",
                    "--root",
                    asset_root.as_posix(),
                    "--mode",
                    "public",
                    "--max-depth",
                    "8",
                    "--output-json",
                    output_json.as_posix(),
                    "--output-md",
                    output_md.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            self.assertNotIn(asset_root.as_posix(), output_json.read_text(encoding="utf-8"))
            report = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Real Local Asset Library Report", report)
            self.assertIn("Duplicate Groups", report)
            self.assertIn("Archive Warnings", report)

    def test_report_output_inside_asset_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_root = Path(temp_dir) / "assets"
            _write_fixture_library(asset_root)
            scan = build_asset_library_scan(asset_root, mode="public", max_depth=8)

            with self.assertRaises(ValueError):
                write_asset_library_outputs(
                    scan,
                    root=asset_root,
                    output_json=asset_root / "scan.json",
                )


def _write_fixture_library(root: Path) -> None:
    files = {
        "houdini/impact_fx.hip": "houdini scene placeholder",
        "unreal/energy_hit.uproject": "unreal project placeholder",
        "blender/prop.blend": "blender scene placeholder",
        "zbrush/creature.ztl": "zbrush tool placeholder",
        "after_effects/comp.aep": "after effects placeholder",
        "davinci/grade.drp": "davinci project placeholder",
        "comfyui/workflows/shot_workflow.json": "{\"nodes\": []}",
        "lookdev/energy_BaseColor.1001.png": "base",
        "lookdev/energy_Normal.1001.png": "normal",
        "lookdev/energy_Roughness.1001.png": "roughness",
        "lookdev/crack_albedo.png": "crack base",
        "lookdev/crack_normal.png": "crack normal",
        "lookdev/energy.mtlx": "<materialx />",
        "lookdev/studio.hdr": "hdr data",
        "cache/smoke.vdb": "vdb cache",
        "models/energy.fbx": "model data",
        "models/energy.abc": "alembic data",
        "media/plate_a.mov": "same duplicate payload",
        "media/plate_b.mov": "same duplicate payload",
        "audio/hit.wav": "audio data",
        "lut/show.cube": "lut data",
        "scripts/build.py": "print('ok')",
        "archives/fx_pack.part1.rar": "archive part one",
        "archives/fx_pack.part3.rar": "archive part three",
        "notes/readme.txt": "unknown doc",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "empty" / "placeholder").mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    unittest.main()
