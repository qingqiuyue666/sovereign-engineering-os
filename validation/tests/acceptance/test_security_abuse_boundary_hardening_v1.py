"""Acceptance tests for Security / Abuse Boundary Hardening V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.security_abuse_boundary_hardening import (
    ZERO_HASH,
    FileBackedSecurityAbuseBoundaryHardening,
)

OBSERVED_AT = "2026-05-29T00:40:00+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _payload() -> dict[str, object]:
    return {
        "request_id": "security-acceptance-528",
        "task_id": "task-acceptance-528",
        "run_id": "run-acceptance-528",
        "approval_required": True,
        "replay_required": True,
        "approval_receipt_hash": _hash("approval"),
        "replay_receipt_hash": _hash("replay"),
        "audit_append_only": True,
        "audit_mode": "append_only",
        "audit_chain_hash": _hash("audit"),
        "operator_console_snapshot_hash": _hash("console"),
        "console_mutation_route": "approval_controlled_execution_runtime",
        "allowed_write_relpaths": ("reports/security.json",),
        "requested_write_relpaths": ("reports/security.json",),
        "provider_id": "disabled",
    }


class SecurityAbuseBoundaryHardeningV1AcceptanceTests(unittest.TestCase):
    def test_security_boundary_accepts_safe_request_and_rejects_bypass_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime = FileBackedSecurityAbuseBoundaryHardening(runtime_root=root)
            accepted = runtime.evaluate(_payload(), observed_at=OBSERVED_AT)
            bypass_payload = _payload()
            bypass_payload.update(
                {
                    "approval_bypass": True,
                    "command": "unsafe",
                    "direct_console_edits_enabled": True,
                    "provider_enabled": True,
                    "request_url": "https://example.invalid",
                }
            )
            rejected = runtime.evaluate(bypass_payload, observed_at=OBSERVED_AT)

        self.assertTrue(accepted.accepted, accepted.failures)
        self.assertFalse(rejected.accepted)
        self.assertNotEqual(accepted.receipt_hash, ZERO_HASH)
        self.assertNotEqual(rejected.wal_record_hash, ZERO_HASH)
        rejected_controls = {
            control.control_id
            for control in rejected.control_results
            if not control.accepted
        }
        for control_id in (
            "approval_replay_bypass",
            "console_mutation_bypass",
            "hidden_network",
            "uncontrolled_provider",
            "unsafe_subprocess",
        ):
            self.assertIn(control_id, rejected_controls)
        self.assertFalse(accepted.network_accessed)
        self.assertFalse(accepted.subprocess_spawned)
        self.assertFalse(accepted.provider_called)


if __name__ == "__main__":
    unittest.main()
