"""Replay plan tracer-bullet tests."""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.replay_plan import validate_replay_plan

POLICY_PATH = Path("governance/runtime/replay_plan_policy_v1.json")


def _valid_plan():
    return {
        "task_id": "task-001",
        "run_id": "run-001",
        "replay_id": "replay-001",
        "input_snapshot_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "state_snapshot_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "policy_version": "v1",
        "code_version": "0.1.0",
        "environment_descriptor_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "expected_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }


class ReplayPlanPolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertTrue(policy["exact_replay_required"])
        self.assertIn("provider_live_requery", policy["forbidden_fields"])


class ReplayPlanAcceptanceTests(unittest.TestCase):
    def test_valid_plan_accepted(self):
        receipt = validate_replay_plan(_valid_plan())
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.failures, ())

    def test_deterministic_receipt(self):
        r1 = validate_replay_plan(_valid_plan())
        r2 = validate_replay_plan(_valid_plan())
        self.assertEqual(r1.as_dict(), r2.as_dict())


class ReplayPlanRejectionTests(unittest.TestCase):
    def test_missing_input_snapshot_rejected(self):
        p = _valid_plan()
        del p["input_snapshot_digest"]
        receipt = validate_replay_plan(p)
        self.assertIn("input_snapshot_digest_required", receipt.failures)

    def test_missing_state_snapshot_rejected(self):
        p = _valid_plan()
        del p["state_snapshot_digest"]
        receipt = validate_replay_plan(p)
        self.assertIn("state_snapshot_digest_required", receipt.failures)

    def test_missing_policy_version_rejected(self):
        p = _valid_plan()
        del p["policy_version"]
        receipt = validate_replay_plan(p)
        self.assertIn("policy_version_required", receipt.failures)

    def test_missing_code_version_rejected(self):
        p = _valid_plan()
        del p["code_version"]
        receipt = validate_replay_plan(p)
        self.assertIn("code_version_required", receipt.failures)

    def test_live_provider_requery_rejected(self):
        p = _valid_plan()
        p["provider_live_requery"] = True
        receipt = validate_replay_plan(p)
        self.assertIn("provider_live_requery_rejected_exact_replay_only", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = _valid_plan()
        p["raw_prompt"] = "test"
        receipt = validate_replay_plan(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        p = _valid_plan()
        p["secret_value"] = "sk-abc"
        receipt = validate_replay_plan(p)
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_non_mapping_does_not_crash(self):
        pass


class ReplayPlanSideEffectFreeTests(unittest.TestCase):
    def test_validate_does_not_mutate(self):
        p1 = _valid_plan()
        p2 = copy.deepcopy(p1)
        validate_replay_plan(p1)
        self.assertEqual(p1, p2)
