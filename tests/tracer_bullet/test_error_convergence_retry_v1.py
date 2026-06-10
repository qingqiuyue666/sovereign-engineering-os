"""Behavior tests for failure convergence and retry execution."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.permits.builder import create_execution_permit
from execution_plane.runtime.error_convergence import (
    classify_failure,
    convergence_decision,
    execute_with_retry,
)


class ErrorConvergenceRetryV1Tests(unittest.TestCase):
    def test_taxonomy_classifies_retryable_terminal_and_patch_repairable_failures(self) -> None:
        retryable = classify_failure(_result(status="BLOCKED", policy_blocks=["SERVICE_UNAVAILABLE"]))
        terminal = classify_failure(_result(status="BLOCKED", policy_blocks=["ENV_NOT_FOUND"]))
        repairable = classify_failure(_result(status="FAILED", policy_blocks=["OUTPUT_INVALID"]))

        self.assertTrue(retryable.retryable)
        self.assertEqual(retryable.category, "transient_retryable")
        self.assertTrue(terminal.terminal)
        self.assertEqual(terminal.category, "dependency_or_environment")
        self.assertTrue(repairable.patch_repairable)
        self.assertEqual(repairable.repair_hint["action"], "create_patch_repair_job")

    def test_execute_with_retry_retries_until_success_and_writes_records(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out", retry_enabled=True, max_attempts=2)
            calls = {"count": 0}

            def dispatch(_permit: dict[str, object], _payload: dict[str, object] | None) -> dict[str, object]:
                calls["count"] += 1
                if calls["count"] == 1:
                    return _result(status="BLOCKED", policy_blocks=["SERVICE_UNAVAILABLE"])
                return _result(status="SUCCEEDED")

            result = execute_with_retry(permit=permit, payload={}, dispatch=dispatch)
            retry_records = json.loads((Path(tempdir) / "out" / "retry_records.json").read_text(encoding="utf-8"))
            convergence = json.loads((Path(tempdir) / "out" / "failure_convergence.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual([item["decision"] for item in retry_records["attempts"]], ["retry_after_backoff", "succeeded"])
        self.assertEqual(convergence["terminal_classifier"], "TERMINAL_SUCCEEDED")

    def test_retry_budget_exhaustion_is_terminal_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out", retry_enabled=True, max_attempts=2)

            def dispatch(_permit: dict[str, object], _payload: dict[str, object] | None) -> dict[str, object]:
                return _result(status="BLOCKED", policy_blocks=["SERVICE_UNAVAILABLE"])

            result = execute_with_retry(permit=permit, payload={}, dispatch=dispatch)

        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["convergence_decision"]["decision"], "no_retry_terminal")
        self.assertEqual(result["convergence_decision"]["terminal_classifier"], "TERMINAL_FAILED")

    def test_patch_repairable_failure_gets_repair_hint_when_policy_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = _permit(Path(tempdir) / "out", patch_enabled=True)
            decision = convergence_decision(
                result=_result(status="FAILED", policy_blocks=["SCHEMA_INVALID"]),
                attempt=1,
                token=permit,
            )

        self.assertEqual(decision["decision"], "patch_repair_recommended")
        self.assertEqual(decision["terminal_classifier"], "PATCH_REPAIR_RECOMMENDED")
        self.assertTrue(decision["repair_hint"]["patch_repair_available"])
        self.assertEqual(decision["repair_hint"]["allowed_tools"], ["cline", "aider"])


def _permit(
    output_root: Path,
    *,
    retry_enabled: bool = False,
    max_attempts: int = 1,
    patch_enabled: bool = False,
) -> dict[str, object]:
    return create_execution_permit(
        task_id="TASK_ERROR_CONVERGENCE",
        operator_approval_id="RCPT_ERROR_CONVERGENCE",
        allowed_adapter="comfyui_local",
        allowed_action="service_probe",
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
        retry={
            "enabled": retry_enabled,
            "max_attempts": max_attempts,
            "backoff_seconds": 1,
        },
        patch_repair={
            "enabled": patch_enabled,
            "mode": "generate_patch_then_test" if patch_enabled else "report_only",
            "allowed_tools": ["cline", "aider"] if patch_enabled else [],
            "auto_apply": False,
        },
    )


def _result(*, status: str, policy_blocks: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": "seos_execution_result_v1",
        "status": status,
        "adapter": "comfyui_local",
        "failure_summary": None if status == "SUCCEEDED" else f"{(policy_blocks or ['EXECUTION_FAILED'])[0]}: test failure",
        "policy_blocks": list(policy_blocks or []),
        "outputs": [],
        "artifact_refs": [],
    }


if __name__ == "__main__":
    unittest.main()
