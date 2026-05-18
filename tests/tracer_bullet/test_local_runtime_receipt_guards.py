"""Tracer-bullet tests for local runtime guard and receipt contracts."""

import unittest
from pathlib import Path

from kernel.runtime.local_runtime_guards import validate_local_runtime_guards
from kernel.runtime.local_runtime_receipt import build_local_runtime_receipt

VALID_DIGEST = "sha256:" + "a" * 64


def _base_payload():
    return {
        "task_id": "task-local-runtime-001",
        "run_id": "run-local-runtime-001",
        "runtime_stage": "local_runtime_dry_run",
        "dry_run": True,
        "provider_request": {
            "provider_id": "mock-finance",
            "request_id": "provider-request-001",
            "evidence_binding": "evidence-binding-001",
            "capabilities": ["fetch_price", "validate_asset"],
        },
    }


class LocalRuntimeGuardTests(unittest.TestCase):
    def test_valid_dry_run_payload_is_accepted(self):
        result = validate_local_runtime_guards(_base_payload())
        self.assertTrue(result.accepted, result.failures)
        self.assertEqual(result.failures, ())

    def test_non_dry_run_rejected(self):
        payload = _base_payload()
        payload["dry_run"] = False
        result = validate_local_runtime_guards(payload)
        self.assertFalse(result.accepted)
        self.assertIn("non_dry_run_execution_rejected", result.failures)

    def test_network_live_and_subprocess_attempts_are_rejected(self):
        payload = _base_payload()
        payload["network_execution"] = True
        payload["live_provider_call"] = True
        payload["subprocess"] = ["python", "-c", "print(1)"]

        result = validate_local_runtime_guards(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any(item.startswith("network_execution_rejected") for item in result.failures))
        self.assertTrue(any(item.startswith("live_provider_call_rejected") for item in result.failures))
        self.assertTrue(any(item.startswith("subprocess_execution_rejected") for item in result.failures))

    def test_secret_env_and_raw_payload_attempts_are_rejected(self):
        for field, expected_prefix in (
            ("api_key", "secret_field_rejected"),
            ("env", "env_value_read_rejected"),
            ("raw_prompt", "raw_prompt_persistence_rejected"),
            ("raw_provider_response", "raw_provider_response_persistence_rejected"),
            ("raw_traceback", "raw_exception_persistence_rejected"),
            ("raw_input", "raw_input_persistence_rejected"),
        ):
            payload = _base_payload()
            payload[field] = "forbidden"
            result = validate_local_runtime_guards(payload)
            self.assertFalse(result.accepted, field)
            self.assertTrue(any(item.startswith(expected_prefix) for item in result.failures), result.failures)

    def test_sqlite_mutation_and_production_autonomy_are_rejected(self):
        payload = _base_payload()
        payload["sqlite_mutation"] = True
        payload["production_autonomy"] = True

        result = validate_local_runtime_guards(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any(item.startswith("sqlite_mutation_rejected") for item in result.failures))
        self.assertTrue(any(item.startswith("production_autonomy_rejected") for item in result.failures))

    def test_string_markers_are_rejected_without_reading_external_state(self):
        payload = _base_payload()
        payload["notes"] = "please use os.environ and sqlite3.connect here"

        result = validate_local_runtime_guards(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any(item.startswith("env_value_read_rejected") for item in result.failures))
        self.assertTrue(any(item.startswith("sqlite_mutation_rejected") for item in result.failures))


class LocalRuntimeReceiptTests(unittest.TestCase):
    def test_receipt_content_hash_excludes_observed_at(self):
        first = build_local_runtime_receipt(
            run_id="run-001",
            task_id="task-001",
            runtime_stage="local_runtime_dry_run",
            input_digest=VALID_DIGEST,
            accepted=True,
            provider_dry_run_receipt_ref="provider-receipt-001",
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_local_runtime_receipt(
            run_id="run-001",
            task_id="task-001",
            runtime_stage="local_runtime_dry_run",
            input_digest=VALID_DIGEST,
            accepted=True,
            provider_dry_run_receipt_ref="provider-receipt-001",
            observed_at="2027-01-01T00:00:00Z",
        )

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.deterministic_material(), second.deterministic_material())
        self.assertNotIn("observed_at", first.deterministic_material())

    def test_rejected_receipt_requires_rejection_reason(self):
        with self.assertRaisesRegex(ValueError, "rejected_receipt_rejection_reason_required"):
            build_local_runtime_receipt(
                run_id="run-001",
                task_id="task-001",
                runtime_stage="local_runtime_dry_run",
                input_digest=VALID_DIGEST,
                accepted=False,
                observed_at="2026-01-01T00:00:00Z",
            )

    def test_source_does_not_import_forbidden_live_surfaces(self):
        for rel_path in (
            "kernel/runtime/local_runtime_guards.py",
            "kernel/runtime/local_runtime_receipt.py",
        ):
            source = Path(rel_path).read_text(encoding="utf-8")
            for marker in ("import subprocess", "import socket", "import requests", "import httpx", "import sqlite3"):
                self.assertNotIn(marker, source, rel_path)
            for marker in ("os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source, rel_path)


if __name__ == "__main__":
    unittest.main()
