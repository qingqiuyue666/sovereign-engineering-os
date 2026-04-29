"""Pure read-only aggregation over rendered governance CI payloads."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "governance_readiness_aggregate"
_VERSION = 1
_RECOVERY_SUBSYSTEM = "_".join(("recovery", "session", "host"))
_REQUIRED_SUBSYSTEMS = (
    "approval_review",
    "evidence_replay",
    _RECOVERY_SUBSYSTEM,
    "task_lifecycle_journal",
)
_CI_PAYLOAD_KEYS = frozenset(
    {
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
    }
)
_REASON_INVALID = "invalid_governance_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"
_FAILURE_ORDER = (
    "payload_not_mapping",
    "missing_subsystem",
    "unknown_subsystem",
    "subsystem_payload_invalid",
    "subsystem_not_ready",
    "subsystem_restore_supported",
    "subsystem_durable_writes",
    "subsystem_cli_commands",
    "subsystem_runtime_dependencies",
    "subsystem_not_json_safe",
)
_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": "mapping_of_rendered_read_only_ci_outputs",
    "required_subsystems": list(_REQUIRED_SUBSYSTEMS),
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [_REASON_INVALID, _REASON_NOT_READY, _REASON_READY],
    "failure_values": list(_FAILURE_ORDER),
}


@dataclass(frozen=True)
class GovernanceReadinessAggregate:
    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    aggregate: dict[str, object]


def governance_readiness_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def build_governance_readiness_aggregate(
    payloads: object,
) -> GovernanceReadinessAggregate:
    reason_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    ready_subsystems: list[str] = []
    not_ready_subsystems: list[str] = []
    invalid_subsystems: list[str] = []
    subsystem_surfaces: dict[str, str | None] = {}
    subsystem_versions: dict[str, int | None] = {}
    cli_command_count = 0
    runtime_dependency_count = 0

    if not isinstance(payloads, Mapping):
        _increment(failure_counts, "payload_not_mapping")
        failures = _ordered_failures(failure_counts)
        return _aggregate_result(
            ready=False,
            reason_code=_REASON_INVALID,
            failures=failures,
            ready_subsystems=ready_subsystems,
            not_ready_subsystems=not_ready_subsystems,
            invalid_subsystems=invalid_subsystems,
            reason_counts=reason_counts,
            failure_counts=failure_counts,
            subsystem_surfaces=subsystem_surfaces,
            subsystem_versions=subsystem_versions,
            cli_command_count=cli_command_count,
            runtime_dependency_count=runtime_dependency_count,
        )

    required = set(_REQUIRED_SUBSYSTEMS)
    present = set(payloads.keys())
    missing = sorted(required.difference(present))
    unknown = sorted(_subsystem_label(key) for key in present.difference(required))

    for subsystem in missing:
        invalid_subsystems.append(subsystem)
        subsystem_surfaces[subsystem] = None
        subsystem_versions[subsystem] = None
        _increment(failure_counts, "missing_subsystem")

    for subsystem in unknown:
        invalid_subsystems.append(subsystem)
        subsystem_surfaces[subsystem] = None
        subsystem_versions[subsystem] = None
        _increment(failure_counts, "unknown_subsystem")

    for subsystem in _REQUIRED_SUBSYSTEMS:
        if subsystem not in payloads:
            continue

        ci_payload = _validated_ci_payload(payloads[subsystem])
        if ci_payload is None:
            invalid_subsystems.append(subsystem)
            subsystem_surfaces[subsystem] = None
            subsystem_versions[subsystem] = None
            _increment(failure_counts, "subsystem_payload_invalid")
            continue

        subsystem_surfaces[subsystem] = ci_payload["surface"]  # type: ignore[assignment]
        subsystem_versions[subsystem] = ci_payload["version"]  # type: ignore[assignment]
        _increment(reason_counts, ci_payload["reason_code"])  # type: ignore[arg-type]

        if isinstance(ci_payload["cli_command_count"], int):
            cli_command_count += ci_payload["cli_command_count"]
        if isinstance(ci_payload["runtime_dependency_count"], int):
            runtime_dependency_count += ci_payload["runtime_dependency_count"]

        subsystem_failures = _subsystem_failures(ci_payload)
        if subsystem_failures:
            not_ready_subsystems.append(subsystem)
            for failure in subsystem_failures:
                _increment(failure_counts, failure)
        else:
            ready_subsystems.append(subsystem)

    failures = _ordered_failures(failure_counts)
    invalid_payload = any(
        failure in failure_counts
        for failure in (
            "payload_not_mapping",
            "missing_subsystem",
            "unknown_subsystem",
            "subsystem_payload_invalid",
        )
    )
    ready = not failures
    if ready:
        reason_code = _REASON_READY
    elif invalid_payload:
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    return _aggregate_result(
        ready=ready,
        reason_code=reason_code,
        failures=failures,
        ready_subsystems=ready_subsystems,
        not_ready_subsystems=not_ready_subsystems,
        invalid_subsystems=invalid_subsystems,
        reason_counts=reason_counts,
        failure_counts=failure_counts,
        subsystem_surfaces=subsystem_surfaces,
        subsystem_versions=subsystem_versions,
        cli_command_count=cli_command_count,
        runtime_dependency_count=runtime_dependency_count,
    )


def render_governance_readiness_aggregate(
    aggregate: GovernanceReadinessAggregate,
) -> dict[str, object]:
    return {
        "ready": aggregate.ready,
        "reason_code": aggregate.reason_code,
        "failures": list(aggregate.failures),
        "aggregate": deepcopy(aggregate.aggregate),
    }


def _aggregate_result(
    *,
    ready: bool,
    reason_code: str,
    failures: tuple[str, ...],
    ready_subsystems: list[str],
    not_ready_subsystems: list[str],
    invalid_subsystems: list[str],
    reason_counts: dict[str, int],
    failure_counts: dict[str, int],
    subsystem_surfaces: dict[str, str | None],
    subsystem_versions: dict[str, int | None],
    cli_command_count: int,
    runtime_dependency_count: int,
) -> GovernanceReadinessAggregate:
    aggregate_payload = {
        "surface": _SURFACE,
        "version": _VERSION,
        "subsystem_count": (
            len(ready_subsystems)
            + len(not_ready_subsystems)
            + len(invalid_subsystems)
        ),
        "ready_count": len(ready_subsystems),
        "not_ready_count": len(not_ready_subsystems),
        "invalid_count": len(invalid_subsystems),
        "ready_subsystems": sorted(ready_subsystems),
        "not_ready_subsystems": sorted(not_ready_subsystems),
        "invalid_subsystems": sorted(invalid_subsystems),
        "reason_counts": _sorted_counts(reason_counts),
        "failure_counts": _ordered_counts(failure_counts),
        "subsystem_surfaces": _sorted_mapping(subsystem_surfaces),
        "subsystem_versions": _sorted_mapping(subsystem_versions),
        "operator_safe": ready,
        "restore_supported": False,
        "durable_writes": False,
        "cli_command_count": cli_command_count,
        "runtime_dependency_count": runtime_dependency_count,
        "json_safe": True,
    }
    return GovernanceReadinessAggregate(
        ready=ready,
        reason_code=reason_code,
        failures=failures,
        aggregate=aggregate_payload,
    )


def _validated_ci_payload(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, Mapping):
        return None
    if set(payload.keys()) != _CI_PAYLOAD_KEYS:
        return None

    ci_ok = payload["ci_ok"]
    reason_code = payload["reason_code"]
    failures = payload["failures"]
    surface = payload["surface"]
    version = payload["version"]
    contract_ready = payload["contract_ready"]
    contract_reason_code = payload["contract_reason_code"]
    restore_supported = payload["restore_supported"]
    durable_writes = payload["durable_writes"]
    cli_command_count = payload["cli_command_count"]
    runtime_dependency_count = payload["runtime_dependency_count"]
    json_safe = payload["json_safe"]

    if type(ci_ok) is not bool:
        return None
    if not isinstance(reason_code, str):
        return None
    if not _is_string_list(failures):
        return None
    if surface is not None and not isinstance(surface, str):
        return None
    if version is not None and type(version) is not int:
        return None
    if type(contract_ready) is not bool:
        return None
    if not isinstance(contract_reason_code, str):
        return None
    if restore_supported is not None and type(restore_supported) is not bool:
        return None
    if durable_writes is not None and type(durable_writes) is not bool:
        return None
    if cli_command_count is not None and type(cli_command_count) is not int:
        return None
    if (
        runtime_dependency_count is not None
        and type(runtime_dependency_count) is not int
    ):
        return None
    if json_safe is not None and type(json_safe) is not bool:
        return None

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


def _subsystem_failures(payload: dict[str, object]) -> tuple[str, ...]:
    failures: list[str] = []

    if payload["ci_ok"] is False:
        failures.append("subsystem_not_ready")
    if payload["restore_supported"] is True:
        failures.append("subsystem_restore_supported")
    if payload["durable_writes"] is True:
        failures.append("subsystem_durable_writes")

    cli_command_count = payload["cli_command_count"]
    if isinstance(cli_command_count, int) and cli_command_count > 0:
        failures.append("subsystem_cli_commands")

    runtime_dependency_count = payload["runtime_dependency_count"]
    if isinstance(runtime_dependency_count, int) and runtime_dependency_count > 0:
        failures.append("subsystem_runtime_dependencies")

    if payload["json_safe"] is not True:
        failures.append("subsystem_not_json_safe")

    return tuple(failures)


def _ordered_failures(counts: dict[str, int]) -> tuple[str, ...]:
    return tuple(failure for failure in _FAILURE_ORDER if failure in counts)


def _ordered_counts(counts: dict[str, int]) -> dict[str, int]:
    return {failure: counts[failure] for failure in _FAILURE_ORDER if failure in counts}


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return {key: counts[key] for key in sorted(counts)}


def _sorted_mapping(mapping: dict[str, object]) -> dict[str, object]:
    return {key: mapping[key] for key in sorted(mapping)}


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _is_string_list(value: object) -> bool:
    return type(value) is list and all(isinstance(item, str) for item in value)


def _subsystem_label(value: object) -> str:
    if isinstance(value, str):
        return value
    return "non_string_subsystem_key"


__all__ = [
    "GovernanceReadinessAggregate",
    "build_governance_readiness_aggregate",
    "governance_readiness_manifest",
    "render_governance_readiness_aggregate",
]
