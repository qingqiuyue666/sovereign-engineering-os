import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote

from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.assets.local_asset_sqlite_index import (
    LOCAL_ASSET_SQLITE_INDEX_FILE,
    LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
    LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE,
    LOCAL_ASSET_SQLITE_SCHEMA_TABLES,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


SQLITE_OUTPUT_FILENAMES = (
    LOCAL_ASSET_SQLITE_INDEX_FILE,
    LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE,
    LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def connect_readonly(path):
    uri = "file:" + quote(Path(path).resolve(strict=True).as_posix()) + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


class LocalAssetSQLiteIndexTests(unittest.TestCase):
    def run_cli(self, input_dir, output_dir, *extra_args):
        stdout = io.StringIO()
        args = [
            "launch-local-asset-scan",
            "--input-dir",
            Path(input_dir).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--project-id",
            "sqlite-index-fixture",
            *extra_args,
        ]
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_fixture(self, root):
        input_dir = root / "input"
        input_dir.mkdir(parents=True)
        (input_dir / "clip.mov").write_bytes(b"clip-data")
        (input_dir / "plate.png").write_bytes(b"plate")
        (input_dir / "plate-copy.jpg").write_bytes(b"plate")
        (input_dir / "api_key.txt").write_text("TOKEN=not-read\n", encoding="utf-8")
        return input_dir

    def run_asset_scan(self, root, output_name="output"):
        input_dir = self.make_fixture(root)
        output_dir = root / output_name
        output_dir.mkdir()
        exit_code, payload = self.run_cli(input_dir, output_dir)
        self.assertEqual(exit_code, 0)
        return input_dir, output_dir, payload

    def write_graph(self, graph_path, input_dir, node_output):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "sqlite-index-graph",
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
                            "output_dir": Path(node_output).as_posix(),
                            "recursive": False,
                            "include_hidden": False,
                            "project_id": "sqlite-index-fixture",
                        },
                    }
                ],
            },
        )

    def test_launch_local_asset_scan_writes_sqlite_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, output_dir, payload = self.run_asset_scan(Path(temp_dir))

            self.assertTrue((output_dir / LOCAL_ASSET_SQLITE_INDEX_FILE).exists())
            self.assertTrue(
                (output_dir / LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE).exists()
            )
            self.assertTrue(
                (output_dir / LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE).exists()
            )
            self.assertEqual(
                payload["local_asset_sqlite_index_path"],
                (output_dir / LOCAL_ASSET_SQLITE_INDEX_FILE).as_posix(),
            )
            self.assertEqual(
                payload["local_asset_sqlite_index_manifest_path"],
                (output_dir / LOCAL_ASSET_SQLITE_INDEX_MANIFEST_FILE).as_posix(),
            )
            self.assertEqual(
                payload["local_asset_sqlite_query_summary_path"],
                (output_dir / LOCAL_ASSET_SQLITE_QUERY_SUMMARY_FILE).as_posix(),
            )
            self.assertTrue(payload["local_asset_sqlite_index_written"])

    def test_sqlite_index_has_expected_tables_and_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, output_dir, payload = self.run_asset_scan(Path(temp_dir))

            with contextlib.closing(
                connect_readonly(payload["local_asset_sqlite_index_path"])
            ) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertTrue(set(LOCAL_ASSET_SQLITE_SCHEMA_TABLES).issubset(tables))
                row_counts = {
                    table: connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                    for table in LOCAL_ASSET_SQLITE_SCHEMA_TABLES
                }
                metadata = dict(
                    connection.execute(
                        "SELECT key, value FROM index_metadata ORDER BY key"
                    ).fetchall()
                )

            self.assertEqual(row_counts["scan_runs"], 1)
            self.assertEqual(row_counts["assets"], 3)
            self.assertEqual(row_counts["duplicate_groups"], 1)
            self.assertEqual(row_counts["quarantine_events"], 1)
            self.assertEqual(row_counts["artifact_sources"], 7)
            self.assertEqual(
                metadata["schema_version"],
                "local_asset_sqlite_index_schema_v1",
            )
            self.assertRegex(metadata["scan_run_id"], r"^scan_run_[0-9a-f]{24}$")

    def test_sqlite_index_supports_core_queries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, output_dir, payload = self.run_asset_scan(Path(temp_dir))

            with contextlib.closing(
                connect_readonly(payload["local_asset_sqlite_index_path"])
            ) as connection:
                png_assets = connection.execute(
                    """
                    SELECT relative_path
                    FROM assets
                    WHERE extension = '.png'
                    ORDER BY relative_path
                    """
                ).fetchall()
                duplicate_groups = connection.execute(
                    """
                    SELECT asset_count, total_size_bytes
                    FROM duplicate_groups
                    ORDER BY duplicate_group_id
                    """
                ).fetchall()
                largest_assets = connection.execute(
                    """
                    SELECT relative_path, size_bytes
                    FROM assets
                    ORDER BY size_bytes DESC, relative_path
                    """
                ).fetchall()
                quarantine_events = connection.execute(
                    """
                    SELECT relative_path, reason
                    FROM quarantine_events
                    ORDER BY relative_path, reason
                    """
                ).fetchall()
                media_classes = connection.execute(
                    """
                    SELECT media_class, COUNT(*)
                    FROM assets
                    GROUP BY media_class
                    ORDER BY media_class
                    """
                ).fetchall()

            self.assertEqual(png_assets, [("plate.png",)])
            self.assertEqual(duplicate_groups, [(2, 10)])
            self.assertEqual(
                largest_assets,
                [("clip.mov", 9), ("plate-copy.jpg", 5), ("plate.png", 5)],
            )
            self.assertEqual(quarantine_events, [("api_key.txt", "secret_looking_path")])
            self.assertEqual(media_classes, [("image", 2), ("video", 1)])

    def test_sqlite_manifest_hashes_database_and_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, output_dir, payload = self.run_asset_scan(Path(temp_dir))

            manifest = read_json(payload["local_asset_sqlite_index_manifest_path"])
            self.assertEqual(
                manifest["database_sha256"],
                sha256_file(output_dir / LOCAL_ASSET_SQLITE_INDEX_FILE),
            )
            source_artifacts = {
                artifact["relative_path"]: artifact
                for artifact in manifest["source_artifacts"]
            }
            for relative_path, artifact in source_artifacts.items():
                self.assertEqual(
                    artifact["sha256"],
                    sha256_file(output_dir / relative_path),
                    relative_path,
                )
            self.assertFalse(manifest["content_indexed"])
            self.assertFalse(manifest["raw_content_copied"])

    def test_sqlite_outputs_are_in_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, output_dir, payload = self.run_asset_scan(Path(temp_dir))

            artifact_index = read_json(payload["artifact_index_path"])
            artifact_names = {
                entry["artifact_name"] for entry in artifact_index["entries"]
            }
            self.assertIn("local_asset_index", artifact_names)
            self.assertIn("local_asset_sqlite_index_manifest", artifact_names)
            self.assertIn("local_asset_sqlite_query_summary", artifact_names)
            self.assertIn("local_asset_incremental_scan_plan", artifact_names)
            self.assertIn("local_asset_incremental_scan_manifest", artifact_names)
            self.assertIn("local_asset_incremental_scan_summary", artifact_names)

    def test_task_graph_artifact_outputs_include_sqlite_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(graph_path, input_dir, node_output)

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "scan_assets"
            }

            self.assertTrue(result.success)
            self.assertIn("local_asset_sqlite_index", roles)
            self.assertIn("local_asset_sqlite_index_manifest", roles)
            self.assertIn("local_asset_sqlite_query_summary", roles)
            self.assertIn("local_asset_incremental_scan_plan", roles)
            self.assertIn("local_asset_incremental_scan_manifest", roles)
            self.assertIn("local_asset_incremental_scan_summary", roles)

    def test_existing_sqlite_index_files_fail_closed_before_runtime(self):
        for file_name in SQLITE_OUTPUT_FILENAMES:
            with self.subTest(file_name=file_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    input_dir = self.make_fixture(root)
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
                        "preflight_sqlite_index_collision",
                    )
                    for runtime_file in OUTPUT_FILENAMES:
                        self.assertFalse((output_dir / runtime_file).exists())
                    self.assertFalse((output_dir / "launcher_summary.md").exists())
                    self.assertFalse((output_dir / "asset_scan_run_receipt.json").exists())
                    self.assertEqual(source.read_bytes(), before_bytes)

    def test_sqlite_index_failure_writes_failure_bundle_without_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_fixture(root)
            output_dir = root / "output"
            output_dir.mkdir()

            with mock.patch(
                "kernel.personal_ai.local_launcher.build_local_asset_sqlite_index",
                side_effect=ValueError("synthetic sqlite failure"),
            ):
                exit_code, payload = self.run_cli(input_dir, output_dir)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["failure_stage"], "sqlite_index_failure")
            self.assertTrue((output_dir / "asset_scan_failure_bundle.json").exists())
            self.assertFalse((output_dir / "artifact_index.json").exists())
            for file_name in OUTPUT_FILENAMES:
                self.assertIn(file_name, payload["partial_outputs_written"])
            self.assertIn("launcher_summary.md", payload["partial_outputs_written"])
            self.assertIn(
                "asset_scan_run_receipt.json",
                payload["partial_outputs_written"],
            )

    def test_sqlite_index_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _input_dir, _output_dir, payload = self.run_asset_scan(Path(temp_dir))
            manifest = read_json(payload["local_asset_sqlite_index_manifest_path"])

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
                self.assertFalse(payload[field], field)
                self.assertFalse(manifest[field], field)
            self.assertFalse(payload["local_asset_sqlite_content_indexed"])
            self.assertFalse(payload["local_asset_sqlite_raw_content_copied"])
            self.assertFalse(manifest["content_indexed"])
            self.assertFalse(manifest["raw_content_copied"])

    def test_sqlite_index_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_input = self.make_fixture(root / "first")
            second_input = self.make_fixture(root / "second")
            first_output = root / "first-output"
            second_output = root / "second-output"
            first_output.mkdir()
            second_output.mkdir()

            first_code, first_payload = self.run_cli(first_input, first_output)
            second_code, second_payload = self.run_cli(second_input, second_output)

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            first_manifest = read_json(
                first_payload["local_asset_sqlite_index_manifest_path"]
            )
            second_manifest = read_json(
                second_payload["local_asset_sqlite_index_manifest_path"]
            )
            self.assertEqual(first_manifest["schema_tables"], second_manifest["schema_tables"])
            self.assertEqual(first_manifest["row_counts"], second_manifest["row_counts"])
            first_source_hashes = {
                artifact["artifact_role"]: artifact["sha256"]
                for artifact in first_manifest["source_artifacts"]
            }
            second_source_hashes = {
                artifact["artifact_role"]: artifact["sha256"]
                for artifact in second_manifest["source_artifacts"]
            }
            self.assertEqual(first_source_hashes, second_source_hashes)

            with (
                contextlib.closing(
                    connect_readonly(first_payload["local_asset_sqlite_index_path"])
                ) as first,
                contextlib.closing(
                    connect_readonly(second_payload["local_asset_sqlite_index_path"])
                ) as second,
            ):
                stable_query = """
                    SELECT relative_path, extension, media_class, size_bytes, sha256,
                           is_duplicate
                    FROM assets
                    ORDER BY relative_path
                """
                self.assertEqual(
                    first.execute(stable_query).fetchall(),
                    second.execute(stable_query).fetchall(),
                )
                self.assertEqual(
                    first.execute(
                        """
                        SELECT sha256, asset_count, total_size_bytes
                        FROM duplicate_groups
                        ORDER BY sha256
                        """
                    ).fetchall(),
                    second.execute(
                        """
                        SELECT sha256, asset_count, total_size_bytes
                        FROM duplicate_groups
                        ORDER BY sha256
                        """
                    ).fetchall(),
                )


if __name__ == "__main__":
    unittest.main()
