"""Template-driven shot planning over the local asset library."""

from __future__ import annotations

from pathlib import Path
from typing import Final
import json

from creative.common import SCHEMA_VERSION, stable_id, write_json

MAX_CANDIDATES_PER_REQUIREMENT: Final[int] = 8

SHOT_TEMPLATES: Final[dict[str, dict[str, object]]] = {
    "energy_impact": {
        "label": "Energy Impact",
        "summary": "A practical VFX impact shot with plate, Houdini/cache, lookdev, comp, and editorial handoff.",
        "required": [
            {"id": "plate", "label": "source plate", "categories": ["video"], "min_count": 1},
            {"id": "fx_source", "label": "Houdini or VDB effect source", "categories": ["houdini", "vdb_cache"], "min_count": 1},
            {"id": "lookdev", "label": "material or texture lookdev", "categories": ["materials", "textures", "hdri"], "min_count": 2},
            {"id": "comp", "label": "comp or finishing surface", "categories": ["after_effects", "davinci"], "min_count": 1},
        ],
        "optional": [
            {"id": "audio", "label": "impact sound", "categories": ["audio"], "min_count": 1},
            {"id": "ai_repair", "label": "ComfyUI repair workflow", "categories": ["comfyui"], "min_count": 1},
        ],
        "manual_steps": [
            "Choose the plate and lock frame range.",
            "Bind the Houdini/VDB effect source to the shot workspace.",
            "Assign lookdev maps and HDRI reference.",
            "Create comp handoff notes and editorial delivery checklist.",
        ],
        "optional_runner_steps": ["houdini_hython_smoke", "comfyui_workflow_smoke"],
    },
    "smoke_dust": {
        "label": "Smoke / Dust",
        "summary": "A local smoke or dust element shot focused on cache review and comp readiness.",
        "required": [
            {"id": "plate", "label": "source plate", "categories": ["video"], "min_count": 1},
            {"id": "cache", "label": "VDB/cache element", "categories": ["vdb_cache"], "min_count": 1},
            {"id": "lookdev", "label": "texture/material support", "categories": ["textures", "materials", "hdri"], "min_count": 1},
        ],
        "optional": [
            {"id": "dcc_scene", "label": "Blender or Houdini staging scene", "categories": ["blender", "houdini"], "min_count": 1},
            {"id": "comp", "label": "After Effects comp", "categories": ["after_effects"], "min_count": 1},
        ],
        "manual_steps": [
            "Confirm cache scale, density, and frame range.",
            "Check plate color management and comp pull requirements.",
            "Package cache and lookdev notes for the compositor.",
        ],
        "optional_runner_steps": ["houdini_hython_smoke"],
    },
    "portal_lightning": {
        "label": "Portal / Lightning",
        "summary": "A stylized portal or lightning shot with FX source, glow lookdev, and comp handoff.",
        "required": [
            {"id": "plate", "label": "source plate", "categories": ["video"], "min_count": 1},
            {"id": "fx_source", "label": "Houdini or DCC effect source", "categories": ["houdini", "blender"], "min_count": 1},
            {"id": "lookdev", "label": "energy material/texture support", "categories": ["materials", "textures", "hdri"], "min_count": 2},
            {"id": "comp", "label": "comp surface", "categories": ["after_effects"], "min_count": 1},
        ],
        "optional": [
            {"id": "ai_repair", "label": "ComfyUI repair workflow", "categories": ["comfyui"], "min_count": 1},
            {"id": "editorial", "label": "DaVinci editorial handoff", "categories": ["davinci"], "min_count": 1},
        ],
        "manual_steps": [
            "Select plate and effect source.",
            "Bind energy lookdev maps and HDRI reference.",
            "Define glow, light wrap, and holdout requirements for comp.",
        ],
        "optional_runner_steps": ["houdini_hython_smoke", "comfyui_workflow_smoke"],
    },
    "editorial_handoff": {
        "label": "Editorial Handoff",
        "summary": "A practical editorial package with plates, audio, LUTs, and delivery notes.",
        "required": [
            {"id": "media", "label": "source media", "categories": ["video"], "min_count": 1},
            {"id": "audio", "label": "audio element", "categories": ["audio"], "min_count": 1},
            {"id": "lut", "label": "show LUT", "categories": ["lut"], "min_count": 1},
            {"id": "editorial", "label": "DaVinci or comp handoff", "categories": ["davinci", "after_effects"], "min_count": 1},
        ],
        "optional": [
            {"id": "script", "label": "handoff script", "categories": ["scripts"], "min_count": 1},
        ],
        "manual_steps": [
            "Collect media, audio, and LUT references.",
            "Write delivery notes for timeline, handles, color, and codec.",
            "Package digest-only evidence for the handoff report.",
        ],
        "optional_runner_steps": [],
    },
}

RUNNER_COMMANDS: Final[dict[str, dict[str, object]]] = {
    "houdini_hython_smoke": {
        "label": "Houdini hython smoke",
        "requires_approval": True,
        "command": "python3 seos.py creative houdini-smoke --approve-local-execution --approval-id APPROVAL_ID",
        "purpose": "Verify local hython before any Houdini render/sim work.",
    },
    "comfyui_workflow_smoke": {
        "label": "ComfyUI workflow smoke",
        "requires_approval": True,
        "command": "python3 seos.py creative comfyui-smoke --approve-local-execution --approval-id APPROVAL_ID",
        "purpose": "Verify local ComfyUI service before any AI repair/generation work.",
    },
}


def list_shot_templates() -> dict[str, object]:
    return {
        "kind": "shot_templates_v1",
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "templates": [
            {
                "label": template["label"],
                "required_count": len(template.get("required", [])),
                "summary": template["summary"],
                "template": key,
            }
            for key, template in SHOT_TEMPLATES.items()
        ],
    }


def build_shot_plan(
    asset_report: dict[str, object],
    *,
    template_name: str,
    shot_id: str,
    mode: str = "public",
    tool_health_report: dict[str, object] | None = None,
    adapter_contracts_report: dict[str, object] | None = None,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    if mode not in {"public", "local"}:
        raise ValueError("mode must be public or local")
    template_key = _normalize_template_name(template_name)
    if template_key not in SHOT_TEMPLATES:
        raise ValueError(f"unknown shot template: {template_name}")
    resolved_shot_id = shot_id if shot_id.startswith("SHOT_") else stable_id("SHOT", shot_id)
    template = SHOT_TEMPLATES[template_key]
    assets = [dict(asset) for asset in asset_report.get("assets", []) if isinstance(asset, dict)]
    required = _requirements(template.get("required", []), assets, required=True)
    optional = _requirements(template.get("optional", []), assets, required=False)
    missing_required = [item for item in required if item["status"] != "READY"]
    runner_plan = _runner_plan(
        template.get("optional_runner_steps", []),
        tool_health_report=tool_health_report,
        adapter_contracts_report=adapter_contracts_report,
    )
    plan = {
        "adapter_contract_summary": _adapter_contract_summary(adapter_contracts_report),
        "asset_report_kind": asset_report.get("kind", ""),
        "complete": not missing_required,
        "destructive_actions_performed": False,
        "execution_plan": {
            "manual_steps": list(template.get("manual_steps", [])),
            "optional_runner_steps": runner_plan,
            "requires_human_approval_before_execution": True,
        },
        "kind": "shot_plan_v1",
        "mode": mode,
        "next_actions": _next_actions(missing_required, runner_plan),
        "ok": True,
        "read_only": True,
        "required_assets": required,
        "optional_assets": optional,
        "schema_version": SCHEMA_VERSION,
        "shot_id": resolved_shot_id,
        "summary": {
            "missing_required_count": len(missing_required),
            "optional_ready_count": sum(1 for item in optional if item["status"] == "READY"),
            "required_ready_count": sum(1 for item in required if item["status"] == "READY"),
            "template": template_key,
            "template_label": template["label"],
            "total_candidate_count": sum(len(item["candidates"]) for item in required + optional),
        },
        "template": {
            "name": template_key,
            "label": template["label"],
            "summary": template["summary"],
        },
        "tool_health_summary": _tool_health_summary(tool_health_report),
    }
    outputs: dict[str, str] = {}
    if output_json is not None:
        write_json(output_json, plan)
        outputs["json"] = output_json.as_posix()
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_shot_plan_markdown(plan), encoding="utf-8")
        outputs["markdown"] = output_markdown.as_posix()
    plan["outputs"] = outputs
    return plan


def render_shot_plan_markdown(plan: dict[str, object]) -> str:
    template = dict(plan.get("template", {}))
    summary = dict(plan.get("summary", {}))
    lines = [
        f"# SEOS Shot Plan: {template.get('label')}",
        "",
        f"- Shot: `{plan.get('shot_id')}`",
        f"- Template: `{template.get('name')}`",
        f"- Complete: `{plan.get('complete')}`",
        f"- Read-only: `{plan.get('read_only')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "required_ready_count",
        "missing_required_count",
        "optional_ready_count",
        "total_candidate_count",
    ):
        lines.append(f"| {key} | {summary.get(key, 0)} |")

    lines.extend(["", "## Required Assets", "", "| Requirement | Status | Candidates |", "| --- | --- | ---: |"])
    for requirement in plan.get("required_assets", []):
        item = dict(requirement)
        lines.append(f"| {item.get('label')} | `{item.get('status')}` | {len(item.get('candidates', []))} |")

    lines.extend(["", "## Optional Assets", "", "| Requirement | Status | Candidates |", "| --- | --- | ---: |"])
    for requirement in plan.get("optional_assets", []):
        item = dict(requirement)
        lines.append(f"| {item.get('label')} | `{item.get('status')}` | {len(item.get('candidates', []))} |")

    lines.extend(["", "## Manual Steps", ""])
    execution = dict(plan.get("execution_plan", {}))
    for index, step in enumerate(execution.get("manual_steps", []), start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", "## Optional Runner Steps", ""])
    runner_steps = execution.get("optional_runner_steps", [])
    if runner_steps:
        for step in runner_steps:
            item = dict(step)
            lines.append(
                f"- {item.get('label')}: `{item.get('readiness')}`. "
                f"Requires approval: `{item.get('requires_approval')}`."
            )
    else:
        lines.append("- No optional runner steps are needed for this template.")

    lines.extend(["", "## Next Actions", ""])
    for action in plan.get("next_actions", []):
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def _requirements(rows: object, assets: list[dict[str, object]], *, required: bool) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for row in rows if isinstance(rows, list) else []:
        spec = dict(row)
        categories = [str(category) for category in spec.get("categories", [])]
        candidates = _candidate_assets(assets, categories)
        min_count = int(spec.get("min_count", 1))
        status = "READY" if len(candidates) >= min_count else ("PARTIAL" if candidates else "MISSING")
        result.append(
            {
                "categories": categories,
                "candidates": candidates[:MAX_CANDIDATES_PER_REQUIREMENT],
                "id": spec.get("id", ""),
                "label": spec.get("label", ""),
                "min_count": min_count,
                "required": required,
                "status": status,
            }
        )
    return result


def _candidate_assets(assets: list[dict[str, object]], categories: list[str]) -> list[dict[str, object]]:
    matched: list[dict[str, object]] = []
    category_set = set(categories)
    for asset in assets:
        category = str(asset.get("category", ""))
        likely_tool = str(asset.get("likely_tool", ""))
        if category not in category_set and likely_tool not in category_set:
            continue
        matched.append(
            {
                "category": category,
                "filename": asset.get("filename", ""),
                "id": asset.get("id", ""),
                "likely_tool": likely_tool,
                "relative_path": asset.get("relative_path", ""),
                "size_bytes": asset.get("size_bytes", 0),
            }
        )
    return matched


def _runner_plan(
    runner_ids: object,
    *,
    tool_health_report: dict[str, object] | None,
    adapter_contracts_report: dict[str, object] | None,
) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    tool_statuses = _tool_statuses(tool_health_report)
    contract_statuses = _adapter_statuses(adapter_contracts_report)
    for runner_id in list(runner_ids) if isinstance(runner_ids, list) else []:
        runner = dict(RUNNER_COMMANDS[str(runner_id)])
        tool = "houdini" if runner_id == "houdini_hython_smoke" else "comfyui"
        readiness = _runner_readiness(tool, tool_statuses.get(tool, ""), contract_statuses.get(tool, ""))
        steps.append(
            {
                "command_template": runner["command"],
                "label": runner["label"],
                "purpose": runner["purpose"],
                "readiness": readiness,
                "requires_approval": runner["requires_approval"],
                "runner_id": runner_id,
                "tool_status": tool_statuses.get(tool, ""),
            }
        )
    return steps


def _runner_readiness(tool: str, tool_status: str, contract_status: str) -> str:
    if tool in {"houdini", "comfyui"} and tool_status in {"FOUND_BUT_UNTESTED", "FOUND_BUT_REQUIRES_USER_LAUNCH", "FOUND_AND_SMOKE_PASSED"}:
        return "LOCAL_PREFLIGHT_RECOMMENDED"
    if contract_status:
        return f"CONTRACT_STATUS_{contract_status}"
    if tool_status in {"CONFIG_REQUIRED", "NOT_FOUND"}:
        return tool_status
    return "CHECK_TOOL_HEALTH_FIRST"


def _tool_statuses(tool_health_report: dict[str, object] | None) -> dict[str, str]:
    if not isinstance(tool_health_report, dict):
        return {}
    if isinstance(tool_health_report.get("software"), dict):
        return {
            str(name): str(dict(entry).get("status", ""))
            for name, entry in dict(tool_health_report.get("software", {})).items()
            if isinstance(entry, dict)
        }
    rows = tool_health_report.get("tool_health")
    statuses: dict[str, str] = {}
    for row in rows if isinstance(rows, list) else []:
        item = dict(row)
        if item.get("tool"):
            statuses[str(item["tool"])] = str(item.get("status", ""))
    return statuses


def _adapter_statuses(adapter_contracts_report: dict[str, object] | None) -> dict[str, str]:
    if not isinstance(adapter_contracts_report, dict):
        return {}
    statuses: dict[str, str] = {}
    for row in adapter_contracts_report.get("adapters", []):
        if not isinstance(row, dict):
            continue
        statuses[str(row.get("adapter", ""))] = str(row.get("contract_status", ""))
    return statuses


def _tool_health_summary(tool_health_report: dict[str, object] | None) -> dict[str, object]:
    statuses = _tool_statuses(tool_health_report)
    return {
        "available": bool(statuses),
        "comfyui": statuses.get("comfyui", ""),
        "houdini": statuses.get("houdini", ""),
    }


def _adapter_contract_summary(adapter_contracts_report: dict[str, object] | None) -> dict[str, object]:
    statuses = _adapter_statuses(adapter_contracts_report)
    return {
        "available": bool(statuses),
        "blender": statuses.get("blender", ""),
        "after_effects": statuses.get("after_effects", ""),
        "davinci": statuses.get("davinci", ""),
        "unreal": statuses.get("unreal", ""),
        "zbrush": statuses.get("zbrush", ""),
    }


def _next_actions(missing_required: list[dict[str, object]], runner_plan: list[dict[str, object]]) -> list[str]:
    actions: list[str] = []
    for item in missing_required:
        categories = ", ".join(str(category) for category in item.get("categories", []))
        actions.append(f"Add or locate {item.get('label')} assets for categories: {categories}.")
    if not actions:
        actions.append("Create the shot workspace and bind the selected candidate assets.")
    for step in runner_plan:
        if step.get("readiness") == "LOCAL_PREFLIGHT_RECOMMENDED":
            actions.append(f"Run approved {step.get('label')} before any real execution step.")
        elif step.get("readiness") in {"CONFIG_REQUIRED", "NOT_FOUND"}:
            actions.append(f"Resolve {step.get('label')} tool health before using that optional runner.")
    actions.append("Keep final creative approval human-owned.")
    return actions


def _normalize_template_name(value: str) -> str:
    return value.strip().lower().replace("-", "_")
