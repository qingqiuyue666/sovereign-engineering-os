"""Replay plan tracer-bullet tests — strict typing."""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.replay_plan import validate_replay_plan


def _valid_plan():
    return {
        "task_id": "task-001", "run_id": "run-001", "replay_id": "replay-001",
        "input_snapshot_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "state_snapshot_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "policy_version": "v1", "code_version": "0.1.0",
        "environment_descriptor_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "expected_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }


class ReplayPlanTests(unittest.TestCase):
    def test_valid_accepted(self):
        receipt = validate_replay_plan(_valid_plan())
        self.assertTrue(receipt.accepted)

    def test_live_provider_requery_rejected(self):
        p = _valid_plan(); p["provider_live_requery"] = True
        self.assertIn("provider_live_requery_rejected_exact_replay_only", validate_replay_plan(p).failures)

    def test_raw_prompt_rejected(self):
        p = _valid_plan(); p["raw_prompt"] = "test"
        self.assertIn("raw_prompt_forbidden", validate_replay_plan(p).failures)

    # Strict typing
    def test_input_snapshot_digest_none_rejected(self):
        p = _valid_plan(); p["input_snapshot_digest"] = None
        self.assertIn("input_snapshot_digest_must_not_be_none", validate_replay_plan(p).failures)

    def test_digest_bad_prefix_rejected(self):
        p = _valid_plan(); p["state_snapshot_digest"] = "bad:abc"
        self.assertTrue(any("valid_digest" in f for f in validate_replay_plan(p).failures))

    def test_digest_short_hex_rejected(self):
        p = _valid_plan(); p["state_snapshot_digest"] = "sha256:abc"
        self.assertTrue(any("valid_digest" in f for f in validate_replay_plan(p).failures))

    def test_booleans_must_be_bool(self):
        p = _valid_plan(); p["provider_live_requery"] = "true"
        self.assertIn("provider_live_requery_must_be_bool", validate_replay_plan(p).failures)

    def test_deterministic(self):
        self.assertEqual(validate_replay_plan(_valid_plan()).as_dict(), validate_replay_plan(_valid_plan()).as_dict())
