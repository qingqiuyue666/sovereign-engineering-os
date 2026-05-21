import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.personal_ai.local_mvp_cli import main


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class AssetScanOperationalControlTests(unittest.TestCase):
    def run_cli(self, input_dir, output_dir, *extra_args):
        stdout = io.StringIO()
        args = [
            "launch-local-asset-scan",
            "--input-dir",
            Path(input_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            *extra_args,
        ]
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

    def test_success_writes_run_receipt_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "asset_scan_run_receipt.json").exists())
            self.assertTrue((output_dir / "artifact_index.json").exists())
            artifact_index = read_json(output_dir / "artifact_index.json")
            artifact_names = {
                entry["artifact_name"] for entry in artifact_index["entries"]
            }
            self.assertIn("asset_scan_run_receipt", artifact_names)
            self.assertIn("local_asset_index", artifact_names)
            self.assertIn("local_asset_sqlite_index_manifest", artifact_names)
            self.assertIn("local_asset_sqlite_query_summary", artifact_names)
            self.assertEqual(artifact_index["indexed_artifacts"], 12)
            self.assertEqual(
                payload["asset_scan_run_receipt_path"],
                (output_dir / "asset_scan_run_receipt.json").as_posix(),
            )
            self.assertTrue(payload["operational_control_receipt_written"])
            self.assertFalse(payload["failure_bundle_written"])

    def test_success_receipt_records_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 0)
            receipt = read_json(payload["asset_scan_run_receipt_path"])
            for field in (
                "input_mutation_performed",
                "file_move_performed",
                "file_rename_performed",
                "file_delete_performed",
                "media_organizer_behavior_performed",
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
            ):
                self.assertFalse(receipt[field], field)

    def test_missing_input_dir_writes_failure_bundle_when_output_dir_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "missing-input"
            output_dir = root / "output"
            output_dir.mkdir()

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "asset_scan_failure_bundle.json").exists())
            self.assertTrue((output_dir / "asset_scan_failure_summary.md").exists())
            self.assertEqual(payload["failure_stage"], "preflight_input_dir_missing")
            bundle = read_json(output_dir / "asset_scan_failure_bundle.json")
            self.assertEqual(bundle["failure_stage"], "preflight_input_dir_missing")
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)
            self.assertFalse((output_dir / "artifact_index.json").exists())

    def test_missing_output_dir_returns_structured_failure_without_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "missing-output"

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertIsNone(payload["failure_bundle_path"])
            self.assertEqual(payload["failure_stage"], "preflight_output_dir_missing")
            self.assertFalse(payload["safe_to_retry"])
            self.assertTrue(payload["required_human_approval"])
            self.assertFalse(output_dir.exists())

    def test_existing_launcher_summary_fails_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()
            source = input_dir / "plate.png"
            before_bytes = source.read_bytes()
            (output_dir / "launcher_summary.md").write_text(
                "existing summary\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["failure_stage"],
                "preflight_launcher_output_collision",
            )
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)
            self.assertEqual(source.read_bytes(), before_bytes)

    def test_existing_artifact_index_fails_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()
            source = input_dir / "notes.txt"
            before_text = source.read_text(encoding="utf-8")
            (output_dir / "artifact_index.json").write_text(
                "existing index\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["failure_stage"],
                "preflight_artifact_index_collision",
            )
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)
            self.assertEqual(source.read_text(encoding="utf-8"), before_text)

    def test_existing_success_receipt_fails_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()
            (output_dir / "asset_scan_run_receipt.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["failure_stage"],
                "preflight_launcher_output_collision",
            )
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((output_dir / filename).exists(), filename)

    def test_soft_quarantine_is_success_with_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "plate.png").write_bytes(b"plate")
            (input_dir / "api_key.txt").write_text(
                "TOKEN=not-read\n",
                encoding="utf-8",
            )

            exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 0)
            receipt = read_json(payload["asset_scan_run_receipt_path"])
            self.assertEqual(receipt["status"], "completed")
            self.assertTrue(receipt["scan_completed_with_quarantine"])
            self.assertGreater(receipt["quarantined_paths"], 0)
            self.assertEqual(
                receipt["recommended_next_action"],
                "human_review_quarantine_manifest",
            )

    def test_failure_bundle_does_not_capture_raw_secret_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()

            with mock.patch(
                "kernel.personal_ai.local_launcher.run_local_asset_runtime",
                side_effect=ValueError(
                    "boom TOKEN=super-secret PASSWORD=hunter API_KEY=abc "
                    "Traceback (most recent call last) line 99 raw-secret"
                ),
            ):
                exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            bundle_text = (
                output_dir / "asset_scan_failure_bundle.json"
            ).read_text(encoding="utf-8")
            summary_text = (
                output_dir / "asset_scan_failure_summary.md"
            ).read_text(encoding="utf-8")
            for raw_value in (
                "super-secret",
                "hunter",
                "API_KEY=abc",
                "Traceback (most recent call last)",
                "line 99 raw-secret",
            ):
                self.assertNotIn(raw_value, bundle_text)
                self.assertNotIn(raw_value, summary_text)
                self.assertNotIn(raw_value, payload["error_message"])
            bundle = read_json(output_dir / "asset_scan_failure_bundle.json")
            self.assertFalse(bundle["raw_traceback_persisted"])

    def test_operational_control_deterministic_success_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            first_output = root / "first-output"
            second_output = root / "second-output"
            first_output.mkdir()
            second_output.mkdir()

            first_code, first_payload = self.run_cli(input_dir, first_output)
            second_code, second_payload = self.run_cli(input_dir, second_output)

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            first_receipt = read_json(first_payload["asset_scan_run_receipt_path"])
            second_receipt = read_json(second_payload["asset_scan_run_receipt_path"])
            stable_receipt_fields = (
                "receipt_type",
                "workflow",
                "status",
                "project_id",
                "recursive",
                "include_hidden",
                "files_scanned",
                "bytes_scanned",
                "duplicate_groups",
                "quarantined_paths",
                "scan_completed_with_quarantine",
                "safe_to_retry",
                "replay_hint",
                "input_mutation_performed",
                "file_move_performed",
                "file_rename_performed",
                "file_delete_performed",
                "media_organizer_behavior_performed",
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
                "required_human_approval",
                "next_allowed_action",
                "recommended_next_action",
            )
            for field in stable_receipt_fields:
                self.assertEqual(first_receipt[field], second_receipt[field], field)

            first_hashes = dict(first_payload["artifact_hashes"])
            second_hashes = dict(second_payload["artifact_hashes"])
            first_hashes.pop("asset_scan_run_receipt")
            second_hashes.pop("asset_scan_run_receipt")
            for unstable_artifact in (
                "local_asset_index",
                "local_asset_sqlite_index_manifest",
                "local_asset_sqlite_query_summary",
            ):
                first_hashes.pop(unstable_artifact)
                second_hashes.pop(unstable_artifact)
            self.assertEqual(first_hashes, second_hashes)


if __name__ == "__main__":
    unittest.main()
