"""Task contract creation for operator tasks."""

from __future__ import annotations

import uuid
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

__all__ = ["create_operator_task_envelope", "OperatorTaskResult"]


@dataclass
class OperatorTaskResult:
    accepted: bool
    envelope: dict[str, object]
    failures: list[str] = field(default_factory=list)


def create_operator_task_envelope(payload: dict[str, object]) -> OperatorTaskResult:
    failures: list[str] = []

    objective = payload.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        failures.append("missing_or_empty_objective")

    classification = payload.get("classification")
    if classification not in ("PUBLIC", "INTERNAL", "RESTRICTED"):
        failures.append("invalid_or_missing_classification")

    policy_version = payload.get("policy_version")
    if policy_version != "v12":
        failures.append("unsupported_policy_version")

    if failures:
        return OperatorTaskResult(accepted=False, envelope={}, failures=failures)

    task_id = _derive_task_id(payload)
    envelope: dict[str, object] = {
        "task_id": task_id,
        "envelope_version": "v12",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "objective": objective,
        "classification": classification,
        "policy_version": policy_version,
        "requested_capabilities": payload.get("requested_capabilities", []),
        "code_version": payload.get("code_version", "unknown"),
        "descriptor": payload.get("descriptor", {}),
        "signature": _sign_envelope(task_id, payload),
    }
    return OperatorTaskResult(accepted=True, envelope=envelope, failures=[])


def _derive_task_id(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"task-{digest[:16]}"


def _sign_envelope(task_id: str, payload: dict[str, object]) -> str:
    raw = f"{task_id}:{json.dumps(payload, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()
