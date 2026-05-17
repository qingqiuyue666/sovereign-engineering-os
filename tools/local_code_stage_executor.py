
#!/usr/bin/env python3

"""Autonomous local code stage executor.

Executes only registered local code stages from code_stage_registry_v1.

No cloud AI, no freeform shell, no secrets, no main mutation, no merge,

no push main, no branch deletion, no production execution.

"""

from __future__ import annotations

import argparse

import datetime as dt

import json

import subprocess

from dataclasses import dataclass

from pathlib import Path

from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

REGISTRY_PATH = ROOT / "governance/local_train/code_stage_registry_v1.json"

LOG_PATH = ROOT / "outputs/logs/autonomous_code_stage.log"

REPORT_PATH = ROOT / "outputs/reports/autonomous_code_stage_report.md"

SUMMARY_PATH = ROOT / "outputs/reports/autonomous_code_stage_summary.json"

DIFF_PATH = ROOT / "outputs/reports/autonomous_code_stage_diff.json"

ALLOWED_STAGE_TYPES = {

    "local_code_generation",

    "local_code_patch",

    "verification",

}

FORBIDDEN_STAGE_TYPES = {

    "cloud_ai",

    "freeform_shell",

    "production_execution",

    "provider_live_execution",

    "vault_live_write",

    "production_autonomy",

    "deployment",

    "unbounded_generation",

}

ALLOWED_ROOTS = (

    "tools/local_code_stages/",

    "governance/local_train/",

    "governance/security/",

    "docs/runbooks/",

    "tests/tracer_bullet/",

)

FORBIDDEN_ROOTS = (

    ".env",

    ".git/",

    "outputs/",

    "kernel/runtime/",

    "kernel/security/",

    "validation/",

    "governance/root/",

)

MAX_LINES_ADDED_PER_STAGE = 2000

MAX_FILES_CHANGED_PER_STAGE = 12

@dataclass(frozen=True)

class CodeStage:

    stage_id: str

    stage_type: str

    script_path: str

    allowed_write_paths: tuple[str, ...]

    verification_commands: tuple[str, ...]

    allow_commit: bool

    allow_push_feature_branch: bool

@dataclass(frozen=True)

class CodeStageResult:

    accepted: bool

    stage_id: str

    script_path: str

    returncode: int

    failures: tuple[str, ...]

    changed_files: tuple[str, ...]

    lines_added: int

    stdout: str

    stderr: str

    @property

    def ok(self) -> bool:

        return self.accepted and self.returncode == 0 and not self.failures

    def as_dict(self) -> dict[str, object]:

        return {

            "accepted": self.accepted,

            "stage_id": self.stage_id,

            "script_path": self.script_path,

            "returncode": self.returncode,

            "ok": self.ok,

            "failures": list(self.failures),

            "changed_files": list(self.changed_files),

            "lines_added": self.lines_added,

            "stdout_tail": self.stdout[-4000:],

            "stderr_tail": self.stderr[-4000:],

        }

def now_utc() -> str:

    return dt.datetime.now(dt.UTC).isoformat()

def ensure_output_dirs() -> None:

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    DIFF_PATH.parent.mkdir(parents=True, exist_ok=True)

def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:

    return subprocess.run(

        tuple(command),

        cwd=ROOT,

        text=True,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        check=False,

    )

def load_registry(path: Path = REGISTRY_PATH) -> dict[str, object]:

    return json.loads(path.read_text(encoding="utf-8"))

def _bool_field(payload: Mapping[str, object], key: str) -> bool:

    value = payload.get(key)

    if not isinstance(value, bool):

        raise ValueError(f"{key}_must_be_bool")

    return value

def _string_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:

    value = payload.get(key)

    if not isinstance(value, list):

        raise ValueError(f"{key}_must_be_list")

    result: list[str] = []

    for item in value:

        if not isinstance(item, str) or not item.strip():

            raise ValueError(f"{key}_item_must_be_nonempty_string")

        result.append(item)

    return tuple(result)

def find_stage(stage_id: str, registry: Mapping[str, object]) -> CodeStage:

    stages = registry.get("stages")

    if not isinstance(stages, list):

        raise ValueError("registry_stages_must_be_list")

    for item in stages:

        if not isinstance(item, dict):

            raise ValueError("registry_stage_must_be_object")

        if item.get("stage_id") == stage_id:

            stage_type = item.get("stage_type")

            script_path = item.get("script_path")

            if not isinstance(stage_type, str) or not stage_type.strip():

                raise ValueError("stage_type_required")

            if not isinstance(script_path, str) or not script_path.strip():

                raise ValueError("script_path_required")

            return CodeStage(

                stage_id=stage_id,

                stage_type=stage_type,

                script_path=script_path,

                allowed_write_paths=_string_tuple(item, "allowed_write_paths"),

                verification_commands=_string_tuple(item, "verification_commands"),

                allow_commit=_bool_field(item, "allow_commit"),

                allow_push_feature_branch=_bool_field(item, "allow_push_feature_branch"),

            )

    raise ValueError("stage_id_must_be_registered")

def _path_allowed(path: str, allowed_paths: tuple[str, ...]) -> bool:

    if path not in allowed_paths:

        return False

    if any(path == root or path.startswith(root) for root in FORBIDDEN_ROOTS):

        return False

    return any(path.startswith(root) for root in ALLOWED_ROOTS)

def validate_stage(stage: CodeStage) -> tuple[str, ...]:

    failures: list[str] = []

    if stage.stage_type in FORBIDDEN_STAGE_TYPES:

        failures.append("forbidden_stage_type")

    if stage.stage_type not in ALLOWED_STAGE_TYPES:

        failures.append("stage_type_not_allowed")

    if stage.allow_commit:

        failures.append("code_stage_commit_forbidden_v1")

    if stage.allow_push_feature_branch:

        failures.append("code_stage_push_forbidden_v1")

    script_path = Path(stage.script_path)

    if script_path.is_absolute():

        failures.append("absolute_script_path_forbidden")

    if ".." in script_path.parts:

        failures.append("path_traversal_forbidden")

    if not stage.script_path.startswith("tools/local_code_stages/"):

        failures.append("script_path_not_allowlisted")

    if script_path.suffix != ".py":

        failures.append("script_must_be_python")

    if not (ROOT / script_path).is_file():

        failures.append("script_file_missing")

    for write_path in stage.allowed_write_paths:

        if not _path_allowed(write_path, stage.allowed_write_paths):

            failures.append(f"write_path_not_allowlisted:{write_path}")

    for command in stage.verification_commands:

        if "&&" in command or ";" in command or "|" in command:

            failures.append("verification_command_freeform_shell_forbidden")

        if command.startswith("git merge") or command.startswith("git push origin main"):

            failures.append("verification_command_forbidden")

    return tuple(failures)

def git_changed_files() -> tuple[str, ...]:

    result = run_command(("git", "status", "--short", "--untracked-files=all"))

    files: list[str] = []

    for line in result.stdout.splitlines():

        item = line[3:].strip()

        if item:

            files.append(item)

    return tuple(files)

def git_numstat() -> tuple[int, int]:

    result = run_command(("git", "diff", "--numstat"))

    added = 0

    files = 0

    for line in result.stdout.splitlines():

        parts = line.split()

        if len(parts) >= 3 and parts[0].isdigit():

            added += int(parts[0])

            files += 1

    return added, files

def validate_diff(stage: CodeStage) -> tuple[tuple[str, ...], int, tuple[str, ...]]:

    changed = git_changed_files()

    lines_added, file_count = git_numstat()

    failures: list[str] = []

    if lines_added > MAX_LINES_ADDED_PER_STAGE:

        failures.append("line_budget_exceeded")

    if file_count > MAX_FILES_CHANGED_PER_STAGE:

        failures.append("file_budget_exceeded")

    for path in changed:

        if path.startswith("?? "):

            path = path[3:]

        if not _path_allowed(path, stage.allowed_write_paths) and path not in {

            "governance/local_train/code_stage_registry_v1.json",

            "governance/security/autonomous_code_stage_policy_v1.json",

            "tools/local_code_stages/generate_local_code_stage_example.py",

            "tools/local_code_stage_executor.py",

            "tests/tracer_bullet/test_autonomous_code_stage.py",

            "docs/runbooks/autonomous_code_stage_v1.md",

        }:

            failures.append(f"changed_path_not_allowlisted:{path}")

    return changed, lines_added, tuple(failures)

def run_verification_commands(commands: tuple[str, ...]) -> tuple[int, str, str]:

    stdout_parts: list[str] = []

    stderr_parts: list[str] = []

    for command in commands:

        result = run_command(tuple(command.split()))

        stdout_parts.append(result.stdout)

        stderr_parts.append(result.stderr)

        if result.returncode != 0:

            return result.returncode, "".join(stdout_parts), "".join(stderr_parts)

    return 0, "".join(stdout_parts), "".join(stderr_parts)

def execute_code_stage(stage_id: str) -> CodeStageResult:

    registry = load_registry()

    stage = find_stage(stage_id, registry)

    failures = list(validate_stage(stage))

    if failures:

        result = CodeStageResult(False, stage.stage_id, stage.script_path, 99, tuple(failures), (), 0, "", "")

        write_reports(result)

        return result

    proc = run_command(("python3", stage.script_path))

    changed_files, lines_added, diff_failures = validate_diff(stage)

    failures.extend(diff_failures)

    verify_code, verify_stdout, verify_stderr = run_verification_commands(stage.verification_commands)

    stdout = proc.stdout + verify_stdout

    stderr = proc.stderr + verify_stderr

    returncode = proc.returncode if proc.returncode != 0 else verify_code

    result = CodeStageResult(

        accepted=not failures,

        stage_id=stage.stage_id,

        script_path=stage.script_path,

        returncode=returncode,

        failures=tuple(failures),

        changed_files=changed_files,

        lines_added=lines_added,

        stdout=stdout,

        stderr=stderr,

    )

    write_reports(result)

    return result

def write_reports(result: CodeStageResult) -> None:

    ensure_output_dirs()

    summary = {

        "generated_at": now_utc(),

        "overall_ok": result.ok,

        "result": result.as_dict(),

        "report_path": str(REPORT_PATH),

        "summary_path": str(SUMMARY_PATH),

        "diff_path": str(DIFF_PATH),

        "log_path": str(LOG_PATH),

    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    DIFF_PATH.write_text(

        json.dumps(

            {

                "generated_at": now_utc(),

                "stage_id": result.stage_id,

                "changed_files": list(result.changed_files),

                "lines_added": result.lines_added,

                "failures": list(result.failures),

            },

            indent=2,

            sort_keys=True,

        )

        + "\n",

        encoding="utf-8",

    )

    lines = [

        "# Autonomous Code Stage Report",

        "",

        f"- generated_at: `{summary['generated_at']}`",

        f"- overall_ok: `{summary['overall_ok']}`",

        f"- stage_id: `{result.stage_id}`",

        f"- script_path: `{result.script_path}`",

        f"- returncode: `{result.returncode}`",

        f"- lines_added: `{result.lines_added}`",

        f"- failures: `{', '.join(result.failures)}`",

        "",

        "## Changed Files",

        "",

    ]

    for path in result.changed_files:

        lines.append(f"- `{path}`")

    lines.extend([

        "",

        "## Safety",

        "",

        "- no cloud AI calls",

        "- no freeform shell",

        "- no merge",

        "- no push to main",

        "- no branch deletion",

        "- no secret read",

        "- no provider live execution",

        "- no vault live write",

        "",

    ])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with LOG_PATH.open("a", encoding="utf-8") as fh:

        fh.write("\n" + "=" * 80 + "\n")

        fh.write(f"autonomous code stage run at {now_utc()}\n")

        fh.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")

        if result.stdout:

            fh.write("\n[stdout]\n")

            fh.write(result.stdout)

        if result.stderr:

            fh.write("\n[stderr]\n")

            fh.write(result.stderr)

def main(argv: Sequence[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description="Autonomous local code stage executor")

    parser.add_argument("--stage-id", required=True)

    args = parser.parse_args(argv)

    result = execute_code_stage(args.stage_id)

    return 0 if result.ok else 1

if __name__ == "__main__":

    raise SystemExit(main())

