"""Idempotency guard tracer-bullet tests.

Tests the deterministic idempotency validator:
- first operation accepted
- repeated same key and digest accepted as duplicate-safe
- same key different digest rejected
- missing idempotency_key rejected
- missing operation_digest rejected
- invalid digest rejected
- forbidden fields rejected
- deterministic receipt
- side-effect free
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.idempotency import (
    IdempotencyGuard,
    IdempotencyReceipt,
    IdempotencyRejection,
    validate_idempotency,
)

POLICY_PATH = Path("governance/runtime/idempotency_policy_v1.json")


def _valid_payload():
    return {
        "idempotency_key": "idem-key-001",
        "operation_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "policy_version": "v1",
        "code_version": "0.1.0",
    }


class IdempotencyPolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "idempotency_policy_v1")
        self.assertTrue(policy["idempotency_key_required"])
        self.assertTrue(policy["operation_digest_required"])
        self.assertTrue(policy["duplicate_safe_on_match"])
        self.assertTrue(policy["reject_different_digest_same_key"])


class IdempotencyAcceptanceTests(unittest.TestCase):
    def test_first_operation_accepted(self):
        receipt = validate_idempotency(_valid_payload())
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.duplicate_safe)
        self.assertEqual(receipt.reasons, ())

    def test_receipt_fields(self):
        receipt = validate_idempotency(_valid_payload())
        self.assertEqual(receipt.idempotency_key, "idem-key-001")
        self.assertTrue(receipt.operation_digest.startswith("sha256:"))
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.reasons, ())

    def test_receipt_as_dict(self):
        receipt = validate_idempotency(_valid_payload())
        d = receipt.as_dict()
        self.assertEqual(d["idempotency_key"], "idem-key-001")
        self.assertTrue(d["accepted"])
        self.assertFalse(d["duplicate_safe"])
        self.assertEqual(d["reasons"], [])

    def test_deterministic_receipt(self):
        r1 = validate_idempotency(_valid_payload())
        r2 = validate_idempotency(_valid_payload())
        self.assertEqual(r1.as_dict(), r2.as_dict())


class IdempotencyGuardTests(unittest.TestCase):
    def test_first_operation_accepted_via_guard(self):
        guard = IdempotencyGuard()
        receipt = guard.check(_valid_payload())
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.duplicate_safe)
        self.assertEqual(guard.seen_count(), 1)

    def test_repeated_same_key_and_digest_duplicate_safe(self):
        guard = IdempotencyGuard()
        guard.check(_valid_payload())
        receipt = guard.check(_valid_payload())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.duplicate_safe)
        self.assertEqual(receipt.reasons, ())
        self.assertEqual(guard.seen_count(), 1)

    def test_same_key_different_digest_rejected(self):
        guard = IdempotencyGuard()
        guard.check(_valid_payload())
        payload = _valid_payload()
        payload["operation_digest"] = "sha256:different_digest_here_1234567890abcdef1234567890ab"
        receipt = guard.check(payload)
        self.assertFalse(receipt.accepted)
        self.assertIn("idempotency_key_digest_mismatch", receipt.reasons)
        self.assertEqual(guard.seen_count(), 1)

    def test_different_keys_both_accepted(self):
        guard = IdempotencyGuard()
        guard.check(_valid_payload())
        payload = _valid_payload()
        payload["idempotency_key"] = "idem-key-002"
        receipt = guard.check(payload)
        self.assertTrue(receipt.accepted)
        self.assertEqual(guard.seen_count(), 2)

    def test_triple_replay_same_key_digest(self):
        guard = IdempotencyGuard()
        guard.check(_valid_payload())
        guard.check(_valid_payload())
        receipt = guard.check(_valid_payload())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.duplicate_safe)

    def test_seen_count_increments_only_for_new_keys(self):
        guard = IdempotencyGuard()
        self.assertEqual(guard.seen_count(), 0)
        guard.check(_valid_payload())
        self.assertEqual(guard.seen_count(), 1)
        guard.check(_valid_payload())
        self.assertEqual(guard.seen_count(), 1)


class IdempotencyRejectionTests(unittest.TestCase):
    def test_missing_idempotency_key_rejected(self):
        payload = _valid_payload()
        del payload["idempotency_key"]
        receipt = validate_idempotency(payload)
        self.assertFalse(receipt.accepted)
        self.assertIn("idempotency_key_required_nonempty_string", receipt.reasons)

    def test_empty_idempotency_key_rejected(self):
        payload = _valid_payload()
        payload["idempotency_key"] = ""
        receipt = validate_idempotency(payload)
        self.assertIn("idempotency_key_required_nonempty_string", receipt.reasons)

    def test_none_idempotency_key_rejected(self):
        payload = _valid_payload()
        payload["idempotency_key"] = None
        receipt = validate_idempotency(payload)
        self.assertIn("idempotency_key_required_nonempty_string", receipt.reasons)

    def test_missing_operation_digest_rejected(self):
        payload = _valid_payload()
        del payload["operation_digest"]
        receipt = validate_idempotency(payload)
        self.assertIn("operation_digest_required_nonempty_string", receipt.reasons)

    def test_invalid_digest_format_rejected(self):
        payload = _valid_payload()
        payload["operation_digest"] = "abc123"
        receipt = validate_idempotency(payload)
        self.assertIn("operation_digest_must_be_sha256_prefixed", receipt.reasons)

    def test_raw_prompt_rejected(self):
        payload = _valid_payload()
        payload["raw_prompt"] = "test"
        receipt = validate_idempotency(payload)
        self.assertIn("raw_prompt_forbidden", receipt.reasons)

    def test_raw_provider_response_rejected(self):
        payload = _valid_payload()
        payload["raw_provider_response"] = "test"
        receipt = validate_idempotency(payload)
        self.assertIn("raw_provider_response_forbidden", receipt.reasons)

    def test_secret_value_rejected(self):
        payload = _valid_payload()
        payload["secret_value"] = "sk-abc"
        receipt = validate_idempotency(payload)
        self.assertIn("secret_value_forbidden", receipt.reasons)

    def test_env_value_rejected(self):
        payload = _valid_payload()
        payload["env_value"] = "PATH=/usr/bin"
        receipt = validate_idempotency(payload)
        self.assertIn("env_value_forbidden", receipt.reasons)

    def test_non_mapping_rejected_by_guard(self):
        guard = IdempotencyGuard()
        receipt = guard.check("not a mapping")
        self.assertFalse(receipt.accepted)
        self.assertIn("input_must_be_mapping", receipt.reasons)


class IdempotencySideEffectFreeTests(unittest.TestCase):
    def test_validate_idempotency_does_not_mutate(self):
        p1 = _valid_payload()
        p2 = copy.deepcopy(p1)
        validate_idempotency(p1)
        self.assertEqual(p1, p2)

    def test_guard_check_does_not_mutate_input(self):
        guard = IdempotencyGuard()
        p1 = _valid_payload()
        p2 = copy.deepcopy(p1)
        guard.check(p1)
        self.assertEqual(p1, p2)
