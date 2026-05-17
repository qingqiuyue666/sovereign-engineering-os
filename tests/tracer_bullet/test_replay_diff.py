"""Replay diff tracer-bullet tests."""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.replay_diff import validate_replay_diff

POLICY_PATH = Path("governance/runtime/replay_diff_policy_v1.json")


def _valid_diff():
    return {
        "expected_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "actual_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "policy_version": "v1",
        "code_version": "0.1.0",
        "bound_version_tuple": ["v1", "0.1.0"],
    }


class ReplayDiffPolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertIn("bound_version_tuple", policy["required_fields"])


class ReplayDiffAcceptanceTests(unittest.TestCase):
    def test_exact_match_accepted(self):
        receipt = validate_replay_diff(_valid_diff())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.replay_match)

    def test_deterministic_receipt(self):
        r1 = validate_replay_diff(_valid_diff())
        r2 = validate_replay_diff(_valid_diff())
        self.assertEqual(r1.as_dict(), r2.as_dict())


class ReplayDiffRejectionTests(unittest.TestCase):
    def test_output_digest_mismatch_detected(self):
        p = _valid_diff()
        p["actual_output_digest"] = "sha256:different_digest_here_1234567890abcdef1234567890ab"
        receipt = validate_replay_diff(p)
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.replay_match)
        self.assertIn("output_digest_mismatch", receipt.failures)

    def test_raw_prompt_rejected(self):
        p = _valid_diff()
        p["raw_prompt"] = "test"
        receipt = validate_replay_diff(p)
        self.assertIn("raw_prompt_forbidden", receipt.failures)

    def test_secret_value_rejected(self):
        p = _valid_diff()
        p["secret_value"] = "sk-abc"
        receipt = validate_replay_diff(p)
        self.assertIn("secret_value_forbidden", receipt.failures)

    def test_missing_bound_version_tuple_rejected(self):
        p = _valid_diff()
        del p["bound_version_tuple"]
        receipt = validate_replay_diff(p)
        self.assertIn("bound_version_tuple_required", receipt.failures)

    def test_empty_bound_version_tuple_rejected(self):
        p = _valid_diff()
        p["bound_version_tuple"] = []
        receipt = validate_replay_diff(p)
        self.assertIn("bound_version_tuple_must_be_nonempty", receipt.failures)


class ReplayDiffSideEffectFreeTests(unittest.TestCase):
    def test_validate_does_not_mutate(self):
        p1 = _valid_diff()
        p2 = copy.deepcopy(p1)
        validate_replay_diff(p1)
        self.assertEqual(p1, p2)
