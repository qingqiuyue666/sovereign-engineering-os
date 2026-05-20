"""Asset-centric materialization primitives for the OS engine v3 core."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from kernel.os_engine.database import stable_content_hash, validate_no_secret_like
from kernel.os_engine.sqlite_artifact_store import sha256_file


class MaterializationError(RuntimeError):
    """Raised when a materialization plan or decision is unsafe."""


class MaterializationStatus(StrEnum):
    MATERIALIZATION_REQUIRED = "materialization_required"
    MATERIALIZED_VALID = "materialized_valid"
    MATERIALIZED_STALE = "materialized_stale"
    BLOCKED_MISSING_UPSTREAM = "blocked_missing_upstream"
    BLOCKED_VALIDATION_FAILED = "blocked_validation_failed"
    BLOCKED_HUMAN_REVIEW_REQUIRED = "blocked_human_review_required"
    BLOCKED_RESOURCE_MISSING = "blocked_resource_missing"
    BLOCKED_VISUAL_PROOF_MISSING = "blocked_visual_proof_missing"
    BLOCKED_PLACEHOLDER_GUIDE = "blocked_placeholder_guide"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class TargetArtifact:
    artifact_id: str
    name: str
    artifact_type: str
    local_path: str
    expected_sha256: str | None = None
    human_review_required: bool = False
    classification: str = "asset"

    def __post_init__(self) -> None:
        _validate_structured_payload(asdict(self))
        if not self.artifact_id or not self.name or not self.artifact_type or not self.local_path:
            raise MaterializationError("target artifact requires id, name, type, and local_path")


@dataclass(frozen=True, slots=True)
class UpstreamInput:
    name: str
    local_path: str
    required: bool = True
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_structured_payload(asdict(self))
        if not self.name or not self.local_path:
            raise MaterializationError("upstream input requires name and local_path")


@dataclass(frozen=True, slots=True)
class MaterializationPlan:
    plan_id: str
    target: TargetArtifact
    upstream_inputs: tuple[UpstreamInput, ...]
    gates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_structured_payload(asdict(self))
        if not self.plan_id:
            raise MaterializationError("plan_id is required")
        if not self.upstream_inputs:
            raise MaterializationError("materialization plans require upstream inputs")

    @property
    def plan_hash(self) -> str:
        return stable_content_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "gates": tuple(sorted(self.gates)),
            "plan_id": self.plan_id,
            "target": asdict(self.target),
            "upstream_inputs": tuple(asdict(item) for item in self.upstream_inputs),
        }


@dataclass(frozen=True, slots=True)
class FreshnessCheck:
    freshness_hash: str
    previous_freshness_hash: str | None
    stale: bool
    missing_upstreams: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    checksum_valid: bool = True
    placeholder_guide: bool = False
    resource_missing: bool = False
    visual_proof_missing: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))


@dataclass(frozen=True, slots=True)
class MaterializationDecision:
    plan_id: str
    target_artifact_id: str
    status: str
    materialization_required: bool
    freshness_hash: str
    validation: ValidationResult
    human_review_required: bool
    human_review_approved: bool
    final_claim_allowed: bool
    reasons: tuple[str, ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def compute_freshness_hash(upstream_inputs: tuple[UpstreamInput, ...] | list[UpstreamInput]) -> str:
    payload = []
    for upstream in sorted(upstream_inputs, key=lambda item: item.name):
        path = Path(upstream.local_path).expanduser()
        exists = path.exists()
        sha = upstream.sha256
        if exists and path.is_file():
            sha = sha256_file(path)
        payload.append(
            {
                "exists": exists,
                "metadata": upstream.metadata,
                "name": upstream.name,
                "required": upstream.required,
                "sha256": sha or "",
            }
        )
    return stable_content_hash(payload)


def check_freshness(
    upstream_inputs: tuple[UpstreamInput, ...] | list[UpstreamInput],
    *,
    previous_freshness_hash: str | None = None,
) -> FreshnessCheck:
    missing = tuple(
        sorted(
            upstream.name
            for upstream in upstream_inputs
            if upstream.required and not Path(upstream.local_path).expanduser().exists()
        )
    )
    freshness_hash = compute_freshness_hash(upstream_inputs)
    return FreshnessCheck(
        freshness_hash=freshness_hash,
        previous_freshness_hash=previous_freshness_hash,
        stale=previous_freshness_hash is not None and previous_freshness_hash != freshness_hash,
        missing_upstreams=missing,
    )


def decide_materialization(
    plan: MaterializationPlan,
    *,
    previous_freshness_hash: str | None = None,
    validation: ValidationResult | None = None,
    human_review_approved: bool = False,
    quarantined: bool = False,
) -> MaterializationDecision:
    validation = validation or ValidationResult(passed=True)
    freshness = check_freshness(plan.upstream_inputs, previous_freshness_hash=previous_freshness_hash)
    target_path = Path(plan.target.local_path).expanduser()
    target_exists = target_path.is_file()
    checksum_valid = validation.checksum_valid
    reasons: list[str] = []

    if target_exists and plan.target.expected_sha256:
        checksum_valid = sha256_file(target_path) == plan.target.expected_sha256
        if not checksum_valid:
            reasons.append("target checksum mismatch")
    if quarantined:
        status = MaterializationStatus.QUARANTINED
        reasons.append("target artifact is quarantined")
    elif freshness.missing_upstreams:
        status = MaterializationStatus.BLOCKED_MISSING_UPSTREAM
        reasons.extend(f"missing upstream: {name}" for name in freshness.missing_upstreams)
    elif validation.placeholder_guide or plan.target.classification.lower() in {"placeholder", "guide", "placeholder guide"}:
        status = MaterializationStatus.BLOCKED_PLACEHOLDER_GUIDE
        reasons.append("placeholder/guide classification blocks final claim")
    elif validation.resource_missing:
        status = MaterializationStatus.BLOCKED_RESOURCE_MISSING
        reasons.append("required resource package is missing")
    elif validation.visual_proof_missing:
        status = MaterializationStatus.BLOCKED_VISUAL_PROOF_MISSING
        reasons.append("visual proof artifact is missing")
    elif not validation.passed or not checksum_valid:
        status = MaterializationStatus.BLOCKED_VALIDATION_FAILED
        reasons.append(validation.message or "validation failed")
    elif not target_exists:
        status = MaterializationStatus.MATERIALIZATION_REQUIRED
        reasons.append("target artifact is missing")
    elif freshness.stale:
        status = MaterializationStatus.MATERIALIZED_STALE
        reasons.append("upstream freshness hash changed")
    elif plan.target.human_review_required and not human_review_approved:
        status = MaterializationStatus.BLOCKED_HUMAN_REVIEW_REQUIRED
        reasons.append("human review approval is required")
    else:
        status = MaterializationStatus.MATERIALIZED_VALID
        reasons.append("target artifact is current and valid")

    final_claim_allowed = (
        status == MaterializationStatus.MATERIALIZED_VALID
        and target_exists
        and checksum_valid
        and validation.passed
        and (not plan.target.human_review_required or human_review_approved)
        and not validation.placeholder_guide
        and not validation.resource_missing
        and not validation.visual_proof_missing
        and plan.target.classification.lower() not in {"placeholder", "guide", "placeholder guide"}
    )
    decision_payload = {
        "final_claim_allowed": final_claim_allowed,
        "freshness_hash": freshness.freshness_hash,
        "human_review_approved": human_review_approved,
        "human_review_required": plan.target.human_review_required,
        "materialization_required": status
        in {MaterializationStatus.MATERIALIZATION_REQUIRED, MaterializationStatus.MATERIALIZED_STALE},
        "plan_id": plan.plan_id,
        "reasons": tuple(sorted(reasons)),
        "status": status.value,
        "target_artifact_id": plan.target.artifact_id,
        "validation": validation.to_dict(),
    }
    return MaterializationDecision(
        plan_id=plan.plan_id,
        target_artifact_id=plan.target.artifact_id,
        status=status.value,
        materialization_required=status
        in {MaterializationStatus.MATERIALIZATION_REQUIRED, MaterializationStatus.MATERIALIZED_STALE},
        freshness_hash=freshness.freshness_hash,
        validation=validation,
        human_review_required=plan.target.human_review_required,
        human_review_approved=human_review_approved,
        final_claim_allowed=final_claim_allowed,
        reasons=tuple(sorted(reasons)),
        content_hash=stable_content_hash(decision_payload),
    )


def _validate_structured_payload(payload: dict[str, Any]) -> None:
    validate_no_secret_like(payload)
