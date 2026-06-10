import ast
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.local_fixture_runner_contract_draft import (
    LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_REVIEW_ATTESTATION,
)
from kernel.capabilities.local_fixture_runner_receipt_contract_draft import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION,
)
from kernel.capabilities.local_fixture_runner_receipt_metadata_artifact import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS,
)
from kernel.capabilities.local_fixture_runner_receipt_preflight_verifier import (
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
)
from kernel.capabilities.local_fixture_runner_stub_admission_gate import (
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS,
    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
)
from kernel.personal_ai.adapters.adapter_registry import DEFAULT_ADAPTER_REGISTRY
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import _SUBCOMMANDS, main
from kernel.personal_ai.product_health_check import build_product_health_report
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]

TARGETS = {
    "local_fixture_runner_contract_draft": (
        "launch_local_fixture_runner_contract_draft",
        "launch-local-fixture-runner-contract-draft",
        "local_fixture_runner_contract_draft_workflow",
    ),
    "local_fixture_runner_stub_admission_gate": (
        "launch_local_fixture_runner_stub_admission_gate",
        "launch-local-fixture-runner-stub-admission-gate",
        "local_fixture_runner_stub_admission_gate_workflow",
    ),
    "local_fixture_runner_receipt_contract_draft": (
        "launch_local_fixture_runner_receipt_contract_draft",
        "launch-local-fixture-runner-receipt-contract-draft",
        "local_fixture_runner_receipt_contract_draft_workflow",
    ),
    "local_fixture_runner_receipt_preflight_verifier": (
        "launch_local_fixture_runner_receipt_preflight_verifier",
        "launch-local-fixture-runner-receipt-preflight-verifier",
        "local_fixture_runner_receipt_preflight_verifier_workflow",
    ),
    "local_fixture_runner_receipt_metadata_artifact": (
        "launch_local_fixture_runner_receipt_metadata_artifact",
        "launch-local-fixture-runner-receipt-metadata-artifact",
        "local_fixture_runner_receipt_metadata_artifact_workflow",
    ),
}

TARGET_MODULE_PATHS = (
    REPO_ROOT / "kernel" / "capabilities" / "local_fixture_runner_contract_draft.py",
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_stub_admission_gate.py",
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_contract_draft.py",
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_preflight_verifier.py",
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_runner_receipt_metadata_artifact.py",
    REPO_ROOT / "kernel" / "personal_ai" / "task_graph.py",
    REPO_ROOT / "kernel" / "personal_ai" / "task_graph_artifact_outputs.py",
)

FORBIDDEN_IMPORT_ROOTS = {
    "http",
    "playwright",
    "requests",
    "selenium",
    "socket",
    "subprocess",
    "urllib",
    "webbrowser",
}
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "os.system",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.run",
    "webbrowser.open",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_cli(argv):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = main(argv)
    payload = json.loads(stdout.getvalue())
    return exit_code, payload


class LocalFixtureRunnerChainIntegrationTests(unittest.TestCase):
    def test_registry_cli_and_product_health_visibility_for_all_five(self):
        registry = {
            entry.adapter_id: entry
            for entry in DEFAULT_ADAPTER_REGISTRY
            if entry.adapter_id in TARGETS
        }

        self.assertEqual(set(registry), set(TARGETS))
        for adapter_id, entry in registry.items():
            capability, subcommand, workflow = TARGETS[adapter_id]
            self.assertEqual(entry.admission_status.value, "candidate")
            self.assertEqual(entry.capabilities, (capability,))
            self.assertIn("metadata_only", entry.required_controls)
            self.assertFalse(entry.boundary.network_allowed)
            self.assertFalse(entry.boundary.subprocess_allowed)
            self.assertFalse(entry.boundary.external_tool_control_allowed)
            self.assertFalse(entry.boundary.input_mutation_allowed)
            self.assertFalse(entry.boundary.overwrite_existing_allowed)
            self.assertIn(subcommand, _SUBCOMMANDS)

        report = build_product_health_report(REPO_ROOT)
        self.assertTrue(report["launcher_workflows_complete"])
        self.assertTrue(report["cli_subcommands_complete"])
        for _adapter_id, (_capability, subcommand, workflow) in TARGETS.items():
            self.assertIn(workflow, report["launcher_workflows"])
            self.assertIn(subcommand, report["required_cli_subcommands"])

    def test_cli_chain_runs_metadata_only_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.run_cli_chain(Path(temp_dir))

            receipt_payload = read_json(paths["receipt_result"])
            self.assertTrue(receipt_payload["receipt_recorded"])
            self.assertTrue(receipt_payload["metadata_only"])
            self.assertTrue(receipt_payload["runner_receipt_metadata_only"])
            self.assertEqual(
                receipt_payload["receipt_status"],
                "local_fixture_runner_receipt_metadata_artifact_completed",
            )
            for field_name in LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS:
                self.assertFalse(receipt_payload[field_name], field_name)

    def test_task_graph_dispatch_and_artifact_outputs_bind_all_five(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            human_path = root / "human_approval.json"
            write_json_atomically(human_path, self.valid_human_approval_payload())

            output_dirs = {
                "contract": root / "contract",
                "stub_gate": root / "stub-gate",
                "receipt_contract": root / "receipt-contract",
                "preflight": root / "preflight",
                "receipt": root / "receipt",
                "graph": root / "graph-output",
            }
            for output_dir in output_dirs.values():
                output_dir.mkdir()

            graph_path = root / "runner-chain-graph.json"
            write_json_atomically(
                graph_path,
                self.runner_chain_graph(root, human_path, output_dirs),
            )

            result = run_local_task_graph_fixture(graph_path, output_dirs["graph"])
            execution_manifest = read_json(result.execution_manifest_path)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)

            self.assertTrue(result.success)
            self.assertEqual(len(execution_manifest["nodes"]), 5)
            self.assertFalse(execution_manifest["runtime_activation_performed"])
            self.assertFalse(execution_manifest["network_runtime_allowed"])
            self.assertFalse(execution_manifest["browser_runtime_allowed"])
            self.assertFalse(execution_manifest["subprocess_runtime_allowed"])
            for node in execution_manifest["nodes"]:
                self.assertEqual(node["status"], "completed")
                self.assertFalse(node["adapter_route_admitted"])
                self.assertEqual(
                    node["adapter_route_policy"],
                    "local_fixture_runner_metadata_chain_not_production_admitted",
                )
                self.assertTrue(node["metadata_only"])
                for field_name in self.boundary_false_fields():
                    if field_name in node:
                        self.assertFalse(node[field_name], (node["node_id"], field_name))

            artifact_adapters = {
                artifact["adapter_id"] for artifact in artifact_outputs["artifacts"]
            }
            self.assertTrue(set(TARGETS).issubset(artifact_adapters))
            for node_id in (
                "runner_01_contract",
                "runner_02_stub_gate",
                "runner_03_receipt_contract",
                "runner_04_preflight",
                "runner_05_receipt",
            ):
                self.assertEqual(artifact_outputs["node_artifact_counts"][node_id], 7)
            for field_name in (
                "network_access_performed",
                "model_api_called",
                "external_runtime_invoked",
                "output_overwrite_performed",
            ):
                self.assertFalse(artifact_outputs[field_name], field_name)

    def test_forbidden_boundary_static_scan_has_no_runtime_materialization(self):
        for path in TARGET_MODULE_PATHS:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(
                            alias.name.split(".", 1)[0],
                            FORBIDDEN_IMPORT_ROOTS,
                            (path, alias.name),
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(
                        node.module.split(".", 1)[0],
                        FORBIDDEN_IMPORT_ROOTS,
                        (path, node.module),
                    )
                elif isinstance(node, ast.Call):
                    call_name = self.call_name(node.func)
                    self.assertNotIn(call_name, FORBIDDEN_CALLS, (path, call_name))

    def run_cli_chain(self, root):
        human_path = root / "human_approval.json"
        write_json_atomically(human_path, self.valid_human_approval_payload())

        contract_dir = root / "contract-output"
        stub_dir = root / "stub-gate-output"
        receipt_contract_dir = root / "receipt-contract-output"
        preflight_dir = root / "preflight-output"
        receipt_dir = root / "receipt-output"
        for output_dir in (
            contract_dir,
            stub_dir,
            receipt_contract_dir,
            preflight_dir,
            receipt_dir,
        ):
            output_dir.mkdir()

        commands = (
            (
                [
                    "launch-local-fixture-runner-contract-draft",
                    "--output-dir",
                    contract_dir.as_posix(),
                    "--runner-contract-id",
                    "runner-contract-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_REVIEW_ATTESTATION,
                    "--project-id",
                    "project-001",
                    "--reviewer-id",
                    "reviewer-001",
                    "--operator-notes",
                    "integration contract review",
                ],
                contract_dir / LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_RESULT_FILE,
            ),
            (
                [
                    "launch-local-fixture-runner-stub-admission-gate",
                    "--human-approval-artifact-result",
                    human_path.as_posix(),
                    "--runner-contract-draft-result",
                    (
                        contract_dir
                        / LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_RESULT_FILE
                    ).as_posix(),
                    "--output-dir",
                    stub_dir.as_posix(),
                    "--gate-id",
                    "runner-stub-gate-001",
                    "--reviewer-id",
                    "reviewer-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION,
                ],
                stub_dir / LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
            ),
            (
                [
                    "launch-local-fixture-runner-receipt-contract-draft",
                    "--output-dir",
                    receipt_contract_dir.as_posix(),
                    "--receipt-contract-id",
                    "runner-receipt-contract-001",
                    "--reviewer-id",
                    "reviewer-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION,
                    "--project-id",
                    "project-001",
                    "--operator-notes",
                    "integration receipt contract review",
                ],
                receipt_contract_dir
                / LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
            ),
            (
                [
                    "launch-local-fixture-runner-receipt-preflight-verifier",
                    "--runner-stub-admission-gate-result",
                    (
                        stub_dir
                        / LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
                    ).as_posix(),
                    "--runner-receipt-contract-draft-result",
                    (
                        receipt_contract_dir
                        / LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
                    ).as_posix(),
                    "--human-approval-artifact-result",
                    human_path.as_posix(),
                    "--output-dir",
                    preflight_dir.as_posix(),
                    "--preflight-id",
                    "runner-receipt-preflight-001",
                    "--reviewer-id",
                    "reviewer-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION,
                    "--project-id",
                    "project-001",
                    "--operator-notes",
                    "integration preflight review",
                ],
                preflight_dir / LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
            ),
            (
                [
                    "launch-local-fixture-runner-receipt-metadata-artifact",
                    "--runner-receipt-preflight-result",
                    (
                        preflight_dir
                        / LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
                    ).as_posix(),
                    "--output-dir",
                    receipt_dir.as_posix(),
                    "--runner-receipt-id",
                    "runner-receipt-001",
                    "--reviewer-id",
                    "reviewer-001",
                    "--review-attestation",
                    LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION,
                    "--project-id",
                    "project-001",
                    "--operator-notes",
                    "integration receipt metadata review",
                ],
                receipt_dir / "local_fixture_runner_receipt_metadata_artifact_result.json",
            ),
        )

        for argv, expected_result in commands:
            exit_code, payload = run_cli(list(argv))
            self.assertEqual(exit_code, 0, payload)
            self.assertTrue(payload["complete"], payload)
            self.assertTrue(expected_result.is_file(), expected_result)

        return {
            "human": human_path,
            "contract_result": contract_dir
            / LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_RESULT_FILE,
            "stub_result": stub_dir / LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE,
            "receipt_contract_result": receipt_contract_dir
            / LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE,
            "preflight_result": preflight_dir
            / LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE,
            "receipt_result": receipt_dir
            / "local_fixture_runner_receipt_metadata_artifact_result.json",
        }

    def runner_chain_graph(self, root, human_path, output_dirs):
        return {
            "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
            "graph_id": "local-fixture-runner-chain-integration",
            "authority": "non_authority",
            "required_human_approval": True,
            "nodes": [
                {
                    "node_id": "runner_01_contract",
                    "adapter_id": "local_fixture_runner_contract_draft",
                    "capability": "launch_local_fixture_runner_contract_draft",
                    "depends_on": [],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "output_dir": output_dirs["contract"].as_posix(),
                        "runner_contract_id": "runner-contract-graph-001",
                        "review_attestation": (
                            LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_REVIEW_ATTESTATION
                        ),
                        "project_id": "project-001",
                        "reviewer_id": "reviewer-001",
                    },
                },
                {
                    "node_id": "runner_02_stub_gate",
                    "adapter_id": "local_fixture_runner_stub_admission_gate",
                    "capability": "launch_local_fixture_runner_stub_admission_gate",
                    "depends_on": ["runner_01_contract"],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "human_approval_artifact_result": human_path.as_posix(),
                        "runner_contract_draft_result": (
                            output_dirs["contract"]
                            / LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_RESULT_FILE
                        ).as_posix(),
                        "output_dir": output_dirs["stub_gate"].as_posix(),
                        "gate_id": "runner-stub-gate-graph-001",
                        "reviewer_id": "reviewer-001",
                        "review_attestation": (
                            LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_ATTESTATION
                        ),
                    },
                },
                {
                    "node_id": "runner_03_receipt_contract",
                    "adapter_id": "local_fixture_runner_receipt_contract_draft",
                    "capability": (
                        "launch_local_fixture_runner_receipt_contract_draft"
                    ),
                    "depends_on": ["runner_02_stub_gate"],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "output_dir": output_dirs["receipt_contract"].as_posix(),
                        "receipt_contract_id": "runner-receipt-contract-graph-001",
                        "reviewer_id": "reviewer-001",
                        "review_attestation": (
                            LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_REVIEW_ATTESTATION
                        ),
                        "project_id": "project-001",
                    },
                },
                {
                    "node_id": "runner_04_preflight",
                    "adapter_id": "local_fixture_runner_receipt_preflight_verifier",
                    "capability": (
                        "launch_local_fixture_runner_receipt_preflight_verifier"
                    ),
                    "depends_on": ["runner_03_receipt_contract"],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "runner_stub_admission_gate_result": (
                            output_dirs["stub_gate"]
                            / LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_RESULT_FILE
                        ).as_posix(),
                        "runner_receipt_contract_draft_result": (
                            output_dirs["receipt_contract"]
                            / LOCAL_FIXTURE_RUNNER_RECEIPT_CONTRACT_DRAFT_RESULT_FILE
                        ).as_posix(),
                        "human_approval_artifact_result": human_path.as_posix(),
                        "output_dir": output_dirs["preflight"].as_posix(),
                        "preflight_id": "runner-receipt-preflight-graph-001",
                        "reviewer_id": "reviewer-001",
                        "review_attestation": (
                            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_ATTESTATION
                        ),
                        "project_id": "project-001",
                    },
                },
                {
                    "node_id": "runner_05_receipt",
                    "adapter_id": "local_fixture_runner_receipt_metadata_artifact",
                    "capability": (
                        "launch_local_fixture_runner_receipt_metadata_artifact"
                    ),
                    "depends_on": ["runner_04_preflight"],
                    "approval_checkpoint_required": True,
                    "inputs": {
                        "runner_receipt_preflight_result": (
                            output_dirs["preflight"]
                            / LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_RESULT_FILE
                        ).as_posix(),
                        "output_dir": output_dirs["receipt"].as_posix(),
                        "runner_receipt_id": "runner-receipt-graph-001",
                        "reviewer_id": "reviewer-001",
                        "review_attestation": (
                            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_ATTESTATION
                        ),
                        "project_id": "project-001",
                    },
                },
            ],
        }

    def valid_human_approval_payload(self):
        payload = {
            "approval_artifact_type": "local_fixture_human_approval_artifact_v1",
            "approval_recorded": True,
            "approval_artifact_status": (
                "local_fixture_human_approval_artifact_completed"
            ),
            "approval_artifact_decision": "record_human_approval_artifact_only",
            "metadata_only": True,
            "human_review_recorded": True,
            "required_human_approval": True,
            "non_production": True,
            "future_runner_requires_separate_pr": True,
            "future_execution_requires_separate_runner_receipt": True,
            "future_execution_requires_explicit_local_fixture_runner_gate": True,
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "local_fixture_sha256": "f" * 64,
            "complete": True,
            "rejection_reasons": [],
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS
            }
        )
        return payload

    def boundary_false_fields(self):
        return set(LOCAL_FIXTURE_RUNNER_STUB_ADMISSION_GATE_FALSE_FIELDS).union(
            LOCAL_FIXTURE_RUNNER_RECEIPT_PREFLIGHT_VERIFIER_FALSE_FIELDS,
            LOCAL_FIXTURE_RUNNER_RECEIPT_METADATA_ARTIFACT_FALSE_FIELDS,
            {
                "execution_runner_created",
                "approval_token_issued",
                "execution_token_issued",
                "adapter_execution_performed",
                "playwright_execution_performed",
                "browser_open_performed",
                "network_access_performed",
                "live_website_access_performed",
                "production_promotion_granted",
                "autonomous_execution_performed",
            },
        )

    def call_name(self, func):
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parent = self.call_name(func.value)
            return parent + "." + func.attr if parent else func.attr
        return ""


if __name__ == "__main__":
    unittest.main()
