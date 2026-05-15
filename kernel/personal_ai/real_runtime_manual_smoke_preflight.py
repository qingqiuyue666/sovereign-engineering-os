"""Manual preflight for real runtime smoke execution.

This module checks readiness for manually gated runtime smoke entries. It does
not call model APIs, launch browsers, contact ComfyUI, launch Blender, read
secret values, or control creative software.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "RealRuntimeManualSmokePreflightResult",
    "run_real_runtime_manual_smoke_preflight",
]

_REPORT_FILE = "real_runtime_manual_smoke_preflight_report.json"
_REPORT_TYPE = "personal_ai_real_runtime_manual_smoke_preflight_report_v1"
_BATCH_FLAG = "SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH"
_MODEL_FLAG = "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE"
_OPENAI_FLAG = "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT"
_OPENAI_KEY = "OPENAI_API_KEY"


@dataclass(frozen=True)
class RealRuntimeManualSmokePreflightResult:
    output_dir: Path
    report_path: Path
    complete: bool
    ready_runtime_count: int
    checked_runtime_count: int
    runtime_execution_performed: bool
    secret_value_read: bool
    required_human_approval: bool


def run_real_runtime_manual_smoke_preflight(
    *,
    output_dir: Path,
    environ: Mapping[str, str] | None = None,
    model_plan_path: Path | None = None,
    browser_admission_path: Path | None = None,
    comfyui_workflow_path: Path | None = None,
    comfyui_endpoint_url: str | None = None,
    blender_scene_path: Path | None = None,
    blender_operation_plan_path: Path | None = None,
) -> RealRuntimeManualSmokePreflightResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    report_path = output_path / _REPORT_FILE
    if report_path.exists():
        raise ValueError("preflight report already exists")
    source = {} if environ is None else environ
    checks = {
        "model_provider": _check_model_provider(source, model_plan_path),
        "browser": _check_browser(browser_admission_path),
        "comfyui": _check_comfyui(comfyui_workflow_path, comfyui_endpoint_url),
        "blender": _check_blender(blender_scene_path, blender_operation_plan_path),
        "creative_tools": _check_creative_tools(),
    }
    ready_count = sum(1 for item in checks.values() if item["ready"] is True)
    report = {
        "report_type": _REPORT_TYPE,
        "complete": True,
        "status": "preflight_completed_no_runtime_execution",
        "checked_runtime_count": len(checks),
        "ready_runtime_count": ready_count,
        "checks": checks,
        "runtime_execution_performed": False,
        "model_api_called": False,
        "browser_launched": False,
        "comfyui_endpoint_called": False,
        "blender_launched": False,
        "creative_software_auto_control_called": False,
        "external_network_accessed": False,
        "secret_value_read": False,
        "secret_value_persisted": False,
        "raw_provider_response_persisted": False,
        "raw_image_payload_persisted": False,
        "arbitrary_subprocess_executed": False,
        "output_triggered_tool_or_file_authority": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_preflight_report_before_manual_runtime_smoke",
    }
    write_json_atomically(report_path, report)
    return RealRuntimeManualSmokePreflightResult(
        output_dir=output_path,
        report_path=report_path,
        complete=True,
        ready_runtime_count=ready_count,
        checked_runtime_count=len(checks),
        runtime_execution_performed=False,
        secret_value_read=False,
        required_human_approval=True,
    )


def _check_model_provider(environ: Mapping[str, str], plan_path: Path | None) -> dict[str, object]:
    failures: list[str] = []
    if plan_path is None:
        failures.append("model_plan_path_missing")
    elif not Path(plan_path).is_file():
        failures.append("model_plan_path_not_file")
    for flag_name in (_BATCH_FLAG, _MODEL_FLAG, _OPENAI_FLAG):
        if environ.get(flag_name) != "true":
            failures.append(flag_name + "_missing_or_not_true")
    if _OPENAI_KEY not in environ:
        failures.append("OPENAI_API_KEY_missing")
    return {
        "runtime": "model_provider",
        "ready": not failures,
        "failures": sorted(failures),
        "plan_artifact_present": plan_path is not None and Path(plan_path).is_file(),
        "batch_flag_present": environ.get(_BATCH_FLAG) == "true",
        "model_flag_present": environ.get(_MODEL_FLAG) == "true",
        "openai_transport_flag_present": environ.get(_OPENAI_FLAG) == "true",
        "openai_api_key_present": _OPENAI_KEY in environ,
        "openai_api_key_value_read": False,
        "runtime_execution_performed": False,
        "forbidden_actions": [
            "api_key_value_read",
            "api_key_value_persisted",
            "raw_provider_response_persisted",
            "model_output_tool_call",
            "model_output_file_edit",
        ],
    }


def _check_browser(admission_path: Path | None) -> dict[str, object]:
    failures: list[str] = []
    admission: dict[str, object] | None = None
    if admission_path is None:
        failures.append("browser_admission_path_missing")
    elif not Path(admission_path).is_file():
        failures.append("browser_admission_path_not_file")
    else:
        admission = _read_json(Path(admission_path), "browser_admission_artifact")
        if admission.get("loopback_only") is not True:
            failures.append("loopback_only_missing")
        if admission.get("isolated_temp_profile_required") is not True:
            failures.append("isolated_temp_profile_required_missing")
        for field_name in (
            "external_network_allowed",
            "real_user_profile_allowed",
            "credential_persistence_allowed",
            "login_allowed",
            "signup_allowed",
            "account_creation_allowed",
            "payment_allowed",
        ):
            if admission.get(field_name) is not False:
                failures.append(field_name + "_must_be_false")
    return {
        "runtime": "browser",
        "ready": not failures,
        "failures": sorted(failures),
        "admission_artifact_present": admission_path is not None and Path(admission_path).is_file(),
        "loopback_only_verified": bool(admission and admission.get("loopback_only") is True),
        "isolated_temp_profile_verified": bool(
            admission and admission.get("isolated_temp_profile_required") is True
        ),
        "runtime_execution_performed": False,
        "forbidden_actions": [
            "external_url",
            "real_user_profile",
            "login",
            "signup",
            "payment",
            "account_creation",
            "credential_persistence",
        ],
    }


def _check_comfyui(workflow_path: Path | None, endpoint_url: str | None) -> dict[str, object]:
    failures: list[str] = []
    if endpoint_url is None:
        failures.append("comfyui_endpoint_url_missing")
    elif not endpoint_url.startswith(("http://127.0.0.1", "http://localhost")):
        failures.append("comfyui_endpoint_not_loopback")
    workflow: dict[str, object] | None = None
    if workflow_path is None:
        failures.append("comfyui_workflow_path_missing")
    elif not Path(workflow_path).is_file():
        failures.append("comfyui_workflow_path_not_file")
    else:
        workflow = _read_json(Path(workflow_path), "comfyui_workflow_artifact")
        node_failures = _validate_comfyui_workflow_nodes(workflow)
        failures.extend(node_failures)
    return {
        "runtime": "comfyui",
        "ready": not failures,
        "failures": sorted(set(failures)),
        "workflow_artifact_present": workflow_path is not None and Path(workflow_path).is_file(),
        "endpoint_loopback_verified": bool(
            endpoint_url and endpoint_url.startswith(("http://127.0.0.1", "http://localhost"))
        ),
        "node_count": 0 if workflow is None else len(workflow.get("nodes", [])),
        "runtime_execution_performed": False,
        "forbidden_actions": [
            "external_download",
            "script_execution",
            "python_execution",
            "subprocess",
            "url_node",
            "network_node",
            "model_download",
            "raw_image_payload_persistence",
        ],
    }


def _check_blender(scene_path: Path | None, operation_plan_path: Path | None) -> dict[str, object]:
    failures: list[str] = []
    if scene_path is None:
        failures.append("blender_scene_path_missing")
    elif not Path(scene_path).is_file():
        failures.append("blender_scene_path_not_file")
    elif Path(scene_path).is_symlink():
        failures.append("blender_scene_path_symlink_forbidden")
    elif Path(scene_path).suffix.lower() not in (".blend", ".glb", ".gltf"):
        failures.append("blender_scene_extension_not_allowed")
    plan: dict[str, object] | None = None
    if operation_plan_path is None:
        failures.append("blender_operation_plan_path_missing")
    elif not Path(operation_plan_path).is_file():
        failures.append("blender_operation_plan_path_not_file")
    else:
        plan = _read_json(Path(operation_plan_path), "blender_operation_plan_artifact")
        failures.extend(_validate_blender_operations(plan))
    return {
        "runtime": "blender",
        "ready": not failures,
        "failures": sorted(set(failures)),
        "scene_artifact_present": scene_path is not None and Path(scene_path).is_file(),
        "operation_plan_artifact_present": operation_plan_path is not None
        and Path(operation_plan_path).is_file(),
        "operation_count": 0 if plan is None else len(plan.get("operations", [])),
        "runtime_execution_performed": False,
        "forbidden_actions": [
            "exec",
            "eval",
            "python",
            "subprocess",
            "os.",
            "sys.",
            "url",
            "network",
            "source_overwrite",
        ],
    }


def _check_creative_tools() -> dict[str, object]:
    return {
        "runtime": "creative_tools",
        "ready": True,
        "failures": [],
        "handoff_only": True,
        "ae_auto_control_called": False,
        "unreal_auto_control_called": False,
        "houdini_auto_control_called": False,
        "zbrush_auto_control_called": False,
        "runtime_execution_performed": False,
        "forbidden_actions": [
            "ae_auto_control",
            "unreal_auto_control",
            "houdini_auto_control",
            "zbrush_auto_control",
            "project_file_mutation_without_human_review",
        ],
    }


def _validate_comfyui_workflow_nodes(workflow: dict[str, object]) -> list[str]:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["comfyui_workflow_nodes_missing_or_malformed"]
    forbidden = ("download", "exec", "http", "network", "python", "script", "subprocess", "url")
    failures: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            failures.append("comfyui_workflow_node_malformed")
            continue
        node_type = str(node.get("type", "")).lower()
        if any(token in node_type for token in forbidden):
            failures.append("comfyui_workflow_forbidden_node_type")
    return failures


def _validate_blender_operations(plan: dict[str, object]) -> list[str]:
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        return ["blender_operations_missing_or_malformed"]
    allowed = {
        "add_camera",
        "add_light",
        "add_mesh_primitive",
        "assign_material",
        "create_collection",
        "export_glb_preview",
        "render_preview",
        "set_camera",
        "set_object_transform",
    }
    forbidden = ("__import__", "eval", "exec", "http", "network", "open(", "os.", "python", "script", "subprocess", "sys.", "url")
    failures: list[str] = []
    for operation in operations:
        if not isinstance(operation, dict):
            failures.append("blender_operation_malformed")
            continue
        if str(operation.get("operation", "")) not in allowed:
            failures.append("blender_operation_not_allowed")
        serialized = json.dumps(operation, sort_keys=True).lower()
        if any(token in serialized for token in forbidden):
            failures.append("blender_operation_forbidden_token")
    return failures


def _read_json(path: Path, name: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(name + " is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError(name + " is malformed")
    return payload
