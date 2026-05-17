"""Deterministic replay plan descriptor foundation.

Produces replay plan descriptors for exact replay only. No cloud re-query,
no live provider calls. Strict field typing enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.runtime._strict_validation import (
    validate_required_digest_fields,
    validate_required_string_fields,
)

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
)

_GATED_BOOL_FIELDS = (
    "provider_live_requery",
)

_REQUIRED_STRING_FIELDS = (
    "task_id",
    "run_id",
    "replay_id",
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS = (
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
    """Validate a replay plan against policy boundaries with strict typing.

    provider_live_requery must be actual bool (True rejected).
    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    # provider_live_requery — must be actual bool
    for field in _GATED_BOOL_FIELDS:
        value = payload_dict.get(field)
        if value is not None:
            if not isinstance(value, bool):
                failures.append(f"{field}_must_be_bool")
            elif value is True:
                failures.append(f"{field}_rejected_exact_replay_only")

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    seed = {
        "task_id": str(payload_dict.get("task_id", "")),
        "run_id": str(payload_dict.get("run_id", "")),
        "replay_id": str(payload_dict.get("replay_id", "")),
        "policy_version": str(payload_dict.get("policy_version", "")),
        "code_version": str(payload_dict.get("code_version", "")),
    }
    replan_id = "replan_" + _digest_payload(seed).split(":", 1)[1][:24]

    if failures:
        return ReplayPlanReceipt(False, replan_id, tuple(failures))
    return ReplayPlanReceipt(True, replan_id, ())
