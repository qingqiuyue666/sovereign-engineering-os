"""Production hardening plans from creative pressure-test evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from creative.common import LOCAL_PATH_MARKERS, SCHEMA_VERSION, partial_sha256, repo_root, stable_id, write_json

DEFAULT_PACKAGE_PATHS: Final[tuple[str, ...]] = (
    "reports/creative/assets/asset_library_report_v1.json",
    "reports/creative/assets/asset_library_report_v1.md",
    "reports/creative/assets/local_production_dashboard_v1.md",
    "reports/creative/assets/local_production_dashboard_v1.html",
    "reports/creative/tool_health/local_tool_health_dashboard_v1.json",
    "reports/creative/tool_health/local_tool_health_dashboard_v1.md",
    "reports/creative/adapters/optional_adapter_contracts_v1.json",
    "reports/creative/adapters/optional_adapter_contracts_v1.md",
    "reports/creative/shots/shot_plan_energy_impact_v1.json",
    "reports/creative/shots/shot_plan_energy_impact_v1.md",
    "reports/creative/pressure/real_project_pressure_test_v1.json",
    "reports/creative/pressure/real_project_pressure_test_v1.md",
)

DEFAULT_MAX_ARTIFACT_BYTES: Final[int] = 1_000_000
DEFAULT_MAX_TOTAL_BYTES: Final[int] = 5_000_000

ACTION_LIBRARY: Final[dict[str, dict[str, str]]] = {
    "ASSET_SCAN_EMPTY": {
        "priority": "P0",
        "workstream": "asset_scan",
        "operator_action": "Point the scanner at a real asset root or restore the fixture root before planning.",
        "verification": "Rerun creative pressure-test and confirm asset_scan_has_assets passes.",
        "command": "python3 seos.py creative pressure-test --root ASSET_ROOT --template energy-impact --shot-id SHOT_ID",
    },
    "SHOT_REQUIRED_ASSETS_MISSING": {
        "priority": "P0",
        "workstream": "shot_binding",
        "operator_action": "Add or relink required assets for the selected shot template.",
        "verification": "Rerun creative shot plan and confirm missing_required_count is 0.",
        "command": "python3 seos.py creative shot plan --template TEMPLATE --shot-id SHOT_ID --registry-json REGISTRY_JSON",
    },
    "ARCHIVE_PART_MISSING": {
        "priority": "P1",
        "workstream": "asset_repair",
        "operator_action": "Restore missing archive parts before extraction or production use.",
        "verification": "Rerun the incomplete archive search and confirm result_count is 0 for production-critical packs.",
        "command": "python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query incomplete-archives",
    },
    "INCOMPLETE_TEXTURE_SETS": {
        "priority": "P1",
        "workstream": "lookdev_repair",
        "operator_action": "Fill missing texture maps or mark the lookdev set as intentionally partial.",
        "verification": "Rerun the missing texture-set search and review remaining results.",
        "command": "python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query missing-texture-sets",
    },
    "INCOMPLETE_PRODUCTION_PACKS": {
        "priority": "P1",
        "workstream": "asset_repair",
        "operator_action": "Resolve incomplete model/material/texture packs before binding them to shots.",
        "verification": "Rerun the incomplete pack search and review remaining results.",
        "command": "python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query incomplete-packs",
    },
    "LOCAL_RUNNER_NOT_READY": {
        "priority": "P1",
        "workstream": "local_runner_readiness",
        "operator_action": "Resolve local tool health before using the optional runner.",
        "verification": "Rerun the tool-health dashboard and confirm the runner status is no longer NOT_FOUND or CONFIG_REQUIRED.",
        "command": "python3 seos.py creative tool-health-dashboard --mode public",
    },
    "DUPLICATES_REQUIRE_REVIEW": {
        "priority": "P2",
        "workstream": "asset_cleanup",
        "operator_action": "Review duplicate groups manually before deleting, archiving, or packaging anything.",
        "verification": "Document the keep/remove decision outside the public fixture report, then rescan.",
        "command": "python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query duplicate-video-audio",
    },
    "ADAPTERS_CONTRACT_ONLY": {
        "priority": "P2",
        "workstream": "adapter_proof",
        "operator_action": "Treat optional adapters as contract-only until adapter-specific local proof exists.",
        "verification": "Open adapter-specific proof PRs before changing supports_execute to true.",
        "command": "python3 seos.py creative optional-adapter-contracts --mode public",
    },
    "EMPTY_DIRECTORIES_PRESENT": {
        "priority": "P3",
        "workstream": "asset_cleanup",
        "operator_action": "Decide whether empty directories are intentional placeholders or stale clutter.",
        "verification": "Rerun the empty-directory search and review remaining paths.",
        "command": "python3 seos.py creative search-assets --registry-json reports/creative/assets/asset_library_report_v1.json --query empty-directories",
    },
}


def build_production_hardening_plan(
    pressure_report: dict[str, object],
    *,
    package_paths: list[str] | None = None,
    root: Path | None = None,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    output_json: Path | None = None,
    output_markdown: Path | None = None,
) -> dict[str, object]:
    """Build a repair/action plan and output package manifest from pressure evidence."""
    repository_root = root or repo_root()
    resolved_package_paths = _package_paths(pressure_report, package_paths)
    package_manifest = _build_package_manifest(
        resolved_package_paths,
        root=repository_root,
        max_artifact_bytes=max_artifact_bytes,
    )
    package_summary = _package_summary(
        package_manifest,
        max_artifact_bytes=max_artifact_bytes,
        max_total_bytes=max_total_bytes,
    )
    actions = _repair_actions(pressure_report)
    hardening_status = _hardening_status(pressure_report, package_summary)
    report = {
        "action_summary": _action_summary(actions),
        "destructive_actions_performed": False,
        "execution_performed": False,
        "hardening_status": hardening_status,
        "kind": "production_hardening_plan_v1",
        "next_actions": _next_actions(actions, package_summary),
        "ok": package_summary["local_path_leak_count"] == 0,
        "output_package_manifest_only": True,
        "package_manifest": package_manifest,
        "package_summary": package_summary,
        "pressure_report": {
            "kind": pressure_report.get("kind", ""),
            "pressure_status": pressure_report.get("pressure_status", ""),
            "scenario": pressure_report.get("scenario", {}),
            "source_outputs": pressure_report.get("outputs", {}),
        },
        "read_only": True,
        "repair_actions": actions,
        "schema_version": SCHEMA_VERSION,
        "safety": {
            "asset_mutation": False,
            "dcc_or_ai_execution": False,
            "file_copy_or_archive_creation": False,
            "local_path_leak_blocks_public_package": True,
            "package_manifest_only": True,
        },
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
        output_markdown.write_text(render_production_hardening_markdown(report), encoding="utf-8")
    return report


def render_production_hardening_markdown(report: dict[str, object]) -> str:
    package_summary = dict(report.get("package_summary", {}))
    action_summary = dict(report.get("action_summary", {}))
    lines = [
        "# SEOS Production Hardening Plan",
        "",
        f"- Hardening status: `{report.get('hardening_status')}`",
        f"- Package status: `{package_summary.get('package_status')}`",
        f"- Read-only: `{report.get('read_only')}`",
        f"- Output package manifest only: `{report.get('output_package_manifest_only')}`",
        "",
        "## Action Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| total_actions | {action_summary.get('total_actions', 0)} |",
        f"| p0_count | {action_summary.get('P0', 0)} |",
        f"| p1_count | {action_summary.get('P1', 0)} |",
        f"| p2_count | {action_summary.get('P2', 0)} |",
        f"| p3_count | {action_summary.get('P3', 0)} |",
        "",
        "## Repair Actions",
        "",
        "| Priority | Source | Workstream | Action |",
        "| --- | --- | --- | --- |",
    ]
    for action in report.get("repair_actions", []):
        item = dict(action)
        lines.append(
            f"| `{item.get('priority')}` | `{item.get('source_finding_code')}` | "
            f"`{item.get('workstream')}` | {item.get('operator_action')} |"
        )

    lines.extend(
        [
            "",
            "## Package Summary",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| artifact_count | {package_summary.get('artifact_count', 0)} |",
            f"| missing_count | {package_summary.get('missing_count', 0)} |",
            f"| oversized_count | {package_summary.get('oversized_count', 0)} |",
            f"| local_path_leak_count | {package_summary.get('local_path_leak_count', 0)} |",
            f"| total_size_bytes | {package_summary.get('total_size_bytes', 0)} |",
            "",
            "## Package Manifest",
            "",
            "| Path | Status | Size | Digest |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for artifact in report.get("package_manifest", []):
        item = dict(artifact)
        lines.append(
            f"| `{item.get('path')}` | `{item.get('status')}` | "
            f"{item.get('size_bytes', 0)} | `{item.get('partial_sha256', '')}` |"
        )

    lines.extend(["", "## Next Actions", ""])
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This hardening plan is read-only.",
            "- It writes a manifest/report only; it does not copy, zip, delete, mutate, launch, render, or generate.",
            "- Public package readiness is blocked if a package artifact leaks a local path marker.",
            "",
        ]
    )
    return "\n".join(lines)


def _package_paths(pressure_report: dict[str, object], package_paths: list[str] | None) -> list[str]:
    paths = list(package_paths or DEFAULT_PACKAGE_PATHS)
    outputs = dict(pressure_report.get("outputs", {}))
    for value in outputs.values():
        text = str(value)
        if text and text not in paths:
            paths.append(text)
    return list(dict.fromkeys(paths))


def _build_package_manifest(
    paths: list[str],
    *,
    root: Path,
    max_artifact_bytes: int,
) -> list[dict[str, object]]:
    manifest = []
    for value in paths:
        path = Path(value)
        resolved = path if path.is_absolute() else root / path
        display_path = _display_path(resolved, root)
        if not resolved.exists():
            manifest.append(
                {
                    "exists": False,
                    "local_path_leak_detected": False,
                    "path": display_path,
                    "partial_sha256": "",
                    "size_bytes": 0,
                    "status": "MISSING",
                    "within_size_limit": False,
                }
            )
            continue
        size_bytes = resolved.stat().st_size
        local_path_leak = _has_local_path_leak(resolved, root)
        within_size_limit = size_bytes <= max_artifact_bytes
        status = "READY"
        if local_path_leak:
            status = "LOCAL_PATH_LEAK_BLOCKED"
        elif not within_size_limit:
            status = "OUTPUT_TOO_LARGE"
        manifest.append(
            {
                "exists": True,
                "local_path_leak_detected": local_path_leak,
                "path": display_path,
                "partial_sha256": partial_sha256(resolved),
                "size_bytes": size_bytes,
                "status": status,
                "within_size_limit": within_size_limit,
            }
        )
    return manifest


def _package_summary(
    manifest: list[dict[str, object]],
    *,
    max_artifact_bytes: int,
    max_total_bytes: int,
) -> dict[str, object]:
    missing_count = sum(1 for item in manifest if not item.get("exists"))
    oversized_count = sum(1 for item in manifest if item.get("exists") and not item.get("within_size_limit"))
    local_path_leak_count = sum(1 for item in manifest if item.get("local_path_leak_detected"))
    total_size_bytes = sum(int(item.get("size_bytes", 0)) for item in manifest if item.get("exists"))
    if local_path_leak_count:
        package_status = "LOCAL_PATH_LEAK_BLOCKED"
    elif oversized_count or total_size_bytes > max_total_bytes:
        package_status = "OUTPUT_SIZE_LIMIT_EXCEEDED"
    elif missing_count:
        package_status = "PACKAGE_INCOMPLETE"
    else:
        package_status = "READY_FOR_HANDOFF"
    return {
        "artifact_count": len(manifest),
        "local_path_leak_count": local_path_leak_count,
        "max_artifact_bytes": max_artifact_bytes,
        "max_total_bytes": max_total_bytes,
        "missing_count": missing_count,
        "oversized_count": oversized_count,
        "package_status": package_status,
        "total_size_bytes": total_size_bytes,
        "within_total_size_limit": total_size_bytes <= max_total_bytes,
    }


def _repair_actions(pressure_report: dict[str, object]) -> list[dict[str, object]]:
    actions = []
    for index, finding in enumerate(pressure_report.get("findings", []), start=1):
        item = dict(finding)
        code = str(item.get("code", "UNKNOWN_FINDING"))
        spec = ACTION_LIBRARY.get(
            code,
            {
                "priority": "P2",
                "workstream": "manual_review",
                "operator_action": str(item.get("next_action", "Review the pressure finding.")),
                "verification": "Rerun the pressure test and confirm the finding is resolved or explicitly accepted.",
                "command": "python3 seos.py creative pressure-test",
            },
        )
        evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
        operator_action = spec["operator_action"]
        if code == "LOCAL_RUNNER_NOT_READY" and evidence:
            runner_id = str(evidence.get("runner_id", "optional_runner"))
            readiness = str(evidence.get("readiness", "not_ready"))
            operator_action = f"Resolve local tool health for {runner_id} ({readiness}) before using the optional runner."
        actions.append(
            {
                "command": spec["command"],
                "done_when": spec["verification"],
                "evidence": evidence,
                "id": stable_id("HARDEN", index, code, evidence),
                "operator_action": operator_action,
                "priority": spec["priority"],
                "severity": item.get("severity", ""),
                "source_finding_code": code,
                "workstream": spec["workstream"],
            }
        )
    return actions


def _action_summary(actions: list[dict[str, object]]) -> dict[str, object]:
    summary = {"total_actions": len(actions), "P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for action in actions:
        priority = str(action.get("priority"))
        if priority in summary:
            summary[priority] = int(summary[priority]) + 1
    return summary


def _hardening_status(pressure_report: dict[str, object], package_summary: dict[str, object]) -> str:
    if package_summary.get("package_status") in {"LOCAL_PATH_LEAK_BLOCKED", "OUTPUT_SIZE_LIMIT_EXCEEDED", "PACKAGE_INCOMPLETE"}:
        return "BLOCKED_NEEDS_PACKAGE_REPAIR"
    severities = {str(finding.get("severity")) for finding in pressure_report.get("findings", [])}
    if "BLOCKER" in severities:
        return "BLOCKED_NEEDS_PROJECT_REPAIR"
    if "WARNING" in severities:
        return "NEEDS_REPAIR_BEFORE_EXECUTION"
    return "READY_FOR_REPEATED_USE"


def _next_actions(actions: list[dict[str, object]], package_summary: dict[str, object]) -> list[str]:
    result = []
    if package_summary.get("package_status") != "READY_FOR_HANDOFF":
        result.append("Repair package manifest blockers before sharing or archiving outputs.")
    for action in actions:
        text = str(action.get("operator_action", ""))
        if text and text not in result:
            result.append(text)
    result.append("Rerun creative pressure-test after repairs and compare the new hardening plan.")
    result.append("Keep final creative and production approval human-owned.")
    return result


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<external-path:{path.name}>"


def _has_local_path_leak(path: Path, root: Path) -> bool:
    if path.suffix.lower() not in {".json", ".md", ".html", ".txt", ".jsonl"}:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    markers = (*LOCAL_PATH_MARKERS, root.as_posix())
    return any(marker and marker in text for marker in markers)
