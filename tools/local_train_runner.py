
#!/usr/bin/env python3

"""Local train runner.

Local-only automation for repository verification, reporting, controlled commit,

and controlled feature-branch push.

This runner does not call cloud AI, does not merge, does not delete branches,

does not push main, and does not read secrets or .env files.

"""

from __future__ import annotations

import argparse

import datetime as dt

import json

import subprocess

from dataclasses import dataclass

from pathlib import Path

from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]

LOG_PATH = ROOT / "outputs/logs/local_train_runner.log"

REPORT_PATH = ROOT / "outputs/reports/local_train_runner_report.md"

SUMMARY_PATH = ROOT / "outputs/reports/local_train_runner_summary.json"
OVERNIGHT_LOG_PATH = ROOT / "outputs/logs/overnight_task_queue.log"
OVERNIGHT_REPORT_PATH = ROOT / "outputs/reports/overnight_task_queue_report.md"
OVERNIGHT_SUMMARY_PATH = ROOT / "outputs/reports/overnight_task_queue_summary.json"
OVERNIGHT_INDEX_PATH = ROOT / "outputs/reports/overnight_task_queue_index.json"
OVERNIGHT_RESUME_PATH = ROOT / "outputs/state/overnight_task_queue_resume.json"
OVERNIGHT_HEARTBEAT_PATH = ROOT / "outputs/state/overnight_task_queue_heartbeat.json"

ALLOWED_SUITES = ("local-core", "full")

ALLOWED_MODES = ("verify", "commit", "commit-push", "overnight")

@dataclass(frozen=True)

class CommandResult:

    command: tuple[str, ...]

    returncode: int

    stdout: str

    stderr: str

    @property

    def ok(self) -> bool:

        return self.returncode == 0

    def as_dict(self) -> dict[str, object]:

        return {

            "command": list(self.command),

            "returncode": self.returncode,

            "ok": self.ok,

            "stdout_tail": self.stdout[-4000:],

            "stderr_tail": self.stderr[-4000:],

        }

def now_utc() -> str:

    return dt.datetime.now(dt.UTC).isoformat()

def ensure_output_dirs() -> None:

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)

def run_command(command: Sequence[str]) -> CommandResult:

    result = subprocess.run(

        tuple(command),

        cwd=ROOT,

        text=True,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        check=False,

    )

    return CommandResult(tuple(command), result.returncode, result.stdout, result.stderr)

def git_output(*args: str) -> str:

    result = run_command(("git", *args))

    return (result.stdout + result.stderr).strip()

def current_branch() -> str:

    return git_output("branch", "--show-current")

def current_head() -> str:

    return git_output("log", "--oneline", "-1")

def git_status_short() -> str:

    return git_output("status", "--short")

def is_main_branch(branch: str) -> bool:

    return branch == "main"

def suite_commands(suite: str) -> tuple[tuple[str, ...], ...]:

    if suite == "local-core":

        return (

            ("python3", "-m", "unittest", "tests.tracer_bullet.test_local_core_operating_foundation", "-v"),

            ("python3", "-m", "unittest", "tests.tracer_bullet.test_local_core_authority_gate", "-v"),

            ("git", "diff", "--check"),

        )

    if suite == "full":

        return (

            ("python3", "-m", "unittest", "discover", "-s", "tests/tracer_bullet", "-v"),

            ("python3", "-m", "unittest", "discover", "-s", "tests/schemas", "-v"),

            ("python3", "-m", "unittest", "discover", "-s", "validation/tests/acceptance", "-v"),

            ("make", "ci"),

            ("git", "diff", "--check"),

        )

    raise ValueError(f"unsupported suite: {suite}")

def validate_safe_mode(

    mode: str,

    branch: str,

    allow_commit: bool,

    allow_push_feature_branch: bool,

) -> list[str]:

    failures: list[str] = []

    if mode not in ALLOWED_MODES:

        failures.append("mode_not_allowed")

    if is_main_branch(branch) and mode in ("commit", "commit-push", "overnight"):

        failures.append("main_branch_mutation_forbidden")

    if mode in ("commit", "commit-push", "overnight") and not allow_commit:

        failures.append("commit_not_explicitly_allowed")

    if mode in ("commit-push", "overnight") and not allow_push_feature_branch:

        failures.append("push_feature_branch_not_explicitly_allowed")

    return failures

def append_log(results: list[CommandResult], metadata: dict[str, object]) -> None:

    ensure_output_dirs()

    with LOG_PATH.open("a", encoding="utf-8") as fh:

        fh.write("\n" + "=" * 80 + "\n")

        fh.write(f"local_train_runner run at {now_utc()}\n")

        fh.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

        for result in results:

            fh.write("\n" + "-" * 80 + "\n")

            fh.write("$ " + " ".join(result.command) + "\n")

            fh.write(f"returncode={result.returncode}\n")

            if result.stdout:

                fh.write("\n[stdout]\n")

                fh.write(result.stdout)

            if result.stderr:

                fh.write("\n[stderr]\n")

                fh.write(result.stderr)

def write_reports(summary: dict[str, object], results: list[CommandResult]) -> None:

    ensure_output_dirs()

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [

        "# Local Train Runner Report",

        "",

        f"- generated_at: `{summary['generated_at']}`",

        f"- branch: `{summary['branch']}`",

        f"- head: `{summary['head']}`",

        f"- suite: `{summary['suite']}`",

        f"- mode: `{summary['mode']}`",

        f"- overall_ok: `{summary['overall_ok']}`",

        f"- first_failure: `{summary.get('first_failure') or ''}`",

        f"- dirty_worktree: `{summary['dirty_worktree']}`",

        f"- committed: `{summary['committed']}`",

        f"- pushed: `{summary['pushed']}`",

        "",

        "## Commands",

        "",

    ]

    for result in results:

        status = "OK" if result.ok else "FAIL"

        lines.append(f"- `{status}` `$ {' '.join(result.command)}` -> `{result.returncode}`")

    lines.extend([

        "",

        "## Git Status",

        "",

        "```text",

        str(summary.get("git_status_short", "")),

        "```",

        "",

        "## Safety",

        "",

        "- no cloud AI calls",

        "- no merge",

        "- no branch deletion",

        "- no push to main",

        "- no secret read",

        "- no provider live execution",

        "- no vault live write",

        "- no production autonomy",

        "",

    ])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

def git_commit(message: str) -> CommandResult:

    add_result = run_command(("git", "add", "-A"))

    if not add_result.ok:

        return add_result

    return run_command(("git", "commit", "-m", message))

def git_push_feature_branch(branch: str) -> CommandResult:

    if is_main_branch(branch):

        return CommandResult(("git", "push", "origin", branch), 99, "", "push_main_forbidden")

    return run_command(("git", "push", "-u", "origin", branch))

def run_suite(

    *,

    suite: str,

    mode: str,

    commit_message: str,

    allow_commit: bool,

    allow_push_feature_branch: bool,

) -> int:

    branch = current_branch()

    head = current_head()

    safety_failures = validate_safe_mode(mode, branch, allow_commit, allow_push_feature_branch)

    results: list[CommandResult] = []

    first_failure = None

    committed = False

    pushed = False

    if safety_failures:

        first_failure = ",".join(safety_failures)

    else:

        for command in suite_commands(suite):

            result = run_command(command)

            results.append(result)

            if not result.ok:

                first_failure = " ".join(command)

                break

        if first_failure is None and mode in ("commit", "commit-push", "overnight"):

            if git_status_short():

                commit_result = git_commit(commit_message)

                results.append(commit_result)

                if commit_result.ok:

                    committed = True

                else:

                    first_failure = "git commit"

        if first_failure is None and mode in ("commit-push", "overnight"):

            push_result = git_push_feature_branch(branch)

            results.append(push_result)

            if push_result.ok:

                pushed = True

            else:

                first_failure = "git push feature branch"

    status = git_status_short()

    summary = {

        "generated_at": now_utc(),

        "branch": branch,

        "head": head,

        "suite": suite,

        "mode": mode,

        "overall_ok": first_failure is None,

        "first_failure": first_failure,

        "dirty_worktree": bool(status),

        "git_status_short": status,

        "committed": committed,

        "pushed": pushed,

        "report_path": str(REPORT_PATH),

        "summary_path": str(SUMMARY_PATH),

        "log_path": str(LOG_PATH),

        "safety_failures": safety_failures,

        "commands": [result.as_dict() for result in results],

    }

    append_log(results, summary)

    write_reports(summary, results)

    return 0 if first_failure is None else 1


def write_overnight_state(

    *,

    queue_path: str,

    stage_index: int,

    stage_count: int,

    stage_id: str,

    task_id: str,

    status: str,

    started_at: str,

    finished_at: str | None = None,

    first_failure: str | None = None,

) -> None:

    ensure_output_dirs()

    heartbeat = {

        "generated_at": now_utc(),

        "queue_path": queue_path,

        "stage_index": stage_index,

        "stage_count": stage_count,

        "stage_id": stage_id,

        "task_id": task_id,

        "status": status,

    }

    resume = {

        "queue_path": queue_path,

        "stage_index": stage_index,

        "stage_count": stage_count,

        "stage_id": stage_id,

        "task_id": task_id,

        "status": status,

        "started_at": started_at,

        "finished_at": finished_at,

        "first_failure": first_failure,

    }

    OVERNIGHT_HEARTBEAT_PATH.write_text(json.dumps(heartbeat, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    OVERNIGHT_RESUME_PATH.write_text(json.dumps(resume, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_overnight_reports(queue_summary: dict[str, object]) -> None:

    ensure_output_dirs()

    OVERNIGHT_SUMMARY_PATH.write_text(json.dumps(queue_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    index_payload = {

        "generated_at": queue_summary.get("generated_at"),

        "queue_path": queue_summary.get("queue_path"),

        "overall_ok": queue_summary.get("overall_ok"),

        "stage_count": queue_summary.get("stage_count"),

        "completed_stage_count": queue_summary.get("completed_stage_count"),

        "first_failure": queue_summary.get("first_failure"),

        "stages": queue_summary.get("stages", []),

    }

    OVERNIGHT_INDEX_PATH.write_text(json.dumps(index_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [

        "# Overnight Task Queue Report",

        "",

        f"- generated_at: `{queue_summary.get('generated_at')}`",

        f"- queue_path: `{queue_summary.get('queue_path')}`",

        f"- overall_ok: `{queue_summary.get('overall_ok')}`",

        f"- first_failure: `{queue_summary.get('first_failure') or ''}`",

        f"- stage_count: `{queue_summary.get('stage_count')}`",

        f"- completed_stage_count: `{queue_summary.get('completed_stage_count')}`",

        "",

        "## Stages",

        "",

    ]

    for stage in queue_summary.get("stages", []):

        if isinstance(stage, dict):

            lines.append(

                f"- `{stage.get('status')}` `{stage.get('stage_id')}` "

                f"task=`{stage.get('task_id')}` suite=`{stage.get('suite')}` mode=`{stage.get('mode')}`"

            )

    lines.extend([

        "",

        "## Safety",

        "",

        "- no cloud AI calls",

        "- no merge",

        "- no branch deletion",

        "- no push to main",

        "- no secret read",

        "- no provider live execution",

        "- no vault live write",

        "- no production autonomy",

        "",

    ])

    OVERNIGHT_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with OVERNIGHT_LOG_PATH.open("a", encoding="utf-8") as fh:

        fh.write("\n" + "=" * 80 + "\n")

        fh.write(f"overnight queue report at {now_utc()}\n")

        fh.write(json.dumps(queue_summary, indent=2, sort_keys=True) + "\n")



def load_queue(path: Path) -> dict[str, object]:

    return json.loads(path.read_text(encoding="utf-8"))

def run_queue(path: Path, fallback_mode: str, allow_commit: bool, allow_push_feature_branch: bool) -> int:

    queue = load_queue(path)

    tasks = queue.get("tasks", [])

    if not isinstance(tasks, list):

        raise SystemExit("queue_tasks_must_be_list")

    queue_path = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)

    started_at = now_utc()

    stages: list[dict[str, object]] = []

    first_failure = None

    exit_code = 0

    for index, task in enumerate(tasks, start=1):

        if not isinstance(task, dict):

            raise SystemExit("queue_task_must_be_object")

        stage_id = str(task.get("stage_id", f"stage-{index:03d}"))

        task_id = str(task.get("task_id", stage_id))

        suite = str(task.get("suite", "full"))

        mode = str(task.get("mode", fallback_mode))

        write_overnight_state(

            queue_path=queue_path,

            stage_index=index,

            stage_count=len(tasks),

            stage_id=stage_id,

            task_id=task_id,

            status="running",

            started_at=started_at,

        )

        exit_code = run_suite(

            suite=suite,

            mode=mode,

            commit_message=str(task.get("commit_message", "local train runner commit")),

            allow_commit=bool(task.get("allow_commit", allow_commit)),

            allow_push_feature_branch=bool(task.get("allow_push_feature_branch", allow_push_feature_branch)),

        )

        stage_status = "ok" if exit_code == 0 else "failed"

        stages.append({

            "stage_index": index,

            "stage_id": stage_id,

            "task_id": task_id,

            "suite": suite,

            "mode": mode,

            "status": stage_status,

            "exit_code": exit_code,

        })

        if exit_code != 0:

            first_failure = stage_id

            write_overnight_state(

                queue_path=queue_path,

                stage_index=index,

                stage_count=len(tasks),

                stage_id=stage_id,

                task_id=task_id,

                status="failed",

                started_at=started_at,

                finished_at=now_utc(),

                first_failure=first_failure,

            )

            break

        write_overnight_state(

            queue_path=queue_path,

            stage_index=index,

            stage_count=len(tasks),

            stage_id=stage_id,

            task_id=task_id,

            status="ok",

            started_at=started_at,

            finished_at=now_utc(),

        )

    queue_summary = {

        "generated_at": now_utc(),

        "queue_path": queue_path,

        "overall_ok": first_failure is None,

        "first_failure": first_failure,

        "stage_count": len(tasks),

        "completed_stage_count": len(stages),

        "stages": stages,

        "report_path": str(OVERNIGHT_REPORT_PATH),

        "summary_path": str(OVERNIGHT_SUMMARY_PATH),

        "index_path": str(OVERNIGHT_INDEX_PATH),

        "resume_path": str(OVERNIGHT_RESUME_PATH),

        "heartbeat_path": str(OVERNIGHT_HEARTBEAT_PATH),

        "log_path": str(OVERNIGHT_LOG_PATH),

    }

    write_overnight_reports(queue_summary)

    return exit_code

def main(argv: Sequence[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description="Local-only train runner")

    parser.add_argument("--suite", choices=ALLOWED_SUITES, default="full")

    parser.add_argument("--mode", choices=ALLOWED_MODES, default="verify")

    parser.add_argument("--commit-message", default="local train runner commit")

    parser.add_argument("--allow-commit", action="store_true")

    parser.add_argument("--allow-push-feature-branch", action="store_true")

    parser.add_argument("--queue", default="")

    args = parser.parse_args(argv)

    if args.queue:

        return run_queue(

            ROOT / args.queue,

            args.mode,

            args.allow_commit,

            args.allow_push_feature_branch,

        )

    return run_suite(

        suite=args.suite,

        mode=args.mode,

        commit_message=args.commit_message,

        allow_commit=args.allow_commit,

        allow_push_feature_branch=args.allow_push_feature_branch,

    )

if __name__ == "__main__":

    raise SystemExit(main())

