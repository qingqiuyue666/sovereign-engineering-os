#!/usr/bin/env python3
"""Validate fake-DCC execution evidence and materialization records."""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.evidence.collector import collect_execution_evidence
from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.result_envelope import sha256_file


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tempdir:
        root = Path(tempdir)
        output_root = root / "out"
        permit = create_execution_permit(
            task_id="TASK_CREATIVE_EVIDENCE",
            operator_approval_id="RCPT_CREATIVE_EVIDENCE",
            allowed_adapter="fake_dcc",
            allowed_action="smoke_generate_file",
            allowed_output_root=output_root,
            expires_at="2099-01-01T00:00:00Z",
        )
        result = run_fake_dcc(permit, job={"output_path": "output.txt", "content": "evidence\n"})
        collected = collect_execution_evidence(
            permit=permit,
            result=result,
            evidence_root=root / "reports" / "execution_plane",
            materialization_root=root / "reports" / "creative" / "materializations",
        )
        result_path = Path(collected["execution_result_path"])
        materialization_paths = [Path(path) for path in collected["materialization_paths"]]
        if not result_path.exists():
            errors.append("missing_execution_result")
        if len(materialization_paths) != 1 or not materialization_paths[0].exists():
            errors.append("missing_materialization_record")
        else:
            materialization = json.loads(materialization_paths[0].read_text(encoding="utf-8"))
            if materialization.get("permit_id") != permit["permit_id"]:
                errors.append("materialization_permit_mismatch")
            if materialization.get("sha256") != sha256_file(output_root / "output.txt"):
                errors.append("materialization_hash_mismatch")
            if str(root) in json.dumps(materialization, sort_keys=True):
                errors.append("materialization_path_leak")
        if str(root) in json.dumps(result, sort_keys=True):
            errors.append("result_path_leak")

    if errors:
        print("creative_real_execution_evidence_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("creative_real_execution_evidence_check_v1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

