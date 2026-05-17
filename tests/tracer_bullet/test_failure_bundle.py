"""Failure bundle tracer-bullet tests.

Tests sanitized failure bundle generation and validation.
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.failure_bundle import (
    FailureBundleRejection,
    FailureBundleValidationResult,
    build_failure_bundle,
    validate_failure_bundle,
)

POLICY_PATH = Path("governance/runtime/failure_bundle_policy_v1.json")


def _valid_bundle():
    return build_failure_bundle(
        task_id="task-001",
        run_id="run-001",
        stage="dry_run",
        error_class="ValueError",
        message="Something went wrong",
        state_snapshot={"stage": "dry_run"},
        input_snapshot={"task_id": "task-001"},
        policy_version="v1",
        code_version="0.1.0",
        retry_decision="no_retry",
        quarantine_ref="q-ref-001",
        rollback_ref="rb-ref-001",
    )


class FailureBundlePolicyTests(unittest.TestCase):
    def test_policy_file_exists(self):
        self.assertTrue(POLICY_PATH.is_file())
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertTrue(policy["sanitized_only"])
        self.assertIn("retry_decision", policy["required_fields"])


class FailureBundleAcceptanceTests(unittest.TestCase):
    def test_valid_bundle_accepted(self):
        result = validate_failure_bundle(_valid_bundle())
        self.assertTrue(result.accepted)
        self.assertEqual(result.failures, ())

    def test_bundle_has_deterministic_digest(self):
        b1 = _valid_bundle()
        b2 = _valid_bundle()
        r1 = validate_failure_bundle(b1)
        r2 = validate_failure_bundle(b2)
        self.assertEqual(r1.bundle_digest, r2.bundle_digest)

    def test_bundle_contains_all_fields(self):
        bundle = _valid_bundle()
        for field in ("failure_id", "task_id", "run_id", "stage", "error_class",
                       "sanitized_message", "state_snapshot_digest", "input_snapshot_digest",
                       "policy_version", "code_version", "retry_decision",
                       "quarantine_ref", "rollback_ref"):
            self.assertIn(field, bundle)

    def test_snapshots_are_digests_only(self):
        bundle = _valid_bundle()
        self.assertTrue(bundle["state_snapshot_digest"].startswith("sha256:"))
        self.assertTrue(bundle["input_snapshot_digest"].startswith("sha256:"))

    def test_failure_id_is_deterministic(self):
        b1 = _valid_bundle()
        b2 = _valid_bundle()
        self.assertEqual(b1["failure_id"], b2["failure_id"])


class FailureBundleRejectionTests(unittest.TestCase):
    def test_raw_prompt_rejected(self):
        bundle = _valid_bundle()
        bundle["raw_prompt"] = "test"
        result = validate_failure_bundle(bundle)
        self.assertIn("raw_prompt_forbidden", result.failures)

    def test_raw_provider_response_rejected(self):
        bundle = _valid_bundle()
        bundle["raw_provider_response"] = "test"
        result = validate_failure_bundle(bundle)
        self.assertIn("raw_provider_response_forbidden", result.failures)

    def test_secret_value_rejected(self):
        bundle = _valid_bundle()
        bundle["secret_value"] = "sk-abc"
        result = validate_failure_bundle(bundle)
        self.assertIn("secret_value_forbidden", result.failures)

    def test_env_value_rejected(self):
        bundle = _valid_bundle()
        bundle["env_value"] = "PATH=/usr/bin"
        result = validate_failure_bundle(bundle)
        self.assertIn("env_value_forbidden", result.failures)

    def test_invalid_digest_rejected(self):
        bundle = _valid_bundle()
        bundle["state_snapshot_digest"] = "bad_digest"
        result = validate_failure_bundle(bundle)
        self.assertIn("state_snapshot_digest_must_be_sha256_prefixed", result.failures)

    def test_missing_retry_decision_rejected(self):
        bundle = _valid_bundle()
        del bundle["retry_decision"]
        result = validate_failure_bundle(bundle)
        self.assertIn("retry_decision_required", result.failures)

    def test_sanitized_message_no_secrets(self):
        bundle = build_failure_bundle(
            task_id="t1", run_id="r1", stage="s1", error_class="E",
            message="sk-secret-key-here", state_snapshot={}, input_snapshot={},
            policy_version="v1", code_version="c1",
            retry_decision="no", quarantine_ref="q", rollback_ref="rb",
        )
        self.assertEqual(bundle["sanitized_message"], "[sanitized]")


class FailureBundleSideEffectFreeTests(unittest.TestCase):
    def test_validate_does_not_mutate(self):
        b1 = _valid_bundle()
        b2 = copy.deepcopy(b1)
        validate_failure_bundle(b1)
        self.assertEqual(b1, b2)

    def test_build_is_deterministic(self):
        kwargs = dict(task_id="t1", run_id="r1", stage="s1", error_class="E",
                       message="msg", state_snapshot={"a": 1},
                       input_snapshot={"b": 2}, policy_version="v1",
                       code_version="c1", retry_decision="no",
                       quarantine_ref="q", rollback_ref="rb")
        b1 = build_failure_bundle(**kwargs)
        b2 = build_failure_bundle(**kwargs)
        self.assertEqual(b1, b2)
