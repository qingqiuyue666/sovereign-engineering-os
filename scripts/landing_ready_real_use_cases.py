#!/usr/bin/env python3
"""Exercise SEOS against external real-use task fixtures."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
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
    scenarios = [
        _code_modification_case(repo, output_dir / "external_code_modification_repo"),
        _local_automation_case(repo, output_dir / "external_local_automation_repo"),
        _release_rollback_case(repo, output_dir / "external_release_rollback_repo"),
    ]
    summary = {
        "schema": "landing_ready_real_use_cases_summary_v1",
        "created_at": _now(),
        "repo": repo.as_posix(),
        "scenario_count": len(scenarios),
        "passed": all(item["passed"] for item in scenarios),
        "scenarios": scenarios,
        "honest_gaps": [
            "SEOS records dry-run execution receipts; the deterministic external patch is operator-applied after approval.",
            "No live AI provider is called; proposal boundaries are simulated with deterministic local artifacts.",
        ],
    }
    path = output_dir / "real_use_cases_summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path.as_posix())
    return 0 if summary["passed"] else 1


def _code_modification_case(repo: Path, case_dir: Path) -> dict[str, object]:
    _reset_dir(case_dir)
    (case_dir / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (case_dir / "test_calculator.py").write_text(
        "import unittest\n\nfrom calculator import add, subtract\n\n\nclass CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n"
        "    def test_subtract(self):\n        self.assertEqual(subtract(5, 3), 2)\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
        encoding="utf-8",
    )
    _git_init(case_dir)
    before = _snapshot(case_dir)
    seos = _seos_flow(
        repo,
        case_dir,
        "uc_code_mod",
        "AI code modification",
        "Add subtract function after deterministic proposal",
        "calculator.py",
    )
    proposal_path = case_dir / ".seos" / "evidence" / "proposal.json"
    proposal = {
        "proposal_type": "deterministic_ai_worker_proposal_boundary_v1",
        "provider_call_performed": False,
        "summary": "Add subtract(a, b) returning a - b",
        "target_file": "calculator.py",
    }
    proposal_path.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (case_dir / "calculator.py").open("a", encoding="utf-8") as handle:
        handle.write("\n\ndef subtract(a, b):\n    return a - b\n")
    validation = _record([sys.executable, "-m", "unittest"], cwd=case_dir, env=_env(repo))
    after = _snapshot(case_dir)
    return _case_result(
        "AI Code Modification Real Task",
        case_dir,
        before,
        after,
        seos,
        validation,
        {"proposal_path": proposal_path.as_posix(), "operator_applied_after_approval": True},
    )


def _local_automation_case(repo: Path, case_dir: Path) -> dict[str, object]:
    _reset_dir(case_dir)
    (case_dir / "generate_report.py").write_text(
        "from pathlib import Path\nPath('automation_report.txt').write_text('automation ok\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    _git_init(case_dir)
    before = _snapshot(case_dir)
    seos = _seos_flow(
        repo,
        case_dir,
        "uc_local_auto",
        "Local automation",
        "Dry-run governed local automation script",
        "generate_report.py",
    )
    validation = _record([sys.executable, "generate_report.py"], cwd=case_dir, env=_env(repo))
    after = _snapshot(case_dir)
    return _case_result(
        "Local Automation Real Task",
        case_dir,
        before,
        after,
        seos,
        validation,
        {"rollback_or_noop_safety": "script writes only a new report file inside the external fixture"},
    )


def _release_rollback_case(repo: Path, case_dir: Path) -> dict[str, object]:
    _reset_dir(case_dir)
    (case_dir / "release_readiness.json").write_text(
        json.dumps({"tests": "passed", "rollback_required": False}, indent=2) + "\n",
        encoding="utf-8",
    )
    _git_init(case_dir)
    before = _snapshot(case_dir)
    seos = _seos_flow(
        repo,
        case_dir,
        "uc_release_decision",
        "Release rollback decision",
        "Decide no rollback for passed fixture",
        "release_readiness.json",
    )
    validation = _record([sys.executable, "-c", "import json; assert json.load(open('release_readiness.json'))['tests'] == 'passed'"], cwd=case_dir, env=_env(repo))
    decision_path = case_dir / ".seos" / "evidence" / "rollback_decision_receipt.json"
    decision_path.write_text(
        json.dumps(
            {
                "decision": "NO_ROLLBACK_REQUIRED",
                "reason": "fixture readiness evidence passed",
                "human_approval_receipt": seos["approval_receipt_path"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    after = _snapshot(case_dir)
    return _case_result(
        "Release / Rollback Real Task",
        case_dir,
        before,
        after,
        seos,
        validation,
        {"decision_receipt": decision_path.as_posix(), "rollback_reasoning": "no rollback because validation passed"},
    )


def _seos_flow(repo: Path, workspace: Path, task_id: str, title: str, objective: str, source: str) -> dict[str, object]:
    init = _seos(repo, workspace, ["init", "--workspace", workspace.as_posix(), "--json"])
    task = _seos(
        repo,
        workspace,
        [
            "task",
            "create",
            "--workspace",
            workspace.as_posix(),
            "--task-id",
            task_id,
            "--title",
            title,
            "--objective",
            objective,
            "--source",
            source,
            "--json",
        ],
    )
    approval = _seos(repo, workspace, ["approve", "--workspace", workspace.as_posix(), task_id, "--json"])
    bundle = _seos(
        repo,
        workspace,
        ["ai", "bundle", "--workspace", workspace.as_posix(), task_id, "--source", source, "--budget", "4000", "--json"],
    )
    execution = _seos(
        repo,
        workspace,
        ["run", "--workspace", workspace.as_posix(), task_id, "--dry-run", "--command", "operator-controlled validation", "--json"],
    )
    trace = _seos(repo, workspace, ["evidence", "trace", "--workspace", workspace.as_posix(), task_id, "--json"])
    return {
        "task_id": task_id,
        "init": init,
        "task": task,
        "approval": approval,
        "approval_receipt_path": approval["payload"].get("receipt_path"),
        "context_bundle": bundle,
        "execution": execution,
        "trace": trace,
        "passed": all(item["returncode"] == 0 for item in (init, task, approval, bundle, execution, trace)),
    }


def _case_result(
    name: str,
    case_dir: Path,
    before: dict[str, object],
    after: dict[str, object],
    seos: dict[str, object],
    validation: dict[str, object],
    extra: dict[str, object],
) -> dict[str, object]:
    passed = bool(seos["passed"] and validation["returncode"] == 0)
    return {
        "name": name,
        "external_path": case_dir.as_posix(),
        "before_state": before,
        "after_state": after,
        "seos_evidence": seos,
        "validation_command": validation,
        "passed": passed,
        **extra,
    }


def _seos(repo: Path, cwd: Path, args: list[str]) -> dict[str, object]:
    result = _record([sys.executable, (repo / "seos.py").as_posix(), *args], cwd=cwd, env=_env(repo))
    try:
        payload = json.loads("\n".join(result["stdout_tail"]))
    except json.JSONDecodeError:
        payload = {}
    result["payload"] = payload
    return result


def _record(command: list[str], *, cwd: Path, env: dict[str, str]) -> dict[str, object]:
    completed = subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True, text=True)
    return {
        "command": " ".join(command),
        "cwd": cwd.as_posix(),
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.splitlines()[-40:],
        "stderr_tail": completed.stderr.splitlines()[-40:],
    }


def _env(repo: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = repo.as_posix()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _reset_dir(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    path.mkdir(parents=True)


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "seos-local@example.invalid"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "SEOS Local Fixture"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "initial fixture"], cwd=path, check=True, capture_output=True, text=True)


def _snapshot(path: Path) -> dict[str, object]:
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_file() and ".git" not in item.parts:
            files.append(
                {
                    "path": item.relative_to(path).as_posix(),
                    "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
                    "size_bytes": item.stat().st_size,
                }
            )
    return {"file_count": len(files), "files": files}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
