"""Tests for runtime-token policy upgrade."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.validator import ExecutionPermitValidationError, validate_execution_permit
from execution_plane.runtime.concurrency import adapter_budget
from execution_plane.runtime.patch_repair_policy import PatchRepairPolicy
from execution_plane.runtime.retry_budget import RetryBudget
from execution_plane.runtime.token_policy import (
    RuntimePolicyError,
    assert_action_allowed,
    auto_provision_allowed,
)


class RuntimeTokenPolicyUpgradeV1Tests(unittest.TestCase):
    def test_permit_expresses_active_runtime_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = create_execution_permit(
                task_id="TASK_POLICY",
                operator_approval_id="RCPT_POLICY",
                allowed_adapter="comfyui_local",
                allowed_action="service_probe",
                allowed_output_root=Path(tempdir) / "out",
                expires_at="2099-01-01T00:00:00Z",
                auto_provision={
                    "enabled": True,
                    "allowed_adapters": ["comfyui_local"],
                    "max_wait_seconds": 5,
                    "heartbeat_interval_seconds": 1,
                },
                concurrency={
                    "max_global_jobs": 3,
                    "max_per_adapter_jobs": {"comfyui_local": 2},
                },
                retry={"enabled": True, "max_attempts": 2, "backoff_seconds": 1},
                patch_repair={
                    "enabled": True,
                    "mode": "generate_patch_then_test",
                    "allowed_tools": ["cline"],
                    "auto_apply": False,
                },
            )
        checked = validate_execution_permit(permit)
        self.assertTrue(auto_provision_allowed(checked, "comfyui_local"))
        self.assertEqual(adapter_budget(checked, "comfyui_local"), 2)
        self.assertTrue(RetryBudget.from_token(checked).attempt_allowed(2))
        self.assertTrue(PatchRepairPolicy.from_token(checked).can_generate_patch())

    def test_gateway_policy_rejects_action_outside_token(self) -> None:
        permit = _permit()
        with self.assertRaises(RuntimePolicyError) as caught:
            assert_action_allowed(permit, adapter="fake_dcc", action="submit_workflow")
        self.assertIn("action_not_allowed_by_token", caught.exception.errors)

    def test_patch_auto_apply_is_rejected(self) -> None:
        permit = _permit()
        permit["patch_repair"]["auto_apply"] = True
        from execution_plane.permits.digest import attach_permit_digest

        permit = attach_permit_digest(permit)
        with self.assertRaises(ExecutionPermitValidationError) as caught:
            validate_execution_permit(permit)
        self.assertIn("patch_repair_auto_apply_must_be_false", caught.exception.errors)


def _permit() -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_POLICY_BASE",
        operator_approval_id="RCPT_POLICY_BASE",
        allowed_adapter="fake_dcc",
        allowed_action="smoke_generate_file",
        allowed_output_root="work/runtime_policy_test",
        expires_at="2099-01-01T00:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()
