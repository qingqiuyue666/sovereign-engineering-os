"""Disabled-by-default OpenAI explicit transport adapter.

This adapter uses only stdlib HTTP primitives, is excluded from normal live
network execution by default, and requires an explicit caller gate plus an
environment gate before attempting any injected/http transport path.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json
import os
import urllib.error
import urllib.request

from kernel.personal_ai.adapters.model_provider_transport_adapter import (
    validate_transport_request,
    validate_transport_response,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "OpenAIExplicitTransportResult",
    "build_openai_explicit_transport",
    "run_openai_explicit_transport",
]

_RESULT_FILE = "openai_explicit_transport_result.json"
_FAILURE_FILE = "openai_explicit_transport_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_openai_explicit_transport_result_v1"
_FAILURE_TYPE = "personal_ai_openai_explicit_transport_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT"
_EXPECTED_ENABLE_VALUE = "true"
_API_KEY_ENV = "OPENAI_API_KEY"
_DEFAULT_URL = "https://api.openai.com/v1/responses"

HttpTransport = Callable[[dict[str, object], str], dict[str, object]]


@dataclass(frozen=True)
class OpenAIExplicitTransportResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    network_call_performed: bool
    api_key_value_persisted: bool
    api_key_value_logged: bool


def build_openai_explicit_transport(*, model: str = "gpt-5.5") -> dict[str, object]:
    if not model:
        raise ValueError("model is required")
    return {
        "transport_id": "openai_explicit_transport_v1",
        "provider_id": "openai",
        "transport_type": "explicit_disabled_by_default",
        "model": model,
        "endpoint": _DEFAULT_URL,
        "api_key_source": "environment_only",
        "api_key_env_var": _API_KEY_ENV,
        "enabled_by_default": False,
        "requires_callsite_allow": True,
        "requires_environment_flag": _ENABLE_FLAG,
        "normal_tests_must_not_call_network": True,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "raw_provider_response_persisted": False,
    }


def run_openai_explicit_transport(
    request: dict[str, object],
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_network: bool = False,
    http_transport: HttpTransport | None = None,
    model: str = "gpt-5.5",
) -> OpenAIExplicitTransportResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        request_validation = validate_transport_request(request)
        if not request_validation["complete"]:
            raise ValueError("transport request validation failed")
        source = os.environ if environ is None else environ
        api_key_present = bool(source.get(_API_KEY_ENV, ""))
        if allow_network is not True:
            return _write_denied_result(
                result_path,
                request,
                status="disabled_by_callsite",
                api_key_present=api_key_present,
                request_validation=request_validation,
            )
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(
                result_path,
                request,
                status="disabled_by_environment_flag",
                api_key_present=api_key_present,
                request_validation=request_validation,
            )
        api_key = source.get(_API_KEY_ENV, "")
        if not api_key:
            return _write_denied_result(
                result_path,
                request,
                status="missing_openai_api_key",
                api_key_present=False,
                request_validation=request_validation,
            )
        if http_transport is None:
            return _write_denied_result(
                result_path,
                request,
                status="missing_explicit_http_transport",
                api_key_present=True,
                request_validation=request_validation,
            )
        provider_response = http_transport(_build_http_payload(request, model), api_key)
        response_validation = validate_transport_response(
            provider_response,
            provider_id="openai",
        )
        result = {
            "result_type": _RESULT_TYPE,
            "transport_id": "openai_explicit_transport_v1",
            "provider_id": "openai",
            "status": "completed_via_explicit_http_transport",
            "model": model,
            "request_validation": request_validation,
            "response_validation": response_validation,
            "allow_network": True,
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "api_key_source": "environment_only",
            "api_key_env_var": _API_KEY_ENV,
            "api_key_present": True,
            "api_key_value_persisted": False,
            "api_key_value_logged": False,
            "http_transport_called": True,
            "network_call_performed": True,
            "tool_calls_allowed": False,
            "tool_calls_performed": False,
            "file_edits_allowed": False,
            "file_edits_performed": False,
            "raw_provider_response_persisted": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_openai_explicit_transport_result",
        }
        write_json_atomically(result_path, result)
        return OpenAIExplicitTransportResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_via_explicit_http_transport",
            network_call_performed=True,
            api_key_value_persisted=False,
            api_key_value_logged=False,
        )
    except (ValueError, urllib.error.URLError) as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "network_call_performed": False,
            "api_key_value_persisted": False,
            "api_key_value_logged": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return OpenAIExplicitTransportResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            network_call_performed=False,
            api_key_value_persisted=False,
            api_key_value_logged=False,
        )


def _build_http_payload(request: dict[str, object], model: str) -> dict[str, object]:
    return {
        "model": model,
        "input": request.get("prompt"),
        "text": {"format": {"type": "json_object"}},
        "tools": [],
        "metadata": {
            "provider_id": "openai",
            "smoke": "true",
            "tool_calls_allowed": "false",
            "file_edits_allowed": "false",
        },
    }


def _write_denied_result(
    result_path: Path,
    request: dict[str, object],
    *,
    status: str,
    api_key_present: bool,
    request_validation: dict[str, object],
) -> OpenAIExplicitTransportResult:
    result = {
        "result_type": _RESULT_TYPE,
        "transport_id": "openai_explicit_transport_v1",
        "provider_id": "openai",
        "status": status,
        "request_validation": request_validation,
        "allow_network": False,
        "environment_enable_flag": _ENABLE_FLAG,
        "api_key_source": "environment_only",
        "api_key_env_var": _API_KEY_ENV,
        "api_key_present": api_key_present,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "http_transport_called": False,
        "network_call_performed": False,
        "tool_calls_allowed": False,
        "tool_calls_performed": False,
        "file_edits_allowed": False,
        "file_edits_performed": False,
        "raw_provider_response_persisted": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_openai_explicit_transport_denial",
    }
    write_json_atomically(result_path, result)
    return OpenAIExplicitTransportResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        network_call_performed=False,
        api_key_value_persisted=False,
        api_key_value_logged=False,
    )


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("openai explicit transport output already exists")


def stdlib_openai_responses_transport(payload: dict[str, object], api_key: str) -> dict[str, object]:
    """Optional stdlib transport helper. Not used by normal tests.

    The caller must pass this explicitly into run_openai_explicit_transport.
    """

    if not api_key:
        raise ValueError("api_key is required")
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _DEFAULT_URL,
        data=data,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw_payload = json.loads(response.read().decode("utf-8"))
    return {
        "status": "ok",
        "provider_id": "openai",
        "response_metadata": {
            "response_id_present": bool(raw_payload.get("id")),
            "raw_response_persisted": False,
        },
        "tool_call_requested": False,
        "file_edit_requested": False,
        "raw_provider_response_persisted": False,
    }
