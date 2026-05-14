import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.spreadsheet_report_planner import (
    build_spreadsheet_report_plan,
)
from kernel.personal_ai.spreadsheet_structural_report import (
    SpreadsheetStructuralReportResult,
    build_spreadsheet_structural_report,
)


EXPECTED_JSON_KEYS = {
    "report_type",
    "authority",
    "execution_capability",
    "required_human_approval",
    "source_artifacts",
    "report_status",
    "planned_sections",
    "issue_categories",
    "summary",
    "file_status_summary",
    "structural_metrics",
    "human_review_notes",
    "forbidden_actions",
    "boundaries",
    "next_allowed_action",
}

EXPECTED_MARKDOWN_SECTIONS = [
    "# Spreadsheet Structural Report",
    "## Authority",
    "## Scope",
    "## File Status Summary",
    "## Structural Metrics",
    "## Issue Categories",
    "## Human Review Required",
    "## Forbidden Actions",
    "## Boundaries",
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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def summary(**overrides):
    values = {
        "selected_artifacts": 5,
        "inspected_files": 1,
        "unsupported_files": 1,
        "missing_files": 1,
        "parse_error_files": 1,
        "path_escape_rejected_files": 1,
        "total_inspected_rows": 4,
        "total_empty_cells": 2,
        "total_ragged_rows": 1,
    }
    values.update(overrides)
    return values


def file_record(**overrides):
    record = {
        "relative_path": "data.csv",
        "extension": ".csv",
        "status": "inspected",
        "inspected_rows": 4,
        "truncated": False,
        "column_count": 3,
        "header_present": True,
        "header_column_count": 3,
        "duplicate_header_count": 0,
        "empty_header_count": 0,
        "ragged_row_count": 0,
        "empty_cell_count": 0,
        "max_observed_columns": 3,
        "min_observed_columns": 2,
        "parse_error_type": None,
    }
    record.update(overrides)
    return record


class SpreadsheetStructuralReportTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return {
            "inspection": root / "spreadsheet_readonly_inspection.json",
            "plan": root / "spreadsheet_report_plan.json",
            "report_json": root / "spreadsheet_structural_report.json",
            "report_markdown": root / "spreadsheet_structural_report.md",
        }

    def write_inspection(self, paths, files=None, inspection_summary=None):
        paths["inspection"].write_text(
            json.dumps(
                {
                    "inspection_type": (
                        "personal_ai_local_spreadsheet_readonly_inspection"
                    ),
                    "files": files
                    if files is not None
                    else [
                        file_record(
                            ragged_row_count=1,
                            duplicate_header_count=1,
                            empty_header_count=1,
                            empty_cell_count=2,
                            truncated=True,
                        ),
                        file_record(status="unsupported_extension"),
                        file_record(status="missing"),
                        file_record(status="parse_error"),
                        file_record(status="path_escape_rejected"),
                    ],
                    "summary": inspection_summary
                    if inspection_summary is not None
                    else summary(),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def build_report(self, files=None, inspection_summary=None):
        paths = self.build_workspace()
        self.write_inspection(paths, files=files, inspection_summary=inspection_summary)
        build_spreadsheet_report_plan(paths["inspection"], paths["plan"])

        result = build_spreadsheet_structural_report(
            paths["inspection"],
            paths["plan"],
            paths["report_json"],
            paths["report_markdown"],
        )
        return result, read_json(paths["report_json"]), paths

    def test_builds_json_and_markdown_structural_reports(self):
        result, report, paths = self.build_report()
        markdown = paths["report_markdown"].read_text(encoding="utf-8")

        self.assertIsInstance(result, SpreadsheetStructuralReportResult)
        self.assertTrue(paths["report_json"].exists())
        self.assertTrue(paths["report_markdown"].exists())
        self.assertEqual(set(report), EXPECTED_JSON_KEYS)
        self.assertEqual(
            report["report_type"],
            "personal_ai_local_spreadsheet_structural_report",
        )
        for section in EXPECTED_MARKDOWN_SECTIONS:
            self.assertIn(section, markdown)

    def test_report_preserves_fixed_non_authority_review_boundary(self):
        result, report, _ = self.build_report()

        self.assertEqual(report["authority"], "non_authority")
        self.assertEqual(report["execution_capability"], "not_introduced")
        self.assertIs(report["required_human_approval"], True)
        self.assertIs(result.required_human_approval, True)
        self.assertEqual(report["next_allowed_action"], "human_review_only")
        self.assertEqual(set(report["forbidden_actions"]), EXPECTED_FORBIDDEN_ACTIONS)
        self.assertIn("copy_raw_cell_values", report["forbidden_actions"])
        self.assertIn("infer_semantic_meaning", report["forbidden_actions"])
        self.assertIn("assign_issue_severity", report["forbidden_actions"])
        self.assertEqual(set(report["boundaries"]), EXPECTED_BOUNDARIES)
        self.assertIn("no_raw_cell_value_copy", report["boundaries"])
        self.assertIn("no_issue_severity_assignment", report["boundaries"])
        self.assertIn(
            "no_business_semantic_interpretation",
            report["boundaries"],
        )

    def test_does_not_copy_raw_headers_or_cell_values(self):
        raw_files = [
            file_record(
                header_names=["RAW_HEADER_SECRET"],
                sample_values=["RAW_CELL_SECRET"],
            )
        ]

        _, _, paths = self.build_report(
            files=raw_files,
            inspection_summary=summary(
                selected_artifacts=1,
                inspected_files=1,
                unsupported_files=0,
                missing_files=0,
                parse_error_files=0,
                path_escape_rejected_files=0,
                total_inspected_rows=2,
                total_empty_cells=0,
                total_ragged_rows=0,
            ),
        )
        combined_output = (
            paths["report_json"].read_text(encoding="utf-8")
            + paths["report_markdown"].read_text(encoding="utf-8")
        )

        self.assertNotIn("RAW_HEADER_SECRET", combined_output)
        self.assertNotIn("RAW_CELL_SECRET", combined_output)

    def test_does_not_assign_severity_or_business_interpretation(self):
        _, report, paths = self.build_report()
        markdown = paths["report_markdown"].read_text(encoding="utf-8")

        self.assertNotIn("severity", report)
        self.assertNotIn("severity_level", markdown)
        self.assertNotIn("business impact", markdown)
        self.assertNotIn("semantic diagnosis", markdown)

    def test_summary_metrics_are_numeric_only(self):
        _, report, _ = self.build_report()

        self.assertEqual(set(report["summary"]), set(summary()))
        self.assertTrue(
            all(isinstance(value, int) for value in report["summary"].values())
        )

    def test_file_status_summary_counts_statuses_only(self):
        _, report, _ = self.build_report()

        self.assertEqual(
            report["file_status_summary"],
            {
                "inspected": 1,
                "unsupported_extension": 1,
                "missing": 1,
                "parse_error": 1,
                "path_escape_rejected": 1,
            },
        )
        self.assertNotIn("relative_path", report["file_status_summary"])

    def test_structural_metrics_count_files_by_metric_presence(self):
        _, report, _ = self.build_report()

        self.assertEqual(
            report["structural_metrics"],
            {
                "files_with_ragged_rows": 1,
                "files_with_duplicate_headers": 1,
                "files_with_empty_headers": 1,
                "files_with_empty_cells": 1,
                "truncated_files": 1,
            },
        )

    def test_rejects_missing_paths_and_output_parents(self):
        paths = self.build_workspace()
        self.write_inspection(paths)
        build_spreadsheet_report_plan(paths["inspection"], paths["plan"])

        missing = paths["report_json"].parent / "missing.json"
        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                missing,
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"],
            )
        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                missing,
                paths["report_json"],
                paths["report_markdown"],
            )
        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"].parent / "missing" / "report.json",
                paths["report_markdown"],
            )
        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"].parent / "missing" / "report.md",
            )

    def test_rejects_malformed_inspection_missing_files(self):
        paths = self.build_workspace()
        paths["inspection"].write_text(
            json.dumps({"summary": summary()}, sort_keys=True),
            encoding="utf-8",
        )
        paths["plan"].write_text(
            json.dumps(
                {
                    "issue_categories": [],
                    "planned_sections": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"],
            )

    def test_rejects_malformed_inspection_missing_summary(self):
        paths = self.build_workspace()
        paths["inspection"].write_text(
            json.dumps({"files": [file_record()]}, sort_keys=True),
            encoding="utf-8",
        )
        paths["plan"].write_text(
            json.dumps(
                {
                    "issue_categories": [],
                    "planned_sections": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"],
            )

    def test_rejects_malformed_report_plan_missing_issue_categories(self):
        paths = self.build_workspace()
        self.write_inspection(paths)
        paths["plan"].write_text(
            json.dumps({"planned_sections": []}, sort_keys=True),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"],
            )

    def test_rejects_malformed_report_plan_missing_planned_sections(self):
        paths = self.build_workspace()
        self.write_inspection(paths)
        paths["plan"].write_text(
            json.dumps({"issue_categories": []}, sort_keys=True),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_spreadsheet_structural_report(
                paths["inspection"],
                paths["plan"],
                paths["report_json"],
                paths["report_markdown"],
            )

    def test_deterministic_json_and_markdown_output(self):
        paths = self.build_workspace()
        self.write_inspection(paths)
        build_spreadsheet_report_plan(paths["inspection"], paths["plan"])

        build_spreadsheet_structural_report(
            paths["inspection"],
            paths["plan"],
            paths["report_json"],
            paths["report_markdown"],
        )
        first_json = paths["report_json"].read_text(encoding="utf-8")
        first_markdown = paths["report_markdown"].read_text(encoding="utf-8")
        build_spreadsheet_structural_report(
            paths["inspection"],
            paths["plan"],
            paths["report_json"],
            paths["report_markdown"],
        )
        second_json = paths["report_json"].read_text(encoding="utf-8")
        second_markdown = paths["report_markdown"].read_text(encoding="utf-8")

        self.assertEqual(first_json, second_json)
        self.assertEqual(first_markdown, second_markdown)


if __name__ == "__main__":
    unittest.main()
