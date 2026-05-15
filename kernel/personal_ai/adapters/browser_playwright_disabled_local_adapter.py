"""Disabled Playwright-like local adapter.

This adapter does not import Playwright and does not launch a browser. It wraps
browser controlled local-smoke plans with an additional Playwright-style contract
that remains disabled by default and loopback-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.adapters.browser_controlled_local_smoke_runner import (
    run_browser_controlled_local_smoke,
)
from kernel.personal_ai.adapters.browser_local_smoke import (
    validate_browser_local_smoke_plan,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserPlaywrightDisabledLocalAdapterResult",
    "run_browser_playwright_disabled_local_adapter",
]

_RESULT_FILE = "browser_playwright_disabled_local_adapter_result.json"
_FAILURE_FILE = "browser_playwright_disabled_local_adapter_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_browser_playwright_disabled_local_adapter_result_v1"
_FAILURE_TYPE = "personal_ai_browser_playwright_disabled_local_adapter_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER"
_EXPECTED_ENABLE_VALUE = "true"

PlaywrightLikeTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class BrowserPlaywrightDisabledLocalAdapterResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    playwright_imported: bool
    real_browser_launched: bool
    external_network_used: bool
    browser_profile_used: bool
    required_human_approval: bool


def run_browser_playwright_disabled_local_adapter(
    plan_path: Path,
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_playwright_adapter: bool = False,
    playwright_transport: PlaywrightLikeTransport | None = None,
) -> BrowserPlaywrightDisabledLocalAdapterResult:
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
        _validate_plan_boundary(plan)
        source = {} if environ is None else environ
        if allow_playwright_adapter is not True:
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
        if playwright_transport is None:
            return _write_denied_result(
                result_path,
                plan_file,
                plan,
                status="missing_explicit_playwright_transport",
            )

        controlled_runner_dir = output_path / "controlled_local_smoke_runner"
        if controlled_runner_dir.exists():
            raise ValueError("controlled local smoke runner dir already exists")
        controlled_runner_dir.mkdir()

        def browser_transport(request: dict[str, object]) -> dict[str, object]:
            adapter_request = _build_playwright_request(plan, plan_file, request)
            response = playwright_transport(adapter_request)
            return _normalize_playwright_response(response)

        runner_result = run_browser_controlled_local_smoke(
            plan_file,
            controlled_runner_dir,
            environ={"SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE": "true"},
            allow_browser_smoke=True,
            browser_transport=browser_transport,
        )
        if runner_result.result_path is None:
            raise ValueError("controlled local smoke runner failed closed")
        runner_payload = _read_plan(runner_result.result_path)
        result = {
            "result_type": _RESULT_TYPE,
            "authority": "non_authority",
            "execution_capability": "explicit_disabled_playwright_like_adapter_only",
            "status": "completed_via_explicit_playwright_like_transport"
            if runner_result.status == "completed_via_explicit_browser_transport"
            else runner_result.status,
            "plan_path": plan_file.as_posix(),
            "plan_sha256": sha256_file(plan_file),
            "target_url": plan.get("target_url"),
            "target_host": plan.get("target_host"),
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "playwright_dependency_added": False,
            "playwright_imported": False,
            "playwright_transport_called": True,
            "real_browser_launched": True,
            "loopback_only": True,
            "external_network_used": False,
            "browser_profile_used": False,
            "persistent_context_used": False,
            "credential_persistence_used": False,
            "login_allowed": False,
            "payment_allowed": False,
            "account_creation_allowed": False,
            "raw_dom_persisted": False,
            "screenshot_payload_persisted": False,
            "controlled_runner_result_path": runner_result.result_path.as_posix(),
            "controlled_runner_status": runner_result.status,
            "controlled_runner_validation_complete": bool(
                runner_payload.get("transport_response_validation", {}).get("complete")
            ),
            "required_human_approval": True,
            "next_allowed_action": "human_review_playwright_local_adapter_result",
        }
        write_json_atomically(result_path, result)
        return BrowserPlaywrightDisabledLocalAdapterResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status=str(result["status"]),
            playwright_imported=False,
            real_browser_launched=True,
            external_network_used=False,
            browser_profile_used=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "plan_path": Path(plan_path).as_posix(),
            "playwright_imported": False,
            "real_browser_launched": False,
            "external_network_used": False,
            "browser_profile_used": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return BrowserPlaywrightDisabledLocalAdapterResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            playwright_imported=False,
            real_browser_launched=False,
            external_network_used=False,
            browser_profile_used=False,
            required_human_approval=True,
        )


def _write_denied_result(
    result_path: Path,
    plan_file: Path,
    plan: dict[str, object],
    *,
    status: str,
) -> BrowserPlaywrightDisabledLocalAdapterResult:
    result = {
        "result_type": _RESULT_TYPE,
        "authority": "non_authority",
        "execution_capability": "playwright_local_adapter_denial_only",
        "status": status,
        "plan_path": plan_file.as_posix(),
        "plan_sha256": sha256_file(plan_file),
        "target_url": plan.get("target_url"),
        "target_host": plan.get("target_host"),
        "environment_enable_flag": _ENABLE_FLAG,
        "playwright_dependency_added": False,
        "playwright_imported": False,
        "playwright_transport_called": False,
        "real_browser_launched": False,
        "loopback_only": True,
        "external_network_used": False,
        "browser_profile_used": False,
        "persistent_context_used": False,
        "credential_persistence_used": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "raw_dom_persisted": False,
        "screenshot_payload_persisted": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_playwright_local_adapter_denial",
    }
    write_json_atomically(result_path, result)
    return BrowserPlaywrightDisabledLocalAdapterResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        playwright_imported=False,
        real_browser_launched=False,
        external_network_used=False,
        browser_profile_used=False,
        required_human_approval=True,
    )


def _build_playwright_request(
    plan: dict[str, object],
    plan_file: Path,
    controlled_request: dict[str, object],
) -> dict[str, object]:
    return {
        "request_type": "personal_ai_browser_playwright_disabled_local_adapter_request_v1",
        "plan_sha256": sha256_file(plan_file),
        "controlled_request": controlled_request,
        "target_url": plan.get("target_url"),
        "target_host": plan.get("target_host"),
        "loopback_only": True,
        "external_network_allowed": False,
        "real_user_profile_allowed": False,
        "persistent_context_allowed": False,
        "credential_persistence_allowed": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "raw_dom_persistence_allowed": False,
        "screenshot_payload_persistence_allowed": False,
    }


def _normalize_playwright_response(response: dict[str, object]) -> dict[str, object]:
    if not isinstance(response, dict):
        return {"status": "malformed_response"}
    return {
        "status": response.get("status"),
        "external_network_used": response.get("external_network_used", False),
        "credential_persistence_used": response.get("credential_persistence_used", False),
        "login_performed": response.get("login_performed", False),
        "payment_performed": response.get("payment_performed", False),
        "account_creation_performed": response.get("account_creation_performed", False),
        "browser_profile_access_performed": response.get("browser_profile_used", False),
        "raw_dom_persisted": response.get("raw_dom_persisted", False),
        "screenshot_payload_persisted": response.get("screenshot_payload_persisted", False),
    }


def _validate_plan_boundary(plan: dict[str, object]) -> None:
    if plan.get("loopback_only") is not True:
        raise ValueError("loopback_only is required")
    for field_name in (
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
    ):
        if plan.get(field_name) is not False:
            raise ValueError(field_name + " must be false")


def _read_plan(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("json artifact is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("json artifact is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("json artifact is malformed")
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("browser playwright disabled local adapter output already exists")
