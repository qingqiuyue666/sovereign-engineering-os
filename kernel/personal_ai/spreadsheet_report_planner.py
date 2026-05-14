"""Deterministic non-executing spreadsheet structural report planning."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "SpreadsheetReportPlanResult",
    "build_spreadsheet_report_plan",
]

_PLANNED_SECTIONS = [
    "inspection_scope",
    "file_status_summary",
    "structure_summary",
    "detected_structure_issues",
    "unsupported_or_unreadable_files",
    "recommended_human_review",
    "forbidden_actions",
]

_STRUCTURAL_METRIC_SOURCES = [
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

_SUMMARY_METRICS = [
    "selected_artifacts",
    "inspected_files",
    "unsupported_files",
    "missing_files",
    "parse_error_files",
    "path_escape_rejected_files",
    "total_inspected_rows",
    "total_empty_cells",
    "total_ragged_rows",
]

_NON_EXECUTING_REPORT_PLAN = [
    "collect readonly inspection summary metrics",
    "organize structural issue categories",
    "prepare structural report sections",
    "require human approval before report generation",
    "preserve original input files unchanged",
    "write future report artifacts only outside input directory",
]

_FORBIDDEN_ACTIONS = [
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
]

_BOUNDARIES = [
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
]


@dataclass(frozen=True)
class SpreadsheetReportPlanResult:
    spreadsheet_readonly_inspection_path: Path
    output_report_plan_path: Path
    report_status: str
    issue_categories: list[str]
    planned_sections: list[str]
    required_human_approval: bool


def build_spreadsheet_report_plan(
    spreadsheet_readonly_inspection_path: Path,
    output_report_plan_path: Path,
) -> SpreadsheetReportPlanResult:
    inspection_path = Path(spreadsheet_readonly_inspection_path)
    output_path = Path(output_report_plan_path)

    if not inspection_path.exists():
        raise ValueError("spreadsheet_readonly_inspection_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_report_plan_path parent is missing")

    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    _validate_inspection_shape(inspection)

    files = list(inspection["files"])
    summary_inputs = _numeric_summary_inputs(inspection["summary"])
    issue_categories = _issue_categories(summary_inputs, files)
    report_status = (
        "no_inspection_data"
        if not files
        else "report_planning_ready"
    )
    planned_sections = list(_PLANNED_SECTIONS)

    plan = {
        "plan_type": "personal_ai_local_spreadsheet_report_plan",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "source_artifacts": {
            "spreadsheet_readonly_inspection": inspection_path.as_posix(),
        },
        "report_status": report_status,
        "planned_sections": planned_sections,
        "issue_categories": issue_categories,
        "structural_metric_sources": list(_STRUCTURAL_METRIC_SOURCES),
        "summary_inputs": summary_inputs,
        "non_executing_report_plan": list(_NON_EXECUTING_REPORT_PLAN),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "boundaries": list(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(output_path, plan)

    return SpreadsheetReportPlanResult(
        spreadsheet_readonly_inspection_path=inspection_path,
        output_report_plan_path=output_path,
        report_status=report_status,
        issue_categories=issue_categories,
        planned_sections=planned_sections,
        required_human_approval=True,
    )


def _validate_inspection_shape(inspection):
    if "files" not in inspection:
        raise ValueError("spreadsheet readonly inspection is missing files")
    if "summary" not in inspection:
        raise ValueError("spreadsheet readonly inspection is missing summary")
    if not isinstance(inspection["files"], list):
        raise ValueError("spreadsheet readonly inspection files is malformed")
    if not isinstance(inspection["summary"], dict):
        raise ValueError("spreadsheet readonly inspection summary is malformed")


def _numeric_summary_inputs(summary):
    numeric_summary = {}
    for metric_name in _SUMMARY_METRICS:
        if metric_name not in summary:
            raise ValueError("spreadsheet readonly inspection summary is malformed")
        value = summary[metric_name]
        if not isinstance(value, int):
            raise ValueError("spreadsheet readonly inspection summary is malformed")
        numeric_summary[metric_name] = value
    return numeric_summary


def _issue_categories(summary, files):
    categories = []
    if summary["unsupported_files"] > 0:
        categories.append("unsupported_spreadsheet_extension")
    if summary["missing_files"] > 0:
        categories.append("missing_selected_file")
    if summary["parse_error_files"] > 0:
        categories.append("parse_error")
    if summary["path_escape_rejected_files"] > 0:
        categories.append("path_escape_rejected")
    if summary["total_ragged_rows"] > 0:
        categories.append("ragged_rows_detected")
    if _any_file_metric_above_zero(files, "duplicate_header_count"):
        categories.append("duplicate_headers_detected")
    if _any_file_metric_above_zero(files, "empty_header_count"):
        categories.append("empty_headers_detected")
    if summary["total_empty_cells"] > 0:
        categories.append("empty_cells_detected")
    if any(bool(file_record.get("truncated", False)) for file_record in files):
        categories.append("truncated_inspection")
    if summary["inspected_files"] == 0:
        categories.append("no_csv_tsv_files_inspected")
    if all(
        category == "no_csv_tsv_files_inspected"
        for category in categories
    ):
        categories.append("no_structural_issues_detected")
    return categories


def _any_file_metric_above_zero(files, metric_name):
    return any(int(file_record.get(metric_name, 0)) > 0 for file_record in files)
