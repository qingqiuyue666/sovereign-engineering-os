"""Product-grade browser runtime facade."""

from dataclasses import dataclass
from pathlib import Path
import json
import os
from urllib.parse import urlparse

from kernel.personal_ai.adapters.browser_fixture_runtime import (
    run_browser_fixture_from_actions_file,
)
from kernel.personal_ai.adapters.browser_runtime_boundary import (
    boundary_for_browser_runtime,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionDecision,
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
)

__all__ = [
    "BrowserRuntimeResult",
    "build_optional_browser_smoke_status",
    "run_browser_runtime",
]

_RESULT_MANIFEST_FILE = "browser_runtime_result_manifest.json"
_DRY_RUN_PLAN_FILE = "browser_runtime_dry_run_plan.json"
_FAILURE_FILE = "browser_runtime_failure_quarantine.json"
_REAL_RUNTIME_ID = "real_browser_boundary"
_SMOKE_ENV = "SEOS_ENABLE_BROWSER_SMOKE"
_SENSITIVE_TERMS = (
    "account",
    "api_key",
    "checkout",
    "credential",
    "login",
    "password",
    "payment",
    "purchase",
    "register",
    "secret",
    "sign_up",
    "signup",
    "token",
)


@dataclass(frozen=True)
class BrowserRuntimeResult:
    output_dir: Path
    result_manifest_path: Path | None
    dry_run_plan_path: Path | None
    action_log_path: Path | None
    evidence_manifest_path: Path | None
    failure_quarantine_path: Path | None
    success: bool
    real_browser_called: bool
    required_human_approval: bool


def run_browser_runtime(
    output_dir: Path,
    *,
    fixture_path: Path | None = None,
    actions_path: Path | None = None,
    target_url: str | None = None,
    admission_config_path: Path | None = None,
    admission_approval_path: Path | None = None,
    admission_manifest_path: Path | None = None,
    dry_run: bool = True,
) -> BrowserRuntimeResult:
    output_path = Path(output_dir)
    _validate_output_dir(output_path)
    result_manifest_path = output_path / _RESULT_MANIFEST_FILE
    dry_run_plan_path = output_path / _DRY_RUN_PLAN_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(result_manifest_path)
    _require_no_overwrite(dry_run_plan_path)
    _require_no_overwrite(failure_path)

    try:
        if target_url is not None:
            return _run_real_browser_dry_run(
                output_path,
                target_url,
                actions_path=actions_path,
                result_manifest_path=result_manifest_path,
                dry_run_plan_path=dry_run_plan_path,
                admission_config_path=admission_config_path,
                admission_approval_path=admission_approval_path,
                admission_manifest_path=admission_manifest_path,
                dry_run=dry_run,
            )
        return _run_local_fixture_browser(
            output_path,
            fixture_path=fixture_path,
            actions_path=actions_path,
            result_manifest_path=result_manifest_path,
        )
    except ValueError as error:
        _write_failure_quarantine(
            failure_path,
            error,
            fixture_path=fixture_path,
            actions_path=actions_path,
            target_url=target_url,
        )
        return BrowserRuntimeResult(
            output_dir=output_path,
            result_manifest_path=None,
            dry_run_plan_path=None,
            action_log_path=None,
            evidence_manifest_path=None,
            failure_quarantine_path=failure_path,
            success=False,
            real_browser_called=False,
            required_human_approval=True,
        )


def build_optional_browser_smoke_status(
    target_url: str,
    admission_decision: RuntimeAdmissionDecision,
    *,
    environ=None,
) -> dict[str, object]:
    source = os.environ if environ is None else environ
    parsed = urlparse(target_url)
    host = (parsed.hostname or "").lower()
    loopback = host in {"127.0.0.1", "localhost", "::1"}
    explicit_env_enabled = source.get(_SMOKE_ENV) == "true"
    enabled = (
        explicit_env_enabled
        and loopback
        and admission_decision.activation_allowed
    )
    return {
        "smoke_type": "personal_ai_optional_browser_smoke_status_v1",
        "enabled": enabled,
        "disabled_by_default": True,
        "explicit_env_required": _SMOKE_ENV,
        "explicit_env_enabled": explicit_env_enabled,
        "target_url": target_url,
        "loopback_only": True,
        "target_url_is_loopback": loopback,
        "admission_activation_allowed": admission_decision.activation_allowed,
        "real_browser_called": False,
        "credential_persistence_used": False,
    }


def _run_local_fixture_browser(
    output_path: Path,
    *,
    fixture_path: Path | None,
    actions_path: Path | None,
    result_manifest_path: Path,
) -> BrowserRuntimeResult:
    if fixture_path is None:
        raise ValueError("fixture_path is required")
    if actions_path is None:
        raise ValueError("actions_path is required")
    fixture_result = run_browser_fixture_from_actions_file(
        Path(fixture_path),
        Path(actions_path),
        output_path,
    )
    manifest = {
        "manifest_type": "personal_ai_browser_runtime_result_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "deterministic_local_fixture_only",
        "runtime_id": "local_fixture_browser",
        "fixture_path": fixture_result.fixture_path.as_posix(),
        "fixture_sha256": sha256_file(fixture_result.fixture_path),
        "actions_path": Path(actions_path).as_posix(),
        "actions_sha256": sha256_file(Path(actions_path)),
        "browser_action_log_path": fixture_result.action_log_path.as_posix(),
        "browser_action_log_sha256": sha256_file(fixture_result.action_log_path),
        "browser_evidence_manifest_path": (
            fixture_result.evidence_manifest_path.as_posix()
        ),
        "browser_evidence_manifest_sha256": sha256_file(
            fixture_result.evidence_manifest_path
        ),
        "real_browser_called": False,
        "playwright_runtime_used": False,
        "selenium_runtime_used": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "login_performed": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "real_screenshot_captured": False,
        "screenshot_evidence_mode": "dom_metadata_only_fixture",
        "required_human_approval": True,
    }
    write_json_atomically(result_manifest_path, manifest)
    return BrowserRuntimeResult(
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=None,
        action_log_path=fixture_result.action_log_path,
        evidence_manifest_path=fixture_result.evidence_manifest_path,
        failure_quarantine_path=None,
        success=True,
        real_browser_called=False,
        required_human_approval=True,
    )


def _run_real_browser_dry_run(
    output_path: Path,
    target_url: str,
    *,
    actions_path: Path | None,
    result_manifest_path: Path,
    dry_run_plan_path: Path,
    admission_config_path: Path | None,
    admission_approval_path: Path | None,
    admission_manifest_path: Path | None,
    dry_run: bool,
) -> BrowserRuntimeResult:
    if actions_path is None:
        raise ValueError("actions_path is required")
    if dry_run is not True:
        raise ValueError("real browser execution is disabled by default")
    boundary = boundary_for_browser_runtime(_REAL_RUNTIME_ID)
    config = _read_optional_json(admission_config_path)
    allowed_domains = tuple(config.get("allowed_domains", boundary.allowed_domains))
    action_records = _read_real_browser_actions(Path(actions_path), boundary)
    host = _validate_target_url(target_url, allowed_domains)
    admission = evaluate_runtime_admission(
        RuntimeAdmissionRequest(
            adapter_id=boundary.adapter_id,
            capability=boundary.capability,
            runtime_class=boundary.runtime_class,
            config_artifact_path=admission_config_path,
            human_approval_artifact_path=admission_approval_path,
            manifest_artifact_path=admission_manifest_path,
            dry_run=True,
            activation_sources=("human_approval_artifact",),
        )
    )
    if not admission.admitted:
        raise ValueError(
            "browser runtime admission denied: "
            + ",".join(admission.reason_codes)
        )

    dry_run_plan = {
        "plan_type": "personal_ai_browser_runtime_dry_run_plan_v1",
        "authority": "non_authority",
        "execution_capability": "dry_run_browser_boundary_only",
        "runtime_id": boundary.runtime_id,
        "target_url": target_url,
        "target_host": host,
        "allowed_domains": list(allowed_domains),
        "actions_path": Path(actions_path).as_posix(),
        "actions_sha256": sha256_file(Path(actions_path)),
        "validated_actions": action_records,
        "playwright_boundary_declared": True,
        "selenium_boundary_declared": True,
        "real_browser_called": False,
        "network_used": False,
        "credential_persistence_used": False,
        "login_performed": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "screenshot_evidence_required": True,
        "real_screenshot_captured": False,
        "runtime_admission_decision": admission.to_dict(),
        "required_human_approval": True,
    }
    result_manifest = {
        "manifest_type": "personal_ai_browser_runtime_result_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "dry_run_browser_boundary_only",
        "runtime_id": boundary.runtime_id,
        "target_url": target_url,
        "target_host": host,
        "dry_run_plan_path": dry_run_plan_path.as_posix(),
        "real_browser_runtime": True,
        "real_browser_enabled_by_default": False,
        "real_browser_called": False,
        "playwright_runtime_used": False,
        "selenium_runtime_used": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "login_performed": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "screenshot_evidence_required": True,
        "real_screenshot_captured": False,
        "failure_quarantine_required": True,
        "runtime_admission_decision": admission.to_dict(),
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(dry_run_plan_path, dry_run_plan)
    write_json_atomically(result_manifest_path, result_manifest)
    return BrowserRuntimeResult(
        output_dir=output_path,
        result_manifest_path=result_manifest_path,
        dry_run_plan_path=dry_run_plan_path,
        action_log_path=None,
        evidence_manifest_path=None,
        failure_quarantine_path=None,
        success=True,
        real_browser_called=False,
        required_human_approval=True,
    )


def _validate_output_dir(output_path: Path) -> None:
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("browser runtime output already exists")


def _read_optional_json(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("browser runtime config is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError("browser runtime config must be an object")
    return payload


def _read_real_browser_actions(
    actions_path: Path,
    boundary,
) -> list[dict[str, object]]:
    if not actions_path.exists() or not actions_path.is_file():
        raise ValueError("actions_path is missing")
    try:
        payload = json.loads(actions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("actions_path is malformed") from error
    actions = payload.get("actions") if isinstance(payload, dict) else payload
    if not isinstance(actions, list):
        raise ValueError("browser actions are malformed")
    records = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("browser action is malformed")
        action_name = str(action.get("action", ""))
        if action_name not in boundary.allowed_actions:
            raise ValueError("browser action is not allowed")
        if _contains_sensitive_intent(action):
            raise ValueError("sensitive browser action is not allowed")
        records.append(
            {
                "index": index,
                "action": action_name,
                "parameter_keys": sorted(str(key) for key in action),
            }
        )
    return records


def _validate_target_url(target_url: str, allowed_domains: tuple[str, ...]) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("browser target_url scheme is not allowed")
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("external browser target_url is denied by default")
    if host not in allowed_domains and not (host == "::1" and "localhost" in allowed_domains):
        raise ValueError("browser target host is not in domain allowlist")
    return host


def _contains_sensitive_intent(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_sensitive_intent(str(key))
            or _contains_sensitive_intent(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_intent(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(term in lowered for term in _SENSITIVE_TERMS)
    return False


def _write_failure_quarantine(
    failure_path: Path,
    error: ValueError,
    *,
    fixture_path: Path | None,
    actions_path: Path | None,
    target_url: str | None,
) -> None:
    payload = {
        "failure_type": "personal_ai_browser_runtime_failure_quarantine_v1",
        "authority": "non_authority",
        "execution_capability": "browser_runtime_boundary_only",
        "fixture_path": None if fixture_path is None else Path(fixture_path).as_posix(),
        "fixture_sha256": sha256_file(Path(fixture_path))
        if fixture_path is not None and Path(fixture_path).exists()
        else None,
        "actions_path": None if actions_path is None else Path(actions_path).as_posix(),
        "actions_sha256": sha256_file(Path(actions_path))
        if actions_path is not None and Path(actions_path).exists()
        else None,
        "target_url": target_url,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "real_browser_called": False,
        "playwright_runtime_used": False,
        "selenium_runtime_used": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "login_performed": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)
