"""Fail-closed guard checks for the bounded local runtime slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "LocalRuntimeGuardResult",
    "validate_local_runtime_guards",
]

_POLICY_VERSION = "local-runtime-guards-v1"
_CODE_VERSION = "0.1.0"

_NETWORK_FLAGS = frozenset(
    {
        "network",
        "network_access",
        "network_enabled",
        "network_execution",
        "network_mode",
        "remote_execution",
    }
)
_LIVE_PROVIDER_FLAGS = frozenset(
    {
        "live_mode",
        "live_provider",
        "live_provider_call",
        "provider_live",
        "provider_live_call",
    }
)
_PROCESS_FIELDS = frozenset(
    {
        "command",
        "process_execution",
        "shell_command",
        "subprocess",
        "subprocess_execution",
    }
)
_ENV_FIELDS = frozenset(
    {
        ".env",
        "dotenv",
        "env",
        "env_file",
        "env_path",
        "env_value",
        "env_values",
        "environment",
        "environment_value",
        "environment_values",
        "getenv",
        "read_env",
    }
)
_SECRET_FIELDS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "authorization_header",
        "capability_token",
        "credential",
        "credentials",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "secret_value",
        "token",
    }
)
_RAW_INPUT_FIELDS = frozenset({"input_payload", "raw_input", "raw_inputs", "raw_payload"})
_RAW_PROMPT_FIELDS = frozenset({"prompt", "raw_prompt", "raw_user_prompt", "persist_raw_prompt"})
_RAW_PROVIDER_FIELDS = frozenset(
    {
        "full_response",
        "provider_response",
        "raw_provider_response",
        "raw_response",
        "response_text",
    }
)
_RAW_EXCEPTION_FIELDS = frozenset(
    {
        "exception",
        "exception_dump",
        "exception_text",
        "raw_exception",
        "raw_exception_dump",
        "raw_traceback",
        "traceback",
    }
)
_SQLITE_MUTATION_FIELDS = frozenset(
    {
        "database_mutation",
        "db_write",
        "sql_mutation",
        "sqlite_mutation",
        "sqlite_write",
    }
)
_AUTONOMY_FLAGS = frozenset(
    {
        "autonomous",
        "autonomous_execution",
        "production_autonomy",
        "production_mode",
    }
)
_STRING_MARKERS = (
    (".env", "env_read_rejected"),
    ("dotenv", "env_read_rejected"),
    ("os." + "environ", "env_value_read_rejected"),
    ("get" + "env(", "env_value_read_rejected"),
    ("traceback (most recent call last)", "raw_traceback_persistence_rejected"),
    ("api_key=", "secret_field_rejected"),
    ("secret=", "secret_field_rejected"),
    ("token=", "secret_field_rejected"),
    ("password=", "secret_field_rejected"),
    ("private_key", "secret_field_rejected"),
    ("authorization:", "secret_field_rejected"),
    ("bearer ", "secret_field_rejected"),
    ("insert into ", "sqlite_mutation_rejected"),
    ("update ", "sqlite_mutation_rejected"),
    ("delete from ", "sqlite_mutation_rejected"),
    ("sqlite3" + ".connect", "sqlite_mutation_rejected"),
)


@dataclass(frozen=True)
class LocalRuntimeGuardResult:
    """Deterministic result for local runtime admission checks."""

    accepted: bool
    failures: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "policy_version": self.policy_version,
            "code_version": self.code_version,
        }


def validate_local_runtime_guards(payload: Mapping[str, object] | object) -> LocalRuntimeGuardResult:
    """Validate local runtime input without reading environment or executing code."""

    if not isinstance(payload, Mapping):
        return _result(("runtime_input_must_be_mapping",))

    failures: list[str] = []
    if payload.get("dry_run") is not True:
        failures.append("non_dry_run_execution_rejected")

    _scan_mapping(payload, failures, path=())
    return _result(tuple(failures))


def _result(failures: tuple[str, ...]) -> LocalRuntimeGuardResult:
    normalized = tuple(sorted(set(failures)))
    return LocalRuntimeGuardResult(accepted=not normalized, failures=normalized)


def _scan_mapping(value: Mapping[object, object], failures: list[str], *, path: tuple[str, ...]) -> None:
    for raw_key, item in value.items():
        key = str(raw_key)
        normalized = key.lower()
        child_path = path + (key,)
        _scan_key(normalized, failures, child_path, item)
        _scan_value(item, failures, child_path)


def _scan_key(key: str, failures: list[str], path: tuple[str, ...], item: object) -> None:
    label = ".".join(path)
    if key in _NETWORK_FLAGS and item is not False:
        failures.append(f"network_execution_rejected:{label}")
    if key in _LIVE_PROVIDER_FLAGS and item is not False:
        failures.append(f"live_provider_call_rejected:{label}")
    if key in _PROCESS_FIELDS:
        failures.append(f"subprocess_execution_rejected:{label}")
    if key in _ENV_FIELDS:
        failures.append(f"env_value_read_rejected:{label}")
    if key in _SECRET_FIELDS:
        failures.append(f"secret_field_rejected:{label}")
    if key in _RAW_INPUT_FIELDS:
        failures.append(f"raw_input_persistence_rejected:{label}")
    if key in _RAW_PROMPT_FIELDS:
        failures.append(f"raw_prompt_persistence_rejected:{label}")
    if key in _RAW_PROVIDER_FIELDS:
        failures.append(f"raw_provider_response_persistence_rejected:{label}")
    if key in _RAW_EXCEPTION_FIELDS:
        failures.append(f"raw_exception_persistence_rejected:{label}")
    if key in _SQLITE_MUTATION_FIELDS:
        failures.append(f"sqlite_mutation_rejected:{label}")
    if key in _AUTONOMY_FLAGS and item is not False:
        failures.append(f"production_autonomy_rejected:{label}")


def _scan_value(value: object, failures: list[str], path: tuple[str, ...]) -> None:
    if isinstance(value, Mapping):
        _scan_mapping(value, failures, path=path)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_value(item, failures, path + (str(index),))
        return
    if isinstance(value, str):
        lowered = value.lower()
        label = ".".join(path)
        for marker, failure_code in _STRING_MARKERS:
            if marker in lowered:
                failures.append(f"{failure_code}:{label}")
