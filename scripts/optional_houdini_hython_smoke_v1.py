#!/usr/bin/env python3
"""Optional Houdini/hython smoke. Safe to skip when hython is unavailable."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from execution_plane.adapters.houdini_hython import run_houdini_hython_smoke
from execution_plane.permits.builder import create_execution_permit


def main() -> int:
    with tempfile.TemporaryDirectory() as tempdir:
        permit = create_execution_permit(
            task_id="TASK_OPTIONAL_HOUDINI",
            operator_approval_id="RCPT_OPTIONAL_HOUDINI",
            allowed_adapter="houdini_hython",
            allowed_action="houdini_generate_geometry_cache",
            allowed_output_root=Path(tempdir) / "out",
            expires_at="2099-01-01T00:00:00Z",
        )
        result = run_houdini_hython_smoke(permit)
    if result["status"] == "SUCCEEDED":
        print("optional_houdini_hython_smoke_v1: PASS")
        return 0
    if result["status"] == "BLOCKED":
        print("optional_houdini_hython_smoke_v1: SKIP")
        print(",".join(result.get("policy_blocks", [])))
        return 0
    print("optional_houdini_hython_smoke_v1: FAIL")
    print(result["failure_summary"])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

