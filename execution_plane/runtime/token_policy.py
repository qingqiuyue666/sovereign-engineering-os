"""Runtime-token policy normalization and fail-closed checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from execution_plane.adapters.base import SUPPORTED_ADAPTER_ACTIONS, SUPPORTED_ADAPTERS

PATCH_REPAIR_MODES = frozenset({"report_only", "generate_patch_then_test"})
KNOWN_PATCH_TOOLS = frozenset({"cline", "aider"})


class RuntimePolicyError(ValueError):
    """Raised when runtime policy fields are malformed or unsafe."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("runtime policy validation failed: " + ", ".join(self.errors))


def default_runtime_policy() -> dict[str, Any]:
    return {
        "auto_provision": {
            "enabled": False,
            "allowed_adapters": [],
            "max_wait_seconds": 0,
            "heartbeat_interval_seconds": 1,
        },
        "concurrency": {
            "max_global_jobs": 1,
            "max_per_adapter_jobs": {adapter: 1 for adapter in SUPPORTED_ADAPTERS},
        },
        "retry": {
            "enabled": False,
            "max_attempts": 1,
            "backoff_seconds": 0,
        },
        "patch_repair": {
            "enabled": False,
            "mode": "report_only",
            "allowed_tools": [],
            "auto_apply": False,
        },
    }


def normalize_runtime_policy(token: Mapping[str, Any]) -> dict[str, Any]:
    policy = default_runtime_policy()
    for section in ("auto_provision", "concurrency", "retry", "patch_repair"):
        incoming = token.get(section)
        if isinstance(incoming, Mapping):
            _deep_merge(policy[section], incoming)
    errors = validate_runtime_policy_errors(policy)
    if errors:
        raise RuntimePolicyError(errors)
    return policy


def validate_runtime_policy_errors(policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_auto_provision(policy.get("auto_provision"), errors)
    _validate_concurrency(policy.get("concurrency"), errors)
    _validate_retry(policy.get("retry"), errors)
    _validate_patch_repair(policy.get("patch_repair"), errors)
    return errors


def assert_action_allowed(token: Mapping[str, Any], *, adapter: str, action: str) -> None:
    allowed_adapter = str(token.get("allowed_adapter", ""))
    allowed_action = str(token.get("allowed_action", ""))
    errors: list[str] = []
    if adapter != allowed_adapter:
        errors.append("adapter_not_allowed_by_token")
    if action != allowed_action:
        errors.append("action_not_allowed_by_token")
    if adapter not in SUPPORTED_ADAPTER_ACTIONS:
        errors.append("unsupported_adapter")
    elif action not in SUPPORTED_ADAPTER_ACTIONS[adapter]:
        errors.append("unsupported_action_for_adapter")
    if errors:
        raise RuntimePolicyError(errors)


def auto_provision_allowed(token: Mapping[str, Any], adapter: str) -> bool:
    policy = normalize_runtime_policy(token)
    section = policy["auto_provision"]
    return bool(section["enabled"]) and adapter in set(section["allowed_adapters"])


def max_global_jobs(token: Mapping[str, Any]) -> int:
    return int(normalize_runtime_policy(token)["concurrency"]["max_global_jobs"])


def max_adapter_jobs(token: Mapping[str, Any], adapter: str) -> int:
    per_adapter = normalize_runtime_policy(token)["concurrency"]["max_per_adapter_jobs"]
    return int(per_adapter.get(adapter, 1))


def with_runtime_policy(token: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(token)
    normalized = normalize_runtime_policy(policy)
    payload.update(deepcopy(normalized))
    return payload


def _deep_merge(target: dict[str, Any], incoming: Mapping[str, Any]) -> None:
    for key, value in incoming.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def _validate_auto_provision(section: object, errors: list[str]) -> None:
    if not isinstance(section, Mapping):
        errors.append("auto_provision_must_be_mapping")
        return
    _require_bool(section, "enabled", errors, "auto_provision")
    _require_nonnegative_int(section, "max_wait_seconds", errors, "auto_provision")
    _require_positive_int(section, "heartbeat_interval_seconds", errors, "auto_provision")
    adapters = section.get("allowed_adapters")
    if not isinstance(adapters, list):
        errors.append("auto_provision_allowed_adapters_must_be_list")
    else:
        for adapter in adapters:
            if adapter not in SUPPORTED_ADAPTERS:
                errors.append("auto_provision_unknown_adapter")


def _validate_concurrency(section: object, errors: list[str]) -> None:
    if not isinstance(section, Mapping):
        errors.append("concurrency_must_be_mapping")
        return
    _require_positive_int(section, "max_global_jobs", errors, "concurrency")
    per_adapter = section.get("max_per_adapter_jobs")
    if not isinstance(per_adapter, Mapping):
        errors.append("concurrency_max_per_adapter_jobs_must_be_mapping")
    else:
        for adapter, value in per_adapter.items():
            if adapter not in SUPPORTED_ADAPTERS:
                errors.append("concurrency_unknown_adapter")
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append("concurrency_adapter_budget_must_be_positive_int")


def _validate_retry(section: object, errors: list[str]) -> None:
    if not isinstance(section, Mapping):
        errors.append("retry_must_be_mapping")
        return
    _require_bool(section, "enabled", errors, "retry")
    _require_positive_int(section, "max_attempts", errors, "retry")
    _require_nonnegative_int(section, "backoff_seconds", errors, "retry")


def _validate_patch_repair(section: object, errors: list[str]) -> None:
    if not isinstance(section, Mapping):
        errors.append("patch_repair_must_be_mapping")
        return
    _require_bool(section, "enabled", errors, "patch_repair")
    if section.get("mode") not in PATCH_REPAIR_MODES:
        errors.append("patch_repair_mode_unsupported")
    tools = section.get("allowed_tools")
    if not isinstance(tools, list):
        errors.append("patch_repair_allowed_tools_must_be_list")
    else:
        for tool in tools:
            if tool not in KNOWN_PATCH_TOOLS:
                errors.append("patch_repair_unknown_tool")
    if section.get("auto_apply") is not False:
        errors.append("patch_repair_auto_apply_must_be_false")


def _require_bool(section: Mapping[str, Any], field: str, errors: list[str], prefix: str) -> None:
    if not isinstance(section.get(field), bool):
        errors.append(f"{prefix}_{field}_must_be_bool")


def _require_positive_int(section: Mapping[str, Any], field: str, errors: list[str], prefix: str) -> None:
    value = section.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{prefix}_{field}_must_be_positive_int")


def _require_nonnegative_int(section: Mapping[str, Any], field: str, errors: list[str], prefix: str) -> None:
    value = section.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"{prefix}_{field}_must_be_nonnegative_int")
