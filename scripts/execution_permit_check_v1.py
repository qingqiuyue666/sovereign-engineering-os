#!/usr/bin/env python3
"""Validate execution permit schema, builder, and fail-closed checks."""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.validator import (
    ExecutionPermitValidationError,
    validate_execution_permit,
)
from kernel.schemas.validator import validate_artifact


def main() -> int:
    errors: list[str] = []
    schema_path = REPO_ROOT / "execution_plane/schemas/execution_permit_v1.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"schema_load_failed:{exc}")
        schema = {}

    with tempfile.TemporaryDirectory() as tempdir:
        permit = create_execution_permit(
            task_id="TASK_PERMIT_CHECK",
            operator_approval_id="RCPT_PERMIT_CHECK",
            allowed_adapter="fake_dcc",
            allowed_action="smoke_generate_file",
            allowed_output_root=Path(tempdir) / "out",
            expires_at="2099-01-01T00:00:00Z",
        )
        errors.extend(validate_artifact(permit, schema))
        try:
            validate_execution_permit(permit)
        except ExecutionPermitValidationError as exc:
            errors.extend(exc.errors)

        tampered = dict(permit)
        tampered["max_files"] = 999
        try:
            validate_execution_permit(tampered)
            errors.append("tampered_digest_was_accepted")
        except ExecutionPermitValidationError as exc:
            if "permit_digest_mismatch" not in exc.errors:
                errors.append("tampered_digest_missing_expected_error")

    if errors:
        print("execution_permit_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("execution_permit_check_v1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

