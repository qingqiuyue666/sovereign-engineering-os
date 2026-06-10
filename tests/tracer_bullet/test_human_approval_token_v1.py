"""Tracer-bullet tests for human approval token v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.human_approval_token import (
    SUPPORTED_ACTION_TYPES,
    create_approval_decision,
    create_human_approval_token,
    evaluate_human_approval,
)

POLICY_PATH = Path("governance/approval/human_approval_token_v1.json")
SOURCE_PATH = Path("kernel/runtime/human_approval_token.py")

NOW = "2026-05-25T00:00:00+00:00"
FUTURE = "2026-05-26T00:00:00+00:00"
PAST = "2026-05-24T00:00:00+00:00"


def _token(**overrides: object):
    fields = {
        "approval_id": "approval-001",
        "operator_id": "operator-001",
        "scope_id": "scope-runtime-dry-run",
        "action_type": "READ_PATH",
        "target_id": "asset-root-001",
        "risk_class": "READ_ONLY",
        "issued_at": NOW,
        "expires_at": FUTURE,
        "reason": "bounded dry-run review",
        "tool_id": None,
        "command_id": None,
        "workflow_id": None,
        "asset_root_id": "asset-root-001",
        "revoked": False,
    }
    fields.update(overrides)
    return create_human_approval_token(**fields)


def _decision(**overrides: object):
    fields = {
        "approval_id": "approval-001",
        "accepted": True,
        "operator_id": "operator-001",
        "decided_at": NOW,
        "rejection_reason": None,
    }
    fields.update(overrides)
    return create_approval_decision(**fields)


class HumanApprovalTokenTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "human_approval_token_v1")
        self.assertFalse(policy["production_autonomy_allowed"])
        self.assertFalse(policy["router_bypass_allowed"])
        self.assertFalse(policy["tool_risk_classifier_bypass_allowed"])
        self.assertFalse(policy["raw_command_allowed"])
        self.assertFalse(policy["payload_argv_allowed"])
        self.assertFalse(policy["command_line_allowed"])
        self.assertFalse(policy["implicit_credential_approval_allowed"])
        self.assertEqual(set(policy["supported_action_types"]), SUPPORTED_ACTION_TYPES)

    def test_valid_scoped_approval_accepted(self):
        result = evaluate_human_approval(
            _token(),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertTrue(result.accepted, result.failures)
        self.assertTrue(result.router_admission_still_required)
        self.assertTrue(result.tool_risk_classifier_still_required)
        self.assertFalse(result.production_autonomy_allowed)

    def test_missing_scope_rejected(self):
        result = evaluate_human_approval(
            _token(scope_id=""),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("scope_id_required", result.failures)

    def test_missing_expiry_rejected(self):
        result = evaluate_human_approval(
            _token(expires_at=""),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("expires_at_required", result.failures)

    def test_expired_approval_rejected(self):
        result = evaluate_human_approval(
            _token(expires_at=PAST),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("approval_expired", result.failures)

    def test_revoked_approval_rejected(self):
        result = evaluate_human_approval(
            _token(revoked=True),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("approval_revoked", result.failures)

    def test_action_mismatch_rejected(self):
        result = evaluate_human_approval(
            _token(action_type="WRITE_PATH", risk_class="HIGH_RISK"),
            action_type="READ_PATH",
            target_id="asset-root-001",
            decision=_decision(),
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("action_type_mismatch", result.failures)

    def test_target_mismatch_rejected(self):
        result = evaluate_human_approval(
            _token(target_id="asset-root-002"),
            action_type="READ_PATH",
            target_id="asset-root-001",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("target_id_mismatch", result.failures)

    def test_high_risk_action_requires_explicit_accepted_decision(self):
        token = _token(
            action_type="LAUNCH_PROCESS",
            target_id="command:diff_check",
            command_id="diff_check",
            risk_class="HIGH_RISK",
        )
        rejected = evaluate_human_approval(
            token,
            action_type="LAUNCH_PROCESS",
            target_id="command:diff_check",
            now=NOW,
        )
        accepted = evaluate_human_approval(
            token,
            action_type="LAUNCH_PROCESS",
            target_id="command:diff_check",
            decision=_decision(),
            now=NOW,
        )
        self.assertFalse(rejected.accepted)
        self.assertIn("accepted_decision_required_for_high_risk_action", rejected.failures)
        self.assertTrue(accepted.accepted, accepted.failures)

    def test_credential_access_cannot_be_implicitly_approved(self):
        result = evaluate_human_approval(
            _token(action_type="CALL_PROVIDER", target_id="provider:x", risk_class="CREDENTIAL_TOUCHING"),
            action_type="CALL_PROVIDER",
            target_id="provider:x",
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("credential_access_requires_explicit_decision", result.failures)

    def test_approval_does_not_authorize_raw_command(self):
        result = evaluate_human_approval(
            _token(),
            action_type="READ_PATH",
            target_id="asset-root-001",
            payload={"raw_command": "rm -rf ."},
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("raw_command_forbidden", result.failures)

    def test_approval_does_not_authorize_arbitrary_argv(self):
        result = evaluate_human_approval(
            _token(),
            action_type="READ_PATH",
            target_id="asset-root-001",
            payload={"payload": {"argv": ["python3"]}},
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("argv_forbidden", result.failures)

    def test_approval_does_not_authorize_command_line(self):
        result = evaluate_human_approval(
            _token(),
            action_type="READ_PATH",
            target_id="asset-root-001",
            payload={"command_line": "python3 -m unittest"},
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("command_line_forbidden", result.failures)

    def test_approval_does_not_bypass_router_or_tool_risk_classifier(self):
        result = evaluate_human_approval(
            _token(),
            action_type="READ_PATH",
            target_id="asset-root-001",
            payload={"bypass_router": True, "bypass_tool_risk_classifier": True},
            now=NOW,
        )
        self.assertFalse(result.accepted)
        self.assertIn("bypass_router_forbidden", result.failures)
        self.assertIn("bypass_tool_risk_classifier_forbidden", result.failures)
        self.assertTrue(result.router_admission_still_required)
        self.assertTrue(result.tool_risk_classifier_still_required)

    def test_content_hash_deterministic_excluding_timestamps(self):
        first = _token(issued_at=NOW, expires_at=FUTURE)
        second = _token(
            issued_at="2030-01-01T00:00:00+00:00",
            expires_at="2030-01-02T00:00:00+00:00",
        )
        first_decision = _decision(decided_at=NOW)
        second_decision = _decision(decided_at="2030-01-01T00:00:00+00:00")
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first_decision.content_hash, second_decision.content_hash)

    def test_no_subprocess_network_provider_or_browser_surface(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
