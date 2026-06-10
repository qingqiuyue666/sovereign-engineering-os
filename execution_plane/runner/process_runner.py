"""Controlled subprocess runner for permit-gated execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import subprocess

from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import (
    ExecutionPermitValidationError,
    validate_execution_permit,
)
from execution_plane.runner.path_guard import (
    PathGuardError,
    assert_within_root,
    resolve_output_root,
    validate_relative_output_path,
)
from execution_plane.runner.resource_guard import output_budget_violations
from execution_plane.runner.result_envelope import (
    build_execution_result,
    collect_output_records,
    utc_now,
)


def run_controlled_process(
    *,
    permit: Mapping[str, Any],
    command: Sequence[str],
    declared_output_paths: Sequence[str] = (),
    now=None,
) -> dict[str, Any]:
    """Run a subprocess under a validated execution permit.

    The runner does not claim to be an OS sandbox. It validates the permit,
    rejects declared output escapes before launch, runs with a timeout, and
    returns only digests and relative output records.
    """

    started_at = utc_now()
    try:
        checked = validate_execution_permit(permit, now=now)
    except ExecutionPermitValidationError as exc:
        return _blocked_result(
            permit=permit,
            started_at=started_at,
            policy_blocks=exc.errors,
            failure_summary="permit_validation_failed",
        )

    output_root = resolve_output_root(str(checked["allowed_output_root"]))
    output_root.mkdir(parents=True, exist_ok=True)
    policy_blocks: list[str] = []
    for relative_path in declared_output_paths:
        try:
            safe_relative = validate_relative_output_path(relative_path)
            assert_within_root(safe_relative, output_root)
        except PathGuardError as exc:
            policy_blocks.append(str(exc))
    if policy_blocks:
        return _blocked_result(
            permit=checked,
            started_at=started_at,
            output_root=output_root,
            policy_blocks=policy_blocks,
            failure_summary="path_guard_blocked",
        )

    run_id = stable_id("RUN", checked["permit_id"], started_at)
    try:
        completed = subprocess.run(
            list(command),
            cwd=output_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=int(checked["max_runtime_seconds"]),
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        status = "SUCCEEDED" if completed.returncode == 0 else "FAILED"
        failure_summary = None if status == "SUCCEEDED" else "process_exit_nonzero"
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        status = "TIMED_OUT"
        failure_summary = "process_timeout"
        exit_code = -1

    outputs = collect_output_records(output_root)
    resource_blocks = output_budget_violations(
        output_root,
        max_files=int(checked["max_files"]),
        max_output_bytes=int(checked["max_output_bytes"]),
    )
    if resource_blocks:
        status = "BLOCKED"
        failure_summary = "output_budget_exceeded"
        policy_blocks.extend(resource_blocks)

    return build_execution_result(
        permit=checked,
        run_id=run_id,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=exit_code,
        status=status,
        output_root=output_root,
        outputs=outputs,
        stdout=stdout,
        stderr=stderr,
        failure_summary=failure_summary,
        policy_blocks=policy_blocks,
        evidence_manifest_path=None,
    )


def _blocked_result(
    *,
    permit: Mapping[str, Any],
    started_at: str,
    policy_blocks: list[str],
    failure_summary: str,
    output_root: Path | None = None,
) -> dict[str, Any]:
    fallback = dict(permit)
    fallback.setdefault("permit_id", "PERMIT_BLOCKED")
    fallback.setdefault("allowed_adapter", fallback.get("allowed_adapter", "unknown"))
    root = output_root or Path(str(fallback.get("allowed_output_root", "blocked-output")))
    run_id = stable_id("RUN", fallback["permit_id"], started_at, "blocked")
    return build_execution_result(
        permit=fallback,
        run_id=run_id,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=-1,
        status="BLOCKED",
        output_root=root,
        outputs=[],
        stdout="",
        stderr="",
        failure_summary=failure_summary,
        policy_blocks=policy_blocks,
        evidence_manifest_path=None,
    )

