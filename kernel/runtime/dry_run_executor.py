"""Dry-run runtime executor foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.security.security_classification import normalize_classification
from kernel.tasks.run_id import deterministic_run_id, digest_payload
from kernel.tasks.task_manifest import validate_task_manifest

__all__ = ["DryRunExecutionResult", "execute_dry_run"]


@dataclass(frozen=True)
class DryRunExecutionResult:
    accepted: bool
    dry_run_result: dict[str, object]
    failures: tuple[str, ...]


def execute_dry_run(task_manifest: Mapping[str, object]) -> DryRunExecutionResult:
    validation = validate_task_manifest(task_manifest)
    if not validation.accepted:
        return DryRunExecutionResult(False, {}, validation.failures)
    manifest = validation.manifest
    classification = normalize_classification(manifest.get("classification"))
    caps = [str(item) for item in manifest.get("requested_capabilities", [])]
    provider_bound = bool(manifest.get("provider_bound")) or any("provider" in cap.lower() for cap in caps)
    if provider_bound and classification in {"SECRET", "CROWN_JEWEL"}:
        return DryRunExecutionResult(False, {}, ("provider_bound_sensitive_task_forbidden",))
    run_id = deterministic_run_id(
        task_id=str(manifest["task_id"]),
        policy_version=str(manifest["policy_version"]),
        code_version=str(manifest["code_version"]),
        input_digest=str(manifest["input_digest"]),
    )
    planned_events = [
        {
            "event_id": f"{run_id}:001",
            "run_id": run_id,
            "task_id": manifest["task_id"],
            "stage": "dry_run",
            "event_type": "plan_created",
            "logical_time": 1,
            "payload_digest": digest_payload({"task_id": manifest["task_id"], "stage": "dry_run"}),
        },
        {
            "event_id": f"{run_id}:002",
            "run_id": run_id,
            "task_id": manifest["task_id"],
            "stage": "dry_run",
            "event_type": "provider_call_skipped",
            "logical_time": 2,
            "payload_digest": digest_payload({"provider_call": "skipped", "dry_run_only": True}),
        },
    ]
    return DryRunExecutionResult(
        True,
        {
            "result_type": "dry_run_result",
            "dry_run_only": True,
            "provider_calls_executed": 0,
            "run_id": run_id,
            "task_id": manifest["task_id"],
            "planned_events": planned_events,
        },
        (),
    )
