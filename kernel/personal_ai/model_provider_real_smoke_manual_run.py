"""Manual model-provider smoke run planner.

This module creates a manually gated model-provider smoke run record. It does
not call model APIs, read secret values, persist secret values, launch tools,
open browsers, mutate files, or grant runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelProviderManualSmokeRunResult",
    "build_model_provider_manual_smoke_run",
    "write_model_provider_manual_smoke_run",
]

_RUN_FILE = "model_provider_real_smoke_manual_run_report.json"
_RUN_TYPE = "personal_ai_model_provider_real_smoke_manual_run_v1"
_REQUIRED_MANUAL_FLAGS = (
    "SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH",
    "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE",
    "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT",
)
_SECRET_ENV_NAMES = ("OPENAI_API_KEY",)
_FORBIDDEN_PLAN_FIELDS = (
    "tool_calls",
    "file_edits",
    "browser_actions",
    "subprocess_commands",
    "creative_software_actions",
    "checkpoint_actions",
)


@dataclass(frozen=True)
class ModelProviderManualSmokeRunResult:
    output_dir: Path
    report_path: Path | None
    complete: bool
    ready_for_manual_execution: bool
    runtime_execution_performed: bool
    model_api_called: bool
    secret_value_read: bool
    secret_value_persisted: bool
    required_human_approval: bool
    report: dict[str, object]


def build_model_provider_manual_smoke_run(
    *,
    environ: Mapping[str, str],
    prompt_text: str,
    provider_name: str,
    model_name: str,
    max_output_tokens: int,
    temperature: float,
    request_id: str,
    expected_response_contract: Mapping[str, object] | None = None,
) -> ModelProviderManualSmokeRunResult:
    failures = _validate_inputs(
        environ=environ,
        prompt_text=prompt_text,
        provider_name=provider_name,
        model_name=model_name,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        request_id=request_id,
        expected_response_contract=expected_response_contract,
    )
    manual_flags = {name: environ.get(name) == "true" for name in _REQUIRED_MANUAL_FLAGS}
    secret_presence = {name: name in environ for name in _SECRET_ENV_NAMES}
    for flag_name, present in manual_flags.items():
        if not present:
            failures.append(flag_name + "_missing_or_not_true")
    if not secret_presence["OPENAI_API_KEY"]:
        failures.append("OPENAI_API_KEY_missing")
    ready = not failures
    prompt_hash = sha256(prompt_text.encode("utf-8")).hexdigest()
    contract_payload = {} if expected_response_contract is None else dict(expected_response_contract)
    report = {
        "report_type": _RUN_TYPE,
        "complete": True,
        "status": "manual_model_provider_smoke_run_planned_no_runtime_execution",
        "request_id": request_id,
        "provider_name": provider_name,
        "model_name": model_name,
        "prompt_sha256": prompt_hash,
        "prompt_length_chars": len(prompt_text),
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
        "expected_response_contract": contract_payload,
        "manual_flags": manual_flags,
        "secret_presence": secret_presence,
        "secret_value_read": False,
        "secret_value_persisted": False,
        "secret_value_serialized": False,
        "raw_prompt_persisted": False,
        "raw_provider_response_persisted": False,
        "runtime_execution_performed": False,
        "model_api_called": False,
        "external_network_accessed": False,
        "browser_launched": False,
        "file_or_tool_action_performed": False,
        "output_triggered_tool_or_file_authority": False,
        "checkpoint_executed": False,
        "wal_truncate_executed": False,
        "sqlite_state_mutated": False,
        "automatic_runtime_authority_granted": False,
        "ready_for_manual_execution": ready,
        "failures": sorted(set(failures)),
        "required_human_approval": True,
        "next_allowed_action": "human_review_report_before_manual_provider_transport",
    }
    return ModelProviderManualSmokeRunResult(
        output_dir=Path("."),
        report_path=None,
        complete=True,
        ready_for_manual_execution=ready,
        runtime_execution_performed=False,
        model_api_called=False,
        secret_value_read=False,
        secret_value_persisted=False,
        required_human_approval=True,
        report=report,
    )


def write_model_provider_manual_smoke_run(
    *,
    output_dir: Path,
    environ: Mapping[str, str],
    prompt_text: str,
    provider_name: str,
    model_name: str,
    max_output_tokens: int,
    temperature: float,
    request_id: str,
    expected_response_contract: Mapping[str, object] | None = None,
) -> ModelProviderManualSmokeRunResult:
    out = Path(output_dir)
    if not out.exists() or not out.is_dir():
        raise ValueError("output_dir is missing")
    report_path = out / _RUN_FILE
    if report_path.exists():
        raise ValueError("model provider manual smoke run report already exists")
    result = build_model_provider_manual_smoke_run(
        environ=environ,
        prompt_text=prompt_text,
        provider_name=provider_name,
        model_name=model_name,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        request_id=request_id,
        expected_response_contract=expected_response_contract,
    )
    write_json_atomically(report_path, result.report)
    return ModelProviderManualSmokeRunResult(
        output_dir=out,
        report_path=report_path,
        complete=True,
        ready_for_manual_execution=result.ready_for_manual_execution,
        runtime_execution_performed=False,
        model_api_called=False,
        secret_value_read=False,
        secret_value_persisted=False,
        required_human_approval=True,
        report=result.report,
    )


def _validate_inputs(
    *,
    environ: Mapping[str, str],
    prompt_text: str,
    provider_name: str,
    model_name: str,
    max_output_tokens: int,
    temperature: float,
    request_id: str,
    expected_response_contract: Mapping[str, object] | None,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(environ, Mapping):
        failures.append("environ_must_be_mapping")
    if not isinstance(prompt_text, str) or not prompt_text:
        failures.append("prompt_text_missing")
    if not isinstance(provider_name, str) or not provider_name:
        failures.append("provider_name_missing")
    if not isinstance(model_name, str) or not model_name:
        failures.append("model_name_missing")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
        failures.append("max_output_tokens_must_be_integer")
    elif max_output_tokens <= 0:
        failures.append("max_output_tokens_must_be_positive")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        failures.append("temperature_must_be_number")
    elif temperature < 0 or temperature > 2:
        failures.append("temperature_out_of_range")
    if not isinstance(request_id, str) or not request_id:
        failures.append("request_id_missing")
    if expected_response_contract is not None:
        if not isinstance(expected_response_contract, Mapping):
            failures.append("expected_response_contract_must_be_mapping")
        else:
            for forbidden in _FORBIDDEN_PLAN_FIELDS:
                if forbidden in expected_response_contract:
                    failures.append(forbidden + "_forbidden")
    return failures
