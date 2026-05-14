"""Deterministic read-only CSV/TSV spreadsheet inspection artifacts."""

from dataclasses import dataclass
from pathlib import Path
import csv
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "SpreadsheetReadonlyInspectionResult",
    "build_spreadsheet_readonly_inspection",
]

_SUPPORTED_EXTENSIONS = (".csv", ".tsv")
_UNSUPPORTED_EXTENSIONS = (".xlsx", ".xlsm", ".xls")

_FORBIDDEN_ACTIONS = [
    "modify_input_files",
    "delete_input_files",
    "move_input_files",
    "rename_input_files",
    "execute_files",
    "write_spreadsheet_outputs",
    "copy_raw_cell_values",
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
    "no_spreadsheet_output_write",
    "no_input_file_mutation",
    "no_raw_cell_value_copy",
    "no_destructive_actions",
]


@dataclass(frozen=True)
class SpreadsheetReadonlyInspectionResult:
    input_dir: Path
    spreadsheet_processor_plan_path: Path
    output_inspection_path: Path
    selected_artifacts: int
    inspected_files: int
    unsupported_files: int
    missing_files: int
    parse_error_files: int
    path_escape_rejected_files: int
    total_inspected_rows: int
    required_human_approval: bool


def build_spreadsheet_readonly_inspection(
    input_dir: Path,
    spreadsheet_processor_plan_path: Path,
    output_inspection_path: Path,
    *,
    max_rows_per_file: int = 1000,
) -> SpreadsheetReadonlyInspectionResult:
    input_path = Path(input_dir)
    plan_path = Path(spreadsheet_processor_plan_path)
    output_path = Path(output_inspection_path)

    _validate_inputs(input_path, plan_path, output_path, max_rows_per_file)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if "selected_spreadsheet_artifacts" not in plan:
        raise ValueError(
            "spreadsheet plan is missing selected_spreadsheet_artifacts"
        )
    selected_artifacts = plan["selected_spreadsheet_artifacts"]
    if not isinstance(selected_artifacts, list):
        raise ValueError(
            "spreadsheet plan selected_spreadsheet_artifacts is malformed"
        )

    files = [
        _inspect_selected_artifact(input_path, artifact, max_rows_per_file)
        for artifact in selected_artifacts
    ]
    summary = _build_summary(len(selected_artifacts), files)

    inspection = {
        "inspection_type": "personal_ai_local_spreadsheet_readonly_inspection",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "source_artifacts": {
            "input_dir": input_path.as_posix(),
            "spreadsheet_processor_plan": plan_path.as_posix(),
        },
        "max_rows_per_file": max_rows_per_file,
        "supported_extensions": list(_SUPPORTED_EXTENSIONS),
        "unsupported_extensions": list(_UNSUPPORTED_EXTENSIONS),
        "files": files,
        "summary": summary,
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "boundaries": list(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(output_path, inspection)

    return SpreadsheetReadonlyInspectionResult(
        input_dir=input_path,
        spreadsheet_processor_plan_path=plan_path,
        output_inspection_path=output_path,
        selected_artifacts=summary["selected_artifacts"],
        inspected_files=summary["inspected_files"],
        unsupported_files=summary["unsupported_files"],
        missing_files=summary["missing_files"],
        parse_error_files=summary["parse_error_files"],
        path_escape_rejected_files=summary["path_escape_rejected_files"],
        total_inspected_rows=summary["total_inspected_rows"],
        required_human_approval=True,
    )


def _validate_inputs(
    input_path,
    plan_path,
    output_path,
    max_rows_per_file,
):
    if not input_path.exists():
        raise ValueError("input_dir is missing")
    if not input_path.is_dir():
        raise ValueError("input_dir is not a directory")
    if not plan_path.exists():
        raise ValueError("spreadsheet_processor_plan_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_inspection_path parent is missing")
    if max_rows_per_file <= 0:
        raise ValueError("max_rows_per_file must be greater than zero")


def _inspect_selected_artifact(input_path, artifact, max_rows_per_file):
    relative_path = str(artifact.get("relative_path", ""))
    extension = str(artifact.get("extension", "")).lower()
    file_path = input_path / relative_path

    if _path_escapes(file_path, input_path):
        return _file_record(
            relative_path=relative_path,
            extension=extension,
            status="path_escape_rejected",
        )

    if extension in _UNSUPPORTED_EXTENSIONS:
        return _file_record(
            relative_path=relative_path,
            extension=extension,
            status="unsupported_extension",
        )

    if extension not in _SUPPORTED_EXTENSIONS:
        return _file_record(
            relative_path=relative_path,
            extension=extension,
            status="unsupported_extension",
        )

    if not file_path.exists():
        return _file_record(
            relative_path=relative_path,
            extension=extension,
            status="missing",
        )

    return _inspect_csv_tsv_file(
        file_path,
        relative_path,
        extension,
        max_rows_per_file,
    )


def _path_escapes(file_path, input_path):
    resolved_file = file_path.resolve(strict=False)
    resolved_input = input_path.resolve(strict=True)
    try:
        resolved_file.relative_to(resolved_input)
    except ValueError:
        return True
    return False


def _inspect_csv_tsv_file(
    file_path,
    relative_path,
    extension,
    max_rows_per_file,
):
    delimiter = "," if extension == ".csv" else "\t"
    record = _file_record(
        relative_path=relative_path,
        extension=extension,
        status="inspected",
    )
    observed_columns = []
    header = None

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as input_file:
            reader = csv.reader(input_file, delimiter=delimiter, strict=True)
            for row in reader:
                if header is None:
                    header = list(row)
                    _record_header_metrics(record, header)
                else:
                    _record_data_row_metrics(record, row)
                observed_columns.append(len(row))
                record["inspected_rows"] += 1
                if record["inspected_rows"] >= max_rows_per_file:
                    record["truncated"] = True
                    break
    except FileNotFoundError:
        return _file_record(
            relative_path=relative_path,
            extension=extension,
            status="missing",
        )
    except (UnicodeDecodeError, csv.Error) as error:
        record["status"] = "parse_error"
        record["parse_error_type"] = error.__class__.__name__

    _finalize_column_metrics(record, observed_columns)
    return record


def _record_header_metrics(record, header):
    record["header_present"] = True
    record["header_column_count"] = len(header)
    record["empty_header_count"] = sum(1 for cell in header if cell == "")
    seen = set()
    duplicate_count = 0
    for cell in header:
        if cell in seen:
            duplicate_count += 1
        else:
            seen.add(cell)
    record["duplicate_header_count"] = duplicate_count
    record["empty_cell_count"] += sum(1 for cell in header if cell == "")


def _record_data_row_metrics(record, row):
    record["empty_cell_count"] += sum(1 for cell in row if cell == "")
    if len(row) != record["header_column_count"]:
        record["ragged_row_count"] += 1


def _finalize_column_metrics(record, observed_columns):
    if observed_columns:
        record["max_observed_columns"] = max(observed_columns)
        record["min_observed_columns"] = min(observed_columns)
    else:
        record["max_observed_columns"] = 0
        record["min_observed_columns"] = 0

    if record["header_present"]:
        record["column_count"] = record["header_column_count"]
    else:
        record["column_count"] = record["max_observed_columns"]


def _file_record(
    *,
    relative_path,
    extension,
    status,
):
    return {
        "relative_path": relative_path,
        "extension": extension,
        "status": status,
        "inspected_rows": 0,
        "truncated": False,
        "column_count": 0,
        "header_present": False,
        "header_column_count": 0,
        "duplicate_header_count": 0,
        "empty_header_count": 0,
        "ragged_row_count": 0,
        "empty_cell_count": 0,
        "max_observed_columns": 0,
        "min_observed_columns": 0,
        "parse_error_type": None,
    }


def _build_summary(selected_artifacts, files):
    return {
        "selected_artifacts": selected_artifacts,
        "inspected_files": _count_status(files, "inspected"),
        "unsupported_files": _count_status(files, "unsupported_extension"),
        "missing_files": _count_status(files, "missing"),
        "parse_error_files": _count_status(files, "parse_error"),
        "path_escape_rejected_files": _count_status(
            files,
            "path_escape_rejected",
        ),
        "total_inspected_rows": sum(
            file_record["inspected_rows"] for file_record in files
        ),
        "total_empty_cells": sum(
            file_record["empty_cell_count"] for file_record in files
        ),
        "total_ragged_rows": sum(
            file_record["ragged_row_count"] for file_record in files
        ),
    }


def _count_status(files, status):
    return sum(1 for file_record in files if file_record["status"] == status)
