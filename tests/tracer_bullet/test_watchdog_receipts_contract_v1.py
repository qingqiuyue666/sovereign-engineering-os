"""Tracer-bullet tests for watchdog receipts contract v1."""

from dataclasses import replace
from pathlib import Path
import unittest

from kernel.runtime.watchdog_receipts_contract import (
    build_watchdog_observation_receipt,
    build_watchdog_policy_receipt,
    validate_watchdog_observation_chain,
    validate_watchdog_observation_receipt,
    validate_watchdog_policy_receipt,
)

GENESIS = "sha256:" + "0" * 64
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64
D5 = "sha256:" + "5" * 64
D6 = "sha256:" + "6" * 64
D7 = "sha256:" + "7" * 64
D8 = "sha256:" + "8" * 64
D9 = "sha256:" + "9" * 64


class WatchdogReceiptsContractV1Tests(unittest.TestCase):
    def _policy_payload(self) -> dict[str, object]:
        return {
            "watchdog_policy_id": "watchdog-policy-001",
            "task_id": "task-001",
            "run_id": "run-001",
            "queue_job_hash": D1,
            "worker_admission_receipt_hash": D2,
            "max_runtime_ms": 30_000,
            "max_memory_mb": 512,
            "stdout_limit_bytes": 4096,
            "stderr_limit_bytes": 4096,
            "kill_allowed": False,
            "retry_allowed": False,
        }

    def _observation_payload(
        self,
        policy_hash: str,
        *,
        sequence: int = 1,
        previous_receipt_hash: str = GENESIS,
        observed_state: str = "ok",
    ) -> dict[str, object]:
        failure_bundle_hash = D8 if observed_state != "ok" else None
        return {
            "watchdog_observation_id": f"watchdog-observation-{sequence:03d}",
            "watchdog_policy_hash": policy_hash,
            "task_id": "task-001",
            "run_id": "run-001",
            "sequence": sequence,
            "previous_receipt_hash": previous_receipt_hash,
            "observed_state": observed_state,
            "elapsed_ms": 1000,
            "observed_memory_mb": 128,
            "stdout_digest": D3,
            "stderr_digest": D4,
            "stdout_truncated": False,
            "stderr_truncated": False,
            "wal_record_hash": D5,
            "artifact_manifest_hash": D6,
            "failure_bundle_hash": failure_bundle_hash,
            "quarantine_required": observed_state != "ok",
        }

    def test_policy_hash_is_deterministic_and_excludes_created_at(self):
        first = build_watchdog_policy_receipt(
            self._policy_payload(),
            created_at="2026-01-01T00:00:00Z",
        )
        second = build_watchdog_policy_receipt(
            self._policy_payload(),
            created_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_watchdog_policy_receipt(first))
        self.assertEqual(first.policy_hash, second.policy_hash)
        self.assertNotEqual(first.created_at, second.created_at)
        self.assertNotIn("created_at", first.deterministic_material())

    def test_policy_rejects_kill_retry_and_raw_material(self):
        for field in ("kill_allowed", "retry_allowed"):
            payload = self._policy_payload()
            payload[field] = True
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    build_watchdog_policy_receipt(payload)

        forbidden_payloads = [
            {"stdout": "raw"},
            {"stderr": "raw"},
            {"raw_output": "raw"},
            {"env": {"TOKEN": "value"}},
            {"argv": ["python"]},
            {"secret_value": "secret"},
            {"filesystem_path": "/tmp/crash.json"},
            {"traceback": "raw trace"},
        ]
        for forbidden in forbidden_payloads:
            payload = self._policy_payload()
            payload.update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    build_watchdog_policy_receipt(payload)

    def test_observation_receipt_is_deterministic_and_allows_digest_only_streams(self):
        policy = build_watchdog_policy_receipt(self._policy_payload())
        first = build_watchdog_observation_receipt(
            self._observation_payload(policy.policy_hash),
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_watchdog_observation_receipt(
            self._observation_payload(policy.policy_hash),
            observed_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(validate_watchdog_observation_receipt(first))
        self.assertEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(first.stdout_digest, D3)
        self.assertEqual(first.stderr_digest, D4)
        self.assertNotIn("observed_at", first.deterministic_material())

    def test_terminal_observation_requires_failure_bundle_and_quarantine(self):
        policy = build_watchdog_policy_receipt(self._policy_payload())
        terminal = build_watchdog_observation_receipt(
            self._observation_payload(policy.policy_hash, observed_state="memory_exceeded")
        )

        self.assertEqual(terminal.observed_state, "memory_exceeded")
        self.assertTrue(terminal.quarantine_required)
        self.assertEqual(terminal.failure_bundle_hash, D8)

        missing_failure = self._observation_payload(
            policy.policy_hash,
            observed_state="deadline_exceeded",
        )
        missing_failure["failure_bundle_hash"] = None
        with self.assertRaises(ValueError):
            build_watchdog_observation_receipt(missing_failure)

        no_quarantine = self._observation_payload(
            policy.policy_hash,
            observed_state="worker_exit_nonzero",
        )
        no_quarantine["quarantine_required"] = False
        with self.assertRaises(ValueError):
            build_watchdog_observation_receipt(no_quarantine)

    def test_ok_observation_rejects_failure_bundle_and_quarantine(self):
        policy = build_watchdog_policy_receipt(self._policy_payload())
        payload = self._observation_payload(policy.policy_hash)
        payload["failure_bundle_hash"] = D8
        with self.assertRaises(ValueError):
            build_watchdog_observation_receipt(payload)

        payload = self._observation_payload(policy.policy_hash)
        payload["quarantine_required"] = True
        with self.assertRaises(ValueError):
            build_watchdog_observation_receipt(payload)

    def test_observation_chain_detects_gap_previous_hash_and_identity_mismatch(self):
        policy = build_watchdog_policy_receipt(self._policy_payload())
        first = build_watchdog_observation_receipt(self._observation_payload(policy.policy_hash))
        second = build_watchdog_observation_receipt(
            self._observation_payload(
                policy.policy_hash,
                sequence=2,
                previous_receipt_hash=first.receipt_hash,
            )
        )
        self.assertEqual(validate_watchdog_observation_chain((first, second)), ())

        gap = replace(second, sequence=3)
        self.assertIn("receipt_2_invalid", validate_watchdog_observation_chain((first, gap)))

        bad_previous = replace(
            second,
            previous_receipt_hash=D9,
            receipt_hash=second.receipt_hash,
        )
        failures = validate_watchdog_observation_chain((first, bad_previous))
        self.assertIn("receipt_2_invalid", failures)

        other_run = replace(second, run_id="run-002")
        self.assertIn("receipt_2_invalid", validate_watchdog_observation_chain((first, other_run)))

    def test_validator_rejects_tampered_hashes(self):
        policy = build_watchdog_policy_receipt(self._policy_payload())
        observation = build_watchdog_observation_receipt(
            self._observation_payload(policy.policy_hash)
        )

        self.assertFalse(validate_watchdog_policy_receipt(replace(policy, policy_hash=D9)))
        self.assertFalse(
            validate_watchdog_observation_receipt(replace(observation, receipt_hash=D9))
        )

    def test_source_has_no_execution_storage_provider_or_daemon_surface(self):
        source = Path("kernel/runtime/watchdog_receipts_contract.py").read_text()

        forbidden = [
            "asyncio",
            "sqlite3",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "argparse",
            "click",
            "typer",
            "schedule",
            "daemon",
            "os.environ",
            "Path(",
            "open(",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
