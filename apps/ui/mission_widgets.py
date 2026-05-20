"""Mission projection helpers for the unified Sovereign Console workspace."""

from __future__ import annotations

from apps.ui.read_models import RuntimeSnapshot

CURRENT_MISSION_ID = "HFX_008"
CURRENT_MISSION_NAME = "HFX_008 Energy Shockwave"
CURRENT_MISSION_TYPE = "HFX Landing Mission"

MISSION_FIELD_KEYS: tuple[str, ...] = (
    "mission_id",
    "mission_name",
    "mission_type",
    "status",
    "final_claim_allowed",
    "blocked_reason",
    "next_action",
    "latest_artifact",
    "latest_run",
    "required_resource_state",
    "human_review_state",
)

HFX_008_COMPACT_CHAIN: tuple[str, ...] = (
    "Topology Audit",
    "Proof Artifact",
    "Validation",
    "Human Review",
    "Summary",
    "Claim Gate",
)


def mission_projection(snapshot: RuntimeSnapshot) -> dict[str, object]:
    """Build the mission card from immutable GUI read projections only."""

    latest_run = snapshot.latest_jobs[0] if snapshot.latest_jobs else None
    latest_artifact = snapshot.latest_artifacts[0] if snapshot.latest_artifacts else None
    pending_reviews = sum(1 for artifact in snapshot.latest_artifacts if artifact.review_status in {"needs_review", "new"})
    final_claim_allowed = bool(latest_run.final_claim_allowed) if latest_run else False
    blocked_reason = "Human review and proof artifact validation required"
    if snapshot.quarantined_jobs:
        blocked_reason = "Quarantined run requires review"
    if not snapshot.runtime_available or not snapshot.database_available:
        blocked_reason = "Runtime projection unavailable"
    return {
        "mission_id": CURRENT_MISSION_ID,
        "mission_name": CURRENT_MISSION_NAME,
        "mission_type": CURRENT_MISSION_TYPE,
        "status": latest_run.status if latest_run else "Read-only Projection",
        "final_claim_allowed": final_claim_allowed,
        "blocked_reason": blocked_reason,
        "next_action": snapshot.next_required_action,
        "latest_artifact": latest_artifact.artifact_id if latest_artifact else "--",
        "latest_run": latest_run.job_id if latest_run else "--",
        "required_resource_state": "Materialization Required",
        "human_review_state": f"{pending_reviews} pending",
    }
