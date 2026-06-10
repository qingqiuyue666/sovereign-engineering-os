"""Local patch tool bridge."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import subprocess

from creative.common import load_json, write_json
from execution_plane.repair.repair_ledger import append_repair_event


def invoke_local_patch_tool(
    job_path: str | Path,
    *,
    tool_command: Sequence[str] | None = None,
    output_root: str | Path = "work/repair_jobs",
) -> dict[str, Any]:
    job = load_json(Path(job_path))
    job_dir = Path(job_path).parent
    prompt_path = job_dir / "patch_prompt.md"
    prompt_path.write_text(_prompt_for_job(job), encoding="utf-8")
    command = list(tool_command or _default_tool_command(job))
    if not command:
        return _tool_failure(job, job_dir, output_root, "LOCAL_TOOL_UNAVAILABLE", "no allowed local patch tool found")
    completed = subprocess.run(command, cwd=Path.cwd(), check=False, capture_output=True, text=True)
    result = {
        "schema_version": "seos.local_patch_tool_result.v1",
        "repair_id": job.get("repair_id"),
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "prompt_path": prompt_path.as_posix(),
    }
    write_json(job_dir / "local_tool_result.json", result)
    append_repair_event(
        output_root,
        {
            "repair_id": job.get("repair_id"),
            "event": "LOCAL_PATCH_TOOL_INVOKED",
            "status": "SUCCEEDED" if completed.returncode == 0 else "FAILED",
            "exit_code": completed.returncode,
        },
    )
    if completed.returncode != 0:
        write_json(
            job_dir / "repair_failure_bundle.json",
            {
                "schema_version": "seos.patch_repair_failure_bundle.v1",
                "repair_id": job.get("repair_id"),
                "failure_code": "LOCAL_TOOL_FAILED",
                "exit_code": completed.returncode,
                "stderr": completed.stderr[-4000:],
            },
        )
    return {"ok": completed.returncode == 0, "result_path": (job_dir / "local_tool_result.json").as_posix(), "result": result}


def _default_tool_command(job: Mapping[str, Any]) -> list[str]:
    raw_command = job.get("tool_command")
    if isinstance(raw_command, list):
        return [str(item) for item in raw_command if str(item)]
    if isinstance(raw_command, str) and raw_command:
        return [raw_command]
    return []


def _prompt_for_job(job: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# SEOS Patch Repair Job",
            "",
            f"Repair ID: {job.get('repair_id')}",
            f"Failure code: {job.get('failure_code')}",
            "Target files:",
            *[f"- {item}" for item in job.get("target_files", [])],
            "",
            f"Reproduction command: {job.get('reproduction_command')}",
            "Test commands:",
            *[f"- {item}" for item in job.get("test_commands", [])],
            "",
            "Generate a minimal patch. Do not apply it unless the job policy allows auto_apply.",
        ]
    )


def _tool_failure(
    job: Mapping[str, Any],
    job_dir: Path,
    output_root: str | Path,
    failure_code: str,
    message: str,
) -> dict[str, Any]:
    bundle = {
        "schema_version": "seos.patch_repair_failure_bundle.v1",
        "repair_id": job.get("repair_id"),
        "failure_code": failure_code,
        "message": message,
    }
    write_json(job_dir / "repair_failure_bundle.json", bundle)
    append_repair_event(
        output_root,
        {
            "repair_id": job.get("repair_id"),
            "event": "LOCAL_PATCH_TOOL_UNAVAILABLE",
            "status": "FAILED",
            "failure_code": failure_code,
        },
    )
    return {"ok": False, "failure_bundle_path": (job_dir / "repair_failure_bundle.json").as_posix(), "failure_bundle": bundle}
