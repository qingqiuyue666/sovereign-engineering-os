#!/usr/bin/env python3
"""Run a CI-safe fake DCC controlled executor smoke."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.result_envelope import sha256_file


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tempdir:
        output_root = Path(tempdir) / "out"
        permit = create_execution_permit(
            task_id="TASK_EXECUTOR_SMOKE",
            operator_approval_id="RCPT_EXECUTOR_SMOKE",
            allowed_adapter="fake_dcc",
            allowed_action="smoke_generate_file",
            allowed_output_root=output_root,
            expires_at="2099-01-01T00:00:00Z",
        )
        result = run_fake_dcc(permit, job={"output_path": "output.txt", "content": "smoke\n"})
        output = output_root / "output.txt"
        if result["status"] != "SUCCEEDED":
            errors.append(f"unexpected_status:{result['status']}")
        if not output.exists():
            errors.append("missing_output_file")
        else:
            record = next((item for item in result["outputs"] if item["relative_path"] == "output.txt"), None)
            if record is None or record.get("sha256") != sha256_file(output):
                errors.append("output_hash_mismatch")
        if str(output_root) in str(result):
            errors.append("absolute_output_root_leaked")

    if errors:
        print("controlled_executor_smoke_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("controlled_executor_smoke_v1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

