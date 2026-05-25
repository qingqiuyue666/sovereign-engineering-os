"""Tests for standalone capability token lifecycle V1."""

from __future__ import annotations

import unittest
from pathlib import Path

from kernel.runtime.capability_token_lifecycle import (
    ALLOWED_LOCAL_RUNNER_COMMAND_IDS,
    CapabilityTokenLifecycle,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "capability_token_lifecycle.py"
POLICY_PATH = ROOT / "governance" / "security" / "capability_token_lifecycle_v1.json"
DOC_PATH = ROOT / "docs" / "decisions" / "capability_token_lifecycle_v1.md"

APPROVAL_DIGEST = "sha256:" + "a" * 64
OTHER_APPROVAL_DIGEST = "sha256:" + "b" * 64
REVISION = "46f536dd31572ab67d0775263acd1456dc625765"
OTHER_REVISION = "56f536dd31572ab67d0775263acd1456dc625766"
ISSUED_AT = "2026-05-25T00:00:00+00:00"
EXPIRES_AT = "2026-05-25T01:00:00+00:00"
NOW = "2026-05-25T00:10:00+00:00"


def issue_token(lifecycle: CapabilityTokenLifecycle, **overrides):
    payload = {
        "command_id": "make_ci",
        "scope": "local_runner_validation",
        "approval_artifact_id": "approval-001",
        "approval_artifact_digest": APPROVAL_DIGEST,
        "repo_revision": REVISION,
        "expires_at": EXPIRES_AT,
        "issue_nonce": "issue-001",
        "issued_at": ISSUED_AT,
        "observed_at": ISSUED_AT,
    }
    payload.update(overrides)
    return lifecycle.issue(**payload)


def consume_token(lifecycle: CapabilityTokenLifecycle, token_id: str, **overrides):
    payload = {
        "token_id": token_id,
        "command_id": "make_ci",
        "scope": "local_runner_validation",
        "approval_artifact_id": "approval-001",
        "approval_artifact_digest": APPROVAL_DIGEST,
        "repo_revision": REVISION,
        "consume_nonce": "consume-001",
        "now": NOW,
        "observed_at": NOW,
    }
    payload.update(overrides)
    return lifecycle.consume(**payload)


class CapabilityTokenLifecycleV1Tests(unittest.TestCase):
    def test_allowlisted_command_issues_and_consumes_once(self) -> None:
        lifecycle = CapabilityTokenLifecycle()
        issued = issue_token(lifecycle)
        self.assertTrue(issued.accepted)
        self.assertIsNotNone(issued.token)
        self.assertTrue(issued.token.single_use)
        self.assertIn(issued.token.command_id, ALLOWED_LOCAL_RUNNER_COMMAND_IDS)
        self.assertTrue(issued.receipt.accepted)
        self.assertEqual(issued.receipt.event_type, "token_issued")

        consumed = consume_token(lifecycle, issued.token.token_id)
        self.assertTrue(consumed.accepted)
        self.assertIsNotNone(consumed.token)
        self.assertEqual(consumed.token.consumed_at, NOW)
        self.assertTrue(consumed.receipt.accepted)
        self.assertEqual(consumed.receipt.event_type, "token_consumed")

    def test_unknown_command_and_bad_binding_are_rejected(self) -> None:
        lifecycle = CapabilityTokenLifecycle()
        unknown = issue_token(lifecycle, command_id="npm_install")
        self.assertFalse(unknown.accepted)
        self.assertIn("command_id_not_allowlisted", unknown.receipt.failures)
        self.assertIsNone(unknown.token)

        bad_digest = issue_token(
            lifecycle,
            issue_nonce="issue-002",
            approval_artifact_digest="not-a-digest",
        )
        self.assertFalse(bad_digest.accepted)
        self.assertIn("approval_artifact_digest_required", bad_digest.receipt.failures)

    def test_expired_revoked_and_double_consumed_tokens_reject(self) -> None:
        expired_lifecycle = CapabilityTokenLifecycle()
        expired = issue_token(
            expired_lifecycle,
            expires_at="2026-05-25T00:05:00+00:00",
        )
        self.assertTrue(expired.accepted)
        expired_consume = consume_token(expired_lifecycle, expired.token.token_id)
        self.assertFalse(expired_consume.accepted)
        self.assertIn("token_expired", expired_consume.receipt.failures)

        revoked_lifecycle = CapabilityTokenLifecycle()
        revoked = issue_token(revoked_lifecycle)
        revoke_result = revoked_lifecycle.revoke(
            token_id=revoked.token.token_id,
            reason="operator_cancelled",
            revoked_at=NOW,
            observed_at=NOW,
        )
        self.assertTrue(revoke_result.accepted)
        revoked_consume = consume_token(revoked_lifecycle, revoked.token.token_id)
        self.assertFalse(revoked_consume.accepted)
        self.assertIn("token_revoked", revoked_consume.receipt.failures)

        consumed_lifecycle = CapabilityTokenLifecycle()
        consumed = issue_token(consumed_lifecycle)
        self.assertTrue(consume_token(consumed_lifecycle, consumed.token.token_id).accepted)
        second = consume_token(
            consumed_lifecycle,
            consumed.token.token_id,
            consume_nonce="consume-002",
        )
        self.assertFalse(second.accepted)
        self.assertIn("token_already_consumed", second.receipt.failures)

    def test_wrong_command_scope_revision_and_approval_reject(self) -> None:
        lifecycle = CapabilityTokenLifecycle()
        issued = issue_token(lifecycle)
        result = consume_token(
            lifecycle,
            issued.token.token_id,
            command_id="diff_check",
            scope="other_scope",
            approval_artifact_id="approval-002",
            approval_artifact_digest=OTHER_APPROVAL_DIGEST,
            repo_revision=OTHER_REVISION,
        )
        self.assertFalse(result.accepted)
        self.assertIn("command_id_mismatch", result.receipt.failures)
        self.assertIn("scope_mismatch", result.receipt.failures)
        self.assertIn("approval_artifact_id_mismatch", result.receipt.failures)
        self.assertIn("approval_artifact_digest_mismatch", result.receipt.failures)
        self.assertIn("repo_revision_mismatch", result.receipt.failures)

    def test_replay_protection_rejects_reused_issue_and_consume_nonces(self) -> None:
        lifecycle = CapabilityTokenLifecycle()
        first = issue_token(lifecycle)
        replay_issue = issue_token(
            lifecycle,
            command_id="diff_check",
            issue_nonce="issue-001",
        )
        self.assertFalse(replay_issue.accepted)
        self.assertIn("issue_nonce_replay", replay_issue.receipt.failures)

        self.assertTrue(consume_token(lifecycle, first.token.token_id).accepted)
        second = issue_token(
            lifecycle,
            command_id="diff_check",
            issue_nonce="issue-002",
        )
        replay_consume = consume_token(
            lifecycle,
            second.token.token_id,
            command_id="diff_check",
            consume_nonce="consume-001",
        )
        self.assertFalse(replay_consume.accepted)
        self.assertIn("replay_nonce_reused", replay_consume.receipt.failures)

    def test_receipts_are_deterministic_and_do_not_store_nonce_material(self) -> None:
        first_lifecycle = CapabilityTokenLifecycle()
        second_lifecycle = CapabilityTokenLifecycle()
        first = issue_token(first_lifecycle)
        second = issue_token(second_lifecycle)
        self.assertEqual(first.token.token_id, second.token.token_id)
        self.assertEqual(first.receipt.receipt_hash, second.receipt.receipt_hash)
        token_dict = first.token.as_dict()
        self.assertNotIn("issue-001", str(token_dict))
        self.assertIn("issue_nonce_digest", token_dict)

    def test_policy_and_doc_record_no_forbidden_authority(self) -> None:
        policy_text = POLICY_PATH.read_text(encoding="utf-8")
        doc_text = " ".join(DOC_PATH.read_text(encoding="utf-8").lower().split())
        for fragment in (
            '"arbitrary_shell_authorized": false',
            '"shell_true_authorized": false',
            '"network_authorized": false',
            '"browser_authorized": false',
            '"provider_api_authorized": false',
            '"credential_storage_authorized": false',
            '"production_autonomy_authorized": false',
        ):
            self.assertIn(fragment, policy_text)
        for phrase in (
            "does not execute commands",
            "does not grant arbitrary shell",
            "provider api calls",
            "credential storage",
            "production autonomy",
            "runner integration remains deferred",
        ):
            self.assertIn(phrase, doc_text)

    def test_source_has_no_shell_network_browser_or_provider_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for marker in (
            "subprocess",
            "shell=True",
            "os.system",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "playwright",
            "npm",
            "npx",
            "api_key",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
