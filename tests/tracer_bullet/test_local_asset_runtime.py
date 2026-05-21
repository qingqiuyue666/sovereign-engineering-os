import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_runtime import (
    LocalAssetRuntimeResult,
    run_local_asset_runtime,
)
from kernel.assets.local_asset_schema import OUTPUT_FILENAMES


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line
    ]


class LocalAssetRuntimeTests(unittest.TestCase):
    def test_normal_scan_fixture_generates_all_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            nested = input_dir / "shots"
            nested.mkdir(parents=True)
            output_dir.mkdir()
            source = input_dir / "plate.mp4"
            source.write_bytes(b"video-bytes")
            (input_dir / "still.png").write_bytes(b"image-bytes")
            (input_dir / "scene.blend").write_bytes(b"dcc-bytes")
            (input_dir / "look.cube").write_text("LUT_3D_SIZE 2\n", encoding="utf-8")
            (nested / "sim.vdb").write_bytes(b"cache-bytes")
            (input_dir / "workflow.json").write_text(
                json.dumps(
                    {
                        "1": {
                            "class_type": "CheckpointLoaderSimple",
                            "inputs": {"ckpt_name": "model.safetensors"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            before_bytes = source.read_bytes()

            result = run_local_asset_runtime(
                input_dir,
                output_dir,
                recursive=True,
                project_id="demo_project",
            )

            self.assertIsInstance(result, LocalAssetRuntimeResult)
            self.assertEqual(result.files_scanned, 6)
            self.assertEqual(source.read_bytes(), before_bytes)
            for filename in OUTPUT_FILENAMES:
                self.assertTrue((output_dir / filename).exists(), filename)
            manifest = read_json(output_dir / "asset_manifest.json")
            assets_by_path = {
                asset["relative_path"]: asset for asset in manifest["assets"]
            }
            self.assertEqual(assets_by_path["plate.mp4"]["asset_type"], "video")
            self.assertEqual(assets_by_path["still.png"]["asset_type"], "image")
            self.assertEqual(assets_by_path["scene.blend"]["asset_type"], "dcc")
            self.assertEqual(assets_by_path["look.cube"]["asset_type"], "color/lookdev")
            self.assertEqual(assets_by_path["shots/sim.vdb"]["asset_type"], "fx/cache")
            self.assertEqual(
                assets_by_path["workflow.json"]["asset_type"],
                "comfyui_workflow",
            )
            self.assertFalse(manifest["boundaries"]["input_files_mutated"])
            self.assertFalse(manifest["boundaries"]["external_creative_runtime_invoked"])

    def test_empty_directory_emits_empty_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            result = run_local_asset_runtime(input_dir, output_dir)

            self.assertEqual(result.files_scanned, 0)
            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(manifest["assets"], [])
            self.assertIn(
                "| none | none | 0 | none |",
                (output_dir / "media_inventory.md").read_text(encoding="utf-8"),
            )

    def test_duplicate_files_reported_by_sha256(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "a.mov").write_bytes(b"same-content")
            (input_dir / "b.mkv").write_bytes(b"same-content")
            (input_dir / "c.wav").write_bytes(b"different")

            result = run_local_asset_runtime(input_dir, output_dir)

            self.assertEqual(result.duplicate_groups, 1)
            duplicates = read_json(output_dir / "duplicates_report.json")
            self.assertEqual(duplicates["duplicate_sha256_group_count"], 1)
            self.assertEqual(
                duplicates["duplicate_groups"][0]["relative_paths"],
                ["a.mov", "b.mkv"],
            )

    def test_unknown_extension_classified_unknown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "asset.weird").write_text("unknown", encoding="utf-8")

            run_local_asset_runtime(input_dir, output_dir)

            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(manifest["assets"][0]["asset_type"], "unknown")

    def test_hidden_files_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / ".hidden.png").write_bytes(b"hidden")
            (input_dir / "visible.png").write_bytes(b"visible")

            run_local_asset_runtime(input_dir, output_dir)

            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(
                [asset["relative_path"] for asset in manifest["assets"]],
                ["visible.png"],
            )
            validation = read_json(output_dir / "asset_runtime_validation_report.json")
            self.assertEqual(validation["counts"]["skipped_hidden_paths"], 1)

    def test_hidden_files_included_only_when_explicitly_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / ".hidden.png").write_bytes(b"hidden")

            run_local_asset_runtime(input_dir, output_dir, include_hidden=True)

            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(
                [asset["relative_path"] for asset in manifest["assets"]],
                [".hidden.png"],
            )
            validation = read_json(output_dir / "asset_runtime_validation_report.json")
            self.assertEqual(validation["counts"]["skipped_hidden_paths"], 0)

    def test_unsafe_dependency_directories_are_quarantined_and_not_scanned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            unsafe_dir = input_dir / "node_modules"
            unsafe_dir.mkdir(parents=True)
            output_dir.mkdir()
            (unsafe_dir / "library.js").write_text("module", encoding="utf-8")
            (input_dir / "safe.py").write_text("print('ok')\n", encoding="utf-8")

            result = run_local_asset_runtime(input_dir, output_dir, recursive=True)

            self.assertEqual(result.files_scanned, 1)
            quarantine = read_json(output_dir / "asset_runtime_quarantine_manifest.json")
            self.assertEqual(quarantine["quarantined_path_count"], 1)
            self.assertEqual(quarantine["items"][0]["relative_path"], "node_modules")
            self.assertEqual(quarantine["items"][0]["reason"], "unsafe_directory")
            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(manifest["assets"][0]["relative_path"], "safe.py")

    def test_symlinks_are_quarantined_without_following_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            outside_target = root / "outside.txt"
            input_dir.mkdir()
            output_dir.mkdir()
            outside_target.write_text("outside", encoding="utf-8")
            link = input_dir / "outside-link.txt"
            try:
                link.symlink_to(outside_target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            result = run_local_asset_runtime(input_dir, output_dir)

            self.assertEqual(result.files_scanned, 0)
            quarantine = read_json(output_dir / "asset_runtime_quarantine_manifest.json")
            self.assertEqual(quarantine["items"][0]["relative_path"], "outside-link.txt")
            self.assertEqual(quarantine["items"][0]["reason"], "dangerous_symlink")
            self.assertFalse(quarantine["items"][0]["target_inside_input"])

    def test_output_overwrite_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "asset.png").write_bytes(b"asset")
            existing = output_dir / "asset_manifest.json"
            existing.write_text("existing manifest\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                run_local_asset_runtime(input_dir, output_dir)

            self.assertEqual(existing.read_text(encoding="utf-8"), "existing manifest\n")
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                ["asset_manifest.json"],
            )

    def test_quarantine_manifest_generated_for_secret_looking_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "api_key.txt").write_text("super-secret", encoding="utf-8")
            (input_dir / "public.jpg").write_bytes(b"public")

            run_local_asset_runtime(input_dir, output_dir)

            quarantine = read_json(output_dir / "asset_runtime_quarantine_manifest.json")
            self.assertEqual(quarantine["quarantined_path_count"], 1)
            self.assertEqual(quarantine["items"][0]["relative_path"], "api_key.txt")
            self.assertEqual(quarantine["items"][0]["reason"], "secret_looking_path")
            manifest = read_json(output_dir / "asset_manifest.json")
            self.assertEqual(
                [asset["relative_path"] for asset in manifest["assets"]],
                ["public.jpg"],
            )

    def test_audit_log_generated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "asset.wav").write_bytes(b"asset")

            run_local_asset_runtime(input_dir, output_dir)

            events = read_jsonl(output_dir / "asset_runtime_audit_log.jsonl")
            self.assertEqual(events[0]["event_type"], "runtime_started")
            self.assertIn("asset_scanned", [event["event_type"] for event in events])
            self.assertEqual(events[-1]["event_type"], "runtime_completed")
            self.assertEqual(
                [event["event_id"] for event in events],
                [f"{index:06d}" for index in range(1, len(events) + 1)],
            )

    def test_deterministic_repeated_run_on_same_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            first_output = root / "first_output"
            second_output = root / "second_output"
            input_dir.mkdir()
            first_output.mkdir()
            second_output.mkdir()
            (input_dir / "b.jpg").write_bytes(b"b")
            (input_dir / "a.jpg").write_bytes(b"a")
            (input_dir / "copy-a.png").write_bytes(b"a")
            (input_dir / "notes.txt").write_text("notes", encoding="utf-8")

            run_local_asset_runtime(
                input_dir,
                first_output,
                recursive=True,
                project_id="stable",
            )
            run_local_asset_runtime(
                input_dir,
                second_output,
                recursive=True,
                project_id="stable",
            )

            for filename in OUTPUT_FILENAMES:
                self.assertEqual(
                    (first_output / filename).read_text(encoding="utf-8"),
                    (second_output / filename).read_text(encoding="utf-8"),
                    filename,
                )


if __name__ == "__main__":
    unittest.main()
