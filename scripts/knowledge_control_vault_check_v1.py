#!/usr/bin/env python3
"""Validate the SEOS knowledge/control-vault layer."""

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


def main() -> int:
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

        export_payload = export_workspace_to_vault(workspace, vault)
        _require(export_payload.get("ok"), "workspace vault export failed")
        _require((vault / "01_Tasks" / "knowledge_demo_task.md").exists(), "task note missing")

        graph_payload = write_workspace_graph(workspace, graph_path)
        _require(graph_payload.get("ok"), "graph build failed")
        _require(graph_payload["graph"]["node_count"] >= 2, "graph missing nodes")

        scan_payload = scan_control_vault(vault)
        _require(scan_payload.get("ok"), json.dumps(scan_payload.get("problems", []), sort_keys=True))

        logseq_payload = export_workspace_to_logseq(workspace, logseq_root)
        _require(logseq_payload.get("ok"), "logseq export failed")
        _require(logseq_payload["execution_authority_granted"] is False, "logseq export changed authority")

        anytype_payload = export_anytype_object_bundle(workspace, anytype_path)
        _require(anytype_payload.get("ok"), "anytype bundle failed")
        _require(anytype_payload["bundle"]["execution_authority_granted"] is False, "anytype bundle changed authority")

        notion_payload = build_notion_readonly_dashboard(workspace, notion_path)
        _require(notion_payload.get("ok"), "notion dashboard failed")
        _require(notion_payload["dashboard"]["network_call_performed"] is False, "notion builder performed network call")

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
        ingest_payload = ingest_proposal_note(proposal_note, workspace)
        _require(ingest_payload.get("ok"), "proposal ingest failed")
        _require(ingest_payload["proposal"]["task_created"] is False, "proposal changed task state")

        print(
            json.dumps(
                {
                    "ok": True,
                    "schema": "seos_knowledge_control_vault_check_v1",
                    "vault_note_count": scan_payload["note_count"],
                    "graph_node_count": graph_payload["graph"]["node_count"],
                    "graph_edge_count": graph_payload["graph"]["edge_count"],
                    "logseq_written": len(logseq_payload["written"]),
                    "anytype_object_count": anytype_payload["bundle"]["object_count"],
                    "notion_task_count": notion_payload["dashboard"]["task_count"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
