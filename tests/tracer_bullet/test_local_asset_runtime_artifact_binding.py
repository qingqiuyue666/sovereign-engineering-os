import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.local_mvp_cli import main


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalAssetRuntimeArtifactBindingTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_fixture(self, root):
        input_dir = root / "input"
        input_dir.mkdir()
        (input_dir / "plate.png").write_bytes(b"plate")
        (input_dir / "plate-copy.jpg").write_bytes(b"plate")
        (input_dir / "notes.txt").write_text("review notes\n", encoding="utf-8")
        return input_dir

    def run_asset_scan(self, input_dir, output_dir):
        output_dir.mkdir()
        return self.run_cli(
            [
                "launch-local-asset-scan",
                "--input-dir",
                input_dir.as_posix(),
                "--output-dir",
                output_dir.as_posix(),
                "--project-id",
                "artifact-binding-fixture",
            ]
        )

    def test_launch_local_asset_scan_writes_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"

            exit_code, payload = self.run_asset_scan(input_dir, output_dir)

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "artifact_index.json").exists())
            self.assertTrue((output_dir / "artifact_index_manifest.json").exists())
            self.assertEqual(
                payload["artifact_index_path"],
                (output_dir / "artifact_index.json").as_posix(),
            )
            self.assertEqual(
                payload["artifact_index_manifest_path"],
                (output_dir / "artifact_index_manifest.json").as_posix(),
            )
            self.assertTrue(payload["artifact_ledger_binding_performed"])
            self.assertEqual(
                payload["artifact_ledger_binding_type"],
                "existing_artifact_index",
            )
            self.assertFalse(payload["artifact_index_content_indexed"])
            self.assertEqual(
                payload["artifact_index_runtime_authority"],
                "non_authority",
            )

            artifact_index = read_json(payload["artifact_index_path"])
            artifact_names = {
                entry["artifact_name"] for entry in artifact_index["entries"]
            }
            self.assertEqual(payload["indexed_artifacts"], 9)
            self.assertEqual(artifact_index["indexed_artifacts"], 9)
            self.assertTrue(
                {
                    "asset_manifest",
                    "asset_index",
                    "duplicates_report",
                    "media_inventory",
                    "asset_runtime_audit_log",
                    "asset_runtime_validation_report",
                    "asset_runtime_quarantine_manifest",
                    "launcher_summary",
                    "asset_scan_run_receipt",
                }.issubset(artifact_names)
            )
            self.assertTrue(
                artifact_names.issubset(set(payload["artifact_hashes"]))
            )

    def test_artifact_index_hashes_asset_scan_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            first_output = root / "first-output"
            second_output = root / "second-output"

            first_code, first_payload = self.run_asset_scan(input_dir, first_output)
            second_code, second_payload = self.run_asset_scan(input_dir, second_output)

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            first_index = read_json(first_payload["artifact_index_path"])
            first_manifest = read_json(
                first_payload["artifact_index_manifest_path"]
            )
            second_manifest = read_json(
                second_payload["artifact_index_manifest_path"]
            )
            for entry in first_index["entries"]:
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(
                    entry["sha256"],
                    sha256_file(first_output / entry["relative_path"]),
                )
            self.assertRegex(
                first_manifest["artifact_index_sha256"],
                r"^[0-9a-f]{64}$",
            )
            self.assertEqual(
                first_manifest["artifact_index_sha256"],
                sha256_file(first_output / "artifact_index.json"),
            )
            first_payload_hashes = dict(first_payload["artifact_hashes"])
            second_payload_hashes = dict(second_payload["artifact_hashes"])
            first_manifest_hashes = dict(first_manifest["artifact_hashes"])
            second_manifest_hashes = dict(second_manifest["artifact_hashes"])
            first_payload_hashes.pop("asset_scan_run_receipt")
            second_payload_hashes.pop("asset_scan_run_receipt")
            first_manifest_hashes.pop("asset_scan_run_receipt")
            second_manifest_hashes.pop("asset_scan_run_receipt")
            self.assertEqual(first_payload_hashes, second_payload_hashes)
            self.assertEqual(first_manifest_hashes, second_manifest_hashes)

    def test_existing_artifact_index_fails_closed_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()
            source = input_dir / "plate.png"
            before_bytes = source.read_bytes()
            (output_dir / "artifact_index.json").write_text(
                "existing index\n",
                encoding="utf-8",
            )

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
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)
            self.assertFalse((output_dir / "launcher_summary.md").exists())
            self.assertFalse((output_dir / "artifact_index_manifest.json").exists())
            self.assertEqual(source.read_bytes(), before_bytes)

    def test_existing_artifact_index_manifest_fails_closed_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()
            source = input_dir / "notes.txt"
            before_text = source.read_text(encoding="utf-8")
            (output_dir / "artifact_index_manifest.json").write_text(
                "existing manifest\n",
                encoding="utf-8",
            )

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
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)
            self.assertFalse((output_dir / "launcher_summary.md").exists())
            self.assertFalse((output_dir / "artifact_index.json").exists())
            self.assertEqual(source.read_text(encoding="utf-8"), before_text)

    def test_no_scope_expansion_boundaries_remain_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"

            exit_code, payload = self.run_asset_scan(input_dir, output_dir)

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["read_only_input"])
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


if __name__ == "__main__":
    unittest.main()
