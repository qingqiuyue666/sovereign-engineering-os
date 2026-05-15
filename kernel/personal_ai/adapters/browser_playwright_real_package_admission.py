"""Playwright real package admission.

This module creates and verifies an admission package for a future real
Playwright loopback transport. It does not add the Playwright dependency, import
Playwright, launch a browser, or perform network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserPlaywrightRealPackageAdmissionResult",
    "build_browser_playwright_real_package_admission",
    "verify_browser_playwright_real_package_admission",
]

_ADMISSION_FILE = "browser_playwright_real_package_admission.json"
_VERIFICATION_FILE = "browser_playwright_real_package_admission_verification.json"
_ADMISSION_TYPE = "personal_ai_browser_playwright_real_package_admission_v1"
_VERIFICATION_TYPE = "personal_ai_browser_playwright_real_package_admission_verification_v1"
_ALLOWED_PACKAGE_NAME = "playwright"


@dataclass(frozen=True)
class BrowserPlaywrightRealPackageAdmissionResult:
    output_dir: Path
    admission_path: Path
    verification_path: Path
    complete: bool
    package_name: str
    admitted: bool
    dependency_added: bool
    playwright_imported: bool
    browser_launched: bool
    required_human_approval: bool


def build_browser_playwright_real_package_admission(
    output_dir: Path,
    *,
    package_name: str = _ALLOWED_PACKAGE_NAME,
    package_version_spec: str = "playwright>=1.45,<2",
    target_url_policy: str = "loopback_only",
    profile_policy: str = "isolated_temp_profile_only",
    network_policy: str = "no_external_network",
) -> BrowserPlaywrightRealPackageAdmissionResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    admission_path = output_path / _ADMISSION_FILE
    verification_path = output_path / _VERIFICATION_FILE
    _require_no_overwrite(admission_path)
    _require_no_overwrite(verification_path)
    _validate_inputs(
        package_name=package_name,
        package_version_spec=package_version_spec,
        target_url_policy=target_url_policy,
        profile_policy=profile_policy,
        network_policy=network_policy,
    )
    admission = {
        "admission_type": _ADMISSION_TYPE,
        "package_name": package_name,
        "package_version_spec": package_version_spec,
        "target_url_policy": target_url_policy,
        "profile_policy": profile_policy,
        "network_policy": network_policy,
        "admission_status": "candidate_only_not_installed",
        "admitted_for_installation": False,
        "dependency_added": False,
        "playwright_imported": False,
        "browser_launched": False,
        "external_network_allowed": False,
        "external_network_used": False,
        "loopback_only": True,
        "real_user_profile_allowed": False,
        "isolated_temp_profile_required": True,
        "persistent_context_allowed": False,
        "credential_persistence_allowed": False,
        "login_allowed": False,
        "signup_allowed": False,
        "account_creation_allowed": False,
        "payment_allowed": False,
        "raw_dom_persistence_allowed": False,
        "screenshot_payload_persistence_allowed_by_default": False,
        "normal_tests_must_not_launch_browser": True,
        "normal_tests_must_not_access_external_network": True,
        "future_transport_must_be_disabled_by_default": True,
        "future_transport_requires_explicit_env_flag": True,
        "future_transport_requires_human_review": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_playwright_real_package_admission",
    }
    write_json_atomically(admission_path, admission)
    verification = _build_verification(admission_path, admission)
    write_json_atomically(verification_path, verification)
    return BrowserPlaywrightRealPackageAdmissionResult(
        output_dir=output_path,
        admission_path=admission_path,
        verification_path=verification_path,
        complete=bool(verification["complete"]),
        package_name=package_name,
        admitted=False,
        dependency_added=False,
        playwright_imported=False,
        browser_launched=False,
        required_human_approval=True,
    )


def verify_browser_playwright_real_package_admission(
    admission_path: Path,
    output_path: Path,
) -> dict[str, object]:
    if Path(output_path).exists():
        raise ValueError("output_path already exists")
    if not Path(output_path).parent.exists() or not Path(output_path).parent.is_dir():
        raise ValueError("output_path parent is missing")
    admission = _read_json(Path(admission_path))
    verification = _build_verification(Path(admission_path), admission)
    write_json_atomically(Path(output_path), verification)
    return verification


def _build_verification(admission_path: Path, admission: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    expected_false = (
        "admitted_for_installation",
        "dependency_added",
        "playwright_imported",
        "browser_launched",
        "external_network_allowed",
        "external_network_used",
        "real_user_profile_allowed",
        "persistent_context_allowed",
        "credential_persistence_allowed",
        "login_allowed",
        "signup_allowed",
        "account_creation_allowed",
        "payment_allowed",
        "raw_dom_persistence_allowed",
        "screenshot_payload_persistence_allowed_by_default",
    )
    for field_name in expected_false:
        if admission.get(field_name) is not False:
            failures.append(field_name + "_must_be_false")
    expected_true = (
        "loopback_only",
        "isolated_temp_profile_required",
        "normal_tests_must_not_launch_browser",
        "normal_tests_must_not_access_external_network",
        "future_transport_must_be_disabled_by_default",
        "future_transport_requires_explicit_env_flag",
        "future_transport_requires_human_review",
        "required_human_approval",
    )
    for field_name in expected_true:
        if admission.get(field_name) is not True:
            failures.append(field_name + "_must_be_true")
    if admission.get("admission_type") != _ADMISSION_TYPE:
        failures.append("admission_type_mismatch")
    if admission.get("package_name") != _ALLOWED_PACKAGE_NAME:
        failures.append("package_name_mismatch")
    if admission.get("target_url_policy") != "loopback_only":
        failures.append("target_url_policy_mismatch")
    if admission.get("profile_policy") != "isolated_temp_profile_only":
        failures.append("profile_policy_mismatch")
    if admission.get("network_policy") != "no_external_network":
        failures.append("network_policy_mismatch")
    return {
        "verification_type": _VERIFICATION_TYPE,
        "admission_path": admission_path.as_posix(),
        "admission_sha256": sha256_file(admission_path),
        "complete": not failures,
        "failures": sorted(set(failures)),
        "dependency_added": False,
        "playwright_imported": False,
        "browser_launched": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "required_human_approval": True,
    }


def _validate_inputs(
    *,
    package_name: str,
    package_version_spec: str,
    target_url_policy: str,
    profile_policy: str,
    network_policy: str,
) -> None:
    if package_name != _ALLOWED_PACKAGE_NAME:
        raise ValueError("package_name must be playwright")
    if not package_version_spec.startswith("playwright"):
        raise ValueError("package_version_spec must target playwright")
    if target_url_policy != "loopback_only":
        raise ValueError("target_url_policy must be loopback_only")
    if profile_policy != "isolated_temp_profile_only":
        raise ValueError("profile_policy must be isolated_temp_profile_only")
    if network_policy != "no_external_network":
        raise ValueError("network_policy must be no_external_network")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        raise ValueError("admission artifact is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("admission artifact is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("admission artifact is malformed")
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("playwright real package admission output already exists")
