"""Execution result envelope helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib

from execution_plane.artifacts import build_artifact_refs
from execution_plane.runner.path_guard import public_output_root_label

EXECUTION_RESULT_SCHEMA_VERSION = "seos_execution_result_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def collect_output_records(output_root: str | Path) -> list[dict[str, Any]]:
    root = Path(output_root).resolve()
    records: list[dict[str, Any]] = []
    if not root.exists():
        return records
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.resolve().relative_to(root).as_posix()
        records.append(
            {
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def build_execution_result(
    *,
    permit: Mapping[str, Any],
    run_id: str,
    started_at: str,
    ended_at: str,
    exit_code: int,
    status: str,
    output_root: str | Path,
    outputs: list[dict[str, Any]],
    stdout: str,
    stderr: str,
    failure_summary: str | None,
    policy_blocks: list[str] | None = None,
    evidence_manifest_path: str | None = None,
    state_transitions: list[dict[str, Any]] | None = None,
    provision_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    node_id = str(permit.get("allowed_action", "adapter_action"))
    return {
        "schema_version": EXECUTION_RESULT_SCHEMA_VERSION,
        "permit_id": str(permit["permit_id"]),
        "run_id": run_id,
        "adapter": str(permit["allowed_adapter"]),
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": exit_code,
        "status": status,
        "output_root": public_output_root_label(output_root),
        "outputs": outputs,
        "artifact_refs": build_artifact_refs(run_id=run_id, node_id=node_id, output_records=outputs),
        "stdout_digest": sha256_bytes(stdout.encode("utf-8", errors="replace")),
        "stderr_digest": sha256_bytes(stderr.encode("utf-8", errors="replace")),
        "failure_summary": failure_summary,
        "policy_blocks": list(policy_blocks or []),
        "evidence_manifest_path": evidence_manifest_path,
        "state_transitions": list(state_transitions or []),
        "provision_result": dict(provision_result or {}),
    }
