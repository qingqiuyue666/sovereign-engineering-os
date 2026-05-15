"""Browser Playwright loopback transport package.

This module defines a disabled-by-default loopback transport package for a
future Playwright execution path. It does not add Playwright as a dependency,
does not import Playwright, and does not launch a browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json

from kernel.personal_ai.adapters.browser_playwright_real_package_admission import (
    verify_browser_playwright_real_package_admission,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserPlaywrightLoopbackTransportPackageResult",
    "build_browser_playwright_loopback_transport_package",
]

_RESULT_FILE = "browser_playwright_loopback_transport_package.json"
_FAILURE_FILE = "browser_playwright_loopback_transport_failure_quarantine.json"
_RESULT_TYPE = "personal_ai_browser_playwright_loopback_transport_package_v1"
_FAILURE_TYPE = "personal_ai_browser_playwright_loopback_transport_failure_v1"
_ENABLE_FLAG = "SEOS_ENABLE_BROWSER_PLAYWRIGHT_LOOPBACK_TRANSPORT_PACKAGE"
_EXPECTED_ENABLE_VALUE = "true"

LoopbackTransport = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class BrowserPlaywrightLoopbackTransportPackageResult:
    output_dir: Path
    result_path: Path | None
    failure_path: Path | None
    status: str
    playwright_dependency_added: bool
    playwright_imported: bool
    browser_launched: bool
    external_network_used: bool
    required_human_approval: bool


def build_browser_playwright_loopback_transport_package(
    admission_path: Path,
    output_dir: Path,
    *,
    environ: Mapping[str, str] | None = None,
    allow_transport_package: bool = False,
    loopback_transport: LoopbackTransport | None = None,
) -> BrowserPlaywrightLoopbackTransportPackageResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    result_path = output_path / _RESULT_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_path)
    _require_no_overwrite(failure_path)
    try:
        verification_path = output_path / "playwright_admission_verification.json"
        verification = verify_browser_playwright_real_package_admission(
            Path(admission_path),
            verification_path,
        )
        if verification.get("complete") is not True:
            raise ValueError("playwright admission verification failed")
        source = {} if environ is None else environ
        if allow_transport_package is not True:
            return _write_denied_result(result_path, admission_path, verification, "disabled_by_callsite")
        if source.get(_ENABLE_FLAG) != _EXPECTED_ENABLE_VALUE:
            return _write_denied_result(result_path, admission_path, verification, "disabled_by_environment_flag")
        if loopback_transport is None:
            return _write_denied_result(result_path, admission_path, verification, "missing_explicit_loopback_transport")
        request = _build_request(admission_path, verification)
        response = loopback_transport(request)
        response_validation = _validate_response(response)
        package = {
            "result_type": _RESULT_TYPE,
            "status": "completed_via_explicit_loopback_transport_package",
            "admission_path": Path(admission_path).as_posix(),
            "admission_sha256": sha256_file(Path(admission_path)),
            "admission_verification": verification,
            "environment_enable_flag": _ENABLE_FLAG,
            "environment_enable_flag_value_matched": True,
            "transport_request": request,
            "transport_response_validation": response_validation,
            "playwright_dependency_added": False,
            "playwright_imported": False,
            "browser_launched": False,
            "external_network_used": False,
            "loopback_only": True,
            "isolated_temp_profile_required": True,
            "real_user_profile_used": False,
            "credential_persistence_used": False,
            "login_performed": False,
            "signup_performed": False,
            "payment_performed": False,
            "raw_dom_persisted": False,
            "screenshot_payload_persisted": False,
            "required_human_approval": True,
            "next_allowed_action": "human_review_playwright_loopback_transport_package",
        }
        write_json_atomically(result_path, package)
        return BrowserPlaywrightLoopbackTransportPackageResult(
            output_dir=output_path,
            result_path=result_path,
            failure_path=None,
            status=str(package["status"]),
            playwright_dependency_added=False,
            playwright_imported=False,
            browser_launched=False,
            external_network_used=False,
            required_human_approval=True,
        )
    except ValueError as error:
        failure = {
            "failure_type": _FAILURE_TYPE,
            "status": "failed_closed",
            "reason": str(error),
            "admission_path": Path(admission_path).as_posix(),
            "playwright_dependency_added": False,
            "playwright_imported": False,
            "browser_launched": False,
            "external_network_used": False,
            "required_human_approval": True,
        }
        write_json_atomically(failure_path, failure)
        return BrowserPlaywrightLoopbackTransportPackageResult(
            output_dir=output_path,
            result_path=None,
            failure_path=failure_path,
            status="failed_closed",
            playwright_dependency_added=False,
            playwright_imported=False,
            browser_launched=False,
            external_network_used=False,
            required_human_approval=True,
        )


def _write_denied_result(result_path: Path, admission_path: Path, verification: dict[str, object], status: str) -> BrowserPlaywrightLoopbackTransportPackageResult:
    package = {
        "result_type": _RESULT_TYPE,
        "status": status,
        "admission_path": Path(admission_path).as_posix(),
        "admission_sha256": sha256_file(Path(admission_path)),
        "admission_verification": verification,
        "environment_enable_flag": _ENABLE_FLAG,
        "loopback_transport_called": False,
        "playwright_dependency_added": False,
        "playwright_imported": False,
        "browser_launched": False,
        "external_network_used": False,
        "loopback_only": True,
        "isolated_temp_profile_required": True,
        "real_user_profile_used": False,
        "credential_persistence_used": False,
        "login_performed": False,
        "signup_performed": False,
        "payment_performed": False,
        "raw_dom_persisted": False,
        "screenshot_payload_persisted": False,
        "required_human_approval": True,
    }
    write_json_atomically(result_path, package)
    return BrowserPlaywrightLoopbackTransportPackageResult(
        output_dir=result_path.parent,
        result_path=result_path,
        failure_path=None,
        status=status,
        playwright_dependency_added=False,
        playwright_imported=False,
        browser_launched=False,
        external_network_used=False,
        required_human_approval=True,
    )


def _build_request(admission_path: Path, verification: dict[str, object]) -> dict[str, object]:
    return {
        "request_type": "personal_ai_browser_playwright_loopback_transport_request_v1",
        "admission_path": Path(admission_path).as_posix(),
        "admission_sha256": sha256_file(Path(admission_path)),
        "verification_complete": verification.get("complete") is True,
        "loopback_only": True,
        "external_network_allowed": False,
        "isolated_temp_profile_required": True,
        "real_user_profile_allowed": False,
        "credential_persistence_allowed": False,
        "login_allowed": False,
        "signup_allowed": False,
        "payment_allowed": False,
        "raw_dom_persistence_allowed": False,
        "screenshot_payload_persistence_allowed": False,
    }


def _validate_response(response: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    if not isinstance(response, dict):
        response = {}
        failures.append("response_malformed")
    if response.get("status") != "ok":
        failures.append("status_not_ok")
    for field_name in (
        "external_network_used",
        "real_user_profile_used",
        "credential_persistence_used",
        "login_performed",
        "signup_performed",
        "payment_performed",
        "raw_dom_persisted",
        "screenshot_payload_persisted",
    ):
        if response.get(field_name) not in (None, False):
            failures.append(field_name)
    return {"complete": not failures, "failures": sorted(set(failures))}


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("playwright loopback transport package output already exists")
