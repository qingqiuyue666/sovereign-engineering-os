"""Pure comparator for rendered verdict summary contract checks."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping


_TOP_LEVEL_KEYS = {"ready", "reason_code", "failures", "manifest"}
_MANIFEST_STRING_LIST_KEYS = {
    "top_level_keys",
    "digest_keys",
    "cli_commands",
    "runtime_dependencies",
}
_COMPARISON_FIELDS = [
    "ready",
    "reason_code",
    "failures",
    "manifest.surface",
    "manifest.version",
    "manifest.restore_supported",
    "manifest.durable_writes",
    "manifest.cli_commands",
    "manifest.runtime_dependencies",
    "manifest.top_level_keys",
    "manifest.digest_keys",
]
_VALIDATION_FAILURE_ORDER = [
    "before_not_mapping",
    "after_not_mapping",
    "before_shape_mismatch",
    "after_shape_mismatch",
    "before_failures_invalid",
    "after_failures_invalid",
    "before_manifest_invalid",
    "after_manifest_invalid",
    "before_manifest_shape_mismatch",
    "after_manifest_shape_mismatch",
]


@dataclass(frozen=True)
class RecoverySessionHostVerdictSummaryComparison:
    ok: bool
    reason_code: str
    failures: tuple[str, ...]
    report: dict[str, object]


def compare_recovery_session_host_verdict_summary_checks(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> RecoverySessionHostVerdictSummaryComparison:
    before_failures = _validation_failures("before", before)
    after_failures = _validation_failures("after", after)
    found_failures = set(before_failures + after_failures)
    failures = [
        failure
        for failure in _VALIDATION_FAILURE_ORDER
        if failure in found_failures
    ]

    if failures:
        return RecoverySessionHostVerdictSummaryComparison(
            ok=False,
            reason_code="invalid_comparison",
            failures=tuple(failures),
            report={
                "comparison_ok": False,
                "reason_code": "invalid_comparison",
                "failures": list(failures),
                "changed": None,
                "change_count": 0,
                "changes": [],
            },
        )

    changes = _changes(before, after)
    return RecoverySessionHostVerdictSummaryComparison(
        ok=True,
        reason_code="ok",
        failures=(),
        report={
            "comparison_ok": True,
            "reason_code": "ok",
            "failures": [],
            "changed": len(changes) > 0,
            "change_count": len(changes),
            "changes": changes,
            "before": _summary(before),
            "after": _summary(after),
        },
    )


def render_recovery_session_host_verdict_summary_comparison(
    comparison: RecoverySessionHostVerdictSummaryComparison,
) -> dict[str, object]:
    return {
        "ok": comparison.ok,
        "reason_code": comparison.reason_code,
        "failures": list(comparison.failures),
        "report": deepcopy(comparison.report),
    }


def _validation_failures(prefix: str, payload: object) -> list[str]:
    failures: list[str] = []
    if not isinstance(payload, Mapping):
        return [f"{prefix}_not_mapping"]

    if set(payload) != _TOP_LEVEL_KEYS:
        failures.append(f"{prefix}_shape_mismatch")
    elif not isinstance(payload.get("ready"), bool) or not isinstance(
        payload.get("reason_code"), str
    ):
        failures.append(f"{prefix}_shape_mismatch")

    if not _is_string_list(payload.get("failures")):
        failures.append(f"{prefix}_failures_invalid")

    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        failures.append(f"{prefix}_manifest_invalid")
    elif not _manifest_shape_is_valid(manifest):
        failures.append(f"{prefix}_manifest_shape_mismatch")

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

    return all(
        _is_string_list(manifest.get(key))
        for key in _MANIFEST_STRING_LIST_KEYS
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _changes(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for field in _COMPARISON_FIELDS:
        before_value = _field_value(before, field)
        after_value = _field_value(after, field)
        if before_value != after_value:
            changes.append(
                {
                    "field": field,
                    "before": before_value,
                    "after": after_value,
                }
            )
    return changes


def _field_value(payload: Mapping[str, object], field: str) -> object:
    if field.startswith("manifest."):
        manifest = payload["manifest"]
        return deepcopy(manifest[field.split(".", 1)[1]])
    return deepcopy(payload[field])


def _summary(payload: Mapping[str, object]) -> dict[str, object]:
    manifest = payload["manifest"]
    return {
        "ready": payload["ready"],
        "reason_code": payload["reason_code"],
        "failure_count": len(payload["failures"]),
        "manifest_surface": _manifest_surface(manifest),
        "manifest_version": _manifest_version(manifest),
    }


def _manifest_surface(manifest: object) -> str | None:
    if isinstance(manifest, dict) and isinstance(manifest.get("surface"), str):
        return manifest["surface"]
    return None


def _manifest_version(manifest: object) -> int | None:
    if isinstance(manifest, dict) and type(manifest.get("version")) is int:
        return manifest["version"]
    return None
