"""Patch repair job writer."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.permits.builder import stable_id
from execution_plane.repair.classifier import classify_repairable_failure
from execution_plane.repair.patch_job import PatchRepairJob
from execution_plane.repair.repair_ledger import append_repair_event
from execution_plane.runner.result_envelope import utc_now


def create_patch_repair_job(
    failure_bundle_path: str | Path,
    *,
    output_root: str | Path = "work/repair_jobs",
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(failure_bundle_path)
    bundle = load_json(source)
    classification = classify_repairable_failure(bundle)
    policy_payload = dict(policy or bundle.get("patch_repair_policy") or {})
    allowed_tools = tuple(str(tool) for tool in policy_payload.get("allowed_tools", ["cline", "aider"]))
    mode = str(policy_payload.get("mode", "generate_patch_then_test"))
    auto_apply = bool(policy_payload.get("auto_apply", False))
    max_iterations = int(policy_payload.get("max_iterations", 2))
    repair_id = stable_id("REPAIR", source.as_posix(), classification["failure_code"], utc_now())
    job_root = Path(output_root) / repair_id
    job_root.mkdir(parents=True, exist_ok=True)
    job = PatchRepairJob(
        repair_id=repair_id,
        source_failure_bundle=source.as_posix(),
        failure_code=str(classification["failure_code"]),
        target_files=tuple(str(item) for item in classification["target_files"]),
        reproduction_command=str(bundle.get("reproduction_command") or ""),
        test_commands=tuple(str(item) for item in bundle.get("test_commands", []) if str(item)),
        allowed_tools=allowed_tools,
        mode=mode,
        auto_apply=auto_apply,
        max_iterations=max_iterations,
        status="READY" if classification["repairable"] else "BLOCKED",
        classification=classification,
    )
    job_payload = job.as_dict()
    write_json(job_root / "patch_repair_job.json", job_payload)
    write_json(job_root / "source_failure_bundle.json", bundle)
    append_repair_event(
        output_root,
        {
            "repair_id": repair_id,
            "event": "PATCH_REPAIR_JOB_CREATED",
            "status": job.status,
            "failure_code": job.failure_code,
        },
    )
    if job.status != "READY":
        write_json(
            job_root / "repair_failure_bundle.json",
            {
                "schema_version": "seos.patch_repair_failure_bundle.v1",
                "repair_id": repair_id,
                "failure_code": "PATCH_REPAIR_NOT_APPLICABLE",
                "classification": classification,
            },
        )
    return {
        "ok": job.status == "READY",
        "repair_id": repair_id,
        "job_path": (job_root / "patch_repair_job.json").as_posix(),
        "job": job_payload,
    }
