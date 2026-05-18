"""Tracer-bullet tests for the bounded local runtime orchestrator."""

import unittest
from pathlib import Path

from kernel.audit.trail import AuditTrail
from kernel.deadlock.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from kernel.retry.backoff import RetryConfig
from kernel.runtime.local_runtime_orchestrator import orchestrate_local_runtime
from tools.provider_transport.provider_adapter_registry import ProviderAdapterDescriptor, register_provider_adapter
from tools.provider_transport.provider_transport_runtime import TransportExecutionResult, execute_provider_transport


def _payload():
    return {
        "task_id": "task-local-runtime-001",
        "run_id": "run-local-runtime-001",
        "runtime_stage": "local_runtime_dry_run",
        "dry_run": True,
        "policy_version": "v1",
        "provider_request": {
            "provider_id": "mock-finance",
            "request_id": "provider-request-001",
            "evidence_binding": "evidence-binding-001",
            "capabilities": ["fetch_price", "validate_asset"],
        },
    }


class LocalRuntimeOrchestratorSuccessTests(unittest.TestCase):
    def test_success_path_creates_deterministic_runtime_receipt(self):
        first = orchestrate_local_runtime(_payload(), observed_at="2026-01-01T00:00:00Z")
        second = orchestrate_local_runtime(_payload(), observed_at="2027-01-01T00:00:00Z")

        self.assertTrue(first.accepted, first.as_dict())
        self.assertTrue(second.accepted, second.as_dict())
        self.assertEqual(first.receipt.content_hash, second.receipt.content_hash)
        self.assertEqual(first.receipt.deterministic_material(), second.receipt.deterministic_material())
        self.assertNotIn("observed_at", first.receipt.deterministic_material())
        self.assertIsNotNone(first.provider_dry_run_receipt)
        self.assertTrue(first.provider_dry_run_receipt.dry_run)
        self.assertTrue(first.provider_dry_run_receipt.no_network)
        self.assertTrue(first.provider_dry_run_receipt.no_provider_call)

    def test_audit_trail_links_are_preserved(self):
        trail = AuditTrail(name="local-runtime-test")
        result = orchestrate_local_runtime(_payload(), audit_trail=trail, observed_at="2026-01-01T00:00:00Z")

        self.assertTrue(result.accepted, result.as_dict())
        self.assertGreaterEqual(trail.count, 6)
        self.assertTrue(trail.verify_integrity())
        self.assertEqual(result.audit_chain_head, trail.entries[-1].hash_chain_entry.current_hash)
        self.assertEqual(result.audit_entry_hashes[-1], trail.entries[-1].content_hash)

    def test_state_transitions_are_deterministic(self):
        first = orchestrate_local_runtime(_payload(), observed_at="2026-01-01T00:00:00Z")
        second = orchestrate_local_runtime(_payload(), observed_at="2027-01-01T00:00:00Z")

        self.assertEqual(first.state_transition_hashes, second.state_transition_hashes)
        self.assertEqual(len(first.state_transition_hashes), 3)

    def test_watchdog_is_observation_control_only(self):
        result = orchestrate_local_runtime(_payload(), observed_at="2026-01-01T00:00:00Z")

        self.assertTrue(result.boundary_flags["watchdog_control_only"])
        self.assertTrue(result.watchdog_snapshot["dry_run_only"])
        self.assertTrue(result.watchdog_snapshot["control_only"])
        self.assertFalse(result.boundary_flags["production_autonomy_allowed"])


class LocalRuntimeOrchestratorFailureTests(unittest.TestCase):
    def test_failure_path_fails_closed_and_emits_failure_bundle(self):
        payload = _payload()
        payload["raw_prompt"] = "do not persist this prompt"

        result = orchestrate_local_runtime(payload, observed_at="2026-01-01T00:00:00Z")

        self.assertFalse(result.accepted)
        self.assertFalse(result.receipt.accepted)
        self.assertIsNotNone(result.failure_bundle)
        self.assertEqual(result.failure_bundle.failure_code, "runtime_guard_rejected")
        self.assertEqual(result.receipt.failure_bundle_ref, result.failure_bundle.content_hash)
        self.assertTrue(result.receipt.rejection_reason)
        self.assertNotIn("do not persist this prompt", str(result.as_dict()))

    def test_network_live_subprocess_secret_env_raw_and_sqlite_attempts_rejected(self):
        cases = (
            ("network_execution", True, "network_execution_rejected"),
            ("live_provider_call", True, "live_provider_call_rejected"),
            ("subprocess", ["python"], "subprocess_execution_rejected"),
            ("api_key", "sk-test", "secret_field_rejected"),
            ("env", {"API_KEY": "value"}, "env_value_read_rejected"),
            ("raw_provider_response", "raw response", "raw_provider_response_persistence_rejected"),
            ("raw_traceback", "traceback", "raw_exception_persistence_rejected"),
            ("sqlite_mutation", True, "sqlite_mutation_rejected"),
            ("production_autonomy", True, "production_autonomy_rejected"),
        )
        for field, value, expected in cases:
            payload = _payload()
            payload[field] = value
            result = orchestrate_local_runtime(payload, observed_at="2026-01-01T00:00:00Z")
            self.assertFalse(result.accepted, field)
            self.assertIn(expected, result.receipt.rejection_reason, result.receipt.rejection_reason)

    def test_wall_clock_timestamps_do_not_enter_failure_hashes(self):
        payload = _payload()
        payload["raw_input"] = "raw input must not persist"
        first = orchestrate_local_runtime(payload, observed_at="2026-01-01T00:00:00Z")
        second = orchestrate_local_runtime(payload, observed_at="2027-01-01T00:00:00Z")

        self.assertNotEqual(first.receipt.observed_at, second.receipt.observed_at)
        self.assertEqual(first.receipt.content_hash, second.receipt.content_hash)
        self.assertEqual(first.failure_bundle.content_hash, second.failure_bundle.content_hash)

    def test_retry_backoff_is_bounded(self):
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary raw failure text")
            register_provider_adapter(
                ProviderAdapterDescriptor(
                    provider_id="mock-finance",
                    capabilities=frozenset(["fetch_price", "validate_asset"]),
                    boundary_ref="local-runtime-dry-run-provider-boundary-v1",
                    enabled=False,
                    dry_run_only=True,
                    no_network=True,
                )
            )
            return execute_provider_transport({
                "provider_id": "mock-finance",
                "request_id": "retry-request-001",
                "capability_token": "fetch_price,validate_asset",
                "evidence_binding": "retry-evidence-001",
                "dry_run": True,
                "live_mode": False,
                "network_mode": False,
            })

        result = orchestrate_local_runtime(
            _payload(),
            retry_config=RetryConfig(max_attempts=2, base_delay_seconds=0.25, max_delay_seconds=0.25),
            provider_operation=flaky,
            observed_at="2026-01-01T00:00:00Z",
        )

        self.assertTrue(result.accepted, result.as_dict())
        self.assertEqual(result.retry_attempts, 2)
        self.assertEqual(result.retry_total_delay_seconds, 0.25)
        self.assertEqual(calls["count"], 2)

    def test_circuit_breaker_rejects_after_failure_threshold(self):
        breaker = CircuitBreaker(
            "local-runtime-test-breaker",
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=999.0),
            clock=lambda: 0.0,
        )

        def failing_provider():
            raise RuntimeError("provider unavailable with raw details")

        first = orchestrate_local_runtime(
            _payload(),
            circuit_breaker=breaker,
            retry_config=RetryConfig(max_attempts=1, base_delay_seconds=0.0, max_delay_seconds=0.0),
            provider_operation=failing_provider,
            observed_at="2026-01-01T00:00:00Z",
        )
        second = orchestrate_local_runtime(
            _payload(),
            circuit_breaker=breaker,
            retry_config=RetryConfig(max_attempts=1, base_delay_seconds=0.0, max_delay_seconds=0.0),
            provider_operation=lambda: self.fail("open breaker must not call provider"),
            observed_at="2026-01-01T00:00:01Z",
        )

        self.assertFalse(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(breaker.state, CircuitState.OPEN)
        self.assertEqual(second.circuit_breaker_snapshot["state"], "OPEN")
        self.assertIn("provider_transport_failed", second.receipt.rejection_reason)

    def test_provider_transport_failure_receipt_does_not_accept_orchestrator(self):
        def rejected_transport():
            return TransportExecutionResult(
                accepted=False,
                dry_run_receipt=None,
                failure_receipt=None,
                preflight_result=None,
                capability_result=None,
                evidence_result=None,
                budget_result=None,
                network_result=None,
            )

        result = orchestrate_local_runtime(
            _payload(),
            provider_operation=rejected_transport,
            observed_at="2026-01-01T00:00:00Z",
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.failure_bundle.failure_stage, "provider_transport")
        self.assertIn("provider_transport_rejected", result.receipt.rejection_reason)

    def test_no_existing_boundary_is_weakened_in_source(self):
        for rel_path in (
            "kernel/runtime/local_runtime_orchestrator.py",
            "kernel/runtime/local_runtime_guards.py",
            "kernel/runtime/local_runtime_receipt.py",
            "kernel/runtime/local_runtime_failure_bundle.py",
        ):
            source = Path(rel_path).read_text(encoding="utf-8")
            for marker in ("import subprocess", "import socket", "import requests", "import httpx", "import sqlite3"):
                self.assertNotIn(marker, source, rel_path)
            for marker in ("os.environ", "os.getenv", "load_dotenv", "write_text("):
                self.assertNotIn(marker, source, rel_path)


if __name__ == "__main__":
    unittest.main()
