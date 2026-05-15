"""Real runtime smoke execution batch entries.

This module exposes manually gated smoke-entry wrappers for real runtime lines.
It does not execute real external runtimes by default. Normal tests must use
fake or injected transports only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.adapters.blender_runtime_admission_disabled_runner import (
    run_blender_runtime_admission_disabled_runner,
)
from kernel.personal_ai.adapters.browser_playwright_loopback_transport_package import (
    build_browser_playwright_loopback_transport_package,
)
from kernel.personal_ai.adapters.comfyui_endpoint_admission_disabled_runner import (
    run_comfyui_endpoint_disabled_runner,
)
from kernel.personal_ai.adapters.model_provider_disabled_live_smoke_runner import (
    run_model_provider_disabled_live_smoke,
)
from kernel.personal_ai.adapters.openai_explicit_transport import (
    run_openai_explicit_transport,
    stdlib_openai_responses_transport,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "RealRuntimeSmokeBatchResult",
    "run_real_runtime_smoke_execution_batch",
]

_RESULT_FILE = "real_runtime_smoke_execution_batch_result.json"
_FAILURE_FILE = "real_runtime_smoke_execution_batch_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_real_runtime_smoke_execution_batch_result_v1"
_FAILURE_TYPE = "personal_ai_real_runtime_smoke_execution_batch_failure_v1"
_BATCH_ENABLE_FLAG = "SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH"
_EXPECTED_ENABLE_VALUE = "true"

ModelTransport = Callable[[dict[str, object]], dict[str, object]]
BrowserTransport = Callable[[dict[str, object]], dict[str, object]]
ComfyUITransport = Callable[[dict[str, object]], dict[str, object]]
BlenderTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class RealRuntimeSmokeBatchResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    real_model_smoke_entry_called: bool
    real_browser_smoke_entry_called: bool
    real_comfyui_smoke_entry_called: bool
    real_blender_smoke_entry_called: bool
    creative_software_auto_control_called: bool
    required_human_approval: bool


def run_real_runtime_smoke_execution_batch(
    *,
    output_dir: Path,
    environ: Mapping[str, str] | None = None,
    allow_batch: bool = False,
    # model provider
    model_plan_path: Path | None = None,
    allow_model_smoke: bool = False,
    model_transport: ModelTransport | None = None,
    use_stdlib_openai_transport: bool = False,
    # browser
    browser_admission_path: Path | None = None,
    allow_browser_smoke: bool = False,
    browser_transport: BrowserTransport | None = None,
    # ComfyUI
    comfyui_workflow_path: Path | None = None,
    allow_comfyui_smoke: bool = False,
    comfyui_transport: ComfyUITransport | None = None,
    # Blender
    blender_scene_path: Path | None = None,
    blender_operation_plan_path: Path | None = None,
    allow_blender_smoke: bool = False,
    blender_transport: BlenderTransport | None = None,
) -> RealRuntimeSmokeBatchResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    source = {} if environ is None else environ
    try:
        if allow_batch is not True:
            return _write_batch_denial(result_path, "disabled_by_callsite")
        if source.get(_BATCH_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_batch_denial(result_path, "disabled_by_environment_flag")

        model_result = _run_model_entry(
            output_path,
            source,
            model_plan_path,
            allow_model_smoke,
            model_transport,
            use_stdlib_openai_transport,
        )
        browser_result = _run_browser_entry(
            output_path,
            source,
            browser_admission_path,
            allow_browser_smoke,
            browser_transport,
        )
        comfyui_result = _run_comfyui_entry(
            output_path,
            source,
            comfyui_workflow_path,
            allow_comfyui_smoke,
            comfyui_transport,
        )
        blender_result = _run_blender_entry(
            output_path,
            source,
            blender_scene_path,
            blender_operation_plan_path,
            allow_blender_smoke,
            blender_transport,
        )
        result = {
            "result_type": _RESULT_TYPE,
            "status": "completed_with_manual_runtime_smoke_entries",
            "batch_enable_flag": _BATCH_ENABLE_FLAG,
            "model_provider": model_result,
            "browser": browser_result,
            "comfyui": comfyui_result,
            "blender": blender_result,
            "creative_tools": _creative_handoff_only_result(),
            "default_live_execution_enabled": False,
            "normal_tests_must_use_fake_or_injected_transports": True,
            "secrets_persisted": False,
            "raw_provider_response_persisted": False,
            "external_network_allowed_by_default": False,
            "arbitrary_subprocess_allowed": False,
            "output_triggered_tool_or_file_authority": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_real_runtime_smoke_batch",
        }
        write_json_atomically(result_path, result)
        return RealRuntimeSmokeBatchResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_with_manual_runtime_smoke_entries",
            real_model_smoke_entry_called=bool(model_result["entry_called"]),
            real_browser_smoke_entry_called=bool(browser_result["entry_called"]),
            real_comfyui_smoke_entry_called=bool(comfyui_result["entry_called"]),
            real_blender_smoke_entry_called=bool(blender_result["entry_called"]),
            creative_software_auto_control_called=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "default_live_execution_enabled": False,
            "secrets_persisted": False,
            "arbitrary_subprocess_allowed": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return RealRuntimeSmokeBatchResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            real_model_smoke_entry_called=False,
            real_browser_smoke_entry_called=False,
            real_comfyui_smoke_entry_called=False,
            real_blender_smoke_entry_called=False,
            creative_software_auto_control_called=False,
            required_human_approval=True,
        )


def _run_model_entry(
    output_path: Path,
    environ: Mapping[str, str],
    plan_path: Path | None,
    allow_smoke: bool,
    model_transport: ModelTransport | None,
    use_stdlib_openai_transport: bool,
) -> dict[str, object]:
    if not allow_smoke:
        return _skipped_entry("model_provider", "disabled_by_callsite")
    if plan_path is None:
        raise ValueError("model_plan_path is required when allow_model_smoke is true")
    model_dir = output_path / "model_provider"
    model_dir.mkdir()

    if model_transport is None and use_stdlib_openai_transport is True:
        explicit_dir = model_dir / "openai_explicit_transport"
        explicit_dir.mkdir()

        def model_transport(request: dict[str, object]) -> dict[str, object]:
            transport_result = run_openai_explicit_transport(
                request,
                explicit_dir,
                allow_network=True,
                http_transport=stdlib_openai_responses_transport,
                environ=environ,
            )
            if transport_result.result_path is None:
                raise ValueError("openai explicit transport failed closed")
            return {"status": "ok", "provider_id": "openai"}

    if model_transport is None:
        raise ValueError("model_transport is required unless stdlib OpenAI transport is explicitly enabled")
    runner = run_model_provider_disabled_live_smoke(
        Path(plan_path),
        model_dir,
        environ=environ,
        allow_live_smoke=True,
        live_transport=model_transport,
    )
    return {
        "entry": "model_provider",
        "entry_called": True,
        "status": runner.status,
        "result_path": None if runner.result_path is None else runner.result_path.as_posix(),
        "failure_path": None if runner.failure_path is None else runner.failure_path.as_posix(),
        "live_provider_called": runner.live_provider_called,
        "network_used_by_runner": runner.network_used_by_runner,
        "api_key_value_persisted": runner.api_key_value_persisted,
        "api_key_value_logged": runner.api_key_value_logged,
        "raw_provider_response_persisted": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
    }


def _run_browser_entry(
    output_path: Path,
    environ: Mapping[str, str],
    admission_path: Path | None,
    allow_smoke: bool,
    browser_transport: BrowserTransport | None,
) -> dict[str, object]:
    if not allow_smoke:
        return _skipped_entry("browser", "disabled_by_callsite")
    if admission_path is None:
        raise ValueError("browser_admission_path is required when allow_browser_smoke is true")
    if browser_transport is None:
        raise ValueError("browser_transport is required when allow_browser_smoke is true")
    browser_dir = output_path / "browser"
    browser_dir.mkdir()
    runner = build_browser_playwright_loopback_transport_package(
        Path(admission_path),
        browser_dir,
        environ={**dict(environ), "SEOS_ENABLE_BROWSER_PLAYWRIGHT_LOOPBACK_TRANSPORT_PACKAGE": "true"},
        allow_transport_package=True,
        loopback_transport=browser_transport,
    )
    return {
        "entry": "browser",
        "entry_called": True,
        "status": runner.status,
        "result_path": None if runner.result_path is None else runner.result_path.as_posix(),
        "failure_path": None if runner.failure_path is None else runner.failure_path.as_posix(),
        "playwright_dependency_added": runner.playwright_dependency_added,
        "playwright_imported": runner.playwright_imported,
        "browser_launched": runner.browser_launched,
        "external_network_used": runner.external_network_used,
        "real_user_profile_used": False,
        "credential_persistence_used": False,
        "login_signup_payment_account_authority": False,
    }


def _run_comfyui_entry(
    output_path: Path,
    environ: Mapping[str, str],
    workflow_path: Path | None,
    allow_smoke: bool,
    comfyui_transport: ComfyUITransport | None,
) -> dict[str, object]:
    if not allow_smoke:
        return _skipped_entry("comfyui", "disabled_by_callsite")
    if workflow_path is None:
        raise ValueError("comfyui_workflow_path is required when allow_comfyui_smoke is true")
    if comfyui_transport is None:
        raise ValueError("comfyui_transport is required when allow_comfyui_smoke is true")
    comfyui_dir = output_path / "comfyui"
    comfyui_dir.mkdir()
    runner = run_comfyui_endpoint_disabled_runner(
        Path(workflow_path),
        comfyui_dir,
        environ={**dict(environ), "SEOS_ENABLE_COMFYUI_ENDPOINT_DISABLED_RUNNER": "true"},
        allow_endpoint_runner=True,
        comfyui_transport=comfyui_transport,
    )
    return {
        "entry": "comfyui",
        "entry_called": True,
        "status": runner.status,
        "result_path": None if runner.result_path is None else runner.result_path.as_posix(),
        "failure_path": None if runner.failure_path is None else runner.failure_path.as_posix(),
        "real_endpoint_called": runner.real_endpoint_called,
        "external_network_used": runner.external_network_used,
        "arbitrary_node_execution_used": runner.arbitrary_node_execution_used,
        "model_download_performed": False,
        "raw_image_payload_persisted": False,
    }


def _run_blender_entry(
    output_path: Path,
    environ: Mapping[str, str],
    scene_path: Path | None,
    operation_plan_path: Path | None,
    allow_smoke: bool,
    blender_transport: BlenderTransport | None,
) -> dict[str, object]:
    if not allow_smoke:
        return _skipped_entry("blender", "disabled_by_callsite")
    if scene_path is None or operation_plan_path is None:
        raise ValueError("blender scene and operation plan paths are required when allow_blender_smoke is true")
    if blender_transport is None:
        raise ValueError("blender_transport is required when allow_blender_smoke is true")
    blender_dir = output_path / "blender"
    blender_dir.mkdir()
    runner = run_blender_runtime_admission_disabled_runner(
        Path(scene_path),
        Path(operation_plan_path),
        blender_dir,
        environ={**dict(environ), "SEOS_ENABLE_BLENDER_RUNTIME_ADMISSION_DISABLED_RUNNER": "true"},
        allow_blender_runner=True,
        blender_transport=blender_transport,
    )
    return {
        "entry": "blender",
        "entry_called": True,
        "status": runner.status,
        "result_path": None if runner.result_path is None else runner.result_path.as_posix(),
        "failure_path": None if runner.failure_path is None else runner.failure_path.as_posix(),
        "blender_runtime_called": runner.blender_runtime_called,
        "subprocess_used": runner.subprocess_used,
        "arbitrary_python_used": runner.arbitrary_python_used,
        "external_network_used": False,
        "source_asset_overwrite_performed": False,
    }


def _creative_handoff_only_result() -> dict[str, object]:
    return {
        "entry": "creative_tools",
        "entry_called": False,
        "ae_auto_control_called": False,
        "unreal_auto_control_called": False,
        "houdini_auto_control_called": False,
        "zbrush_auto_control_called": False,
        "handoff_manifest_only": True,
        "required_human_approval": True,
    }


def _skipped_entry(entry: str, status: str) -> dict[str, object]:
    return {
        "entry": entry,
        "entry_called": False,
        "status": status,
        "required_human_approval": True,
    }


def _write_batch_denial(result_path: Path, status: str) -> RealRuntimeSmokeBatchResult:
    result = {
        "result_type": _RESULT_TYPE,
        "status": status,
        "batch_enable_flag": _BATCH_ENABLE_FLAG,
        "default_live_execution_enabled": False,
        "real_model_smoke_entry_called": False,
        "real_browser_smoke_entry_called": False,
        "real_comfyui_smoke_entry_called": False,
        "real_blender_smoke_entry_called": False,
        "creative_software_auto_control_called": False,
        "secrets_persisted": False,
        "arbitrary_subprocess_allowed": False,
        "required_human_approval": True,
    }
    write_json_atomically(result_path, result)
    return RealRuntimeSmokeBatchResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        real_model_smoke_entry_called=False,
        real_browser_smoke_entry_called=False,
        real_comfyui_smoke_entry_called=False,
        real_blender_smoke_entry_called=False,
        creative_software_auto_control_called=False,
        required_human_approval=True,
    )


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("real runtime smoke batch output already exists")
