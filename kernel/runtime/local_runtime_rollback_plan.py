"""Deterministic rollback planning receipt for local runtime review gate.

This module produces a symbolic rollback plan that describes what would be
rolled back WITHOUT executing any rollback, shell commands, file deletion,
or database mutations.

No provider calls, network access, secrets, env reads, subprocess, or
SQLite mutations happen here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "RollbackPlanReceipt",
    "build_rollback_plan",
    "validate_rollback_plan",
]

_POLICY_VERSION = "local-runtime-rollback-plan-v1"
_CODE_VERSION = "0.1.0"

_FORBIDDEN_ROLLBACK_FIELDS = frozenset({
    "shell_command",
    "shell_commands",
    "raw_exception",
    "raw_exception_text",
    "raw_traceback",
    "raw_prompt",
    "raw_provider_response",
    "secret",
    "secret_value",
    "api_key",
    "token",
    "password",
    "env_value",
    "env",
    "environment_value",
    "file_deletion",
    "file_deletion_command",
    "database_mutation",
    "sqlite_mutation",
    "db_write",
})


@dataclass(frozen=True)
class RollbackPlanReceipt:
    """Immutable symbolic rollback plan. Does not execute any rollback operations."""

    rollback_scope: str
    affected_run_id: str
    affected_task_id: str
    receipt_hashes_to_discard: tuple[str, ...]
    audit_refs_to_preserve: tuple[str, ...]
    manual_operator_steps: tuple[str, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "affected_run_id": self.affected_run_id,
            "affected_task_id": self.affected_task_id,
            "audit_refs_to_preserve": list(self.audit_refs_to_preserve),
            "code_version": self.code_version,
            "manual_operator_steps": list(self.manual_operator_steps),
            "policy_version": self.policy_version,
            "receipt_hashes_to_discard": list(self.receipt_hashes_to_discard),
            "rollback_scope": self.rollback_scope,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_rollback_plan(
    *,
    rollback_scope: str,
    affected_run_id: str,
    affected_task_id: str,
    receipt_hashes_to_discard: tuple[str, ...] = (),
    audit_refs_to_preserve: tuple[str, ...] = (),
    manual_operator_steps: tuple[str, ...] = (),
    policy_version: str = _POLICY_VERSION,
    code_version: str = _CODE_VERSION,
    observed_at: str | None = None,
) -> RollbackPlanReceipt:
    """Build a deterministic symbolic rollback plan.

    The plan describes what would be rolled back. It does NOT execute any
    rollback, shell commands, file deletion, or database mutations.
    """

    for field, value in (
        ("rollback_scope", rollback_scope),
        ("affected_run_id", affected_run_id),
        ("affected_task_id", affected_task_id),
        ("policy_version", policy_version),
        ("code_version", code_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")

    if not _validate_forbidden_fields(manual_operator_steps, "manual_operator_steps"):
        raise ValueError("manual_operator_steps_contain_forbidden_content")
    if not _validate_step_ids_symbolic(manual_operator_steps):
        raise ValueError("manual_operator_steps_must_be_symbolic_only")

    if not isinstance(receipt_hashes_to_discard, tuple):
        raise ValueError("receipt_hashes_to_discard_must_be_tuple")
    if not isinstance(audit_refs_to_preserve, tuple):
        raise ValueError("audit_refs_to_preserve_must_be_tuple")
    if not isinstance(manual_operator_steps, tuple):
        raise ValueError("manual_operator_steps_must_be_tuple")

    for entry in receipt_hashes_to_discard:
        if not strict_digest(entry):
            raise ValueError("receipt_hash_entry_must_be_valid_digest")

    observed = _observed_at(observed_at)
    material = {
        "affected_run_id": affected_run_id,
        "affected_task_id": affected_task_id,
        "audit_refs_to_preserve": list(audit_refs_to_preserve),
        "code_version": code_version,
        "manual_operator_steps": list(manual_operator_steps),
        "policy_version": policy_version,
        "receipt_hashes_to_discard": list(receipt_hashes_to_discard),
        "rollback_scope": rollback_scope,
    }
    return RollbackPlanReceipt(
        rollback_scope=rollback_scope,
        affected_run_id=affected_run_id,
        affected_task_id=affected_task_id,
        receipt_hashes_to_discard=receipt_hashes_to_discard,
        audit_refs_to_preserve=audit_refs_to_preserve,
        manual_operator_steps=manual_operator_steps,
        policy_version=policy_version,
        code_version=code_version,
        content_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_rollback_plan(plan: RollbackPlanReceipt) -> bool:
    """Validate that the rollback plan is deterministic and contains no forbidden material."""

    if not isinstance(plan, RollbackPlanReceipt):
        return False
    for field in ("rollback_scope", "affected_run_id", "affected_task_id", "policy_version", "code_version"):
        if not strict_nonempty_string(getattr(plan, field)):
            return False
    if not isinstance(plan.receipt_hashes_to_discard, tuple):
        return False
    if not isinstance(plan.audit_refs_to_preserve, tuple):
        return False
    if not isinstance(plan.manual_operator_steps, tuple):
        return False
    for entry in plan.receipt_hashes_to_discard:
        if not strict_digest(entry):
            return False
    if not strict_digest(plan.content_hash):
        return False
    if not _validate_step_ids_symbolic(plan.manual_operator_steps):
        return False
    if not _validate_forbidden_fields(plan.manual_operator_steps, "manual_operator_steps"):
        return False
    return plan.content_hash == digest_payload(plan.deterministic_material())


def _validate_forbidden_fields(steps: tuple[str, ...], context: str) -> bool:
    lowered = [s.lower() for s in steps]
    for forbidden in _FORBIDDEN_ROLLBACK_FIELDS:
        for step in lowered:
            if forbidden in step:
                return False
    return True


def _validate_step_ids_symbolic(steps: tuple[str, ...]) -> bool:
    for step in steps:
        if not isinstance(step, str):
            return False
        if not step.strip():
            return False
        lower = step.lower()
        for marker in (
            "rm -", "rm ", "del ", "delete ", "drop ", "truncate",
            "sudo ", "chmod ", "chown ", "exec(", "eval(", "subprocess",
            "os.system", "shell_exec", "__import__",
        ):
            if marker in lower:
                return False
    return True


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("observed_at_must_be_nonempty_string")
    return value
