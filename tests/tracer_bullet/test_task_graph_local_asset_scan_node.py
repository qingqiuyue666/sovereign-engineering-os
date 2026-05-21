import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_schema import OUTPUT_FILENAMES
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class TaskGraphLocalAssetScanNodeTests(unittest.TestCase):
    def write_graph(self, graph_path, nodes, *, graph_id="asset-scan-graph"):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": graph_id,
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def asset_scan_node(
        self,
        *,
        node_id,
        input_dir,
        output_dir,
        depends_on=(),
        approval_checkpoint_required=True,
        recursive=True,
        include_hidden=False,
        project_id="asset-test",
    ):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_scan",
            "execution_mode": "fixture",
            "depends_on": list(depends_on),
            "approval_checkpoint_required": approval_checkpoint_required,
            "inputs": {
                "input_dir": Path(input_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "recursive": recursive,
                "include_hidden": include_hidden,
                "project_id": project_id,
            },
        }

    def make_input_dir(self, root, name="input"):
        input_dir = root / name
        nested_dir = input_dir / "nested"
        nested_dir.mkdir(parents=True)
        (input_dir / "plate.png").write_bytes(b"plate")
        (nested_dir / "clip.mov").write_bytes(b"clip")
        return input_dir

    def node_record(self, execution_manifest, node_id):
        for node in execution_manifest["nodes"]:
            if node["node_id"] == node_id:
                return node
        self.fail("node not found: " + node_id)

    def test_task_graph_executes_local_asset_scan_node_successfully(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=node_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            replay_manifest = read_json(result.replay_manifest_path)
            node = self.node_record(execution_manifest, "scan_assets")

            self.assertTrue(result.success)
            self.assertTrue((graph_output / "task_graph_execution_manifest.json").exists())
            self.assertTrue((graph_output / "task_graph_replay_manifest.json").exists())
            self.assertTrue((node_output / "asset_scan_run_receipt.json").exists())
            self.assertTrue((node_output / "artifact_index.json").exists())
            self.assertTrue((node_output / "local_asset_index.sqlite").exists())
            self.assertTrue(
                (node_output / "local_asset_sqlite_index_manifest.json").exists()
            )
            self.assertTrue(
                (node_output / "local_asset_sqlite_query_summary.md").exists()
            )
            self.assertEqual(node["status"], "completed")
            self.assertTrue(node["local_asset_scan_complete"])
            self.assertEqual(
                node["asset_scan_run_receipt_path"],
                (node_output / "asset_scan_run_receipt.json").as_posix(),
            )
            self.assertEqual(
                node["artifact_index_path"],
                (node_output / "artifact_index.json").as_posix(),
            )
            self.assertEqual(
                node["local_asset_sqlite_index_path"],
                (node_output / "local_asset_index.sqlite").as_posix(),
            )
            self.assertEqual(
                node["local_asset_sqlite_index_manifest_path"],
                (node_output / "local_asset_sqlite_index_manifest.json").as_posix(),
            )
            self.assertEqual(
                node["local_asset_sqlite_query_summary_path"],
                (node_output / "local_asset_sqlite_query_summary.md").as_posix(),
            )
            self.assertGreater(node["indexed_artifacts"], 0)
            for field in (
                "runtime_activation_performed",
                "real_runtime_activation_allowed",
                "task_graph_can_activate_real_runtime_without_admission",
                "input_mutation_performed",
                "overwrite_performed",
                "network_runtime_allowed",
                "subprocess_runtime_allowed",
                "browser_runtime_allowed",
                "model_api_runtime_allowed",
                "creative_runtime_allowed",
            ):
                self.assertFalse(execution_manifest[field], field)
            self.assertIn("node_output_refs_sha256", replay_manifest)
            self.assertIn("local_asset_scan_receipts_sha256", replay_manifest)

    def test_task_graph_local_asset_scan_node_failure_propagates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing_input = root / "missing-input"
            failed_output = root / "failed-output"
            dependent_input = self.make_input_dir(root, "dependent-input")
            dependent_output = root / "dependent-output"
            graph_output = root / "graph-output"
            failed_output.mkdir()
            dependent_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_missing",
                        input_dir=missing_input,
                        output_dir=failed_output,
                    ),
                    self.asset_scan_node(
                        node_id="dependent_scan",
                        input_dir=dependent_input,
                        output_dir=dependent_output,
                        depends_on=("scan_missing",),
                    ),
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            graph_failure = read_json(result.failure_bundle_path)
            failed_node = self.node_record(execution_manifest, "scan_missing")
            skipped_node = self.node_record(execution_manifest, "dependent_scan")

            self.assertFalse(result.success)
            self.assertTrue((graph_output / "task_graph_failure_bundle.json").exists())
            self.assertTrue((failed_output / "asset_scan_failure_bundle.json").exists())
            self.assertEqual(graph_failure["failed_node_id"], "scan_missing")
            self.assertEqual(
                graph_failure["failure_stage"],
                "preflight_input_dir_missing",
            )
            self.assertEqual(failed_node["status"], "failed")
            self.assertEqual(failed_node["failure_stage"], "preflight_input_dir_missing")
            self.assertEqual(skipped_node["status"], "skipped")
            self.assertEqual(skipped_node["blocked_dependencies"], ["scan_missing"])
            self.assertFalse((dependent_output / "asset_scan_run_receipt.json").exists())

    def test_task_graph_respects_dependency_order_for_asset_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=node_output,
                        depends_on=("prepare_dependency",),
                    ),
                    {
                        "node_id": "prepare_dependency",
                        "adapter_id": "mock_model_typed_schema_runtime",
                        "capability": "classify_local_job_package",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                ],
                graph_id="dependency-order-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)

            self.assertTrue(result.success)
            self.assertEqual(
                result.node_order,
                ("prepare_dependency", "scan_assets"),
            )
            self.assertEqual(
                execution_manifest["node_order"],
                ["prepare_dependency", "scan_assets"],
            )

    def test_task_graph_local_asset_scan_soft_quarantine_remains_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "node-output"
            graph_output = root / "graph-output"
            input_dir.mkdir()
            output_dir.mkdir()
            graph_output.mkdir()
            (input_dir / "plate.png").write_bytes(b"plate")
            (input_dir / "api_key.txt").write_text("TOKEN=not-read\n", encoding="utf-8")
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=output_dir,
                        recursive=False,
                    )
                ],
                graph_id="quarantine-success-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            node = self.node_record(execution_manifest, "scan_assets")
            receipt = read_json(output_dir / "asset_scan_run_receipt.json")

            self.assertTrue(result.success)
            self.assertEqual(node["status"], "completed")
            self.assertTrue(receipt["scan_completed_with_quarantine"])
            self.assertGreater(receipt["quarantined_paths"], 0)
            self.assertEqual(
                receipt["recommended_next_action"],
                "human_review_quarantine_manifest",
            )

    def test_task_graph_rejects_local_asset_scan_node_without_approval_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=node_output,
                        approval_checkpoint_required=False,
                    )
                ],
                graph_id="approval-required-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            failure = read_json(result.failure_bundle_path)

            self.assertFalse(result.success)
            self.assertIsNone(result.execution_manifest_path)
            self.assertIn("must require approval checkpoint", failure["error_message"])
            self.assertFalse((node_output / "asset_scan_run_receipt.json").exists())

    def test_task_graph_local_asset_scan_no_scope_expansion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=node_output,
                    )
                ],
                graph_id="scope-boundary-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            node = self.node_record(execution_manifest, "scan_assets")

            self.assertTrue(result.success)
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
                self.assertFalse(node[field], field)
            for field in (
                "runtime_activation_performed",
                "real_runtime_activation_allowed",
                "task_graph_can_activate_real_runtime_without_admission",
                "input_mutation_performed",
                "overwrite_performed",
                "network_runtime_allowed",
                "subprocess_runtime_allowed",
                "browser_runtime_allowed",
                "model_api_runtime_allowed",
                "creative_runtime_allowed",
            ):
                self.assertFalse(execution_manifest[field], field)

    def test_task_graph_local_asset_scan_output_collision_fails_before_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            (node_output / "asset_scan_run_receipt.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_assets",
                        input_dir=input_dir,
                        output_dir=node_output,
                    )
                ],
                graph_id="collision-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            execution_manifest = read_json(result.execution_manifest_path)
            graph_failure = read_json(result.failure_bundle_path)
            node = self.node_record(execution_manifest, "scan_assets")

            self.assertFalse(result.success)
            self.assertEqual(node["status"], "failed")
            self.assertEqual(
                node["failure_stage"],
                "preflight_launcher_output_collision",
            )
            self.assertEqual(
                graph_failure["failure_stage"],
                "preflight_launcher_output_collision",
            )
            for filename in OUTPUT_FILENAMES:
                self.assertFalse((node_output / filename).exists(), filename)
            self.assertFalse((node_output / "artifact_index.json").exists())
            self.assertTrue((node_output / "asset_scan_failure_bundle.json").exists())


if __name__ == "__main__":
    unittest.main()
