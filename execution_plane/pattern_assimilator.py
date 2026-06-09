"""Pattern assimilator report generator."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import json

from creative.common import load_json, write_json
from execution_plane.runner.result_envelope import utc_now


def generate_pattern_report(
    *,
    runtime_root: str | Path = "work/production_runtime",
    package_root: str | Path = "work/packages",
    review_root: str | Path = "work/review_artifacts",
    repair_root: str | Path = "work/repair_jobs",
    output_root: str | Path = "work/pattern_assimilator",
) -> dict[str, Any]:
    state = _load_optional(Path(runtime_root) / "production_state.json")
    package_manifests = [load_json(path) for path in Path(package_root).glob("*/*/manifest.json")] if Path(package_root).exists() else []
    reviews = [load_json(path) for path in Path(review_root).glob("*/review_artifact.json")] if Path(review_root).exists() else []
    repair_events = _repair_events(repair_root)
    terminal_counts = Counter()
    failure_codes = Counter()
    for shot in state.get("shots", {}).values() if isinstance(state.get("shots"), dict) else []:
        for run in shot.get("runs", []):
            terminal_counts[str(run.get("terminal_status"))] += 1
            receipt_path = Path(str(run.get("receipt_path", "")))
            if receipt_path.exists():
                receipt = load_json(receipt_path)
                workflow = receipt.get("workflow_receipt", {})
                failure = workflow.get("failure_code")
                if failure:
                    failure_codes[str(failure)] += 1
    report = {
        "schema_version": "seos.pattern_assimilator_report.v1",
        "created_at": utc_now(),
        "project_count": len(state.get("projects", {})) if isinstance(state.get("projects"), dict) else 0,
        "shot_count": len(state.get("shots", {})) if isinstance(state.get("shots"), dict) else 0,
        "package_count": len(package_manifests),
        "review_count": len(reviews),
        "repair_event_count": len(repair_events),
        "terminal_status_counts": dict(sorted(terminal_counts.items())),
        "failure_code_counts": dict(sorted(failure_codes.items())),
        "suggested_actions": _suggested_actions(failure_codes, terminal_counts),
    }
    output = Path(output_root)
    write_json(output / "pattern_report.json", report)
    (output / "pattern_report.md").write_text(_markdown(report), encoding="utf-8")
    return {"ok": True, "report_path": (output / "pattern_report.json").as_posix(), "markdown_path": (output / "pattern_report.md").as_posix(), "report": report}


def _load_optional(path: Path) -> dict[str, Any]:
    return load_json(path) if path.exists() else {}


def _repair_events(root: str | Path) -> list[dict[str, Any]]:
    path = Path(root) / "repair_ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _suggested_actions(failure_codes: Counter[str], terminal_counts: Counter[str]) -> list[str]:
    actions = []
    if failure_codes.get("ENV_NOT_FOUND"):
        actions.append("Install or configure missing local DCC runtime before rerunning affected shots.")
    if terminal_counts.get("TERMINAL_FAILED"):
        actions.append("Review failure bundles and convergence receipts for failed shot runs.")
    if not actions:
        actions.append("No recurring failure pattern detected.")
    return actions


def _markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Pattern Assimilator Report",
            "",
            f"Projects: {report['project_count']}",
            f"Shots: {report['shot_count']}",
            f"Packages: {report['package_count']}",
            f"Reviews: {report['review_count']}",
            "",
            "Suggested actions:",
            *[f"- {item}" for item in report["suggested_actions"]],
            "",
        ]
    )
