"""MCP-inspired manifest for the SEOS agent-intake boundary.

SEOS does not need to depend on the MCP SDK for this manifest. The goal is to
absorb the useful protocol distinction between read-only resources and
side-effecting tools while preserving SEOS authority boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path

from kernel.knowledge.object_model import digest_payload, now_utc

__all__ = ["build_agent_intake_manifest", "write_agent_intake_manifest"]


def build_agent_intake_manifest() -> dict[str, object]:
    resources = [
        {
            "uri": "seos://status/public",
            "name": "SEOS public status summary",
            "read_only": True,
            "side_effects": False,
            "authority": "mirror",
        },
        {
            "uri": "seos://knowledge/graph/public",
            "name": "SEOS public knowledge graph",
            "read_only": True,
            "side_effects": False,
            "authority": "mirror",
        },
        {
            "uri": "seos://evidence/trace/{task_id}",
            "name": "SEOS evidence trace summary",
            "read_only": True,
            "side_effects": False,
            "authority": "mirror",
        },
    ]
    tools = [
        {
            "name": "seos_agent_write_proposal",
            "intent": "proposal",
            "side_effects": "writes proposal artifact only",
            "authority": "proposal",
            "creates_task": False,
            "creates_approval": False,
            "creates_permit": False,
            "executes_command": False,
            "requires_human_review_after_call": True,
        },
        {
            "name": "seos_agent_request_evidence",
            "intent": "evidence_request",
            "side_effects": "writes proposal artifact only",
            "authority": "proposal",
            "creates_task": False,
            "creates_approval": False,
            "creates_permit": False,
            "executes_command": False,
            "requires_human_review_after_call": True,
        },
        {
            "name": "seos_agent_patch_proposal",
            "intent": "patch_proposal",
            "side_effects": "writes proposal artifact only",
            "authority": "proposal",
            "creates_task": False,
            "creates_approval": False,
            "creates_permit": False,
            "executes_command": False,
            "requires_human_review_after_call": True,
        },
    ]
    forbidden = [
        "approve",
        "create_permit",
        "execute",
        "run_local_command",
        "read_secret",
        "desktop_control",
        "browser_control",
        "rpa",
        "mutate_authority_store",
    ]
    manifest = {
        "schema": "seos_agent_intake_mcp_manifest_v1",
        "created_at": now_utc(),
        "protocol_inspiration": "model_context_protocol_resource_tool_boundary",
        "dependency_required": False,
        "authority": "proposal_or_mirror_only",
        "execution_authority_granted": False,
        "resources": resources,
        "tools": tools,
        "forbidden_intents": forbidden,
        "notes": [
            "MCP resources map to SEOS read-only mirrors.",
            "MCP-like tools are limited to proposal artifacts.",
            "Any approval, permit, or execution must happen through normal SEOS gates.",
        ],
    }
    manifest["digest"] = digest_payload({"resources": resources, "tools": tools, "forbidden_intents": forbidden})
    return manifest


def write_agent_intake_manifest(output: str | Path) -> dict[str, object]:
    manifest = build_agent_intake_manifest()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "manifest": manifest, "path": output_path.as_posix()}
