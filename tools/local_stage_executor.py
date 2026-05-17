
#!/usr/bin/env python3

"""Autonomous local stage executor.

Executes only allowlisted local stage scripts from the stage script registry.

No freeform shell, no cloud AI, no merge, no push main, no branch delete,

no secret reads, no provider live execution, no vault live write.

"""

from __future__ import annotations

import argparse

import datetime as dt

import json

import subprocess

import sys

from dataclasses import dataclass

from pathlib import Path

from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

REGISTRY_PATH = ROOT / "governance/local_train/stage_script_registry_v1.json"

LOG_PATH = ROOT / "outputs/logs/autonomous_stage_executor.log"

REPORT_PATH = ROOT / "outputs/reports/autonomous_stage_executor_report.md"

SUMMARY_PATH = ROOT / "outputs/reports/autonomous_stage_executor_summary.json"

FORBIDDEN_STAGE_TYPES = {

    "cloud_ai",

    "freeform_shell",

    "production_execution",

    "provider_live_execution",

    "vault_live_write",

    "deployment",

}

FORBIDDEN_AUTHORITY_FAILURES = (

    "push_main_forbidden",

    "main_branch_mutation_forbidden",

    "git_merge_forbidden",

    "git_branch_delete_forbidden",

)

@dataclass(frozen=True)

class StageScript:

    script_id: str

    stage_type: str

    script_path: str

    allow_commit: bool

    allow_push_feature_branch: bool

@dataclass(frozen=True)

class StageExecutionResult:

    accepted: bool

    script_id: str

    script_path: str

    returncode: int

    failures: tuple[str, ...]

    stdout: str

    stderr: str

    @property

    def ok(self) -> bool:

        return self.accepted and self.returncode == 0 and not self.failures

    def as_dict(self) -> dict[str, object]:

        return {

            "accepted": self.accepted,

            "script_id": self.script_id,

            "script_path": self.script_path,

            "returncode": self.returncode,

            "ok": self.ok,

            "failures": list(self.failures),

            "stdout_tail": self.stdout[-4000:],

            "stderr_tail": self.stderr[-4000:],

        }

def now_utc() -> str:

    return dt.datetime.now(dt.UTC).isoformat()

def ensure_output_dirs() -> None:

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_registry(path: Path = REGISTRY_PATH) -> dict[str, object]:

    return json.loads(path.read_text(encoding="utf-8"))

def _bool_field(payload: Mapping[str, object], key: str) -> bool:

    value = payload.get(key)

    if not isinstance(value, bool):

        raise ValueError(f"{key}_must_be_bool")

    return value

def find_script(script_id: str, registry: Mapping[str, object]) -> StageScript:

    scripts = registry.get("scripts")

    if not isinstance(scripts, list):

        raise ValueError("registry_scripts_must_be_list")

    for item in scripts:

        if not isinstance(item, dict):

            raise ValueError("registry_script_must_be_object")

        if item.get("script_id") == script_id:

            stage_type = item.get("stage_type")

            script_path = item.get("script_path")

            if not isinstance(stage_type, str) or not stage_type.strip():

                raise ValueError("stage_type_required")

            if not isinstance(script_path, str) or not script_path.strip():

                raise ValueError("script_path_required")

            return StageScript(

                script_id=script_id,

                stage_type=stage_type,

                script_path=script_path,

                allow_commit=_bool_field(item, "allow_commit"),

                allow_push_feature_branch=_bool_field(item, "allow_push_feature_branch"),

            )

    raise ValueError("stage_id_must_be_registered")

def validate_script(script: StageScript) -> tuple[str, ...]:

    failures: list[str] = []

    if script.stage_type in FORBIDDEN_STAGE_TYPES:

        failures.append("forbidden_stage_type")

    if script.stage_type not in {"verification", "local_script"}:

        failures.append("stage_type_not_allowed")

    if script.allow_commit:

        failures.append("stage_script_commit_forbidden_v1")

    if script.allow_push_feature_branch:

        failures.append("stage_script_push_forbidden_v1")

    path = Path(script.script_path)

    if path.is_absolute():

        failures.append("absolute_script_path_forbidden")

    if ".." in path.parts:

        failures.append("path_traversal_forbidden")

    if not script.script_path.startswith("tools/local_stage_scripts/"):

        failures.append("script_path_not_allowlisted")

    if path.suffix != ".py":

        failures.append("script_must_be_python")

    full_path = ROOT / path

    if not full_path.is_file():

        failures.append("script_file_missing")

    return tuple(failures)

def run_stage_script(script: StageScript) -> StageExecutionResult:

    failures = validate_script(script)

    if failures:

        return StageExecutionResult(

            accepted=False,

            script_id=script.script_id,

            script_path=script.script_path,

            returncode=99,

            failures=failures,

            stdout="",

            stderr="",

        )

    result = subprocess.run(

        ("python3", script.script_path),

        cwd=ROOT,

        text=True,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        check=False,

    )

    return StageExecutionResult(

        accepted=True,

        script_id=script.script_id,

        script_path=script.script_path,

        returncode=result.returncode,

        failures=(),

        stdout=result.stdout,

        stderr=result.stderr,

    )

def write_reports(result: StageExecutionResult) -> None:

    ensure_output_dirs()

    summary = {

        "generated_at": now_utc(),

        "overall_ok": result.ok,

        "result": result.as_dict(),

        "report_path": str(REPORT_PATH),

        "summary_path": str(SUMMARY_PATH),

        "log_path": str(LOG_PATH),

    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [

        "# Autonomous Stage Executor Report",

        "",

        f"- generated_at: `{summary['generated_at']}`",

        f"- overall_ok: `{summary['overall_ok']}`",

        f"- script_id: `{result.script_id}`",

        f"- script_path: `{result.script_path}`",

        f"- returncode: `{result.returncode}`",

        f"- failures: `{', '.join(result.failures)}`",

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

    ]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with LOG_PATH.open("a", encoding="utf-8") as fh:

        fh.write("\n" + "=" * 80 + "\n")

        fh.write(f"autonomous stage executor run at {now_utc()}\n")

        fh.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")

        if result.stdout:

            fh.write("\n[stdout]\n")

            fh.write(result.stdout)

        if result.stderr:

            fh.write("\n[stderr]\n")

            fh.write(result.stderr)

def execute_stage(script_id: str) -> StageExecutionResult:

    registry = load_registry()

    script = find_script(script_id, registry)

    result = run_stage_script(script)

    write_reports(result)

    return result

def main(argv: Sequence[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description="Autonomous local stage executor")

    parser.add_argument("--script-id", required=True)

    args = parser.parse_args(argv)

    result = execute_stage(args.script_id)

    return 0 if result.ok else 1

if __name__ == "__main__":

    raise SystemExit(main())

