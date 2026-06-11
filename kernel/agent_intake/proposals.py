"""Write external-agent requests as bounded SEOS proposal artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import json

from kernel.agent_intake.boundary import evaluate_agent_request
from kernel.knowledge.object_model import digest_payload, now_utc, safe_id
from kernel.security.secret_scanner import CoreSecretScanner

__all__ = ["write_agent_proposal"]


def write_agent_proposal(workspace: str | Path, request: Mapping[str, Any], *, source: str = "external_agent") -> dict[str, object]:
    """Write a proposal artifact if the request passes the agent boundary.

    The artifact is intentionally separate from `.seos/tasks`, `.seos/receipts`,
    and execution-plane permit stores. A human operator must still create or
    update a SEOS task through normal intake and approval gates.
    """

    workspace_root = Path(workspace).resolve()
    seos_root = workspace_root / ".seos"
    if not (seos_root / "workspace.json").exists():
        return {"ok": False, "error": "workspace_not_initialized", "workspace": workspace_root.as_posix()}

    request_text = json.dumps(dict(request), ensure_ascii=False, sort_keys=True)
    scan = CoreSecretScanner().scan_text(request_text, path="agent_intake_request")
    if not scan.clean:
        return {
            "ok": False,
            "error": "agent_request_failed_safety_scan",
            "finding_kinds": sorted({finding.kind for finding in scan.findings}),
        }

    decision = evaluate_agent_request(request)
    if not decision.get("accepted"):
        return {"ok": False, "decision": decision, "error": "agent_request_rejected"}

    request_id = safe_id(decision.get("request_id"), fallback="agent_request")
    proposal = {
        "schema": "seos_agent_proposal_v1",
        "created_at": now_utc(),
        "source": source,
        "request_id": request_id,
        "intent": decision.get("intent"),
        "authority": "proposal",
        "request_digest": digest_payload(dict(request)),
        "request_summary": _request_summary(request),
        "decision": decision,
        "task_created": False,
        "approval_created": False,
        "permit_created": False,
        "execution_performed": False,
        "execution_authority_granted": False,
        "next_required_operator_action": "review_then_create_or_update_seos_task",
    }
    proposal["digest"] = digest_payload(proposal)
    output = seos_root / "agent_intake" / "proposals" / f"{request_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        return {"ok": False, "error": "agent_proposal_already_exists", "path": output.as_posix()}
    output.write_text(json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "proposal": proposal, "path": output.as_posix()}


def _request_summary(request: Mapping[str, Any]) -> dict[str, object]:
    return {
        "title": str(request.get("title") or request.get("name") or request.get("intent") or "agent proposal")[:160],
        "objective": str(request.get("objective") or request.get("summary") or request.get("description") or "")[:400],
        "target_task_id": str(request.get("task_id") or request.get("target_task_id") or "")[:160],
    }
