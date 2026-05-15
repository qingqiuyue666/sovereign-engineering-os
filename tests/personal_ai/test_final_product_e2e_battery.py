import json
import tempfile
import time
import unittest
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.adapters.blender_runtime import run_blender_runtime
from kernel.personal_ai.adapters.browser_runtime import run_browser_runtime
from kernel.personal_ai.adapters.comfyui_runtime import run_comfyui_runtime
from kernel.personal_ai.adapters.creative_adapter_contract import CreativeAdapterFamily
from kernel.personal_ai.adapters.creative_handoff_package import (
    build_creative_handoff_package,
)
from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    run_model_fixture,
    write_model_provider_request,
)
from kernel.personal_ai.adapters.xlsx_output_writer import (
    approve_xlsx_output,
    create_approved_xlsx_output,
    plan_xlsx_output,
)
from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_browser_runtime_dry_run_launcher,
    run_model_provider_dry_run_launcher,
    run_product_health_check_launcher,
    run_task_graph_launcher,
)
from kernel.personal_ai.runtime_delivery_package import (
    build_runtime_delivery_package,
    validate_runtime_delivery_package,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class FinalProductE2EBatteryTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_realistic_workbook(self, path):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Revenue Raw"
        sheet["A1"] = "RAW_HEADER_SECRET"
        sheet["B1"] = "Amount"
        sheet["A2"] = "RAW_CELL_SECRET"
        sheet["B2"] = 42
        second = workbook.create_sheet("Ops")
        second["A1"] = "Status"
        second["A2"] = "Ready"
        workbook.save(path)

    def test_office_redaction_approved_output_and_delivery_battery(self):
        root = self.make_root()
        input_dir = root / "input"
        office_dir = root / "office"
        package_root = root / "packages"
        delivery_validation_path = root / "delivery_validation.json"
        for path in (input_dir, office_dir, package_root):
            path.mkdir()
        workbook_path = input_dir / "realistic.xlsx"
        self.write_realistic_workbook(workbook_path)
        original_hash = sha256_file(workbook_path)

        inspection = inspect_xlsx_readonly(
            workbook_path,
            office_dir,
            redact_sheet_names=True,
            redact_input_path=True,
        )
        plan = plan_xlsx_output(
            workbook_path,
            inspection.xlsx_inspection_path,
            office_dir,
            redact_input_path=True,
        )
        approval = approve_xlsx_output(
            plan.plan_path,
            office_dir / "xlsx_output_approval.json",
            approved=True,
            human_reviewed=True,
            reviewer_id="qa-reviewer-001",
        )
        output = create_approved_xlsx_output(
            workbook_path,
            plan.plan_path,
            approval.approval_path,
            office_dir,
        )
        package = build_runtime_delivery_package(
            office_dir,
            package_root,
            package_id="final-product-delivery",
            input_dir=input_dir,
        )
        delivery_validation = validate_runtime_delivery_package(
            package.package_dir,
            delivery_validation_path,
            raw_sentinel_values=["RAW_HEADER_SECRET", "RAW_CELL_SECRET"],
        )
        inspection_text = inspection.xlsx_inspection_path.read_text(encoding="utf-8")

        self.assertTrue(output.complete)
        self.assertTrue(package.complete)
        self.assertTrue(delivery_validation.complete)
        self.assertEqual(original_hash, sha256_file(workbook_path))
        self.assertNotIn("RAW_CELL_SECRET", inspection_text)
        self.assertNotIn("Revenue Raw", inspection_text)
        self.assertIn("generated_output_xlsx", package.packaged_artifacts)

    def test_malformed_workbook_model_schema_and_browser_forbidden_battery(self):
        root = self.make_root()
        bad_input = root / "bad-input"
        bad_input.mkdir()
        bad_workbook = bad_input / "damaged.xlsx"
        bad_workbook.write_bytes(b"not a valid workbook")
        bad_output = root / "bad-office"
        bad_output.mkdir()

        with self.assertRaisesRegex(ValueError, "valid xlsx"):
            inspect_xlsx_readonly(bad_workbook, bad_output)

        input_artifact = root / "model_input.json"
        write_json_atomically(
            input_artifact,
            {
                "route_type": "spreadsheet_review",
                "recommended_processor_lane": "human_review_only",
            },
        )
        request_path = root / "model_request.json"
        model_output = root / "model-output"
        model_output.mkdir()
        write_model_provider_request(
            input_artifact,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        request = read_json(request_path)
        request["fixture_response"] = {
            "schema_name": ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
            "authority": "non_authority",
            "can_grant_authority": True,
            "can_edit_files": False,
            "can_call_tools": False,
        }
        write_json_atomically(request_path, request)
        model_result = run_model_fixture(request_path, model_output)
        model_failure = read_json(model_result.failure_bundle_path)

        browser_actions = root / "browser_forbidden_actions.json"
        write_json_atomically(
            browser_actions,
            {"actions": [{"action": "payment"}]},
        )
        browser_output = root / "browser-output"
        browser_output.mkdir()
        browser_result = run_browser_runtime(
            browser_output,
            actions_path=browser_actions,
            target_url="http://127.0.0.1",
        )
        browser_failure = read_json(browser_result.failure_quarantine_path)

        self.assertFalse(model_result.success)
        self.assertTrue(model_failure["invalid_output_quarantined"])
        self.assertFalse(model_failure["network_used"])
        self.assertFalse(browser_result.success)
        self.assertFalse(browser_failure["real_browser_called"])
        self.assertFalse(browser_failure["credential_persistence_used"])
        self.assertIn("not allowed", browser_failure["error_message"])

    def test_model_and_browser_dry_run_launchers_battery(self):
        root = self.make_root()
        input_artifact = root / "model_input.json"
        write_json_atomically(
            input_artifact,
            {
                "route_type": "spreadsheet_review",
                "recommended_processor_lane": "human_review_only",
            },
        )
        model_dir = root / "model-dry-run"
        browser_dir = root / "browser-dry-run"
        model_dir.mkdir()
        browser_dir.mkdir()
        browser_actions = root / "browser_dry_run_actions.json"
        write_json_atomically(
            browser_actions,
            {"actions": [{"action": "navigate"}, {"action": "inspect_title"}]},
        )

        model = run_model_provider_dry_run_launcher(
            input_artifact,
            model_dir,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        browser = run_browser_runtime_dry_run_launcher(
            browser_actions,
            browser_dir,
            target_url="http://127.0.0.1",
        )

        self.assertTrue(model.complete)
        self.assertTrue(browser.complete)
        self.assertFalse(model.payload["live_model_provider_called"])
        self.assertFalse(browser.payload["real_browser_called"])
        self.assertTrue(Path(model.payload["model_provider_dry_run_plan_path"]).exists())
        self.assertTrue(Path(browser.payload["browser_runtime_dry_run_plan_path"]).exists())

    def test_comfyui_blender_and_creative_handoff_battery(self):
        root = self.make_root()
        workflow_path = root / "workflow.json"
        asset_path = root / "asset.png"
        asset_path.write_bytes(b"COMFYUI_ASSET")
        write_json_atomically(
            workflow_path,
            {
                "nodes": [
                    {"id": "load", "type": "LoadImage", "inputs": {"image": "asset.png"}},
                    {"id": "preview", "type": "PreviewImage", "inputs": {"source": "load"}},
                ]
            },
        )
        comfyui_output = root / "comfyui"
        comfyui_output.mkdir()
        comfyui = run_comfyui_runtime(
            workflow_path,
            comfyui_output,
            input_asset_paths=(asset_path,),
        )

        scene_path = root / "scene.blend"
        scene_path.write_bytes(b"BLENDER_SCENE")
        plan_path = root / "blender_plan.json"
        write_json_atomically(
            plan_path,
            {
                "operations": [
                    {"operation": "add_camera", "parameters": {"name": "Camera"}},
                    {"operation": "render_preview", "parameters": {"samples": 16}},
                ]
            },
        )
        blender_output = root / "blender"
        blender_output.mkdir()
        blender = run_blender_runtime(scene_path, plan_path, blender_output)

        handoff_root = root / "handoff"
        handoff_root.mkdir()
        handoff = build_creative_handoff_package(
            CreativeAdapterFamily.BLENDER,
            (scene_path,),
            handoff_root,
            package_id="final-product-handoff",
        )
        handoff_manifest = read_json(handoff.package_manifest_path)

        self.assertTrue(comfyui.success)
        self.assertFalse(comfyui.real_endpoint_called)
        self.assertTrue(blender.success)
        self.assertFalse(blender.real_blender_called)
        self.assertTrue(handoff.complete)
        self.assertFalse(handoff_manifest["external_tool_control_performed"])
        self.assertEqual(sha256_file(scene_path), handoff_manifest["source_asset_hashes"][scene_path.as_posix()])

    def test_task_graph_launcher_health_and_performance_smoke_battery(self):
        root = self.make_root()
        runtime_dir = root / "runtime"
        package_root = root / "packages"
        graph_output = root / "graph-output"
        health_output = root / "health-output"
        for path in (runtime_dir, package_root, graph_output, health_output):
            path.mkdir()
        write_json_atomically(
            runtime_dir / "model_inference_artifact.json",
            {
                "artifact_type": "personal_ai_execution_os_v2_model_inference_artifact",
                "authority": "non_authority",
            },
        )
        package = build_runtime_delivery_package(
            runtime_dir,
            package_root,
            package_id="battery-delivery",
        )
        graph_path = root / "task_graph.json"
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "battery-graph",
                "execution_mode": "dry_run_plan",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "model_fixture",
                        "adapter_id": "mock_model_typed_schema_runtime",
                        "capability": "classify_local_job_package",
                        "execution_mode": "mock",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {},
                    },
                    {
                        "node_id": "delivery_validation",
                        "adapter_id": "runtime_delivery_package",
                        "capability": "validate_runtime_delivery",
                        "execution_mode": "dry_run",
                        "depends_on": ["model_fixture"],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "package_dir": package.package_dir.as_posix(),
                            "output_path": (
                                graph_output / "delivery_validation.json"
                            ).as_posix(),
                        },
                    },
                ],
            },
        )

        start = time.monotonic()
        graph = run_task_graph_launcher(graph_path, graph_output)
        health = run_product_health_check_launcher(health_output)
        duration_seconds = time.monotonic() - start
        graph_manifest = read_json(graph.payload["task_graph_execution_manifest_path"])
        health_report = read_json(health.payload["product_health_report_path"])

        self.assertTrue(graph.complete)
        self.assertTrue(health.complete)
        self.assertTrue(graph_manifest["dry_run_planning_mode"])
        self.assertFalse(graph_manifest["runtime_activation_performed"])
        self.assertFalse(health_report["runtime_activation_performed"])
        self.assertLess(duration_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
