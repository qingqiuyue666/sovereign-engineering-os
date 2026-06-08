"""Tests for SEOS execution permit V1."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.digest import attach_permit_digest, compute_permit_digest
from execution_plane.permits.validator import (
    ExecutionPermitValidationError,
    validate_execution_permit,
)
from kernel.schemas.validator import validate_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]


class ExecutionPermitV1Tests(unittest.TestCase):
    def test_valid_permit_is_accepted_and_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = create_execution_permit(
                task_id="TASK_1",
                operator_approval_id="RCPT_1",
                allowed_adapter="fake_dcc",
                allowed_action="smoke_generate_file",
                allowed_output_root=Path(tempdir) / "out",
                expires_at="2099-01-01T00:00:00Z",
            )
        schema = json.loads(
            (REPO_ROOT / "execution_plane/schemas/execution_permit_v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(validate_artifact(permit, schema), [])
        checked = validate_execution_permit(permit)
        self.assertEqual(checked["permit_digest"], compute_permit_digest(checked))

    def test_fixture_permit_is_valid(self) -> None:
        permit = json.loads(
            (REPO_ROOT / "tests/fixtures/execution_plane/valid_execution_permit_v1.json").read_text(
                encoding="utf-8"
            )
        )
        checked = validate_execution_permit(permit)
        self.assertEqual(checked["permit_id"], "PERMIT_FIXTURE_VALID")

    def test_missing_approval_is_rejected(self) -> None:
        permit = _valid_permit()
        permit["operator_approval_id"] = ""
        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(permit)
        self.assertIn("operator_approval_id_required", caught.exception.errors)

    def test_expired_permit_is_rejected(self) -> None:
        permit = _valid_permit(expires_at="2020-01-01T00:00:00Z")
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(
                permit,
                now=datetime(2026, 6, 8, tzinfo=timezone.utc),
            )
        self.assertIn("permit_expired", caught.exception.errors)

    def test_unsupported_adapter_is_rejected(self) -> None:
        permit = _valid_permit()
        permit["allowed_adapter"] = "desktop_rpa"
        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(permit)
        self.assertIn("unsupported_adapter", caught.exception.errors)

    def test_path_traversal_is_rejected(self) -> None:
        permit = _valid_permit()
        permit["allowed_output_root"] = "../outside"
        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(permit)
        self.assertIn("allowed_output_root_path_traversal", caught.exception.errors)

    def test_digest_tampering_is_rejected(self) -> None:
        permit = _valid_permit()
        permit["max_files"] = 101
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(permit)
        self.assertIn("permit_digest_mismatch", caught.exception.errors)


def _valid_permit(*, expires_at: str = "2099-01-01T00:00:00Z") -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_TEST",
        operator_approval_id="RCPT_TEST",
        allowed_adapter="fake_dcc",
        allowed_action="smoke_generate_file",
        allowed_output_root="work/execution_plane_test_output",
        expires_at=expires_at,
    )


if __name__ == "__main__":
    unittest.main()

