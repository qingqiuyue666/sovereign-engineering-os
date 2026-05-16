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

from kernel.evidence.sealed_redaction_contract import (
    redacted_digest,
    validate_sealed_evidence_record,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelProviderManualSmokeRunResult",
    "build_model_provider_manual_smoke_run",
    "build_model_provider_smoke_sealed_evidence_payload",
    "write_model_provider_manual_smoke_run",
]

_RUN_FILE = "model_provider_real_smoke_manual_run_report.json"
_RUN_TYPE = "personal_ai_model_provider_real_smoke_manual_run_v1"
_SEALED_EVIDENCE_CONTRACT = "sealed_redaction_v1"
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
    report["sealed_evidence_payload"] = build_model_provider_smoke_sealed_evidence_payload(report)
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


def build_model_provider_smoke_sealed_evidence_payload(
    report: Mapping[str, object]
) -> dict[str, object]:
    """Build a sealed evidence payload for a manual model-provider smoke report.

    The payload carries only hashes, booleans, and boundary metadata. It does not
    include raw prompt text, raw provider response, secret values, or model API
    output. The returned nested evidence object is validated by the sealed
    evidence contract before being embedded in the report.
    """

    request_id = _required_string(report, "request_id")
    evidence_payload = {
        "request_id": request_id,
        "provider_name": _required_string(report, "provider_name"),
        "model_name": _required_string(report, "model_name"),
        "prompt_sha256": _required_string(report, "prompt_sha256"),
        "prompt_length_chars": _required_integer(report, "prompt_length_chars"),
        "manual_flags": _required_mapping(report, "manual_flags"),
        "secret_presence": _redact_secret_presence(_required_mapping(report, "secret_presence")),
        "secret_value_read": False,
        "secret_value_persisted": False,
        "secret_value_serialized": False,
        "raw_prompt_persisted": False,
        "raw_provider_response_persisted": False,
        "runtime_execution_performed": False,
        "model_api_called": False,
        "external_network_accessed": False,
        "file_or_tool_action_performed": False,
        "output_triggered_tool_or_file_authority": False,
        "automatic_runtime_authority_granted": False,
        "required_human_approval": True,
    }
    evidence_record = {
        "evidence_id": "ev-model-provider-smoke-" + request_id,
        "classification": "secret",
        "digest": redacted_digest(evidence_payload),
        "representation": "redacted_digest",
        "payload": evidence_payload,
    }
    validation = validate_sealed_evidence_record(evidence_record)
    if not validation.accepted:
        raise ValueError(
            "model provider smoke sealed evidence contract failed: "
            + "; ".join(validation.failures[:5])
        )
    return {
        "evidence_contract": _SEALED_EVIDENCE_CONTRACT,
        "evidence": evidence_record,
    }


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


def _required_string(report: Mapping[str, object], key: str) -> str:
    value = report.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(key + " is required")
    return value


def _required_integer(report: Mapping[str, object], key: str) -> int:
    value = report.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(key + " must be an integer")
    return value


def _required_mapping(report: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = report.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(key + " must be a mapping")
    return value


def _redact_secret_presence(secret_presence: Mapping[str, object]) -> dict[str, object]:
    return {
        "declared_secret_names_digest": redacted_digest(secret_presence),
        "any_secret_present": any(value is True for value in secret_presence.values()),
        "secret_value_read": False,
        "secret_value_persisted": False,
        "secret_value_serialized": False,
    }
