"""Local product launcher workflows for Personal AI Execution OS."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.adapters.browser_fixture_runtime import (
    run_browser_fixture_from_actions_file,
)
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    run_model_fixture,
    write_model_fixture_request,
)
from kernel.personal_ai.adapters.xlsx_output_writer import plan_xlsx_output
from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.markdown_utils import write_markdown_atomically
from kernel.personal_ai.runtime_delivery_package import validate_runtime_delivery_package

__all__ = [
    "LauncherWorkflowResult",
    "run_browser_fixture_launcher",
    "run_local_office_launcher",
    "run_model_fixture_launcher",
    "run_runtime_delivery_validation_launcher",
]

_SUMMARY_FILE = "launcher_summary.md"
_MODEL_REQUEST_FILE = "model_request.json"


@dataclass(frozen=True)
class LauncherWorkflowResult:
    workflow: str
    output_dir: Path
    complete: bool
    payload: dict[str, object]
    summary_path: Path
    required_human_approval: bool

    def to_cli_payload(self) -> dict[str, object]:
        payload = {
            "workflow": self.workflow,
            "complete": self.complete,
            "output_dir": self.output_dir.as_posix(),
            "human_summary_path": self.summary_path.as_posix(),
            "required_human_approval": self.required_human_approval,
        }
        payload.update(self.payload)
        return payload


def run_local_office_launcher(
    input_workbook: Path,
    output_dir: Path,
    *,
    output_workbook_name: str = "derived_xlsx_summary.xlsx",
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    _require_no_overwrite(summary_path)
    inspection = inspect_xlsx_readonly(Path(input_workbook), output_path)
    plan = plan_xlsx_output(
        Path(input_workbook),
        inspection.xlsx_inspection_path,
        output_path,
        output_workbook_name=output_workbook_name,
    )
    payload = {
        "input_workbook_path": Path(input_workbook).as_posix(),
        "xlsx_inspection_path": inspection.xlsx_inspection_path.as_posix(),
        "xlsx_inspection_summary_path": (
            inspection.xlsx_inspection_summary_path.as_posix()
        ),
        "xlsx_output_plan_path": plan.plan_path.as_posix(),
        "input_sha256": inspection.input_sha256,
        "sheet_count": inspection.sheet_count,
        "output_write_performed": False,
        "input_mutation_performed": False,
        "next_allowed_action": "human_review_xlsx_output_plan",
    }
    _write_summary(
        summary_path,
        title="Office Workflow",
        lines=[
            "Status: complete",
            "Runtime: local XLSX metadata inspection and output planning only",
            "Output write performed: false",
            "Input mutation performed: false",
            "Next action: human review of the XLSX output plan",
        ],
    )
    return LauncherWorkflowResult(
        workflow="local_office_workflow",
        output_dir=output_path,
        complete=True,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_model_fixture_launcher(
    input_artifact_path: Path,
    output_dir: Path,
    *,
    schema_name: str,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    request_path = output_path / _MODEL_REQUEST_FILE
    _require_no_overwrite(summary_path)
    _require_no_overwrite(request_path)
    write_model_fixture_request(
        Path(input_artifact_path),
        request_path,
        schema_name=schema_name,
    )
    result = run_model_fixture(request_path, output_path)
    payload = {
        "request_path": request_path.as_posix(),
        "model_inference_artifact_path": None
        if result.inference_artifact_path is None
        else result.inference_artifact_path.as_posix(),
        "model_failure_bundle_path": None
        if result.failure_bundle_path is None
        else result.failure_bundle_path.as_posix(),
        "schema_name": result.schema_name,
        "live_model_provider_called": False,
        "network_runtime_allowed": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Model Fixture Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: deterministic local typed-schema mock provider",
            "Live model provider called: false",
            "Network runtime allowed: false",
            "Next action: human review of model fixture artifact",
        ],
    )
    return LauncherWorkflowResult(
        workflow="model_fixture_workflow",
        output_dir=output_path,
        complete=result.success,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_browser_fixture_launcher(
    fixture_path: Path,
    actions_path: Path,
    output_dir: Path,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    _require_no_overwrite(summary_path)
    result = run_browser_fixture_from_actions_file(
        Path(fixture_path),
        Path(actions_path),
        output_path,
    )
    payload = {
        "fixture_path": result.fixture_path.as_posix(),
        "actions_path": Path(actions_path).as_posix(),
        "browser_action_log_path": result.action_log_path.as_posix(),
        "browser_evidence_manifest_path": (
            result.evidence_manifest_path.as_posix()
        ),
        "action_count": result.action_count,
        "real_browser_runtime_used": False,
        "external_network_used": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Browser Fixture Workflow",
        lines=[
            "Status: complete",
            "Runtime: deterministic local HTML fixture interpreter",
            "Real browser runtime used: false",
            "External network used: false",
            "Next action: human review of browser fixture evidence",
        ],
    )
    return LauncherWorkflowResult(
        workflow="browser_fixture_workflow",
        output_dir=output_path,
        complete=True,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_runtime_delivery_validation_launcher(
    package_dir: Path,
    output_dir: Path,
    *,
    raw_sentinel_values: list[str] | None = None,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    validation_path = output_path / "runtime_delivery_validation.json"
    _require_no_overwrite(summary_path)
    _require_no_overwrite(validation_path)
    result = validate_runtime_delivery_package(
        Path(package_dir),
        validation_path,
        raw_sentinel_values=raw_sentinel_values or [],
    )
    payload = {
        "package_dir": result.package_dir.as_posix(),
        "runtime_delivery_manifest_path": (
            result.runtime_delivery_manifest_path.as_posix()
        ),
        "runtime_delivery_validation_path": (
            result.runtime_delivery_validation_path.as_posix()
        ),
        "packaged_artifacts": list(result.packaged_artifacts),
        "raw_value_leakage_detected": result.raw_value_leakage_detected,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Runtime Delivery Validation",
        lines=[
            "Status: complete" if result.complete else "Status: failed",
            "Runtime: local manifest and replay validation only",
            "Raw value leakage detected: "
            + str(result.raw_value_leakage_detected).lower(),
            "Next action: human review of delivery validation",
        ],
    )
    return LauncherWorkflowResult(
        workflow="runtime_delivery_validation_workflow",
        output_dir=output_path,
        complete=result.complete,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def _validate_output_dir(output_dir):
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    return output_path


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("launcher output already exists")


def _write_summary(summary_path, *, title, lines):
    _require_no_overwrite(summary_path)
    body = ["# " + title, ""]
    body.extend(lines)
    body.append("")
    body.append("Boundary: local fixture only; human approval required.")
    write_markdown_atomically(summary_path, "\n".join(body))
