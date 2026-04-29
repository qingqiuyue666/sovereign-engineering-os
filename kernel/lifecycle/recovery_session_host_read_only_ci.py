"""Read-only CI consumer over rendered cross-phase digest contract checks."""

from copy import deepcopy
from typing import Mapping


__all__ = [
    "consume_recovery_session_host_read_only_ci",
    "recovery_session_host_read_only_ci_manifest",
]


_PAYLOAD_KEYS = ("contract", "failures", "ready", "reason_code")
_OUTPUT_KEYS = (
    "ci_ok",
    "cli_command_count",
    "contract_ready",
    "contract_reason_code",
    "durable_writes",
    "failures",
    "json_safe",
    "reason_code",
    "restore_supported",
    "runtime_dependency_count",
    "surface",
    "version",
)
_REASON_INVALID = "invalid_ci_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_FAILURE_VALUES = (
    "contract_cli_commands_invalid",
    "contract_durable_writes_invalid",
    "contract_json_safe_invalid",
    "contract_restore_supported_invalid",
    "contract_runtime_dependencies_invalid",
    "durable_writes",
    "has_cli_commands",
    "has_runtime_dependencies",
    "invalid_ci_payload",
    "not_json_safe",
    "restore_supported",
)
_MANIFEST = {
    "surface": "recovery_session_host_read_only_ci",
    "version": 1,
    "input_shape": "rendered_cross_phase_digest_contract_check",
    "payload_keys": list(_PAYLOAD_KEYS),
    "output_keys": list(_OUTPUT_KEYS),
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_VALUES),
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
}


def recovery_session_host_read_only_ci_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def consume_recovery_session_host_read_only_ci(
    payload: object,
) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        return _invalid_result()
    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        return _invalid_result()

    ready = payload["ready"]
    reason_code = payload["reason_code"]
    failures = payload["failures"]
    contract = payload["contract"]

    if not isinstance(ready, bool):
        return _invalid_result()
    if not isinstance(reason_code, str):
        return _invalid_result()
    if not _is_string_list(failures):
        return _invalid_result()
    if not isinstance(contract, Mapping):
        return _invalid_result()

    surface = contract.get("surface")
    version = contract.get("version")
    restore_supported = contract.get("restore_supported")
    durable_writes = contract.get("durable_writes")
    cli_commands = contract.get("cli_commands")
    runtime_dependencies = contract.get("runtime_dependencies")
    json_safe = contract.get("json_safe")

    surface_value = surface if isinstance(surface, str) else None
    version_value = version if _is_int(version) else None
    restore_value = (
        restore_supported if isinstance(restore_supported, bool) else None
    )
    durable_value = (
        durable_writes if isinstance(durable_writes, bool) else None
    )
    cli_count = _string_list_count(cli_commands)
    runtime_count = _string_list_count(runtime_dependencies)
    json_safe_value = json_safe if isinstance(json_safe, bool) else None

    hazard_failures: list[str] = []
    if restore_value is None:
        hazard_failures.append("contract_restore_supported_invalid")
    elif restore_value is True:
        hazard_failures.append("restore_supported")
    if durable_value is None:
        hazard_failures.append("contract_durable_writes_invalid")
    elif durable_value is True:
        hazard_failures.append("durable_writes")
    if cli_count is None:
        hazard_failures.append("contract_cli_commands_invalid")
    elif cli_count > 0:
        hazard_failures.append("has_cli_commands")
    if runtime_count is None:
        hazard_failures.append("contract_runtime_dependencies_invalid")
    elif runtime_count > 0:
        hazard_failures.append("has_runtime_dependencies")
    if json_safe_value is None:
        hazard_failures.append("contract_json_safe_invalid")
    elif json_safe_value is False:
        hazard_failures.append("not_json_safe")

    contract_ready_value = ready
    contract_reason_code_value = reason_code

    if (
        ready is True
        and reason_code == _REASON_READY
        and list(failures) == []
        and not hazard_failures
    ):
        return _result(
            ci_ok=True,
            reason_code=_REASON_READY,
            failures=[],
            surface=surface_value,
            version=version_value,
            contract_ready=contract_ready_value,
            contract_reason_code=contract_reason_code_value,
            restore_supported=restore_value,
            durable_writes=durable_value,
            cli_command_count=cli_count,
            runtime_dependency_count=runtime_count,
            json_safe=json_safe_value,
        )

    merged_failures = list(failures) + [
        item for item in hazard_failures if item not in failures
    ]
    return _result(
        ci_ok=False,
        reason_code=_REASON_NOT_READY,
        failures=merged_failures,
        surface=surface_value,
        version=version_value,
        contract_ready=contract_ready_value,
        contract_reason_code=contract_reason_code_value,
        restore_supported=restore_value,
        durable_writes=durable_value,
        cli_command_count=cli_count,
        runtime_dependency_count=runtime_count,
        json_safe=json_safe_value,
    )


def _invalid_result() -> dict[str, object]:
    return _result(
        ci_ok=False,
        reason_code=_REASON_INVALID,
        failures=[_REASON_INVALID],
        surface=None,
        version=None,
        contract_ready=False,
        contract_reason_code=_REASON_INVALID,
        restore_supported=None,
        durable_writes=None,
        cli_command_count=None,
        runtime_dependency_count=None,
        json_safe=None,
    )


def _result(
    *,
    ci_ok: bool,
    reason_code: str,
    failures: list[str],
    surface: str | None,
    version: int | None,
    contract_ready: bool,
    contract_reason_code: str,
    restore_supported: bool | None,
    durable_writes: bool | None,
    cli_command_count: int | None,
    runtime_dependency_count: int | None,
    json_safe: bool | None,
) -> dict[str, object]:
    return {
        "ci_ok": ci_ok,
        "reason_code": reason_code,
        "failures": list(failures),
        "surface": surface,
        "version": version,
        "contract_ready": contract_ready,
        "contract_reason_code": contract_reason_code,
        "restore_supported": restore_supported,
        "durable_writes": durable_writes,
        "cli_command_count": cli_command_count,
        "runtime_dependency_count": runtime_dependency_count,
        "json_safe": json_safe,
    }


def _is_int(value: object) -> bool:
    return type(value) is int


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _string_list_count(value: object) -> int | None:
    if not _is_string_list(value):
        return None
    return len(value)
