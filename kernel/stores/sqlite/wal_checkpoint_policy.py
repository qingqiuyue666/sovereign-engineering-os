"""SQLite WAL checkpoint policy planner foundation.

This module defines a non-mutating checkpoint policy record and a deterministic
planner. It never opens a SQLite database, never invokes checkpointing, never
truncates WAL files, and never mutates SQLite state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "WalCheckpointObservation",
    "WalCheckpointPlanResult",
    "WalCheckpointPolicy",
    "build_wal_checkpoint_plan",
    "write_wal_checkpoint_plan",
]

_POLICY_TYPE = "seos_wal_checkpoint_policy_v1"
_PLAN_TYPE = "seos_wal_checkpoint_plan_v1"
_PLAN_FILE = "wal_checkpoint_plan.json"
_ALLOWED_MODES = frozenset({"passive", "full", "restart"})


@dataclass(frozen=True)
class WalCheckpointPolicy:
    policy_id: str
    max_wal_pages: int
    max_wal_bytes: int
    max_age_seconds: int
    trigger_on_snapshot: bool
    manual_checkpoint_allowed: bool
    truncate_allowed: bool
    created_at: str
    version: str = "v1"


@dataclass(frozen=True)
class WalCheckpointObservation:
    wal_pages: int
    wal_bytes: int
    age_seconds: int
    snapshot_creation_pending: bool
    dirty_tail_detected: bool = False
    mid_segment_corruption_detected: bool = False


@dataclass(frozen=True)
class WalCheckpointPlanResult:
    plan: dict[str, object]
    checkpoint_required: bool
    execution_allowed: bool
    truncate_allowed: bool
    mutating_checkpoint_executed: bool
    required_human_approval: bool


def build_wal_checkpoint_plan(
    policy: WalCheckpointPolicy | Mapping[str, object],
    observation: WalCheckpointObservation | Mapping[str, object],
) -> WalCheckpointPlanResult:
    normalized_policy = _normalize_policy(policy)
    normalized_observation = _normalize_observation(observation)
    failures = _validate_policy(normalized_policy) + _validate_observation(normalized_observation)
    reason_codes: list[str] = []

    if not failures:
        if normalized_observation.wal_pages >= normalized_policy.max_wal_pages:
            reason_codes.append("wal_pages_threshold_reached")
        if normalized_observation.wal_bytes >= normalized_policy.max_wal_bytes:
            reason_codes.append("wal_bytes_threshold_reached")
        if normalized_observation.age_seconds >= normalized_policy.max_age_seconds:
            reason_codes.append("wal_age_threshold_reached")
        if normalized_policy.trigger_on_snapshot and normalized_observation.snapshot_creation_pending:
            reason_codes.append("snapshot_trigger_pending")
        if normalized_observation.dirty_tail_detected:
            reason_codes.append("dirty_tail_requires_recovery_review")
        if normalized_observation.mid_segment_corruption_detected:
            reason_codes.append("mid_segment_corruption_requires_recovery_review")

    checkpoint_required = bool(reason_codes) and not failures
    recommended_mode = _recommended_mode(normalized_policy, normalized_observation, reason_codes)
    plan = {
        "plan_type": _PLAN_TYPE,
        "complete": not failures,
        "checkpoint_required": checkpoint_required,
        "reason_codes": sorted(reason_codes),
        "policy": _policy_to_dict(normalized_policy),
        "observation": _observation_to_dict(normalized_observation),
        "recommended_mode": recommended_mode,
        "requires_human_approval": True,
        "execution_allowed": False,
        "manual_checkpoint_allowed_by_policy": normalized_policy.manual_checkpoint_allowed,
        "truncate_allowed_by_policy": normalized_policy.truncate_allowed,
        "truncate_allowed": False,
        "database_opened": False,
        "pragma_wal_checkpoint_executed": False,
        "wal_truncate_executed": False,
        "sqlite_state_mutated": False,
        "mutating_checkpoint_executed": False,
        "planner_only": True,
        "failures": sorted(failures),
    }
    return WalCheckpointPlanResult(
        plan=plan,
        checkpoint_required=checkpoint_required,
        execution_allowed=False,
        truncate_allowed=False,
        mutating_checkpoint_executed=False,
        required_human_approval=True,
    )


def write_wal_checkpoint_plan(
    policy: WalCheckpointPolicy | Mapping[str, object],
    observation: WalCheckpointObservation | Mapping[str, object],
    output_dir: Path,
) -> WalCheckpointPlanResult:
    out = Path(output_dir)
    if not out.exists() or not out.is_dir():
        raise ValueError("output_dir is missing")
    plan_path = out / _PLAN_FILE
    if plan_path.exists():
        raise ValueError("wal checkpoint plan already exists")
    result = build_wal_checkpoint_plan(policy, observation)
    write_json_atomically(plan_path, result.plan)
    return result


def _normalize_policy(policy: WalCheckpointPolicy | Mapping[str, object]) -> WalCheckpointPolicy:
    if isinstance(policy, WalCheckpointPolicy):
        return policy
    if not isinstance(policy, Mapping):
        raise ValueError("policy must be mapping or WalCheckpointPolicy")
    return WalCheckpointPolicy(
        policy_id=str(policy.get("policy_id", "")),
        max_wal_pages=_as_int(policy.get("max_wal_pages"), "max_wal_pages"),
        max_wal_bytes=_as_int(policy.get("max_wal_bytes"), "max_wal_bytes"),
        max_age_seconds=_as_int(policy.get("max_age_seconds"), "max_age_seconds"),
        trigger_on_snapshot=_as_bool(policy.get("trigger_on_snapshot"), "trigger_on_snapshot"),
        manual_checkpoint_allowed=_as_bool(policy.get("manual_checkpoint_allowed"), "manual_checkpoint_allowed"),
        truncate_allowed=_as_bool(policy.get("truncate_allowed"), "truncate_allowed"),
        created_at=str(policy.get("created_at", "")),
        version=str(policy.get("version", "v1")),
    )


def _normalize_observation(observation: WalCheckpointObservation | Mapping[str, object]) -> WalCheckpointObservation:
    if isinstance(observation, WalCheckpointObservation):
        return observation
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be mapping or WalCheckpointObservation")
    return WalCheckpointObservation(
        wal_pages=_as_int(observation.get("wal_pages"), "wal_pages"),
        wal_bytes=_as_int(observation.get("wal_bytes"), "wal_bytes"),
        age_seconds=_as_int(observation.get("age_seconds"), "age_seconds"),
        snapshot_creation_pending=_as_bool(observation.get("snapshot_creation_pending"), "snapshot_creation_pending"),
        dirty_tail_detected=_as_bool(observation.get("dirty_tail_detected", False), "dirty_tail_detected"),
        mid_segment_corruption_detected=_as_bool(
            observation.get("mid_segment_corruption_detected", False),
            "mid_segment_corruption_detected",
        ),
    )


def _validate_policy(policy: WalCheckpointPolicy) -> list[str]:
    failures: list[str] = []
    if not policy.policy_id:
        failures.append("policy_id_missing")
    if policy.version != "v1":
        failures.append("policy_version_not_v1")
    if policy.max_wal_pages <= 0:
        failures.append("max_wal_pages_must_be_positive")
    if policy.max_wal_bytes <= 0:
        failures.append("max_wal_bytes_must_be_positive")
    if policy.max_age_seconds <= 0:
        failures.append("max_age_seconds_must_be_positive")
    if not policy.created_at:
        failures.append("created_at_missing")
    if policy.truncate_allowed:
        failures.append("truncate_allowed_forbidden_in_foundation")
    return failures


def _validate_observation(observation: WalCheckpointObservation) -> list[str]:
    failures: list[str] = []
    if observation.wal_pages < 0:
        failures.append("wal_pages_negative")
    if observation.wal_bytes < 0:
        failures.append("wal_bytes_negative")
    if observation.age_seconds < 0:
        failures.append("age_seconds_negative")
    return failures


def _recommended_mode(
    policy: WalCheckpointPolicy,
    observation: WalCheckpointObservation,
    reason_codes: list[str],
) -> str:
    if observation.mid_segment_corruption_detected or observation.dirty_tail_detected:
        return "none_recovery_review_required"
    if not reason_codes:
        return "none"
    if not policy.manual_checkpoint_allowed:
        return "none_manual_checkpoint_not_allowed"
    return "passive"


def _policy_to_dict(policy: WalCheckpointPolicy) -> dict[str, object]:
    return {
        "policy_type": _POLICY_TYPE,
        "policy_id": policy.policy_id,
        "max_wal_pages": policy.max_wal_pages,
        "max_wal_bytes": policy.max_wal_bytes,
        "max_age_seconds": policy.max_age_seconds,
        "trigger_on_snapshot": policy.trigger_on_snapshot,
        "manual_checkpoint_allowed": policy.manual_checkpoint_allowed,
        "truncate_allowed": policy.truncate_allowed,
        "created_at": policy.created_at,
        "version": policy.version,
    }


def _observation_to_dict(observation: WalCheckpointObservation) -> dict[str, object]:
    return {
        "wal_pages": observation.wal_pages,
        "wal_bytes": observation.wal_bytes,
        "age_seconds": observation.age_seconds,
        "snapshot_creation_pending": observation.snapshot_creation_pending,
        "dirty_tail_detected": observation.dirty_tail_detected,
        "mid_segment_corruption_detected": observation.mid_segment_corruption_detected,
    }


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(field_name + " must be integer")
    return value


def _as_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(field_name + " must be boolean")
    return value
