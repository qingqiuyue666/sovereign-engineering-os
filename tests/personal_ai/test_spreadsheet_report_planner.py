import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.spreadsheet_report_planner import (
    SpreadsheetReportPlanResult,
    build_spreadsheet_report_plan,
)


EXPECTED_KEYS = {
    "plan_type",
    "authority",
    "execution_capability",
    "required_human_approval",
    "source_artifacts",
    "report_status",
    "planned_sections",
    "issue_categories",
    "structural_metric_sources",
    "summary_inputs",
    "non_executing_report_plan",
    "forbidden_actions",
    "boundaries",
    "next_allowed_action",
}

EXPECTED_PLANNED_SECTIONS = [
    "inspection_scope",
    "file_status_summary",
    "structure_summary",
    "detected_structure_issues",
    "unsupported_or_unreadable_files",
    "recommended_human_review",
    "forbidden_actions",
]

EXPECTED_FORBIDDEN_ACTIONS = {
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "write_spreadsheet_outputs",
    "copy_raw_cell_values",
    "infer_semantic_meaning",
    "assign_issue_severity",
    "call_network",
    "call_ai_api",
    "run_subprocess",
    "control_external_tools",
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
    "no_raw_cell_value_copy",
    "no_spreadsheet_output_write",
    "no_issue_severity_assignment",
    "no_business_semantic_interpretation",
    "no_input_file_mutation",
    "no_destructive_actions",
}

EXPECTED_STRUCTURAL_METRIC_SOURCES = [
    "selected_artifacts",
    "inspected_files",
    "unsupported_files",
    "missing_files",
    "parse_error_files",
    "path_escape_rejected_files",
    "total_inspected_rows",
    "total_empty_cells",
    "total_ragged_rows",
    "duplicate_header_count",
    "empty_header_count",
    "truncated",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def base_summary(**overrides):
    summary = {
        "selected_artifacts": 1,
        "inspected_files": 1,
        "unsupported_files": 0,
        "missing_files": 0,
        "parse_error_files": 0,
        "path_escape_rejected_files": 0,
        "total_inspected_rows": 2,
        "total_empty_cells": 0,
        "total_ragged_rows": 0,
    }
    summary.update(overrides)
    return summary


def file_record(**overrides):
    record = {
        "relative_path": "data.csv",
        "extension": ".csv",
        "status": "inspected",
        "inspected_rows": 2,
        "truncated": False,
        "column_count": 2,
        "header_present": True,
        "header_column_count": 2,
        "duplicate_header_count": 0,
        "empty_header_count": 0,
        "ragged_row_count": 0,
        "empty_cell_count": 0,
        "max_observed_columns": 2,
        "min_observed_columns": 2,
        "parse_error_type": None,
    }
    record.update(overrides)
    return record


class SpreadsheetReportPlannerTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return (
            root / "spreadsheet_readonly_inspection.json",
            root / "spreadsheet_report_plan.json",
        )

    def write_inspection(self, files, summary):
        inspection_path, output_path = self.build_workspace()
        inspection_path.write_text(
            json.dumps(
                {
                    "inspection_type": (
                        "personal_ai_local_spreadsheet_readonly_inspection"
                    ),
                    "files": list(files),
                    "summary": dict(summary),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return inspection_path, output_path

    def build_plan(self, files=None, summary=None):
        inspection_path, output_path = self.write_inspection(
            files if files is not None else [file_record()],
            summary if summary is not None else base_summary(),
        )
        result = build_spreadsheet_report_plan(
            inspection_path,
            output_path,
        )
        return result, read_json(output_path), output_path

    def test_builds_spreadsheet_report_plan_from_readonly_inspection(self):
        result, plan, output_path = self.build_plan()

        self.assertIsInstance(result, SpreadsheetReportPlanResult)
        self.assertTrue(output_path.exists())
        self.assertEqual(set(plan), EXPECTED_KEYS)
        self.assertEqual(
            plan["plan_type"],
            "personal_ai_local_spreadsheet_report_plan",
        )
        self.assertEqual(result.report_status, "report_planning_ready")
        self.assertEqual(plan["report_status"], "report_planning_ready")
        self.assertEqual(plan["planned_sections"], EXPECTED_PLANNED_SECTIONS)
        self.assertEqual(
            plan["structural_metric_sources"],
            EXPECTED_STRUCTURAL_METRIC_SOURCES,
        )
        self.assertEqual(plan["summary_inputs"], base_summary())

    def test_writes_fixed_non_authority_human_review_boundary(self):
        result, plan, _ = self.build_plan()

        self.assertEqual(plan["authority"], "non_authority")
        self.assertEqual(plan["execution_capability"], "not_introduced")
        self.assertIs(plan["required_human_approval"], True)
        self.assertIs(result.required_human_approval, True)
        self.assertEqual(plan["next_allowed_action"], "human_review_only")
        self.assertEqual(set(plan["forbidden_actions"]), EXPECTED_FORBIDDEN_ACTIONS)
        self.assertIn("infer_semantic_meaning", plan["forbidden_actions"])
        self.assertIn("assign_issue_severity", plan["forbidden_actions"])
        self.assertEqual(set(plan["boundaries"]), EXPECTED_BOUNDARIES)
        self.assertIn("no_issue_severity_assignment", plan["boundaries"])
        self.assertIn(
            "no_business_semantic_interpretation",
            plan["boundaries"],
        )

    def test_no_inspection_data_status_when_files_list_is_empty(self):
        _, plan, _ = self.build_plan(
            files=[],
            summary=base_summary(
                selected_artifacts=0,
                inspected_files=0,
                total_inspected_rows=0,
            ),
        )

        self.assertEqual(plan["report_status"], "no_inspection_data")
        self.assertEqual(
            plan["issue_categories"],
            ["no_csv_tsv_files_inspected", "no_structural_issues_detected"],
        )

    def test_issue_category_rules_are_deterministic(self):
        cases = [
            (
                "unsupported_spreadsheet_extension",
                [file_record(status="unsupported_extension")],
                base_summary(unsupported_files=1),
            ),
            (
                "missing_selected_file",
                [file_record(status="missing")],
                base_summary(missing_files=1),
            ),
            (
                "parse_error",
                [file_record(status="parse_error")],
                base_summary(parse_error_files=1),
            ),
            (
                "path_escape_rejected",
                [file_record(status="path_escape_rejected")],
                base_summary(path_escape_rejected_files=1),
            ),
            (
                "ragged_rows_detected",
                [file_record(ragged_row_count=1)],
                base_summary(total_ragged_rows=1),
            ),
            (
                "empty_cells_detected",
                [file_record(empty_cell_count=1)],
                base_summary(total_empty_cells=1),
            ),
            (
                "duplicate_headers_detected",
                [file_record(duplicate_header_count=1)],
                base_summary(),
            ),
            (
                "empty_headers_detected",
                [file_record(empty_header_count=1)],
                base_summary(),
            ),
            (
                "truncated_inspection",
                [file_record(truncated=True)],
                base_summary(),
            ),
            (
                "no_csv_tsv_files_inspected",
                [],
                base_summary(
                    selected_artifacts=0,
                    inspected_files=0,
                    total_inspected_rows=0,
                ),
            ),
            (
                "no_structural_issues_detected",
                [file_record()],
                base_summary(),
            ),
        ]

        for expected_issue, files, summary in cases:
            with self.subTest(expected_issue=expected_issue):
                _, plan, _ = self.build_plan(files=files, summary=summary)
                self.assertIn(expected_issue, plan["issue_categories"])

    def test_plan_does_not_assign_severity_or_copy_raw_values(self):
        raw_files = [
            file_record(
                header_names=["RAW_HEADER_SECRET"],
                sample_values=["RAW_CELL_SECRET"],
            )
        ]

        _, _, output_path = self.build_plan(files=raw_files)
        output_text = output_path.read_text(encoding="utf-8")
        plan = read_json(output_path)

        self.assertNotIn("severity", plan)
        self.assertNotIn("RAW_HEADER_SECRET", output_text)
        self.assertNotIn("RAW_CELL_SECRET", output_text)

    def test_rejects_missing_inspection_path(self):
        _, output_path = self.build_workspace()

        with self.assertRaises(ValueError):
            build_spreadsheet_report_plan(
                output_path.parent / "missing.json",
                output_path,
            )

    def test_rejects_missing_output_parent(self):
        inspection_path, output_path = self.write_inspection(
            [file_record()],
            base_summary(),
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_report_plan(
                inspection_path,
                output_path.parent / "missing" / "plan.json",
            )

    def test_rejects_malformed_inspection_missing_files(self):
        inspection_path, output_path = self.build_workspace()
        inspection_path.write_text(
            json.dumps({"summary": base_summary()}, sort_keys=True),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_report_plan(inspection_path, output_path)

    def test_rejects_malformed_inspection_missing_summary(self):
        inspection_path, output_path = self.build_workspace()
        inspection_path.write_text(
            json.dumps({"files": [file_record()]}, sort_keys=True),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_report_plan(inspection_path, output_path)

    def test_deterministic_output(self):
        inspection_path, output_path = self.write_inspection(
            [file_record()],
            base_summary(),
        )

        build_spreadsheet_report_plan(inspection_path, output_path)
        first_output = output_path.read_text(encoding="utf-8")
        build_spreadsheet_report_plan(inspection_path, output_path)
        second_output = output_path.read_text(encoding="utf-8")

        self.assertEqual(first_output, second_output)


if __name__ == "__main__":
    unittest.main()
