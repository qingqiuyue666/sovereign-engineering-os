"""Flat read-only CI consumer for rendered evidence/replay contract checks.

This module accepts only an already-rendered P2-02 contract-check payload
and projects it to a bounded JSON-safe CI verdict for downstream surfaces.
It does not open data stores, invoke repositories, call CLI code, or run
recovery behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy


_SURFACE = "evidence_replay_readiness_ci"
_VERSION = 1
_INPUT_SHAPE = "rendered_evidence_replay_readiness_contract_check"

_PAYLOAD_KEYS = ("contract", "failures", "ready", "reason_code")
_OUTPUT_KEYS = (
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "contract_ready",
    "contract_reason_code",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
)
_REASON_CODE_INVALID_CI_PAYLOAD = "invalid_ci_payload"
_REASON_CODE_NOT_READY = "not_ready"
_REASON_CODE_READY = "ready"
_FAILURE_VALUES = (
    "invalid_ci_payload",
    "contract_restore_supported_invalid",
    "contract_durable_writes_invalid",
    "contract_cli_commands_invalid",
    "contract_runtime_dependencies_invalid",
    "contract_json_safe_invalid",
    "restore_supported",
    "durable_writes",
    "has_cli_commands",
    "has_runtime_dependencies",
    "not_json_safe",
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": _INPUT_SHAPE,
    "payload_keys": list(_PAYLOAD_KEYS),
    "output_keys": list(_OUTPUT_KEYS),
    "reason_codes": [
        _REASON_CODE_INVALID_CI_PAYLOAD,
        _REASON_CODE_NOT_READY,
        _REASON_CODE_READY,
    ],
    "failure_values": list(_FAILURE_VALUES),
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
}


def evidence_replay_readiness_ci_manifest() -> dict[str, object]:
    """Return a defensive JSON-safe manifest for the CI consumer."""

    return deepcopy(_MANIFEST)


def consume_evidence_replay_readiness_ci(
    payload: object,
) -> dict[str, object]:
    """Flatten a rendered contract check into a bounded CI result."""

    if not isinstance(payload, Mapping):
        return _invalid_result()
    if set(payload.keys()) != set(_PAYLOAD_KEYS):
        return _invalid_result()

    ready = payload["ready"]
    reason_code = payload["reason_code"]
    failures = payload["failures"]
    contract = payload["contract"]

    if type(ready) is not bool:
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
        restore_supported if type(restore_supported) is bool else None
    )
    durable_value = durable_writes if type(durable_writes) is bool else None
    cli_count = _string_list_count(cli_commands)
    runtime_count = _string_list_count(runtime_dependencies)
    json_safe_value = json_safe if type(json_safe) is bool else None

    hazard_failures = _hazard_failures(
        restore_value=restore_value,
        durable_value=durable_value,
        cli_count=cli_count,
        runtime_count=runtime_count,
        json_safe_value=json_safe_value,
    )

    if (
        ready is True
        and reason_code == _REASON_CODE_READY
        and failures == []
        and restore_value is False
        and durable_value is False
        and cli_count == 0
        and runtime_count == 0
        and json_safe_value is True
    ):
        return _result(
            ci_ok=True,
            reason_code=_REASON_CODE_READY,
            failures=[],
            surface=surface_value,
            version=version_value,
            contract_ready=ready,
            contract_reason_code=reason_code,
            restore_supported=restore_value,
            durable_writes=durable_value,
            cli_command_count=cli_count,
            runtime_dependency_count=runtime_count,
            json_safe=json_safe_value,
        )

    merged_failures = list(failures) + [
        failure for failure in hazard_failures if failure not in failures
    ]
    return _result(
        ci_ok=False,
        reason_code=_REASON_CODE_NOT_READY,
        failures=merged_failures,
        surface=surface_value,
        version=version_value,
        contract_ready=ready,
        contract_reason_code=reason_code,
        restore_supported=restore_value,
        durable_writes=durable_value,
        cli_command_count=cli_count,
        runtime_dependency_count=runtime_count,
        json_safe=json_safe_value,
    )


def _hazard_failures(
    *,
    restore_value: bool | None,
    durable_value: bool | None,
    cli_count: int | None,
    runtime_count: int | None,
    json_safe_value: bool | None,
) -> list[str]:
    failures: list[str] = []

    if restore_value is None:
        failures.append("contract_restore_supported_invalid")
    elif restore_value is True:
        failures.append("restore_supported")

    if durable_value is None:
        failures.append("contract_durable_writes_invalid")
    elif durable_value is True:
        failures.append("durable_writes")

    if cli_count is None:
        failures.append("contract_cli_commands_invalid")
    elif cli_count > 0:
        failures.append("has_cli_commands")

    if runtime_count is None:
        failures.append("contract_runtime_dependencies_invalid")
    elif runtime_count > 0:
        failures.append("has_runtime_dependencies")

    if json_safe_value is None:
        failures.append("contract_json_safe_invalid")
    elif json_safe_value is False:
        failures.append("not_json_safe")

    return failures


def _invalid_result() -> dict[str, object]:
    return _result(
        ci_ok=False,
        reason_code=_REASON_CODE_INVALID_CI_PAYLOAD,
        failures=[_REASON_CODE_INVALID_CI_PAYLOAD],
        surface=None,
        version=None,
        contract_ready=False,
        contract_reason_code=_REASON_CODE_INVALID_CI_PAYLOAD,
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
    return type(value) is list and all(isinstance(item, str) for item in value)


def _string_list_count(value: object) -> int | None:
    if not _is_string_list(value):
        return None
    return len(value)


__all__ = [
    "consume_evidence_replay_readiness_ci",
    "evidence_replay_readiness_ci_manifest",
]
