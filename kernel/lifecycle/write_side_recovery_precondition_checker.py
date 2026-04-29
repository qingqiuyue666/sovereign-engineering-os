"""Pure read-only payload evaluator for write-side recovery preconditions.

This module never mutates state, never opens external resources, and never
calls upstream renderers. It accepts already-rendered precondition payloads
and reports whether they satisfy the documented preconditions.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass


_SURFACE = "write_side_recovery_precondition_check"
_VERSION = 1
_BASELINE_TAG = "read-only-governance-layer-v1"
_BASELINE_COMMIT = "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"

_TOP_LEVEL_KEYS = (
    "source_truth",
    "governance",
    "target_task",
    "evidence_replay",
    "approval_review",
    "human_approval",
    "dry_run",
    "idempotency",
    "evidence_snapshot",
    "transaction",
    "schema_runtime",
    "operator_confirmation",
)

_REASON_INVALID = "invalid_precondition_payload"
_REASON_NOT_READY = "not_ready"
_REASON_READY = "ready"

_FAILURE_ORDER = (
    "payload_not_mapping",
    "payload_shape_mismatch",
    "source_truth_invalid",
    "baseline_tag_unresolved",
    "baseline_commit_mismatch",
    "working_tree_dirty",
    "governance_invalid",
    "governance_not_ready",
    "target_task_invalid",
    "target_task_not_ready",
    "evidence_replay_invalid",
    "evidence_replay_not_ready",
    "approval_review_invalid",
    "approval_review_not_ready",
    "human_approval_invalid",
    "human_approval_missing",
    "dry_run_invalid",
    "dry_run_missing",
    "dry_run_failed",
    "dry_run_target_mismatch",
    "idempotency_invalid",
    "idempotency_missing",
    "idempotency_replay_risk",
    "evidence_snapshot_invalid",
    "evidence_snapshot_missing",
    "transaction_invalid",
    "transaction_missing",
    "rollback_missing",
    "schema_runtime_invalid",
    "schema_migration_required",
    "db_repair_required",
    "runtime_boundary_violation",
    "operator_confirmation_invalid",
    "cli_confirmation_missing",
)

_INVALID_FAILURES = frozenset(
    {
        "payload_not_mapping",
        "payload_shape_mismatch",
        "source_truth_invalid",
        "governance_invalid",
        "target_task_invalid",
        "evidence_replay_invalid",
        "approval_review_invalid",
        "human_approval_invalid",
        "dry_run_invalid",
        "idempotency_invalid",
        "evidence_snapshot_invalid",
        "transaction_invalid",
        "schema_runtime_invalid",
        "operator_confirmation_invalid",
    }
)

_ALLOWED_REPLAY_STATUS = frozenset({"new", "same_attempt_safe"})

_MANIFEST: dict[str, object] = {
    "surface": _SURFACE,
    "version": _VERSION,
    "input_shape": "mapping_of_already_rendered_precondition_payloads",
    "baseline_tag": _BASELINE_TAG,
    "baseline_commit": _BASELINE_COMMIT,
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "durable_writes": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        _REASON_INVALID,
        _REASON_NOT_READY,
        _REASON_READY,
    ],
    "failure_values": list(_FAILURE_ORDER),
}


@dataclass(frozen=True)
class WriteSideRecoveryPreconditionCheck:
    ready: bool
    reason_code: str
    failures: tuple[str, ...]
    preconditions: dict[str, object]


def write_side_recovery_precondition_manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def check_write_side_recovery_preconditions(
    payload: object,
) -> WriteSideRecoveryPreconditionCheck:
    failures: list[str] = []
    section_ready: dict[str, bool] = {
        "source_truth_ready": False,
        "governance_ready": False,
        "target_task_ready": False,
        "evidence_replay_ready": False,
        "approval_review_ready": False,
        "human_approval_ready": False,
        "dry_run_ready": False,
        "idempotency_ready": False,
        "evidence_snapshot_ready": False,
        "transaction_ready": False,
        "rollback_ready": False,
        "schema_migration_safe": False,
        "runtime_boundary_safe": False,
        "operator_confirmation_ready": False,
        "operator_safe": False,
    }

    if not isinstance(payload, Mapping):
        failures.append("payload_not_mapping")
        return _finalize(failures, section_ready)

    expected = set(_TOP_LEVEL_KEYS)
    present = set(payload.keys())
    if expected != present:
        failures.append("payload_shape_mismatch")
        return _finalize(failures, section_ready)

    _check_source_truth(payload["source_truth"], failures, section_ready)
    _check_readiness_section(
        payload["governance"],
        failures,
        section_ready,
        ready_key="governance_ready",
        invalid_failure="governance_invalid",
        not_ready_failure="governance_not_ready",
    )
    _check_readiness_section(
        payload["target_task"],
        failures,
        section_ready,
        ready_key="target_task_ready",
        invalid_failure="target_task_invalid",
        not_ready_failure="target_task_not_ready",
    )
    _check_readiness_section(
        payload["evidence_replay"],
        failures,
        section_ready,
        ready_key="evidence_replay_ready",
        invalid_failure="evidence_replay_invalid",
        not_ready_failure="evidence_replay_not_ready",
    )
    _check_readiness_section(
        payload["approval_review"],
        failures,
        section_ready,
        ready_key="approval_review_ready",
        invalid_failure="approval_review_invalid",
        not_ready_failure="approval_review_not_ready",
    )
    _check_human_approval(payload["human_approval"], failures, section_ready)
    _check_dry_run(payload["dry_run"], failures, section_ready)
    _check_idempotency(payload["idempotency"], failures, section_ready)
    _check_evidence_snapshot(payload["evidence_snapshot"], failures, section_ready)
    _check_transaction(payload["transaction"], failures, section_ready)
    _check_schema_runtime(payload["schema_runtime"], failures, section_ready)
    _check_operator_confirmation(
        payload["operator_confirmation"], failures, section_ready
    )

    return _finalize(failures, section_ready)


def render_write_side_recovery_precondition_check(
    check: WriteSideRecoveryPreconditionCheck,
) -> dict[str, object]:
    return {
        "ready": check.ready,
        "reason_code": check.reason_code,
        "failures": list(check.failures),
        "preconditions": deepcopy(check.preconditions),
    }


def _finalize(
    failures: list[str],
    section_ready: dict[str, bool],
) -> WriteSideRecoveryPreconditionCheck:
    ordered = _ordered_failures(failures)
    ready = not ordered
    if ready:
        reason_code = _REASON_READY
    elif any(failure in _INVALID_FAILURES for failure in ordered):
        reason_code = _REASON_INVALID
    else:
        reason_code = _REASON_NOT_READY

    preconditions: dict[str, object] = {
        "surface": _SURFACE,
        "version": _VERSION,
        "source_truth_ready": section_ready["source_truth_ready"],
        "governance_ready": section_ready["governance_ready"],
        "target_task_ready": section_ready["target_task_ready"],
        "evidence_replay_ready": section_ready["evidence_replay_ready"],
        "approval_review_ready": section_ready["approval_review_ready"],
        "human_approval_ready": section_ready["human_approval_ready"],
        "dry_run_ready": section_ready["dry_run_ready"],
        "idempotency_ready": section_ready["idempotency_ready"],
        "evidence_snapshot_ready": section_ready["evidence_snapshot_ready"],
        "transaction_ready": section_ready["transaction_ready"],
        "rollback_ready": section_ready["rollback_ready"],
        "schema_migration_safe": section_ready["schema_migration_safe"],
        "runtime_boundary_safe": section_ready["runtime_boundary_safe"],
        "operator_confirmation_ready": section_ready["operator_confirmation_ready"],
        "operator_safe": section_ready["operator_safe"],
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "json_safe": True,
    }
    return WriteSideRecoveryPreconditionCheck(
        ready=ready,
        reason_code=reason_code,
        failures=ordered,
        preconditions=preconditions,
    )


def _ordered_failures(failures: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for failure in _FAILURE_ORDER:
        if failure in failures and failure not in seen:
            ordered.append(failure)
            seen.add(failure)
    return tuple(ordered)


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and len(value) > 0


def _is_bool(value: object) -> bool:
    return type(value) is bool


def _check_source_truth(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "baseline_tag",
        "baseline_commit",
        "current_head",
        "working_tree_clean",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("source_truth_invalid")
        return

    baseline_tag = section["baseline_tag"]
    baseline_commit = section["baseline_commit"]
    current_head = section["current_head"]
    working_tree_clean = section["working_tree_clean"]

    if (
        not isinstance(baseline_tag, str)
        or not isinstance(baseline_commit, str)
        or not isinstance(current_head, str)
        or not _is_bool(working_tree_clean)
    ):
        failures.append("source_truth_invalid")
        return

    if not _is_non_empty_str(current_head):
        failures.append("source_truth_invalid")
        return

    section_failed = False
    if baseline_tag != _BASELINE_TAG:
        failures.append("baseline_tag_unresolved")
        section_failed = True
    if baseline_commit != _BASELINE_COMMIT:
        failures.append("baseline_commit_mismatch")
        section_failed = True
    if working_tree_clean is not True:
        failures.append("working_tree_dirty")
        section_failed = True

    if not section_failed:
        section_ready["source_truth_ready"] = True


def _check_readiness_section(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
    *,
    ready_key: str,
    invalid_failure: str,
    not_ready_failure: str,
) -> None:
    if not isinstance(section, Mapping):
        failures.append(invalid_failure)
        return

    has_ready_style = "ready" in section
    has_ci_style = "ci_ok" in section
    if has_ready_style == has_ci_style:
        failures.append(invalid_failure)
        return

    if "reason_code" not in section or "failures" not in section:
        failures.append(invalid_failure)
        return

    reason_code = section["reason_code"]
    section_failures = section["failures"]
    if not isinstance(reason_code, str):
        failures.append(invalid_failure)
        return
    if type(section_failures) is not list:
        failures.append(invalid_failure)
        return
    if not all(isinstance(item, str) for item in section_failures):
        failures.append(invalid_failure)
        return

    if has_ready_style:
        ready_flag = section["ready"]
    else:
        ready_flag = section["ci_ok"]
    if not _is_bool(ready_flag):
        failures.append(invalid_failure)
        return

    is_ready = (
        ready_flag is True
        and reason_code == "ready"
        and len(section_failures) == 0
    )

    if "restore_supported" in section:
        value = section["restore_supported"]
        if value is not None and not _is_bool(value):
            failures.append(invalid_failure)
            return
        if value is True:
            is_ready = False
    if "durable_writes" in section:
        value = section["durable_writes"]
        if value is not None and not _is_bool(value):
            failures.append(invalid_failure)
            return
        if value is True:
            is_ready = False
    if "cli_command_count" in section:
        value = section["cli_command_count"]
        if value is not None and type(value) is not int:
            failures.append(invalid_failure)
            return
        if isinstance(value, int) and value > 0:
            is_ready = False
    if "runtime_dependency_count" in section:
        value = section["runtime_dependency_count"]
        if value is not None and type(value) is not int:
            failures.append(invalid_failure)
            return
        if isinstance(value, int) and value > 0:
            is_ready = False
    if "json_safe" in section:
        value = section["json_safe"]
        if value is not True:
            is_ready = False

    if is_ready:
        section_ready[ready_key] = True
    else:
        failures.append(not_ready_failure)


def _check_human_approval(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "approval_present",
        "actor_identity",
        "scope",
        "reason",
        "created_at",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("human_approval_invalid")
        return

    approval_present = section["approval_present"]
    actor_identity = section["actor_identity"]
    scope = section["scope"]
    reason = section["reason"]
    created_at = section["created_at"]

    if (
        not _is_bool(approval_present)
        or not isinstance(actor_identity, str)
        or not isinstance(scope, str)
        or not isinstance(reason, str)
        or not isinstance(created_at, str)
    ):
        failures.append("human_approval_invalid")
        return

    if (
        not _is_non_empty_str(actor_identity)
        or not _is_non_empty_str(scope)
        or not _is_non_empty_str(reason)
        or not _is_non_empty_str(created_at)
    ):
        failures.append("human_approval_invalid")
        return

    if approval_present is not True:
        failures.append("human_approval_missing")
        return

    section_ready["human_approval_ready"] = True


def _check_dry_run(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "dry_run_present",
        "dry_run_ok",
        "target_task_id",
        "projected_action",
        "projected_evidence_ref",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("dry_run_invalid")
        return

    dry_run_present = section["dry_run_present"]
    dry_run_ok = section["dry_run_ok"]
    target_task_id = section["target_task_id"]
    projected_action = section["projected_action"]
    projected_evidence_ref = section["projected_evidence_ref"]

    if (
        not _is_bool(dry_run_present)
        or not _is_bool(dry_run_ok)
        or not isinstance(target_task_id, str)
        or not isinstance(projected_action, str)
        or not isinstance(projected_evidence_ref, str)
    ):
        failures.append("dry_run_invalid")
        return

    section_failed = False
    if dry_run_present is not True:
        failures.append("dry_run_missing")
        section_failed = True
    if dry_run_ok is not True:
        failures.append("dry_run_failed")
        section_failed = True
    if (
        not _is_non_empty_str(target_task_id)
        or not _is_non_empty_str(projected_action)
        or not _is_non_empty_str(projected_evidence_ref)
    ):
        failures.append("dry_run_target_mismatch")
        section_failed = True

    if not section_failed:
        section_ready["dry_run_ready"] = True


def _check_idempotency(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "idempotency_key",
        "target_task_id",
        "operation_kind",
        "replay_status",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("idempotency_invalid")
        return

    idempotency_key = section["idempotency_key"]
    target_task_id = section["target_task_id"]
    operation_kind = section["operation_kind"]
    replay_status = section["replay_status"]

    if (
        not isinstance(idempotency_key, str)
        or not isinstance(target_task_id, str)
        or not isinstance(operation_kind, str)
        or not isinstance(replay_status, str)
    ):
        failures.append("idempotency_invalid")
        return

    section_failed = False
    if (
        not _is_non_empty_str(idempotency_key)
        or not _is_non_empty_str(target_task_id)
        or not _is_non_empty_str(operation_kind)
    ):
        failures.append("idempotency_missing")
        section_failed = True
    if replay_status not in _ALLOWED_REPLAY_STATUS:
        failures.append("idempotency_replay_risk")
        section_failed = True

    if not section_failed:
        section_ready["idempotency_ready"] = True


def _check_evidence_snapshot(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "before_snapshot_ref",
        "projected_after_snapshot_ref",
        "immutable",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("evidence_snapshot_invalid")
        return

    before_ref = section["before_snapshot_ref"]
    after_ref = section["projected_after_snapshot_ref"]
    immutable = section["immutable"]

    if (
        not isinstance(before_ref, str)
        or not isinstance(after_ref, str)
        or not _is_bool(immutable)
    ):
        failures.append("evidence_snapshot_invalid")
        return

    if (
        not _is_non_empty_str(before_ref)
        or not _is_non_empty_str(after_ref)
        or immutable is not True
    ):
        failures.append("evidence_snapshot_missing")
        return

    section_ready["evidence_snapshot_ready"] = True


def _check_transaction(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "transaction_declared",
        "rollback_declared",
        "expected_rejection_policy",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("transaction_invalid")
        return

    transaction_declared = section["transaction_declared"]
    rollback_declared = section["rollback_declared"]
    expected_rejection_policy = section["expected_rejection_policy"]

    if (
        not _is_bool(transaction_declared)
        or not _is_bool(rollback_declared)
        or not isinstance(expected_rejection_policy, str)
    ):
        failures.append("transaction_invalid")
        return

    if transaction_declared is not True:
        failures.append("transaction_missing")
    else:
        section_ready["transaction_ready"] = True

    if rollback_declared is not True or not _is_non_empty_str(
        expected_rejection_policy
    ):
        failures.append("rollback_missing")
    else:
        section_ready["rollback_ready"] = True


def _check_schema_runtime(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {
        "schema_migration_required",
        "db_repair_required",
        "runtime_boundary_safe",
    }
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("schema_runtime_invalid")
        return

    schema_required = section["schema_migration_required"]
    db_repair = section["db_repair_required"]
    runtime_safe = section["runtime_boundary_safe"]

    if (
        not _is_bool(schema_required)
        or not _is_bool(db_repair)
        or not _is_bool(runtime_safe)
    ):
        failures.append("schema_runtime_invalid")
        return

    if schema_required is True:
        failures.append("schema_migration_required")
    if db_repair is True:
        failures.append("db_repair_required")
    if runtime_safe is not True:
        failures.append("runtime_boundary_violation")

    if schema_required is False and db_repair is False:
        section_ready["schema_migration_safe"] = True
    if runtime_safe is True:
        section_ready["runtime_boundary_safe"] = True


def _check_operator_confirmation(
    section: object,
    failures: list[str],
    section_ready: dict[str, bool],
) -> None:
    expected_keys = {"cli_confirmation_present", "operator_safe"}
    if not isinstance(section, Mapping) or set(section.keys()) != expected_keys:
        failures.append("operator_confirmation_invalid")
        return

    cli_confirmation_present = section["cli_confirmation_present"]
    operator_safe = section["operator_safe"]

    if not _is_bool(cli_confirmation_present) or not _is_bool(operator_safe):
        failures.append("operator_confirmation_invalid")
        return

    if cli_confirmation_present is not True or operator_safe is not True:
        failures.append("cli_confirmation_missing")
        return

    section_ready["operator_confirmation_ready"] = True
    section_ready["operator_safe"] = True


__all__ = [
    "WriteSideRecoveryPreconditionCheck",
    "check_write_side_recovery_preconditions",
    "render_write_side_recovery_precondition_check",
    "write_side_recovery_precondition_manifest",
]
