"""Read-only production inspection spine for operator handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Final
import json
import re

from creative.adapters.optional_contracts import build_optional_adapter_contracts
from creative.assets.local_asset_library import build_asset_library_scan, write_asset_library_outputs
from creative.common import SCHEMA_VERSION, repo_root, stable_id, write_json
from creative.hardening.production import build_production_hardening_plan
from creative.operation.real_works import build_real_works_operation_report
from creative.pressure.real_project import build_real_project_pressure_test
from creative.reports.local_production_dashboard import build_local_production_dashboard
from creative.reports.local_tool_health_dashboard import build_local_tool_health_dashboard
from creative.shots.shot_planner import build_shot_plan
from kernel.knowledge.frontmatter import dump_frontmatter
from kernel.knowledge.object_model import digest_payload

SPINE_ID: Final[str] = "operator-production-spine-v1"
DEFAULT_OUTPUT_DIR: Final[Path] = Path("reports/creative/production_spine_v1")
DEFAULT_ASSET_ROOT: Final[Path] = Path("tests/fixtures/creative/assets")
DEFAULT_TEMPLATE: Final[str] = "energy-impact"
DEFAULT_SHOT_ID: Final[str] = "SHOT_OPERATOR_PRODUCTION_SPINE_V1"
DEFAULT_SCENARIO_ID: Final[str] = "OPERATOR_PRODUCTION_SPINE_V1"
DEFAULT_SCENARIO_LABEL: Final[str] = "Operator production spine v1"

FORBIDDEN_RUNTIME_MARKERS: Final[tuple[str, ...]] = (
    "--approve-local-execution",
    "houdini-smoke",
    "comfyui-smoke",
    "seos.py run ",
    "seos.py rpc invoke",
    "seos.py shot run",
    "seos.py package run",
    "notion_api_endpoint",
)


def build_operator_production_spine_inspection(
    *,
    asset_root: Path = DEFAULT_ASSET_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    mode: str = "public",
    template_name: str = DEFAULT_TEMPLATE,
    shot_id: str = DEFAULT_SHOT_ID,
    scenario_id: str = DEFAULT_SCENARIO_ID,
    scenario_label: str = DEFAULT_SCENARIO_LABEL,
    doctor_report: dict[str, object] | None = None,
    max_depth: int = 12,
) -> dict[str, object]:
    """Run the safe production inspection spine and write operator artifacts.

    This function only performs local, read-only inspection and report writing.
    It does not launch DCC tools, call cloud services, move assets, create
    approval or permit records, or grant execution authority.
    """

    if mode not in {"public", "local"}:
        raise ValueError("mode must be public or local")

    root = repo_root()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_root = Path(asset_root)
    run_id = stable_id(SPINE_ID, asset_root.as_posix(), template_name, shot_id, scenario_id)

    paths = _artifact_paths(output_dir)

    asset_scan = build_asset_library_scan(asset_root, mode=mode, max_depth=max_depth)
    write_asset_library_outputs(
        asset_scan,
        root=asset_root,
        output_json=paths["asset_scan_json"],
        output_markdown=paths["asset_scan_md"],
    )

    production_dashboard = build_local_production_dashboard(
        asset_scan,
        output_markdown=paths["production_dashboard_md"],
        output_html=paths["production_dashboard_html"],
    )
    production_dashboard["outputs"] = dict(production_dashboard.get("outputs", {})) | {
        "json": _display_path(paths["production_dashboard_json"], root)
    }
    write_json(paths["production_dashboard_json"], production_dashboard)

    tool_health = build_local_tool_health_dashboard(
        doctor_report,
        mode=mode,
        output_json=paths["tool_health_json"],
        output_markdown=paths["tool_health_md"],
        output_html=paths["tool_health_html"],
    )
    adapter_contracts = build_optional_adapter_contracts(
        doctor_report,
        mode=mode,
        output_json=paths["adapter_contracts_json"],
        output_markdown=paths["adapter_contracts_md"],
    )

    shot_plan = build_shot_plan(
        asset_scan,
        template_name=template_name,
        shot_id=shot_id,
        mode=mode,
        tool_health_report=tool_health,
        adapter_contracts_report=adapter_contracts,
        output_json=paths["shot_plan_json"],
        output_markdown=paths["shot_plan_md"],
    )

    pressure_test = build_real_project_pressure_test(
        asset_scan,
        template_name=template_name,
        shot_id=shot_id,
        mode=mode,
        scenario_id=scenario_id,
        scenario_label=scenario_label,
        tool_health_report=tool_health,
        adapter_contracts_report=adapter_contracts,
        output_json=paths["pressure_test_json"],
        output_markdown=paths["pressure_test_md"],
    )

    hardening_package_paths = [
        _package_input_path(paths[key], root)
        for key in (
            "asset_scan_json",
            "asset_scan_md",
            "production_dashboard_json",
            "production_dashboard_md",
            "production_dashboard_html",
            "tool_health_json",
            "tool_health_md",
            "adapter_contracts_json",
            "adapter_contracts_md",
            "shot_plan_json",
            "shot_plan_md",
            "pressure_test_json",
            "pressure_test_md",
        )
    ]
    hardening_plan = build_production_hardening_plan(
        pressure_test,
        package_paths=hardening_package_paths,
        root=root,
        output_json=paths["hardening_plan_json"],
        output_markdown=paths["hardening_plan_md"],
    )

    works_operation = build_real_works_operation_report(
        asset_scan,
        mode=mode,
        tool_health_report=tool_health,
        adapter_contracts_report=adapter_contracts,
        pressure_report=pressure_test,
        hardening_plan=hardening_plan,
        output_json=paths["works_operation_json"],
        output_markdown=paths["works_operation_md"],
    )

    action_list = build_action_list(
        asset_scan=asset_scan,
        tool_health=tool_health,
        adapter_contracts=adapter_contracts,
        pressure_test=pressure_test,
        hardening_plan=hardening_plan,
        works_operation=works_operation,
    )
    write_json(paths["action_list_json"], action_list)
    paths["action_list_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["action_list_md"].write_text(render_action_list_markdown(action_list), encoding="utf-8")

    stage_outputs = _stage_outputs(paths, root)
    knowledge_graph = build_knowledge_graph(
        run_id=run_id,
        stage_outputs=stage_outputs,
        asset_scan=asset_scan,
        tool_health=tool_health,
        adapter_contracts=adapter_contracts,
        pressure_test=pressure_test,
        hardening_plan=hardening_plan,
        works_operation=works_operation,
        action_list=action_list,
    )
    write_json(paths["knowledge_graph_json"], knowledge_graph)
    paths["knowledge_graph_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["knowledge_graph_md"].write_text(render_knowledge_graph_markdown(knowledge_graph), encoding="utf-8")

    vault = write_obsidian_vault(
        vault_dir=paths["obsidian_vault_dir"],
        run_id=run_id,
        stage_outputs=stage_outputs,
        asset_scan=asset_scan,
        tool_health=tool_health,
        pressure_test=pressure_test,
        hardening_plan=hardening_plan,
        works_operation=works_operation,
        action_list=action_list,
        knowledge_graph=knowledge_graph,
        root=root,
    )

    safety = _safety_summary()
    status = _inspection_status(hardening_plan, works_operation, action_list)
    report = {
        "action_summary": action_list["summary"],
        "asset_summary": asset_scan.get("summary", {}),
        "authority_model": {
            "action_list_authority": "operator_queue_suggestion_only",
            "execution_authority": "not_granted",
            "knowledge_graph_authority": "derived_index",
            "obsidian_vault_authority": "mirror",
            "permit_authority": "unchanged_external_to_this_command",
        },
        "forbidden_runtime_markers": list(FORBIDDEN_RUNTIME_MARKERS),
        "hardening_status": hardening_plan.get("hardening_status", ""),
        "inspection_status": status,
        "kind": "operator_production_spine_inspection_v1",
        "knowledge_graph": {
            "edge_count": knowledge_graph["summary"]["edge_count"],
            "json": _display_path(paths["knowledge_graph_json"], root),
            "markdown": _display_path(paths["knowledge_graph_md"], root),
            "node_count": knowledge_graph["summary"]["node_count"],
        },
        "mode": mode,
        "ok": bool(hardening_plan.get("ok", True)) and bool(action_list.get("ok", True)),
        "operation_status": works_operation.get("operation_status", ""),
        "outputs": {
            "action_list_json": _display_path(paths["action_list_json"], root),
            "action_list_md": _display_path(paths["action_list_md"], root),
            "manifest_json": _display_path(paths["manifest_json"], root),
            "manifest_md": _display_path(paths["manifest_md"], root),
            "obsidian_vault": _display_path(paths["obsidian_vault_dir"], root),
        },
        "pressure_status": pressure_test.get("pressure_status", ""),
        "read_only": True,
        "ready_for_execution": False,
        "run_id": run_id,
        "safety": safety,
        "schema_version": SCHEMA_VERSION,
        "spine_id": SPINE_ID,
        "stage_outputs": stage_outputs,
        "tool_health_summary": tool_health.get("summary", {}),
        "vault": vault,
    }
    write_json(paths["manifest_json"], report)
    paths["manifest_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["manifest_md"].write_text(render_inspection_markdown(report), encoding="utf-8")
    report["outputs"]["manifest_json"] = _display_path(paths["manifest_json"], root)
    report["outputs"]["manifest_md"] = _display_path(paths["manifest_md"], root)
    return report


def load_doctor_report(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_action_list(
    *,
    asset_scan: dict[str, object],
    tool_health: dict[str, object],
    adapter_contracts: dict[str, object],
    pressure_test: dict[str, object],
    hardening_plan: dict[str, object],
    works_operation: dict[str, object],
) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    seen: set[str] = set()

    for action in hardening_plan.get("repair_actions", []):
        item = dict(action)
        _append_action(
            actions,
            seen,
            priority=str(item.get("priority", "P2")),
            source=f"hardening:{item.get('source_finding_code', 'finding')}",
            workstream=str(item.get("workstream", "hardening")),
            action=str(item.get("operator_action", "")),
            done_when=str(item.get("done_when", "")),
            command=str(item.get("command", "")),
        )

    for need in works_operation.get("development_needs", []):
        item = dict(need)
        _append_action(
            actions,
            seen,
            priority=str(item.get("priority", "P2")),
            source=f"works_operation:{item.get('source', 'development_need')}",
            workstream=str(item.get("workstream", "operation")),
            action=str(item.get("need", "")),
            done_when="Rerun production inspect and confirm the related workflow or finding improved.",
            command="python3 seos.py production inspect",
        )

    for action in tool_health.get("next_actions", []):
        _append_action(
            actions,
            seen,
            priority="P1",
            source="tool_health",
            workstream="local_tool_readiness",
            action=str(action),
            done_when="Rerun production inspect and confirm tool-health blocked_count is lower or explained.",
            command="python3 seos.py production inspect",
        )

    for action in adapter_contracts.get("next_actions", []):
        _append_action(
            actions,
            seen,
            priority="P2",
            source="adapter_contracts",
            workstream="adapter_proof",
            action=str(action),
            done_when="Keep adapter claims contract-only until a separate local proof exists.",
            command="python3 seos.py production inspect",
        )

    for source_name, payload in (
        ("asset_scan", asset_scan),
        ("pressure_test", pressure_test),
        ("works_operation", works_operation),
    ):
        for action in payload.get("next_actions", []):
            _append_action(
                actions,
                seen,
                priority="P2",
                source=source_name,
                workstream=source_name,
                action=str(action),
                done_when="Rerun production inspect and compare the new manifest.",
                command="python3 seos.py production inspect",
            )

    actions.sort(key=lambda item: (_priority_rank(str(item.get("priority"))), str(item.get("source")), str(item.get("action"))))
    for index, action in enumerate(actions, start=1):
        action["order"] = index
        action["id"] = stable_id("ACTION", index, action.get("priority"), action.get("source"), action.get("action"))
    summary = _action_summary(actions)
    return {
        "actions": actions,
        "authority": "operator_action_list_only",
        "execution_authority_granted": False,
        "approval_or_permit_created": False,
        "kind": "operator_production_action_list_v1",
        "ok": all(bool(action.get("allowed_without_new_authority")) for action in actions),
        "read_only": True,
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
    }


def build_knowledge_graph(
    *,
    run_id: str,
    stage_outputs: list[dict[str, object]],
    asset_scan: dict[str, object],
    tool_health: dict[str, object],
    adapter_contracts: dict[str, object],
    pressure_test: dict[str, object],
    hardening_plan: dict[str, object],
    works_operation: dict[str, object],
    action_list: dict[str, object],
) -> dict[str, object]:
    stage_nodes = [
        {
            "authority": "derived_report",
            "id": str(stage["id"]),
            "label": str(stage["label"]),
            "output_paths": list(stage.get("outputs", [])),
            "status": str(stage.get("status", "COMPLETED")),
            "type": "stage",
        }
        for stage in stage_outputs
    ]
    summary_nodes = [
        {
            "authority": "derived_summary",
            "id": "asset_summary",
            "label": "Asset summary",
            "metrics": {
                "archive_warning_count": dict(asset_scan.get("summary", {})).get("archive_warning_count", 0),
                "duplicate_group_count": dict(asset_scan.get("summary", {})).get("duplicate_group_count", 0),
                "total_assets": dict(asset_scan.get("summary", {})).get("total_assets", 0),
            },
            "type": "summary",
        },
        {
            "authority": "derived_summary",
            "id": "tool_health_summary",
            "label": "Tool health summary",
            "metrics": dict(tool_health.get("summary", {})),
            "type": "summary",
        },
        {
            "authority": "derived_summary",
            "id": "adapter_contract_summary",
            "label": "Adapter contract summary",
            "metrics": dict(adapter_contracts.get("summary", {})),
            "type": "summary",
        },
        {
            "authority": "derived_summary",
            "id": "pressure_status",
            "label": "Pressure status",
            "metrics": {"status": pressure_test.get("pressure_status", "")},
            "type": "summary",
        },
        {
            "authority": "derived_summary",
            "id": "hardening_status",
            "label": "Hardening status",
            "metrics": {"status": hardening_plan.get("hardening_status", "")},
            "type": "summary",
        },
        {
            "authority": "derived_summary",
            "id": "operation_status",
            "label": "Operation status",
            "metrics": {"status": works_operation.get("operation_status", "")},
            "type": "summary",
        },
    ]
    action_nodes = [
        {
            "authority": "operator_queue_suggestion_only",
            "id": str(action.get("id")),
            "label": str(action.get("action")),
            "priority": str(action.get("priority")),
            "source": str(action.get("source")),
            "type": "action",
        }
        for action in action_list.get("actions", [])
    ]
    sequential_edges = [
        {"from": "asset_scan", "to": "production_dashboard", "type": "feeds"},
        {"from": "production_dashboard", "to": "shot_plan", "type": "informs"},
        {"from": "tool_health", "to": "shot_plan", "type": "gates_optional_runners"},
        {"from": "adapter_contracts", "to": "shot_plan", "type": "bounds_execution_claims"},
        {"from": "shot_plan", "to": "pressure_test", "type": "feeds"},
        {"from": "pressure_test", "to": "hardening_plan", "type": "findings_to_actions"},
        {"from": "hardening_plan", "to": "works_operation", "type": "informs"},
        {"from": "works_operation", "to": "action_list", "type": "feeds"},
        {"from": "action_list", "to": "obsidian_vault", "type": "mirrors"},
        {"from": "knowledge_graph", "to": "obsidian_vault", "type": "mirrors"},
    ]
    action_edges = [
        {"from": _source_node_for_action(str(action.get("source", "action_source"))), "to": str(action.get("id")), "type": "creates_operator_action"}
        for action in action_list.get("actions", [])
    ]
    nodes = stage_nodes + summary_nodes + action_nodes
    edges = sequential_edges + action_edges
    return {
        "authority": "derived_index_only",
        "edges": edges,
        "execution_authority_granted": False,
        "approval_or_permit_created": False,
        "kind": "operator_production_knowledge_graph_v1",
        "nodes": nodes,
        "read_only": True,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "action_node_count": len(action_nodes),
            "edge_count": len(edges),
            "node_count": len(nodes),
            "stage_node_count": len(stage_nodes),
        },
    }


def write_obsidian_vault(
    *,
    vault_dir: Path,
    run_id: str,
    stage_outputs: list[dict[str, object]],
    asset_scan: dict[str, object],
    tool_health: dict[str, object],
    pressure_test: dict[str, object],
    hardening_plan: dict[str, object],
    works_operation: dict[str, object],
    action_list: dict[str, object],
    knowledge_graph: dict[str, object],
    root: Path,
) -> dict[str, object]:
    vault_dir.mkdir(parents=True, exist_ok=True)
    report_dir = vault_dir / "01_Reports"
    action_dir = vault_dir / "02_Actions"
    graph_dir = vault_dir / "03_Graph"
    for directory in (report_dir, action_dir, graph_dir):
        directory.mkdir(parents=True, exist_ok=True)

    files = {
        "index": vault_dir / "00_Index.md",
        "asset_scan": report_dir / "asset_scan.md",
        "tool_health": report_dir / "tool_health.md",
        "pressure_test": report_dir / "pressure_test.md",
        "hardening_plan": report_dir / "hardening_plan.md",
        "works_operation": report_dir / "works_operation.md",
        "action_list": action_dir / "action_list.md",
        "knowledge_graph": graph_dir / "knowledge_graph.md",
    }

    frontmatter = _frontmatter(run_id)
    files["index"].write_text(
        frontmatter
        + "\n# SEOS Production Spine Index\n\n"
        + "- Spine: `operator-production-spine-v1`\n"
        + "- Authority: `mirror`\n"
        + "- Execution authority granted: `false`\n"
        + "- Approval or permit created: `false`\n"
        + "- Reports: [[asset_scan]], [[tool_health]], [[pressure_test]], [[hardening_plan]], [[works_operation]]\n"
        + "- Operator queue: [[action_list]]\n"
        + "- Graph: [[knowledge_graph]]\n\n"
        + "## Stage Outputs\n\n"
        + "\n".join(f"- `{stage.get('id')}`: {', '.join(str(path) for path in stage.get('outputs', []))}" for stage in stage_outputs)
        + "\n",
        encoding="utf-8",
    )
    files["asset_scan"].write_text(frontmatter + _summary_note("Asset Scan", asset_scan.get("summary", {})), encoding="utf-8")
    files["tool_health"].write_text(frontmatter + _summary_note("Tool Health", tool_health.get("summary", {})), encoding="utf-8")
    files["pressure_test"].write_text(
        frontmatter
        + "# Pressure Test\n\n"
        + f"- Pressure status: `{pressure_test.get('pressure_status')}`\n"
        + f"- Ready for execution: `{pressure_test.get('ready_for_execution')}`\n"
        + f"- Finding count: `{len(pressure_test.get('findings', []))}`\n",
        encoding="utf-8",
    )
    files["hardening_plan"].write_text(
        frontmatter
        + "# Hardening Plan\n\n"
        + f"- Hardening status: `{hardening_plan.get('hardening_status')}`\n"
        + f"- Repair action count: `{len(hardening_plan.get('repair_actions', []))}`\n"
        + f"- Package status: `{dict(hardening_plan.get('package_summary', {})).get('package_status')}`\n",
        encoding="utf-8",
    )
    files["works_operation"].write_text(
        frontmatter
        + "# Works Operation\n\n"
        + f"- Operation status: `{works_operation.get('operation_status')}`\n"
        + f"- Workflow count: `{dict(works_operation.get('repeatability_summary', {})).get('workflow_count', 0)}`\n"
        + f"- Blocked workflow count: `{dict(works_operation.get('repeatability_summary', {})).get('blocked_workflow_count', 0)}`\n",
        encoding="utf-8",
    )
    files["action_list"].write_text(frontmatter + render_action_list_markdown(action_list), encoding="utf-8")
    files["knowledge_graph"].write_text(frontmatter + render_knowledge_graph_markdown(knowledge_graph), encoding="utf-8")

    return {
        "authority": "mirror",
        "execution_authority_granted": False,
        "approval_or_permit_created": False,
        "kind": "obsidian_vault_manifest_v1",
        "path": _display_path(vault_dir, root),
        "files": {name: _display_path(path, root) for name, path in files.items()},
        "read_only": True,
    }


def render_action_list_markdown(action_list: dict[str, object]) -> str:
    summary = dict(action_list.get("summary", {}))
    lines = [
        "# SEOS Production Action List",
        "",
        f"- Authority: `{action_list.get('authority')}`",
        f"- Execution authority granted: `{action_list.get('execution_authority_granted')}`",
        f"- Approval or permit created: `{action_list.get('approval_or_permit_created')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in ("total_actions", "P0", "P1", "P2", "P3", "blocked_command_count"):
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.extend(["", "## Actions", "", "| Order | Priority | Source | Action | Command |", "| ---: | --- | --- | --- | --- |"])
    for action in action_list.get("actions", []):
        item = dict(action)
        lines.append(
            f"| {item.get('order')} | `{item.get('priority')}` | `{item.get('source')}` | "
            f"{_markdown_cell(item.get('action'))} | `{_markdown_code_cell(item.get('command'))}` |"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This list is a planning queue only.",
            "- It does not create approvals or permits.",
            "- It does not grant execution authority.",
            "- Commands containing local execution markers are blocked from immediate action.",
            "",
        ]
    )
    return "\n".join(lines)


def render_knowledge_graph_markdown(graph: dict[str, object]) -> str:
    summary = dict(graph.get("summary", {}))
    lines = [
        "# SEOS Production Knowledge Graph",
        "",
        f"- Authority: `{graph.get('authority')}`",
        f"- Execution authority granted: `{graph.get('execution_authority_granted')}`",
        f"- Approval or permit created: `{graph.get('approval_or_permit_created')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| node_count | {summary.get('node_count', 0)} |",
        f"| edge_count | {summary.get('edge_count', 0)} |",
        f"| stage_node_count | {summary.get('stage_node_count', 0)} |",
        f"| action_node_count | {summary.get('action_node_count', 0)} |",
        "",
        "## Stage Nodes",
        "",
        "| Node | Type | Authority |",
        "| --- | --- | --- |",
    ]
    for node in graph.get("nodes", []):
        item = dict(node)
        if item.get("type") != "stage":
            continue
        lines.append(f"| `{item.get('id')}` | `{item.get('type')}` | `{item.get('authority')}` |")
    lines.extend(["", "## Edges", "", "| From | To | Type |", "| --- | --- | --- |"])
    for edge in graph.get("edges", [])[:80]:
        item = dict(edge)
        lines.append(f"| `{item.get('from')}` | `{item.get('to')}` | `{item.get('type')}` |")
    return "\n".join(lines) + "\n"


def render_inspection_markdown(report: dict[str, object]) -> str:
    action_summary = dict(report.get("action_summary", {}))
    lines = [
        "# SEOS Operator Production Spine Inspection",
        "",
        f"- Spine: `{report.get('spine_id')}`",
        f"- Run id: `{report.get('run_id')}`",
        f"- Inspection status: `{report.get('inspection_status')}`",
        f"- Pressure status: `{report.get('pressure_status')}`",
        f"- Hardening status: `{report.get('hardening_status')}`",
        f"- Operation status: `{report.get('operation_status')}`",
        f"- Ready for execution: `{report.get('ready_for_execution')}`",
        "",
        "## Safety",
        "",
    ]
    for key, value in dict(report.get("safety", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Action Summary",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| total_actions | {action_summary.get('total_actions', 0)} |",
            f"| P0 | {action_summary.get('P0', 0)} |",
            f"| P1 | {action_summary.get('P1', 0)} |",
            f"| P2 | {action_summary.get('P2', 0)} |",
            f"| P3 | {action_summary.get('P3', 0)} |",
            "",
            "## Stage Outputs",
            "",
            "| Stage | Status | Outputs |",
            "| --- | --- | --- |",
        ]
    )
    for stage in report.get("stage_outputs", []):
        item = dict(stage)
        lines.append(f"| `{item.get('id')}` | `{item.get('status')}` | {', '.join(f'`{path}`' for path in item.get('outputs', []))} |")
    lines.extend(
        [
            "",
            "## Vault And Graph",
            "",
            f"- Obsidian vault: `{dict(report.get('outputs', {})).get('obsidian_vault')}`",
            f"- Knowledge graph JSON: `{dict(report.get('knowledge_graph', {})).get('json')}`",
            f"- Action list JSON: `{dict(report.get('outputs', {})).get('action_list_json')}`",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "action_list_json": output_dir / "action_list.json",
        "action_list_md": output_dir / "action_list.md",
        "adapter_contracts_json": output_dir / "adapter_contracts.json",
        "adapter_contracts_md": output_dir / "adapter_contracts.md",
        "asset_scan_json": output_dir / "asset_scan.json",
        "asset_scan_md": output_dir / "asset_scan.md",
        "hardening_plan_json": output_dir / "hardening_plan.json",
        "hardening_plan_md": output_dir / "hardening_plan.md",
        "knowledge_graph_json": output_dir / "knowledge_graph.json",
        "knowledge_graph_md": output_dir / "knowledge_graph.md",
        "manifest_json": output_dir / "manifest.json",
        "manifest_md": output_dir / "manifest.md",
        "obsidian_vault_dir": output_dir / "obsidian_vault",
        "pressure_test_json": output_dir / "pressure_test.json",
        "pressure_test_md": output_dir / "pressure_test.md",
        "production_dashboard_json": output_dir / "production_dashboard.json",
        "production_dashboard_md": output_dir / "production_dashboard.md",
        "production_dashboard_html": output_dir / "production_dashboard.html",
        "shot_plan_json": output_dir / "shot_plan.json",
        "shot_plan_md": output_dir / "shot_plan.md",
        "tool_health_json": output_dir / "tool_health.json",
        "tool_health_md": output_dir / "tool_health.md",
        "tool_health_html": output_dir / "tool_health.html",
        "works_operation_json": output_dir / "works_operation.json",
        "works_operation_md": output_dir / "works_operation.md",
    }


def _stage_outputs(paths: dict[str, Path], root: Path) -> list[dict[str, object]]:
    specs = (
        ("asset_scan", "Asset Scan", ("asset_scan_json", "asset_scan_md")),
        ("production_dashboard", "Production Dashboard", ("production_dashboard_json", "production_dashboard_md", "production_dashboard_html")),
        ("tool_health", "Tool Health", ("tool_health_json", "tool_health_md", "tool_health_html")),
        ("adapter_contracts", "Adapter Contracts", ("adapter_contracts_json", "adapter_contracts_md")),
        ("shot_plan", "Shot Plan", ("shot_plan_json", "shot_plan_md")),
        ("pressure_test", "Pressure Test", ("pressure_test_json", "pressure_test_md")),
        ("hardening_plan", "Hardening Plan", ("hardening_plan_json", "hardening_plan_md")),
        ("works_operation", "Works Operation", ("works_operation_json", "works_operation_md")),
        ("action_list", "Action List", ("action_list_json", "action_list_md")),
        ("knowledge_graph", "Knowledge Graph", ("knowledge_graph_json", "knowledge_graph_md")),
        ("obsidian_vault", "Obsidian Vault", ("obsidian_vault_dir",)),
    )
    return [
        {
            "id": stage_id,
            "label": label,
            "outputs": [_display_path(paths[key], root) for key in keys],
            "status": "COMPLETED",
        }
        for stage_id, label, keys in specs
    ]


def _append_action(
    actions: list[dict[str, object]],
    seen: set[str],
    *,
    priority: str,
    source: str,
    workstream: str,
    action: str,
    done_when: str,
    command: str,
) -> None:
    text = " ".join(action.split())
    if not text:
        return
    key = re.sub(r"\s+", " ", f"{source}|{workstream}|{text}").lower()
    if key in seen:
        return
    seen.add(key)
    blocked_markers = [marker for marker in FORBIDDEN_RUNTIME_MARKERS if marker in command or marker in text]
    actions.append(
        {
            "action": text,
            "allowed_without_new_authority": not blocked_markers,
            "blocked_runtime_markers": blocked_markers,
            "command": command,
            "done_when": done_when,
            "execution_authority_granted": False,
            "priority": priority if priority in {"P0", "P1", "P2", "P3"} else "P2",
            "source": source,
            "status": "OPEN",
            "workstream": workstream,
        }
    )


def _action_summary(actions: list[dict[str, object]]) -> dict[str, int]:
    summary = {"total_actions": len(actions), "P0": 0, "P1": 0, "P2": 0, "P3": 0, "blocked_command_count": 0}
    for action in actions:
        priority = str(action.get("priority", "P2"))
        if priority in {"P0", "P1", "P2", "P3"}:
            summary[priority] += 1
        if not action.get("allowed_without_new_authority"):
            summary["blocked_command_count"] += 1
    return summary


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 4)


def _inspection_status(
    hardening_plan: dict[str, object],
    works_operation: dict[str, object],
    action_list: dict[str, object],
) -> str:
    summary = dict(action_list.get("summary", {}))
    if int(summary.get("P0", 0)):
        return "ACTIVE_P0_REPAIR_LOOP"
    if works_operation.get("operation_status") == "ACTIVE_REPAIR_LOOP":
        return "ACTIVE_REPAIR_LOOP"
    if hardening_plan.get("hardening_status") in {"NEEDS_REPAIR_BEFORE_EXECUTION", "BLOCKED_NEEDS_PROJECT_REPAIR", "BLOCKED_NEEDS_PACKAGE_REPAIR"}:
        return "ACTIVE_REPAIR_LOOP"
    return "READY_FOR_REPEATABLE_MANUAL_OPERATION"


def _safety_summary() -> dict[str, bool]:
    return {
        "asset_mutation_performed": False,
        "asset_move_performed": False,
        "approval_or_permit_created": False,
        "cloud_call_performed": False,
        "dcc_execution_performed": False,
        "destructive_action_performed": False,
        "execution_authority_granted": False,
        "package_or_archive_created": False,
    }


def _frontmatter(run_id: str) -> str:
    return dump_frontmatter(
        {
            "schema": "seos_knowledge_object_v1",
            "seos_type": "production_inspection_mirror",
            "seos_id": run_id,
            "title": "SEOS production spine mirror",
            "authority": "mirror",
            "source": "seos",
            "digest": digest_payload({"spine_id": SPINE_ID, "run_id": run_id}),
            "public": True,
            "local_path_redacted": True,
            "execution_authority_granted": False,
            "approval_or_permit_created": False,
        }
    )


def _summary_note(title: str, summary: object) -> str:
    lines = [f"# {title}", "", "| Metric | Value |", "| --- | --- |"]
    for key, value in sorted(dict(summary).items()):
        if isinstance(value, (dict, list)):
            continue
        lines.append(f"| `{key}` | `{value}` |")
    return "\n".join(lines) + "\n"


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<external-path:{path.name}>"


def _package_input_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _source_node_for_action(source: str) -> str:
    root_source = source.split(":", 1)[0]
    if root_source == "hardening":
        return "hardening_plan"
    return root_source


def _markdown_cell(value: object) -> str:
    text = str(value or "").replace("|", "\\|")
    return text


def _markdown_code_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("`", "'")
