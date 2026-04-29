"""Pure cross-phase digest for rendered verdict check payloads."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


_CHECK_TOP_LEVEL_KEYS = {"ready", "reason_code", "failures", "manifest"}
_COMPARISON_TOP_LEVEL_KEYS = {"ok", "reason_code", "failures", "report"}
_FAILURE_ORDER = [
    "check_not_mapping",
    "comparison_not_mapping",
    "check_shape_mismatch",
    "comparison_shape_mismatch",
    "check_failures_invalid",
    "comparison_failures_invalid",
    "check_manifest_invalid",
    "comparison_report_invalid",
    "check_manifest_shape_mismatch",
    "comparison_report_shape_mismatch",
]


@dataclass(frozen=True)
class RecoverySessionHostVerdictCrossPhaseDigest:
    ok: bool
    reason_code: str
    failures: tuple[str, ...]
    digest: dict[str, object]


def build_recovery_session_host_verdict_cross_phase_digest(
    rendered_check: Mapping[str, object],
    rendered_comparison: Mapping[str, object],
) -> RecoverySessionHostVerdictCrossPhaseDigest:
    check_failures = _check_validation_failures(rendered_check)
    comparison_failures = _comparison_validation_failures(rendered_comparison)
    found_failures = set(check_failures + comparison_failures)
    failures = [
        failure for failure in _FAILURE_ORDER if failure in found_failures
    ]

    if failures:
        return RecoverySessionHostVerdictCrossPhaseDigest(
            ok=False,
            reason_code="invalid_cross_phase_digest",
            failures=tuple(failures),
            digest={
                "cross_phase_ok": False,
                "reason_code": "invalid_cross_phase_digest",
                "failures": list(failures),
                "operator_safe": False,
            },
        )

    manifest = rendered_check["manifest"]
    report = rendered_comparison["report"]
    contract_ready = rendered_check["ready"]
    contract_failure_count = len(rendered_check["failures"])
    comparison_ok = report["comparison_ok"]
    comparison_failure_count = len(report["failures"])
    comparison_changed = report["changed"]
    comparison_change_count = report["change_count"]
    before = report.get("before") if comparison_ok else None
    after = report.get("after") if comparison_ok else None
    cli_command_count = len(manifest["cli_commands"])
    runtime_dependency_count = len(manifest["runtime_dependencies"])
    restore_supported = manifest["restore_supported"]
    durable_writes = manifest["durable_writes"]
    json_safe = manifest["json_safe"]
    has_drift = comparison_changed is True or comparison_change_count > 0
    has_contract_failure = (
        contract_ready is False
        or contract_failure_count > 0
        or comparison_ok is False
        or comparison_failure_count > 0
    )
    has_runtime_dependencies = runtime_dependency_count > 0
    has_cli_commands = cli_command_count > 0
    has_restore_or_durable_surface = restore_supported or durable_writes
    operator_safe = (
        contract_ready is True
        and contract_failure_count == 0
        and comparison_ok is True
        and comparison_failure_count == 0
        and has_drift is False
        and has_runtime_dependencies is False
        and has_cli_commands is False
        and has_restore_or_durable_surface is False
        and json_safe is True
    )

    return RecoverySessionHostVerdictCrossPhaseDigest(
        ok=True,
        reason_code="ok",
        failures=(),
        digest={
            "cross_phase_ok": True,
            "reason_code": "ok",
            "failures": [],
            "operator_safe": operator_safe,
            "contract_ready": contract_ready,
            "contract_reason_code": rendered_check["reason_code"],
            "contract_failure_count": contract_failure_count,
            "manifest_surface": manifest.get("surface"),
            "manifest_version": manifest.get("version"),
            "restore_supported": restore_supported,
            "durable_writes": durable_writes,
            "cli_command_count": cli_command_count,
            "runtime_dependency_count": runtime_dependency_count,
            "json_safe": json_safe,
            "comparison_ok": comparison_ok,
            "comparison_reason_code": report["reason_code"],
            "comparison_failure_count": comparison_failure_count,
            "comparison_changed": comparison_changed,
            "comparison_change_count": comparison_change_count,
            "before_ready": _summary_field(before, "ready"),
            "after_ready": _summary_field(after, "ready"),
            "before_reason_code": _summary_field(before, "reason_code"),
            "after_reason_code": _summary_field(after, "reason_code"),
            "before_manifest_version": _summary_field(
                before, "manifest_version"
            ),
            "after_manifest_version": _summary_field(
                after, "manifest_version"
            ),
            "has_drift": has_drift,
            "has_contract_failure": has_contract_failure,
            "has_runtime_dependencies": has_runtime_dependencies,
            "has_cli_commands": has_cli_commands,
            "has_restore_or_durable_surface": has_restore_or_durable_surface,
        },
    )


def render_recovery_session_host_verdict_cross_phase_digest(
    digest: RecoverySessionHostVerdictCrossPhaseDigest,
) -> dict[str, object]:
    return {
        "ok": digest.ok,
        "reason_code": digest.reason_code,
        "failures": list(digest.failures),
        "digest": deepcopy(digest.digest),
    }


def _check_validation_failures(payload: object) -> list[str]:
    failures: list[str] = []
    if not isinstance(payload, Mapping):
        return ["check_not_mapping"]

    if set(payload) != _CHECK_TOP_LEVEL_KEYS:
        failures.append("check_shape_mismatch")
    elif not isinstance(payload.get("ready"), bool) or not isinstance(
        payload.get("reason_code"), str
    ):
        failures.append("check_shape_mismatch")

    if not _is_string_list(payload.get("failures")):
        failures.append("check_failures_invalid")

    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        failures.append("check_manifest_invalid")
    elif not _manifest_shape_is_valid(manifest):
        failures.append("check_manifest_shape_mismatch")

    return failures


def _comparison_validation_failures(payload: object) -> list[str]:
    failures: list[str] = []
    if not isinstance(payload, Mapping):
        return ["comparison_not_mapping"]

    if set(payload) != _COMPARISON_TOP_LEVEL_KEYS:
        failures.append("comparison_shape_mismatch")
    elif not isinstance(payload.get("ok"), bool) or not isinstance(
        payload.get("reason_code"), str
    ):
        failures.append("comparison_shape_mismatch")

    if not _is_string_list(payload.get("failures")):
        failures.append("comparison_failures_invalid")

    report = payload.get("report")
    if not isinstance(report, dict):
        failures.append("comparison_report_invalid")
    elif not _report_shape_is_valid(report):
        failures.append("comparison_report_shape_mismatch")

    return failures


def _manifest_shape_is_valid(manifest: dict[str, object]) -> bool:
    if not isinstance(manifest.get("surface"), str):
        return False
    if type(manifest.get("version")) is not int:
        return False
    if not isinstance(manifest.get("restore_supported"), bool):
        return False
    if not isinstance(manifest.get("durable_writes"), bool):
        return False
    if not _is_string_list(manifest.get("cli_commands")):
        return False
    if not _is_string_list(manifest.get("runtime_dependencies")):
        return False
    return isinstance(manifest.get("json_safe"), bool)


def _report_shape_is_valid(report: dict[str, object]) -> bool:
    if not isinstance(report.get("comparison_ok"), bool):
        return False
    if not isinstance(report.get("reason_code"), str):
        return False
    if not _is_string_list(report.get("failures")):
        return False
    if not _changed_is_valid(report.get("changed")):
        return False
    if type(report.get("change_count")) is not int:
        return False
    if not _is_dict_list(report.get("changes")):
        return False

    if report["comparison_ok"] is True:
        return _success_report_shape_is_valid(report)

    return (
        report.get("changed") is None
        and report["change_count"] == 0
        and report.get("changes") == []
    )


def _success_report_shape_is_valid(report: dict[str, object]) -> bool:
    before = report.get("before")
    after = report.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    return _summary_shape_is_valid(before) and _summary_shape_is_valid(after)


def _summary_shape_is_valid(summary: dict[str, object]) -> bool:
    if not isinstance(summary.get("ready"), bool):
        return False
    if not isinstance(summary.get("reason_code"), str):
        return False
    if type(summary.get("failure_count")) is not int:
        return False
    if not _optional_str_is_valid(summary.get("manifest_surface")):
        return False
    return _optional_int_is_valid(summary.get("manifest_version"))


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _is_dict_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) for item in value
    )


def _changed_is_valid(value: object) -> bool:
    return isinstance(value, bool) or value is None


def _optional_str_is_valid(value: object) -> bool:
    return isinstance(value, str) or value is None


def _optional_int_is_valid(value: object) -> bool:
    return type(value) is int or value is None


def _summary_field(summary: object, key: str) -> object:
    if isinstance(summary, dict):
        return summary.get(key)
    return None
