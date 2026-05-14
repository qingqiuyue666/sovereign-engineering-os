import json
import tempfile
import unittest
import uuid
from pathlib import Path

from openpyxl import Workbook

from kernel.personal_ai.adapters.xlsx_adapter_contract import XlsxReadonlyLimits
from kernel.personal_ai.adapters.xlsx_readonly_runtime import (
    XlsxReadonlyInspectionResult,
    inspect_xlsx_readonly,
)
from kernel.personal_ai.hash_utils import sha256_file


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class XlsxReadonlyRuntimeTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        workbook_path = input_dir / "fixture.xlsx"
        self.write_fixture_workbook(workbook_path)
        return input_dir, workbook_path, output_dir

    def write_fixture_workbook(self, workbook_path):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = "RAW_HEADER_SECRET"
        sheet["B1"] = "Value"
        sheet["A2"] = "RAW_CELL_SECRET"
        sheet["B2"] = 7
        sheet["B3"] = "=SUM(B2:B2)"
        sheet["A1"].style = "Headline 1"
        extra = workbook.create_sheet("Empty")
        extra["A1"] = "Only"
        workbook.save(workbook_path)

    def test_inspects_xlsx_readonly_and_writes_bounded_outputs(self):
        _, workbook_path, output_dir = self.build_workspace()

        result = inspect_xlsx_readonly(workbook_path, output_dir)
        inspection = read_json(result.xlsx_inspection_path)

        self.assertIsInstance(result, XlsxReadonlyInspectionResult)
        self.assertTrue(result.xlsx_inspection_path.exists())
        self.assertTrue(result.xlsx_inspection_summary_path.exists())
        self.assertEqual(inspection["sheet_count"], 2)
        self.assertEqual(inspection["sheet_names"], ["Data", "Empty"])
        self.assertEqual(inspection["sheets"][0]["max_row"], 3)
        self.assertEqual(inspection["sheets"][0]["max_column"], 2)
        self.assertTrue(inspection["sheets"][0]["formula_presence"])
        self.assertGreaterEqual(inspection["sheets"][0]["formula_count_observed"], 1)
        self.assertFalse(inspection["raw_cell_values_copied"])
        self.assertEqual(
            inspection["extraction_limits"]["header_preview_raw_values"],
            False,
        )
        self.assertFalse(inspection["redaction"]["sheet_names_redacted"])
        self.assertFalse(inspection["redaction"]["input_path_redacted"])

    def test_preserves_input_hash_and_writes_outside_input_directory(self):
        input_dir, workbook_path, output_dir = self.build_workspace()
        before_hash = sha256_file(workbook_path)

        result = inspect_xlsx_readonly(workbook_path, output_dir)

        self.assertEqual(sha256_file(workbook_path), before_hash)
        self.assertFalse(str(result.xlsx_inspection_path).startswith(str(input_dir)))
        self.assertFalse(str(result.xlsx_inspection_summary_path).startswith(str(input_dir)))

    def test_refuses_output_directory_inside_input_directory(self):
        input_dir, workbook_path, _ = self.build_workspace()
        unsafe_output_dir = input_dir / "generated"
        unsafe_output_dir.mkdir()

        with self.assertRaises(ValueError):
            inspect_xlsx_readonly(workbook_path, unsafe_output_dir)

    def test_refuses_existing_outputs(self):
        _, workbook_path, output_dir = self.build_workspace()
        (output_dir / "xlsx_inspection.json").write_text("{}", encoding="utf-8")

        with self.assertRaises(ValueError):
            inspect_xlsx_readonly(workbook_path, output_dir)

    def test_does_not_dump_raw_workbook_values(self):
        _, workbook_path, output_dir = self.build_workspace()

        inspect_xlsx_readonly(workbook_path, output_dir)
        inspection_text = (output_dir / "xlsx_inspection.json").read_text(
            encoding="utf-8"
        )
        summary_text = (output_dir / "xlsx_inspection_summary.md").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("RAW_HEADER_SECRET", inspection_text)
        self.assertNotIn("RAW_CELL_SECRET", inspection_text)
        self.assertNotIn("RAW_HEADER_SECRET", summary_text)
        self.assertNotIn("RAW_CELL_SECRET", summary_text)

    def test_redacts_sheet_names_and_input_path_when_requested(self):
        input_dir, workbook_path, output_dir = self.build_workspace()
        secret_sheet = "sheet_" + uuid.uuid4().hex[:20]
        workbook = Workbook()
        workbook.active.title = secret_sheet
        workbook.active["A1"] = "safe"
        workbook.save(workbook_path)

        result = inspect_xlsx_readonly(
            workbook_path,
            output_dir,
            redact_sheet_names=True,
            redact_input_path=True,
        )
        inspection = read_json(result.xlsx_inspection_path)
        inspection_text = result.xlsx_inspection_path.read_text(encoding="utf-8")
        summary_text = result.xlsx_inspection_summary_path.read_text(encoding="utf-8")

        self.assertEqual(inspection["sheet_names"], ["sheet_1"])
        self.assertEqual(inspection["sheets"][0]["sheet_name"], "sheet_1")
        self.assertTrue(inspection["sheets"][0]["sheet_name_redacted"])
        self.assertFalse(inspection["sheets"][0]["raw_sheet_name_included"])
        self.assertEqual(inspection["input_workbook"]["path"], "[redacted-input-path]")
        self.assertEqual(
            inspection["input_workbook"]["file_name"], "[redacted-input-file-name]"
        )
        self.assertTrue(inspection["redaction"]["sheet_names_redacted"])
        self.assertTrue(inspection["redaction"]["input_path_redacted"])
        self.assertNotIn(secret_sheet, inspection_text)
        self.assertNotIn(secret_sheet, summary_text)
        self.assertNotIn(input_dir.as_posix(), inspection_text)
        self.assertNotIn(input_dir.as_posix(), summary_text)

    def test_dynamic_raw_sentinels_and_formula_text_do_not_leak_to_audit_artifacts(self):
        _, workbook_path, output_dir = self.build_workspace()
        secret_header = "header_" + uuid.uuid4().hex
        secret_cell = "cell_" + uuid.uuid4().hex
        secret_formula_text = "formula_" + uuid.uuid4().hex
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "safe_sheet"
        sheet["A1"] = secret_header
        sheet["A2"] = secret_cell
        sheet["B2"] = '=CONCAT("' + secret_formula_text + '","")'
        workbook.save(workbook_path)

        result = inspect_xlsx_readonly(workbook_path, output_dir)
        inspection = read_json(result.xlsx_inspection_path)
        inspection_text = result.xlsx_inspection_path.read_text(encoding="utf-8")
        summary_text = result.xlsx_inspection_summary_path.read_text(encoding="utf-8")

        self.assertTrue(inspection["sheets"][0]["formula_presence"])
        for sentinel in (secret_header, secret_cell, secret_formula_text):
            self.assertNotIn(sentinel, inspection_text)
            self.assertNotIn(sentinel, summary_text)

    def test_rejects_invalid_extension_and_invalid_xlsx_file(self):
        _, workbook_path, output_dir = self.build_workspace()
        text_path = workbook_path.with_suffix(".txt")
        text_path.write_text("not xlsx", encoding="utf-8")

        with self.assertRaises(ValueError):
            inspect_xlsx_readonly(text_path, output_dir)

        bad_xlsx = workbook_path.with_name("bad.xlsx")
        bad_xlsx.write_text("not a zip", encoding="utf-8")
        with self.assertRaises(ValueError):
            inspect_xlsx_readonly(bad_xlsx, output_dir)

    def test_rejects_damaged_truncated_workbook(self):
        _, workbook_path, output_dir = self.build_workspace()
        damaged_path = workbook_path.with_name("damaged.xlsx")
        original_bytes = workbook_path.read_bytes()
        damaged_path.write_bytes(original_bytes[: max(1, len(original_bytes) // 3)])

        with self.assertRaises(ValueError):
            inspect_xlsx_readonly(damaged_path, output_dir)

    def test_rejects_symlink_input_and_symlink_output_directory(self):
        input_dir, workbook_path, output_dir = self.build_workspace()
        symlink_workbook = input_dir / "linked.xlsx"
        symlink_output = output_dir.parent / "linked-output"
        try:
            symlink_workbook.symlink_to(workbook_path)
            symlink_output.symlink_to(output_dir, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"symlinks unavailable: {error}")

        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            inspect_xlsx_readonly(symlink_workbook, output_dir)
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            inspect_xlsx_readonly(workbook_path, symlink_output)

    def test_rejects_workbook_over_configured_large_file_guard(self):
        _, workbook_path, output_dir = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "exceeds max_workbook_bytes"):
            inspect_xlsx_readonly(
                workbook_path,
                output_dir,
                limits=XlsxReadonlyLimits(max_workbook_bytes=1),
            )

    def test_deterministic_output_for_fixture_workbook(self):
        _, workbook_path, output_dir = self.build_workspace()

        first_result = inspect_xlsx_readonly(
            workbook_path,
            output_dir,
            limits=XlsxReadonlyLimits(max_header_rows=2, max_header_columns=2),
        )
        first = read_json(first_result.xlsx_inspection_path)
        first_result.xlsx_inspection_path.unlink()
        first_result.xlsx_inspection_summary_path.unlink()
        second_result = inspect_xlsx_readonly(
            workbook_path,
            output_dir,
            limits=XlsxReadonlyLimits(max_header_rows=2, max_header_columns=2),
        )
        second = read_json(second_result.xlsx_inspection_path)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
