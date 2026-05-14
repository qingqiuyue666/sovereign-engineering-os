import contextlib
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.adapters.model_adapter_contract import ModelFixtureSchema
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    write_model_fixture_request,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.runtime_delivery_package import build_runtime_delivery_package
from kernel.personal_ai.io_utils import write_json_atomically


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalMVPCLIV2RuntimeTests(unittest.TestCase):
    def run_cli_raw(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exit_code = main(args)
            except SystemExit as error:
                exit_code = error.code if isinstance(error.code, int) else 1
        output = stdout.getvalue()
        payload = json.loads(output) if output.strip() else None
        return exit_code, payload, stderr.getvalue()

    def run_cli(self, args):
        exit_code, payload, _ = self.run_cli_raw(args)
        self.assertIsNotNone(payload)
        return exit_code, payload

    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        xlsx_runtime_dir = root / "xlsx-runtime"
        model_dir = root / "model"
        browser_dir = root / "browser"
        package_root = root / "packages"
        for path in (input_dir, xlsx_runtime_dir, model_dir, browser_dir, package_root):
            path.mkdir()
        workbook_path = input_dir / "source.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = "RAW_HEADER_SECRET"
        sheet["A2"] = "RAW_CELL_SECRET"
        workbook.save(workbook_path)
        return root, input_dir, workbook_path, xlsx_runtime_dir, model_dir, browser_dir, package_root

    def test_xlsx_runtime_cli_flow(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()

        inspect_code, inspect_payload = self.run_cli(
            [
                "inspect-xlsx",
                "--input-workbook",
                workbook_path.as_posix(),
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        plan_code, plan_payload = self.run_cli(
            [
                "plan-xlsx-output",
                "--input-workbook",
                workbook_path.as_posix(),
                "--xlsx-inspection",
                inspect_payload["xlsx_inspection_path"],
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        approval_path = xlsx_dir / "xlsx_output_approval.json"
        approve_code, approve_payload = self.run_cli(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                approval_path.as_posix(),
                "--approved",
                "true",
                "--human-reviewed",
                "true",
                "--reviewer-id",
                "reviewer-001",
            ]
        )
        create_code, create_payload = self.run_cli(
            [
                "create-approved-xlsx-output",
                "--input-workbook",
                workbook_path.as_posix(),
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--approval-path",
                approve_payload["xlsx_output_approval_path"],
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        validate_code, validate_payload = self.run_cli(
            [
                "validate-xlsx-output",
                "--output-dir",
                xlsx_dir.as_posix(),
                "--output-path",
                (xlsx_dir / "xlsx_output_validation_cli.json").as_posix(),
            ]
        )

        self.assertEqual(inspect_code, 0)
        self.assertEqual(plan_code, 0)
        self.assertEqual(approve_code, 0)
        self.assertEqual(create_code, 0)
        self.assertEqual(validate_code, 0)
        self.assertTrue(create_payload["complete"])
        self.assertTrue(validate_payload["manifest_hash_verified"])

    def test_approve_xlsx_output_cli_requires_approved_flag(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, stderr = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--human-reviewed",
                "true",
                "--reviewer-id",
                "reviewer-001",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertIsNone(payload)
        self.assertIn("--approved", stderr)

    def test_approve_xlsx_output_cli_requires_human_reviewed_flag(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, stderr = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "true",
                "--reviewer-id",
                "reviewer-001",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertIsNone(payload)
        self.assertIn("--human-reviewed", stderr)

    def test_approve_xlsx_output_cli_requires_reviewer_id_flag(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, stderr = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "true",
                "--human-reviewed",
                "true",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertIsNone(payload)
        self.assertIn("--reviewer-id", stderr)

    def test_approve_xlsx_output_cli_rejects_approved_false(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, _ = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "false",
                "--human-reviewed",
                "true",
                "--reviewer-id",
                "reviewer-001",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertFalse(payload["complete"])
        self.assertIn("--approved must be exactly true", payload["error_message"])

    def test_approve_xlsx_output_cli_rejects_human_reviewed_false(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, _ = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "true",
                "--human-reviewed",
                "false",
                "--reviewer-id",
                "reviewer-001",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertFalse(payload["complete"])
        self.assertIn(
            "--human-reviewed must be exactly true",
            payload["error_message"],
        )

    def test_approve_xlsx_output_cli_rejects_placeholder_reviewer_id(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        for reviewer_id in ("local_human_review", "default", "anonymous"):
            with self.subTest(reviewer_id=reviewer_id):
                exit_code, payload, _ = self.run_cli_raw(
                    [
                        "approve-xlsx-output",
                        "--plan-path",
                        plan_payload["xlsx_output_plan_path"],
                        "--output-path",
                        (xlsx_dir / f"approval-{reviewer_id}.json").as_posix(),
                        "--approved",
                        "true",
                        "--human-reviewed",
                        "true",
                        "--reviewer-id",
                        reviewer_id,
                    ]
                )

                self.assertNotEqual(exit_code, 0)
                self.assertFalse(payload["complete"])
                self.assertIn(
                    "placeholder reviewer_id is not allowed",
                    payload["error_message"],
                )

    def test_approve_xlsx_output_cli_rejects_blank_reviewer_id(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload, _ = self.run_cli_raw(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "true",
                "--human-reviewed",
                "true",
                "--reviewer-id",
                "  ",
            ]
        )

        self.assertNotEqual(exit_code, 0)
        self.assertFalse(payload["complete"])
        self.assertIn("explicit reviewer_id is required", payload["error_message"])

    def test_approve_xlsx_output_cli_accepts_explicit_reviewer_approval(self):
        _, _, workbook_path, xlsx_dir, _, _, _ = self.build_workspace()
        plan_payload = self.build_xlsx_output_plan(workbook_path, xlsx_dir)

        exit_code, payload = self.run_cli(
            [
                "approve-xlsx-output",
                "--plan-path",
                plan_payload["xlsx_output_plan_path"],
                "--output-path",
                (xlsx_dir / "approval.json").as_posix(),
                "--approved",
                "true",
                "--human-reviewed",
                "true",
                "--reviewer-id",
                "reviewer-001",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["approved"])

    def build_xlsx_output_plan(self, workbook_path, xlsx_dir):
        _, inspect_payload = self.run_cli(
            [
                "inspect-xlsx",
                "--input-workbook",
                workbook_path.as_posix(),
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        _, plan_payload = self.run_cli(
            [
                "plan-xlsx-output",
                "--input-workbook",
                workbook_path.as_posix(),
                "--xlsx-inspection",
                inspect_payload["xlsx_inspection_path"],
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        return plan_payload

    def test_model_and_browser_fixture_cli_commands(self):
        root, _, _, _, model_dir, browser_dir, _ = self.build_workspace()
        input_artifact = root / "route.json"
        write_json_atomically(
            input_artifact,
            {
                "route_type": "spreadsheet_route",
                "recommended_processor_lane": "spreadsheet_review",
            },
        )
        request_path = root / "model_request.json"
        write_model_fixture_request(
            input_artifact,
            request_path,
            schema_name=ModelFixtureSchema.JOB_ROUTE_CLASSIFICATION,
        )
        model_code, model_payload = self.run_cli(
            [
                "run-model-fixture",
                "--request-path",
                request_path.as_posix(),
                "--output-dir",
                model_dir.as_posix(),
            ]
        )

        fixture_dir = root / "fixture"
        fixture_dir.mkdir()
        fixture_path = fixture_dir / "page.html"
        fixture_path.write_text(
            "<html><head><title>Fixture</title></head><body>"
            "<input name='query' data-seos-allowed-field='true' />"
            "<button id='go' data-seos-allowed-button='true'>Go</button>"
            "</body></html>",
            encoding="utf-8",
        )
        actions_path = root / "actions.json"
        write_json_atomically(
            actions_path,
            {
                "actions": [
                    {"action": "open_local_fixture"},
                    {
                        "action": "fill_allowed_field",
                        "field_name": "query",
                        "value": "typed value",
                    },
                    {"action": "click_allowed_button", "button_id": "go"},
                ]
            },
        )
        browser_code, browser_payload = self.run_cli(
            [
                "run-browser-fixture",
                "--fixture-path",
                fixture_path.as_posix(),
                "--actions-path",
                actions_path.as_posix(),
                "--output-dir",
                browser_dir.as_posix(),
            ]
        )

        self.assertEqual(model_code, 0)
        self.assertEqual(browser_code, 0)
        self.assertTrue(model_payload["complete"])
        self.assertEqual(browser_payload["action_count"], 3)

    def test_registry_and_tool_intake_cli_commands(self):
        root, _, _, _, _, _, _ = self.build_workspace()
        registry_output = root / "adapter_registry.json"
        tool_output = root / "tool_intake_validation.json"

        registry_code, registry_payload = self.run_cli(
            ["show-adapter-registry", "--output-path", registry_output.as_posix()]
        )
        tool_code, tool_payload = self.run_cli(
            [
                "validate-tool-intake",
                "--register-path",
                "governance/integration/runtime_tool_admission_register.yaml",
                "--output-path",
                tool_output.as_posix(),
            ]
        )

        self.assertEqual(registry_code, 0)
        self.assertEqual(tool_code, 0)
        self.assertTrue(registry_payload["complete"])
        self.assertTrue(tool_payload["complete"])
        self.assertTrue(registry_output.exists())
        self.assertTrue(tool_output.exists())
        self.assertIn(
            "xlsx_readonly_runtime",
            [entry["adapter_id"] for entry in registry_payload["entries"]],
        )

    def test_validate_runtime_delivery_cli(self):
        root, input_dir, workbook_path, xlsx_dir, model_dir, browser_dir, package_root = self.build_workspace()
        self.run_cli(
            [
                "inspect-xlsx",
                "--input-workbook",
                workbook_path.as_posix(),
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        write_json_atomically(
            xlsx_dir / "model_inference_artifact.json",
            {"artifact_type": "personal_ai_execution_os_v2_model_inference_artifact"},
        )
        write_json_atomically(
            xlsx_dir / "browser_action_log.json",
            {"log_type": "personal_ai_execution_os_v2_browser_action_log"},
        )
        write_json_atomically(
            xlsx_dir / "browser_evidence_manifest.json",
            {"manifest_type": "personal_ai_execution_os_v2_browser_evidence_manifest"},
        )
        package = build_runtime_delivery_package(
            xlsx_dir,
            package_root,
            package_id="runtime-delivery-001",
            input_dir=input_dir,
        )
        validation_path = root / "runtime_delivery_validation_cli.json"

        exit_code, payload = self.run_cli(
            [
                "validate-runtime-delivery",
                "--package-dir",
                package.package_dir.as_posix(),
                "--output-path",
                validation_path.as_posix(),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(validation_path.exists())

    def test_validate_runtime_delivery_cli_accepts_dynamic_leakage_sentinel(self):
        root, input_dir, workbook_path, xlsx_dir, _, _, package_root = self.build_workspace()
        self.run_cli(
            [
                "inspect-xlsx",
                "--input-workbook",
                workbook_path.as_posix(),
                "--output-dir",
                xlsx_dir.as_posix(),
            ]
        )
        package = build_runtime_delivery_package(
            xlsx_dir,
            package_root,
            package_id="runtime-delivery-001",
            input_dir=input_dir,
        )
        dynamic_sentinel = "secret_" + uuid.uuid4().hex
        (package.package_dir / "leak.md").write_text(dynamic_sentinel, encoding="utf-8")
        validation_path = root / "runtime_delivery_validation_leak.json"

        exit_code, payload = self.run_cli(
            [
                "validate-runtime-delivery",
                "--package-dir",
                package.package_dir.as_posix(),
                "--output-path",
                validation_path.as_posix(),
                "--raw-sentinel",
                dynamic_sentinel,
            ]
        )

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["complete"])
        self.assertTrue(payload["raw_value_leakage_detected"])


if __name__ == "__main__":
    unittest.main()
