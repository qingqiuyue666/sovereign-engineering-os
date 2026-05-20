"""HFX materialization plans expressed as OS engine v3 assets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kernel.os_engine.database import stable_content_hash
from kernel.os_engine.materialization import (
    MaterializationDecision,
    MaterializationPlan,
    TargetArtifact,
    UpstreamInput,
    ValidationResult,
    decide_materialization,
)

HFX_008_TARGET_NAMES = (
    "HFX_008_topology_audit_json",
    "HFX_008_single_frame_proof_artifact",
    "HFX_008_human_review_decision",
    "HFX_008_materialization_summary",
)

HFX_008_UPSTREAM_NAMES = (
    "HFX_008 HIP path",
    "hfx_topology_auditor.py",
    "hfx_single_frame_prover.py",
    "render_artifact_ledger.py",
    "Houdini/hython executable path metadata",
    "local proof workspace path metadata",
)

HFX_008_GATES = (
    "topology audit must pass before single-frame proof",
    "placeholder/guide classification blocks proof",
    "missing render node blocks proof",
    "missing resource package marks blocked_resource_missing when required",
    "missing visual frame marks blocked_visual_proof_missing",
    "human review required before final claim",
    "final_claim_allowed false by default",
)


@dataclass(frozen=True, slots=True)
class HFX008MaterializationPlan:
    plan_id: str
    target_artifacts: tuple[TargetArtifact, ...]
    upstream_inputs: tuple[UpstreamInput, ...]
    gates: tuple[str, ...]
    materialization_plans: tuple[MaterializationPlan, ...]
    plan_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def build_hfx_008_materialization_plan(
    *,
    repo_root: Path,
    hfx_008_hip_path: Path,
    proof_workspace: Path,
    hython_executable_metadata: str,
) -> HFX008MaterializationPlan:
    repo = repo_root.resolve(strict=False)
    workspace = proof_workspace.resolve(strict=False)
    upstreams = (
        UpstreamInput(name="HFX_008 HIP path", local_path=str(hfx_008_hip_path.resolve(strict=False))),
        UpstreamInput(name="hfx_topology_auditor.py", local_path=str(repo / "kernel" / "vfx" / "hfx_topology_auditor.py")),
        UpstreamInput(name="hfx_single_frame_prover.py", local_path=str(repo / "kernel" / "vfx" / "hfx_single_frame_prover.py")),
        UpstreamInput(name="render_artifact_ledger.py", local_path=str(repo / "kernel" / "vfx" / "render_artifact_ledger.py")),
        UpstreamInput(
            name="Houdini/hython executable path metadata",
            local_path=str(workspace / "hython_executable.metadata"),
            required=False,
            metadata={"metadata_value": hython_executable_metadata},
        ),
        UpstreamInput(
            name="local proof workspace path metadata",
            local_path=str(workspace),
            required=False,
            metadata={"workspace_path": str(workspace)},
        ),
    )
    targets = (
        TargetArtifact(
            artifact_id="HFX_008_topology_audit_json",
            name="HFX_008_topology_audit_json",
            artifact_type="audit_json",
            local_path=str(workspace / "HFX_008_topology_audit.json"),
        ),
        TargetArtifact(
            artifact_id="HFX_008_single_frame_proof_artifact",
            name="HFX_008_single_frame_proof_artifact",
            artifact_type="hfx_proof_result",
            local_path=str(workspace / "HFX_008_single_frame_proof.json"),
            human_review_required=True,
        ),
        TargetArtifact(
            artifact_id="HFX_008_human_review_decision",
            name="HFX_008_human_review_decision",
            artifact_type="materialization_summary",
            local_path=str(workspace / "HFX_008_human_review_decision.json"),
            human_review_required=True,
        ),
        TargetArtifact(
            artifact_id="HFX_008_materialization_summary",
            name="HFX_008_materialization_summary",
            artifact_type="materialization_summary",
            local_path=str(workspace / "HFX_008_materialization_summary.json"),
            human_review_required=True,
        ),
    )
    plans = tuple(
        MaterializationPlan(
            plan_id=f"hfx_008::{target.name}",
            target=target,
            upstream_inputs=upstreams,
            gates=HFX_008_GATES,
        )
        for target in targets
    )
    payload = {
        "gates": HFX_008_GATES,
        "plan_id": "HFX_008_materialization_plan_v1",
        "target_artifacts": tuple(asdict(target) for target in targets),
        "upstream_inputs": tuple(asdict(upstream) for upstream in upstreams),
    }
    return HFX008MaterializationPlan(
        plan_id="HFX_008_materialization_plan_v1",
        target_artifacts=targets,
        upstream_inputs=upstreams,
        gates=HFX_008_GATES,
        materialization_plans=plans,
        plan_hash=stable_content_hash(payload),
    )


def evaluate_hfx_008_materialization(
    plan: HFX008MaterializationPlan,
    *,
    topology_audit_passed: bool = True,
    classification: str = "asset",
    render_node_present: bool = True,
    resource_package_required: bool = False,
    resource_package_present: bool = True,
    visual_frame_present: bool = True,
    human_review_approved: bool = False,
    artifact_validation_passed: bool = True,
    previous_freshness_hash: str | None = None,
) -> MaterializationDecision:
    summary_plan = next(
        item for item in plan.materialization_plans if item.target.name == "HFX_008_materialization_summary"
    )
    validation = ValidationResult(
        passed=bool(topology_audit_passed and render_node_present and artifact_validation_passed),
        placeholder_guide=classification.lower() in {"placeholder", "guide", "placeholder guide"},
        resource_missing=bool(resource_package_required and not resource_package_present),
        visual_proof_missing=not visual_frame_present,
        message=_hfx_validation_message(
            topology_audit_passed=topology_audit_passed,
            render_node_present=render_node_present,
            artifact_validation_passed=artifact_validation_passed,
        ),
    )
    return decide_materialization(
        summary_plan,
        previous_freshness_hash=previous_freshness_hash,
        validation=validation,
        human_review_approved=human_review_approved,
    )


def _hfx_validation_message(
    *,
    topology_audit_passed: bool,
    render_node_present: bool,
    artifact_validation_passed: bool,
) -> str:
    if not topology_audit_passed:
        return "topology audit failed"
    if not render_node_present:
        return "render node missing"
    if not artifact_validation_passed:
        return "artifact validation failed"
    return "validation passed"
