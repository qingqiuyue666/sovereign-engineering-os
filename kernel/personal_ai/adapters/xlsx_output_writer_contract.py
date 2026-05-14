"""Contract helpers for approved XLSX output writer runtime."""

from dataclasses import dataclass

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRiskClass,
)

__all__ = [
    "XlsxOutputWriterPaths",
    "build_xlsx_output_writer_capability_request",
]


@dataclass(frozen=True)
class XlsxOutputWriterPaths:
    plan_file: str = "xlsx_output_plan.json"
    manifest_file: str = "xlsx_output_manifest.json"
    delivery_summary_file: str = "xlsx_output_delivery_summary.md"
    validation_report_file: str = "xlsx_output_validation.json"


def build_xlsx_output_writer_capability_request() -> AdapterCapabilityRequest:
    return AdapterCapabilityRequest(
        adapter_id="xlsx_output_writer",
        capability="create_metadata_summary_workbook",
        mode=AdapterMode.APPROVED_WRITE,
        risk_class=AdapterRiskClass.APPROVED_OUTPUT_WRITE,
        requested_operations=(
            "write_new_xlsx_output",
            "write_output_manifest",
            "write_validation_report",
        ),
        boundary=AdapterExecutionBoundary(output_write_allowed=True),
    )
