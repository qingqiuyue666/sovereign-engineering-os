"""Local product launcher workflows for Personal AI Execution OS."""

from dataclasses import dataclass
from pathlib import Path

from kernel.assets.local_asset_runtime import run_local_asset_runtime
from kernel.assets.local_asset_schema import (
    ASSET_INDEX_FILE,
    ASSET_MANIFEST_FILE,
    AUDIT_LOG_FILE,
    DUPLICATES_REPORT_FILE,
    MEDIA_INVENTORY_FILE,
    QUARANTINE_MANIFEST_FILE,
    VALIDATION_REPORT_FILE,
)
from kernel.personal_ai.adapters.blender_runtime import run_blender_runtime
from kernel.personal_ai.adapters.blender_runtime_boundary import (
    write_blender_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.browser_fixture_runtime import (
    run_browser_fixture_from_actions_file,
)
from kernel.personal_ai.adapters.browser_runtime import run_browser_runtime
from kernel.personal_ai.adapters.browser_runtime_boundary import (
    write_browser_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.comfyui_runtime import run_comfyui_runtime
from kernel.personal_ai.adapters.comfyui_runtime_boundary import (
    write_comfyui_runtime_admission_artifacts,
)
from kernel.personal_ai.adapters.creative_handoff_package import (
    build_creative_handoff_package,
)
from kernel.personal_ai.adapters.model_provider_boundary import (
    write_model_provider_admission_artifacts,
)
from kernel.personal_ai.adapters.model_provider_runtime import (
    run_model_provider_runtime,
)
from kernel.personal_ai.adapters.model_typed_schema_runtime import (
    run_model_fixture,
    write_model_fixture_request,
    write_model_provider_request,
)
from kernel.personal_ai.adapters.xlsx_output_writer import plan_xlsx_output
from kernel.personal_ai.adapters.xlsx_readonly_runtime import inspect_xlsx_readonly
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically
from kernel.personal_ai.product_health_check import write_product_health_check
from kernel.personal_ai.runtime_delivery_package import validate_runtime_delivery_package
from kernel.personal_ai.task_graph import run_local_task_graph_fixture

__all__ = [
    "LauncherWorkflowResult",
    "run_browser_fixture_launcher",
    "run_browser_runtime_dry_run_launcher",
    "run_blender_dry_run_launcher",
    "run_comfyui_dry_run_launcher",
    "run_creative_handoff_launcher",
    "run_local_asset_scan_launcher",
    "run_local_office_launcher",
    "run_model_fixture_launcher",
    "run_model_provider_dry_run_launcher",
    "run_product_health_check_launcher",
    "run_runtime_delivery_validation_launcher",
    "run_task_graph_launcher",
]

_SUMMARY_FILE = "launcher_summary.md"
_MODEL_REQUEST_FILE = "model_request.json"
_MODEL_PROVIDER_REQUEST_FILE = "model_provider_request.json"
_ADMISSION_DIR = "runtime_admission"
_COMFYUI_ENDPOINT_CONFIG_FILE = "comfyui_endpoint_config.json"
_BLENDER_CONFIG_FILE = "blender_runtime_config.json"
_PRODUCT_HEALTH_FILE = "product_health_report.json"


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


def run_local_asset_scan_launcher(
    input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = False,
    include_hidden: bool = False,
    project_id: str | None = None,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    _require_no_overwrite(summary_path)
    result = run_local_asset_runtime(
        Path(input_dir),
        output_path,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
    )
    payload = {
        "input_dir": result.input_dir.as_posix(),
        "asset_manifest_path": result.output_paths[ASSET_MANIFEST_FILE].as_posix(),
        "asset_index_path": result.output_paths[ASSET_INDEX_FILE].as_posix(),
        "duplicates_report_path": (
            result.output_paths[DUPLICATES_REPORT_FILE].as_posix()
        ),
        "media_inventory_path": result.output_paths[MEDIA_INVENTORY_FILE].as_posix(),
        "asset_runtime_audit_log_path": (
            result.output_paths[AUDIT_LOG_FILE].as_posix()
        ),
        "asset_runtime_validation_report_path": (
            result.output_paths[VALIDATION_REPORT_FILE].as_posix()
        ),
        "asset_runtime_quarantine_manifest_path": (
            result.output_paths[QUARANTINE_MANIFEST_FILE].as_posix()
        ),
        "asset_runtime_output_paths": {
            filename: path.as_posix()
            for filename, path in sorted(result.output_paths.items())
        },
        "files_scanned": result.files_scanned,
        "bytes_scanned": result.bytes_scanned,
        "duplicate_groups": result.duplicate_groups,
        "quarantined_paths": result.quarantined_paths,
        "recursive": result.recursive,
        "include_hidden": result.include_hidden,
        "project_id": result.project_id,
        "read_only_input": True,
        "input_mutation_performed": False,
        "file_move_performed": False,
        "file_rename_performed": False,
        "file_delete_performed": False,
        "media_organizer_behavior_performed": False,
        "output_overwrite_performed": False,
        "network_access_performed": False,
        "model_api_called": False,
        "desktop_ui_added": False,
        "browser_runtime_invoked": False,
        "comfyui_runtime_invoked": False,
        "blender_runtime_invoked": False,
        "houdini_runtime_invoked": False,
        "after_effects_runtime_invoked": False,
        "davinci_runtime_invoked": False,
        "external_runtime_invoked": False,
    }
    _write_summary(
        summary_path,
        title="Local Asset Scan",
        lines=[
            "Status: complete",
            "Runtime: read-only local asset metadata scan",
            "Files scanned: " + str(result.files_scanned),
            "Input mutation performed: false",
            "File movement performed: false",
            "File renaming performed: false",
            "File deletion performed: false",
            "Network access performed: false",
            "Model API called: false",
            "External runtime invoked: false",
            "Media organizer behavior performed: false",
            "Next action: human review of local asset reports",
        ],
        boundary="read-only local asset scan; human review required.",
    )
    return LauncherWorkflowResult(
        workflow="local_asset_scan_workflow",
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


def run_model_provider_dry_run_launcher(
    input_artifact_path: Path,
    output_dir: Path,
    *,
    schema_name: str,
    provider_id: str = "openai",
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    request_path = output_path / _MODEL_PROVIDER_REQUEST_FILE
    admission_dir = output_path / _ADMISSION_DIR
    _require_no_overwrite(summary_path)
    _require_no_overwrite(request_path)
    _require_no_overwrite(admission_dir)
    admission_dir.mkdir()
    write_model_provider_request(
        Path(input_artifact_path),
        request_path,
        schema_name=schema_name,
        provider=provider_id,
    )
    artifacts = write_model_provider_admission_artifacts(
        admission_dir,
        provider_id=provider_id,
        schema_name=schema_name,
    )
    result = run_model_provider_runtime(
        request_path,
        output_path,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
        environ={},
    )
    payload = {
        "request_path": request_path.as_posix(),
        "provider_id": result.provider_id,
        "model_provider_result_manifest_path": None
        if result.result_manifest_path is None
        else result.result_manifest_path.as_posix(),
        "model_provider_dry_run_plan_path": None
        if result.dry_run_plan_path is None
        else result.dry_run_plan_path.as_posix(),
        "model_provider_failure_quarantine_path": None
        if result.failure_quarantine_path is None
        else result.failure_quarantine_path.as_posix(),
        "live_model_provider_called": result.live_provider_called,
        "network_runtime_allowed": False,
        "api_key_persisted": False,
        "api_key_logged": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Model Provider Dry Run Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: dry-run live provider boundary only",
            "Live model provider called: false",
            "Network runtime allowed: false",
            "API key persisted: false",
            "Next action: human review of model provider dry-run plan",
        ],
    )
    return LauncherWorkflowResult(
        workflow="model_provider_dry_run_workflow",
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


def run_browser_runtime_dry_run_launcher(
    actions_path: Path,
    output_dir: Path,
    *,
    target_url: str = "http://127.0.0.1",
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    admission_dir = output_path / _ADMISSION_DIR
    _require_no_overwrite(summary_path)
    _require_no_overwrite(admission_dir)
    admission_dir.mkdir()
    artifacts = write_browser_runtime_admission_artifacts(admission_dir)
    result = run_browser_runtime(
        output_path,
        actions_path=Path(actions_path),
        target_url=target_url,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
    )
    payload = {
        "target_url": target_url,
        "browser_runtime_result_manifest_path": None
        if result.result_manifest_path is None
        else result.result_manifest_path.as_posix(),
        "browser_runtime_dry_run_plan_path": None
        if result.dry_run_plan_path is None
        else result.dry_run_plan_path.as_posix(),
        "browser_runtime_failure_quarantine_path": None
        if result.failure_quarantine_path is None
        else result.failure_quarantine_path.as_posix(),
        "real_browser_called": result.real_browser_called,
        "external_network_used": False,
        "credential_persistence_used": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Browser Runtime Dry Run Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: dry-run Playwright/Selenium boundary only",
            "Real browser called: false",
            "External network used: false",
            "Credential persistence used: false",
            "Next action: human review of browser dry-run plan",
        ],
    )
    return LauncherWorkflowResult(
        workflow="browser_runtime_dry_run_workflow",
        output_dir=output_path,
        complete=result.success,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_comfyui_dry_run_launcher(
    workflow_path: Path,
    output_dir: Path,
    *,
    input_asset_paths: tuple[Path, ...] = (),
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    admission_dir = output_path / _ADMISSION_DIR
    endpoint_config_path = output_path / _COMFYUI_ENDPOINT_CONFIG_FILE
    _require_no_overwrite(summary_path)
    _require_no_overwrite(admission_dir)
    _require_no_overwrite(endpoint_config_path)
    admission_dir.mkdir()
    write_json_atomically(
        endpoint_config_path,
        {
            "endpoint": "http://127.0.0.1:8188",
            "enable_real_endpoint": False,
        },
    )
    artifacts = write_comfyui_runtime_admission_artifacts(admission_dir)
    result = run_comfyui_runtime(
        Path(workflow_path),
        output_path,
        input_asset_paths=tuple(Path(path) for path in input_asset_paths),
        endpoint_config_path=endpoint_config_path,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
    )
    payload = {
        "workflow_path": Path(workflow_path).as_posix(),
        "comfyui_runtime_result_manifest_path": None
        if result.result_manifest_path is None
        else result.result_manifest_path.as_posix(),
        "comfyui_endpoint_dry_run_plan_path": None
        if result.dry_run_plan_path is None
        else result.dry_run_plan_path.as_posix(),
        "comfyui_runtime_failure_quarantine_path": None
        if result.failure_quarantine_path is None
        else result.failure_quarantine_path.as_posix(),
        "real_comfyui_endpoint_called": result.real_endpoint_called,
        "network_runtime_allowed": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="ComfyUI Dry Run Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: dry-run loopback ComfyUI endpoint boundary only",
            "Real ComfyUI endpoint called: false",
            "Network runtime allowed: false",
            "Next action: human review of ComfyUI dry-run plan",
        ],
    )
    return LauncherWorkflowResult(
        workflow="comfyui_dry_run_workflow",
        output_dir=output_path,
        complete=result.success,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_blender_dry_run_launcher(
    scene_path: Path,
    operation_plan_path: Path,
    output_dir: Path,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    admission_dir = output_path / _ADMISSION_DIR
    blender_config_path = output_path / _BLENDER_CONFIG_FILE
    _require_no_overwrite(summary_path)
    _require_no_overwrite(admission_dir)
    _require_no_overwrite(blender_config_path)
    admission_dir.mkdir()
    write_json_atomically(
        blender_config_path,
        {
            "blender_executable": "deferred-explicit-configuration-required",
            "enable_real_blender": False,
            "allow_subprocess": False,
            "allow_arbitrary_python": False,
        },
    )
    artifacts = write_blender_runtime_admission_artifacts(admission_dir)
    result = run_blender_runtime(
        Path(scene_path),
        Path(operation_plan_path),
        output_path,
        blender_config_path=blender_config_path,
        admission_config_path=artifacts.config_path,
        admission_approval_path=artifacts.human_approval_path,
        admission_manifest_path=artifacts.manifest_path,
    )
    payload = {
        "scene_path": Path(scene_path).as_posix(),
        "operation_plan_path": Path(operation_plan_path).as_posix(),
        "blender_runtime_result_manifest_path": None
        if result.result_manifest_path is None
        else result.result_manifest_path.as_posix(),
        "blender_runtime_dry_run_plan_path": None
        if result.dry_run_plan_path is None
        else result.dry_run_plan_path.as_posix(),
        "blender_runtime_failure_quarantine_path": None
        if result.failure_quarantine_path is None
        else result.failure_quarantine_path.as_posix(),
        "real_blender_called": result.real_blender_called,
        "subprocess_execution_performed": False,
        "arbitrary_python_execution_performed": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Blender Dry Run Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: dry-run Blender boundary only",
            "Real Blender called: false",
            "Subprocess execution performed: false",
            "Arbitrary Python execution performed: false",
            "Next action: human review of Blender dry-run plan",
        ],
    )
    return LauncherWorkflowResult(
        workflow="blender_dry_run_workflow",
        output_dir=output_path,
        complete=result.success,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_creative_handoff_launcher(
    family: str,
    source_asset_paths: tuple[Path, ...],
    output_dir: Path,
    *,
    package_id: str = "creative-handoff-package",
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    _require_no_overwrite(summary_path)
    result = build_creative_handoff_package(
        family,
        tuple(Path(path) for path in source_asset_paths),
        output_path,
        package_id=package_id,
    )
    payload = {
        "family": result.family,
        "package_id": result.package_id,
        "creative_handoff_package_dir": result.package_dir.as_posix(),
        "creative_handoff_manifest_path": (
            result.package_manifest_path.as_posix()
        ),
        "creative_handoff_tool_manifest_path": (
            result.tool_manifest_path.as_posix()
        ),
        "creative_handoff_instructions_path": (
            result.instructions_path.as_posix()
        ),
        "external_tool_control_performed": False,
        "source_asset_overwrite_performed": False,
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Creative Handoff Workflow",
        lines=[
            "Status: complete",
            "Runtime: human handoff package only",
            "External tool control performed: false",
            "Source asset overwrite performed: false",
            "Next action: human review and manual tool execution only",
        ],
    )
    return LauncherWorkflowResult(
        workflow="creative_handoff_workflow",
        output_dir=output_path,
        complete=result.complete,
        payload=payload,
        summary_path=summary_path,
        required_human_approval=True,
    )


def run_task_graph_launcher(
    graph_path: Path,
    output_dir: Path,
) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    summary_path = output_path / _SUMMARY_FILE
    _require_no_overwrite(summary_path)
    result = run_local_task_graph_fixture(Path(graph_path), output_path)
    payload = {
        "graph_path": result.graph_path.as_posix(),
        "task_graph_execution_manifest_path": None
        if result.execution_manifest_path is None
        else result.execution_manifest_path.as_posix(),
        "task_graph_replay_manifest_path": None
        if result.replay_manifest_path is None
        else result.replay_manifest_path.as_posix(),
        "task_graph_failure_bundle_path": None
        if result.failure_bundle_path is None
        else result.failure_bundle_path.as_posix(),
        "node_order": list(result.node_order),
        "input_mutation_performed": False,
    }
    _write_summary(
        summary_path,
        title="Task Graph Workflow",
        lines=[
            "Status: complete" if result.success else "Status: failed",
            "Runtime: local task graph fixture and dry-run planner only",
            "Real runtime activation performed: false",
            "Next action: human review of graph manifests",
        ],
    )
    return LauncherWorkflowResult(
        workflow="task_graph_workflow",
        output_dir=output_path,
        complete=result.success,
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


def run_product_health_check_launcher(output_dir: Path) -> LauncherWorkflowResult:
    output_path = _validate_output_dir(output_dir)
    result = write_product_health_check(
        output_path,
        report_file_name=_PRODUCT_HEALTH_FILE,
        summary_file_name=_SUMMARY_FILE,
    )
    return LauncherWorkflowResult(
        workflow="product_health_check_workflow",
        output_dir=output_path,
        complete=result.complete,
        payload={"product_health_report_path": result.product_health_report_path.as_posix()},
        summary_path=result.product_health_summary_path,
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


def _write_summary(
    summary_path,
    *,
    title,
    lines,
    boundary="local fixture only; human approval required.",
):
    _require_no_overwrite(summary_path)
    body = ["# " + title, ""]
    body.extend(lines)
    body.append("")
    body.append("Boundary: " + boundary)
    write_markdown_atomically(summary_path, "\n".join(body))
