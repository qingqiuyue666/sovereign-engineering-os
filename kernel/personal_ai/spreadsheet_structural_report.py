"""Deterministic spreadsheet structural reports from readonly metrics."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "SpreadsheetStructuralReportResult",
    "build_spreadsheet_structural_report",
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

_KNOWN_STATUSES = [
    "inspected",
    "unsupported_extension",
    "missing",
    "parse_error",
    "path_escape_rejected",
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
class SpreadsheetStructuralReportResult:
    spreadsheet_readonly_inspection_path: Path
    spreadsheet_report_plan_path: Path
    output_report_json_path: Path
    output_report_markdown_path: Path
    report_status: str
    issue_categories: list[str]
    required_human_approval: bool


def build_spreadsheet_structural_report(
    spreadsheet_readonly_inspection_path: Path,
    spreadsheet_report_plan_path: Path,
    output_report_json_path: Path,
    output_report_markdown_path: Path,
) -> SpreadsheetStructuralReportResult:
    inspection_path = Path(spreadsheet_readonly_inspection_path)
    plan_path = Path(spreadsheet_report_plan_path)
    json_path = Path(output_report_json_path)
    markdown_path = Path(output_report_markdown_path)

    if not inspection_path.exists():
        raise ValueError("spreadsheet_readonly_inspection_path is missing")
    if not plan_path.exists():
        raise ValueError("spreadsheet_report_plan_path is missing")
    if not json_path.parent.exists() or not json_path.parent.is_dir():
        raise ValueError("output_report_json_path parent is missing")
    if not markdown_path.parent.exists() or not markdown_path.parent.is_dir():
        raise ValueError("output_report_markdown_path parent is missing")

    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    _validate_inspection_shape(inspection)
    _validate_plan_shape(plan)

    files = list(inspection["files"])
    summary = _numeric_summary(inspection["summary"])
    file_status_summary = _file_status_summary(files)
    structural_metrics = _structural_metrics(files)
    issue_categories = list(plan["issue_categories"])
    planned_sections = list(plan["planned_sections"])
    report_status = str(plan.get("report_status", "report_planning_ready"))

    report = {
        "report_type": "personal_ai_local_spreadsheet_structural_report",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "source_artifacts": {
            "spreadsheet_readonly_inspection": inspection_path.as_posix(),
            "spreadsheet_report_plan": plan_path.as_posix(),
        },
        "report_status": report_status,
        "planned_sections": planned_sections,
        "issue_categories": issue_categories,
        "summary": summary,
        "file_status_summary": file_status_summary,
        "structural_metrics": structural_metrics,
        "human_review_notes": [
            "human_review_only",
            "review structural metrics before any follow-up action",
            "do not treat this report as authorization to modify files",
        ],
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "boundaries": list(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(json_path, report)
    write_markdown_atomically(
        markdown_path,
        _render_markdown_report(
            report_status,
            issue_categories,
            summary,
            file_status_summary,
            structural_metrics,
        ),
    )

    return SpreadsheetStructuralReportResult(
        spreadsheet_readonly_inspection_path=inspection_path,
        spreadsheet_report_plan_path=plan_path,
        output_report_json_path=json_path,
        output_report_markdown_path=markdown_path,
        report_status=report_status,
        issue_categories=issue_categories,
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


def _validate_plan_shape(plan):
    if "issue_categories" not in plan:
        raise ValueError("spreadsheet report plan is missing issue_categories")
    if "planned_sections" not in plan:
        raise ValueError("spreadsheet report plan is missing planned_sections")
    if not isinstance(plan["issue_categories"], list):
        raise ValueError("spreadsheet report plan issue_categories is malformed")
    if not isinstance(plan["planned_sections"], list):
        raise ValueError("spreadsheet report plan planned_sections is malformed")


def _numeric_summary(summary):
    numeric_summary = {}
    for metric_name in _SUMMARY_METRICS:
        if metric_name not in summary:
            raise ValueError("spreadsheet readonly inspection summary is malformed")
        value = summary[metric_name]
        if not isinstance(value, int):
            raise ValueError("spreadsheet readonly inspection summary is malformed")
        numeric_summary[metric_name] = value
    return numeric_summary


def _file_status_summary(files):
    status_counts = {
        status: 0
        for status in _KNOWN_STATUSES
    }
    for file_record in files:
        status = str(file_record.get("status", ""))
        status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts


def _structural_metrics(files):
    return {
        "files_with_ragged_rows": _count_file_metric(files, "ragged_row_count"),
        "files_with_duplicate_headers": _count_file_metric(
            files,
            "duplicate_header_count",
        ),
        "files_with_empty_headers": _count_file_metric(
            files,
            "empty_header_count",
        ),
        "files_with_empty_cells": _count_file_metric(
            files,
            "empty_cell_count",
        ),
        "truncated_files": sum(
            1 for file_record in files if bool(file_record.get("truncated", False))
        ),
    }


def _count_file_metric(files, metric_name):
    return sum(
        1
        for file_record in files
        if int(file_record.get(metric_name, 0)) > 0
    )


def _render_markdown_report(
    report_status,
    issue_categories,
    summary,
    file_status_summary,
    structural_metrics,
):
    lines = [
        "# Spreadsheet Structural Report",
        "",
        "## Authority",
        "",
        "- authority: non_authority",
        "- execution capability: not_introduced",
        "- required human approval: true",
        "- next allowed action: human_review_only",
        "",
        "## Scope",
        "",
        "- source: spreadsheet readonly inspection metrics",
        "- report status: " + report_status,
        "- raw header names copied: false",
        "- raw cell values copied: false",
        "",
        "## File Status Summary",
        "",
    ]
    for status in sorted(file_status_summary):
        lines.append(f"- {status}: {file_status_summary[status]}")

    lines.extend(["", "## Structural Metrics", ""])
    for metric_name in sorted(structural_metrics):
        lines.append(f"- {metric_name}: {structural_metrics[metric_name]}")

    lines.extend(["", "## Issue Categories", ""])
    if issue_categories:
        for issue_category in issue_categories:
            lines.append(f"- {issue_category}")
    else:
        lines.append("- none")

    lines.extend(["", "## Human Review Required", ""])
    for metric_name in _SUMMARY_METRICS:
        lines.append(f"- {metric_name}: {summary[metric_name]}")
    lines.append("- approval gate: human_review_only")

    lines.extend(["", "## Forbidden Actions", ""])
    for action in _FORBIDDEN_ACTIONS:
        lines.append(f"- {action}")

    lines.extend(["", "## Boundaries", ""])
    for boundary in _BOUNDARIES:
        lines.append(f"- {boundary}")

    lines.append("")
    return "\n".join(lines)
