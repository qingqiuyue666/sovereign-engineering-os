"""Runtime integration trace tracer-bullet tests.

Tests the deterministic integration trace descriptor:
- valid trace accepted
- missing required digest rejected
- malformed digest rejected
- raw fields rejected
- optional failure/replay digests accepted if valid
- deterministic trace digest
- non-mapping rejected
- input not mutated
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.integration_trace import (
    IntegrationTraceReceipt,
    IntegrationTraceRejection,
    validate_integration_trace,
)

POLICY_PATH = Path("governance/runtime/runtime_integration_trace_policy_v1.json")


def _valid_trace():
    return {
        "execution_descriptor_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "runner_receipt_digest": "sha256:1111111122222222333333334444444455555555666666667777777788888888",
        "state_transition_digest": "sha256:2222222233333333444444445555555566666666777777778888888899999999",
        "idempotency_digest": "sha256:33333333444444445555555566666666777777778888888899999999aaaaaaa0",
        "event_journal_digest": "sha256:444444445555555566666666777777778888888899999999aaaaaaaabbbbbbbb",
        "provider_boundary_digest": "sha256:5555555566666666777777778888888899999999aaaaaaaabbbbbbbbcccccccc",
        "evidence_boundary_digest": "sha256:66666666777777778888888899999999aaaaaaaabbbbbbbbccccccccdddddddd",
        "policy_version": "v1",
        "code_version": "0.1.0",
    }


class IntegrationTracePolicyTests(unittest.TestCase):
    """Policy file integrity tests."""

    def test_policy_file_exists_and_is_valid_json(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Policy file missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "runtime_integration_trace_policy_v1")
        self.assertEqual(policy["version"], "v1")
        self.assertTrue(policy["dry_run_only"])
        self.assertTrue(policy["deterministic_required"])
        self.assertTrue(policy["digest_refs_only"])
        for field in ("execution_descriptor_digest", "runner_receipt_digest",
                      "state_transition_digest", "idempotency_digest",
                      "event_journal_digest", "provider_boundary_digest",
                      "evidence_boundary_digest"):
            self.assertIn(field, policy["required_digest_fields"])
        for field in ("failure_bundle_digest", "replay_plan_digest", "replay_diff_digest"):
            self.assertIn(field, policy["optional_digest_fields"])
        for field in ("raw_prompt", "raw_provider_response", "secret_value", "env_value",
                      "inline_payload", "live_provider_response", "network_result"):
            self.assertIn(field, policy["forbidden_fields"])


class IntegrationTraceAcceptanceTests(unittest.TestCase):
    """Happy-path acceptance tests."""

    def test_valid_trace_accepted(self):
        receipt = validate_integration_trace(_valid_trace())
        self.assertIsInstance(receipt, IntegrationTraceReceipt)
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.failures, ())
        self.assertTrue(receipt.trace_digest.startswith("sha256:"))

    def test_deterministic_trace_digest(self):
        r1 = validate_integration_trace(_valid_trace())
        r2 = validate_integration_trace(_valid_trace())
        self.assertEqual(r1.trace_digest, r2.trace_digest)
        self.assertEqual(r1.as_dict(), r2.as_dict())

    def test_optional_failure_bundle_digest_accepted(self):
        trace = _valid_trace()
        trace["failure_bundle_digest"] = "sha256:777777778888888899999999aaaaaaaabbbbbbbbccccccccddddddddeeeeeeee"
        receipt = validate_integration_trace(trace)
        self.assertTrue(receipt.accepted, f"Expected accepted but got: {receipt.failures}")

    def test_optional_replay_plan_digest_accepted(self):
        trace = _valid_trace()
        trace["replay_plan_digest"] = "sha256:8888888899999999aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffff"
        receipt = validate_integration_trace(trace)
        self.assertTrue(receipt.accepted, f"Expected accepted but got: {receipt.failures}")

    def test_optional_replay_diff_digest_accepted(self):
        trace = _valid_trace()
        trace["replay_diff_digest"] = "sha256:99999999aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffff00000000"
        receipt = validate_integration_trace(trace)
        self.assertTrue(receipt.accepted, f"Expected accepted but got: {receipt.failures}")

    def test_input_not_mutated(self):
        trace = _valid_trace()
        before = copy.deepcopy(trace)
        validate_integration_trace(trace)
        self.assertEqual(trace, before)


class IntegrationTraceRejectionTests(unittest.TestCase):
    """Rejection-path tests."""

    def test_non_mapping_rejected(self):
        with self.assertRaises(IntegrationTraceRejection):
            validate_integration_trace(None)

        with self.assertRaises(IntegrationTraceRejection):
            validate_integration_trace("not_a_mapping")

        with self.assertRaises(IntegrationTraceRejection):
            validate_integration_trace(42)

    def test_missing_execution_descriptor_digest_rejected(self):
        trace = _valid_trace()
        del trace["execution_descriptor_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("execution_descriptor_digest_must_not_be_none", receipt.failures)

    def test_missing_runner_receipt_digest_rejected(self):
        trace = _valid_trace()
        del trace["runner_receipt_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("runner_receipt_digest_must_not_be_none", receipt.failures)

    def test_missing_state_transition_digest_rejected(self):
        trace = _valid_trace()
        del trace["state_transition_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("state_transition_digest_must_not_be_none", receipt.failures)

    def test_missing_idempotency_digest_rejected(self):
        trace = _valid_trace()
        del trace["idempotency_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("idempotency_digest_must_not_be_none", receipt.failures)

    def test_missing_event_journal_digest_rejected(self):
        trace = _valid_trace()
        del trace["event_journal_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("event_journal_digest_must_not_be_none", receipt.failures)

    def test_missing_provider_boundary_digest_rejected(self):
        trace = _valid_trace()
        del trace["provider_boundary_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("provider_boundary_digest_must_not_be_none", receipt.failures)

    def test_missing_evidence_boundary_digest_rejected(self):
        trace = _valid_trace()
        del trace["evidence_boundary_digest"]
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("evidence_boundary_digest_must_not_be_none", receipt.failures)

    def test_malformed_digest_rejected(self):
        trace = _valid_trace()
        trace["execution_descriptor_digest"] = "not-a-digest"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("execution_descriptor_digest_must_be_valid_digest", receipt.failures)

    def test_uppercase_digest_rejected(self):
        trace = _valid_trace()
        trace["execution_descriptor_digest"] = "sha256:ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("execution_descriptor_digest_must_be_valid_digest", receipt.failures)

    def test_raw_prompt_rejected(self):
        trace = _valid_trace()
        trace["raw_prompt"] = "do something"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_raw_provider_response_rejected(self):
        trace = _valid_trace()
        trace["raw_provider_response"] = "response"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("raw_provider_response_forbidden", receipt.failures)

    def test_inline_payload_rejected(self):
        trace = _valid_trace()
        trace["inline_payload"] = {"data": "sensitive"}
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("inline_payload_forbidden", receipt.failures)

    def test_live_provider_response_rejected(self):
        trace = _valid_trace()
        trace["live_provider_response"] = "live response"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("live_provider_response_forbidden", receipt.failures)

    def test_network_result_rejected(self):
        trace = _valid_trace()
        trace["network_result"] = "http 200"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("network_result_forbidden", receipt.failures)

    def test_optional_malformed_failure_bundle_digest_rejected(self):
        trace = _valid_trace()
        trace["failure_bundle_digest"] = "bad-digest"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("failure_bundle_digest_must_be_valid_digest", receipt.failures)

    def test_optional_malformed_replay_plan_digest_rejected(self):
        trace = _valid_trace()
        trace["replay_plan_digest"] = "bad-digest"
        receipt = validate_integration_trace(trace)
        self.assertFalse(receipt.accepted)
        self.assertIn("replay_plan_digest_must_be_valid_digest", receipt.failures)


class IntegrationTraceSideEffectFreeTests(unittest.TestCase):
    """Side-effect freedom tests."""

    def test_validate_integration_trace_does_not_mutate(self):
        trace = _valid_trace()
        before = copy.deepcopy(trace)
        validate_integration_trace(trace)
        self.assertEqual(trace, before)

    def test_no_network_imports(self):
        import kernel.runtime.integration_trace as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("requests", content)
            self.assertNotIn("urllib", content)

    def test_no_sqlite_import(self):
        import kernel.runtime.integration_trace as mod
        source = mod.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("sqlite3", content)
