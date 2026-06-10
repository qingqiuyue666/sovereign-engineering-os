"""Build a local static operator dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.runner.result_envelope import utc_now


def build_dashboard(
    *,
    runtime_root: str | Path = "work/production_runtime",
    package_root: str | Path = "work/packages",
    repair_root: str | Path = "work/repair_jobs",
    output_root: str | Path = "work/operator_dashboard",
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    state = _load_optional_json(Path(runtime_root) / "production_state.json")
    packages = _package_manifests(package_root)
    repairs = _repair_events(repair_root)
    dashboard_state = {
        "schema_version": "seos.operator_dashboard_state.v1",
        "created_at": utc_now(),
        "project_count": len(state.get("projects", {})) if isinstance(state.get("projects"), dict) else 0,
        "shot_count": len(state.get("shots", {})) if isinstance(state.get("shots"), dict) else 0,
        "asset_scan_count": len(state.get("asset_scans", {})) if isinstance(state.get("asset_scans"), dict) else 0,
        "package_count": len(packages),
        "repair_event_count": len(repairs),
        "latest_runs": _latest_runs(state),
        "packages": packages,
        "repair_events": repairs[-20:],
    }
    write_json(output / "dashboard_state.json", dashboard_state)
    (output / "index.html").write_text(_render_html(dashboard_state), encoding="utf-8")
    return {"ok": True, "dashboard_path": (output / "index.html").as_posix(), "state_path": (output / "dashboard_state.json").as_posix(), "state": dashboard_state}


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def _package_manifests(package_root: str | Path) -> list[dict[str, Any]]:
    root = Path(package_root)
    if not root.exists():
        return []
    manifests = []
    for path in sorted(root.glob("*/*/manifest.json")):
        payload = load_json(path)
        manifests.append({"path": path.as_posix(), "package_kind": payload.get("package_kind"), "id": payload.get("run_id") or payload.get("shot_id")})
    return manifests


def _repair_events(repair_root: str | Path) -> list[dict[str, Any]]:
    path = Path(repair_root) / "repair_ledger.jsonl"
    if not path.exists():
        return []
    import json

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _latest_runs(state: dict[str, Any]) -> list[dict[str, Any]]:
    shots = state.get("shots", {})
    if not isinstance(shots, dict):
        return []
    runs = []
    for shot_id, shot in shots.items():
        for run in shot.get("runs", []) if isinstance(shot, dict) else []:
            runs.append({"shot_id": shot_id, **dict(run)})
    return runs[-20:]


def _render_html(state: dict[str, Any]) -> str:
    rows = "\n".join(
        f"<tr><td>{run.get('shot_id')}</td><td>{run.get('run_id')}</td><td>{run.get('terminal_status')}</td></tr>"
        for run in state["latest_runs"]
    )
    package_rows = "\n".join(
        f"<tr><td>{item.get('package_kind')}</td><td>{item.get('id')}</td><td>{item.get('path')}</td></tr>"
        for item in state["packages"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SEOS Operator Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 24px; color: #1f2933; }}
    .metrics {{ display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #d8dee4; border-radius: 6px; padding: 12px; background: #f6f8fa; }}
    .metric strong {{ display: block; font-size: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #d8dee4; padding: 8px; text-align: left; font-size: 13px; }}
  </style>
</head>
<body>
  <h1>SEOS Operator Dashboard</h1>
  <div class="metrics">
    <div class="metric"><span>Projects</span><strong>{state['project_count']}</strong></div>
    <div class="metric"><span>Shots</span><strong>{state['shot_count']}</strong></div>
    <div class="metric"><span>Asset Scans</span><strong>{state['asset_scan_count']}</strong></div>
    <div class="metric"><span>Packages</span><strong>{state['package_count']}</strong></div>
    <div class="metric"><span>Repair Events</span><strong>{state['repair_event_count']}</strong></div>
  </div>
  <h2>Latest Runs</h2>
  <table><thead><tr><th>Shot</th><th>Run</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
  <h2>Packages</h2>
  <table><thead><tr><th>Kind</th><th>ID</th><th>Manifest</th></tr></thead><tbody>{package_rows}</tbody></table>
</body>
</html>
"""
