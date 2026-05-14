"""Contract helpers for the bounded XLSX readonly adapter."""

from dataclasses import dataclass

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterRiskClass,
)

__all__ = [
    "XlsxReadonlyLimits",
    "build_xlsx_readonly_capability_request",
]


@dataclass(frozen=True)
class XlsxReadonlyLimits:
    max_header_rows: int = 3
    max_header_columns: int = 8
    max_formula_scan_cells: int = 1000
    max_style_scan_cells: int = 1000

    def validate(self) -> None:
        if self.max_header_rows <= 0:
            raise ValueError("max_header_rows must be greater than zero")
        if self.max_header_columns <= 0:
            raise ValueError("max_header_columns must be greater than zero")
        if self.max_formula_scan_cells <= 0:
            raise ValueError("max_formula_scan_cells must be greater than zero")
        if self.max_style_scan_cells <= 0:
            raise ValueError("max_style_scan_cells must be greater than zero")


def build_xlsx_readonly_capability_request() -> AdapterCapabilityRequest:
    return AdapterCapabilityRequest(
        adapter_id="xlsx_readonly_runtime",
        capability="inspect_local_xlsx_metadata",
        mode=AdapterMode.READONLY,
        risk_class=AdapterRiskClass.LOCAL_READONLY,
        requested_operations=("open_workbook_readonly", "write_metadata_artifacts"),
        boundary=AdapterExecutionBoundary(),
    )
