"""HFX_008 landed dry-run materialization chain."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.builtin_workers import hfx_008_real_run_commands
from kernel.os_engine.database import stable_content_hash
from kernel.os_engine.local_job_runner import LocalJobRunner, LocalJobRunResult
from kernel.os_engine.local_os_runtime import LocalOSRuntime


HFX_008_STAGES: tuple[str, ...] = (
    "topology_audit",
    "single_frame_proof",
    "human_review_decision",
    "materialization_summary",
)


@dataclass(frozen=True, slots=True)
class Hfx008LandingChainSummary:
    asset: str
    dry_run: bool
    job_ids: tuple[str, ...]
    stage_statuses: tuple[dict[str, str], ...]
    artifact_ids: tuple[str, ...]
    materialization_statuses: tuple[dict[str, str], ...]
    blockers: tuple[str, ...]
    final_claim_allowed: bool
    real_run_commands: tuple[str, ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def build_hfx_008_dry_run_jobs(
    runtime: LocalOSRuntime,
    *,
    resource_package_path: Path | None = None,
) -> tuple[str, ...]:
    job_ids: list[str] = []
    resource_path = resource_package_path or runtime.root / "missing_hfx_008_resource_package"
    for stage in HFX_008_STAGES:
        job_id = f"hfx_008_{stage}_dry_run"
        if _job_exists(runtime, job_id):
            job_ids.append(job_id)
            continue
        runtime.job_queue.create_job(
            job_id=job_id,
            job_type="hfx_008_materialization_dry_run",
            input_manifest={
                "inputs": {
                    "asset": "HFX_008",
                    "stage": stage,
                    "dry_run": True,
                    "resource_package_path": str(resource_path),
                },
                "max_runtime_seconds": 60,
                "memory_limit_mb": 512,
            },
            output_dir=str(runtime.artifact_store.artifact_root / "hfx_008"),
            human_review_required=stage != "topology_audit",
            dry_run=True,
            local_only=True,
        )
        runtime.job_queue.admit_job(job_id)
        runtime.job_queue.enqueue_job(job_id)
        job_ids.append(job_id)
    return tuple(job_ids)


def execute_hfx_008_dry_run_chain(
    runtime: LocalOSRuntime,
    *,
    resource_package_path: Path | None = None,
) -> Hfx008LandingChainSummary:
    job_ids = build_hfx_008_dry_run_jobs(runtime, resource_package_path=resource_package_path)
    runner = LocalJobRunner(runtime)
    run_results: list[LocalJobRunResult] = []
    for job_id in job_ids:
        state = runtime.job_queue.get_job_state(job_id)
        if state.current_status in {"admitted", "pending"}:
            run_results.append(runner.run_next(job_id=job_id))
    _ = run_results
    return summarize_hfx_008_landing_chain(runtime, job_ids=job_ids)


def summarize_hfx_008_landing_chain(
    runtime: LocalOSRuntime,
    *,
    job_ids: tuple[str, ...] | None = None,
) -> Hfx008LandingChainSummary:
    ids = job_ids or tuple(f"hfx_008_{stage}_dry_run" for stage in HFX_008_STAGES if _job_exists(runtime, f"hfx_008_{stage}_dry_run"))
    stage_statuses = []
    artifact_ids: list[str] = []
    for job_id in ids:
        state = runtime.job_queue.get_job_state(job_id)
        stage_statuses.append({"job_id": job_id, "status": state.current_status, "final_claim_allowed": str(state.final_claim_allowed).lower()})
        artifact_ids.extend(state.artifact_ids)
    materializations = _materialization_rows(runtime)
    blockers = _chain_blockers(materializations=materializations, runtime=runtime)
    payload = {
        "artifact_ids": tuple(sorted(set(artifact_ids))),
        "asset": "HFX_008",
        "blockers": tuple(sorted(blockers)),
        "dry_run": True,
        "final_claim_allowed": False,
        "job_ids": ids,
        "materialization_statuses": tuple(materializations),
        "real_run_commands": tuple(hfx_008_real_run_commands(runtime.repo_root)),
        "stage_statuses": tuple(stage_statuses),
    }
    return Hfx008LandingChainSummary(content_hash=stable_content_hash(payload), **payload)


def _job_exists(runtime: LocalOSRuntime, job_id: str) -> bool:
    with runtime.database.connect() as connection:
        return connection.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone() is not None


def _materialization_rows(runtime: LocalOSRuntime) -> tuple[dict[str, str], ...]:
    with runtime.database.connect() as connection:
        rows = connection.execute(
            """
            SELECT materialization_id, target_artifact_id, status, final_claim_allowed, validation_json
            FROM materializations
            WHERE target_artifact_id LIKE 'hfx_008_%'
            ORDER BY target_artifact_id
            """
        ).fetchall()
    return tuple(
        {
            "final_claim_allowed": str(bool(row["final_claim_allowed"])).lower(),
            "materialization_id": str(row["materialization_id"]),
            "status": str(row["status"]),
            "target_artifact_id": str(row["target_artifact_id"]),
            "validation_json": str(row["validation_json"]),
        }
        for row in rows
    )


def _chain_blockers(*, materializations: tuple[dict[str, str], ...], runtime: LocalOSRuntime) -> list[str]:
    blockers = {"real visual proof missing", "human review approval missing"}
    if any("resource_missing" in item["validation_json"] and "true" in item["validation_json"].lower() for item in materializations):
        blockers.add("resource package missing")
    if not materializations:
        blockers.add("dry-run materializations missing")
    reviews = runtime.human_review_gate.list_reviews()
    if any(review.decision == "approved" for review in reviews):
        blockers.add("approval alone cannot unlock final claim without valid visual proof")
    return sorted(blockers)
