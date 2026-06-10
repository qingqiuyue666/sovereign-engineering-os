"""Realistic project pressure testing over creative pipeline reports."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from creative.assets.asset_search import search_asset_library
from creative.common import SCHEMA_VERSION, stable_id, write_json
from creative.reports.local_production_dashboard import build_local_production_dashboard
from creative.shots.shot_planner import build_shot_plan

SEARCH_PROBES: Final[tuple[dict[str, str], ...]] = (
    {"id": "houdini_fx", "query": "houdini-fx-assets", "purpose": "Find Houdini source assets for FX binding."},
    {"id": "vdb_cache", "query": "vdb-cache-assets", "purpose": "Find VDB/cache assets for smoke, dust, or impact elements."},
    {"id": "duplicate_media", "query": "duplicate-video-audio", "purpose": "Expose duplicate video or audio groups before cleanup."},
    {"id": "incomplete_archives", "query": "incomplete-archives", "purpose": "Expose missing archive parts before extraction or shot use."},
    {"id": "empty_directories", "query": "empty-directories", "purpose": "Expose stale or placeholder folders before packaging."},
    {"id": "incomplete_packs", "query": "incomplete-packs", "purpose": "Expose model/material/texture packs that need repair."},
    {"id": "missing_texture_sets", "query": "missing-texture-sets", "purpose": "Expose incomplete texture sets before lookdev."},
)

READY_RUNNER_STATUSES: Final[set[str]] = {
    "READY",
    "FOUND",
    "FOUND_AND_SMOKE_PASSED",
    "FOUND_BUT_UNTESTED",
    "FOUND_BUT_REQUIRES_USER_LAUNCH",
}


def build_real_project_pressure_test(
    asset_report: dict[str, object],
    *,
    template_name: str = "energy-impact",
    shot_id: str = "SHOT_PRESSURE_TEST_001",
    mode: str = "public",
    scenario_id: str = "PROJECT_PRESSURE_ENERGY_IMPACT_FIXTURE",
    scenario_label: str = "Energy impact fixture pressure test",
    tool_health_report: dict[str, object] | None = None,
    adapter_contracts_report: dict[str, object] | None = None,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    """Build a read-only pressure report for a realistic creative task."""
    if mode not in {"public", "local"}:
        raise ValueError("mode must be public or local")

    searches = [_run_search_probe(asset_report, probe, mode=mode) for probe in SEARCH_PROBES]
    dashboard = build_local_production_dashboard(asset_report)
    shot_plan = build_shot_plan(
        asset_report,
        template_name=template_name,
        shot_id=shot_id,
        mode=mode,
        tool_health_report=tool_health_report,
        adapter_contracts_report=adapter_contracts_report,
    )
    findings = _build_findings(
        asset_report=asset_report,
        dashboard=dashboard,
        shot_plan=shot_plan,
        adapter_contracts_report=adapter_contracts_report,
    )
    regression_checks = _build_regression_checks(
        asset_report=asset_report,
        searches=searches,
        shot_plan=shot_plan,
    )
    pressure_status = _pressure_status(findings)
    report = {
        "adapter_contract_summary": shot_plan.get("adapter_contract_summary", {"available": False}),
        "dashboard_summary": _dashboard_summary(dashboard),
        "destructive_actions_performed": False,
        "execution_performed": False,
        "findings": findings,
        "kind": "real_project_pressure_test_v1",
        "mode": mode,
        "next_actions": _next_actions(findings, shot_plan),
        "ok": True,
        "pipeline_steps": _pipeline_steps(
            asset_report=asset_report,
            searches=searches,
            dashboard=dashboard,
            shot_plan=shot_plan,
            tool_health_report=tool_health_report,
            adapter_contracts_report=adapter_contracts_report,
        ),
        "pressure_status": pressure_status,
        "read_only": True,
        "ready_for_execution": False,
        "ready_for_manual_shot_planning": pressure_status != "BLOCKED_NEEDS_ASSET_OR_TEMPLATE_REPAIR",
        "regression_checks": regression_checks,
        "schema_version": SCHEMA_VERSION,
        "scenario": {
            "asset_report_kind": asset_report.get("kind", ""),
            "asset_root": asset_report.get("asset_root", "<asset-root>"),
            "asset_root_name": asset_report.get("asset_root_name", ""),
            "id": scenario_id,
            "label": scenario_label,
            "scenario_digest": stable_id("PRESSURE", scenario_id, template_name, shot_id),
            "shot_id": shot_plan.get("shot_id", shot_id),
            "template": shot_plan.get("summary", {}).get("template", template_name) if isinstance(shot_plan.get("summary"), dict) else template_name,
        },
        "search_probes": searches,
        "shot_plan_summary": _shot_plan_summary(shot_plan),
        "safety": {
            "archive_extraction": False,
            "asset_mutation": False,
            "dcc_or_ai_execution": False,
            "duplicate_deletion": False,
            "requires_separate_approval_for_optional_runners": True,
        },
        "tool_health_summary": shot_plan.get("tool_health_summary", {"available": False}),
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
        output_markdown.write_text(render_real_project_pressure_markdown(report), encoding="utf-8")
    return report


def render_real_project_pressure_markdown(report: dict[str, object]) -> str:
    scenario = dict(report.get("scenario", {}))
    shot_summary = dict(report.get("shot_plan_summary", {}))
    dashboard_summary = dict(report.get("dashboard_summary", {}))
    lines = [
        "# SEOS Real Project Pressure Test",
        "",
        f"- Scenario: `{scenario.get('id')}`",
        f"- Shot: `{scenario.get('shot_id')}`",
        f"- Template: `{scenario.get('template')}`",
        f"- Pressure status: `{report.get('pressure_status')}`",
        f"- Ready for manual shot planning: `{report.get('ready_for_manual_shot_planning')}`",
        f"- Ready for execution: `{report.get('ready_for_execution')}`",
        "",
        "## Asset And Shot Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| total_assets | {dashboard_summary.get('total_assets', 0)} |",
        f"| duplicate_group_count | {dashboard_summary.get('duplicate_group_count', 0)} |",
        f"| archive_warning_count | {dashboard_summary.get('archive_warning_count', 0)} |",
        f"| empty_directory_count | {dashboard_summary.get('empty_directory_count', 0)} |",
        f"| missing_required_count | {shot_summary.get('missing_required_count', 0)} |",
        f"| total_candidate_count | {shot_summary.get('total_candidate_count', 0)} |",
        "",
        "## Search Probes",
        "",
        "| Probe | Result Type | Count | Purpose |",
        "| --- | --- | ---: | --- |",
    ]
    for probe in report.get("search_probes", []):
        item = dict(probe)
        lines.append(f"| `{item.get('query')}` | `{item.get('result_type')}` | {item.get('result_count')} | {item.get('purpose')} |")

    lines.extend(["", "## Findings", ""])
    findings = list(report.get("findings", []))
    if findings:
        for finding in findings:
            item = dict(finding)
            lines.append(f"- `{item.get('severity')}` `{item.get('code')}`: {item.get('message')}")
    else:
        lines.append("- No pressure findings were emitted.")

    lines.extend(["", "## Regression Checks", "", "| Check | Passed | Detail |", "| --- | --- | --- |"])
    for check in report.get("regression_checks", []):
        item = dict(check)
        lines.append(f"| `{item.get('id')}` | `{item.get('passed')}` | {item.get('detail')} |")

    lines.extend(["", "## Next Actions", ""])
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This pressure test is read-only.",
            "- It does not delete duplicates, extract archives, mutate assets, launch DCC tools, or submit AI jobs.",
            "- Optional local runners require separate explicit approval.",
            "",
        ]
    )
    return "\n".join(lines)


def _run_search_probe(asset_report: dict[str, object], probe: dict[str, str], *, mode: str) -> dict[str, object]:
    result = search_asset_library(asset_report, query=probe["query"], mode=mode, limit=5)
    return {
        "id": probe["id"],
        "items": result.get("items", []),
        "next_actions": result.get("next_actions", []),
        "purpose": probe["purpose"],
        "query": result.get("query", probe["query"]),
        "result_count": result.get("result_count", 0),
        "result_type": result.get("result_type", ""),
        "returned_count": result.get("returned_count", 0),
    }


def _dashboard_summary(dashboard: dict[str, object]) -> dict[str, object]:
    summary = dict(dashboard.get("summary", {}))
    return {
        "archive_warning_count": int(summary.get("archive_warning_count", 0)),
        "duplicate_group_count": int(summary.get("duplicate_group_count", 0)),
        "empty_directory_count": int(summary.get("empty_directory_count", 0)),
        "incomplete_texture_set_count": int(summary.get("incomplete_texture_set_count", 0)),
        "likely_incomplete_pack_count": int(summary.get("likely_incomplete_pack_count", 0)),
        "total_assets": int(summary.get("total_assets", 0)),
        "total_size_bytes": int(summary.get("total_size_bytes", 0)),
    }


def _shot_plan_summary(shot_plan: dict[str, object]) -> dict[str, object]:
    summary = dict(shot_plan.get("summary", {}))
    return {
        "complete": bool(shot_plan.get("complete")),
        "missing_required_count": int(summary.get("missing_required_count", 0)),
        "optional_ready_count": int(summary.get("optional_ready_count", 0)),
        "required_ready_count": int(summary.get("required_ready_count", 0)),
        "template": summary.get("template", ""),
        "template_label": summary.get("template_label", ""),
        "total_candidate_count": int(summary.get("total_candidate_count", 0)),
    }


def _pipeline_steps(
    *,
    asset_report: dict[str, object],
    searches: list[dict[str, object]],
    dashboard: dict[str, object],
    shot_plan: dict[str, object],
    tool_health_report: dict[str, object] | None,
    adapter_contracts_report: dict[str, object] | None,
) -> list[dict[str, object]]:
    return [
        {
            "id": "asset_scan",
            "status": "COMPLETED",
            "summary": _dashboard_summary({"summary": asset_report.get("summary", {})}),
        },
        {
            "id": "asset_search_probes",
            "status": "COMPLETED",
            "probe_count": len(searches),
            "non_empty_probe_count": sum(1 for probe in searches if int(probe.get("result_count", 0)) > 0),
        },
        {
            "id": "production_dashboard",
            "status": "COMPLETED" if dashboard.get("ok") else "FAILED",
            "recommended_cleanup_action_count": len(dashboard.get("recommended_cleanup_actions", [])),
        },
        {
            "id": "shot_planner",
            "status": "COMPLETE" if shot_plan.get("complete") else "INCOMPLETE",
            "summary": _shot_plan_summary(shot_plan),
        },
        {
            "id": "local_tool_health",
            "status": "REPORT_LOADED" if tool_health_report else "NOT_PROVIDED",
        },
        {
            "id": "optional_adapter_contracts",
            "status": "REPORT_LOADED" if adapter_contracts_report else "NOT_PROVIDED",
        },
        {
            "id": "local_execution",
            "status": "NOT_RUN_APPROVAL_REQUIRED",
        },
    ]


def _build_findings(
    *,
    asset_report: dict[str, object],
    dashboard: dict[str, object],
    shot_plan: dict[str, object],
    adapter_contracts_report: dict[str, object] | None,
) -> list[dict[str, object]]:
    summary = _dashboard_summary(dashboard)
    findings: list[dict[str, object]] = []
    if summary["total_assets"] == 0:
        findings.append(_finding("ASSET_SCAN_EMPTY", "BLOCKER", "No assets were found for the scenario.", "Point the pressure test at a real asset root or fixture with production assets."))
    if summary["duplicate_group_count"]:
        findings.append(_finding("DUPLICATES_REQUIRE_REVIEW", "WARNING", "Duplicate groups were detected and need human cleanup decisions.", "Review duplicate groups manually before deleting or packaging anything."))
    if summary["archive_warning_count"]:
        findings.append(_finding("ARCHIVE_PART_MISSING", "WARNING", "Missing archive parts were detected.", "Restore missing archive parts before extraction or production use."))
    if summary["empty_directory_count"]:
        findings.append(_finding("EMPTY_DIRECTORIES_PRESENT", "INFO", "Empty directories were detected.", "Decide whether empty directories are intentional placeholders or stale clutter."))
    if summary["incomplete_texture_set_count"]:
        findings.append(_finding("INCOMPLETE_TEXTURE_SETS", "WARNING", "Incomplete texture sets were detected.", "Fill missing texture maps before lookdev binding."))
    if summary["likely_incomplete_pack_count"]:
        findings.append(_finding("INCOMPLETE_PRODUCTION_PACKS", "WARNING", "Likely incomplete model/material/texture packs were detected.", "Resolve incomplete packs before shot planning."))
    shot_summary = _shot_plan_summary(shot_plan)
    if not shot_summary["complete"]:
        findings.append(_finding("SHOT_REQUIRED_ASSETS_MISSING", "BLOCKER", "The shot plan is missing required assets.", "Add or relink required shot assets, then rerun the pressure test."))
    for runner in dict(shot_plan.get("execution_plan", {})).get("optional_runner_steps", []):
        item = dict(runner)
        readiness = str(item.get("readiness", ""))
        if readiness and readiness not in READY_RUNNER_STATUSES:
            findings.append(
                _finding(
                    "LOCAL_RUNNER_NOT_READY",
                    "WARNING",
                    f"{item.get('label')} is not ready: {readiness}.",
                    "Resolve local tool health before using that optional runner.",
                    evidence={"runner_id": item.get("runner_id", ""), "readiness": readiness},
                )
            )
    contract_only = _contract_only_adapters(adapter_contracts_report)
    if contract_only:
        findings.append(
            _finding(
                "ADAPTERS_CONTRACT_ONLY",
                "INFO",
                "Some optional adapters are contract-only and cannot execute from this pressure test.",
                "Use adapter-specific local proof PRs before claiming execution support.",
                evidence={"adapters": contract_only},
            )
        )
    return findings


def _contract_only_adapters(adapter_contracts_report: dict[str, object] | None) -> list[str]:
    if not adapter_contracts_report:
        return []
    names = []
    for adapter in adapter_contracts_report.get("adapters", []):
        item = dict(adapter)
        if item.get("execution_support") == "CONTRACT_ONLY" or item.get("supports_execute") is False:
            names.append(str(item.get("adapter", "")))
    return [name for name in names if name]


def _finding(
    code: str,
    severity: str,
    message: str,
    next_action: str,
    *,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "code": code,
        "evidence": evidence or {},
        "message": message,
        "next_action": next_action,
        "severity": severity,
    }


def _build_regression_checks(
    *,
    asset_report: dict[str, object],
    searches: list[dict[str, object]],
    shot_plan: dict[str, object],
) -> list[dict[str, object]]:
    summary = dict(asset_report.get("summary", {}))
    search_results_are_structured = all("result_count" in probe and "result_type" in probe for probe in searches)
    optional_runners = dict(shot_plan.get("execution_plan", {})).get("optional_runner_steps", [])
    return [
        {
            "id": "asset_scan_has_assets",
            "passed": int(summary.get("total_assets", 0)) > 0,
            "detail": "The scenario has at least one scanned asset.",
        },
        {
            "id": "search_probes_are_structured",
            "passed": search_results_are_structured,
            "detail": "All practical asset-search probes returned structured counts.",
        },
        {
            "id": "shot_plan_generated",
            "passed": bool(shot_plan.get("ok")),
            "detail": "The shot planner returned a report.",
        },
        {
            "id": "shot_plan_complete",
            "passed": bool(shot_plan.get("complete")),
            "detail": "Required shot assets are present for the selected template.",
        },
        {
            "id": "optional_runners_remain_approval_gated",
            "passed": all(dict(step).get("requires_approval") is True for step in optional_runners),
            "detail": "Optional local runners are represented as approval-gated command templates.",
        },
        {
            "id": "local_execution_not_performed",
            "passed": True,
            "detail": "The pressure test did not launch DCC tools or submit AI jobs.",
        },
    ]


def _pressure_status(findings: list[dict[str, object]]) -> str:
    severities = {str(finding.get("severity")) for finding in findings}
    if "BLOCKER" in severities:
        return "BLOCKED_NEEDS_ASSET_OR_TEMPLATE_REPAIR"
    if "WARNING" in severities:
        return "USABLE_WITH_MANUAL_REPAIR"
    return "READY_FOR_MANUAL_SHOT_PLANNING"


def _next_actions(findings: list[dict[str, object]], shot_plan: dict[str, object]) -> list[str]:
    actions = []
    for finding in findings:
        next_action = str(finding.get("next_action", ""))
        if next_action == "Resolve local tool health before using that optional runner.":
            continue
        if next_action and next_action not in actions:
            actions.append(next_action)
    for action in shot_plan.get("next_actions", []):
        text = str(action)
        if "final creative approval" in text or "final production approval" in text:
            continue
        if text and text not in actions:
            actions.append(text)
    if not actions:
        actions.append("Create the shot workspace and bind the selected candidate assets.")
    final_action = "Keep final creative and production approval human-owned."
    if final_action not in actions:
        actions.append(final_action)
    return actions
