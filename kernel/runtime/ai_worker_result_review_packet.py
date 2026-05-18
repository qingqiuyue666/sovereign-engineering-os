"""Deterministic packet for reviewing AI worker final report claims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    prepare_material,
    render_markdown,
    require_list_fields,
    require_string_fields,
    require_valid_choice,
)

__all__ = [
    "AI_WORKER_REQUIRED_FINAL_REPORT_SECTIONS",
    "AIWorkerResultReviewPacket",
    "build_ai_worker_result_review_packet",
    "render_ai_worker_result_review_packet_markdown",
]

_POLICY_VERSION = "ai-worker-result-review-packet-v1"
_CODE_VERSION = "0.1.0"
_REVIEW_DECISIONS = ("structurally_complete", "structurally_incomplete", "requires_human_verification", "reject")

AI_WORKER_REQUIRED_FINAL_REPORT_SECTIONS = (
    "FINAL_COMMIT",
    "BRANCH",
    "FILES_CHANGED",
    "TESTS_ADDED",
    "COMMANDS_RUN",
    "EXACT_RESULTS",
    "BOUNDARIES_PRESERVED",
    "DETERMINISM_AUDIT",
    "FAILURE_PATH_AUDIT",
    "ROOT_INTEGRITY_AUDIT",
    "REMAINING_RISKS",
    "ROLLBACK_PLAN",
)

_STRING_FIELDS = (
    "packet_id",
    "worker_name",
    "claimed_branch",
    "claimed_commit",
    "review_decision",
    "policy_version",
    "code_version",
)
_LIST_FIELDS = (
    "claimed_files_changed",
    "claimed_tests_run",
    "claimed_results",
    "claimed_boundaries_preserved",
    "claimed_risks",
    "claimed_rollback_plan",
    "missing_sections",
    "contradiction_findings",
    "required_human_checks",
)
_ALLOW_EMPTY_LISTS = (
    "claimed_risks",
    "missing_sections",
    "contradiction_findings",
    "required_human_checks",
)


@dataclass(frozen=True)
class AIWorkerResultReviewPacket:
    """Repository-ready structural review packet for AI worker final reports."""

    packet_id: str
    worker_name: str
    claimed_branch: str
    claimed_commit: str
    claimed_files_changed: tuple[object, ...]
    claimed_tests_run: tuple[object, ...]
    claimed_results: tuple[object, ...]
    claimed_boundaries_preserved: tuple[object, ...]
    claimed_risks: tuple[object, ...]
    claimed_rollback_plan: tuple[object, ...]
    missing_sections: tuple[object, ...]
    contradiction_findings: tuple[object, ...]
    review_decision: str
    required_human_checks: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "claimed_boundaries_preserved": list(self.claimed_boundaries_preserved),
            "claimed_branch": self.claimed_branch,
            "claimed_commit": self.claimed_commit,
            "claimed_files_changed": list(self.claimed_files_changed),
            "claimed_results": list(self.claimed_results),
            "claimed_risks": list(self.claimed_risks),
            "claimed_rollback_plan": list(self.claimed_rollback_plan),
            "claimed_tests_run": list(self.claimed_tests_run),
            "code_version": self.code_version,
            "contradiction_findings": list(self.contradiction_findings),
            "missing_sections": list(self.missing_sections),
            "packet_id": self.packet_id,
            "policy_version": self.policy_version,
            "required_human_checks": list(self.required_human_checks),
            "review_decision": self.review_decision,
            "worker_name": self.worker_name,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_ai_worker_result_review_packet(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> AIWorkerResultReviewPacket:
    """Build a deterministic structure-only review packet for worker claims."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="ai_worker_result_review_packet_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS, allow_empty=_ALLOW_EMPTY_LISTS)
    require_valid_choice(normalized["review_decision"], field="review_decision", allowed=_REVIEW_DECISIONS)
    if normalized["review_decision"] == "structurally_complete":
        if normalized["missing_sections"]:
            raise ValueError("missing_sections_block_structurally_complete")
        if normalized["contradiction_findings"]:
            raise ValueError("contradictions_block_structurally_complete")

    packet = AIWorkerResultReviewPacket(
        packet_id=normalized["packet_id"],
        worker_name=normalized["worker_name"],
        claimed_branch=normalized["claimed_branch"],
        claimed_commit=normalized["claimed_commit"],
        claimed_files_changed=tuple(normalized["claimed_files_changed"]),
        claimed_tests_run=tuple(normalized["claimed_tests_run"]),
        claimed_results=tuple(normalized["claimed_results"]),
        claimed_boundaries_preserved=tuple(normalized["claimed_boundaries_preserved"]),
        claimed_risks=tuple(normalized["claimed_risks"]),
        claimed_rollback_plan=tuple(normalized["claimed_rollback_plan"]),
        missing_sections=tuple(normalized["missing_sections"]),
        contradiction_findings=tuple(normalized["contradiction_findings"]),
        review_decision=normalized["review_decision"],
        required_human_checks=tuple(normalized["required_human_checks"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(packet)


def render_ai_worker_result_review_packet_markdown(packet: AIWorkerResultReviewPacket) -> str:
    """Render AI worker result review packet Markdown deterministically."""

    if not isinstance(packet, AIWorkerResultReviewPacket):
        raise ValueError("packet_must_be_ai_worker_result_review_packet")
    material = packet.deterministic_material()
    return render_markdown(
        "AI Worker Result Review Packet",
        metadata_rows=(
            ("packet_id", packet.packet_id),
            ("worker_name", packet.worker_name),
            ("claimed_branch", packet.claimed_branch),
            ("claimed_commit", packet.claimed_commit),
            ("policy_version", packet.policy_version),
            ("code_version", packet.code_version),
            ("content_hash", packet.content_hash),
            ("observed_at", packet.observed_at),
        ),
        sections=(
            ("Worker Result Summary", {"review_decision": packet.review_decision}),
            ("Claimed Branch / Commit", {"branch": packet.claimed_branch, "commit": packet.claimed_commit}),
            ("Claimed Files Changed", material["claimed_files_changed"]),
            ("Claimed Tests Run", material["claimed_tests_run"]),
            ("Claimed Results", material["claimed_results"]),
            ("Boundary Claims", material["claimed_boundaries_preserved"]),
            ("Missing Sections", material["missing_sections"]),
            ("Contradiction Findings", material["contradiction_findings"]),
            ("Review Decision", packet.review_decision),
            ("Required Human Checks", material["required_human_checks"]),
            ("Claimed Rollback Plan", material["claimed_rollback_plan"]),
        ),
    )


def _with_hash(packet: AIWorkerResultReviewPacket) -> AIWorkerResultReviewPacket:
    return AIWorkerResultReviewPacket(
        packet_id=packet.packet_id,
        worker_name=packet.worker_name,
        claimed_branch=packet.claimed_branch,
        claimed_commit=packet.claimed_commit,
        claimed_files_changed=packet.claimed_files_changed,
        claimed_tests_run=packet.claimed_tests_run,
        claimed_results=packet.claimed_results,
        claimed_boundaries_preserved=packet.claimed_boundaries_preserved,
        claimed_risks=packet.claimed_risks,
        claimed_rollback_plan=packet.claimed_rollback_plan,
        missing_sections=packet.missing_sections,
        contradiction_findings=packet.contradiction_findings,
        review_decision=packet.review_decision,
        required_human_checks=packet.required_human_checks,
        policy_version=packet.policy_version,
        code_version=packet.code_version,
        content_hash=compute_content_hash(packet.deterministic_material()),
        observed_at=packet.observed_at,
    )
