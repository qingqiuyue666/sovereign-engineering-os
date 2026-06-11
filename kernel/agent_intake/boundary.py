"""Authority boundary evaluator for external AI and agent requests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kernel.knowledge.object_model import digest_payload, now_utc, safe_id

__all__ = ["AGENT_INTAKE_ALLOWED_INTENTS", "AGENT_INTAKE_FORBIDDEN_INTENTS", "AgentBoundaryDecision", "evaluate_agent_request"]

AGENT_INTAKE_ALLOWED_INTENTS = frozenset(
    {
        "proposal",
        "task_draft",
        "patch_proposal",
        "failure_explanation",
        "test_plan",
        "evidence_request",
        "repair_job_draft",
        "knowledge_query",
        "readonly_status",
    }
)

AGENT_INTAKE_FORBIDDEN_INTENTS = frozenset(
    {
        "approve",
        "reject_as_authority",
        "create_permit",
        "execute",
        "run_local_command",
        "read_secret",
        "write_secret",
        "desktop_control",
        "browser_control",
        "rpa",
        "mutate_authority_store",
        "bypass_human_review",
    }
)

_FORBIDDEN_KEYS = frozenset(
    {
        "approval_created",
        "permit_created",
        "execution_authority_granted",
        "execute_now",
        "run_command",
        "secret",
        "token",
        "password",
        "api_key",
    }
)


@dataclass(frozen=True)
class AgentBoundaryDecision:
    """Decision envelope for an external agent request."""

    accepted: bool
    terminal_status: str
    intent: str
    request_id: str
    reasons: tuple[str, ...]
    next_required_action: str

    def as_dict(self) -> dict[str, object]:
        payload = {
            "schema": "seos_agent_boundary_decision_v1",
            "created_at": now_utc(),
            "accepted": self.accepted,
            "terminal_status": self.terminal_status,
            "intent": self.intent,
            "request_id": self.request_id,
            "reasons": list(self.reasons),
            "next_required_action": self.next_required_action,
            "approval_created": False,
            "permit_created": False,
            "execution_performed": False,
            "execution_authority_granted": False,
        }
        payload["digest"] = digest_payload(payload)
        return payload


def evaluate_agent_request(request: Mapping[str, Any]) -> dict[str, object]:
    """Classify an agent request without creating authority.

    Accepted requests are admitted only as proposal/read-only intents. Rejected
    requests explain which boundary failed. This function is pure and performs no
    filesystem mutation, network access, process execution, approval, or permit
    creation.
    """

    intent = safe_id(request.get("intent") or request.get("type") or "proposal", fallback="proposal")
    request_id = safe_id(request.get("request_id") or request.get("id") or digest_payload(dict(request))[-16:], fallback="agent_request")
    reasons: list[str] = []

    if intent in AGENT_INTAKE_FORBIDDEN_INTENTS:
        reasons.append(f"forbidden_intent:{intent}")
    if intent not in AGENT_INTAKE_ALLOWED_INTENTS:
        reasons.append(f"unsupported_intent:{intent}")
    _scan_for_forbidden_keys(request, reasons, prefix="request")
    if bool(request.get("execution_authority_granted", False)):
        reasons.append("request_claims_execution_authority")
    if bool(request.get("approval_created", False)):
        reasons.append("request_claims_approval_created")
    if bool(request.get("permit_created", False)):
        reasons.append("request_claims_permit_created")

    accepted = not reasons
    decision = AgentBoundaryDecision(
        accepted=accepted,
        terminal_status="ACCEPTED_AS_PROPOSAL" if accepted else "REJECTED_BY_AGENT_BOUNDARY",
        intent=intent,
        request_id=request_id,
        reasons=tuple(reasons),
        next_required_action="write_proposal_then_normal_seos_task_intake" if accepted else "remove_forbidden_authority_claims",
    )
    return decision.as_dict()


def _scan_for_forbidden_keys(value: object, reasons: list[str], *, prefix: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in _FORBIDDEN_KEYS:
                reasons.append(f"forbidden_key:{prefix}.{key_text}")
            _scan_for_forbidden_keys(item, reasons, prefix=f"{prefix}.{key_text}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_forbidden_keys(item, reasons, prefix=f"{prefix}[{index}]")
