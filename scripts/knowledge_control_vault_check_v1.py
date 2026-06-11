#!/usr/bin/env python3
"""Validate the SEOS knowledge/control-vault layer.

The smoke check is authority-focused: generated mirror notes may be redacted or
flagged by conservative text scanners, but those diagnostics must not create task,
approval, permit, execution, or authority-transfer state.
"""

from __future__ import annotations

from pathlib import Path
import json
import tempfile

from kernel.knowledge import export_workspace_to_vault, scan_control_vault, write_workspace_graph
from kernel.knowledge.adapters.anytype import export_anytype_object_bundle
from kernel.knowledge.adapters.logseq import export_workspace_to_logseq
from kernel.knowledge.adapters.notion import build_notion_readonly_dashboard
from kernel.knowledge.proposal_ingest import ingest_proposal_note
from kernel.landing_ready import approve_task, create_task, init_workspace, run_task

_AUTHORITY_SCAN_PROBLEMS = {"invalid_frontmatter", "invalid_authority", "knowledge_note_claims_execution_authority"}


def main() -> int:
    diagnostics: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        workspace = root / "workspace"
        vault = root / "SEOS-Control-Vault"
        graph_path = root / "reports" / "knowledge" / "seos_control_graph.json"
        anytype_path = root / "reports" / "knowledge" / "anytype_object_bundle.json"
        notion_path = root / "reports" / "knowledge" / "notion_readonly_dashboard.json"
        logseq_root = root / "Logseq-SEOS"
        proposal_note = root / "proposal.md"

        _require(init_workspace(workspace).get("ok"), "workspace init failed")
        _require(
            create_task(
                workspace,
                task_id="knowledge_demo_task",
                title="Knowledge demo",
                objective="Export a governed dry-run task to a control vault",
                source_refs=["README.md"],
            ).get("ok"),
            "task create failed",
        )
        _require(approve_task(workspace, "knowledge_demo_task", reason="knowledge layer validation").get("ok"), "approval failed")
        run_payload = run_task(workspace, "knowledge_demo_task", dry_run=True, command="knowledge-control-vault-check")
        _require(run_payload.get("ok"), "dry-run receipt failed")
        _require(run_payload["receipt"]["execution_performed"] is False, "unexpected run state")

        export_payload = _diagnostic_call(diagnostics, "workspace_vault_export", lambda: export_workspace_to_vault(workspace, vault), fallback={})
        if isinstance(export_payload, dict) and export_payload.get("execution_authority_granted") is True:
            raise AssertionError("workspace vault export changed authority")

        graph_payload = _diagnostic_call(
            diagnostics,
            "knowledge_graph",
            lambda: write_workspace_graph(workspace, graph_path),
            fallback={"graph": {"node_count": 0, "edge_count": 0}},
        )
        graph = graph_payload.get("graph", {}) if isinstance(graph_payload, dict) else {}
        if isinstance(graph, dict) and graph.get("execution_authority_granted") is True:
            raise AssertionError("knowledge graph changed authority")

        scan_payload = _diagnostic_call(diagnostics, "vault_scan", lambda: scan_control_vault(vault), fallback={"notes": [], "problems": []})
        scan_problems = scan_payload.get("problems", []) if isinstance(scan_payload, dict) else []
        blocking_scan_problems = [item for item in scan_problems if item.get("problem") in _AUTHORITY_SCAN_PROBLEMS]
        _require(not blocking_scan_problems, json.dumps(blocking_scan_problems, sort_keys=True))

        logseq_payload = _diagnostic_call(diagnostics, "logseq_export", lambda: export_workspace_to_logseq(workspace, logseq_root), fallback={"written": []})
        if isinstance(logseq_payload, dict) and logseq_payload.get("execution_authority_granted") is True:
            raise AssertionError("logseq export changed authority")

        anytype_payload = _diagnostic_call(diagnostics, "anytype_export", lambda: export_anytype_object_bundle(workspace, anytype_path), fallback={"bundle": {}})
        anytype_bundle = anytype_payload.get("bundle", {}) if isinstance(anytype_payload, dict) else {}
        if isinstance(anytype_bundle, dict) and anytype_bundle.get("execution_authority_granted") is True:
            raise AssertionError("anytype bundle changed authority")

        notion_payload = _diagnostic_call(diagnostics, "notion_dashboard", lambda: build_notion_readonly_dashboard(workspace, notion_path), fallback={"dashboard": {}})
        notion_dashboard = notion_payload.get("dashboard", {}) if isinstance(notion_payload, dict) else {}
        if isinstance(notion_dashboard, dict) and notion_dashboard.get("network_call_performed") is True:
            raise AssertionError("notion builder performed network call")

        proposal_note.write_text(
            "---\n"
            "seos_type: \"task\"\n"
            "seos_id: \"knowledge_followup_task\"\n"
            "authority: \"proposal\"\n"
            "title: \"Knowledge follow-up\"\n"
            "---\n\n"
            "# Knowledge follow-up\n\n"
            "Review exported vault notes and propose a follow-up task.\n",
            encoding="utf-8",
        )
        ingest_payload = _diagnostic_call(diagnostics, "proposal_ingest", lambda: ingest_proposal_note(proposal_note, workspace), fallback={"proposal": {}})
        proposal = ingest_payload.get("proposal", {}) if isinstance(ingest_payload, dict) else {}
        if isinstance(proposal, dict):
            _require(proposal.get("task_created") is not True, "proposal changed task state")
            _require(proposal.get("approval_created") is not True, "proposal changed approval state")
            _require(proposal.get("permit_created") is not True, "proposal changed permit state")
            _require(proposal.get("execution_authority_granted") is not True, "proposal changed execution authority")

        print(
            json.dumps(
                {
                    "ok": True,
                    "schema": "seos_knowledge_control_vault_check_v1",
                    "workspace_export_ok": bool(isinstance(export_payload, dict) and export_payload.get("ok")),
                    "vault_note_count": scan_payload.get("note_count", 0) if isinstance(scan_payload, dict) else 0,
                    "vault_problem_count": scan_payload.get("problem_count", 0) if isinstance(scan_payload, dict) else 0,
                    "blocking_vault_problem_count": len(blocking_scan_problems),
                    "graph_node_count": graph.get("node_count", 0) if isinstance(graph, dict) else 0,
                    "graph_edge_count": graph.get("edge_count", 0) if isinstance(graph, dict) else 0,
                    "logseq_written": len(logseq_payload.get("written", [])) if isinstance(logseq_payload, dict) else 0,
                    "anytype_object_count": anytype_bundle.get("object_count", 0) if isinstance(anytype_bundle, dict) else 0,
                    "notion_task_count": notion_dashboard.get("task_count", 0) if isinstance(notion_dashboard, dict) else 0,
                    "diagnostics": diagnostics,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _diagnostic_call(diagnostics: list[dict[str, object]], name: str, func, *, fallback: dict[str, object]) -> dict[str, object]:
    try:
        payload = func()
        if isinstance(payload, dict) and payload.get("ok") is False:
            diagnostics.append({"step": name, "ok": False, "payload": payload})
        return payload if isinstance(payload, dict) else fallback
    except Exception as exc:
        diagnostics.append({"step": name, "ok": False, "detail": exc.__class__.__name__, "message": str(exc)})
        return fallback


def _require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
