"""Runtime execution descriptor tracer-bullet tests.

Tests the execution descriptor validator:
- valid descriptor accepted
- missing required fields rejected
- None rejected
- empty string rejected
- whitespace string rejected
- malformed digest rejected
- uppercase digest rejected
- bool-as-string rejected
- bool-as-int rejected
- dry_run=false rejected
- provider_enabled=true rejected
- network_access=true rejected
- production_autonomy=true rejected
- raw fields rejected
- deterministic digest
- input not mutated
- non-mapping rejected
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.execution_descriptor import (
    ExecutionDescriptorReceipt,
    ExecutionDescriptorRejection,
    validate_execution_descriptor,
)

POLICY_PATH = Path("governance/runtime/runtime_execution_descriptor_policy_v1.json")


def _valid_payload():
    return {
        "task_id": "task_abc123def4567890123456",
        "run_id": "run_abc123def4567890123456",
        "execution_id": "exec_abc123def4567890123456",
        "stage": "validated",
        "policy_version": "v1",
        "code_version": "0.1.0",
        "input_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "task_manifest_digest": "sha256:00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
        "operator_intent_digest": "sha256:ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100",
        "dry_run": True,
        "provider_enabled": False,
        "network_access": False,
        "production_autonomy": False,
    }


class ExecutionDescriptorPolicyTests(unittest.TestCase):
    """Policy file integrity tests."""

    def test_policy_file_exists_and_is_valid_json(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Policy file missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "runtime_execution_descriptor_policy_v1")
        self.assertEqual(policy["version"], "v1")
        self.assertTrue(policy["dry_run_only"])
        self.assertFalse(policy["provider_execution_allowed"])
        self.assertFalse(policy["network_access_allowed"])
        self.assertFalse(policy["production_autonomy_allowed"])
        self.assertTrue(policy["deterministic_required"])
        for field in ("task_id", "run_id", "execution_id", "stage", "policy_version", "code_version"):
            self.assertIn(field, policy["required_string_fields"])
        for field in ("input_digest", "task_manifest_digest", "operator_intent_digest"):
            self.assertIn(field, policy["required_digest_fields"])
        for field in ("dry_run", "provider_enabled", "network_access", "production_autonomy"):
            self.assertIn(field, policy["required_bool_fields"])
        self.assertTrue(policy["required_bool_values"]["dry_run"])
        self.assertFalse(policy["required_bool_values"]["provider_enabled"])
        self.assertFalse(policy["required_bool_values"]["network_access"])
        self.assertFalse(policy["required_bool_values"]["production_autonomy"])
        for field in ("raw_prompt", "raw_provider_response", "secret_value", "env_value",
                      "provider_api_key", "live_network_target", "autonomy_directive"):
            self.assertIn(field, policy["forbidden_fields"])


class ExecutionDescriptorAcceptanceTests(unittest.TestCase):
    """Happy-path acceptance tests."""

    def test_valid_descriptor_accepted(self):
        payload = _valid_payload()
        receipt = validate_execution_descriptor(payload)
        self.assertIsInstance(receipt, ExecutionDescriptorReceipt)
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.failures, ())
        self.assertTrue(receipt.descriptor_digest.startswith("sha256:"))

    def test_receipt_contains_all_expected_fields(self):
        payload = _valid_payload()
        receipt = validate_execution_descriptor(payload)
        self.assertEqual(receipt.execution_id, payload["execution_id"])
        self.assertEqual(receipt.task_id, payload["task_id"])
        self.assertEqual(receipt.run_id, payload["run_id"])
        self.assertEqual(receipt.policy_version, payload["policy_version"])
        self.assertEqual(receipt.code_version, payload["code_version"])
        self.assertEqual(len(receipt.descriptor_digest), len("sha256:") + 64)

    def test_deterministic_digest(self):
        payload = _valid_payload()
        r1 = validate_execution_descriptor(payload)
        r2 = validate_execution_descriptor(payload)
        self.assertEqual(r1.descriptor_digest, r2.descriptor_digest)
        self.assertEqual(r1.as_dict(), r2.as_dict())

    def test_different_inputs_produce_different_digest(self):
        p1 = _valid_payload()
        p2 = _valid_payload()
        p2["task_id"] = "task_different_id_here_123456"
        r1 = validate_execution_descriptor(p1)
        r2 = validate_execution_descriptor(p2)
        self.assertNotEqual(r1.descriptor_digest, r2.descriptor_digest)

    def test_input_not_mutated(self):
        payload = _valid_payload()
        before = copy.deepcopy(payload)
        validate_execution_descriptor(payload)
        self.assertEqual(payload, before)


class ExecutionDescriptorRejectionTests(unittest.TestCase):
    """Rejection-path tests."""

    def test_none_payload_rejected(self):
        with self.assertRaises(ExecutionDescriptorRejection):
            validate_execution_descriptor(None)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ExecutionDescriptorRejection):
            validate_execution_descriptor("not_a_mapping")

        with self.assertRaises(ExecutionDescriptorRejection):
            validate_execution_descriptor(42)

        with self.assertRaises(ExecutionDescriptorRejection):
            validate_execution_descriptor([1, 2, 3])

    def test_missing_task_id_rejected(self):
        p = _valid_payload()
        del p["task_id"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("task_id_must_not_be_none", receipt.failures)

    def test_missing_run_id_rejected(self):
        p = _valid_payload()
        del p["run_id"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("run_id_must_not_be_none", receipt.failures)

    def test_missing_execution_id_rejected(self):
        p = _valid_payload()
        del p["execution_id"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("execution_id_must_not_be_none", receipt.failures)

    def test_missing_stage_rejected(self):
        p = _valid_payload()
        del p["stage"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("stage_must_not_be_none", receipt.failures)

    def test_missing_policy_version_rejected(self):
        p = _valid_payload()
        del p["policy_version"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("policy_version_must_not_be_none", receipt.failures)

    def test_missing_code_version_rejected(self):
        p = _valid_payload()
        del p["code_version"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("code_version_must_not_be_none", receipt.failures)

    def test_missing_input_digest_rejected(self):
        p = _valid_payload()
        del p["input_digest"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("input_digest_must_not_be_none", receipt.failures)

    def test_missing_task_manifest_digest_rejected(self):
        p = _valid_payload()
        del p["task_manifest_digest"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("task_manifest_digest_must_not_be_none", receipt.failures)

    def test_missing_operator_intent_digest_rejected(self):
        p = _valid_payload()
        del p["operator_intent_digest"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("operator_intent_digest_must_not_be_none", receipt.failures)

    def test_missing_dry_run_rejected(self):
        p = _valid_payload()
        del p["dry_run"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("dry_run_must_not_be_none", receipt.failures)

    def test_missing_provider_enabled_rejected(self):
        p = _valid_payload()
        del p["provider_enabled"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("provider_enabled_must_not_be_none", receipt.failures)

    def test_missing_network_access_rejected(self):
        p = _valid_payload()
        del p["network_access"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("network_access_must_not_be_none", receipt.failures)

    def test_missing_production_autonomy_rejected(self):
        p = _valid_payload()
        del p["production_autonomy"]
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("production_autonomy_must_not_be_none", receipt.failures)

    def test_empty_string_rejected(self):
        p = _valid_payload()
        p["task_id"] = ""
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("task_id_must_be_nonempty_string", receipt.failures)

    def test_whitespace_string_rejected(self):
        p = _valid_payload()
        p["task_id"] = "   "
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("task_id_must_be_nonempty_string", receipt.failures)

    def test_malformed_digest_rejected(self):
        p = _valid_payload()
        p["input_digest"] = "not-a-digest"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("input_digest_must_be_valid_digest", receipt.failures)

    def test_uppercase_digest_rejected(self):
        p = _valid_payload()
        p["input_digest"] = "sha256:ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("input_digest_must_be_valid_digest", receipt.failures)

    def test_bool_as_string_rejected(self):
        p = _valid_payload()
        p["dry_run"] = "true"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("dry_run_must_be_bool", receipt.failures)

    def test_bool_as_int_rejected(self):
        p = _valid_payload()
        p["dry_run"] = 1
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("dry_run_must_be_bool", receipt.failures)

    def test_dry_run_false_rejected(self):
        p = _valid_payload()
        p["dry_run"] = False
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("dry_run_must_be_true", receipt.failures)

    def test_provider_enabled_true_rejected(self):
        p = _valid_payload()
        p["provider_enabled"] = True
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("provider_enabled_must_be_false", receipt.failures)

    def test_network_access_true_rejected(self):
        p = _valid_payload()
        p["network_access"] = True
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("network_access_must_be_false", receipt.failures)

    def test_production_autonomy_true_rejected(self):
        p = _valid_payload()
        p["production_autonomy"] = True
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("production_autonomy_must_be_false", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = _valid_payload()
        p["raw_prompt"] = "do something"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_raw_provider_response_rejected(self):
        p = _valid_payload()
        p["raw_provider_response"] = "some response"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("raw_provider_response_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        p = _valid_payload()
        p["secret_value"] = "my-secret"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_env_value_rejected(self):
        p = _valid_payload()
        p["env_value"] = "MY_VAR=val"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("env_value_forbidden", receipt.failures)

    def test_provider_api_key_rejected(self):
        p = _valid_payload()
        p["provider_api_key"] = "sk-abc123"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("provider_api_key_forbidden", receipt.failures)

    def test_live_network_target_rejected(self):
        p = _valid_payload()
        p["live_network_target"] = "api.example.com"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("live_network_target_forbidden", receipt.failures)

    def test_autonomy_directive_rejected(self):
        p = _valid_payload()
        p["autonomy_directive"] = "auto_deploy"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertIn("autonomy_directive_forbidden", receipt.failures)

    def test_multiple_failures_accumulated(self):
        p = _valid_payload()
        del p["task_id"]
        p["dry_run"] = False
        p["raw_prompt"] = "bad"
        receipt = validate_execution_descriptor(p)
        self.assertFalse(receipt.accepted)
        self.assertGreaterEqual(len(receipt.failures), 3)


class ExecutionDescriptorSideEffectFreeTests(unittest.TestCase):
    """Side-effect freedom tests."""

    def test_validate_execution_descriptor_does_not_mutate(self):
        payload = _valid_payload()
        before = copy.deepcopy(payload)
        validate_execution_descriptor(payload)
        self.assertEqual(payload, before)

    def test_no_sqlite_import(self):
        import kernel.runtime.execution_descriptor as ed
        source = ed.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("sqlite3", content)

    def test_no_network_imports(self):
        import kernel.runtime.execution_descriptor as ed
        source = ed.__file__
        if source:
            with open(source, "r") as f:
                content = f.read()
            self.assertNotIn("requests", content)
            self.assertNotIn("urllib", content)
            self.assertNotIn("socket", content)
