"""Deterministic replay plan descriptor foundation.

Produces replay plan descriptors for exact replay only. No cloud re-query,
no live provider calls. The plan captures input snapshot refs and version
tuples to enable deterministic replay verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "ReplayPlanReceipt",
    "ReplayPlanRejection",
    "validate_replay_plan",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "provider_live_requery",
)

_REQUIRED_FIELDS = (
    "task_id",
    "run_id",
    "replay_id",
    "input_snapshot_digest",
    "state_snapshot_digest",
    "policy_version",
    "code_version",
    "environment_descriptor_digest",
    "expected_output_digest",
)

_DIGEST_FIELDS = (
    "input_snapshot_digest",
    "state_snapshot_digest",
    "environment_descriptor_digest",
    "expected_output_digest",
)


class ReplayPlanRejection(ValueError):
    """Raised when a replay plan violates policy boundaries."""


@dataclass(frozen=True)
class ReplayPlanReceipt:
    accepted: bool
    replan_id: str
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "replan_id": self.replan_id,
            "failures": list(self.failures),
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_replay_plan(payload: Mapping[str, object]) -> ReplayPlanReceipt:
    """Validate a replay plan against policy boundaries.

    Returns accepted=True only if all required fields are present, no forbidden
    fields are found, all digests have sha256: prefix, and provider_live_requery
    is not set to true (exact replay only).
    """
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            if field == "provider_live_requery":
                if payload[field] is True:
                    failures.append("provider_live_requery_rejected_exact_replay_only")
            else:
                failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    for field in _DIGEST_FIELDS:
        if field in payload:
            val = payload[field]
            if isinstance(val, str) and val and not val.startswith("sha256:"):
                failures.append(f"{field}_must_be_sha256_prefixed")

    seed = {
        "task_id": str(payload.get("task_id", "")),
        "run_id": str(payload.get("run_id", "")),
        "replay_id": str(payload.get("replay_id", "")),
        "policy_version": str(payload.get("policy_version", "")),
        "code_version": str(payload.get("code_version", "")),
    }
    replan_id = "replan_" + _digest_payload(seed).split(":", 1)[1][:24]

    if failures:
        return ReplayPlanReceipt(False, replan_id, tuple(failures))

    return ReplayPlanReceipt(True, replan_id, ())
