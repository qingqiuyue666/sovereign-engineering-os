#!/usr/bin/env python3
"""Repository-local agent execution check harness.

This script runs a fixed verification command set from the repository root and
writes an evidence report. It does not read secrets, does not execute live
runtimes, and does not perform merge/delete/tag operations.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable

REPO_MARKERS = (".git", "tests", "kernel")
POLICY_PATH = Path("policy/agent_execution_policy.yaml")
DEFAULT_REPORT_DIR = Path(".agent_evidence")
FORBIDDEN_FILE_NAMES = {".env", ".env.local"}
FORBIDDEN_COMMAND_MARKERS = (
    "sudo",
    "rm -rf",
    "chmod -R",
    "chown -R",
    "killall",
    "pkill",
    "launchctl",
    "osascript",
    "defaults write",
    "security",
    "ssh-keygen",
    "curl | sh",
    "wget | sh",
    "npm install -g",
    "brew install",
)
FORBIDDEN_SCAN_MARKERS = (
    "subprocess.Popen",
    "os.system",
    "eval(",
    "exec(",
)
COMMANDS = (
    ("personal_ai", (sys.executable, "-m", "unittest", "discover", "-s", "tests/personal_ai", "-v")),
    ("make_ci", ("make", "ci")),
    ("diff_check", ("git", "diff", "--check")),
    ("git_status_short", ("git", "status", "--short")),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run repo-local agent checks")
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="Directory inside the repository for evidence output",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Only run repository/policy/scan checks; do not run unittest or make ci",
    )
    args = parser.parse_args(argv)

    repo_root = _find_repo_root(Path.cwd())
    _assert_inside_repo(repo_root, Path.cwd())
    _assert_policy_present(repo_root)
    _assert_no_forbidden_file_read_request()
    report_dir = _resolve_report_dir(repo_root, Path(args.report_dir))
    report_dir.mkdir(parents=True, exist_ok=True)

    started = _utc_now()
    git_status_before = _run_command(repo_root, ("git", "status", "--short"))
    command_results = []
    if not args.skip_tests:
        for name, command in COMMANDS:
            _assert_command_allowed(command)
            command_results.append(_run_named_command(repo_root, name, command))
    else:
        command_results.append(
            {
                "name": "skip_tests",
                "command": "--skip-tests",
                "returncode": 0,
                "stdout_tail": "tests skipped by explicit local flag",
                "stderr_tail": "",
            }
        )
    forbidden_scan_results = _run_forbidden_scans(repo_root)
    git_status_after = _run_command(repo_root, ("git", "status", "--short"))
    completed = _utc_now()

    report = {
        "evidence_type": "repo_local_agent_execution_harness_report_v1",
        "repository_root": repo_root.as_posix(),
        "current_branch": _run_command(repo_root, ("git", "branch", "--show-current"))["stdout"].strip(),
        "git_head": _run_command(repo_root, ("git", "rev-parse", "HEAD"))["stdout"].strip(),
        "policy_path": str(POLICY_PATH),
        "policy_sha256": _sha256_file(repo_root / POLICY_PATH),
        "started_at_utc": started,
        "completed_at_utc": completed,
        "git_status_before": git_status_before["stdout"],
        "git_status_after": git_status_after["stdout"],
        "command_results": command_results,
        "forbidden_scan_results": forbidden_scan_results,
        "live_runtime_executed": False,
        "secrets_read": False,
        "merge_performed": False,
        "branch_deleted": False,
        "complete": _is_complete(command_results, forbidden_scan_results),
    }
    report_path = report_dir / "agent_run_checks_report.json"
    summary_path = report_dir / "agent_run_checks_summary.md"
    _write_json_no_overwrite(report_path, report)
    _write_text_no_overwrite(summary_path, _render_summary(report))
    print(report_path)
    print(summary_path)
    return 0 if report["complete"] else 1


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if all((candidate / marker).exists() for marker in REPO_MARKERS):
            return candidate
    raise SystemExit("repository root not found")


def _assert_inside_repo(repo_root: Path, path: Path) -> None:
    resolved_root = repo_root.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise SystemExit("current path is outside repository")


def _assert_policy_present(repo_root: Path) -> None:
    policy = repo_root / POLICY_PATH
    if not policy.exists() or not policy.is_file():
        raise SystemExit("agent execution policy is missing")


def _assert_no_forbidden_file_read_request() -> None:
    for name in FORBIDDEN_FILE_NAMES:
        if name in os.environ.get("SEOS_AGENT_READ_FILE", ""):
            raise SystemExit("forbidden secret file read request")


def _resolve_report_dir(repo_root: Path, report_dir: Path) -> Path:
    resolved = report_dir if report_dir.is_absolute() else repo_root / report_dir
    resolved = resolved.resolve()
    _assert_inside_repo(repo_root, resolved)
    return resolved


def _assert_command_allowed(command: Iterable[str]) -> None:
    command_text = " ".join(command)
    for marker in FORBIDDEN_COMMAND_MARKERS:
        if marker in command_text:
            raise SystemExit("forbidden command requested: " + marker)


def _run_named_command(repo_root: Path, name: str, command: tuple[str, ...]) -> dict[str, object]:
    result = _run_command(repo_root, command)
    return {
        "name": name,
        "command": " ".join(command),
        "returncode": result["returncode"],
        "stdout_tail": _tail(result["stdout"]),
        "stderr_tail": _tail(result["stderr"]),
    }


def _run_command(repo_root: Path, command: tuple[str, ...]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        env=_sanitized_env(),
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _sanitized_env() -> dict[str, str]:
    allowed_prefixes = ("PATH", "HOME", "SHELL", "TMPDIR", "PYTHON", "LANG", "LC_")
    env = {}
    for key, value in os.environ.items():
        if key in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"}:
            continue
        if key.startswith(allowed_prefixes):
            env[key] = value
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run_forbidden_scans(repo_root: Path) -> list[dict[str, object]]:
    results = []
    for marker in FORBIDDEN_SCAN_MARKERS:
        matches = []
        for path in _iter_scannable_files(repo_root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if marker in text:
                matches.append(path.relative_to(repo_root).as_posix())
        results.append({"marker": marker, "matches": sorted(matches)})
    return results


def _iter_scannable_files(repo_root: Path):
    for path in repo_root.rglob("*.py"):
        rel = path.relative_to(repo_root).as_posix()
        if rel.startswith(".git/") or rel.startswith(".agent_evidence/"):
            continue
        yield path


def _is_complete(command_results: list[dict[str, object]], forbidden_scan_results: list[dict[str, object]]) -> bool:
    commands_ok = all(item["returncode"] == 0 for item in command_results)
    scan_ok = all(
        not any(match.startswith("kernel/") for match in item["matches"])
        for item in forbidden_scan_results
    )
    return commands_ok and scan_ok


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_no_overwrite(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise SystemExit("evidence report already exists")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text_no_overwrite(path: Path, text: str) -> None:
    if path.exists():
        raise SystemExit("evidence summary already exists")
    path.write_text(text, encoding="utf-8")


def _render_summary(report: dict[str, object]) -> str:
    status = "complete" if report["complete"] else "blocked"
    return "\n".join(
        [
            "# Agent Run Checks Summary",
            "",
            f"Status: {status}",
            f"Branch: {report['current_branch']}",
            f"Git head: {report['git_head']}",
            "Live runtime executed: false",
            "Secrets read: false",
            "Merge performed: false",
            "Branch deleted: false",
            "",
        ]
    )


def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
