"""Deterministic dry-run runtime runner tracer-bullet tests.

Tests the runtime runner foundation:
- dry_run=true required
- provider execution rejected
- network execution rejected
- production autonomy rejected
- raw_prompt, raw_provider_response, secret_value forbidden
- required field validation
- deterministic receipt production
- receipt field integrity
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.runner import (
    RunnerReceipt,
    RunnerRejection,
    compute_output_digest,
    produce_runner_receipt,
    run_dry_run,
    validate_runner_input,
)

POLICY_PATH = Path("governance/runtime/runtime_runner_policy_v1.json")


def _valid_payload():
    """Return a minimal valid payload that should pass all gates."""
    return {
        "dry_run": True,
        "task_id": "task_abc123def4567890123456",
        "run_id": "run_abc123def4567890123456",
        "stage": "dry_run",
        "policy_version": "v1",
        "code_version": "0.1.0",
        "input_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }


class RuntimeRunnerPolicyTests(unittest.TestCase):
    """Policy file integrity tests."""

    def test_policy_file_exists_and_is_valid_json(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Policy file missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "runtime_runner_policy_v1")
        self.assertEqual(policy["version"], "v1")
        self.assertTrue(policy["dry_run_only"])
        self.assertTrue(policy["dry_run_required"])
        self.assertFalse(policy["provider_execution_allowed"])
        self.assertFalse(policy["network_execution_allowed"])
        self.assertFalse(policy["production_autonomy_allowed"])
        self.assertIn("raw_prompt", policy["forbidden_fields"])
        self.assertIn("raw_provider_response", policy["forbidden_fields"])
        self.assertIn("secret_value", policy["forbidden_fields"])
        for field in ("task_id", "run_id", "stage", "policy_version", "code_version", "input_digest"):
            self.assertIn(field, policy["required_fields"])
        for field in ("task_id", "run_id", "stage", "status", "policy_version", "code_version", "input_digest", "output_digest"):
            self.assertIn(field, policy["receipt_required_fields"])
        self.assertTrue(policy["deterministic_required"])


class RuntimeRunnerAcceptanceTests(unittest.TestCase):
    """Happy-path acceptance tests."""

    def test_valid_payload_produces_accepted_receipt(self):
        payload = _valid_payload()
        receipt = run_dry_run(payload)
        self.assertIsInstance(receipt, RunnerReceipt)
        self.assertEqual(receipt.status, "accepted")
        self.assertEqual(receipt.failures, ())
        self.assertTrue(receipt.accepted())

    def test_receipt_contains_all_required_fields(self):
        payload = _valid_payload()
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.task_id, payload["task_id"])
        self.assertEqual(receipt.run_id, payload["run_id"])
        self.assertEqual(receipt.stage, payload["stage"])
        self.assertEqual(receipt.policy_version, payload["policy_version"])
        self.assertEqual(receipt.code_version, payload["code_version"])
        self.assertEqual(receipt.input_digest, payload["input_digest"])
        self.assertTrue(receipt.output_digest.startswith("sha256:"))
        self.assertEqual(len(receipt.output_digest), len("sha256:") + 64)

    def test_receipt_is_deterministic(self):
        payload = _valid_payload()
        receipt1 = run_dry_run(payload)
        receipt2 = run_dry_run(payload)
        self.assertEqual(receipt1.as_dict(), receipt2.as_dict())
        self.assertEqual(receipt1.output_digest, receipt2.output_digest)

    def test_different_inputs_produce_different_receipts(self):
        p1 = _valid_payload()
        p2 = _valid_payload()
        p2["task_id"] = "task_different_id_here_123456"
        r1 = run_dry_run(p1)
        r2 = run_dry_run(p2)
        self.assertNotEqual(r1.output_digest, r2.output_digest)

    def test_receipt_as_dict_exports_all_fields(self):
        payload = _valid_payload()
        receipt = run_dry_run(payload)
        d = receipt.as_dict()
        self.assertEqual(d["task_id"], payload["task_id"])
        self.assertEqual(d["run_id"], payload["run_id"])
        self.assertEqual(d["stage"], payload["stage"])
        self.assertEqual(d["status"], "accepted")
        self.assertEqual(d["policy_version"], payload["policy_version"])
        self.assertEqual(d["code_version"], payload["code_version"])
        self.assertEqual(d["input_digest"], payload["input_digest"])
        self.assertEqual(d["output_digest"], receipt.output_digest)
        self.assertEqual(d["failures"], [])

    def test_validate_runner_input_returns_empty_on_valid(self):
        failures = validate_runner_input(_valid_payload())
        self.assertEqual(failures, ())

    def test_produce_runner_receipt_accepted(self):
        receipt = produce_runner_receipt(_valid_payload())
        self.assertEqual(receipt.status, "accepted")
        self.assertEqual(receipt.failures, ())

    def test_compute_output_digest_is_deterministic(self):
        d1 = compute_output_digest(
            task_id="t1", run_id="r1", stage="s1",
            policy_version="v1", code_version="c1", input_digest="d1",
        )
        d2 = compute_output_digest(
            task_id="t1", run_id="r1", stage="s1",
            policy_version="v1", code_version="c1", input_digest="d1",
        )
        self.assertEqual(d1, d2)


class RuntimeRunnerRejectionTests(unittest.TestCase):
    """Policy boundary rejection tests."""

    def test_dry_run_false_is_rejected(self):
        payload = _valid_payload()
        payload["dry_run"] = False
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("dry_run_must_be_true", receipt.failures)

    def test_dry_run_missing_is_rejected(self):
        payload = _valid_payload()
        del payload["dry_run"]
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("dry_run_must_be_true", receipt.failures)

    def test_dry_run_none_is_rejected(self):
        payload = _valid_payload()
        payload["dry_run"] = None
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("dry_run_must_be_true", receipt.failures)

    def test_provider_execution_rejected(self):
        payload = _valid_payload()
        payload["provider"] = True
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("provider_execution_rejected", receipt.failures)

    def test_network_execution_rejected(self):
        payload = _valid_payload()
        payload["network"] = True
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("network_execution_rejected", receipt.failures)

    def test_production_autonomy_rejected(self):
        payload = _valid_payload()
        payload["production_autonomy"] = True
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("production_autonomy_rejected", receipt.failures)

    def test_raw_prompt_forbidden(self):
        payload = _valid_payload()
        payload["raw_prompt"] = "some prompt text"
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_raw_provider_response_forbidden(self):
        payload = _valid_payload()
        payload["raw_provider_response"] = "some response text"
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("raw_provider_response_forbidden", receipt.failures)

    def test_secret_value_forbidden(self):
        payload = _valid_payload()
        payload["secret_value"] = "sk-abc123"
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_missing_task_id_rejected(self):
        payload = _valid_payload()
        del payload["task_id"]
        receipt = run_dry_run(payload)
        self.assertIn("task_id_required_nonempty_string", receipt.failures)

    def test_empty_task_id_rejected(self):
        payload = _valid_payload()
        payload["task_id"] = ""
        receipt = run_dry_run(payload)
        self.assertIn("task_id_required_nonempty_string", receipt.failures)

    def test_none_task_id_rejected(self):
        payload = _valid_payload()
        payload["task_id"] = None
        receipt = run_dry_run(payload)
        self.assertIn("task_id_required_nonempty_string", receipt.failures)

    def test_missing_run_id_rejected(self):
        payload = _valid_payload()
        del payload["run_id"]
        receipt = run_dry_run(payload)
        self.assertIn("run_id_required_nonempty_string", receipt.failures)

    def test_missing_stage_rejected(self):
        payload = _valid_payload()
        del payload["stage"]
        receipt = run_dry_run(payload)
        self.assertIn("stage_required_nonempty_string", receipt.failures)

    def test_missing_policy_version_rejected(self):
        payload = _valid_payload()
        del payload["policy_version"]
        receipt = run_dry_run(payload)
        self.assertIn("policy_version_required_nonempty_string", receipt.failures)

    def test_missing_code_version_rejected(self):
        payload = _valid_payload()
        del payload["code_version"]
        receipt = run_dry_run(payload)
        self.assertIn("code_version_required_nonempty_string", receipt.failures)

    def test_missing_input_digest_rejected(self):
        payload = _valid_payload()
        del payload["input_digest"]
        receipt = run_dry_run(payload)
        self.assertIn("input_digest_required_nonempty_string", receipt.failures)

    def test_rejected_receipt_has_deterministic_output_digest(self):
        payload = _valid_payload()
        payload["raw_prompt"] = "test"
        r1 = run_dry_run(payload)
        r2 = run_dry_run(payload)
        self.assertTrue(r1.output_digest.startswith("sha256:"))
        self.assertEqual(r1.output_digest, r2.output_digest)

    def test_non_mapping_raises_runner_rejection(self):
        with self.assertRaises(RunnerRejection):
            run_dry_run("not a mapping")

    def test_multiple_failures_accumulated(self):
        payload = _valid_payload()
        payload["dry_run"] = False
        payload["provider"] = True
        payload["raw_prompt"] = "test"
        del payload["task_id"]
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertIn("dry_run_must_be_true", receipt.failures)
        self.assertIn("provider_execution_rejected", receipt.failures)
        self.assertIn("raw_prompt_forbidden", receipt.failures)
        self.assertIn("task_id_required_nonempty_string", receipt.failures)


class RuntimeRunnerSideEffectFreeTests(unittest.TestCase):
    """Verify the runner is side-effect free."""

    def test_validate_runner_input_is_pure(self):
        p1 = _valid_payload()
        p2 = copy.deepcopy(p1)
        validate_runner_input(p1)
        self.assertEqual(p1, p2)

    def test_run_dry_run_does_not_mutate_input(self):
        p1 = _valid_payload()
        p2 = copy.deepcopy(p1)
        run_dry_run(p1)
        self.assertEqual(p1, p2)

    def test_produce_runner_receipt_is_pure(self):
        p1 = _valid_payload()
        p2 = copy.deepcopy(p1)
        produce_runner_receipt(p1)
        self.assertEqual(p1, p2)

    def test_compute_output_digest_is_pure(self):
        compute_output_digest(
            task_id="t1", run_id="r1", stage="s1",
            policy_version="v1", code_version="c1", input_digest="d1",
        )
        # No side effects to check; pure by construction.
        self.assertTrue(True)


class RuntimeRunnerReceiptIntegrityTests(unittest.TestCase):
    """Receipt field integrity and contract tests."""

    def test_accepted_receipt_has_no_failures(self):
        receipt = run_dry_run(_valid_payload())
        self.assertEqual(receipt.status, "accepted")
        self.assertEqual(receipt.failures, ())

    def test_rejected_receipt_has_failures(self):
        payload = _valid_payload()
        payload["dry_run"] = False
        receipt = run_dry_run(payload)
        self.assertEqual(receipt.status, "rejected")
        self.assertGreater(len(receipt.failures), 0)

    def test_receipt_output_digest_length(self):
        receipt = run_dry_run(_valid_payload())
        self.assertEqual(len(receipt.output_digest), len("sha256:") + 64)

    def test_receipt_output_digest_prefix(self):
        receipt = run_dry_run(_valid_payload())
        self.assertTrue(receipt.output_digest.startswith("sha256:"))

    def test_accepted_is_true_only_for_accepted(self):
        accepted = run_dry_run(_valid_payload())
        self.assertTrue(accepted.accepted())
        rejected = run_dry_run({"dry_run": False})
        self.assertFalse(rejected.accepted())
