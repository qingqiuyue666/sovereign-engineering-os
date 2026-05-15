"""Explicit model-provider transport contract.

This module defines strict request/response validation for a future provider
transport. It does not perform network I/O and does not persist secrets.
"""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ModelProviderTransportRequest",
    "ModelProviderTransportResponse",
    "build_live_smoke_transport_request",
    "validate_transport_request",
    "validate_transport_response",
    "write_transport_validation_report",
]

_REQUEST_TYPE = "personal_ai_model_provider_live_smoke_transport_request_v1"
_RESPONSE_TYPE = "personal_ai_model_provider_live_smoke_transport_response_v1"
_VALIDATION_TYPE = "personal_ai_model_provider_transport_validation_v1"


@dataclass(frozen=True)
class ModelProviderTransportRequest:
    provider_id: str
    plan_sha256: str
    prompt: str
    timeout_seconds: int
    max_budget_usd: float
    schema_name: str
    tool_calls_allowed: bool = False
    file_edits_allowed: bool = False
    raw_prompt_contains_secret: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "request_type": _REQUEST_TYPE,
            "provider_id": self.provider_id,
            "plan_sha256": self.plan_sha256,
            "prompt": self.prompt,
            "timeout_seconds": self.timeout_seconds,
            "max_budget_usd": self.max_budget_usd,
            "schema_name": self.schema_name,
            "schema_validation_required": True,
            "tool_calls_allowed": self.tool_calls_allowed,
            "file_edits_allowed": self.file_edits_allowed,
            "raw_prompt_contains_secret": self.raw_prompt_contains_secret,
            "expected_schema": {
                "type": "object",
                "required_keys": ["status", "provider_id"],
                "status_allowed_values": ["ok"],
            },
        }


@dataclass(frozen=True)
class ModelProviderTransportResponse:
    provider_id: str
    status: str
    response_metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "response_type": _RESPONSE_TYPE,
            "provider_id": self.provider_id,
            "status": self.status,
            "response_metadata": dict(self.response_metadata),
            "tool_call_requested": False,
            "file_edit_requested": False,
            "raw_provider_response_persisted": False,
        }


def build_live_smoke_transport_request(
    *,
    provider_id: str,
    plan_sha256: str,
    timeout_seconds: int = 20,
    max_budget_usd: float = 0.01,
    schema_name: str = "live_smoke_status_v1",
) -> dict[str, object]:
    request = ModelProviderTransportRequest(
        provider_id=provider_id,
        plan_sha256=plan_sha256,
        prompt="Return a minimal valid JSON object: {\"status\": \"ok\", \"provider_id\": \"%s\"}." % provider_id,
        timeout_seconds=timeout_seconds,
        max_budget_usd=max_budget_usd,
        schema_name=schema_name,
    ).to_dict()
    failures = validate_transport_request(request)["failures"]
    if failures:
        raise ValueError("transport request is invalid: " + ",".join(failures))
    return request


def validate_transport_request(request: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(request, dict):
        return _validation(False, ["request_malformed"], "request")
    if request.get("request_type") != _REQUEST_TYPE:
        failures.append("request_type_mismatch")
    if not isinstance(request.get("provider_id"), str) or not request.get("provider_id"):
        failures.append("provider_id_missing")
    if not isinstance(request.get("plan_sha256"), str) or len(str(request.get("plan_sha256"))) < 32:
        failures.append("plan_sha256_missing")
    if not isinstance(request.get("prompt"), str) or not request.get("prompt"):
        failures.append("prompt_missing")
    if request.get("schema_validation_required") is not True:
        failures.append("schema_validation_required")
    if request.get("tool_calls_allowed") is not False:
        failures.append("tool_calls_must_be_false")
    if request.get("file_edits_allowed") is not False:
        failures.append("file_edits_must_be_false")
    if request.get("raw_prompt_contains_secret") is not False:
        failures.append("raw_prompt_contains_secret_must_be_false")
    timeout = request.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout <= 0 or timeout > 60:
        failures.append("timeout_seconds_out_of_range")
    budget = request.get("max_budget_usd")
    if not isinstance(budget, (int, float)) or budget < 0 or budget > 0.05:
        failures.append("max_budget_usd_out_of_range")
    schema = request.get("expected_schema")
    if not isinstance(schema, dict):
        failures.append("expected_schema_missing")
    return _validation(not failures, failures, "request")


def validate_transport_response(response: dict[str, object], provider_id: str | None = None) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        return _validation(False, ["response_malformed"], "response")
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    actual_provider = response.get("provider_id")
    if not isinstance(actual_provider, str) or not actual_provider:
        failures.append("provider_id_missing")
    if provider_id is not None and actual_provider != provider_id:
        failures.append("provider_id_mismatch")
    if response.get("tool_call_requested") not in (None, False):
        failures.append("tool_call_requested")
    if response.get("file_edit_requested") not in (None, False):
        failures.append("file_edit_requested")
    if response.get("raw_provider_response_persisted") not in (None, False):
        failures.append("raw_provider_response_persisted")
    return _validation(not failures, failures, "response")


def write_transport_validation_report(
    output_path: Path,
    *,
    request: dict[str, object],
    response: dict[str, object] | None = None,
) -> dict[str, object]:
    report_path = Path(output_path)
    if report_path.exists():
        raise ValueError("transport validation report already exists")
    if not report_path.parent.exists() or not report_path.parent.is_dir():
        raise ValueError("transport validation report parent is missing")
    request_validation = validate_transport_request(request)
    provider_id = request.get("provider_id") if isinstance(request, dict) else None
    response_validation = None
    if response is not None:
        response_validation = validate_transport_response(
            response,
            provider_id=provider_id if isinstance(provider_id, str) else None,
        )
    report = {
        "validation_type": _VALIDATION_TYPE,
        "request_validation": request_validation,
        "response_validation": response_validation,
        "complete": request_validation["complete"] and (
            response_validation is None or response_validation["complete"]
        ),
        "network_performed_by_validator": False,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "raw_provider_response_persisted": False,
    }
    write_json_atomically(report_path, report)
    return report


def _validation(complete: bool, failures: list[str], subject: str) -> dict[str, object]:
    return {
        "subject": subject,
        "complete": complete,
        "failures": sorted(set(failures)),
        "schema_validation_performed": True,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "raw_secret_material_allowed": False,
    }
