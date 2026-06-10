"""Local production dashboard for real asset-library scan reports."""

from __future__ import annotations

from html import escape
from pathlib import Path
import json

TOOL_CATEGORY_MAP = {
    "houdini": ("houdini", "vdb_cache"),
    "unreal": ("unreal", "fbx_obj_usd_alembic"),
    "blender": ("blender",),
    "zbrush": ("zbrush",),
    "after_effects": ("after_effects",),
    "davinci": ("davinci",),
    "comfyui": ("comfyui",),
}


def build_local_production_dashboard(
    report: dict[str, object],
    *,
    output_markdown: Path | None = None,
    output_html: Path | None = None,
) -> dict[str, object]:
    dashboard = {
        "ok": True,
        "kind": "local_production_dashboard_v1",
        "read_only": True,
        "asset_root": report.get("asset_root", "<asset-root>"),
        "summary": report.get("summary", {}),
        "category_counts": dict(report.get("summary", {}).get("category_counts", {})),
        "largest_directories": list(report.get("largest_directories", [])),
        "duplicate_groups": list(report.get("duplicate_groups", [])),
        "empty_directories": list(report.get("empty_directories", [])),
        "archive_warnings": list(report.get("archive_warnings", [])),
        "texture_sets": list(report.get("texture_sets", [])),
        "production_groups": list(report.get("production_groups", [])),
        "production_readiness_by_tool_category": _tool_readiness(report),
        "recommended_cleanup_actions": _cleanup_actions(report),
        "next_actions": list(report.get("next_actions", [])),
        "safety": {
            "input_mutation": False,
            "duplicate_deletion": False,
            "archive_extraction": False,
            "dcc_execution": False,
        },
    }
    outputs: dict[str, str] = {}
    if output_markdown is not None:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(render_local_production_dashboard_markdown(dashboard), encoding="utf-8")
        outputs["markdown"] = output_markdown.as_posix()
    if output_html is not None:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(render_local_production_dashboard_html(dashboard), encoding="utf-8")
        outputs["html"] = output_html.as_posix()
    dashboard["outputs"] = outputs
    return dashboard


def render_local_production_dashboard_markdown(dashboard: dict[str, object]) -> str:
    summary = dict(dashboard.get("summary", {}))
    lines = [
        "# SEOS Local Production Dashboard",
        "",
        f"- Asset root: `{dashboard.get('asset_root')}`",
        f"- Read-only: `{dashboard.get('read_only')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "total_assets",
        "total_size_bytes",
        "duplicate_group_count",
        "archive_warning_count",
        "empty_directory_count",
        "texture_set_count",
        "incomplete_texture_set_count",
        "production_group_count",
        "likely_incomplete_pack_count",
    ):
        lines.append(f"| {key} | {summary.get(key, 0)} |")

    lines.extend(["", "## Assets By Category", "", "| Category | Count |", "| --- | ---: |"])
    for category, count in sorted(dict(dashboard.get("category_counts", {})).items()):
        lines.append(f"| `{category}` | {count} |")

    lines.extend(["", "## Largest Folders", "", "| Folder | Size | Files |", "| --- | ---: | ---: |"])
    for row in dashboard.get("largest_directories", [])[:10]:
        item = dict(row)
        lines.append(f"| `{item.get('relative_path')}` | {item.get('size_bytes')} | {item.get('file_count')} |")

    lines.extend(["", "## Duplicate Groups", ""])
    duplicates = list(dashboard.get("duplicate_groups", []))
    if duplicates:
        for group in duplicates[:20]:
            item = dict(group)
            lines.append(f"- `{item.get('id')}`: {item.get('asset_count')} files, manual review only")
    else:
        lines.append("- No duplicate groups detected.")

    lines.extend(["", "## Empty Folders", ""])
    empty_dirs = list(dashboard.get("empty_directories", []))
    if empty_dirs:
        for item in empty_dirs[:30]:
            lines.append(f"- `{dict(item).get('relative_path')}`")
    else:
        lines.append("- No empty folders detected.")

    lines.extend(["", "## Archive Warnings", ""])
    warnings = list(dashboard.get("archive_warnings", []))
    if warnings:
        for warning in warnings:
            item = dict(warning)
            lines.append(f"- `{item.get('base_name')}` missing parts `{item.get('missing_part_numbers')}`")
    else:
        lines.append("- No missing archive parts detected.")

    lines.extend(["", "## Texture And Pack Status", ""])
    for texture in dashboard.get("texture_sets", [])[:30]:
        item = dict(texture)
        lines.append(f"- Texture set `{item.get('base_name')}`: `{item.get('status')}`, missing `{item.get('missing_standard_maps')}`")
    for group in dashboard.get("production_groups", [])[:30]:
        item = dict(group)
        lines.append(f"- Pack `{item.get('directory')}`: `{item.get('status')}`, missing `{item.get('missing_components')}`")
    if not dashboard.get("texture_sets") and not dashboard.get("production_groups"):
        lines.append("- No texture sets or production packs detected.")

    lines.extend(["", "## Production Readiness By Tool Category", "", "| Tool | Status | Asset Count | Next Action |", "| --- | --- | ---: | --- |"])
    for row in dashboard.get("production_readiness_by_tool_category", []):
        item = dict(row)
        lines.append(f"| `{item.get('tool')}` | `{item.get('status')}` | {item.get('asset_count')} | {item.get('next_action')} |")

    lines.extend(["", "## Recommended Cleanup Actions", ""])
    for action in dashboard.get("recommended_cleanup_actions", []):
        lines.append(f"- {action}")

    lines.extend(["", "## Next Actions", ""])
    for action in dashboard.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend([
        "",
        "## Safety",
        "",
        "- Dashboard generation does not mutate input assets.",
        "- Dashboard generation does not delete duplicates or extract archives.",
        "- Dashboard generation does not execute DCC or AI tools.",
        "",
    ])
    return "\n".join(lines)


def render_local_production_dashboard_html(dashboard: dict[str, object]) -> str:
    markdown = render_local_production_dashboard_markdown(dashboard)
    body = "\n".join(f"<p>{escape(line)}</p>" if line else "" for line in markdown.splitlines())
    payload = escape(json.dumps(dashboard.get("summary", {}), sort_keys=True))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SEOS Local Production Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 1100px; line-height: 1.45; }}
    p {{ margin: .25rem 0; }}
    code {{ background: #f1f3f5; padding: .1rem .25rem; }}
  </style>
</head>
<body>
  {body}
  <script type="application/json" id="seos-summary">{payload}</script>
</body>
</html>
"""


def _tool_readiness(report: dict[str, object]) -> list[dict[str, object]]:
    counts = dict(report.get("summary", {}).get("category_counts", {}))
    readiness = []
    for tool, categories in TOOL_CATEGORY_MAP.items():
        asset_count = sum(int(counts.get(category, 0)) for category in categories)
        status = "ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED" if asset_count else "NO_ASSETS_DETECTED"
        readiness.append(
            {
                "tool": tool,
                "asset_count": asset_count,
                "status": status,
                "next_action": "Run local tool doctor before execution." if asset_count else "No tool-specific action from this scan.",
            }
        )
    return readiness


def _cleanup_actions(report: dict[str, object]) -> list[str]:
    actions = []
    summary = dict(report.get("summary", {}))
    if int(summary.get("duplicate_group_count", 0)):
        actions.append("Review duplicate groups manually before cleanup.")
    if int(summary.get("archive_warning_count", 0)):
        actions.append("Restore missing archive parts before using affected packs.")
    if int(summary.get("empty_directory_count", 0)):
        actions.append("Review empty folders for stale placeholders.")
    if int(summary.get("incomplete_texture_set_count", 0)):
        actions.append("Fill missing texture maps before lookdev or shot binding.")
    if int(summary.get("likely_incomplete_pack_count", 0)):
        actions.append("Resolve incomplete production packs before shot planning.")
    if not actions:
        actions.append("No cleanup blockers detected by the current dashboard.")
    return actions
