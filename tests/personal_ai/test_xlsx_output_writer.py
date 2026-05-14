import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.adapters.xlsx_output_writer import (
    approve_xlsx_output,
    create_approved_xlsx_output,
    plan_xlsx_output,
    validate_xlsx_output,
)
from kernel.personal_ai.hash_utils import sha256_file


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class XlsxOutputWriterTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        inspection_dir = root / "inspection"
        output_dir = root / "output"
        input_dir.mkdir()
        inspection_dir.mkdir()
        output_dir.mkdir()
        workbook_path = input_dir / "source.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = "RAW_HEADER_SECRET"
        sheet["A2"] = "RAW_CELL_SECRET"
        workbook.save(workbook_path)
        inspection = inspect_xlsx_readonly(workbook_path, inspection_dir)
        plan = plan_xlsx_output(
            workbook_path,
            inspection.xlsx_inspection_path,
            output_dir,
        )
        approval_path = root / "approval.json"
        approval = approve_xlsx_output(plan.plan_path, approval_path)
        return root, input_dir, workbook_path, inspection, output_dir, plan, approval

    def test_plan_requires_hash_bound_inspection(self):
        _, _, workbook_path, inspection, output_dir, _, _ = self.build_workspace()
        second_output_dir = output_dir.parent / "second"
        second_output_dir.mkdir()

        result = plan_xlsx_output(
            workbook_path,
            inspection.xlsx_inspection_path,
            second_output_dir,
        )
        plan = read_json(result.plan_path)

        self.assertEqual(plan["input_sha256"], sha256_file(workbook_path))
        self.assertEqual(
            plan["xlsx_inspection_sha256"],
            sha256_file(inspection.xlsx_inspection_path),
        )
        self.assertTrue(plan["required_human_approval"])

    def test_approval_required(self):
        _, _, workbook_path, _, output_dir, plan, _ = self.build_workspace()
        missing_approval_path = output_dir.parent / "missing_approval.json"

        with self.assertRaises(ValueError):
            create_approved_xlsx_output(
                workbook_path,
                plan.plan_path,
                missing_approval_path,
                output_dir,
            )

    def test_hash_mismatch_rejected(self):
        _, _, workbook_path, _, output_dir, plan, approval = self.build_workspace()
        workbook = Workbook()
        workbook.active["A1"] = "changed"
        workbook.save(workbook_path)

        with self.assertRaises(ValueError):
            create_approved_xlsx_output(
                workbook_path,
                plan.plan_path,
                approval.approval_path,
                output_dir,
            )

    def test_creates_output_manifest_hash_summary_and_validation(self):
        _, _, workbook_path, _, output_dir, plan, approval = self.build_workspace()

        result = create_approved_xlsx_output(
            workbook_path,
            plan.plan_path,
            approval.approval_path,
            output_dir,
        )
        manifest = read_json(result.output_manifest_path)
        validation = read_json(result.validation_report_path)

        self.assertTrue(result.output_workbook_path.exists())
        self.assertTrue(result.output_manifest_path.exists())
        self.assertTrue(result.delivery_summary_path.exists())
        self.assertTrue(result.validation_report_path.exists())
        self.assertEqual(manifest["output_workbook_sha256"], result.output_sha256)
        self.assertTrue(validation["complete"])
        self.assertTrue(validation["manifest_hash_verified"])

    def test_refuses_existing_output_workbook(self):
        _, _, workbook_path, _, output_dir, plan, approval = self.build_workspace()
        (output_dir / "derived_xlsx_summary.xlsx").write_text("", encoding="utf-8")

        with self.assertRaises(ValueError):
            create_approved_xlsx_output(
                workbook_path,
                plan.plan_path,
                approval.approval_path,
                output_dir,
            )

    def test_preserves_input_and_does_not_leak_raw_values_to_audit_artifacts(self):
        _, _, workbook_path, _, output_dir, plan, approval = self.build_workspace()
        before_hash = sha256_file(workbook_path)

        result = create_approved_xlsx_output(
            workbook_path,
            plan.plan_path,
            approval.approval_path,
            output_dir,
        )

        self.assertEqual(sha256_file(workbook_path), before_hash)
        for path in (
            plan.plan_path,
            approval.approval_path,
            result.output_manifest_path,
            result.delivery_summary_path,
            result.validation_report_path,
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("RAW_HEADER_SECRET", text)
            self.assertNotIn("RAW_CELL_SECRET", text)

    def test_validate_xlsx_output_writes_separate_report_without_overwrite(self):
        root, _, workbook_path, _, output_dir, plan, approval = self.build_workspace()
        create_approved_xlsx_output(
            workbook_path,
            plan.plan_path,
            approval.approval_path,
            output_dir,
        )
        report_path = root / "validation-rerun.json"

        validation = validate_xlsx_output(output_dir, report_path)

        self.assertTrue(validation.complete)
        self.assertTrue(report_path.exists())
        with self.assertRaises(ValueError):
            validate_xlsx_output(output_dir, report_path)


if __name__ == "__main__":
    unittest.main()
