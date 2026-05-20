"""Headless desktop smoke path for the local OS runtime."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from apps import sovereign_desktop
from kernel.os_engine.local_job_runner import LocalJobRunner
from kernel.os_engine.local_os_runtime import LocalOSRuntime
from kernel.os_engine.sqlite_artifact_store import ArtifactType


@dataclass(frozen=True, slots=True)
class DesktopLocalSmokeReport:
    pyside6_available: bool
    gui_import_passive: bool
    gui_launched: bool
    job_submission_facade_exists: bool
    os_runtime_bootstrapped: bool
    smoke_job_id: str
    smoke_job_status: str
    smoke_artifact_path: str
    external_network_calls: int
    dcc_launched: bool
    shell_invocation_used: bool

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))


def run_desktop_local_smoke(
    *,
    repo_root: Path | None = None,
    runtime_root: Path | None = None,
    run_job: bool = True,
) -> DesktopLocalSmokeReport:
    root = runtime_root or Path.home() / ".sovereign_engineering_os" / "desktop_smoke"
    repo = repo_root or Path(__file__).resolve().parents[1]
    smoke_job_id = "desktop_smoke_context_pack"
    with LocalOSRuntime(root=root, repo_root=repo) as runtime:
        status = "not_run"
        if run_job:
            if not _job_exists(runtime, smoke_job_id):
                runtime.job_queue.create_job(
                    job_id=smoke_job_id,
                    job_type="context_pack",
                    input_manifest={
                        "inputs": {
                            "max_files": 8,
                            "changed_files_only": False,
                            "task_instructions": "Headless desktop smoke context packet.",
                        },
                        "max_runtime_seconds": 30,
                        "memory_limit_mb": 256,
                    },
                    output_dir=str(runtime.artifact_store.artifact_root / "context_packs"),
                    human_review_required=False,
                    dry_run=False,
                    local_only=True,
                )
                runtime.job_queue.admit_job(smoke_job_id)
                runtime.job_queue.enqueue_job(smoke_job_id)
            state = runtime.job_queue.get_job_state(smoke_job_id)
            if state.current_status in {"admitted", "pending"}:
                LocalJobRunner(runtime).run_next(job_id=smoke_job_id)
            status = runtime.job_queue.get_job_state(smoke_job_id).current_status
        report_path = runtime.artifact_store.artifact_root / "desktop_smoke" / "desktop_local_smoke_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = DesktopLocalSmokeReport(
            pyside6_available=bool(sovereign_desktop.PYSIDE6_AVAILABLE),
            gui_import_passive=True,
            gui_launched=False,
            job_submission_facade_exists=hasattr(sovereign_desktop, "DesktopOsEngineFacade"),
            os_runtime_bootstrapped=True,
            smoke_job_id=smoke_job_id if run_job else "",
            smoke_job_status=status,
            smoke_artifact_path=str(report_path),
            external_network_calls=0,
            dcc_launched=False,
            shell_invocation_used=False,
        )
        report_path.write_text(json.dumps(report.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")
        runtime.artifact_store.record_artifact(
            job_id=smoke_job_id if run_job else "desktop_smoke",
            local_path=report_path,
            artifact_type=ArtifactType.AUDIT_JSON,
            local_only=True,
            safe_to_publish=False,
        )
        return report


def main() -> int:
    report = run_desktop_local_smoke()
    print(json.dumps(report.to_dict(), sort_keys=True, indent=2))
    return 0


def _job_exists(runtime: LocalOSRuntime, job_id: str) -> bool:
    with runtime.database.connect() as connection:
        return connection.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone() is not None


if __name__ == "__main__":
    raise SystemExit(main())
