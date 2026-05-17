"""Sanitized failure bundle generation."""

from __future__ import annotations

from typing import Mapping

from kernel.security.ai_context_firewall import filter_ai_context
from kernel.tasks.run_id import digest_payload

__all__ = ["build_failure_bundle"]


def build_failure_bundle(
    *,
    task_id: str,
    run_id: str,
    stage: str,
    error_class: str,
    message: str,
    state_snapshot: Mapping[str, object],
    input_snapshot: Mapping[str, object],
    policy_version: str,
    code_version: str,
    quarantine_ref: str,
    rollback_ref: str,
) -> dict[str, object]:
    filtered_message = filter_ai_context({"message": message}).filtered_context["message"]
    payload = {
        "task_id": task_id,
        "run_id": run_id,
        "stage": stage,
        "error_class": error_class,
        "state_snapshot_digest": digest_payload(state_snapshot),
        "input_snapshot_digest": digest_payload(input_snapshot),
    }
    failure_id = "failure_" + digest_payload(payload).split(":", 1)[1][:24]
    return {
        "failure_id": failure_id,
        "task_id": task_id,
        "run_id": run_id,
        "stage": stage,
        "error_class": error_class,
        "sanitized_message": filtered_message,
        "state_snapshot_digest": payload["state_snapshot_digest"],
        "input_snapshot_digest": payload["input_snapshot_digest"],
        "policy_version": policy_version,
        "code_version": code_version,
        "quarantine_ref": quarantine_ref,
        "rollback_ref": rollback_ref,
    }
