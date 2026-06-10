"""Repeated real-work operation loop for the creative pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from creative.common import SCHEMA_VERSION, write_json
from creative.shots.shot_planner import build_shot_plan

WORKFLOWS: Final[tuple[dict[str, str], ...]] = (
    {
        "id": "energy_impact",
        "label": "Energy Impact",
        "shot_id": "SHOT_WORKS_ENERGY_IMPACT",
        "template": "energy-impact",
        "purpose": "Impact VFX with plate, FX source, lookdev, comp, and optional local runner checks.",
    },
    {
        "id": "smoke_dust",
        "label": "Smoke / Dust",
        "shot_id": "SHOT_WORKS_SMOKE_DUST",
        "template": "smoke-dust",
        "purpose": "Cache-focused smoke or dust shot with plate, VDB/cache, and lookdev handoff.",
    },
    {
        "id": "portal_lightning",
        "label": "Portal / Lightning",
        "shot_id": "SHOT_WORKS_PORTAL_LIGHTNING",
        "template": "portal-lightning",
        "purpose": "Stylized FX shot with DCC source, energy lookdev, comp, and optional repair workflow.",
    },
    {
        "id": "editorial_handoff",
        "label": "Editorial Handoff",
        "shot_id": "SHOT_WORKS_EDITORIAL_HANDOFF",
        "template": "editorial-handoff",
        "purpose": "Editorial package with media, audio, LUT, and finishing handoff.",
    },
)


def build_real_works_operation_report(
    asset_report: dict[str, object],
    *,
    mode: str = "public",
    tool_health_report: dict[str, object] | None = None,
    adapter_contracts_report: dict[str, object] | None = None,
    pressure_report: dict[str, object] | None = None,
    hardening_plan: dict[str, object] | None = None,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    """Build a read-only repeated-operation report for practical creative work."""
    if mode not in {"public", "local"}:
        raise ValueError("mode must be public or local")
    workflows = [
        _workflow_report(
            asset_report,
            workflow,
            mode=mode,
            tool_health_report=tool_health_report,
            adapter_contracts_report=adapter_contracts_report,
        )
        for workflow in WORKFLOWS
    ]
    workflows.append(_asset_library_workflow(asset_report, pressure_report, hardening_plan))
    operation_status = _operation_status(workflows, pressure_report, hardening_plan)
    report = {
        "destructive_actions_performed": False,
        "development_needs": _development_needs(pressure_report, hardening_plan, workflows),
        "execution_performed": False,
        "kind": "real_works_operation_v1",
        "mode": mode,
        "next_actions": _next_actions(workflows, pressure_report, hardening_plan),
        "ok": True,
        "operation_loop": _operation_loop(),
        "operation_status": operation_status,
        "pressure_status": pressure_report.get("pressure_status", "NOT_PROVIDED") if pressure_report else "NOT_PROVIDED",
        "hardening_status": hardening_plan.get("hardening_status", "NOT_PROVIDED") if hardening_plan else "NOT_PROVIDED",
        "read_only": True,
        "repeatability_summary": _repeatability_summary(workflows),
        "schema_version": SCHEMA_VERSION,
        "safety": {
            "asset_mutation": False,
            "dcc_or_ai_execution": False,
            "duplicate_deletion": False,
            "package_creation": False,
            "requires_separate_approval_for_optional_runners": True,
        },
        "workflows": workflows,
    }
    outputs: dict[str, str] = {}
    if output_json is not None:
        outputs["json"] = output_json.as_posix()
    if output_markdown is not None:
        outputs["markdown"] = output_markdown.as_posix()
    report["outputs"] = outputs
    if output_json is not None:
        write_json(output_json, report)
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_real_works_operation_markdown(report), encoding="utf-8")
    return report


def render_real_works_operation_markdown(report: dict[str, object]) -> str:
    summary = dict(report.get("repeatability_summary", {}))
    lines = [
        "# SEOS Real Works Operation",
        "",
        f"- Operation status: `{report.get('operation_status')}`",
        f"- Pressure status: `{report.get('pressure_status')}`",
        f"- Hardening status: `{report.get('hardening_status')}`",
        f"- Read-only: `{report.get('read_only')}`",
        "",
        "## Repeatability Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| workflow_count | {summary.get('workflow_count', 0)} |",
        f"| complete_workflow_count | {summary.get('complete_workflow_count', 0)} |",
        f"| blocked_workflow_count | {summary.get('blocked_workflow_count', 0)} |",
        f"| optional_runner_count | {summary.get('optional_runner_count', 0)} |",
        f"| nonready_optional_runner_count | {summary.get('nonready_optional_runner_count', 0)} |",
        "",
        "## Workflows",
        "",
        "| Workflow | Status | Missing Required | Candidates | Optional Runners |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for workflow in report.get("workflows", []):
        item = dict(workflow)
        summary_item = dict(item.get("summary", {}))
        lines.append(
            f"| `{item.get('id')}` | `{item.get('status')}` | "
            f"{summary_item.get('missing_required_count', 0)} | "
            f"{summary_item.get('total_candidate_count', 0)} | "
            f"{len(item.get('optional_runner_steps', []))} |"
        )

    lines.extend(["", "## Development Needs", "", "| Priority | Source | Need |", "| --- | --- | --- |"])
    for need in report.get("development_needs", []):
        item = dict(need)
        lines.append(f"| `{item.get('priority')}` | `{item.get('source')}` | {item.get('need')} |")

    lines.extend(["", "## Operation Loop", ""])
    for step in report.get("operation_loop", []):
        item = dict(step)
        lines.append(f"{item.get('order')}. `{item.get('command')}`")

    lines.extend(["", "## Next Actions", ""])
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This operation report is read-only.",
            "- It does not mutate assets, launch DCC tools, submit AI jobs, render, simulate, export, copy packages, or delete duplicates.",
            "- Optional runner steps remain separate approval-gated commands.",
            "",
        ]
    )
    return "\n".join(lines)


def _workflow_report(
    asset_report: dict[str, object],
    workflow: dict[str, str],
    *,
    mode: str,
    tool_health_report: dict[str, object] | None,
    adapter_contracts_report: dict[str, object] | None,
) -> dict[str, object]:
    plan = build_shot_plan(
        asset_report,
        template_name=workflow["template"],
        shot_id=workflow["shot_id"],
        mode=mode,
        tool_health_report=tool_health_report,
        adapter_contracts_report=adapter_contracts_report,
    )
    summary = dict(plan.get("summary", {}))
    runner_steps = list(dict(plan.get("execution_plan", {})).get("optional_runner_steps", []))
    return {
        "id": workflow["id"],
        "label": workflow["label"],
        "next_actions": plan.get("next_actions", []),
        "optional_runner_steps": runner_steps,
        "purpose": workflow["purpose"],
        "shot_id": plan.get("shot_id", workflow["shot_id"]),
        "status": "READY_FOR_MANUAL_PLANNING" if plan.get("complete") else "BLOCKED_MISSING_REQUIRED_ASSETS",
        "summary": {
            "missing_required_count": int(summary.get("missing_required_count", 0)),
            "optional_ready_count": int(summary.get("optional_ready_count", 0)),
            "required_ready_count": int(summary.get("required_ready_count", 0)),
            "template": summary.get("template", workflow["template"]),
            "total_candidate_count": int(summary.get("total_candidate_count", 0)),
        },
        "template": workflow["template"],
    }


def _asset_library_workflow(
    asset_report: dict[str, object],
    pressure_report: dict[str, object] | None,
    hardening_plan: dict[str, object] | None,
) -> dict[str, object]:
    summary = dict(asset_report.get("summary", {}))
    total_assets = int(summary.get("total_assets", len(asset_report.get("assets", []))))
    dashboard_summary = dict(pressure_report.get("dashboard_summary", {})) if pressure_report else {}
    package_summary = dict(hardening_plan.get("package_summary", {})) if hardening_plan else {}
    next_actions = []
    if int(dashboard_summary.get("archive_warning_count", 0)):
        next_actions.append("Restore missing archive parts before production extraction.")
    if int(dashboard_summary.get("duplicate_group_count", 0)):
        next_actions.append("Review duplicate asset groups before cleanup.")
    if int(dashboard_summary.get("incomplete_texture_set_count", 0)):
        next_actions.append("Repair or explicitly accept incomplete texture sets.")
    if package_summary.get("package_status") not in {"", "READY_FOR_HANDOFF", None}:
        next_actions.append("Repair output package manifest blockers before handoff.")
    if not next_actions:
        next_actions.append("Keep scanning new asset drops before shot binding.")
    return {
        "id": "asset_library",
        "label": "Asset Library",
        "next_actions": next_actions,
        "optional_runner_steps": [],
        "purpose": "Repeated scan, cleanup, package-readiness, and report-handoff workflow for the local asset library.",
        "shot_id": "",
        "status": "READY_FOR_MANUAL_PLANNING" if total_assets else "BLOCKED_MISSING_REQUIRED_ASSETS",
        "summary": {
            "missing_required_count": 0 if total_assets else 1,
            "optional_ready_count": 0,
            "required_ready_count": 1 if total_assets else 0,
            "template": "asset_library",
            "total_candidate_count": total_assets,
        },
        "template": "asset-library",
    }


def _operation_status(
    workflows: list[dict[str, object]],
    pressure_report: dict[str, object] | None,
    hardening_plan: dict[str, object] | None,
) -> str:
    if any(workflow.get("status") == "BLOCKED_MISSING_REQUIRED_ASSETS" for workflow in workflows):
        return "ACTIVE_REPAIR_LOOP"
    pressure_status = pressure_report.get("pressure_status", "") if pressure_report else ""
    hardening_status = hardening_plan.get("hardening_status", "") if hardening_plan else ""
    if pressure_status in {"USABLE_WITH_MANUAL_REPAIR", "BLOCKED_NEEDS_ASSET_OR_TEMPLATE_REPAIR"}:
        return "ACTIVE_REPAIR_LOOP"
    if hardening_status in {"NEEDS_REPAIR_BEFORE_EXECUTION", "BLOCKED_NEEDS_PROJECT_REPAIR", "BLOCKED_NEEDS_PACKAGE_REPAIR"}:
        return "ACTIVE_REPAIR_LOOP"
    return "READY_FOR_REPEATED_LOCAL_OPERATION"


def _repeatability_summary(workflows: list[dict[str, object]]) -> dict[str, object]:
    optional_runner_count = sum(len(workflow.get("optional_runner_steps", [])) for workflow in workflows)
    nonready_optional_runner_count = 0
    for workflow in workflows:
        for step in workflow.get("optional_runner_steps", []):
            readiness = str(dict(step).get("readiness", ""))
            if readiness not in {"READY", "FOUND", "FOUND_AND_SMOKE_PASSED", "FOUND_BUT_UNTESTED"}:
                nonready_optional_runner_count += 1
    return {
        "blocked_workflow_count": sum(1 for workflow in workflows if workflow.get("status") != "READY_FOR_MANUAL_PLANNING"),
        "complete_workflow_count": sum(1 for workflow in workflows if workflow.get("status") == "READY_FOR_MANUAL_PLANNING"),
        "nonready_optional_runner_count": nonready_optional_runner_count,
        "optional_runner_count": optional_runner_count,
        "workflow_count": len(workflows),
    }


def _development_needs(
    pressure_report: dict[str, object] | None,
    hardening_plan: dict[str, object] | None,
    workflows: list[dict[str, object]],
) -> list[dict[str, object]]:
    needs = []
    if hardening_plan:
        for action in hardening_plan.get("repair_actions", []):
            item = dict(action)
            needs.append(
                {
                    "need": item.get("operator_action", ""),
                    "priority": item.get("priority", "P2"),
                    "source": item.get("source_finding_code", "hardening_action"),
                    "workstream": item.get("workstream", ""),
                }
            )
    elif pressure_report:
        for finding in pressure_report.get("findings", []):
            item = dict(finding)
            needs.append(
                {
                    "need": item.get("next_action", ""),
                    "priority": "P1" if item.get("severity") == "WARNING" else "P2",
                    "source": item.get("code", "pressure_finding"),
                    "workstream": "pressure_repair",
                }
            )
    for workflow in workflows:
        if workflow.get("status") == "BLOCKED_MISSING_REQUIRED_ASSETS":
            needs.append(
                {
                    "need": f"Add required assets for {workflow.get('id')} before this workflow can be repeated.",
                    "priority": "P0",
                    "source": "workflow_blocker",
                    "workstream": "shot_binding",
                }
            )
    return needs


def _operation_loop() -> list[dict[str, object]]:
    return [
        {"order": 1, "command": "python3 seos.py creative scan-assets --root ASSET_ROOT --mode public --output-json REGISTRY_JSON --output-md REPORT_MD"},
        {"order": 2, "command": "python3 seos.py creative production-dashboard --registry-json REGISTRY_JSON --output-md DASHBOARD_MD --output-html DASHBOARD_HTML"},
        {"order": 3, "command": "python3 seos.py creative shot plan --template TEMPLATE --shot-id SHOT_ID --registry-json REGISTRY_JSON"},
        {"order": 4, "command": "python3 seos.py creative pressure-test --registry-json REGISTRY_JSON --template TEMPLATE --shot-id SHOT_ID"},
        {"order": 5, "command": "python3 seos.py creative hardening-plan --pressure-json PRESSURE_JSON"},
        {"order": 6, "command": "Use optional runner commands only after explicit approval and tool-health readiness."},
    ]


def _next_actions(
    workflows: list[dict[str, object]],
    pressure_report: dict[str, object] | None,
    hardening_plan: dict[str, object] | None,
) -> list[str]:
    actions = []
    for workflow in workflows:
        if workflow.get("status") == "BLOCKED_MISSING_REQUIRED_ASSETS":
            actions.append(f"Repair missing required assets for {workflow.get('id')}.")
    if hardening_plan:
        for action in hardening_plan.get("next_actions", []):
            text = str(action)
            if text and text not in actions:
                actions.append(text)
    elif pressure_report:
        for action in pressure_report.get("next_actions", []):
            text = str(action)
            if text and text not in actions:
                actions.append(text)
    actions.append("Run the operation report again after repairs to confirm repeatability improved.")
    actions.append("Keep new development tied to a workflow blocker, pressure finding, hardening action, or real project need.")
    return list(dict.fromkeys(actions))
