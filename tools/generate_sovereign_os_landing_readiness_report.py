"""Generate the deterministic Sovereign OS landing readiness report."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.os_engine.builtin_workers import hfx_008_real_run_commands
from kernel.os_engine.local_os_runtime import LocalOSRuntime


REPORT_DIR = Path("reports/sovereign_os_landing_readiness")
JSON_NAME = "landing_readiness.json"
README_NAME = "README.md"


def generate_report(*, repo_root: Path | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    repo = (repo_root or Path.cwd()).resolve()
    out = (output_dir or repo / REPORT_DIR).resolve()
    with tempfile.TemporaryDirectory(prefix="sovereign_os_readiness_") as tmp:
        with LocalOSRuntime(root=Path(tmp), repo_root=repo) as runtime:
            summary = runtime.summary()
            runtime_status = summary.to_dict()
    payload: dict[str, Any] = {
        "artifact_store_status": {
            "backend": "sqlite",
            "metadata_only": True,
            "large_binary_vendoring": False,
        },
        "built_in_worker_status": {
            "registered_workers": runtime_status["registered_workers"],
            "minimum_workers_present": all(
                worker in runtime_status["registered_workers"]
                for worker in ("artifact_review", "context_pack", "git_status", "hfx_008_materialization_dry_run")
            ),
        },
        "current_git_commit": _git(repo, "rev-parse", "HEAD"),
        "desktop_smoke_status": {
            "headless_entrypoint": "apps/desktop_local_smoke.py",
            "gui_opened_by_tests": False,
        },
        "final_claim_allowed": False,
        "hfx_008_dry_run_landing_status": {
            "chain_file": "kernel/os_engine/hfx_008_landing_chain.py",
            "dry_run_only": True,
            "physical_proof_created": False,
            "human_review_required": True,
        },
        "hfx_pipeline_scaffolding_status": {
            "decision": "defer",
            "audit_file": "docs/research/hfx_pipeline_scaffolding_branch_audit_v1.md",
            "merged_now": False,
        },
        "human_review_gate_status": {
            "hard_gate": True,
            "approval_required_for_final_claim": True,
        },
        "local_runtime_status": {
            "runtime_file": "kernel/os_engine/local_os_runtime.py",
            "schema_version": runtime_status["schema_version"],
            "worker_count": len(runtime_status["registered_workers"]),
            "executed_jobs_on_init": runtime_status["executed_jobs_on_init"],
        },
        "next_real_run_command_list": hfx_008_real_run_commands(repo),
        "os_core_v2_v3_status": {
            "local_job_queue": "landed",
            "worker_registry": "landed",
            "artifact_store": "landed",
            "sqlite_wal_brain": "landed",
            "event_sourced_projection": "landed",
        },
        "real_files_referenced": [
            "kernel/os_engine/local_os_runtime.py",
            "kernel/os_engine/builtin_workers.py",
            "kernel/os_engine/local_job_runner.py",
            "apps/desktop_local_smoke.py",
            "kernel/os_engine/hfx_008_landing_chain.py",
            "docs/operator/sovereign_os_local_landing_runbook_v1.md",
            "docs/research/hfx_pipeline_scaffolding_branch_audit_v1.md",
        ],
        "remaining_blockers": [
            "real HFX_008 visual proof artifact missing",
            "human approval missing for final physical proof",
            "external DCC proof must be run manually by an operator later",
        ],
        "resource_warning_status": {
            "warning_as_error_tests": "tests/tracer_bullet/test_os_engine_sqlite_resource_cleanup.py",
            "global_suppression": False,
        },
        "sqlite_wal_status": {
            "journal_mode": runtime_status["journal_mode"],
            "schema_version": runtime_status["schema_version"],
            "db_path_runtime_owned": True,
        },
    }
    normalized = json.loads(json.dumps(payload, sort_keys=True))
    _validate_referenced_files(repo, normalized["real_files_referenced"])
    out.mkdir(parents=True, exist_ok=True)
    (out / JSON_NAME).write_text(json.dumps(normalized, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out / README_NAME).write_text(_markdown(normalized), encoding="utf-8")
    return normalized


def main() -> int:
    payload = generate_report()
    print(json.dumps({"final_claim_allowed": payload["final_claim_allowed"], "report_dir": str(REPORT_DIR)}, sort_keys=True))
    return 0


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _validate_referenced_files(repo: Path, files: list[str]) -> None:
    missing = [item for item in files if not (repo / item).is_file()]
    if missing:
        raise RuntimeError(f"report references missing files: {', '.join(missing)}")


def _markdown(payload: dict[str, Any]) -> str:
    blockers = "\n".join(f"- {item}" for item in payload["remaining_blockers"])
    commands = "\n".join(f"- `{item}`" for item in payload["next_real_run_command_list"])
    return "\n".join(
        [
            "# Sovereign OS Landing Readiness",
            "",
            f"- Current git commit: `{payload['current_git_commit']}`",
            f"- SQLite WAL status: `{payload['sqlite_wal_status']['journal_mode']}`",
            f"- Local runtime file: `{payload['local_runtime_status']['runtime_file']}`",
            f"- Built-in workers ready: `{payload['built_in_worker_status']['minimum_workers_present']}`",
            f"- Desktop smoke entrypoint: `{payload['desktop_smoke_status']['headless_entrypoint']}`",
            "- Final claim allowed: `false`",
            "",
            "## Remaining Blockers",
            blockers,
            "",
            "## Next Real-Run Commands",
            commands,
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
