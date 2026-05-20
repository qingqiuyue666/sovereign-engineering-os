"""Safe built-in workers for the landed local OS runtime."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.context_router import ContextRouter, ContextUseCase
from kernel.os_engine.database import OSDatabase, stable_content_hash, utc_now_iso, validate_no_secret_like
from kernel.os_engine.human_review_gate import HumanReviewGate, HumanReviewGateError
from kernel.os_engine.job_queue import Job
from kernel.os_engine.materialization import (
    MaterializationDecision,
    MaterializationPlan,
    TargetArtifact,
    UpstreamInput,
    ValidationResult,
    decide_materialization,
)
from kernel.os_engine.sqlite_artifact_store import ArtifactType, ReviewStatus, SQLiteArtifactStore
from kernel.os_engine.worker_registry import (
    BaseWorker,
    WorkerAdmissionError,
    WorkerRegistry,
    WorkerRunResult,
)


class BuiltinWorkerError(RuntimeError):
    """Raised when a local built-in worker cannot complete safely."""


@dataclass(frozen=True, slots=True)
class BuiltinWorkerContext:
    repo_root: Path
    runtime_root: Path
    artifact_root: Path
    crash_dir: Path
    database: OSDatabase
    sqlite_artifact_store: SQLiteArtifactStore
    human_review_gate: HumanReviewGate
    environment: dict[str, str]


class GitStatusWorker(BaseWorker):
    name = "GitStatusWorker"
    capabilities = frozenset({"git_read", "artifact_collection", "subprocess"})
    safety_boundary = "read_only_git_status_shell_free"

    async def preflight(self, job: Job, context: BuiltinWorkerContext) -> None:  # type: ignore[override]
        await super().preflight(job, context)  # type: ignore[arg-type]
        if not (context.repo_root / ".git").exists():
            raise WorkerAdmissionError(f"repo root is not a git worktree: {context.repo_root}")

    async def run(self, job: Job, context: BuiltinWorkerContext) -> WorkerRunResult:  # type: ignore[override]
        await self.preflight(job, context)
        if bool(job.inputs.get("dry_run_git_status", False)):
            returncode = 0
            stdout = "## dry-run git status\n"
            stderr = ""
        else:
            completed = await asyncio.to_thread(
                subprocess.run,
                ["git", "status", "--short", "--branch"],
                cwd=context.repo_root,
                capture_output=True,
                text=True,
                timeout=float(job.inputs.get("timeout_seconds", 10)),
                check=False,
                shell=False,
            )
            returncode = int(completed.returncode)
            stdout = str(completed.stdout)
            stderr = str(completed.stderr)
        artifact = _write_json_artifact(
            context.artifact_root,
            "git_status",
            f"{job.id}.json",
            {
                "job_id": job.id,
                "worker": self.name,
                "command": ["git", "status", "--short", "--branch"],
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
                "mutated_repository": False,
                "network_calls": 0,
                "created_at": "1970-01-01T00:00:00+00:00",
            },
        )
        return WorkerRunResult(
            succeeded=returncode == 0,
            quarantined=False,
            exit_code=returncode,
            stdout=stdout,
            stderr=stderr,
            artifact_paths=(artifact,),
            metadata={
                "artifact_type": ArtifactType.AUDIT_JSON.value,
                "mutated_repository": False,
                "network_calls": 0,
                "physical_proof": False,
            },
        )


class ContextPackWorker(BaseWorker):
    name = "ContextPackWorker"
    capabilities = frozenset({"context_pack", "artifact_collection"})
    safety_boundary = "deterministic_context_router_no_network"

    async def preflight(self, job: Job, context: BuiltinWorkerContext) -> None:  # type: ignore[override]
        await super().preflight(job, context)  # type: ignore[arg-type]
        if not (context.repo_root / ".git").exists():
            raise WorkerAdmissionError(f"repo root is not a git worktree: {context.repo_root}")

    async def run(self, job: Job, context: BuiltinWorkerContext) -> WorkerRunResult:  # type: ignore[override]
        await self.preflight(job, context)
        router = ContextRouter(
            repo_root=context.repo_root,
            output_dir=context.artifact_root / "context_packs",
            command_timeout_seconds=float(job.inputs.get("timeout_seconds", 10)),
        )
        result = await router.build_context_pack(
            max_files=int(job.inputs.get("max_files", 32)),
            task_instructions=str(
                job.inputs.get(
                    "task_instructions",
                    "Produce a local landing context packet without external network calls.",
                )
            ),
            use_case=str(job.inputs.get("use_case", ContextUseCase.CODEX_BRANCH_HARDENING.value)),
            changed_files_only=bool(job.inputs.get("changed_files_only", False)),
            deterministic=True,
        )
        return WorkerRunResult(
            succeeded=True,
            quarantined=False,
            exit_code=0,
            artifact_paths=(result.path,),
            metadata={
                "artifact_type": ArtifactType.CONTEXT_PACKET.value,
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "skipped_paths": list(result.skipped_paths),
                "summary_mode": result.summary_mode,
                "physical_proof": False,
            },
        )


class ArtifactReviewWorker(BaseWorker):
    name = "ArtifactReviewWorker"
    capabilities = frozenset({"artifact_collection"})
    safety_boundary = "durable_human_review_gate_no_final_claim_without_approval"
    human_review_required = True

    async def run(self, job: Job, context: BuiltinWorkerContext) -> WorkerRunResult:  # type: ignore[override]
        await super().preflight(job, context)  # type: ignore[arg-type]
        artifact_id = _required_text(job.inputs, "artifact_id")
        decision = str(job.inputs.get("decision", "pending")).strip().lower()
        if decision not in {"pending", "approved", "rejected"}:
            raise BuiltinWorkerError("artifact review decision must be pending, approved, or rejected")
        reason = str(job.inputs.get("reason", "operator review requested"))
        reviewer = str(job.inputs.get("reviewer", "operator"))
        artifact = context.sqlite_artifact_store.get_artifact(artifact_id)
        if artifact is None:
            raise BuiltinWorkerError(f"artifact not found for review: {artifact_id}")
        reviews = context.human_review_gate.list_reviews(job_id=artifact.job_id, artifact_id=artifact_id)
        review = reviews[0] if reviews else context.human_review_gate.request_review(
            job_id=artifact.job_id,
            artifact_id=artifact_id,
            reason=reason,
        )
        if decision == "pending":
            context.sqlite_artifact_store.review_artifact(artifact_id, review_status=ReviewStatus.NEEDS_REVIEW)
        elif decision == "approved":
            if review.decision == "pending":
                context.human_review_gate.approve_review(review_id=review.review_id, reviewer=reviewer, reason=reason)
            context.sqlite_artifact_store.review_artifact(artifact_id, review_status=ReviewStatus.APPROVED)
        else:
            if review.decision == "pending":
                context.human_review_gate.reject_review(review_id=review.review_id, reviewer=reviewer, reason=reason)
            context.sqlite_artifact_store.review_artifact(artifact_id, review_status=ReviewStatus.REJECTED)
        updated_reviews = context.human_review_gate.list_reviews(job_id=artifact.job_id, artifact_id=artifact_id)
        final_claim_allowed = any(item.decision == "approved" for item in updated_reviews)
        report_path = _write_json_artifact(
            context.artifact_root,
            "artifact_reviews",
            f"{job.id}.json",
            {
                "job_id": job.id,
                "worker": self.name,
                "artifact_id": artifact_id,
                "decision": decision,
                "review_ids": [item.review_id for item in updated_reviews],
                "final_claim_allowed": final_claim_allowed,
            },
        )
        return WorkerRunResult(
            succeeded=decision != "rejected",
            quarantined=decision == "rejected",
            exit_code=0 if decision != "rejected" else 1,
            artifact_paths=(report_path,),
            metadata={
                "artifact_type": ArtifactType.MATERIALIZATION_SUMMARY.value,
                "decision": decision,
                "final_claim_allowed": final_claim_allowed,
                "physical_proof": False,
                "requires_human_review": decision == "pending",
            },
        )


class Hfx008MaterializationDryRunWorker(BaseWorker):
    name = "Hfx008MaterializationDryRunWorker"
    capabilities = frozenset({"artifact_collection", "houdini_topology_audit", "houdini_single_frame_proof"})
    safety_boundary = "hfx_008_dry_run_no_dcc_no_physical_proof"
    human_review_required = True

    async def run(self, job: Job, context: BuiltinWorkerContext) -> WorkerRunResult:  # type: ignore[override]
        await super().preflight(job, context)  # type: ignore[arg-type]
        stage = str(job.inputs.get("stage", "materialization_summary")).strip().lower()
        if stage not in {"topology_audit", "single_frame_proof", "human_review_decision", "materialization_summary"}:
            raise BuiltinWorkerError(f"unsupported HFX_008 dry-run stage: {stage}")
        resource_package = Path(str(job.inputs.get("resource_package_path", context.runtime_root / "missing_hfx_008_resources")))
        plan, validation = hfx_008_dry_run_plan(
            context=context,
            stage=stage,
            resource_package_path=resource_package,
        )
        decision = decide_materialization(plan, validation=validation, human_review_approved=False)
        record_materialization_decision(context.database, plan=plan, decision=decision)
        report_path = _write_json_artifact(
            context.artifact_root,
            "hfx_008",
            f"{stage}_{job.id}.json",
            {
                "asset": "HFX_008",
                "job_id": job.id,
                "stage": stage,
                "dry_run": True,
                "houdini_launched": False,
                "dcc_launched": False,
                "physical_proof_created": False,
                "final_claim_allowed": False,
                "materialization_decision": decision.to_dict(),
                "operator_next_step_command": hfx_008_real_run_commands(context.repo_root)[0],
            },
        )
        requires_review = True
        return WorkerRunResult(
            succeeded=False,
            quarantined=False,
            exit_code=0,
            artifact_paths=(report_path,),
            metadata={
                "artifact_type": ArtifactType.MATERIALIZATION_SUMMARY.value,
                "asset": "HFX_008",
                "stage": stage,
                "dry_run": True,
                "physical_proof": False,
                "final_claim_allowed": False,
                "requires_human_review": requires_review,
                "blocked_reasons": list(decision.reasons),
                "status": decision.status,
            },
        )


def build_builtin_worker_registry() -> WorkerRegistry:
    registry = WorkerRegistry()
    register_builtin_workers(registry)
    return registry


def register_builtin_workers(registry: WorkerRegistry) -> WorkerRegistry:
    for job_type, worker in {
        "git_status": GitStatusWorker(),
        "context_pack": ContextPackWorker(),
        "artifact_review": ArtifactReviewWorker(),
        "hfx_008_materialization_dry_run": Hfx008MaterializationDryRunWorker(),
    }.items():
        registry.register(job_type, worker)
    return registry


def hfx_008_dry_run_plan(
    *,
    context: BuiltinWorkerContext,
    stage: str,
    resource_package_path: Path,
) -> tuple[MaterializationPlan, ValidationResult]:
    target_map = {
        "topology_audit": ("hfx_008_topology_audit_json", "HFX_008 topology audit JSON", "audit_json"),
        "single_frame_proof": ("hfx_008_single_frame_proof", "HFX_008 single-frame proof artifact", "hfx_proof_result"),
        "human_review_decision": ("hfx_008_human_review_decision", "HFX_008 human review decision", "materialization_summary"),
        "materialization_summary": ("hfx_008_materialization_summary", "HFX_008 materialization summary", "materialization_summary"),
    }
    target_id, target_name, artifact_type = target_map[stage]
    target = TargetArtifact(
        artifact_id=target_id,
        name=target_name,
        artifact_type=artifact_type,
        local_path=str(context.artifact_root / "hfx_008" / f"{stage}_target_dry_run.json"),
        human_review_required=stage != "topology_audit",
        classification="dry_run",
    )
    upstream = UpstreamInput(
        name="hfx_008_resource_package",
        local_path=str(resource_package_path),
        required=True,
        metadata={"asset": "HFX_008", "dry_run": True},
    )
    validation = ValidationResult(
        passed=stage == "topology_audit" and resource_package_path.exists(),
        resource_missing=not resource_package_path.exists(),
        visual_proof_missing=stage in {"single_frame_proof", "human_review_decision", "materialization_summary"},
        message="dry-run blocks final claim until real resource package, visual proof, and human review exist",
    )
    plan = MaterializationPlan(
        plan_id=f"hfx_008_{stage}_dry_run_v1",
        target=target,
        upstream_inputs=(upstream,),
        gates=("dry_run_only", "human_review_required", "no_final_claim"),
    )
    return plan, validation


def record_materialization_decision(
    database: OSDatabase,
    *,
    plan: MaterializationPlan,
    decision: MaterializationDecision,
) -> str:
    materialization_id = f"mat_{stable_content_hash({'plan_id': plan.plan_id, 'target': plan.target.artifact_id})[:24]}"
    payload = {
        "final_claim_allowed": False,
        "freshness_hash": decision.freshness_hash,
        "human_review_required": decision.human_review_required,
        "materialization_id": materialization_id,
        "status": decision.status,
        "target_artifact_id": decision.target_artifact_id,
        "target_name": plan.target.name,
        "upstream_inputs": [asdict(item) for item in plan.upstream_inputs],
        "validation": decision.validation.to_dict(),
    }
    validate_no_secret_like(payload)
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO materializations(
                materialization_id,
                target_artifact_id,
                target_name,
                upstream_inputs_json,
                status,
                freshness_hash,
                validation_json,
                human_review_required,
                final_claim_allowed,
                content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(materialization_id) DO UPDATE SET
                target_artifact_id = excluded.target_artifact_id,
                target_name = excluded.target_name,
                upstream_inputs_json = excluded.upstream_inputs_json,
                status = excluded.status,
                freshness_hash = excluded.freshness_hash,
                validation_json = excluded.validation_json,
                human_review_required = excluded.human_review_required,
                final_claim_allowed = excluded.final_claim_allowed,
                content_hash = excluded.content_hash
            """,
            (
                materialization_id,
                decision.target_artifact_id,
                plan.target.name,
                json.dumps(payload["upstream_inputs"], sort_keys=True, separators=(",", ":")),
                decision.status,
                decision.freshness_hash,
                json.dumps(decision.validation.to_dict(), sort_keys=True, separators=(",", ":")),
                int(decision.human_review_required),
                0,
                stable_content_hash(payload),
            ),
        )
    return materialization_id


def hfx_008_real_run_commands(repo_root: Path) -> list[str]:
    _ = repo_root
    return [
        "python3 -m kernel.vfx.hfx_topology_auditor --repo-root . --asset HFX_008 --write-audit",
        "hython kernel/vfx/hfx_single_frame_prover.py --asset HFX_008 --operator-run",
        "python3 tools/generate_sovereign_os_landing_readiness_report.py",
    ]


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuiltinWorkerError(f"{key} is required")
    return value.strip()


def _write_json_artifact(artifact_root: Path, subdir: str, filename: str, payload: dict[str, Any]) -> Path:
    validate_no_secret_like(payload)
    directory = (artifact_root / subdir).resolve()
    root = artifact_root.resolve()
    if not directory.is_relative_to(root):
        raise BuiltinWorkerError(f"artifact directory escapes artifact root: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    path = (directory / filename).resolve()
    if not path.is_relative_to(root):
        raise BuiltinWorkerError(f"artifact path escapes artifact root: {path}")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path
