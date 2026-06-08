"""Local tool-health dashboard for the SEOS creative operator."""

from __future__ import annotations

from html import escape
from importlib import metadata as importlib_metadata
from importlib import util as importlib_util
from pathlib import Path
from typing import Sequence
import json
import re
import tomllib

from creative.common import repo_root, sanitize_path
from creative.software.doctor import run_doctor

TOOL_ORDER = (
    "python",
    "python_dependencies",
    "macos",
    "apple_silicon",
    "git",
    "ffmpeg",
    "houdini",
    "comfyui",
    "blender",
    "after_effects",
    "davinci",
    "unreal",
    "zbrush",
)

TOOL_LABELS = {
    "python": "Python runtime",
    "python_dependencies": "Python dependencies",
    "macos": "macOS host",
    "apple_silicon": "Apple Silicon",
    "git": "Git CLI",
    "ffmpeg": "FFmpeg CLI",
    "houdini": "Houdini / hython",
    "comfyui": "ComfyUI",
    "blender": "Blender",
    "after_effects": "After Effects",
    "davinci": "DaVinci Resolve",
    "unreal": "Unreal Engine",
    "zbrush": "ZBrush",
}

PROPRIETARY_TOOLS = {"houdini", "blender", "after_effects", "davinci", "unreal", "zbrush"}
READY_STATUSES = {"FOUND_AND_SMOKE_PASSED", "FOUND_BUT_UNTESTED", "FOUND_BUT_REQUIRES_USER_LAUNCH"}
PROBLEM_STATUSES = {"NOT_FOUND", "CONFIG_REQUIRED", "LICENSE_BLOCKED", "UNKNOWN"}


def build_local_tool_health_dashboard(
    doctor_report: dict[str, object] | None = None,
    *,
    mode: str = "public",
    output_json: Path | None = None,
    output_markdown: Path | None = None,
    output_html: Path | None = None,
    dependency_names: Sequence[str] | None = None,
) -> dict[str, object]:
    """Build a truthful local tool-health dashboard without launching DCC tools."""

    if mode not in {"public", "local"}:
        raise ValueError("mode must be 'public' or 'local'")

    report = dict(doctor_report if doctor_report is not None else run_doctor())
    software = dict(report.get("software", {}))
    dependency_health = _dependency_health_from_report(report, software)
    if dependency_health is None:
        dependency_health = _detect_python_dependencies(dependency_names)
    software["python_dependencies"] = dependency_health["tool_entry"]

    rows = [_tool_row(tool, dict(software.get(tool, {})), mode=mode) for tool in _ordered_tools(software)]
    summary = _summary(rows)
    dashboard = {
        "ok": True,
        "kind": "local_tool_health_dashboard_v1",
        "mode": mode,
        "read_only": True,
        "destructive_actions_performed": bool(report.get("destructive_actions_performed", False)),
        "dcc_or_ai_tools_launched": False,
        "proprietary_tools_required_for_default_ci": [],
        "summary": summary,
        "tool_health": rows,
        "python_dependency_details": dependency_health["dependencies"],
        "warnings": list(report.get("warnings", [])),
        "next_actions": _next_actions(rows),
        "safety": {
            "dcc_execution": False,
            "ai_service_calls": False,
            "license_checkout": False,
            "filesystem_mutation": False,
            "default_ci_requires_proprietary_tools": False,
        },
    }

    outputs: dict[str, str] = {}
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(dashboard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        outputs["json"] = output_json.as_posix()
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_local_tool_health_dashboard_markdown(dashboard), encoding="utf-8")
        outputs["markdown"] = output_markdown.as_posix()
    if output_html is not None:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(render_local_tool_health_dashboard_html(dashboard), encoding="utf-8")
        outputs["html"] = output_html.as_posix()
    dashboard["outputs"] = outputs
    return dashboard


def render_local_tool_health_dashboard_markdown(dashboard: dict[str, object]) -> str:
    summary = dict(dashboard.get("summary", {}))
    lines = [
        "# SEOS Local Tool Health Dashboard",
        "",
        f"- Mode: `{dashboard.get('mode')}`",
        f"- Read-only: `{dashboard.get('read_only')}`",
        f"- DCC or AI tools launched: `{dashboard.get('dcc_or_ai_tools_launched')}`",
        f"- Proprietary tools required for default CI: `{dashboard.get('proprietary_tools_required_for_default_ci')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "tool_count",
        "ready_or_detected_count",
        "smoke_passed_count",
        "available_but_untested_count",
        "requires_user_launch_count",
        "config_required_count",
        "missing_count",
        "blocked_count",
    ):
        lines.append(f"| {key} | {summary.get(key, 0)} |")

    lines.extend(
        [
            "",
            "## Tool Health",
            "",
            "| Tool | Status | Version | Configured path | Smoke capability | Next fix action |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in dashboard.get("tool_health", []):
        item = dict(row)
        lines.append(
            "| "
            f"{item.get('label')} | "
            f"`{item.get('status')}` | "
            f"{_markdown_cell(item.get('version'))} | "
            f"{_markdown_cell(item.get('configured_path'))} | "
            f"{item.get('smoke_capability')} | "
            f"{item.get('next_fix_action')} |"
        )

    lines.extend(["", "## Python Dependency Details", ""])
    details = list(dashboard.get("python_dependency_details", []))
    if details:
        lines.extend(["| Package | Status | Version |", "| --- | --- | --- |"])
        for detail in details:
            item = dict(detail)
            lines.append(f"| `{item.get('name')}` | `{item.get('status')}` | {_markdown_cell(item.get('version'))} |")
    else:
        lines.append("- No Python dependencies were listed in the project metadata.")

    lines.extend(["", "## Next Actions", ""])
    for action in dashboard.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Tool-health dashboard generation does not launch DCC or AI tools.",
            "- Tool-health dashboard generation does not check out licenses.",
            "- Missing tools remain unavailable evidence, not failures hidden as success.",
            "- Default CI does not require Houdini, Blender, Unreal, DaVinci Resolve, After Effects, ZBrush, or ComfyUI.",
            "",
        ]
    )
    return "\n".join(lines)


def render_local_tool_health_dashboard_html(dashboard: dict[str, object]) -> str:
    markdown = render_local_tool_health_dashboard_markdown(dashboard)
    body = "\n".join(f"<p>{escape(line)}</p>" if line else "" for line in markdown.splitlines())
    payload = escape(json.dumps(dashboard.get("summary", {}), sort_keys=True))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SEOS Local Tool Health Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 1100px; line-height: 1.45; }}
    p {{ margin: .25rem 0; }}
    code {{ background: #f1f3f5; padding: .1rem .25rem; }}
  </style>
</head>
<body>
  {body}
  <script type="application/json" id="seos-tool-health-summary">{payload}</script>
</body>
</html>
"""


def _ordered_tools(software: dict[str, object]) -> list[str]:
    ordered = [tool for tool in TOOL_ORDER if tool in software]
    extras = sorted(tool for tool in software if tool not in set(TOOL_ORDER))
    return ordered + extras


def _tool_row(tool: str, entry: dict[str, object], *, mode: str) -> dict[str, object]:
    status = str(entry.get("status") or "UNKNOWN")
    return {
        "tool": tool,
        "label": TOOL_LABELS.get(tool, tool.replace("_", " ").title()),
        "status": status,
        "available": status in READY_STATUSES,
        "version": str(entry.get("version") or ""),
        "configured_path": _configured_path(entry.get("path"), mode=mode),
        "smoke_capability": _smoke_capability(status),
        "next_fix_action": _next_fix_action(tool, status),
        "default_ci_requirement": _default_ci_requirement(tool),
        "proprietary": tool in PROPRIETARY_TOOLS,
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    statuses = [str(row.get("status")) for row in rows]
    return {
        "tool_count": len(rows),
        "ready_or_detected_count": sum(1 for status in statuses if status in READY_STATUSES),
        "smoke_passed_count": statuses.count("FOUND_AND_SMOKE_PASSED"),
        "available_but_untested_count": statuses.count("FOUND_BUT_UNTESTED"),
        "requires_user_launch_count": statuses.count("FOUND_BUT_REQUIRES_USER_LAUNCH"),
        "config_required_count": statuses.count("CONFIG_REQUIRED"),
        "missing_count": statuses.count("NOT_FOUND"),
        "blocked_count": sum(1 for status in statuses if status in PROBLEM_STATUSES),
    }


def _detect_python_dependencies(dependency_names: Sequence[str] | None) -> dict[str, object]:
    names = list(dependency_names) if dependency_names is not None else _project_dependency_names()
    rows = []
    for name in names:
        module_name = _dependency_module_name(name)
        found = importlib_util.find_spec(module_name) is not None
        rows.append(
            {
                "name": module_name,
                "status": "FOUND" if found else "NOT_FOUND",
                "version": _dependency_version(module_name) if found else "",
            }
        )
    missing = [row["name"] for row in rows if row.get("status") != "FOUND"]
    status = "FOUND_AND_SMOKE_PASSED" if not missing else "CONFIG_REQUIRED"
    version = f"present {len(rows) - len(missing)}/{len(rows)}" if rows else "no project dependencies listed"
    return {
        "tool_entry": {
            "status": status,
            "version": version,
            "path": "",
            "missing_dependencies": missing,
        },
        "dependencies": rows,
    }


def _dependency_health_from_report(
    report: dict[str, object],
    software: dict[str, object],
) -> dict[str, object] | None:
    entry = software.get("python_dependencies")
    details = report.get("python_dependency_details")
    if not isinstance(entry, dict) or not isinstance(details, list):
        return None
    return {"tool_entry": dict(entry), "dependencies": list(details)}


def _project_dependency_names() -> list[str]:
    path = repo_root() / "pyproject.toml"
    if not path.exists():
        return []
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies = payload.get("project", {}).get("dependencies", [])
    return [_dependency_module_name(str(item)) for item in dependencies]


def _dependency_module_name(requirement: str) -> str:
    name = re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()
    return name.replace("-", "_")


def _dependency_version(module_name: str) -> str:
    candidates = [module_name, module_name.replace("_", "-")]
    for candidate in candidates:
        try:
            return importlib_metadata.version(candidate)
        except importlib_metadata.PackageNotFoundError:
            continue
    return "importable"


def _configured_path(value: object, *, mode: str) -> str:
    if not value:
        return ""
    return str(value) if mode == "local" else sanitize_path(value)


def _smoke_capability(status: str) -> str:
    if status == "FOUND_AND_SMOKE_PASSED":
        return "SMOKE_PASSED_BY_DISCOVERY"
    if status == "FOUND_BUT_UNTESTED":
        return "PATH_DETECTED_NO_SMOKE_RUN"
    if status == "FOUND_BUT_REQUIRES_USER_LAUNCH":
        return "CONFIG_DETECTED_APP_NOT_LAUNCHED"
    if status == "CONFIG_REQUIRED":
        return "NOT_RUN_CONFIG_REQUIRED"
    if status == "NOT_FOUND":
        return "NOT_RUN_ENV_NOT_FOUND"
    if status == "LICENSE_BLOCKED":
        return "NOT_RUN_LICENSE_BLOCKED"
    return "NOT_RUN_UNKNOWN_STATUS"


def _next_fix_action(tool: str, status: str) -> str:
    if status == "FOUND_AND_SMOKE_PASSED":
        return "Ready for gated local production use."
    if status == "FOUND_BUT_UNTESTED":
        return "Run an operator-approved smoke check before production execution."
    if status == "FOUND_BUT_REQUIRES_USER_LAUNCH":
        return "Launch or configure the app, then rerun the doctor before execution."
    if status == "LICENSE_BLOCKED":
        return "Resolve the local license issue, then rerun a smoke check."
    if tool == "python_dependencies" and status == "CONFIG_REQUIRED":
        return "Install project dependencies, for example with python -m pip install -e ."
    if tool == "comfyui" and status == "CONFIG_REQUIRED":
        return "Configure ComfyUI path or service settings before running ComfyUI jobs."
    if tool in {"after_effects", "davinci", "unreal"} and status == "CONFIG_REQUIRED":
        return "Configure the local install or scripting path before adapter smoke tests."
    if status == "CONFIG_REQUIRED":
        return "Add the required local configuration, then rerun tool health."
    if status == "NOT_FOUND":
        return "Install the tool, add it to PATH, or configure an explicit local path."
    return "Inspect the tool entry and rerun the doctor after local setup changes."


def _default_ci_requirement(tool: str) -> str:
    if tool in {"python", "python_dependencies", "git"}:
        return "required"
    return "optional"


def _next_actions(rows: list[dict[str, object]]) -> list[str]:
    actions = []
    for row in rows:
        status = str(row.get("status"))
        if status in PROBLEM_STATUSES:
            actions.append(f"{row.get('label')}: {row.get('next_fix_action')}")
    if not actions:
        actions.append("All reported tools are detected; run gated smoke checks before real production execution.")
    return actions


def _markdown_cell(value: object) -> str:
    text = str(value or "")
    return "`-`" if not text else f"`{text}`"
