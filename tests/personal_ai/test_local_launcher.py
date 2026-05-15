import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalLauncherTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        office_dir = root / "office"
        model_dir = root / "model"
        browser_dir = root / "browser"
        delivery_source_dir = root / "delivery-source"
        delivery_package_root = root / "delivery-packages"
        delivery_validation_dir = root / "delivery-validation"
        for path in (
            input_dir,
            office_dir,
            model_dir,
            browser_dir,
            delivery_source_dir,
            delivery_package_root,
            delivery_validation_dir,
        ):
            path.mkdir()
        workbook_path = input_dir / "source.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "LauncherData"
        sheet["A1"] = "RAW_LAUNCHER_HEADER_SENTINEL"
        sheet["A2"] = "RAW_LAUNCHER_CELL_SENTINEL"
        workbook.save(workbook_path)
        model_input_path = input_dir / "model_input.json"
        write_json_atomically(
            model_input_path,
            {
                "route_type": "spreadsheet_review",
                "recommended_processor_lane": "human_review_only",
            },
        )
        fixture_path = input_dir / "fixture.html"
        fixture_path.write_text(
            "<html><title>Fixture</title><body>"
            "<input name='query' data-seos-allowed-field='true'>"
            "<button id='search' data-seos-allowed-button='true'>Search</button>"
            "</body></html>",
            encoding="utf-8",
        )
        actions_path = input_dir / "actions.json"
        write_json_atomically(
            actions_path,
            {
                "actions": [
                    {
                        "action": "fill_allowed_field",
                        "field_name": "query",
                        "value": "redacted",
                    },
                    {"action": "click_allowed_button", "button_id": "search"},
                ],
                "policy": {"timeout_seconds": 5},
            },
        )
        write_json_atomically(
            delivery_source_dir / "model_inference_artifact.json",
            {
                "artifact_type": "personal_ai_model_inference_artifact_v1",
                "authority": "non_authority",
            },
        )
        package = build_runtime_delivery_package(
            delivery_source_dir,
            delivery_package_root,
            package_id="launcher-delivery",
        )
        return {
            "root": root,
            "workbook_path": workbook_path,
            "office_dir": office_dir,
            "model_input_path": model_input_path,
            "model_dir": model_dir,
            "fixture_path": fixture_path,
            "actions_path": actions_path,
            "browser_dir": browser_dir,
            "package": package,
            "delivery_validation_dir": delivery_validation_dir,
        }

    def test_launch_office_workflow_writes_json_and_human_summary(self):
        workspace = self.build_workspace()

        exit_code, payload = self.run_cli(
            [
                "launch-office-workflow",
                "--input-workbook",
                workspace["workbook_path"].as_posix(),
                "--output-dir",
                workspace["office_dir"].as_posix(),
            ]
        )
        summary_text = Path(payload["human_summary_path"]).read_text(encoding="utf-8")
        inspection_text = Path(payload["xlsx_inspection_path"]).read_text(
            encoding="utf-8"
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["output_write_performed"])
        self.assertFalse(payload["input_mutation_performed"])
        self.assertTrue(Path(payload["xlsx_output_plan_path"]).exists())
        self.assertIn("Office Workflow", summary_text)
        self.assertNotIn("RAW_LAUNCHER_CELL_SENTINEL", inspection_text)
        self.assertNotIn("RAW_LAUNCHER_HEADER_SENTINEL", summary_text)

    def test_launch_model_fixture_workflow_is_local_only(self):
        workspace = self.build_workspace()

        exit_code, payload = self.run_cli(
            [
                "launch-model-fixture",
                "--input-artifact-path",
                workspace["model_input_path"].as_posix(),
                "--output-dir",
                workspace["model_dir"].as_posix(),
                "--schema-name",
                "job_route_classification_v1",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["live_model_provider_called"])
        self.assertFalse(payload["network_runtime_allowed"])
        self.assertTrue(Path(payload["model_inference_artifact_path"]).exists())
        self.assertTrue(Path(payload["human_summary_path"]).exists())

    def test_launch_browser_fixture_workflow_is_local_only(self):
        workspace = self.build_workspace()

        exit_code, payload = self.run_cli(
            [
                "launch-browser-fixture",
                "--fixture-path",
                workspace["fixture_path"].as_posix(),
                "--actions-path",
                workspace["actions_path"].as_posix(),
                "--output-dir",
                workspace["browser_dir"].as_posix(),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertFalse(payload["real_browser_runtime_used"])
        self.assertFalse(payload["external_network_used"])
        self.assertEqual(payload["action_count"], 2)
        self.assertTrue(Path(payload["browser_evidence_manifest_path"]).exists())

    def test_launch_runtime_delivery_validation_workflow(self):
        workspace = self.build_workspace()

        exit_code, payload = self.run_cli(
            [
                "launch-runtime-delivery-validation",
                "--package-dir",
                workspace["package"].package_dir.as_posix(),
                "--output-dir",
                workspace["delivery_validation_dir"].as_posix(),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertIn("model_inference_artifact", payload["packaged_artifacts"])
        self.assertFalse(payload["raw_value_leakage_detected"])
        self.assertTrue(Path(payload["runtime_delivery_validation_path"]).exists())
        self.assertTrue(Path(payload["human_summary_path"]).exists())

    def test_launcher_refuses_summary_overwrite(self):
        workspace = self.build_workspace()
        (workspace["model_dir"] / "launcher_summary.md").write_text(
            "existing",
            encoding="utf-8",
        )

        exit_code, payload = self.run_cli(
            [
                "launch-model-fixture",
                "--input-artifact-path",
                workspace["model_input_path"].as_posix(),
                "--output-dir",
                workspace["model_dir"].as_posix(),
                "--schema-name",
                "job_route_classification_v1",
            ]
        )

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["complete"])
        self.assertIn("already exists", payload["error_message"])


if __name__ == "__main__":
    unittest.main()
