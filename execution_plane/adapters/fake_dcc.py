"""CI-safe fake DCC adapter that materializes real local files."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from creative.common import write_json
from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.path_guard import (
    PathGuardError,
    assert_within_root,
    resolve_output_root,
    validate_relative_output_path,
)
from execution_plane.runner.result_envelope import (
    build_execution_result,
    collect_output_records,
    utc_now,
)


def run_fake_dcc(
    permit: Mapping[str, Any],
    *,
    job: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = validate_execution_permit(
        permit,
        expected_adapter="fake_dcc",
        expected_action="smoke_generate_file",
    )
    started_at = utc_now()
    output_root = resolve_output_root(str(checked["allowed_output_root"]))
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = stable_id("RUN", checked["permit_id"], started_at, "fake_dcc")
    job_data = dict(job or {})
    output_relpath = str(job_data.get("output_path", "output.txt"))
    content = str(job_data.get("content", "SEOS fake DCC materialized output\n"))
    try:
        safe_output_relpath = validate_relative_output_path(output_relpath)
        output_path = assert_within_root(safe_output_relpath, output_root)
    except PathGuardError as exc:
        return build_execution_result(
            permit=checked,
            run_id=run_id,
            started_at=started_at,
            ended_at=utc_now(),
            exit_code=-1,
            status="BLOCKED",
            output_root=output_root,
            outputs=[],
            stdout="",
            stderr="",
            failure_summary="path_guard_blocked",
            policy_blocks=[str(exc)],
            evidence_manifest_path=None,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    manifest_path = output_root / "manifest.json"
    manifest_payload = {
        "schema_version": "seos_fake_dcc_manifest_v1",
        "adapter": "fake_dcc",
        "action": "smoke_generate_file",
        "run_id": run_id,
        "permit_id": checked["permit_id"],
        "outputs": [
            {
                "relative_path": safe_output_relpath,
            }
        ],
    }
    write_json(manifest_path, manifest_payload)
    outputs = collect_output_records(output_root)
    return build_execution_result(
        permit=checked,
        run_id=run_id,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=0,
        status="SUCCEEDED",
        output_root=output_root,
        outputs=outputs,
        stdout="fake_dcc completed",
        stderr="",
        failure_summary=None,
        policy_blocks=[],
        evidence_manifest_path="manifest.json",
    )

