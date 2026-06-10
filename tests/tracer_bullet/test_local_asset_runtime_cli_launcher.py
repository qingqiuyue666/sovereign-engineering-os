import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.product_health_check import build_product_health_report


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalAssetRuntimeCLILauncherTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def test_launch_local_asset_scan_generates_reports_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            nested_dir = input_dir / "nested"
            nested_dir.mkdir(parents=True)
            output_dir.mkdir()
            source = input_dir / "plate.png"
            source.write_bytes(b"visible-image")
            (nested_dir / "clip.mov").write_bytes(b"nested-video")
            before_bytes = source.read_bytes()

            exit_code, payload = self.run_cli(
                [
                    "launch-local-asset-scan",
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--recursive",
                    "--project-id",
                    "demo-project",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(payload["workflow"], "local_asset_scan_workflow")
            self.assertEqual(source.read_bytes(), before_bytes)
            for filename in OUTPUT_FILENAMES:
                self.assertTrue((output_dir / filename).exists(), filename)
            self.assertTrue((output_dir / "launcher_summary.md").exists())
            self.assertTrue(
                (output_dir / "local_asset_incremental_scan_plan.json").exists()
            )
            self.assertTrue(
                (output_dir / "local_asset_incremental_scan_manifest.json").exists()
            )
            self.assertTrue(
                (output_dir / "local_asset_incremental_scan_summary.md").exists()
            )
            self.assertEqual(
                payload["local_asset_incremental_plan_mode"],
                "baseline_no_previous_scan",
            )
            self.assertFalse(payload["incremental_cache_execution_performed"])
            self.assertFalse(payload["incremental_automatic_skip_performed"])

            manifest = read_json(payload["asset_manifest_path"])
            validation = read_json(payload["asset_runtime_validation_report_path"])
            relative_paths = [
                asset["relative_path"] for asset in manifest["assets"]
            ]
            self.assertEqual(relative_paths, ["nested/clip.mov", "plate.png"])
            self.assertEqual(manifest["project_id"], "demo-project")
            self.assertEqual(validation["project_id"], "demo-project")
            self.assertFalse(manifest["boundaries"]["input_files_mutated"])
            self.assertFalse(manifest["boundaries"]["network_access_performed"])
            self.assertFalse(manifest["boundaries"]["model_api_called"])
            self.assertFalse(manifest["boundaries"]["desktop_ui_added"])
            self.assertFalse(
                manifest["boundaries"]["external_creative_runtime_invoked"]
            )
            self.assertFalse(validation["boundaries"]["browser_runtime_invoked"])
            for field in (
                "input_mutation_performed",
                "file_move_performed",
                "file_rename_performed",
                "file_delete_performed",
                "media_organizer_behavior_performed",
                "output_overwrite_performed",
                "network_access_performed",
                "model_api_called",
                "desktop_ui_added",
                "browser_runtime_invoked",
                "comfyui_runtime_invoked",
                "blender_runtime_invoked",
                "houdini_runtime_invoked",
                "after_effects_runtime_invoked",
                "davinci_runtime_invoked",
                "external_runtime_invoked",
            ):
                self.assertFalse(payload[field], field)

    def test_launch_local_asset_scan_overwrite_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "asset.png").write_bytes(b"asset")
            existing_manifest = output_dir / "asset_manifest.json"
            existing_manifest.write_text("existing manifest\n", encoding="utf-8")

            exit_code, payload = self.run_cli(
                [
                    "launch-local-asset-scan",
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertEqual(payload["failure_stage"], "runtime_output_collision")
            self.assertIn("already exists", payload["error_message"])
            self.assertTrue((output_dir / "asset_scan_failure_bundle.json").exists())
            self.assertTrue((output_dir / "asset_scan_failure_summary.md").exists())
            self.assertEqual(
                existing_manifest.read_text(encoding="utf-8"),
                "existing manifest\n",
            )
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                [
                    "asset_manifest.json",
                    "asset_scan_failure_bundle.json",
                    "asset_scan_failure_summary.md",
                ],
            )

    def test_hidden_and_recursive_flags_match_runtime_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            nested_dir = input_dir / "nested"
            default_output = root / "default-output"
            hidden_output = root / "hidden-output"
            recursive_output = root / "recursive-output"
            nested_dir.mkdir(parents=True)
            for output_dir in (default_output, hidden_output, recursive_output):
                output_dir.mkdir()
            (input_dir / "visible.png").write_bytes(b"visible")
            (input_dir / ".hidden.png").write_bytes(b"hidden")
            (nested_dir / "nested.png").write_bytes(b"nested")

            default_code, default_payload = self.run_cli(
                [
                    "launch-local-asset-scan",
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-dir",
                    default_output.as_posix(),
                ]
            )
            hidden_code, hidden_payload = self.run_cli(
                [
                    "launch-local-asset-scan",
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-dir",
                    hidden_output.as_posix(),
                    "--include-hidden",
                ]
            )
            recursive_code, recursive_payload = self.run_cli(
                [
                    "launch-local-asset-scan",
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-dir",
                    recursive_output.as_posix(),
                    "--recursive",
                ]
            )

            self.assertEqual(default_code, 0)
            self.assertEqual(hidden_code, 0)
            self.assertEqual(recursive_code, 0)
            default_manifest = read_json(default_payload["asset_manifest_path"])
            hidden_manifest = read_json(hidden_payload["asset_manifest_path"])
            recursive_manifest = read_json(recursive_payload["asset_manifest_path"])
            default_validation = read_json(
                default_payload["asset_runtime_validation_report_path"]
            )
            self.assertEqual(
                [asset["relative_path"] for asset in default_manifest["assets"]],
                ["visible.png"],
            )
            self.assertEqual(default_validation["counts"]["skipped_hidden_paths"], 1)
            self.assertEqual(
                default_validation["counts"]["skipped_nonrecursive_dirs"],
                1,
            )
            self.assertFalse(default_payload["include_hidden"])
            self.assertFalse(default_payload["recursive"])
            self.assertEqual(
                [asset["relative_path"] for asset in hidden_manifest["assets"]],
                [".hidden.png", "visible.png"],
            )
            self.assertTrue(hidden_payload["include_hidden"])
            self.assertEqual(
                [asset["relative_path"] for asset in recursive_manifest["assets"]],
                ["nested/nested.png", "visible.png"],
            )
            self.assertTrue(recursive_payload["recursive"])

    def test_product_health_recognizes_local_asset_scan_surface(self):
        report = build_product_health_report(Path.cwd())
        static_checks = report["launcher_static_checks"]

        self.assertIn("local_asset_scan_workflow", report["launcher_workflows"])
        self.assertIn(
            "launch-local-asset-scan",
            report["required_cli_subcommands"],
        )
        self.assertTrue(
            static_checks["launcher_workflows_declared"][
                "local_asset_scan_workflow"
            ]
        )
        self.assertTrue(
            static_checks["required_cli_subcommands_declared"][
                "launch-local-asset-scan"
            ]
        )
        self.assertTrue(report["does_not_execute_launcher_workflows"])
        self.assertFalse(report["runtime_activation_performed"])


if __name__ == "__main__":
    unittest.main()
