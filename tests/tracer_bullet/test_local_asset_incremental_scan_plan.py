import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kernel.assets.local_asset_incremental_plan import (
    LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE,
    LOCAL_ASSET_INCREMENTAL_OUTPUT_FILENAMES,
    LOCAL_ASSET_INCREMENTAL_PLAN_FILE,
    LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE,
)
from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalAssetIncrementalScanPlanTests(unittest.TestCase):
    def run_cli(self, input_dir, output_dir, *extra_args):
        stdout = io.StringIO()
        args = [
            "launch-local-asset-scan",
            "--input-dir",
            Path(input_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--project-id",
            "incremental-fixture",
            *extra_args,
        ]
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_input(self, root, files):
        input_dir = Path(root)
        input_dir.mkdir(parents=True, exist_ok=True)
        for relative_path, content in files.items():
            path = input_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return input_dir

    def run_scan(self, root, name, files, *extra_args):
        input_dir = self.make_input(root / (name + "-input"), files)
        output_dir = root / (name + "-output")
        output_dir.mkdir()
        exit_code, payload = self.run_cli(input_dir, output_dir, *extra_args)
        self.assertEqual(exit_code, 0, payload)
        return input_dir, output_dir, payload

    def write_graph(self, graph_path, input_dir, output_dir, previous_output_dir):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "incremental-asset-scan-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "scan_assets",
                        "adapter_id": "local_asset_runtime",
                        "capability": "launch_local_asset_scan",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "input_dir": Path(input_dir).as_posix(),
                            "output_dir": Path(output_dir).as_posix(),
                            "previous_scan_output_dir": Path(
                                previous_output_dir
                            ).as_posix(),
                            "recursive": False,
                            "include_hidden": False,
                            "project_id": "incremental-fixture",
                        },
                    }
                ],
            },
        )

    def test_baseline_scan_writes_incremental_plan_without_previous_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _input_dir, output_dir, payload = self.run_scan(
                root,
                "baseline",
                {
                    "plate.png": b"plate",
                    "notes.txt": b"notes",
                },
            )

            plan = read_json(output_dir / LOCAL_ASSET_INCREMENTAL_PLAN_FILE)

            self.assertTrue((output_dir / LOCAL_ASSET_INCREMENTAL_PLAN_FILE).exists())
            self.assertTrue(
                (output_dir / LOCAL_ASSET_INCREMENTAL_MANIFEST_FILE).exists()
            )
            self.assertTrue((output_dir / LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE).exists())
            self.assertEqual(payload["local_asset_incremental_plan_mode"], "baseline_no_previous_scan")
            self.assertEqual(plan["plan_mode"], "baseline_no_previous_scan")
            self.assertEqual(plan["new_asset_count"], plan["current_asset_count"])
            self.assertEqual(plan["missing_assets"], [])
            self.assertEqual(plan["unchanged_assets"], [])
            self.assertEqual(plan["changed_assets"], [])
            self.assertFalse(plan["automatic_skip_performed"])
            self.assertFalse(plan["cache_execution_performed"])

    def test_compare_previous_scan_classifies_unchanged_changed_new_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _prev_input, previous_output, _prev_payload = self.run_scan(
                root,
                "previous",
                {
                    "keep.png": b"same",
                    "change.txt": b"old",
                    "missing.mov": b"missing",
                },
            )
            _current_input, current_output, payload = self.run_scan(
                root,
                "current",
                {
                    "keep.png": b"same",
                    "change.txt": b"new",
                    "new.wav": b"brand-new",
                },
                "--previous-scan-output-dir",
                previous_output.as_posix(),
            )

            plan = read_json(payload["local_asset_incremental_scan_plan_path"])

            self.assertEqual(plan["plan_mode"], "compare_previous_scan")
            self.assertEqual(plan["unchanged_asset_count"], 1)
            self.assertEqual(plan["changed_asset_count"], 1)
            self.assertEqual(plan["new_asset_count"], 1)
            self.assertEqual(plan["missing_asset_count"], 1)
            self.assertEqual(
                [asset["relative_path"] for asset in plan["unchanged_assets"]],
                ["keep.png"],
            )
            self.assertEqual(
                [asset["relative_path"] for asset in plan["changed_assets"]],
                ["change.txt"],
            )
            self.assertEqual(
                [asset["relative_path"] for asset in plan["new_assets"]],
                ["new.wav"],
            )
            self.assertEqual(
                [asset["relative_path"] for asset in plan["missing_assets"]],
                ["missing.mov"],
            )

    def test_incremental_plan_detects_duplicate_state_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _prev_input, previous_output, _prev_payload = self.run_scan(
                root,
                "previous",
                {"plate.png": b"plate"},
            )
            _current_input, current_output, payload = self.run_scan(
                root,
                "current",
                {
                    "plate.png": b"plate",
                    "plate-copy.jpg": b"plate",
                },
                "--previous-scan-output-dir",
                previous_output.as_posix(),
            )

            plan = read_json(payload["local_asset_incremental_scan_plan_path"])
            changes = plan["duplicate_state_changes"]

            self.assertGreater(plan["duplicate_state_changed_count"], 0)
            self.assertEqual([change["relative_path"] for change in changes], ["plate.png"])
            self.assertIn(
                "duplicate_membership_changed",
                changes[0]["change_reasons"],
            )
            self.assertEqual(
                changes[0]["current"]["duplicate_group_paths"],
                ["plate-copy.jpg", "plate.png"],
            )

    def test_incremental_plan_detects_quarantine_state_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _prev_input, previous_output, _prev_payload = self.run_scan(
                root,
                "previous",
                {"plate.png": b"plate"},
            )
            _current_input, current_output, payload = self.run_scan(
                root,
                "current",
                {
                    "plate.png": b"plate",
                    "api_key.txt": b"TOKEN=not-read",
                },
                "--previous-scan-output-dir",
                previous_output.as_posix(),
            )

            plan = read_json(payload["local_asset_incremental_scan_plan_path"])
            changes = plan["quarantine_state_changes"]

            self.assertGreater(plan["quarantine_state_changed_count"], 0)
            self.assertEqual([change["relative_path"] for change in changes], ["api_key.txt"])
            self.assertEqual(changes[0]["current"]["reasons"], ["secret_looking_path"])

    def test_incremental_manifest_hashes_plan_and_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _prev_input, previous_output, _prev_payload = self.run_scan(
                root,
                "previous",
                {"plate.png": b"plate"},
            )
            _current_input, current_output, payload = self.run_scan(
                root,
                "current",
                {"plate.png": b"plate", "notes.txt": b"notes"},
                "--previous-scan-output-dir",
                previous_output.as_posix(),
            )

            manifest = read_json(payload["local_asset_incremental_scan_manifest_path"])

            self.assertEqual(
                manifest["plan_sha256"],
                sha256_file(current_output / LOCAL_ASSET_INCREMENTAL_PLAN_FILE),
            )
            self.assertEqual(
                manifest["summary_sha256"],
                sha256_file(current_output / LOCAL_ASSET_INCREMENTAL_SUMMARY_FILE),
            )
            for artifact in manifest["current_source_artifacts"]:
                if artifact["exists"]:
                    self.assertEqual(
                        artifact["sha256"],
                        sha256_file(current_output / artifact["relative_path"]),
                    )
            for artifact in manifest["previous_source_artifacts"]:
                if artifact["exists"]:
                    self.assertEqual(
                        artifact["sha256"],
                        sha256_file(previous_output / artifact["relative_path"]),
                    )

    def test_incremental_outputs_are_in_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _input_dir, output_dir, payload = self.run_scan(
                root,
                "current",
                {"plate.png": b"plate"},
            )

            artifact_index = read_json(payload["artifact_index_path"])
            artifact_names = {
                entry["artifact_name"] for entry in artifact_index["entries"]
            }

            self.assertIn("local_asset_incremental_scan_plan", artifact_names)
            self.assertIn("local_asset_incremental_scan_manifest", artifact_names)
            self.assertIn("local_asset_incremental_scan_summary", artifact_names)

    def test_task_graph_artifact_outputs_include_incremental_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            previous_input, previous_output, _prev_payload = self.run_scan(
                root,
                "previous",
                {"plate.png": b"plate"},
            )
            current_input = self.make_input(root / "current-input", {"plate.png": b"plate"})
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(graph_path, current_input, node_output, previous_output)

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            execution_manifest = read_json(result.execution_manifest_path)
            node = execution_manifest["nodes"][0]
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "scan_assets"
            }

            self.assertTrue(result.success)
            self.assertEqual(node["local_asset_incremental_plan_mode"], "compare_previous_scan")
            self.assertFalse(node["incremental_cache_execution_performed"])
            self.assertFalse(node["incremental_automatic_skip_performed"])
            self.assertIn("local_asset_incremental_scan_plan", roles)
            self.assertIn("local_asset_incremental_scan_manifest", roles)
            self.assertIn("local_asset_incremental_scan_summary", roles)
            self.assertTrue(previous_input.exists())

    def test_existing_incremental_output_files_fail_closed_before_runtime(self):
        for file_name in LOCAL_ASSET_INCREMENTAL_OUTPUT_FILENAMES:
            with self.subTest(file_name=file_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    input_dir = self.make_input(root / "input", {"plate.png": b"plate"})
                    output_dir = root / "output"
                    output_dir.mkdir()
                    source = input_dir / "plate.png"
                    before_bytes = source.read_bytes()
                    (output_dir / file_name).write_text(
                        "preexisting\n",
                        encoding="utf-8",
                    )

                    exit_code, payload = self.run_cli(input_dir, output_dir)

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["failure_stage"],
                        "preflight_incremental_output_collision",
                    )
                    for runtime_file in OUTPUT_FILENAMES:
                        self.assertFalse((output_dir / runtime_file).exists())
                    self.assertFalse((output_dir / "launcher_summary.md").exists())
                    self.assertFalse((output_dir / "asset_scan_run_receipt.json").exists())
                    self.assertEqual(source.read_bytes(), before_bytes)

    def test_incremental_plan_failure_writes_failure_bundle_without_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input(root / "input", {"plate.png": b"plate"})
            output_dir = root / "output"
            output_dir.mkdir()

            with mock.patch(
                "kernel.personal_ai.local_launcher.build_local_asset_incremental_plan",
                side_effect=ValueError("synthetic incremental failure"),
            ):
                exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["failure_stage"], "incremental_plan_failure")
            self.assertTrue((output_dir / "asset_scan_failure_bundle.json").exists())
            self.assertFalse((output_dir / "artifact_index.json").exists())
            for file_name in OUTPUT_FILENAMES:
                self.assertIn(file_name, payload["partial_outputs_written"])
            for file_name in (
                "launcher_summary.md",
                "asset_scan_run_receipt.json",
                "local_asset_index.sqlite",
                "local_asset_sqlite_index_manifest.json",
                "local_asset_sqlite_query_summary.md",
            ):
                self.assertIn(file_name, payload["partial_outputs_written"])

    def test_previous_scan_output_dir_validation(self):
        cases = (
            ("missing", lambda root, output: root / "missing-previous"),
            (
                "symlink",
                self._previous_scan_symlink_case,
            ),
            ("equal_output_dir", lambda root, output: output),
            (
                "output_inside_previous",
                self._output_inside_previous_case,
            ),
            (
                "previous_inside_output",
                self._previous_inside_output_case,
            ),
        )
        for case_name, previous_factory in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    input_dir = self.make_input(root / "input", {"plate.png": b"plate"})
                    output_dir = root / "output"
                    output_dir.mkdir()
                    source = input_dir / "plate.png"
                    before_bytes = source.read_bytes()
                    previous_dir = previous_factory(root, output_dir)

                    exit_code, payload = self.run_cli(
                        input_dir,
                        output_dir,
                        "--previous-scan-output-dir",
                        Path(previous_dir).as_posix(),
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertIn(
                        payload["failure_stage"],
                        {
                            "preflight_previous_scan_missing",
                            "preflight_previous_scan_invalid",
                        },
                    )
                    for runtime_file in OUTPUT_FILENAMES:
                        self.assertFalse((output_dir / runtime_file).exists())
                    self.assertEqual(source.read_bytes(), before_bytes)

    def _previous_scan_symlink_case(self, root, output_dir):
        target = root / "previous-target"
        target.mkdir()
        symlink = root / "previous-link"
        symlink.symlink_to(target, target_is_directory=True)
        return symlink

    def _output_inside_previous_case(self, root, output_dir):
        return root

    def _previous_inside_output_case(self, root, output_dir):
        previous = output_dir / "previous"
        previous.mkdir()
        return previous

    def test_incremental_plan_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _input_dir, output_dir, payload = self.run_scan(
                root,
                "current",
                {"plate.png": b"plate"},
            )
            plan = read_json(payload["local_asset_incremental_scan_plan_path"])
            manifest = read_json(payload["local_asset_incremental_scan_manifest_path"])

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
                self.assertFalse(plan[field], field)
                self.assertFalse(manifest[field], field)
                self.assertFalse(payload[field], field)
            for field in (
                "cache_execution_performed",
                "automatic_skip_performed",
                "raw_content_copied",
                "content_indexed",
            ):
                self.assertFalse(plan[field], field)
                self.assertFalse(manifest[field], field)
                self.assertFalse(payload[field], field)
            self.assertFalse(payload["incremental_cache_execution_performed"])
            self.assertFalse(payload["incremental_automatic_skip_performed"])

    def test_incremental_plan_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_previous = root / "first-previous"
            second_previous = root / "second-previous"
            first_current = root / "first-current"
            second_current = root / "second-current"
            for directory in (
                first_previous,
                second_previous,
                first_current,
                second_current,
            ):
                directory.mkdir()

            _first_prev_input, first_previous_output, _payload = self.run_scan(
                first_previous,
                "scan",
                {
                    "same.png": b"same",
                    "change.txt": b"old",
                    "missing.mov": b"missing",
                },
            )
            _second_prev_input, second_previous_output, _payload = self.run_scan(
                second_previous,
                "scan",
                {
                    "same.png": b"same",
                    "change.txt": b"old",
                    "missing.mov": b"missing",
                },
            )
            _first_current_input, _first_current_output, first_payload = self.run_scan(
                first_current,
                "scan",
                {
                    "same.png": b"same",
                    "change.txt": b"new",
                    "new.wav": b"new",
                },
                "--previous-scan-output-dir",
                first_previous_output.as_posix(),
            )
            _second_current_input, _second_current_output, second_payload = self.run_scan(
                second_current,
                "scan",
                {
                    "same.png": b"same",
                    "change.txt": b"new",
                    "new.wav": b"new",
                },
                "--previous-scan-output-dir",
                second_previous_output.as_posix(),
            )

            first_plan = read_json(first_payload["local_asset_incremental_scan_plan_path"])
            second_plan = read_json(
                second_payload["local_asset_incremental_scan_plan_path"]
            )

            self.assertEqual(
                self._stable_plan_projection(first_plan),
                self._stable_plan_projection(second_plan),
            )

    def _stable_plan_projection(self, plan):
        fields = (
            "plan_type",
            "authority",
            "execution_capability",
            "plan_mode",
            "project_id",
            "recursive",
            "include_hidden",
            "current_asset_count",
            "previous_asset_count",
            "unchanged_asset_count",
            "changed_asset_count",
            "new_asset_count",
            "missing_asset_count",
            "duplicate_state_changed_count",
            "quarantine_state_changed_count",
            "suspicious_change_count",
            "safe_to_use_as_plan",
            "cache_execution_performed",
            "automatic_skip_performed",
        )
        return {
            field: plan[field] for field in fields
        } | {
            "unchanged_assets": self._stable_assets(plan["unchanged_assets"]),
            "new_assets": self._stable_assets(plan["new_assets"]),
            "missing_assets": self._stable_assets(plan["missing_assets"]),
            "changed_assets": [
                {
                    "relative_path": record["relative_path"],
                    "previous": self._stable_asset(record["previous"]),
                    "current": self._stable_asset(record["current"]),
                    "change_reasons": record["change_reasons"],
                }
                for record in plan["changed_assets"]
            ],
            "duplicate_state_changes": plan["duplicate_state_changes"],
            "quarantine_state_changes": plan["quarantine_state_changes"],
            "suspicious_changes": plan["suspicious_changes"],
        }

    def _stable_assets(self, assets):
        return [self._stable_asset(asset) for asset in assets]

    def _stable_asset(self, asset):
        return {
            "relative_path": asset["relative_path"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
            "asset_type": asset["asset_type"],
            "extension": asset["extension"],
        }


if __name__ == "__main__":
    unittest.main()
