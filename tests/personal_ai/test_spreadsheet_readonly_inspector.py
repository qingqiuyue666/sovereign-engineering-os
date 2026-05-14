import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.spreadsheet_readonly_inspector import (
    SpreadsheetReadonlyInspectionResult,
    build_spreadsheet_readonly_inspection,
)


EXPECTED_KEYS = {
    "inspection_type",
    "authority",
    "execution_capability",
    "required_human_approval",
    "source_artifacts",
    "max_rows_per_file",
    "supported_extensions",
    "unsupported_extensions",
    "files",
    "summary",
    "forbidden_actions",
    "boundaries",
    "next_allowed_action",
}

EXPECTED_FILE_KEYS = {
    "relative_path",
    "extension",
    "status",
    "inspected_rows",
    "truncated",
    "column_count",
    "header_present",
    "header_column_count",
    "duplicate_header_count",
    "empty_header_count",
    "ragged_row_count",
    "empty_cell_count",
    "max_observed_columns",
    "min_observed_columns",
    "parse_error_type",
}

EXPECTED_BOUNDARIES = {
    "no_runtime_authority",
    "no_execution_capability",
    "no_external_tool_control",
    "no_network",
    "no_api_calls",
    "no_subprocess",
    "no_adapter_implementation",
    "no_ai_classification",
    "no_semantic_classification",
    "no_spreadsheet_output_write",
    "no_input_file_mutation",
    "no_raw_cell_value_copy",
    "no_destructive_actions",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def selected_artifact(relative_path, extension):
    return {
        "relative_path": relative_path,
        "extension": extension,
        "size_bytes": 10,
        "sha256": "0" * 64,
        "modified_time_ns": 100,
        "category": "spreadsheet",
    }


class SpreadsheetReadonlyInspectorTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        return input_dir, output_dir / "spreadsheet_processor_plan.json", (
            output_dir / "spreadsheet_readonly_inspection.json"
        )

    def write_plan(self, plan_path, artifacts):
        plan_path.write_text(
            json.dumps(
                {
                    "plan_type": "personal_ai_local_spreadsheet_processor_plan",
                    "selected_spreadsheet_artifacts": list(artifacts),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def build_inspection(self, files, *, max_rows_per_file=1000):
        input_dir, plan_path, output_path = self.build_workspace()
        for relative_path, content in files.items():
            path = input_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.write_plan(
            plan_path,
            [
                selected_artifact(relative_path, Path(relative_path).suffix)
                for relative_path in files
            ],
        )

        result = build_spreadsheet_readonly_inspection(
            input_dir,
            plan_path,
            output_path,
            max_rows_per_file=max_rows_per_file,
        )
        return result, read_json(output_path), output_path

    def test_inspects_csv_file_read_only_and_writes_json(self):
        result, inspection, output_path = self.build_inspection(
            {"data.csv": "a,b\n1,2\n"}
        )

        self.assertIsInstance(result, SpreadsheetReadonlyInspectionResult)
        self.assertTrue(output_path.exists())
        self.assertEqual(set(inspection), EXPECTED_KEYS)
        self.assertEqual(set(inspection["files"][0]), EXPECTED_FILE_KEYS)
        self.assertEqual(inspection["files"][0]["status"], "inspected")
        self.assertEqual(result.inspected_files, 1)

    def test_inspects_tsv_file_read_only(self):
        _, inspection, _ = self.build_inspection({"data.tsv": "a\tb\n1\t2\n"})

        file_record = inspection["files"][0]
        self.assertEqual(file_record["extension"], ".tsv")
        self.assertEqual(file_record["status"], "inspected")
        self.assertEqual(file_record["column_count"], 2)

    def test_does_not_include_raw_header_names_or_raw_cell_values(self):
        _, _, output_path = self.build_inspection(
            {
                "data.csv": (
                    "RAW_HEADER_SECRET,other\n"
                    "RAW_CELL_SECRET,2\n"
                )
            }
        )

        output_text = output_path.read_text(encoding="utf-8")
        self.assertNotIn("RAW_HEADER_SECRET", output_text)
        self.assertNotIn("RAW_CELL_SECRET", output_text)

    def test_counts_basic_row_and_header_metrics(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        file_record = inspection["files"][0]
        self.assertEqual(file_record["inspected_rows"], 2)
        self.assertEqual(file_record["column_count"], 2)
        self.assertIs(file_record["header_present"], True)
        self.assertEqual(file_record["header_column_count"], 2)

    def test_counts_duplicate_header_count_without_emitting_header_values(self):
        _, inspection, output_path = self.build_inspection(
            {
                "data.csv": (
                    "DUPLICATE_HEADER_SECRET,DUPLICATE_HEADER_SECRET,x\n"
                    "1,2,3\n"
                )
            }
        )

        self.assertEqual(inspection["files"][0]["duplicate_header_count"], 1)
        self.assertNotIn(
            "DUPLICATE_HEADER_SECRET",
            output_path.read_text(encoding="utf-8"),
        )

    def test_counts_empty_header_count(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,,c\n1,2,3\n"})

        self.assertEqual(inspection["files"][0]["empty_header_count"], 1)

    def test_counts_empty_cell_count(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,,c\n1,,3\n,,\n"})

        self.assertEqual(inspection["files"][0]["empty_cell_count"], 5)

    def test_counts_ragged_row_count(self):
        _, inspection, _ = self.build_inspection(
            {"data.csv": "a,b,c\n1,2\n3,4,5,6\n"}
        )

        self.assertEqual(inspection["files"][0]["ragged_row_count"], 2)

    def test_computes_max_and_min_observed_columns(self):
        _, inspection, _ = self.build_inspection(
            {"data.csv": "a,b,c\n1,2\n3,4,5,6\n"}
        )

        file_record = inspection["files"][0]
        self.assertEqual(file_record["max_observed_columns"], 4)
        self.assertEqual(file_record["min_observed_columns"], 2)

    def test_truncates_at_max_rows_per_file(self):
        _, inspection, _ = self.build_inspection(
            {"data.csv": "a,b\n1,2\n3,4\n"},
            max_rows_per_file=2,
        )

        file_record = inspection["files"][0]
        self.assertEqual(file_record["inspected_rows"], 2)
        self.assertIs(file_record["truncated"], True)

    def test_records_unsupported_spreadsheet_extensions_without_opening(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(
            plan_path,
            [
                selected_artifact("book.xlsx", ".xlsx"),
                selected_artifact("macro.xlsm", ".xlsm"),
                selected_artifact("legacy.xls", ".xls"),
            ],
        )

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)
        inspection = read_json(output_path)

        self.assertEqual(
            [file_record["status"] for file_record in inspection["files"]],
            [
                "unsupported_extension",
                "unsupported_extension",
                "unsupported_extension",
            ],
        )
        self.assertEqual(inspection["summary"]["unsupported_files"], 3)

    def test_records_missing_selected_file_as_missing(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(plan_path, [selected_artifact("missing.csv", ".csv")])

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)

        inspection = read_json(output_path)
        self.assertEqual(inspection["files"][0]["status"], "missing")
        self.assertEqual(inspection["summary"]["missing_files"], 1)

    def test_rejects_path_escape_selected_artifact(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(plan_path, [selected_artifact("../escape.csv", ".csv")])

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)

        inspection = read_json(output_path)
        self.assertEqual(
            inspection["files"][0]["status"],
            "path_escape_rejected",
        )
        self.assertEqual(
            inspection["summary"]["path_escape_rejected_files"],
            1,
        )

    def test_records_unicode_decode_error_without_raw_content(self):
        input_dir, plan_path, output_path = self.build_workspace()
        (input_dir / "bad.csv").write_bytes(b"\xff\xfeSECRET_BYTES")
        self.write_plan(plan_path, [selected_artifact("bad.csv", ".csv")])

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)

        inspection = read_json(output_path)
        self.assertEqual(inspection["files"][0]["status"], "parse_error")
        self.assertEqual(
            inspection["files"][0]["parse_error_type"],
            "UnicodeDecodeError",
        )
        self.assertNotIn("SECRET_BYTES", output_path.read_text(encoding="utf-8"))

    def test_rejects_missing_input_dir(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(plan_path, [])

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_dir / "missing",
                plan_path,
                output_path,
            )

    def test_rejects_non_directory_input_dir(self):
        input_dir, plan_path, output_path = self.build_workspace()
        input_file = input_dir / "not-dir.txt"
        input_file.write_text("x", encoding="utf-8")
        self.write_plan(plan_path, [])

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_file,
                plan_path,
                output_path,
            )

    def test_rejects_missing_spreadsheet_processor_plan_path(self):
        input_dir, _, output_path = self.build_workspace()

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_dir,
                input_dir / "missing-plan.json",
                output_path,
            )

    def test_rejects_missing_output_parent(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(plan_path, [])

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_dir,
                plan_path,
                output_path.parent / "missing" / output_path.name,
            )

    def test_rejects_max_rows_per_file_less_than_or_equal_to_zero(self):
        input_dir, plan_path, output_path = self.build_workspace()
        self.write_plan(plan_path, [])

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_dir,
                plan_path,
                output_path,
                max_rows_per_file=0,
            )

    def test_rejects_malformed_plan_missing_selected_artifacts(self):
        input_dir, plan_path, output_path = self.build_workspace()
        plan_path.write_text(json.dumps({"plan_type": "bad"}), encoding="utf-8")

        with self.assertRaises(ValueError):
            build_spreadsheet_readonly_inspection(
                input_dir,
                plan_path,
                output_path,
            )

    def test_writes_non_authority(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertEqual(inspection["authority"], "non_authority")

    def test_writes_execution_capability_not_introduced(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertEqual(inspection["execution_capability"], "not_introduced")

    def test_writes_required_human_approval_true(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertIs(inspection["required_human_approval"], True)

    def test_writes_next_allowed_action_human_review_only(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertEqual(inspection["next_allowed_action"], "human_review_only")

    def test_writes_required_forbidden_actions(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertIn(
            "copy_raw_cell_values",
            inspection["forbidden_actions"],
        )
        self.assertIn(
            "write_spreadsheet_outputs",
            inspection["forbidden_actions"],
        )

    def test_writes_all_required_boundaries(self):
        _, inspection, _ = self.build_inspection({"data.csv": "a,b\n1,2\n"})

        self.assertEqual(set(inspection["boundaries"]), EXPECTED_BOUNDARIES)
        self.assertIn("no_raw_cell_value_copy", inspection["boundaries"])
        self.assertIn("no_spreadsheet_output_write", inspection["boundaries"])

    def test_produces_deterministic_output(self):
        input_dir, plan_path, output_path = self.build_workspace()
        (input_dir / "data.csv").write_text("b,a\n2,1\n", encoding="utf-8")
        self.write_plan(plan_path, [selected_artifact("data.csv", ".csv")])
        second_output_path = output_path.with_name("second.json")

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)
        build_spreadsheet_readonly_inspection(
            input_dir,
            plan_path,
            second_output_path,
        )

        self.assertEqual(
            output_path.read_text(encoding="utf-8"),
            second_output_path.read_text(encoding="utf-8"),
        )

    def test_does_not_modify_input_files(self):
        input_dir, plan_path, output_path = self.build_workspace()
        data_path = input_dir / "data.csv"
        data_path.write_text("a,b\n1,2\n", encoding="utf-8")
        before_bytes = data_path.read_bytes()
        before_mtime = data_path.stat().st_mtime_ns
        self.write_plan(plan_path, [selected_artifact("data.csv", ".csv")])

        build_spreadsheet_readonly_inspection(input_dir, plan_path, output_path)

        self.assertEqual(data_path.read_bytes(), before_bytes)
        self.assertEqual(data_path.stat().st_mtime_ns, before_mtime)
        self.assertTrue(data_path.exists())


if __name__ == "__main__":
    unittest.main()
