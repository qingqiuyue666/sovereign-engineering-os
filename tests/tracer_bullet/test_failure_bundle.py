"""Failure bundle tracer-bullet tests — strict typing."""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.failure_bundle import (
    build_failure_bundle,
    validate_failure_bundle,
)

POLICY_PATH = Path("governance/runtime/failure_bundle_policy_v1.json")


def _valid_bundle():
    return build_failure_bundle(
        task_id="task-001", run_id="run-001", stage="dry_run",
        error_class="ValueError", message="Something went wrong",
        state_snapshot={"stage": "dry_run"}, input_snapshot={"task_id": "task-001"},
        policy_version="v1", code_version="0.1.0",
        retry_decision="no_retry", quarantine_ref="q-ref-001", rollback_ref="rb-ref-001",
    )


class FailureBundleAcceptanceTests(unittest.TestCase):
    def test_valid_bundle_accepted(self):
        result = validate_failure_bundle(_valid_bundle())
        self.assertTrue(result.accepted)

    def test_build_is_deterministic(self):
        kwargs = dict(task_id="t1", run_id="r1", stage="s1", error_class="E",
                       message="msg", state_snapshot={"a": 1}, input_snapshot={"b": 2},
                       policy_version="v1", code_version="c1", retry_decision="no",
                       quarantine_ref="q", rollback_ref="rb")
        self.assertEqual(build_failure_bundle(**kwargs), build_failure_bundle(**kwargs))


class FailureBundleRejectionTests(unittest.TestCase):
    def test_raw_prompt_rejected(self):
        b = _valid_bundle(); b["raw_prompt"] = "test"
        self.assertIn("raw_prompt_forbidden", validate_failure_bundle(b).failures)

    def test_secret_value_rejected(self):
        b = _valid_bundle(); b["secret_value"] = "sk-abc"
        self.assertIn("secret_value_forbidden", validate_failure_bundle(b).failures)

    def test_invalid_digest_format_rejected(self):
        b = _valid_bundle(); b["state_snapshot_digest"] = "bad"
        self.assertTrue(any("valid_digest" in f for f in validate_failure_bundle(b).failures))

    def test_digest_none_rejected(self):
        b = _valid_bundle(); b["state_snapshot_digest"] = None
        self.assertIn("state_snapshot_digest_must_not_be_none", validate_failure_bundle(b).failures)

    def test_task_id_none_rejected(self):
        b = _valid_bundle(); b["task_id"] = None
        self.assertIn("task_id_must_not_be_none", validate_failure_bundle(b).failures)

    def test_task_id_empty_rejected(self):
        b = _valid_bundle(); b["task_id"] = ""
        self.assertTrue(any("task_id" in f for f in validate_failure_bundle(b).failures))
