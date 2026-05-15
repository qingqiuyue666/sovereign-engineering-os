"""Controlled local-browser smoke plan.

This module does not launch a browser. It validates that a future browser smoke
plan remains loopback-only, non-credentialed, and disabled by default.
"""

from dataclasses import dataclass
from pathlib import Path
import json
from urllib.parse import urlparse

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserLocalSmokePlanResult",
    "build_browser_local_smoke_plan",
    "validate_browser_local_smoke_plan",
]

_PLAN_FILE = "browser_local_smoke_plan.json"
_VALIDATION_FILE = "browser_local_smoke_validation.json"
_PLAN_TYPE = "personal_ai_browser_local_smoke_plan_v1"
_VALIDATION_TYPE = "personal_ai_browser_local_smoke_validation_v1"
_FORBIDDEN_INTENTS = (
    "account",
    "checkout",
    "credential",
    "login",
    "password",
    "payment",
    "purchase",
    "register",
    "secret",
    "signup",
    "token",
)
_ALLOWED_ACTIONS = ("open", "assert_text", "capture_dom_summary")


@dataclass(frozen=True)
class BrowserLocalSmokePlanResult:
    output_dir: Path
    plan_path: Path
    validation_path: Path
    complete: bool
    real_browser_called: bool
    external_network_used: bool
    required_human_approval: bool


def build_browser_local_smoke_plan(
    actions_path: Path,
    output_dir: Path,
    *,
    target_url: str,
) -> BrowserLocalSmokePlanResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    actions_file = Path(actions_path)
    actions = _read_actions(actions_file)
    host = _validate_target_url(target_url)
    plan_path = output_path / _PLAN_FILE
    validation_path = output_path / _VALIDATION_FILE
    _require_no_overwrite(plan_path)
    _require_no_overwrite(validation_path)
    plan = {
        "plan_type": _PLAN_TYPE,
        "authority": "non_authority",
        "execution_capability": "controlled_local_browser_smoke_plan_only",
        "target_url": target_url,
        "target_host": host,
        "loopback_only": True,
        "external_url_allowed": False,
        "browser_smoke_enabled": False,
        "real_browser_called": False,
        "playwright_runtime_used": False,
        "selenium_runtime_used": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "login_allowed": False,
        "payment_allowed": False,
        "account_creation_allowed": False,
        "allowed_actions": list(_ALLOWED_ACTIONS),
        "actions_path": actions_file.as_posix(),
        "actions_sha256": sha256_file(actions_file),
        "validated_action_count": len(actions),
        "screenshot_evidence_required": True,
        "normal_tests_must_not_launch_browser": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_browser_local_smoke_plan",
    }
    write_json_atomically(plan_path, plan)
    validation = _validate_plan_payload(plan_path)
    write_json_atomically(validation_path, validation)
    return BrowserLocalSmokePlanResult(
        output_dir=output_path,
        plan_path=plan_path,
        validation_path=validation_path,
        complete=bool(validation["complete"]),
        real_browser_called=False,
        external_network_used=False,
        required_human_approval=True,
    )


def validate_browser_local_smoke_plan(plan_path: Path) -> dict[str, object]:
    return _validate_plan_payload(Path(plan_path))


def _read_actions(actions_path: Path) -> list[dict[str, object]]:
    if not actions_path.exists() or not actions_path.is_file():
        raise ValueError("actions_path is missing")
    try:
        payload = json.loads(actions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("actions_path is malformed") from error
    actions = payload.get("actions") if isinstance(payload, dict) else payload
    if not isinstance(actions, list) or not actions:
        raise ValueError("browser smoke actions are malformed")
    validated = []
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("browser smoke action is malformed")
        action_name = action.get("action")
        if action_name not in _ALLOWED_ACTIONS:
            raise ValueError("browser smoke action is not allowed")
        if _contains_forbidden_intent(action):
            raise ValueError("browser smoke action contains forbidden intent")
        validated.append({"action": action_name})
    return validated


def _validate_target_url(target_url: str) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("browser smoke target_url scheme is not allowed")
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("browser smoke target_url must be loopback")
    return host


def _contains_forbidden_intent(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_forbidden_intent(str(key))
            or _contains_forbidden_intent(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_intent(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(term in lowered for term in _FORBIDDEN_INTENTS)
    return False


def _validate_plan_payload(plan_path: Path) -> dict[str, object]:
    failures: list[str] = []
    plan = _read_plan(plan_path, failures)
    if plan:
        if plan.get("plan_type") != _PLAN_TYPE:
            failures.append("plan_type_mismatch")
        if plan.get("loopback_only") is not True:
            failures.append("loopback_only_required")
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
                failures.append(field_name + "_must_be_false")
        if plan.get("required_human_approval") is not True:
            failures.append("required_human_approval")
    return {
        "validation_type": _VALIDATION_TYPE,
        "plan_path": plan_path.as_posix(),
        "plan_sha256": sha256_file(plan_path)
        if plan_path.exists() and plan_path.is_file()
        else None,
        "complete": not failures,
        "failures": sorted(set(failures)),
        "real_browser_called": False,
        "external_network_used": False,
        "credential_persistence_used": False,
        "required_human_approval": True,
    }


def _read_plan(path: Path, failures: list[str]) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        failures.append("plan_missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append("plan_malformed")
        return {}
    if not isinstance(payload, dict):
        failures.append("plan_malformed")
        return {}
    return payload


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("browser local smoke output already exists")
