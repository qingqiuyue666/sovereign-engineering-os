"""Replay diff tracer-bullet tests — strict typing."""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.replay_diff import validate_replay_diff


def _valid_diff():
    return {
        "expected_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "actual_output_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "policy_version": "v1", "code_version": "0.1.0",
        "bound_version_tuple": ["v1", "0.1.0"],
    }


class ReplayDiffTests(unittest.TestCase):
    def test_exact_match_accepted(self):
        receipt = validate_replay_diff(_valid_diff())
        self.assertTrue(receipt.accepted)
        self.assertTrue(receipt.replay_match)

    def test_output_digest_mismatch(self):
        p = _valid_diff()
        p["actual_output_digest"] = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        receipt = validate_replay_diff(p)
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.replay_match)

    def test_raw_prompt_rejected(self):
        p = _valid_diff(); p["raw_prompt"] = "test"
        self.assertIn("raw_prompt_forbidden", validate_replay_diff(p).failures)

    # Strict typing
    def test_digest_none_rejected(self):
        p = _valid_diff(); p["expected_output_digest"] = None
        self.assertIn("expected_output_digest_must_not_be_none", validate_replay_diff(p).failures)

    def test_digest_bad_prefix_rejected(self):
        p = _valid_diff(); p["expected_output_digest"] = "bad:abc"
        self.assertTrue(any("valid_digest" in f for f in validate_replay_diff(p).failures))

    def test_digest_short_hex_rejected(self):
        p = _valid_diff(); p["actual_output_digest"] = "sha256:abc"
        self.assertTrue(any("valid_digest" in f for f in validate_replay_diff(p).failures))

    def test_bound_version_tuple_none_rejected(self):
        p = _valid_diff(); p["bound_version_tuple"] = None
        self.assertIn("bound_version_tuple_must_not_be_none", validate_replay_diff(p).failures)

    def test_bound_version_tuple_empty_rejected(self):
        p = _valid_diff(); p["bound_version_tuple"] = []
        self.assertIn("bound_version_tuple_must_be_nonempty", validate_replay_diff(p).failures)

    def test_deterministic(self):
        self.assertEqual(validate_replay_diff(_valid_diff()).as_dict(), validate_replay_diff(_valid_diff()).as_dict())
