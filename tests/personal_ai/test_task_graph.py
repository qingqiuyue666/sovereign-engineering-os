import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_runtime_boundary import (
    write_blender_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.browser_runtime_boundary import (
    write_browser_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    write_comfyui_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_provider_boundary import (
    write_model_provider_admission_artifacts,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    write_runtime_admission_decision,
)
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

    def write_runtime_decision(
        self,
        output_dir,
        artifacts,
        *,
        adapter_id,
        capability,
        runtime_class,
        decision_name,
        dry_run=True,
    ):
        decision_path = Path(output_dir) / decision_name
        write_runtime_admission_decision(
            RuntimeAdmissionRequest(
                adapter_id=adapter_id,
                capability=capability,
                runtime_class=runtime_class,
                config_artifact_path=artifacts.config_path,
                human_approval_artifact_path=artifacts.human_approval_path,
                manifest_artifact_path=artifacts.manifest_path,
                dry_run=dry_run,
                activation_sources=("human_approval_artifact", "task_graph"),
            ),
            decision_path,
        )
        return decision_path

    def test_runs_local_graph_fixture_with_delivery_integration(self):
        _, graph_path, graph_output, delivery = self.build_workspace()

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        replay_manifest = read_json(result.replay_manifest_path)

        self.assertTrue(result.success)
        self.assertEqual(result.node_order, ("model_contract", "delivery_validation"))
        self.assertEqual(execution_manifest["graph_execution_mode"], "fixture_execution")
        self.assertFalse(execution_manifest["runtime_activation_performed"])
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
        self.assertEqual(replay_manifest["graph_execution_mode"], "fixture_execution")

    def test_full_dry_run_product_graph_records_admission_references(self):
        root, graph_path, graph_output, delivery = self.build_workspace()
        admissions_dir = root / "runtime-admissions"
        admissions_dir.mkdir()

        model_dir = admissions_dir / "model"
        browser_dir = admissions_dir / "browser"
        comfyui_dir = admissions_dir / "comfyui"
        blender_dir = admissions_dir / "blender"
        for path in (model_dir, browser_dir, comfyui_dir, blender_dir):
            path.mkdir()
        model_artifacts = write_model_provider_admission_artifacts(
            model_dir,
            provider_id="openai",
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        browser_artifacts = write_browser_runtime_admission_artifacts(browser_dir)
        comfyui_artifacts = write_comfyui_runtime_admission_artifacts(comfyui_dir)
        blender_artifacts = write_blender_runtime_admission_artifacts(blender_dir)
        model_decision = self.write_runtime_decision(
            model_dir,
            model_artifacts,
            adapter_id="live_model_provider_boundary",
            capability="call_typed_schema_provider",
            runtime_class="live_model_provider",
            decision_name="model_runtime_decision.json",
        )
        browser_decision = self.write_runtime_decision(
            browser_dir,
            browser_artifacts,
            adapter_id="real_browser_runtime_boundary",
            capability="drive_real_browser_with_allowlist",
            runtime_class="external_browser",
            decision_name="browser_runtime_decision.json",
        )
        comfyui_decision = self.write_runtime_decision(
            comfyui_dir,
            comfyui_artifacts,
            adapter_id="comfyui_local_endpoint_boundary",
            capability="submit_comfyui_workflow_to_loopback_endpoint",
            runtime_class="comfyui_endpoint",
            decision_name="comfyui_runtime_decision.json",
        )
        blender_decision = self.write_runtime_decision(
            blender_dir,
            blender_artifacts,
            adapter_id="blender_real_runtime_boundary",
            capability="execute_blender_operation_plan",
            runtime_class="blender_runtime",
            decision_name="blender_runtime_decision.json",
        )
        dry_run_validation_path = graph_output / "dry_run_delivery_validation.json"
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "full-product-dry-run",
                "execution_mode": "dry_run_plan",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "office_intake",
                        "adapter_id": "xlsx_readonly_runtime",
                        "capability": "inspect_local_xlsx_metadata",
                        "runtime_class": "readonly",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "model_provider",
                        "adapter_id": "live_model_provider_boundary",
                        "capability": "call_typed_schema_provider",
                        "runtime_class": "live_model_provider",
                        "execution_mode": "dry_run",
                        "runtime_admission_decision_path": model_decision.as_posix(),
                        "depends_on": ["office_intake"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "browser_runtime",
                        "adapter_id": "real_browser_runtime_boundary",
                        "capability": "drive_real_browser_with_allowlist",
                        "runtime_class": "external_browser",
                        "execution_mode": "dry_run",
                        "runtime_admission_decision_path": browser_decision.as_posix(),
                        "depends_on": ["model_provider"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "comfyui_endpoint",
                        "adapter_id": "comfyui_local_endpoint_boundary",
                        "capability": "submit_comfyui_workflow_to_loopback_endpoint",
                        "runtime_class": "comfyui_endpoint",
                        "execution_mode": "dry_run",
                        "runtime_admission_decision_path": comfyui_decision.as_posix(),
                        "depends_on": ["browser_runtime"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "blender_runtime",
                        "adapter_id": "blender_real_runtime_boundary",
                        "capability": "execute_blender_operation_plan",
                        "runtime_class": "blender_runtime",
                        "execution_mode": "dry_run",
                        "runtime_admission_decision_path": blender_decision.as_posix(),
                        "depends_on": ["comfyui_endpoint"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "creative_handoff",
                        "adapter_id": "creative_handoff_package",
                        "capability": "build_handoff_package",
                        "runtime_class": "approved_output_write",
                        "execution_mode": "fixture",
                        "depends_on": ["blender_runtime"],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "delivery_validation",
                        "adapter_id": "runtime_delivery_package",
                        "capability": "validate_runtime_delivery",
                        "execution_mode": "dry_run",
                        "depends_on": ["creative_handoff"],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "package_dir": delivery.package_dir.as_posix(),
                            "output_path": dry_run_validation_path.as_posix(),
                        },
                    },
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        replay_manifest = read_json(result.replay_manifest_path)

        self.assertTrue(result.success)
        self.assertEqual(execution_manifest["graph_execution_mode"], "dry_run_plan")
        self.assertTrue(execution_manifest["dry_run_planning_mode"])
        self.assertFalse(execution_manifest["runtime_activation_performed"])
        self.assertFalse(execution_manifest["real_runtime_activation_allowed"])
        self.assertEqual(len(execution_manifest["runtime_admission_decisions"]), 4)
        self.assertFalse(dry_run_validation_path.exists())
        self.assertTrue(execution_manifest["delivery_package_integration"])
        self.assertEqual(
            {node["status"] for node in execution_manifest["nodes"]},
            {"planned"},
        )
        self.assertEqual(
            execution_manifest["nodes"][1]["adapter_route_policy"],
            "runtime_admission_dry_run_plan",
        )
        self.assertFalse(
            execution_manifest[
                "task_graph_can_activate_real_runtime_without_admission"
            ]
        )
        self.assertEqual(replay_manifest["graph_execution_mode"], "dry_run_plan")
        self.assertIn(
            "runtime_admission_decisions_sha256",
            replay_manifest,
        )

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

    def test_denies_real_runtime_activation_without_activation_admission(self):
        root, graph_path, graph_output, _ = self.build_workspace()
        admission_dir = root / "runtime-admission"
        admission_dir.mkdir()
        artifacts = write_model_provider_admission_artifacts(
            admission_dir,
            provider_id="openai",
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        dry_run_decision = self.write_runtime_decision(
            admission_dir,
            artifacts,
            adapter_id="live_model_provider_boundary",
            capability="call_typed_schema_provider",
            runtime_class="live_model_provider",
            decision_name="dry_run_runtime_decision.json",
        )
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "unsafe-real-runtime",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "real_model",
                        "adapter_id": "live_model_provider_boundary",
                        "capability": "call_typed_schema_provider",
                        "runtime_class": "live_model_provider",
                        "execution_mode": "real_runtime",
                        "runtime_admission_decision_path": dry_run_decision.as_posix(),
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    }
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("real runtime activation is not admitted", failure["error_message"])

    def test_requires_runtime_admission_reference_for_real_runtime_class(self):
        _, graph_path, graph_output, _ = self.build_workspace()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "missing-runtime-admission",
                "execution_mode": "dry_run_plan",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "model_provider",
                        "adapter_id": "live_model_provider_boundary",
                        "capability": "call_typed_schema_provider",
                        "runtime_class": "live_model_provider",
                        "execution_mode": "dry_run",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    }
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        failure = read_json(result.failure_bundle_path)

        self.assertFalse(result.success)
        self.assertIn("runtime admission decision is required", failure["error_message"])

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
