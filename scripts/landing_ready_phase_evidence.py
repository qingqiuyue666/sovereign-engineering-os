#!/usr/bin/env python3
"""Generate Phase B-E landing-ready evidence receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    phase_b = _phase_b(repo, output_dir / "phase_b_cli_workspace")
    phase_c = _phase_c(repo, output_dir / "phase_c_ai_workspace")
    phase_d = _phase_d(repo, output_dir / "phase_d_evidence_workspace")
    phase_e = _phase_e(output_dir)
    reports = {
        "phase_b_cli_evidence.json": phase_b,
        "phase_c_ai_evidence.json": phase_c,
        "phase_d_evidence_query_evidence.json": phase_d,
        "phase_e_real_use_case_hardening.json": phase_e,
    }
    for name, payload in reports.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print((output_dir / name).as_posix())
    return 0 if all(payload["passed"] for payload in reports.values()) else 1


def _phase_b(repo: Path, workspace: Path) -> dict[str, object]:
    _reset(workspace)
    commands = [
        _seos(repo, workspace, ["init", "--workspace", workspace.as_posix(), "--json"], item=8),
        _seos(repo, workspace, ["status", "--workspace", workspace.as_posix(), "--human"], item=9),
        _seos(
            repo,
            workspace,
            [
                "task",
                "create",
                "--workspace",
                workspace.as_posix(),
                "--task-id",
                "phase_b_task",
                "--title",
                "Phase B task",
                "--objective",
                "Prove practical CLI task flow",
                "--json",
            ],
            item=10,
        ),
        _seos(repo, workspace, ["task", "list", "--workspace", workspace.as_posix(), "--json"], item=10),
        _seos(repo, workspace, ["task", "show", "--workspace", workspace.as_posix(), "phase_b_task", "--json"], item=10),
        _seos(repo, workspace, ["approve", "--workspace", workspace.as_posix(), "phase_b_task", "--json"], item=11),
        _seos(
            repo,
            workspace,
            [
                "task",
                "create",
                "--workspace",
                workspace.as_posix(),
                "--task-id",
                "phase_b_reject_task",
                "--title",
                "Phase B reject task",
                "--objective",
                "Prove rejection receipt",
                "--json",
            ],
            item=11,
        ),
        _seos(repo, workspace, ["reject", "--workspace", workspace.as_posix(), "phase_b_reject_task", "--json"], item=11),
        _seos(repo, workspace, ["run", "--workspace", workspace.as_posix(), "phase_b_reject_task", "--dry-run", "--json"], item=12, expect_success=False),
        _seos(repo, workspace, ["run", "--workspace", workspace.as_posix(), "phase_b_task", "--dry-run", "--command", "phase-b-dry-run", "--json"], item=12),
        _seos(repo, workspace, ["release", "check", "--workspace", workspace.as_posix(), "--json"], item=13, run_cwd=repo),
    ]
    return _report("phase_b_practical_cli_v1", commands, {8: "init", 9: "status", 10: "task_create_list_show", 11: "approve_reject", 12: "run", 13: "release_check"})


def _phase_c(repo: Path, workspace: Path) -> dict[str, object]:
    _reset(workspace)
    setup = [
        _seos(repo, workspace, ["init", "--workspace", workspace.as_posix(), "--json"], item=14),
        _seos(
            repo,
            workspace,
            [
                "task",
                "create",
                "--workspace",
                workspace.as_posix(),
                "--task-id",
                "phase_c_task",
                "--title",
                "Phase C AI task",
                "--objective",
                "Prove token-aware context and routing",
                "--source",
                "README.md",
                "--json",
            ],
            item=14,
        ),
    ]
    commands = setup + [
        _seos(repo, workspace, ["ai", "bundle", "--workspace", workspace.as_posix(), "phase_c_task", "--source", "README.md", "--budget", "4000", "--json"], item=14, run_cwd=repo),
        _seos(repo, workspace, ["ai", "bundle", "--workspace", workspace.as_posix(), "phase_c_task", "--source", "README.md", "--budget", "10", "--json"], item=15, expect_success=False, run_cwd=repo),
        _seos(repo, workspace, ["ai", "bundle", "--workspace", workspace.as_posix(), "phase_c_task", "--source", "apps/operator_cli/main.py", "--budget", "4000", "--json"], item=16, run_cwd=repo),
        _seos(repo, workspace, ["ai", "repo-map", "--workspace", workspace.as_posix(), "--json"], item=17, run_cwd=repo),
        _seos(repo, workspace, ["failure", "compress", "--workspace", workspace.as_posix(), "--command", "phase-c-validation", "--exit-code", "1", "--log", "FAILED phase c sample", "--json"], item=18),
        _seos(repo, workspace, ["failure", "explain", "--workspace", workspace.as_posix(), "latest", "--json"], item=18),
        _seos(repo, workspace, ["ai", "token-roi", "--workspace", workspace.as_posix(), "--json"], item=19),
    ]
    return _report("phase_c_ai_efficiency_layer_v1", commands, {14: "context_bundle", 15: "token_budget_gate", 16: "model_routing_policy", 17: "repo_map_symbol_index", 18: "failure_bundle_compression", 19: "token_roi_report"})


def _phase_d(repo: Path, workspace: Path) -> dict[str, object]:
    _reset(workspace)
    setup = [
        _seos(repo, workspace, ["init", "--workspace", workspace.as_posix(), "--json"], item=20),
        _seos(
            repo,
            workspace,
            [
                "task",
                "create",
                "--workspace",
                workspace.as_posix(),
                "--task-id",
                "phase_d_task",
                "--title",
                "Phase D evidence task",
                "--objective",
                "Prove evidence query UX",
                "--source",
                "README.md",
                "--json",
            ],
            item=20,
        ),
        _seos(repo, workspace, ["approve", "--workspace", workspace.as_posix(), "phase_d_task", "--json"], item=20),
        _seos(repo, workspace, ["run", "--workspace", workspace.as_posix(), "phase_d_task", "--dry-run", "--command", "phase-d-dry-run", "--json"], item=20),
        _seos(repo, workspace, ["failure", "compress", "--workspace", workspace.as_posix(), "--command", "phase-d-validation", "--exit-code", "1", "--log", "FAILED phase d sample", "--json"], item=24),
    ]
    task_file = workspace / ".seos" / "tasks" / "phase_d_task.json"
    commands = setup + [
        _seos(repo, workspace, ["evidence", "trace", "--workspace", workspace.as_posix(), "phase_d_task"], item=20),
        _seos(repo, workspace, ["evidence", "trace", "--workspace", workspace.as_posix(), "phase_d_task", "--json"], item=20),
        _seos(repo, workspace, ["evidence", "show", "--workspace", workspace.as_posix(), task_file.relative_to(workspace / ".seos").as_posix(), "--json"], item=21),
        _seos(repo, workspace, ["receipt", "list", "--workspace", workspace.as_posix(), "--json"], item=22),
        _seos(repo, workspace, ["receipt", "show", "--workspace", workspace.as_posix(), "latest", "--json"], item=22),
        _seos(repo, workspace, ["replay", "explain", "--workspace", workspace.as_posix(), "phase_d_task", "--json"], item=23),
        _seos(repo, workspace, ["failure", "explain", "--workspace", workspace.as_posix(), "latest", "--json"], item=24),
    ]
    return _report("phase_d_evidence_query_ux_v1", commands, {20: "evidence_trace", 21: "evidence_show", 22: "receipt_show", 23: "replay_explain", 24: "failure_explain"})


def _phase_e(output_dir: Path) -> dict[str, object]:
    summary_path = output_dir / "real_use_cases_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    item_map = {
        25: "AI Code Modification Real Task",
        26: "Local Automation Real Task",
        27: "Release / Rollback Real Task",
    }
    item_results = {
        item: next((scenario for scenario in summary["scenarios"] if scenario["name"] == name), {})
        for item, name in item_map.items()
    }
    return {
        "schema": "landing_ready_phase_e_real_use_case_hardening_v1",
        "created_at": _now(),
        "passed": summary.get("passed") is True and all(item_results[item].get("passed") for item in item_map),
        "items": item_map,
        "item_results": item_results,
        "real_use_case_summary": summary_path.as_posix(),
    }


def _report(name: str, commands: list[dict[str, object]], item_labels: dict[int, str]) -> dict[str, object]:
    item_results = {}
    for item, label in item_labels.items():
        item_commands = [command for command in commands if command["item"] == item]
        item_results[item] = {
            "label": label,
            "passed": all(command["accepted_result"] for command in item_commands),
            "commands": item_commands,
        }
    return {
        "schema": name,
        "created_at": _now(),
        "passed": all(result["passed"] for result in item_results.values()),
        "item_results": item_results,
    }


def _seos(
    repo: Path,
    cwd: Path,
    args: list[str],
    *,
    item: int,
    expect_success: bool = True,
    run_cwd: Path | None = None,
) -> dict[str, object]:
    env = dict(os.environ)
    env["PYTHONPATH"] = repo.as_posix()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, (repo / "seos.py").as_posix(), *args]
    actual_cwd = run_cwd or cwd
    completed = subprocess.run(command, cwd=actual_cwd, env=env, check=False, capture_output=True, text=True)
    return {
        "item": item,
        "command": " ".join(command),
        "cwd": actual_cwd.as_posix(),
        "returncode": completed.returncode,
        "accepted_result": completed.returncode == 0 if expect_success else completed.returncode != 0,
        "stdout_tail": completed.stdout.splitlines()[-40:],
        "stderr_tail": completed.stderr.splitlines()[-40:],
    }


def _reset(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    path.mkdir(parents=True)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
