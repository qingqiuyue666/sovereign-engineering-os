import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from kernel.personal_ai.task_graph_artifact_outputs import (
    task_graph_artifact_outputs_projection_sha256,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class TaskGraphArtifactOutputBindingTests(unittest.TestCase):
    def write_graph(self, graph_path, nodes, *, graph_id="artifact-binding-graph"):
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
        project_id="artifact-binding-test",
    ):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_scan",
            "execution_mode": "fixture",
            "depends_on": list(depends_on),
            "approval_checkpoint_required": True,
            "inputs": {
                "input_dir": Path(input_dir).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "recursive": True,
                "include_hidden": False,
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

    def run_successful_asset_scan_graph(self, root, *, graph_id="artifact-binding-graph"):
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
            graph_id=graph_id,
        )
        result = run_local_task_graph_fixture(graph_path, graph_output)
        return {
            "result": result,
            "graph_output": graph_output,
            "node_output": node_output,
            "execution_manifest": read_json(result.execution_manifest_path),
            "replay_manifest": read_json(result.replay_manifest_path),
            "artifact_outputs": read_json(result.artifact_outputs_manifest_path),
        }

    def artifact_roles(self, artifact_outputs, *, node_id=None):
        return {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if node_id is None or artifact["node_id"] == node_id
        }

    def artifact_by_role(self, artifact_outputs, role, *, node_id=None):
        matches = [
            artifact
            for artifact in artifact_outputs["artifacts"]
            if artifact["artifact_role"] == role
            and (node_id is None or artifact["node_id"] == node_id)
        ]
        self.assertEqual(len(matches), 1, role)
        return matches[0]

    def test_task_graph_writes_artifact_outputs_manifest_for_successful_asset_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run = self.run_successful_asset_scan_graph(Path(temp_dir))
            artifact_outputs_path = (
                run["graph_output"] / "task_graph_artifact_outputs.json"
            )
            artifact_outputs = run["artifact_outputs"]
            execution_manifest = run["execution_manifest"]
            replay_manifest = run["replay_manifest"]

            self.assertTrue(run["result"].success)
            self.assertTrue(artifact_outputs_path.exists())
            self.assertEqual(
                execution_manifest["task_graph_artifact_outputs_path"],
                artifact_outputs_path.as_posix(),
            )
            self.assertTrue(execution_manifest["task_graph_artifact_outputs_written"])
            self.assertEqual(
                execution_manifest["task_graph_artifact_count"],
                artifact_outputs["artifact_count"],
            )
            self.assertEqual(
                replay_manifest["task_graph_artifact_outputs_sha256"],
                task_graph_artifact_outputs_projection_sha256(artifact_outputs),
            )
            self.assertTrue(
                replay_manifest["task_graph_artifact_outputs_manifest_bound"]
            )
            roles = self.artifact_roles(artifact_outputs, node_id="scan_assets")
            for role in (
                "asset_scan_run_receipt",
                "artifact_index",
                "artifact_index_manifest",
                "local_asset_sqlite_index",
                "local_asset_sqlite_index_manifest",
                "local_asset_sqlite_query_summary",
                "asset_manifest",
                "asset_index",
                "duplicates_report",
                "media_inventory",
                "asset_runtime_audit_log",
                "asset_runtime_validation_report",
                "asset_runtime_quarantine_manifest",
            ):
                self.assertIn(role, roles)

    def test_task_graph_artifact_outputs_hashes_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_outputs = self.run_successful_asset_scan_graph(Path(temp_dir))[
                "artifact_outputs"
            ]

            for artifact in artifact_outputs["artifacts"]:
                if not artifact["exists"]:
                    continue
                artifact_path = Path(artifact["path"])
                self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(artifact["sha256"], sha256_file(artifact_path))
                self.assertEqual(artifact["size_bytes"], artifact_path.stat().st_size)
                self.assertFalse(artifact["content_indexed"])
                self.assertFalse(artifact["raw_content_copied"])

    def test_task_graph_artifact_outputs_include_graph_level_manifests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_outputs = self.run_successful_asset_scan_graph(Path(temp_dir))[
                "artifact_outputs"
            ]

            roles = self.artifact_roles(artifact_outputs, node_id="__task_graph__")
            self.assertIn("task_graph_execution_manifest", roles)
            self.assertIn("task_graph_replay_manifest", roles)
            execution_artifact = self.artifact_by_role(
                artifact_outputs,
                "task_graph_execution_manifest",
                node_id="__task_graph__",
            )
            replay_artifact = self.artifact_by_role(
                artifact_outputs,
                "task_graph_replay_manifest",
                node_id="__task_graph__",
            )
            self.assertTrue(execution_artifact["exists"])
            self.assertTrue(replay_artifact["exists"])
            self.assertEqual(
                execution_artifact["relative_path"],
                "task_graph_execution_manifest.json",
            )
            self.assertEqual(
                replay_artifact["relative_path"],
                "task_graph_replay_manifest.json",
            )

    def test_task_graph_artifact_outputs_for_failed_asset_scan_node(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing_input = root / "missing-input"
            node_output = root / "failed-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.asset_scan_node(
                        node_id="scan_missing",
                        input_dir=missing_input,
                        output_dir=node_output,
                    )
                ],
                graph_id="failed-artifact-binding-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)

            self.assertFalse(result.success)
            self.assertTrue((graph_output / "task_graph_artifact_outputs.json").exists())
            roles = self.artifact_roles(artifact_outputs)
            self.assertIn("asset_scan_failure_bundle", roles)
            self.assertIn("asset_scan_failure_summary", roles)
            self.assertIn("task_graph_failure_bundle", roles)
            for artifact_ref in artifact_outputs["failed_node_artifacts"]:
                self.assertTrue(artifact_ref["exists"], artifact_ref["artifact_role"])
                self.assertRegex(artifact_ref["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(artifact_ref["size_bytes"], 0)

    def test_task_graph_artifact_outputs_fail_closed_on_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.make_input_dir(root)
            node_output = root / "node-output"
            graph_output = root / "graph-output"
            node_output.mkdir()
            graph_output.mkdir()
            existing_manifest = graph_output / "task_graph_artifact_outputs.json"
            existing_manifest.write_text("do not overwrite\n", encoding="utf-8")
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
                graph_id="preexisting-artifact-output-graph",
            )

            with self.assertRaisesRegex(ValueError, "already exists"):
                run_local_task_graph_fixture(graph_path, graph_output)

            self.assertEqual(
                existing_manifest.read_text(encoding="utf-8"),
                "do not overwrite\n",
            )
            self.assertFalse((node_output / "asset_scan_run_receipt.json").exists())

    def test_task_graph_artifact_outputs_deterministic_across_runs(self):
        with (
            tempfile.TemporaryDirectory() as first_dir,
            tempfile.TemporaryDirectory() as second_dir,
        ):
            first = self.run_successful_asset_scan_graph(
                Path(first_dir),
                graph_id="deterministic-artifact-binding-graph",
            )["artifact_outputs"]
            second = self.run_successful_asset_scan_graph(
                Path(second_dir),
                graph_id="deterministic-artifact-binding-graph",
            )["artifact_outputs"]

            stable_first = [
                (
                    artifact["node_id"],
                    artifact["adapter_id"],
                    artifact["capability"],
                    artifact["artifact_role"],
                    artifact["artifact_type"],
                    artifact["exists"],
                    artifact["content_indexed"],
                    artifact["raw_content_copied"],
                )
                for artifact in first["artifacts"]
            ]
            stable_second = [
                (
                    artifact["node_id"],
                    artifact["adapter_id"],
                    artifact["capability"],
                    artifact["artifact_role"],
                    artifact["artifact_type"],
                    artifact["exists"],
                    artifact["content_indexed"],
                    artifact["raw_content_copied"],
                )
                for artifact in second["artifacts"]
            ]
            self.assertEqual(first["artifact_count"], second["artifact_count"])
            self.assertEqual(first["node_artifact_counts"], second["node_artifact_counts"])
            self.assertEqual(stable_first, stable_second)
            for role in (
                "asset_manifest",
                "asset_index",
                "duplicates_report",
                "media_inventory",
                "asset_runtime_audit_log",
                "asset_runtime_validation_report",
                "asset_runtime_quarantine_manifest",
            ):
                self.assertEqual(
                    self.artifact_by_role(first, role, node_id="scan_assets")["sha256"],
                    self.artifact_by_role(second, role, node_id="scan_assets")[
                        "sha256"
                    ],
                    role,
                )

    def test_task_graph_artifact_outputs_no_scope_expansion_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run = self.run_successful_asset_scan_graph(Path(temp_dir))
            artifact_outputs = run["artifact_outputs"]
            execution_manifest = run["execution_manifest"]

            for field in (
                "input_mutation_performed",
                "file_move_performed",
                "file_rename_performed",
                "file_delete_performed",
                "media_organizer_behavior_performed",
                "output_overwrite_performed",
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
            ):
                self.assertFalse(artifact_outputs[field], field)
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
            for artifact in artifact_outputs["artifacts"]:
                self.assertFalse(artifact["content_indexed"])
                self.assertFalse(artifact["raw_content_copied"])

    def test_task_graph_artifact_outputs_dependency_skip(self):
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
                graph_id="dependency-skip-artifact-binding-graph",
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)

            self.assertFalse(result.success)
            self.assertIn(
                {
                    "node_id": "dependent_scan",
                    "blocked_dependencies": ["scan_missing"],
                    "status": "skipped",
                },
                artifact_outputs["skipped_nodes"],
            )
            self.assertEqual(
                [
                    artifact
                    for artifact in artifact_outputs["artifacts"]
                    if artifact["node_id"] == "dependent_scan"
                ],
                [],
            )


if __name__ == "__main__":
    unittest.main()
