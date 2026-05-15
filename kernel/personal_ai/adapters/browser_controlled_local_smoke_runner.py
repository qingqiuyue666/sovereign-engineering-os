"""Controlled local browser smoke runner.

This module does not launch a real browser. It validates a loopback-only smoke
plan and can call an explicitly injected local browser transport. Normal tests
exercise denied and fake transport paths only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.adapters.browser_local_smoke import (
    validate_browser_local_smoke_plan,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserControlledLocalSmokeRunnerResult",
    "run_browser_controlled_local_smoke",
]

_RESULT_FILE = "browser_controlled_local_smoke_result.json"
_FAILURE_FILE = "browser_controlled_local_smoke_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_browser_controlled_local_smoke_result_v1"
_FAILURE_TYPE = "personal_ai_browser_controlled_local_smoke_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE"
_EXPECTED_ENABLE_VALUE = "true"

BrowserLocalTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class BrowserControlledLocalSmokeRunnerResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    real_browser_called: bool
    external_network_used: bool
    credential_persistence_used: bool
    required_human_approval: bool


def run_browser_controlled_local_smoke(
    plan_path: Path,
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_browser_smoke: bool = False,
    browser_transport: BrowserLocalTransport | None = None,
) -> BrowserControlledLocalSmokeRunnerResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        plan_file = Path(plan_path)
        validation = validate_browser_local_smoke_plan(plan_file)
        if not validation["complete"]:
            raise ValueError("browser local smoke plan validation failed")
        plan = _read_plan(plan_file)
        _validate_plan_runtime_boundary(plan)
        source = {} if environ is None else environ
        if allow_browser_smoke is not True:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="disabled_by_callsite",
            )
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="disabled_by_environment_flag",
            )
        if browser_transport is None:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="missing_explicit_browser_transport",
            )
        request = _build_transport_request(plan, plan_file)
        response = browser_transport(request)
        response_validation = _validate_transport_response(response)
        result = {
            "result_type": _RESULT_TYPE,
            "authority": "non_authority",
            "execution_capability": "explicit_loopback_browser_smoke_only",
            "status": "completed_via_explicit_browser_transport",
            "plan_path": plan_file.as_posix(),
            "plan_sha256": sha256_file(plan_file),
            "target_url": plan.get("target_url"),
            "target_host": plan.get("target_host"),
            "allow_browser_smoke": True,
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "browser_transport_required": True,
            "browser_transport_called": True,
            "real_browser_called": True,
            "loopback_only": True,
            "external_network_used": False,
            "credential_persistence_used": False,
            "login_allowed": False,
            "payment_allowed": False,
            "account_creation_allowed": False,
            "browser_profile_access_allowed": False,
            "browser_profile_access_performed": False,
            "screenshot_payload_persisted": False,
            "raw_dom_persisted": False,
            "transport_response_validation": response_validation,
            "required_human_approval": True,
            "next_allowed_action": "human_review_browser_local_smoke_result",
        }
        write_json_atomically(result_path, result)
        return BrowserControlledLocalSmokeRunnerResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status="completed_via_explicit_browser_transport",
            real_browser_called=True,
            external_network_used=False,
            credential_persistence_used=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "plan_path": Path(plan_path).as_posix(),
            "real_browser_called": False,
            "external_network_used": False,
            "credential_persistence_used": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return BrowserControlledLocalSmokeRunnerResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            real_browser_called=False,
            external_network_used=False,
            credential_persistence_used=False,
            required_human_approval=True,
        )


def _write_denied_result(
    result_path: Path,
    plan_file: Path,
    plan: dict[str, object],
    *,
    status: str,
) -> BrowserControlledLocalSmokeRunnerResult:
    result = {
        "result_type": _RESULT_TYPE,
        "authority": "non_authority",
        "execution_capability": "browser_local_smoke_denial_only",
        "status": status,
        "plan_path": plan_file.as_posix(),
        "plan_sha256": sha256_file(plan_file),
        "target_url": plan.get("target_url"),
        "target_host": plan.get("target_host"),
        "allow_browser_smoke": False,
        "environment_enable_flag": _ENABLE_FLAG,
        "browser_transport_called": False,
        "real_browser_called": False,
        "loopback_only": True,
        "external_network_used": False,
        "credential_persistence_used": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "browser_profile_access_allowed": False,
        "browser_profile_access_performed": False,
        "screenshot_payload_persisted": False,
        "raw_dom_persisted": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_browser_local_smoke_denial",
    }
    write_json_atomically(result_path, result)
    return BrowserControlledLocalSmokeRunnerResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        real_browser_called=False,
        external_network_used=False,
        credential_persistence_used=False,
        required_human_approval=True,
    )


def _build_transport_request(plan: dict[str, object], plan_file: Path) -> dict[str, object]:
    return {
        "request_type": "personal_ai_browser_controlled_local_smoke_transport_request_v1",
        "plan_sha256": sha256_file(plan_file),
        "target_url": plan.get("target_url"),
        "target_host": plan.get("target_host"),
        "loopback_only": True,
        "allowed_actions": plan.get("allowed_actions", []),
        "real_browser_profile_allowed": False,
        "external_network_allowed": False,
        "credential_persistence_allowed": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "raw_dom_persistence_allowed": False,
        "screenshot_payload_persistence_allowed": False,
    }


def _validate_transport_response(response: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        failures.append("response_malformed")
        response = {}
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    for field_name in (
        "external_network_used",
        "credential_persistence_used",
        "login_performed",
        "payment_performed",
        "account_creation_performed",
        "browser_profile_access_performed",
        "raw_dom_persisted",
        "screenshot_payload_persisted",
    ):
        if response.get(field_name) not in (None, False):
            failures.append(field_name)
    return {
        "complete": not failures,
        "failures": sorted(set(failures)),
        "schema_validation_performed": True,
        "external_network_allowed": False,
        "credential_persistence_allowed": False,
        "raw_dom_persistence_allowed": False,
    }


def _validate_plan_runtime_boundary(plan: dict[str, object]) -> None:
    required_false = (
        "external_url_allowed",
        "browser_smoke_enabled",
        "real_browser_called",
        "playwright_runtime_used",
        "selenium_runtime_used",
        "external_network_used",
        "credential_persistence_used",
        "login_allowed",
        "payment_allowed",
        "account_creation_allowed",
    )
    for field_name in required_false:
        if plan.get(field_name) is not False:
            raise ValueError(field_name + " must be false")
    if plan.get("loopback_only") is not True:
        raise ValueError("loopback_only is required")


def _read_plan(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("browser local smoke plan is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("browser local smoke plan is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("browser local smoke plan is malformed")
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("browser controlled local smoke output already exists")
