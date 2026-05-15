
"""WAL checkpoint plan audit integration.

This module combines the existing WAL observation collector and checkpoint

policy planner into one non-mutating audit report.

It does not execute checkpointing, does not truncate WAL files, does not open

SQLite for write, and does not mutate SQLite state.

"""

from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from typing import Mapping

from kernel.personal_ai.io_utils import write_json_atomically

from kernel.stores.sqlite.wal_checkpoint_observation_collector import (

    collect_wal_checkpoint_observation,

)

from kernel.stores.sqlite.wal_checkpoint_policy import (

    WalCheckpointPolicy,

    build_wal_checkpoint_plan,

)

__all__ = [

    "WalCheckpointPlanAuditResult",

    "run_wal_checkpoint_plan_audit",

]

_REPORT_FILE = "wal_checkpoint_plan_audit_report.json"

_REPORT_TYPE = "seos_wal_checkpoint_plan_audit_v1"

@dataclass(frozen=True)

class WalCheckpointPlanAuditResult:

    report_path: Path

    report: dict[str, object]

    observation: dict[str, object]

    policy: dict[str, object]

    plan: dict[str, object]

    checkpoint_required: bool

    execution_allowed: bool

    truncate_allowed: bool

    mutating_checkpoint_executed: bool

    required_human_approval: bool

def run_wal_checkpoint_plan_audit(

    *,

    db_path: Path,

    output_dir: Path,

    policy: WalCheckpointPolicy | Mapping[str, object],

    now_seconds: int | None = None,

    snapshot_creation_pending: bool = False,

    dirty_tail_detected: bool = False,

    mid_segment_corruption_detected: bool = False,

    allow_readonly_page_size_query: bool = False,

    page_size_override: int | None = None,

) -> WalCheckpointPlanAuditResult:

    out = Path(output_dir)

    if not out.exists() or not out.is_dir():

        raise ValueError("output_dir is missing")

    report_path = out / _REPORT_FILE

    if report_path.exists():

        raise ValueError("wal checkpoint plan audit report already exists")

    observation_result = collect_wal_checkpoint_observation(

        db_path=Path(db_path),

        now_seconds=now_seconds,

        snapshot_creation_pending=snapshot_creation_pending,

        dirty_tail_detected=dirty_tail_detected,

        mid_segment_corruption_detected=mid_segment_corruption_detected,

        allow_readonly_page_size_query=allow_readonly_page_size_query,

        page_size_override=page_size_override,

    )

    plan_result = build_wal_checkpoint_plan(policy, observation_result.observation)

    observation_payload = dict(observation_result.payload)

    plan_payload = dict(plan_result.plan)

    policy_payload = dict(plan_payload.get("policy", {}))

    report = {

        "report_type": _REPORT_TYPE,

        "complete": True,

        "observation": observation_payload,

        "policy": policy_payload,

        "plan": plan_payload,

        "checkpoint_required": plan_result.checkpoint_required,

        "reason_codes": list(plan_payload.get("reason_codes", [])),

        "recommended_mode": plan_payload.get("recommended_mode"),

        "requires_human_approval": True,

        "execution_allowed": False,

        "truncate_allowed": False,

        "database_opened_read_only": bool(

            observation_payload.get("database_opened_read_only", False)

        ),

        "database_opened_for_write": False,

        "write_transaction_opened": False,

        "checkpoint_executed": False,

        "pragma_wal_checkpoint_executed": False,

        "wal_truncate_executed": False,

        "sqlite_state_mutated": False,

        "mutating_checkpoint_executed": False,

        "planner_only": True,

        "observation_only": True,

    }

    write_json_atomically(report_path, report)

    return WalCheckpointPlanAuditResult(

        report_path=report_path,

        report=report,

        observation=observation_payload,

        policy=policy_payload,

        plan=plan_payload,

        checkpoint_required=plan_result.checkpoint_required,

        execution_allowed=False,

        truncate_allowed=False,

        mutating_checkpoint_executed=False,

        required_human_approval=True,

    )

