import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class TaskGraphTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        runtime_dir = root / "runtime"
        package_root = root / "packages"
        graph_output = root / "graph-output"
        runtime_dir.mkdir()
        package_root.mkdir()
        graph_output.mkdir()
        write_json_atomically(
            runtime_dir / "model_inference_artifact.json",
            {
                "artifact_type": "personal_ai_model_inference_artifact_v1",
                "authority": "non_authority",
                "execution_capability": "mock_runtime_only",
                "classification": "fixture",
            },
        )
        delivery = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="task-graph-delivery",
        )
        graph_path = root / "task_graph.json"
        write_json_atomically(
            graph_path,
            self.safe_graph(
                package_dir=delivery.package_dir,
                validation_output_path=graph_output
                / "graph_runtime_delivery_validation.json",
            ),
        )
        return root, graph_path, graph_output, delivery

    def safe_graph(self, *, package_dir, validation_output_path):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "fixture-graph",
            "authority": "non_authority",
            "required_human_approval": True,
            "nodes": [
                {
                    "node_id": "model_contract",
                    "adapter_id": "mock_model_typed_schema_runtime",
                    "capability": "classify_local_job_package",
                    "depends_on": [],
                    "approval_checkpoint_required": True,
                    "inputs": {},
                },
                {
                    "node_id": "delivery_validation",
                    "adapter_id": "runtime_delivery_package",
                    "capability": "validate_runtime_delivery",
                    "depends_on": ["model_contract"],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "package_dir": Path(package_dir).as_posix(),
                        "output_path": Path(validation_output_path).as_posix(),
                    },
                },
            ],
        }

    def test_runs_local_graph_fixture_with_delivery_integration(self):
        _, graph_path, graph_output, delivery = self.build_workspace()

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        replay_manifest = read_json(result.replay_manifest_path)

        self.assertTrue(result.success)
        self.assertEqual(result.node_order, ("model_contract", "delivery_validation"))
        self.assertTrue(execution_manifest["delivery_package_integration"])
        self.assertFalse(execution_manifest["network_runtime_allowed"])
        self.assertFalse(execution_manifest["subprocess_runtime_allowed"])
        self.assertFalse(execution_manifest["creative_runtime_allowed"])
        self.assertEqual(
            execution_manifest["nodes"][1]["delivery_validation"][
                "runtime_delivery_manifest_path"
            ],
            delivery.runtime_delivery_manifest_path.as_posix(),
        )
        self.assertTrue(replay_manifest["replay_requires_same_graph_sha256"])

    def test_cli_runs_local_graph_fixture(self):
        _, graph_path, graph_output, _ = self.build_workspace()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "run-task-graph-fixture",
                    "--graph-path",
                    graph_path.as_posix(),
                    "--output-dir",
                    graph_output.as_posix(),
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertEqual(payload["node_order"], ["model_contract", "delivery_validation"])
        self.assertTrue(Path(payload["task_graph_execution_manifest_path"]).exists())

    def test_unknown_adapter_is_quarantined_without_execution_manifest(self):
        root, graph_path, graph_output, _ = self.build_workspace()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "bad-graph",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "bad",
                        "adapter_id": "unregistered_runtime",
                        "capability": "execute",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    }
                ],
            },
        )
        self.assertEqual(root, graph_path.parent)

        result = run_local_task_graph_fixture(graph_path, graph_output)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIsNone(result.execution_manifest_path)
        self.assertIn("adapter route is not registered", failure["error_message"])
        self.assertTrue(failure["failure_quarantine_required"])

    def test_rejects_cycles_and_missing_approval_checkpoints(self):
        _, graph_path, graph_output, _ = self.build_workspace()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "cycle",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "a",
                        "adapter_id": "mock_model_typed_schema_runtime",
                        "capability": "classify_local_job_package",
                        "depends_on": ["b"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "b",
                        "adapter_id": "mock_model_typed_schema_runtime",
                        "capability": "classify_local_job_package",
                        "depends_on": ["a"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("cycle", failure["error_message"])


if __name__ == "__main__":
    unittest.main()
