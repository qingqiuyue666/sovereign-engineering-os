"""Behavior tests for the cross-software workflow engine."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.workflows.definition import load_workflow_definition
from execution_plane.workflows.runner import run_workflow
from execution_plane.workflows.scheduler import topological_layers


class CrossSoftwareWorkflowEngineV1Tests(unittest.TestCase):
    def test_example_definition_schedules_houdini_comfyui_then_davinci(self) -> None:
        definition = load_workflow_definition(
            {
                "workflow_path": "examples/workflows/cross_dcc_workflow_v1.json",
                "output_root": "work/test_cross_dcc_workflow_engine",
            }
        )
        layers = topological_layers(definition)
        self.assertEqual(
            [[node.node_id for node in layer] for layer in layers],
            [["houdini_smoke_cache"], ["comfyui_submit"], ["davinci_project_probe"]],
        )

    def test_artifact_refs_are_routed_to_dependent_node_payloads(self) -> None:
        seen_payloads: dict[str, dict[str, object]] = {}
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "workflow"

            def dispatch(permit: dict[str, object], payload: dict[str, object] | None) -> dict[str, object]:
                node_id = Path(str(permit["allowed_output_root"])).name
                seen_payloads[node_id] = dict(payload or {})
                return _success_result(
                    permit,
                    artifact_refs=[_artifact_ref(node_id)] if node_id == "producer" else [],
                )

            receipt = run_workflow(_two_node_params(output_root), dispatch=dispatch)
            routed_payload = json.loads((output_root / "consumer" / "node_input_payload.json").read_text(encoding="utf-8"))
            route_receipt = json.loads((output_root / "consumer" / "artifact_routing_receipt.json").read_text(encoding="utf-8"))

        self.assertEqual(receipt["terminal_status"], "TERMINAL_SUCCEEDED")
        self.assertEqual(seen_payloads["consumer"]["artifact_refs"][0]["producer_node_id"], "producer")
        self.assertEqual(routed_payload["artifact_refs"][0]["storage_mode"], "path_ref")
        self.assertEqual(route_receipt["artifact_refs"][0]["artifact_id"], "ART_PRODUCER")

    def test_failure_blocks_downstream_and_writes_rerun_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "workflow"

            def dispatch(permit: dict[str, object], _payload: dict[str, object] | None) -> dict[str, object]:
                node_id = Path(str(permit["allowed_output_root"])).name
                if node_id == "producer":
                    return _failed_result(permit, "ENV_NOT_FOUND: test adapter unavailable")
                return _success_result(permit)

            receipt = run_workflow(_two_node_params(output_root), dispatch=dispatch)
            consumer_bundle = json.loads((output_root / "consumer" / "failure_bundle.json").read_text(encoding="utf-8"))
            rerun = json.loads((output_root / "rerun_from_failed_node.json").read_text(encoding="utf-8"))

        self.assertEqual(receipt["terminal_status"], "TERMINAL_FAILED")
        self.assertEqual(receipt["node_results"][1]["result"]["status"], "BLOCKED")
        self.assertEqual(consumer_bundle["policy_blocks"], ["DEPENDENCY_FAILED"])
        self.assertEqual(rerun["rerun"]["failed_node_id"], "producer")
        self.assertEqual(rerun["rerun"]["included_node_ids"], ["consumer", "producer"])

    def test_runner_writes_workflow_receipt_manifest_and_state_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "workflow"
            receipt = run_workflow(
                {
                    "workflow_id": "single_success",
                    "output_root": output_root.as_posix(),
                    "nodes": [
                        {
                            "node_id": "only",
                            "adapter": "fake_dcc",
                            "action": "smoke_generate_file",
                        }
                    ],
                },
                dispatch=lambda permit, payload: _success_result(permit, artifact_refs=[_artifact_ref("only")]),
            )
            loaded_receipt = json.loads((output_root / "workflow_receipt.json").read_text(encoding="utf-8"))
            manifest = json.loads((output_root / "artifact_manifest.json").read_text(encoding="utf-8"))
            states = [
                json.loads(line)["state"]
                for line in (output_root / "workflow_state_ledger.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(receipt["terminal_status"], "TERMINAL_SUCCEEDED")
        self.assertEqual(loaded_receipt["artifact_refs"][0]["artifact_id"], "ART_ONLY")
        self.assertEqual(manifest["artifact_refs"][0]["producer_node_id"], "only")
        self.assertEqual(states, ["CREATED", "VALIDATING", "RUNNING", "TERMINAL_SUCCEEDED"])


def _two_node_params(output_root: Path) -> dict[str, object]:
    return {
        "workflow_id": "artifact_route_test",
        "output_root": output_root.as_posix(),
        "nodes": [
            {
                "node_id": "producer",
                "adapter": "houdini_hython",
                "action": "smoke_cache_test",
            },
            {
                "node_id": "consumer",
                "adapter": "comfyui_local",
                "action": "submit_workflow",
                "payload": {"workflow_path": "examples/comfyui/workflows/minimal_save_image.json"},
            },
        ],
        "edges": [{"from": "producer", "to": "consumer"}],
    }


def _success_result(permit: dict[str, object], *, artifact_refs: list[dict[str, object]] | None = None) -> dict[str, object]:
    output_root = str(permit.get("allowed_output_root", ""))
    return {
        "schema_version": "seos_execution_result_v1",
        "permit_id": str(permit.get("permit_id", "")),
        "run_id": "RUN_TEST",
        "adapter": str(permit.get("allowed_adapter", "")),
        "started_at": "2026-01-01T00:00:00Z",
        "ended_at": "2026-01-01T00:00:01Z",
        "exit_code": 0,
        "status": "SUCCEEDED",
        "output_root": output_root,
        "outputs": [],
        "artifact_refs": list(artifact_refs or []),
        "stdout_digest": "sha256:" + "0" * 64,
        "stderr_digest": "sha256:" + "0" * 64,
        "failure_summary": None,
        "policy_blocks": [],
        "evidence_manifest_path": None,
        "state_transitions": [],
        "provision_result": {},
    }


def _failed_result(permit: dict[str, object], failure_summary: str) -> dict[str, object]:
    result = _success_result(permit)
    result["status"] = "FAILED"
    result["exit_code"] = 1
    result["failure_summary"] = failure_summary
    result["policy_blocks"] = ["ENV_NOT_FOUND"]
    return result


def _artifact_ref(node_id: str) -> dict[str, object]:
    upper = node_id.upper()
    return {
        "schema_version": "seos.artifact_ref.v1",
        "artifact_id": f"ART_{upper}",
        "producer_run_id": f"RUN_{upper}",
        "producer_node_id": node_id,
        "uri": f"seos://run/RUN_{upper}/out.txt",
        "relative_path": "out.txt",
        "size_bytes": 3,
        "sha256": "sha256:" + "a" * 64,
        "media_type": "text/plain",
        "storage_mode": "path_ref",
        "copy_policy": "zero_copy_reference",
        "lifetime": "managed_by_run_package",
    }


if __name__ == "__main__":
    unittest.main()
