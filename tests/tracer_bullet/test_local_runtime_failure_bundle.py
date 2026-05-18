"""Tracer-bullet tests for the local runtime failure bundle contract."""

import unittest
from pathlib import Path

from kernel.runtime.local_runtime_failure_bundle import (
    build_local_runtime_failure_bundle,
    sanitize_exception_type,
    validate_local_runtime_failure_bundle,
)

VALID_DIGEST = "sha256:" + "b" * 64


class LocalRuntimeFailureBundleTests(unittest.TestCase):
    def test_failure_bundle_contains_only_sanitized_contract_fields(self):
        bundle = build_local_runtime_failure_bundle(
            failure_code="runtime_guard_rejected",
            failure_stage="guard",
            input_digest=VALID_DIGEST,
            run_id="run-001",
            task_id="task-001",
            exception=RuntimeError("raw secret traceback text should not persist"),
        )

        payload = bundle.as_dict()

        self.assertEqual(payload["failure_code"], "runtime_guard_rejected")
        self.assertEqual(payload["failure_stage"], "guard")
        self.assertEqual(payload["sanitized_exception_type"], "RuntimeError")
        self.assertEqual(payload["input_digest"], VALID_DIGEST)
        self.assertTrue(payload["content_hash"].startswith("sha256:"))
        self.assertNotIn("raw_traceback", payload)
        self.assertNotIn("raw_exception", payload)
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("raw_provider_response", payload)
        self.assertTrue(validate_local_runtime_failure_bundle(bundle))

    def test_failure_bundle_hash_is_deterministic(self):
        first = build_local_runtime_failure_bundle(
            failure_code="provider_transport_failed",
            failure_stage="provider_transport",
            input_digest=VALID_DIGEST,
            run_id="run-001",
            task_id="task-001",
            exception_type="ValueError",
        )
        second = build_local_runtime_failure_bundle(
            failure_code="provider_transport_failed",
            failure_stage="provider_transport",
            input_digest=VALID_DIGEST,
            run_id="run-001",
            task_id="task-001",
            exception_type="ValueError",
        )

        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(first.content_hash, second.content_hash)

    def test_exception_type_sanitizer_never_keeps_exception_text(self):
        self.assertEqual(
            sanitize_exception_type("RuntimeError: token=abc\nTraceback (most recent call last)"),
            "SanitizedException",
        )
        self.assertEqual(sanitize_exception_type("builtins.ValueError"), "ValueError")

    def test_invalid_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "input_digest_must_be_valid_digest"):
            build_local_runtime_failure_bundle(
                failure_code="provider_transport_failed",
                failure_stage="provider_transport",
                input_digest="not-a-digest",
                run_id="run-001",
                task_id="task-001",
            )

    def test_source_does_not_persist_raw_forbidden_payloads(self):
        source = Path("kernel/runtime/local_runtime_failure_bundle.py").read_text(encoding="utf-8")
        for marker in ("import traceback", "format_exc", "write_text(", "import sqlite3"):
            self.assertNotIn(marker, source)
        for marker in ("import subprocess", "import socket", "import requests", "import httpx"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
