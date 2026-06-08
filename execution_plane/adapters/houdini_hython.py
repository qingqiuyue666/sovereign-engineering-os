"""Optional Houdini/hython adapter contract."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import shutil

from execution_plane.permits.builder import stable_id
from execution_plane.permits.validator import validate_execution_permit
from execution_plane.runner.process_runner import run_controlled_process
from execution_plane.runner.result_envelope import build_execution_result, utc_now


def detect_hython() -> str | None:
    return shutil.which("hython")


def run_houdini_hython_smoke(permit: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_execution_permit(
        permit,
        expected_adapter="houdini_hython",
        expected_action="houdini_generate_geometry_cache",
    )
    started_at = utc_now()
    hython = detect_hython()
    if not hython:
        return build_execution_result(
            permit=checked,
            run_id=stable_id("RUN", checked["permit_id"], started_at, "hython_missing"),
            started_at=started_at,
            ended_at=utc_now(),
            exit_code=-1,
            status="BLOCKED",
            output_root=Path(str(checked["allowed_output_root"])),
            outputs=[],
            stdout="",
            stderr="",
            failure_summary="ENV_NOT_FOUND: hython not found",
            policy_blocks=["ENV_NOT_FOUND"],
            evidence_manifest_path=None,
        )

    script = (
        "import json, pathlib\n"
        "root = pathlib.Path.cwd()\n"
        "payload = {'schema_version':'seos_houdini_hython_smoke_v1',"
        "'adapter':'houdini_hython','output':'hython_scene_summary.json'}\n"
        "(root / 'hython_scene_summary.json').write_text(json.dumps(payload, sort_keys=True) + '\\n', encoding='utf-8')\n"
    )
    result = run_controlled_process(
        permit=checked,
        command=[hython, "-c", script],
        declared_output_paths=["hython_scene_summary.json"],
    )
    if result["status"] != "SUCCEEDED":
        result = dict(result)
        result["status"] = "BLOCKED"
        result["failure_summary"] = "LICENSE_BLOCKED_OR_HYTHON_UNAVAILABLE"
        blocks = list(result.get("policy_blocks", []))
        if "LICENSE_BLOCKED" not in blocks:
            blocks.append("LICENSE_BLOCKED")
        result["policy_blocks"] = blocks
    return result

