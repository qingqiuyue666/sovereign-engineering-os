"""Policy-controlled patch apply handler."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

from creative.common import load_json, write_json
from execution_plane.repair.repair_ledger import append_repair_event


def apply_patch_for_job(
    job_path: str | Path,
    patch_path: str | Path,
    *,
    repo_root: str | Path = ".",
    output_root: str | Path = "work/repair_jobs",
) -> dict[str, Any]:
    job = load_json(Path(job_path))
    job_dir = Path(job_path).parent
    if job.get("auto_apply") is not True:
        bundle = {
            "schema_version": "seos.patch_repair_failure_bundle.v1",
            "repair_id": job.get("repair_id"),
            "failure_code": "AUTO_APPLY_DISABLED",
            "message": "patch application is policy-blocked; operator must review",
        }
        write_json(job_dir / "patch_apply_blocked.json", bundle)
        append_repair_event(output_root, {"repair_id": job.get("repair_id"), "event": "PATCH_APPLY_BLOCKED", "status": "BLOCKED"})
        return {"ok": False, "receipt_path": (job_dir / "patch_apply_blocked.json").as_posix(), "receipt": bundle}
    check = subprocess.run(["git", "apply", "--check", str(patch_path)], cwd=Path(repo_root), check=False, capture_output=True, text=True)
    if check.returncode != 0:
        receipt = {
            "schema_version": "seos.patch_apply_receipt.v1",
            "repair_id": job.get("repair_id"),
            "status": "FAILED",
            "failure_code": "PATCH_CHECK_FAILED",
            "stderr": check.stderr[-4000:],
        }
        write_json(job_dir / "patch_apply_receipt.json", receipt)
        append_repair_event(output_root, {"repair_id": job.get("repair_id"), "event": "PATCH_APPLY_FAILED", "status": "FAILED"})
        return {"ok": False, "receipt_path": (job_dir / "patch_apply_receipt.json").as_posix(), "receipt": receipt}
    applied = subprocess.run(["git", "apply", str(patch_path)], cwd=Path(repo_root), check=False, capture_output=True, text=True)
    receipt = {
        "schema_version": "seos.patch_apply_receipt.v1",
        "repair_id": job.get("repair_id"),
        "status": "SUCCEEDED" if applied.returncode == 0 else "FAILED",
        "exit_code": applied.returncode,
        "stderr": applied.stderr[-4000:],
    }
    write_json(job_dir / "patch_apply_receipt.json", receipt)
    append_repair_event(output_root, {"repair_id": job.get("repair_id"), "event": "PATCH_APPLY_ATTEMPTED", "status": receipt["status"]})
    return {"ok": applied.returncode == 0, "receipt_path": (job_dir / "patch_apply_receipt.json").as_posix(), "receipt": receipt}
