import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.adapters.browser_fixture_runtime import run_browser_fixture
from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    run_model_fixture,
    write_model_fixture_request,
)
from kernel.personal_ai.adapters.xlsx_output_writer import (
    approve_xlsx_output,
    create_approved_xlsx_output,
    plan_xlsx_output,
    validate_xlsx_output,
)
from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class V2RuntimeDemoEndToEndTests(unittest.TestCase):
    def test_personal_ai_execution_os_v2_demo_flow(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        runtime_dir = root / "runtime"
        fixture_dir = root / "fixture"
        delivery_root = root / "delivery"
        for path in (input_dir, runtime_dir, fixture_dir, delivery_root):
            path.mkdir()

        workbook_path = input_dir / "source.xlsx"
        _write_fixture_workbook(workbook_path)
        input_hash_before = sha256_file(workbook_path)

        inspection = inspect_xlsx_readonly(workbook_path, runtime_dir)
        plan = plan_xlsx_output(
            workbook_path,
            inspection.xlsx_inspection_path,
            runtime_dir,
        )
        approval = approve_xlsx_output(
            plan.plan_path,
            runtime_dir / "xlsx_output_approval.json",
        )
        output = create_approved_xlsx_output(
            workbook_path,
            plan.plan_path,
            approval.approval_path,
            runtime_dir,
        )
        validation = validate_xlsx_output(
            runtime_dir,
            runtime_dir / "xlsx_output_validation_rerun.json",
        )

        route_path = root / "route.json"
        write_json_atomically(
            route_path,
            {
                "route_type": "spreadsheet_route",
                "recommended_processor_lane": "spreadsheet_review",
                "next_allowed_action": "human_review_only",
            },
        )
        request_path = root / "model_request.json"
        write_model_fixture_request(
            route_path,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        model = run_model_fixture(request_path, runtime_dir)

        fixture_path = fixture_dir / "page.html"
        fixture_path.write_text(
            "<html><head><title>Runtime Demo</title></head><body>"
            "<a href='/local'>Local</a>"
            "<input name='query' data-seos-allowed-field='true' />"
            "<button id='go' data-seos-allowed-button='true'>Go</button>"
            "</body></html>",
            encoding="utf-8",
        )
        browser = run_browser_fixture(
            fixture_path,
            runtime_dir,
            [
                {"action": "open_local_fixture"},
                {"action": "inspect_title"},
                {"action": "inspect_links"},
                {
                    "action": "fill_allowed_field",
                    "field_name": "query",
                    "value": "demo typed value",
                },
                {"action": "click_allowed_button", "button_id": "go"},
            ],
        )

        delivery = build_runtime_delivery_package(
            runtime_dir,
            delivery_root,
            package_id="runtime-demo-delivery",
            input_dir=input_dir,
        )

        self.assertEqual(sha256_file(workbook_path), input_hash_before)
        self.assertTrue(inspection.xlsx_inspection_path.exists())
        self.assertTrue(output.output_workbook_path.exists())
        self.assertTrue(validation.complete)
        self.assertTrue(model.success)
        self.assertEqual(browser.action_count, 5)
        self.assertTrue(delivery.complete)
        self.assertIn("generated_output_xlsx", delivery.packaged_artifacts)
        self.assertIn("model_inference_artifact", delivery.packaged_artifacts)
        self.assertIn("browser_action_log", delivery.packaged_artifacts)
        self.assertFalse(
            read_json(delivery.runtime_delivery_validation_path)[
                "raw_value_leakage_detected"
            ]
        )
        for path in delivery.package_dir.iterdir():
            if path.suffix.lower() in (".json", ".md"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("RAW_HEADER_SECRET", text)
                self.assertNotIn("RAW_CELL_SECRET", text)


def _write_fixture_workbook(workbook_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "RAW_HEADER_SECRET"
    sheet["B1"] = "Value"
    sheet["A2"] = "RAW_CELL_SECRET"
    sheet["B2"] = 42
    sheet["B3"] = "=SUM(B2:B2)"
    workbook.create_sheet("Notes")["A1"] = "metadata"
    workbook.save(workbook_path)


if __name__ == "__main__":
    unittest.main()
